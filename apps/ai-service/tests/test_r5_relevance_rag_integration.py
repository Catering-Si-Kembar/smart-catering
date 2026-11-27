from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.ml.relevance.inference import RelevanceClassifierService
from app.rag.guardrails import DomainRelevanceClassifier
from app.rag.prompts import OUT_OF_DOMAIN_REPLY
from app.rag.schemas import LLMResponse
from app.rag.service import AgenticRagService
from tests.test_agentic_rag import (
    TEN_OUT_OF_DOMAIN_QUESTIONS,
    FakeKnowledgeBase,
    FakeOperationalBackend,
    ScriptedLLMClient,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
ARTIFACTS_DIR = Path(__file__).resolve().parents[1] / "app" / "ml" / "relevance" / "artifacts"
METADATA_PATH = ARTIFACTS_DIR / "relevance_metadata.json"
NOTEBOOK_PATH = REPO_ROOT / "notebooks" / "04_relevance_classification.ipynb"

STAFF_OPERATIONAL_PROBES: tuple[str, ...] = (
    "Bagaimana jadwal produksi dan rincian pesanan ORD-202612-0001?",
    "Cek status DP pesanan ORD-202612-0001 dan aturan minimal DP katering?",
    "Berapa nominal invoice dan DP pesanan ORD-202612-0001?",
    "Cek status pesanan ORD-999999-9999",
    "Cek daftar pesanan nasi box terbaru",
    "Bagaimana jadwal masak dapur untuk pesanan 150 porsi besok?",
    "Apakah invoice INV-202612-0005 sudah lunas atau masih menunggu pelunasan?",
    "Tolong tampilkan jadwal produksi katering tanggal 15 Desember status CONFIRMED.",
)


@pytest.mark.anyio
@pytest.mark.parametrize("prefer_joblib", [True, False])
async def test_domain_relevance_classifier_uses_ai02_service_in_both_artifact_modes(
    prefer_joblib: bool,
) -> None:
    service = RelevanceClassifierService(
        artifacts_dir=ARTIFACTS_DIR,
        prefer_joblib=prefer_joblib,
    )
    classifier = DomainRelevanceClassifier(relevance_service=service)

    for query in STAFF_OPERATIONAL_PROBES:
        decision = await classifier.classify(query)
        assert decision.model_version == "relevance_lr_v1.0", (
            f"Expected real AI-02 model_version, got {decision.model_version!r}"
        )
        assert decision.is_relevant is True, (
            f"Staff operational query misclassified as OOD (prefer_joblib={prefer_joblib}): "
            f"{query!r} -> {decision}"
        )
        assert decision.label == "relevant"

    for ood_query in TEN_OUT_OF_DOMAIN_QUESTIONS:
        decision = await classifier.classify(ood_query)
        assert decision.model_version == "relevance_lr_v1.0", (
            f"Expected real AI-02 model_version, got {decision.model_version!r}"
        )
        assert decision.is_relevant is False, (
            f"OOD query leaked as relevant (prefer_joblib={prefer_joblib}): "
            f"{ood_query!r} -> {decision}"
        )
        assert decision.label == "out_of_domain"


@pytest.mark.anyio
async def test_domain_relevance_classifier_default_uses_ai02_and_falls_back_only_when_missing(
    tmp_path: Path,
) -> None:
    default_classifier = DomainRelevanceClassifier()
    decision = await default_classifier.classify(
        "Bagaimana jadwal produksi dan rincian pesanan ORD-202612-0001?"
    )
    assert decision.model_version == "relevance_lr_v1.0"
    assert decision.is_relevant is True

    empty_decision = await default_classifier.classify("   ")
    assert empty_decision.is_relevant is False
    assert empty_decision.label == "out_of_domain"

    missing_service = RelevanceClassifierService(
        artifacts_dir=tmp_path / "missing_artifacts",
        prefer_joblib=False,
    )
    fallback_classifier = DomainRelevanceClassifier(relevance_service=missing_service)
    fb_rel = await fallback_classifier.classify(
        "Berapa harga paket nasi box 50 porsi untuk rapat kantor?"
    )
    assert fb_rel.model_version == "fallback_rule_relevance_v0"
    assert fb_rel.is_relevant is True

    fb_ood = await fallback_classifier.classify(
        "Apakah harga saham dan bitcoin sedang naik minggu ini?"
    )
    assert fb_ood.model_version == "fallback_rule_relevance_v0"
    assert fb_ood.is_relevant is False


def test_create_app_shares_singleton_relevance_service_with_rag_service() -> None:
    custom_service = RelevanceClassifierService(
        artifacts_dir=ARTIFACTS_DIR,
        prefer_joblib=False,
    )
    app = create_app(env={"APP_ENV": "test"}, relevance_service=custom_service)
    assert app.state.relevance_service is custom_service
    rag_service: AgenticRagService = app.state.rag_service
    classifier = rag_service._graph._relevance_classifier
    assert isinstance(classifier, DomainRelevanceClassifier)
    assert classifier._relevance_service is custom_service


@pytest.mark.parametrize("prefer_joblib", [True, False])
def test_rag_chat_endpoint_rejects_all_ten_ood_questions_via_ai02_with_zero_llm_calls(
    prefer_joblib: bool,
) -> None:
    rel_service = RelevanceClassifierService(
        artifacts_dir=ARTIFACTS_DIR,
        prefer_joblib=prefer_joblib,
    )
    llm = ScriptedLLMClient([LLMResponse(content="MUST NEVER BE CALLED")])
    rag_service = AgenticRagService(
        relevance_classifier=DomainRelevanceClassifier(relevance_service=rel_service),
        knowledge_base=FakeKnowledgeBase(),
        operational_backend=FakeOperationalBackend(),
        llm_client=llm,
        timeout_seconds=10.0,
    )
    app = create_app(
        env={"APP_ENV": "test"},
        relevance_service=rel_service,
        rag_service=rag_service,
    )
    with TestClient(app) as client:
        for question in TEN_OUT_OF_DOMAIN_QUESTIONS:
            res = client.post(
                "/api/v1/rag/chat",
                json={
                    "message": question,
                    "conversation_id": "ses_r5_ood",
                    "user_role": "STAFF",
                },
            )
            assert res.status_code == 200
            data = res.json()["data"]
            assert data["is_relevant"] is False, f"OOD leaked on RAG chat: {question!r}"
            assert data["reply"] == OUT_OF_DOMAIN_REPLY
            assert data["tools_called"] == []
            assert data["sources"] == []

    assert len(llm.invocations) == 0


def test_r5_metadata_and_notebook_remain_consistent_after_retrain() -> None:
    metadata: dict[str, Any] = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
    assert metadata["isSynthetic"] is True
    assert float(metadata["confidenceThreshold"]) == pytest.approx(0.60, abs=1e-6)
    assert float(metadata["metrics"]["f1Score"]) >= 0.88
    assert float(metadata["metrics"]["accuracy"]) >= 0.88
    assert float(metadata["metricsByThreshold"]["0.50"]["f1Score"]) >= 0.88
    assert float(metadata["metricsByThreshold"]["0.60"]["f1Score"]) >= 0.88
    assert int(metadata["datasetStats"]["total"]) >= 470

    nb_text = NOTEBOOK_PATH.read_text(encoding="utf-8")
    assert "Verifikasi label is_synthetic: True" in nb_text
    assert "Pipeline([" in nb_text
