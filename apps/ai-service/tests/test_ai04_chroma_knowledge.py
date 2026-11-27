from __future__ import annotations

from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.chroma.chunker import load_and_chunk_knowledge_dir
from app.chroma.client import (
    ChromaCollectionNotFoundError,
    ChromaHttpVectorStoreAdapter,
    ChromaKnowledgeService,
    ChromaUnavailableError,
    InMemoryVectorStoreAdapter,
)
from app.chroma.ingest import DEFAULT_EVAL_SAMPLES, evaluate_knowledge_base_hit_at_3
from app.main import create_app
from app.rag.service import evaluate_retrieval_hit_at_3

REPO_ROOT = Path(__file__).resolve().parents[3]
KNOWLEDGE_DIR = REPO_ROOT / "data" / "knowledge"
REQUIRED_DOMAIN_FILES: tuple[str, ...] = (
    "menus.md",
    "faq.md",
    "sop.md",
    "payment_policy.md",
)


def _build_in_memory_service() -> ChromaKnowledgeService:
    return ChromaKnowledgeService(
        adapter=InMemoryVectorStoreAdapter(collection_name="catering_knowledge"),
        default_knowledge_dir=KNOWLEDGE_DIR,
    )


def test_knowledge_base_has_all_four_curated_domains_and_four_pic_metadata_fields() -> None:
    for filename in REQUIRED_DOMAIN_FILES:
        file_path = KNOWLEDGE_DIR / filename
        assert file_path.is_file(), f"Missing required knowledge file: {filename}"

    chunks = load_and_chunk_knowledge_dir(KNOWLEDGE_DIR)
    assert len(chunks) >= 12, f"Expected >= 12 curated chunks across 4 domains, got {len(chunks)}"

    sources_seen = {chunk.metadata.source for chunk in chunks}
    assert set(REQUIRED_DOMAIN_FILES).issubset(sources_seen)

    for chunk in chunks:
        assert chunk.chunk_id.strip() != ""
        assert 80 <= len(chunk.content) <= 650
        meta = chunk.metadata
        assert meta.doc_id.strip() != ""
        assert meta.source in REQUIRED_DOMAIN_FILES
        assert meta.category in {"menu", "faq", "sop", "payment"}
        assert meta.version.strip() != ""
        assert meta.validated_at.strip() != ""
        assert meta.validation_status == "verified"
        assert meta.is_verified is True


def test_ingest_is_strictly_idempotent_across_repeated_runs() -> None:
    service = _build_in_memory_service()

    first = service.ingest_directory(KNOWLEDGE_DIR)
    second = service.ingest_directory(KNOWLEDGE_DIR)

    assert first.files_processed >= 4
    assert first.chunks_upserted >= 12
    assert first.total_chunks == first.chunks_upserted
    assert second.files_processed == first.files_processed
    assert second.chunks_upserted == first.chunks_upserted
    assert second.total_chunks == first.total_chunks
    assert second.idempotent is True


def test_unverified_draft_documents_are_excluded_from_production_queries(
    tmp_path: Path,
) -> None:
    verified_doc = tmp_path / "faq.md"
    verified_doc.write_text(
        (
            "---\n"
            "doc_id: faq_verified_01\n"
            "source: faq.md\n"
            "category: faq\n"
            'version: "1.0"\n'
            'validated_at: "2026-11-27"\n'
            "validation_status: verified\n"
            "is_verified: true\n"
            "---\n\n"
            "## Minimal Order Nasi Box\n"
            "Pemesanan minimal nasi box Catering Si Kembar adalah 20 box untuk area Bandung.\n"
        ),
        encoding="utf-8",
    )
    draft_doc = tmp_path / "draft_promo.md"
    draft_doc.write_text(
        (
            "---\n"
            "doc_id: promo_draft_01\n"
            "source: draft_promo.md\n"
            "category: faq\n"
            'version: "0.1"\n'
            'validated_at: "2026-11-27"\n'
            "validation_status: draft\n"
            "is_verified: false\n"
            "---\n\n"
            "## Promo Rahasia Belum Disetujui\n"
            "Diskon khusus 90 persen untuk promo simulasi internal yang belum divalidasi PIC.\n"
        ),
        encoding="utf-8",
    )

    service = _build_in_memory_service()
    service.ingest_directory(tmp_path)

    hits = service.query("promo rahasia diskon 90 persen simulasi internal", top_k=5)
    assert all(hit.metadata.is_verified for hit in hits)
    assert all(hit.metadata.validation_status == "verified" for hit in hits)
    assert all(hit.metadata.source != "draft_promo.md" for hit in hits)


