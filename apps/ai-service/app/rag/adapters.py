from __future__ import annotations

import asyncio
import importlib
import json
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Mapping, Sequence
from typing import Any, Final

from app.contracts import RagUserRole
from app.rag.ports import (
    RagConfigurationError,
    RagRateLimitError,
    RagTimeoutError,
    RagUpstreamError,
)
from app.rag.schemas import (
    KnowledgeChunk,
    LLMResponse,
    OperationalToolResult,
    ToolCallRequest,
)

_DEFAULT_CHROMA_DISTANCE_THRESHOLD: Final[float] = 0.65


async def _http_request_json(
    *,
    method: str,
    url: str,
    headers: Mapping[str, str],
    json_body: dict[str, Any] | None = None,
    params: Mapping[str, str] | None = None,
    timeout_seconds: float = 15.0,
) -> tuple[int, Any]:
    """Perform async JSON HTTP request via httpx when installed, else stdlib urllib."""
    try:
        httpx = importlib.import_module("httpx")
    except ImportError:
        httpx = None

    if httpx is not None:
        try:
            async with httpx.AsyncClient(timeout=timeout_seconds) as client:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=dict(headers),
                    params=dict(params) if params else None,
                    json=json_body,
                )
                body = response.json() if response.content else {}
                return int(response.status_code), body
        except httpx.TimeoutException as exc:
            raise RagTimeoutError("Upstream HTTP request timed out.") from exc
        except httpx.HTTPError as exc:
            raise RagUpstreamError("Upstream HTTP request failed.", retryable=True) from exc
        except ValueError as exc:
            raise RagUpstreamError("Upstream returned invalid JSON.") from exc

    return await asyncio.to_thread(
        _urllib_request_json_sync,
        method=method,
        url=url,
        headers=headers,
        json_body=json_body,
        params=params,
        timeout_seconds=timeout_seconds,
    )


