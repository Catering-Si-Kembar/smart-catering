from __future__ import annotations

from collections.abc import Sequence

from app.config import AppSettings
from app.contracts import RagChatData, RagChatRequest
from app.ml.relevance.inference import RelevanceClassifierService
from app.rag.adapters import (
    ExpressReadOnlyToolsAdapter,
    OpenAICompatibleLLMClient,
)
from app.rag.graph import AgenticRagGraph
from app.rag.guardrails import DomainRelevanceClassifier
from app.rag.ports import (
    KnowledgeBasePort,
    LLMClientPort,
    OperationalBackendPort,
    RelevanceClassifierPort,
)
from app.rag.schemas import AgentContext, RetrievalEvalReport, RetrievalEvalSample
from app.rag.tools import ToolRegistry


class AgenticRagService:
    """Application service facade exposing Agentic RAG chat and Hit@3 retrieval evaluation."""

    def __init__(
        self,
        *,
        relevance_classifier: RelevanceClassifierPort,
        knowledge_base: KnowledgeBasePort,
        operational_backend: OperationalBackendPort,
        llm_client: LLMClientPort,
        timeout_seconds: float = 15.0,
        max_tool_iterations: int = 3,
    ) -> None:
        self._knowledge_base = knowledge_base
        self._tool_registry = ToolRegistry(
            knowledge_base=knowledge_base,
            operational_backend=operational_backend,
        )
        self._graph = AgenticRagGraph(
            relevance_classifier=relevance_classifier,
            tool_registry=self._tool_registry,
            llm_client=llm_client,
            timeout_seconds=timeout_seconds,
            max_tool_iterations=max_tool_iterations,
        )

    @property
    def tool_registry(self) -> ToolRegistry:
        return self._tool_registry

    async def chat(self, payload: RagChatRequest, *, request_id: str) -> RagChatData:
        context = AgentContext(
            conversation_id=payload.conversation_id,
            user_role=payload.user_role,
            user_id=payload.user_id,
            request_id=request_id,
            history=list(payload.history),
        )
        return await self._graph.run(message=payload.message, context=context)


async def evaluate_retrieval_hit_at_3(
    knowledge_base: KnowledgeBasePort,
    samples: Sequence[RetrievalEvalSample],
) -> RetrievalEvalReport:
    """Evaluate Hit@3 retrieval accuracy and 4-field PIC metadata completeness."""
    if not samples:
        return RetrievalEvalReport(
            total_queries=0,
            hits_at_3=0,
            hit_rate_at_3=0.0,
            metadata_complete_ratio=0.0,
        )

    hits = 0
    total_chunks = 0
    complete_chunks = 0

    for sample in samples:
        chunks = await knowledge_base.search(
            sample.query,
            top_k=3,
            category=sample.category,
        )
        expected = {src.lower() for src in sample.expected_sources}
        retrieved_sources = {chunk.source.lower() for chunk in chunks[:3]}
        if expected & retrieved_sources:
            hits += 1

        for chunk in chunks[:3]:
            total_chunks += 1
            if (
                bool(chunk.source)
                and bool(chunk.version)
                and bool(chunk.validated_at)
                and chunk.validation_status == "verified"
                and chunk.is_verified
            ):
                complete_chunks += 1

    return RetrievalEvalReport(
        total_queries=len(samples),
        hits_at_3=hits,
        hit_rate_at_3=round(hits / len(samples), 4),
        metadata_complete_ratio=(
            round(complete_chunks / total_chunks, 4) if total_chunks > 0 else 0.0
        ),
    )


def build_default_rag_service(
    settings: AppSettings,
    *,
    relevance_service: RelevanceClassifierService | None = None,
    knowledge_base: KnowledgeBasePort | None = None,
) -> AgenticRagService:
    """Assemble default AgenticRagService from isolated AppSettings."""
    if knowledge_base is not None:
        resolved_kb: KnowledgeBasePort = knowledge_base
    else:
        from app.chroma.client import build_default_chroma_service

        resolved_kb = build_default_chroma_service(settings)
    return AgenticRagService(
        relevance_classifier=DomainRelevanceClassifier(relevance_service=relevance_service),
        knowledge_base=resolved_kb,
        operational_backend=ExpressReadOnlyToolsAdapter(
            backend_api_url=settings.backend_api_url,
            internal_service_secret=settings.internal_service_secret,
            timeout_seconds=settings.rag_timeout_seconds,
        ),
        llm_client=OpenAICompatibleLLMClient(
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
            model=settings.llm_model,
        ),
        timeout_seconds=settings.rag_timeout_seconds,
    )