@pytest.mark.asyncio
async def test_hit_at_3_evaluation_and_no_source_threshold_rejection() -> None:
    service = _build_in_memory_service()
    service.ingest_directory(KNOWLEDGE_DIR)

    eval_result = evaluate_knowledge_base_hit_at_3(service)
    assert eval_result.total_positive_queries >= 12
    assert eval_result.hit_rate_at_3 >= 0.85
    assert eval_result.metadata_complete_ratio == 1.0
    assert eval_result.total_negative_queries >= 4
    assert eval_result.negative_rejection_rate == 1.0

    rag_report = await evaluate_retrieval_hit_at_3(service, DEFAULT_EVAL_SAMPLES)
    assert rag_report.total_queries >= 12
    assert rag_report.hit_rate_at_3 >= 0.85
    assert rag_report.metadata_complete_ratio == 1.0


def test_chroma_http_adapter_parses_local_and_vps_urls() -> None:
    local_adapter = ChromaHttpVectorStoreAdapter(
        chroma_url="http://127.0.0.1:8000",
        collection_name="catering_knowledge",
    )
    vps_adapter = ChromaHttpVectorStoreAdapter(
        chroma_url="http://chroma:8000",
        collection_name="catering_knowledge",
    )
    https_adapter = ChromaHttpVectorStoreAdapter(
        chroma_url="https://chroma.internal.example",
        collection_name="catering_knowledge",
    )

    assert (local_adapter.host, local_adapter.port, local_adapter.ssl_enabled) == (
        "127.0.0.1",
        8000,
        False,
    )
    assert (vps_adapter.host, vps_adapter.port, vps_adapter.ssl_enabled) == (
        "chroma",
        8000,
        False,
    )
    assert (https_adapter.host, https_adapter.port, https_adapter.ssl_enabled) == (
        "chroma.internal.example",
        443,
        True,
    )