def _urllib_request_json_sync(
    *,
    method: str,
    url: str,
    headers: Mapping[str, str],
    json_body: dict[str, Any] | None,
    params: Mapping[str, str] | None,
    timeout_seconds: float,
) -> tuple[int, Any]:
    target_url = url
    if params:
        encoded = urllib.parse.urlencode(params)
        separator = "&" if "?" in target_url else "?"
        target_url = f"{target_url}{separator}{encoded}"

    data_bytes = (
        json.dumps(json_body, ensure_ascii=False).encode("utf-8") if json_body is not None else None
    )
    req = urllib.request.Request(
        target_url,
        data=data_bytes,
        headers=dict(headers),
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:  # noqa: S310
            raw = resp.read().decode("utf-8")
            parsed = json.loads(raw) if raw.strip() else {}
            return int(resp.status), parsed
    except urllib.error.HTTPError as exc:
        raw_err = exc.read().decode("utf-8", errors="replace")
        try:
            parsed_err: Any = json.loads(raw_err) if raw_err.strip() else {}
        except ValueError:
            parsed_err = {"detail": raw_err[:200]}
        return int(exc.code), parsed_err
    except TimeoutError as exc:
        raise RagTimeoutError("Upstream HTTP request timed out.") from exc
    except urllib.error.URLError as exc:
        if isinstance(exc.reason, TimeoutError):
            raise RagTimeoutError("Upstream HTTP request timed out.") from exc
        raise RagUpstreamError("Upstream HTTP connection failed.", retryable=True) from exc
    except ValueError as exc:
        raise RagUpstreamError("Upstream returned invalid JSON.") from exc


class ChromaKnowledgeBaseAdapter:
    """ChromaDB retrieval adapter enforcing PIC-verified metadata (AI-04)."""

    def __init__(
        self,
        *,
        chroma_url: str,
        collection_name: str = "catering_knowledge",
        max_distance: float = _DEFAULT_CHROMA_DISTANCE_THRESHOLD,
        timeout_seconds: float = 10.0,
    ) -> None:
        self._chroma_url = chroma_url.rstrip("/")
        self._collection_name = collection_name
        self._max_distance = max_distance
        self._timeout_seconds = timeout_seconds

    async def search(
        self,
        query: str,
        *,
        top_k: int = 3,
        category: str | None = None,
    ) -> list[KnowledgeChunk]:
        try:
            chromadb = importlib.import_module("chromadb")
        except ImportError:
            return []

        return await asyncio.to_thread(
            self._query_sync,
            chromadb,
            query,
            top_k,
            category,
        )

    def _query_sync(
        self,
        chromadb_mod: Any,
        query: str,
        top_k: int,
        category: str | None,
    ) -> list[KnowledgeChunk]:
        parsed = urllib.parse.urlparse(self._chroma_url)
        host = parsed.hostname or "127.0.0.1"
        port = parsed.port or (443 if parsed.scheme == "https" else 8000)
        ssl_enabled = parsed.scheme == "https"

        try:
            client = chromadb_mod.HttpClient(host=host, port=port, ssl=ssl_enabled)
            collection = client.get_collection(name=self._collection_name)
            where_filter: dict[str, Any] = (
                {"$and": [{"is_verified": True}, {"category": category}]}
                if category
                else {"is_verified": True}
            )
            raw = collection.query(
                query_texts=[query],
                n_results=top_k,
                where=where_filter,
                include=["documents", "metadatas", "distances"],
            )
        except Exception as exc:
            raise RagUpstreamError(
                "ChromaDB knowledge base is temporarily unavailable.",
                retryable=True,
            ) from exc

        ids_list = (raw.get("ids") or [[]])[0]
        docs_list = (raw.get("documents") or [[]])[0]
        metas_list = (raw.get("metadatas") or [[]])[0]
        dists_list = (raw.get("distances") or [[]])[0]

        chunks: list[KnowledgeChunk] = []
        for chunk_id, doc, meta, dist in zip(
            ids_list,
            docs_list,
            metas_list,
            dists_list,
            strict=False,
        ):
            if not isinstance(meta, Mapping) or not isinstance(doc, str):
                continue
            distance = float(dist) if dist is not None else 1.0
            if distance > self._max_distance:
                continue
            is_verified = bool(meta.get("is_verified", False))
            validation_status = str(meta.get("validation_status", "draft"))
            source = str(meta.get("source") or "").strip()
            version = str(meta.get("version") or "").strip()
            validated_at = str(meta.get("validated_at") or meta.get("last_updated") or "").strip()
            chunk_category = str(meta.get("category") or "general").strip()
            if (
                not is_verified
                or validation_status != "verified"
                or not source
                or not version
                or not validated_at
            ):
                continue
            chunks.append(
                KnowledgeChunk(
                    chunk_id=str(chunk_id),
                    content=doc,
                    distance=round(distance, 4),
                    source=source,
                    category=chunk_category,
                    version=version,
                    validated_at=validated_at,
                    validation_status="verified",
                    is_verified=True,
                )
            )
        return chunks


class ExpressReadOnlyToolsAdapter:
    """Strictly read-only HTTP GET client to Express /api/v1/internal/agent-tools/* (FS-07)."""

    def __init__(
        self,
        *,
        backend_api_url: str,
        internal_service_secret: str = "",
        timeout_seconds: float = 10.0,
    ) -> None:
        self._base_url = backend_api_url.rstrip("/")
        self._internal_secret = internal_service_secret
        self._timeout_seconds = timeout_seconds

    def _build_headers(
        self,
        *,
        actor_role: RagUserRole,
        actor_id: str | None,
        request_id: str,
    ) -> dict[str, str]:
        headers: dict[str, str] = {
            "Accept": "application/json",
            "X-Actor-Role": actor_role,
            "X-Request-Id": request_id,
        }
        if actor_id:
            headers["X-Actor-Id"] = actor_id
        if self._internal_secret:
            headers["X-Internal-Token"] = self._internal_secret
        return headers

    async def _call_read_only_endpoint(
        self,
        *,
        tool_name: str,
        source_label: str,
        path: str,
        params: Mapping[str, str],
        actor_role: RagUserRole,
        actor_id: str | None,
        request_id: str,
        reference_hint: str | None = None,
    ) -> OperationalToolResult:
        url = f"{self._base_url}{path}"
        headers = self._build_headers(
            actor_role=actor_role,
            actor_id=actor_id,
            request_id=request_id,
        )
        try:
            status_code, body = await _http_request_json(
                method="GET",
                url=url,
                headers=headers,
                params=params,
                timeout_seconds=self._timeout_seconds,
            )
        except RagTimeoutError:
            return OperationalToolResult(
                tool_name=tool_name,
                source=source_label,
                status="timeout",
                message="Permintaan data ke backend Express melebihi batas waktu.",
            )
        except RagUpstreamError:
            return OperationalToolResult(
                tool_name=tool_name,
                source=source_label,
                status="unavailable",
                message="Layanan data operasional backend Express sementara tidak dapat dijangkau.",
            )

        if status_code == 403:
            return OperationalToolResult(
                tool_name=tool_name,
                source=source_label,
                status="forbidden",
                message="Akses data ini ditolak oleh kebijakan RBAC backend Express.",
            )
        if status_code == 404:
            return OperationalToolResult(
                tool_name=tool_name,
                source=source_label,
                status="not_found",
                message="Data operasional yang dicari tidak ditemukan di sistem.",
            )
        if status_code == 422:
            return OperationalToolResult(
                tool_name=tool_name,
                source=source_label,
                status="invalid_input",
                message="Parameter pencarian data operasional tidak valid.",
            )
        if status_code != 200:
            return OperationalToolResult(
                tool_name=tool_name,
                source=source_label,
                status="unavailable",
                message="Backend Express mengembalikan status gangguan layanan.",
            )

        data = body.get("data") if isinstance(body, Mapping) else None
        if data is None or (isinstance(data, list) and len(data) == 0):
            return OperationalToolResult(
                tool_name=tool_name,
                source=source_label,
                status="not_found",
                message="Data operasional tidak ditemukan untuk kriteria pencarian tersebut.",
            )

        ref_id = reference_hint
        if isinstance(data, Mapping):
            ref_id = (
                str(
                    data.get("orderNumber")
                    or data.get("invoiceNumber")
                    or data.get("id")
                    or reference_hint
                    or ""
                )
                or None
            )
        elif isinstance(data, list) and data and isinstance(data[0], Mapping):
            first = data[0]
            ref_id = (
                str(
                    first.get("orderNumber")
                    or first.get("invoiceNumber")
                    or first.get("id")
                    or reference_hint
                    or ""
                )
                or None
            )

        return OperationalToolResult(
            tool_name=tool_name,
            source=source_label,
            status="ok",
            reference_id=ref_id,
            data=data if isinstance(data, (dict, list)) else {"value": data},
            message="Data operasional berhasil diambil secara baca-saja.",
        )

    async def get_order_details(
        self,
        *,
        query: str,
        actor_role: RagUserRole,
        actor_id: str | None,
        request_id: str,
    ) -> OperationalToolResult:
        return await self._call_read_only_endpoint(
            tool_name="get_order_details",
            source_label="postgresql:orders",
            path="/api/v1/internal/agent-tools/orders",
            params={"q": query.strip()},
            actor_role=actor_role,
            actor_id=actor_id,
            request_id=request_id,
            reference_hint=query.strip(),
        )

    async def get_production_schedule(
        self,
        *,
        start_date: str | None,
        end_date: str | None,
        status: str | None,
        actor_role: RagUserRole,
        actor_id: str | None,
        request_id: str,
    ) -> OperationalToolResult:
        params: dict[str, str] = {}
        if start_date:
            params["startDate"] = start_date
        if end_date:
            params["endDate"] = end_date
        if status:
            params["status"] = status
        return await self._call_read_only_endpoint(
            tool_name="get_production_schedule",
            source_label="postgresql:schedule",
            path="/api/v1/internal/agent-tools/schedule",
            params=params,
            actor_role=actor_role,
            actor_id=actor_id,
            request_id=request_id,
            reference_hint=start_date or "schedule",
        )

    async def get_invoice_and_payment_status(
        self,
        *,
        query: str,
        actor_role: RagUserRole,
        actor_id: str | None,
        request_id: str,
    ) -> OperationalToolResult:
        return await self._call_read_only_endpoint(
            tool_name="get_invoice_and_payment_status",
            source_label="postgresql:invoices",
            path="/api/v1/internal/agent-tools/invoices",
            params={"q": query.strip()},
            actor_role=actor_role,
            actor_id=actor_id,
            request_id=request_id,
            reference_hint=query.strip(),
        )


class OpenAICompatibleLLMClient:
    """Proprietary LLM API client (OpenAI-compatible / Gemini endpoint). Never uses Modal SLM."""

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        model: str,
        max_retries: int = 1,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._max_retries = max_retries

    async def generate_with_tools(
        self,
        *,
        messages: Sequence[dict[str, Any]],
        tools: Sequence[dict[str, Any]],
        timeout_seconds: float,
    ) -> LLMResponse:
        if not self._api_key or not self._base_url or not self._model:
            raise RagConfigurationError(
                "LLM_API_KEY, LLM_BASE_URL, and LLM_MODEL must be configured for RAG chat."
            )

        endpoint = (
            self._base_url
            if self._base_url.endswith("/chat/completions")
            else f"{self._base_url}/chat/completions"
        )
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload: dict[str, Any] = {
            "model": self._model,
            "messages": list(messages),
            "temperature": 0.1,
        }
        if tools:
            payload["tools"] = list(tools)
            payload["tool_choice"] = "auto"

        last_exc: Exception | None = None
        for attempt in range(self._max_retries + 1):
            try:
                status_code, body = await _http_request_json(
                    method="POST",
                    url=endpoint,
                    headers=headers,
                    json_body=payload,
                    timeout_seconds=timeout_seconds,
                )
            except RagTimeoutError:
                raise
            except RagUpstreamError as exc:
                last_exc = exc
                if exc.retryable and attempt < self._max_retries:
                    continue
                raise

            if status_code == 429:
                raise RagRateLimitError("Proprietary LLM provider quota or rate limit exceeded.")
            if status_code in {500, 502, 503, 504} and attempt < self._max_retries:
                last_exc = RagUpstreamError(
                    f"LLM provider returned transient HTTP {status_code}.",
                    retryable=True,
                )
                continue
            if status_code != 200:
                raise RagUpstreamError(
                    f"LLM provider returned HTTP {status_code}.",
                    retryable=False,
                )

            return self._parse_completion_response(body)

        raise last_exc or RagUpstreamError("LLM request failed after retries.")

    def _parse_completion_response(self, body: Any) -> LLMResponse:
        if not isinstance(body, Mapping):
            raise RagUpstreamError("Malformed response from LLM provider.")
        choices = body.get("choices")
        if not isinstance(choices, list) or not choices:
            raise RagUpstreamError("LLM provider returned empty choices.")

        message = choices[0].get("message", {}) if isinstance(choices[0], Mapping) else {}
        content = str(message.get("content") or "").strip()

        raw_calls = message.get("tool_calls") or []
        parsed_calls: list[ToolCallRequest] = []
        if isinstance(raw_calls, list):
            for idx, item in enumerate(raw_calls):
                if not isinstance(item, Mapping):
                    continue
                fn = item.get("function")
                if not isinstance(fn, Mapping):
                    continue
                name = str(fn.get("name") or "").strip()
                raw_args = fn.get("arguments")
                args_dict: dict[str, Any]
                if isinstance(raw_args, Mapping):
                    args_dict = dict(raw_args)
                elif isinstance(raw_args, str) and raw_args.strip():
                    try:
                        loaded = json.loads(raw_args)
                        args_dict = loaded if isinstance(loaded, dict) else {}
                    except ValueError:
                        args_dict = {}
                else:
                    args_dict = {}
                if name:
                    parsed_calls.append(
                        ToolCallRequest(
                            call_id=str(item.get("id") or f"call_{idx}"),
                            name=name,
                            arguments=args_dict,
                        )
                    )

        usage = body.get("usage")
        tokens_used: int | None = None
        if isinstance(usage, Mapping) and isinstance(usage.get("total_tokens"), int):
            tokens_used = max(0, int(usage["total_tokens"]))

        return LLMResponse(
            content=content,
            tool_calls=parsed_calls,
            tokens_used=tokens_used,
        )
