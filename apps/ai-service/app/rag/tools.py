from __future__ import annotations

import importlib
import re
from collections.abc import Awaitable, Callable
from typing import Any, Final

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.contracts import RagSourceItem
from app.rag.guardrails import detect_input_guardrail, log_security_event, wrap_tool_output
from app.rag.ports import KnowledgeBasePort, OperationalBackendPort
from app.rag.schemas import AgentContext, KnowledgeCategory, OperationalToolResult

_DATE_PATTERN: Final[re.Pattern[str]] = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_VALID_ORDER_STATUSES: Final[frozenset[str]] = frozenset(
    {"DRAFT", "CONFIRMED", "IN_PREPARATION", "READY", "DELIVERED", "CANCELLED"}
)

ALLOWED_TOOL_NAMES: Final[frozenset[str]] = frozenset(
    {
        "search_catering_knowledge",
        "get_order_details",
        "get_production_schedule",
        "get_invoice_and_payment_status",
    }
)


class SearchKnowledgeArgs(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    query: str = Field(min_length=1, max_length=500)
    category: KnowledgeCategory | None = None
    top_k: int = Field(default=3, ge=1, le=5)


class OrderLookupArgs(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    query: str = Field(min_length=1, max_length=120)


class ScheduleLookupArgs(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    start_date: str | None = Field(default=None, max_length=20)
    end_date: str | None = Field(default=None, max_length=20)
    status: str | None = Field(default=None, max_length=32)


class InvoiceLookupArgs(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    query: str = Field(min_length=1, max_length=120)


class ToolExecutionOutcome(BaseModel):
    """Sanitized result produced by executing one allowlisted read-only tool."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    tool_name: str
    content_for_llm: str
    sources: list[RagSourceItem] = Field(default_factory=list)
    status: str
    forbidden: bool = False
    not_found: bool = False


class ToolRegistry:
    """Allowlisted dual-source read-only tool registry (ChromaDB + Express PostgreSQL tools)."""

    def __init__(
        self,
        *,
        knowledge_base: KnowledgeBasePort,
        operational_backend: OperationalBackendPort,
    ) -> None:
        self._knowledge_base = knowledge_base
        self._operational_backend = operational_backend

    def openai_tool_schemas(self) -> list[dict[str, Any]]:
        """Export OpenAI-compatible function tool specifications for LLM tool calling."""
        return [
            {
                "type": "function",
                "function": {
                    "name": "search_catering_knowledge",
                    "description": (
                        "Cari informasi resmi tervalidasi PIC di knowledge base ChromaDB "
                        "tentang menu, FAQ, SOP operasional, dan aturan pembayaran/DP."
                    ),
                    "parameters": SearchKnowledgeArgs.model_json_schema(),
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_order_details",
                    "description": (
                        "Ambil detail pesanan aktual secara baca-saja dari PostgreSQL melalui "
                        "Express backend (berdasarkan kode pesanan ORD-... atau nama pemesan)."
                    ),
                    "parameters": OrderLookupArgs.model_json_schema(),
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_production_schedule",
                    "description": (
                        "Ambil jadwal produksi katering aktual secara baca-saja dari PostgreSQL "
                        "melalui Express backend (filter opsional tanggal YYYY-MM-DD dan status)."
                    ),
                    "parameters": ScheduleLookupArgs.model_json_schema(),
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_invoice_and_payment_status",
                    "description": (
                        "Ambil data invoice, total tagihan, status DP, nominal terbayar, dan "
                        "pelunasan aktual secara baca-saja melalui Express backend (dibatasi "
                        "RBAC backend berdasarkan peran pengguna)."
                    ),
                    "parameters": InvoiceLookupArgs.model_json_schema(),
                },
            },
        ]

    def build_langchain_tools(self, context: AgentContext) -> list[Any]:
        """Build LangChain StructuredTool instances when langchain_core is installed."""
        try:
            lc_tools = importlib.import_module("langchain_core.tools")
        except ImportError:
            return []

        structured_tool_cls = lc_tools.StructuredTool
        specs: tuple[tuple[str, str, type[BaseModel]], ...] = (
            (
                "search_catering_knowledge",
                "Cari menu, FAQ, SOP, dan aturan pembayaran tervalidasi PIC di ChromaDB.",
                SearchKnowledgeArgs,
            ),
            (
                "get_order_details",
                "Ambil detail pesanan aktual secara baca-saja via Express backend.",
                OrderLookupArgs,
            ),
            (
                "get_production_schedule",
                "Ambil jadwal produksi aktual secara baca-saja via Express backend.",
                ScheduleLookupArgs,
            ),
            (
                "get_invoice_and_payment_status",
                "Ambil status invoice, DP, dan pelunasan aktual via Express backend (RBAC).",
                InvoiceLookupArgs,
            ),
        )

        tools_out: list[Any] = []
        for tool_name, description, args_schema in specs:
            runner = self._make_langchain_coroutine(tool_name, context)
            tools_out.append(
                structured_tool_cls.from_function(
                    coroutine=runner,
                    name=tool_name,
                    description=description,
                    args_schema=args_schema,
                )
            )
        return tools_out

    def _make_langchain_coroutine(
        self,
        tool_name: str,
        context: AgentContext,
    ) -> Callable[..., Awaitable[str]]:
        async def _invoke(**kwargs: Any) -> str:
            outcome = await self.execute(tool_name, kwargs, context)
            return outcome.content_for_llm

        return _invoke

    async def execute(
        self,
        tool_name: str,
        raw_arguments: dict[str, Any],
        context: AgentContext,
    ) -> ToolExecutionOutcome:
        """Validate allowlist, arguments, and security guardrails before invoking a tool."""
        if tool_name not in ALLOWED_TOOL_NAMES:
            log_security_event(
                category="prompt_injection",
                user_role=context.user_role,
                conversation_id=context.conversation_id,
                request_id=context.request_id,
                tool_name=tool_name,
                detail="Blocked invocation of non-allowlisted or mutating tool.",
            )
            return ToolExecutionOutcome(
                tool_name=tool_name,
                content_for_llm=wrap_tool_output(
                    "security_policy",
                    {"status": "forbidden", "message": "Tool tidak diizinkan."},
                ),
                status="forbidden",
                forbidden=True,
            )

        for value in raw_arguments.values():
            if isinstance(value, str):
                verdict = detect_input_guardrail(value)
                if verdict.blocked:
                    log_security_event(
                        category=verdict.category,
                        user_role=context.user_role,
                        conversation_id=context.conversation_id,
                        request_id=context.request_id,
                        tool_name=tool_name,
                        detail="Blocked unsafe tool argument.",
                    )
                    return ToolExecutionOutcome(
                        tool_name=tool_name,
                        content_for_llm=wrap_tool_output(
                            "security_policy",
                            {"status": "forbidden", "message": "Argumen tool tidak aman."},
                        ),
                        status="forbidden",
                        forbidden=True,
                    )

        if tool_name == "search_catering_knowledge":
            return await self._exec_search_knowledge(raw_arguments)
        if tool_name == "get_order_details":
            return await self._exec_order_details(raw_arguments, context)
        if tool_name == "get_production_schedule":
            return await self._exec_schedule(raw_arguments, context)
        return await self._exec_invoice_status(raw_arguments, context)

    async def _exec_search_knowledge(
        self,
        raw_arguments: dict[str, Any],
    ) -> ToolExecutionOutcome:
        try:
            args = SearchKnowledgeArgs.model_validate(raw_arguments)
        except ValidationError:
            return ToolExecutionOutcome(
                tool_name="search_catering_knowledge",
                content_for_llm=wrap_tool_output(
                    "chromadb",
                    {"status": "invalid_input", "message": "Parameter pencarian KB tidak valid."},
                ),
                status="invalid_input",
            )

        chunks = await self._knowledge_base.search(
            args.query,
            top_k=args.top_k,
            category=args.category,
        )
        verified_chunks = [
            chunk for chunk in chunks if chunk.is_verified and chunk.validation_status == "verified"
        ]
        if not verified_chunks:
            return ToolExecutionOutcome(
                tool_name="search_catering_knowledge",
                content_for_llm=wrap_tool_output(
                    "chromadb",
                    {
                        "status": "not_found",
                        "message": "Tidak ada dokumen tervalidasi PIC yang relevan ditemukan.",
                        "results": [],
                    },
                ),
                status="not_found",
                not_found=True,
            )

        sources = [
            RagSourceItem(
                source=chunk.source,
                category=chunk.category,
                chunk_id=chunk.chunk_id,
                version=chunk.version,
                validated_at=chunk.validated_at,
                validation_status=chunk.validation_status,
                is_verified=chunk.is_verified,
            )
            for chunk in verified_chunks
        ]
        payload = {
            "status": "ok",
            "results": [
                {
                    "chunk_id": chunk.chunk_id,
                    "source": chunk.source,
                    "category": chunk.category,
                    "version": chunk.version,
                    "validated_at": chunk.validated_at,
                    "validation_status": chunk.validation_status,
                    "content": chunk.content,
                }
                for chunk in verified_chunks
            ],
        }
        return ToolExecutionOutcome(
            tool_name="search_catering_knowledge",
            content_for_llm=wrap_tool_output("chromadb", payload),
            sources=sources,
            status="ok",
        )

    async def _exec_order_details(
        self,
        raw_arguments: dict[str, Any],
        context: AgentContext,
    ) -> ToolExecutionOutcome:
        try:
            args = OrderLookupArgs.model_validate(raw_arguments)
        except ValidationError:
            return self._invalid_outcome("get_order_details")

        result = await self._operational_backend.get_order_details(
            query=args.query,
            actor_role=context.user_role,
            actor_id=context.user_id,
            request_id=context.request_id,
        )
        return self._map_operational_result(result, context)

    async def _exec_schedule(
        self,
        raw_arguments: dict[str, Any],
        context: AgentContext,
    ) -> ToolExecutionOutcome:
        try:
            args = ScheduleLookupArgs.model_validate(raw_arguments)
        except ValidationError:
            return self._invalid_outcome("get_production_schedule")

        if args.start_date is not None and not _DATE_PATTERN.match(args.start_date):
            return self._invalid_outcome("get_production_schedule")
        if args.end_date is not None and not _DATE_PATTERN.match(args.end_date):
            return self._invalid_outcome("get_production_schedule")
        normalized_status: str | None = None
        if args.status is not None:
            upper_status = args.status.strip().upper()
            if upper_status not in _VALID_ORDER_STATUSES:
                return self._invalid_outcome("get_production_schedule")
            normalized_status = upper_status

        result = await self._operational_backend.get_production_schedule(
            start_date=args.start_date,
            end_date=args.end_date,
            status=normalized_status,
            actor_role=context.user_role,
            actor_id=context.user_id,
            request_id=context.request_id,
        )
        return self._map_operational_result(result, context)

    async def _exec_invoice_status(
        self,
        raw_arguments: dict[str, Any],
        context: AgentContext,
    ) -> ToolExecutionOutcome:
        try:
            args = InvoiceLookupArgs.model_validate(raw_arguments)
        except ValidationError:
            return self._invalid_outcome("get_invoice_and_payment_status")

        result = await self._operational_backend.get_invoice_and_payment_status(
            query=args.query,
            actor_role=context.user_role,
            actor_id=context.user_id,
            request_id=context.request_id,
        )
        return self._map_operational_result(result, context)

    def _invalid_outcome(self, tool_name: str) -> ToolExecutionOutcome:
        return ToolExecutionOutcome(
            tool_name=tool_name,
            content_for_llm=wrap_tool_output(
                "backend_validation",
                {"status": "invalid_input", "message": "Parameter tool tidak valid."},
            ),
            status="invalid_input",
        )

    def _map_operational_result(
        self,
        result: OperationalToolResult,
        context: AgentContext,
    ) -> ToolExecutionOutcome:
        if result.status == "forbidden":
            log_security_event(
                category="data_exfiltration",
                user_role=context.user_role,
                conversation_id=context.conversation_id,
                request_id=context.request_id,
                tool_name=result.tool_name,
                detail="Backend Express enforced RBAC denial (403) on operational tool.",
            )
            return ToolExecutionOutcome(
                tool_name=result.tool_name,
                content_for_llm=wrap_tool_output(
                    result.source,
                    {"status": "forbidden", "message": result.message},
                ),
                status="forbidden",
                forbidden=True,
            )

        if result.status == "not_found":
            return ToolExecutionOutcome(
                tool_name=result.tool_name,
                content_for_llm=wrap_tool_output(
                    result.source,
                    {"status": "not_found", "message": result.message},
                ),
                status="not_found",
                not_found=True,
            )

        if result.status != "ok":
            return ToolExecutionOutcome(
                tool_name=result.tool_name,
                content_for_llm=wrap_tool_output(
                    result.source,
                    {"status": result.status, "message": result.message},
                ),
                status=result.status,
            )

        sources = [
            RagSourceItem(
                source=result.source,
                category="operational_db",
                reference_id=result.reference_id,
            )
        ]
        return ToolExecutionOutcome(
            tool_name=result.tool_name,
            content_for_llm=wrap_tool_output(
                result.source,
                {
                    "status": "ok",
                    "reference_id": result.reference_id,
                    "data": result.data,
                },
            ),
            sources=sources,
            status="ok",
        )