def test_fastapi_chroma_ingest_query_and_problem_details_contracts() -> None:
    service = _build_in_memory_service()
    secret = "chroma-internal-secret-test-999"
    app = create_app(
        env={"APP_ENV": "test", "DOCS_ENABLED": "true", "INTERNAL_SERVICE_SECRET": secret},
        chroma_service=service,
    )
    client = TestClient(app)

    unauth = client.post("/api/v1/chroma/query", json={"query": "minimal order nasi box"})
    assert unauth.status_code == 401
    assert unauth.headers["content-type"].startswith("application/problem+json")

    headers = {"X-Internal-Token": secret}

    # Before ingest: collection does not exist -> 404 RFC 9457
    not_ready = client.post(
        "/api/v1/chroma/query",
        json={"query": "Berapa minimal order nasi box?"},
        headers=headers,
    )
    assert not_ready.status_code == 404
    assert not_ready.headers["content-type"].startswith("application/problem+json")

    # Ingest twice -> idempotent 200 OK
    ingest_1 = client.post("/api/v1/chroma/ingest", json={}, headers=headers)
    assert ingest_1.status_code == 200
    data_1 = ingest_1.json()["data"]
    assert data_1["files_processed"] >= 4
    assert data_1["total_chunks"] == data_1["chunks_upserted"]

    ingest_2 = client.post("/api/v1/chroma/ingest", json={}, headers=headers)
    assert ingest_2.status_code == 200
    assert ingest_2.json()["data"]["total_chunks"] == data_1["total_chunks"]
    assert ingest_2.json()["data"]["idempotent"] is True

    # Query with matching domain -> 200 OK with 4 PIC metadata fields
    query_ok = client.post(
        "/api/v1/chroma/query",
        json={"query": "Berapa ketentuan minimal DP pembayaran katering?", "top_k": 3},
        headers=headers,
    )
    assert query_ok.status_code == 200
    q_data = query_ok.json()["data"]
    assert q_data["total_hits"] >= 1
    first_hit = q_data["results"][0]
    assert first_hit["metadata"]["source"] == "payment_policy.md"
    assert first_hit["metadata"]["is_verified"] is True
    assert first_hit["metadata"]["validation_status"] == "verified"
    assert first_hit["metadata"]["version"]
    assert first_hit["metadata"]["validated_at"]

    # Query without source in KB -> 200 OK with empty results
    no_source = client.post(
        "/api/v1/chroma/query",
        json={"query": "Bagaimana cara konfigurasi kernel Linux Ubuntu di server AWS?"},
        headers=headers,
    )
    assert no_source.status_code == 200
    assert no_source.json()["data"]["results"] == []
    assert no_source.json()["data"]["total_hits"] == 0

    # Validation 422 on empty query & path traversal on ingest
    bad_query = client.post("/api/v1/chroma/query", json={"query": "   "}, headers=headers)
    assert bad_query.status_code == 422
    assert bad_query.headers["content-type"].startswith("application/problem+json")

    bad_dir = client.post(
        "/api/v1/chroma/ingest",
        json={"knowledge_dir": "../../etc"},
        headers=headers,
    )
    assert bad_dir.status_code == 422
    assert bad_dir.headers["content-type"].startswith("application/problem+json")

    # OpenAPI 3.1.0 documents both endpoints
    spec = client.get("/openapi.json").json()
    assert spec["openapi"] == "3.1.0"
    assert "/api/v1/chroma/query" in spec["paths"]
    assert "/api/v1/chroma/ingest" in spec["paths"]
    assert "404" in spec["paths"]["/api/v1/chroma/query"]["post"]["responses"]
    assert "503" in spec["paths"]["/api/v1/chroma/query"]["post"]["responses"]


def test_fastapi_chroma_returns_503_when_vector_store_unavailable(
    make_client: Callable[[Mapping[str, str | None] | None], TestClient],
) -> None:
    class _BrokenAdapter:
        def collection_exists(self) -> bool:
            raise ChromaUnavailableError("ChromaDB server unreachable.")

        def count(self) -> int:
            raise ChromaUnavailableError("ChromaDB server unreachable.")

        def upsert_chunks(self, chunks: Any) -> int:
            raise ChromaUnavailableError("ChromaDB server unreachable.")

        def query(
            self,
            query_text: str,
            *,
            top_k: int = 3,
            category: str | None = None,
            max_distance: float = 0.65,
        ) -> Any:
            raise ChromaUnavailableError("ChromaDB server unreachable.")

    app = create_app(
        env={"APP_ENV": "test"},
        chroma_service=ChromaKnowledgeService(
            adapter=_BrokenAdapter(),  # type: ignore[arg-type]
            default_knowledge_dir=KNOWLEDGE_DIR,
        ),
    )
    client = TestClient(app)

    res_q = client.post("/api/v1/chroma/query", json={"query": "menu nasi box"})
    assert res_q.status_code == 503
    assert res_q.headers["content-type"].startswith("application/problem+json")

    res_i = client.post("/api/v1/chroma/ingest", json={})
    assert res_i.status_code == 503
    assert res_i.headers["content-type"].startswith("application/problem+json")


def test_in_memory_adapter_raises_not_found_before_ingest() -> None:
    adapter = InMemoryVectorStoreAdapter(collection_name="empty_kb")
    with pytest.raises(ChromaCollectionNotFoundError):
        adapter.query("menu ayam bakar", top_k=3)
