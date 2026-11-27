from __future__ import annotations

import json
import time
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from app.main import create_app
from app.ml.relevance.inference import RelevanceClassifierService
from tests.conftest import UUID_REGEX

REPO_ROOT = Path(__file__).resolve().parents[3]
AI_SERVICE_ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK_PATH = REPO_ROOT / "notebooks" / "04_relevance_classification.ipynb"
README_PATH = AI_SERVICE_ROOT / "README.md"
MODULE_README_PATH = AI_SERVICE_ROOT / "app" / "ml" / "relevance" / "README.md"


def test_predict_relevance_returns_200_for_relevant_and_out_of_domain(
    make_client: Callable[[Mapping[str, str | None] | None], TestClient],
) -> None:
    client = make_client({"APP_ENV": "test"})
    req_id = "01941234-5678-7abc-8def-0123456789ab"

    t0 = time.perf_counter()
    rel_res = client.post(
        "/api/v1/ml/predict-relevance",
        json={"text": "Apakah ada paket nasi box ayam bakar untuk acara kantor 100 orang?"},
        headers={"X-Request-Id": req_id},
    )
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    assert rel_res.status_code == 200
    assert rel_res.headers["x-request-id"] == req_id
    assert "x-process-time-ms" in rel_res.headers
    assert elapsed_ms < 100.0, f"Expected single request < 100ms, got {elapsed_ms:.2f}ms"

    rel_body = rel_res.json()
    assert rel_body["meta"] == {"requestId": req_id}
    assert rel_body["data"]["label"] == "relevant"
    assert rel_body["data"]["is_relevant"] is True
    assert 0.60 <= rel_body["data"]["confidence"] <= 1.0
    assert rel_body["data"]["model_version"] == "relevance_lr_v1.0"

    ood_res = client.post(
        "/api/v1/ml/predict-relevance",
        json={"text": "Berapa harga saham bank BCA di bursa efek hari ini?"},
    )
    assert ood_res.status_code == 200
    assert UUID_REGEX.match(ood_res.headers["x-request-id"])
    ood_body = ood_res.json()
    assert ood_body["data"]["label"] == "out_of_domain"
    assert ood_body["data"]["is_relevant"] is False
    assert 0.0 <= ood_body["data"]["confidence"] <= 1.0


def test_relevance_metadata_endpoint_returns_200_with_synthetic_disclosure(
    make_client: Callable[[Mapping[str, str | None] | None], TestClient],
) -> None:
    client = make_client({"APP_ENV": "test"})
    res = client.get("/api/v1/ml/relevance/metadata")
    assert res.status_code == 200
    assert UUID_REGEX.match(res.headers["x-request-id"])
    assert "x-process-time-ms" in res.headers

    body = res.json()
    data = body["data"]
    assert data["modelName"] == "relevance_classifier"
    assert data["version"] == "1.0.0"
    assert "LogisticRegression" in data["algorithm"]
    assert data["classes"] == ["relevant", "out_of_domain"]
    assert data["isSynthetic"] is True
    assert 0.88 <= float(data["metrics"]["f1Score"]) <= 1.0
    assert 0.88 <= float(data["metrics"]["accuracy"]) <= 1.0


def test_relevance_endpoints_enforce_internal_token_guard(
    make_client: Callable[[Mapping[str, str | None] | None], TestClient],
) -> None:
    secret = "ai02-internal-secret-token-xyz987"
    client = make_client({"APP_ENV": "test", "INTERNAL_SERVICE_SECRET": secret})

    unauth_pred = client.post(
        "/api/v1/ml/predict-relevance",
        json={"text": "Apakah ada nasi box 50 porsi?"},
    )
    assert unauth_pred.status_code == 401
    assert unauth_pred.headers["content-type"].startswith("application/problem+json")

    unauth_meta = client.get("/api/v1/ml/relevance/metadata")
    assert unauth_meta.status_code == 401

    ok_pred = client.post(
        "/api/v1/ml/predict-relevance",
        json={"text": "Apakah ada nasi box 50 porsi?"},
        headers={"X-Internal-Token": secret},
    )
    assert ok_pred.status_code == 200
    assert ok_pred.json()["data"]["label"] == "relevant"

    ok_meta = client.get(
        "/api/v1/ml/relevance/metadata",
        headers={"X-Internal-Token": secret},
    )
    assert ok_meta.status_code == 200
    assert ok_meta.json()["data"]["isSynthetic"] is True


def test_relevance_endpoints_return_503_problem_details_when_artifacts_missing(
    tmp_path: Path,
) -> None:
    missing_service = RelevanceClassifierService(
        artifacts_dir=tmp_path / "does_not_exist",
        prefer_joblib=False,
    )
    app = create_app(env={"APP_ENV": "test"}, relevance_service=missing_service)
    with TestClient(app) as client:
        pred_res = client.post(
            "/api/v1/ml/predict-relevance",
            json={"text": "Apakah ada nasi box 50 porsi?"},
        )
        assert pred_res.status_code == 503
        assert pred_res.headers["content-type"].startswith("application/problem+json")
        assert pred_res.json()["status"] == 503

        meta_res = client.get("/api/v1/ml/relevance/metadata")
        assert meta_res.status_code == 503
        assert meta_res.headers["content-type"].startswith("application/problem+json")
        assert meta_res.json()["status"] == 503


def test_relevance_api_portable_mode_matches_default_mode_for_ci_compatibility() -> None:
    portable_svc = RelevanceClassifierService(prefer_joblib=False)
    default_svc = RelevanceClassifierService(prefer_joblib=True)

    app_portable = create_app(env={"APP_ENV": "test"}, relevance_service=portable_svc)
    app_default = create_app(env={"APP_ENV": "test"}, relevance_service=default_svc)

    probes = (
        "Berapa harga paket nasi box ayam lengkuas 100 porsi?",
        "Bagaimana cara memperbaiki error komponen React TypeScript?",
    )
    with TestClient(app_portable) as c_port, TestClient(app_default) as c_def:
        for text in probes:
            r_port = c_port.post("/api/v1/ml/predict-relevance", json={"text": text})
            r_def = c_def.post("/api/v1/ml/predict-relevance", json={"text": text})
            assert r_port.status_code == 200 and r_def.status_code == 200
            d_port = r_port.json()["data"]
            d_def = r_def.json()["data"]
            assert d_port["label"] == d_def["label"]
            assert abs(float(d_port["confidence"]) - float(d_def["confidence"])) < 1e-3


def test_openapi_documents_is_synthetic_on_relevance_metadata(
    make_client: Callable[[Mapping[str, str | None] | None], TestClient],
) -> None:
    client = make_client({"APP_ENV": "test", "DOCS_ENABLED": "true"})
    spec = client.get("/openapi.json").json()
    meta_schema = spec["components"]["schemas"]["RelevanceMetadataData"]
    assert "isSynthetic" in meta_schema["properties"]
    example_data = spec["paths"]["/api/v1/ml/relevance/metadata"]["get"]["responses"]["200"][
        "content"
    ]["application/json"]["example"]["data"]
    assert example_data["isSynthetic"] is True


def test_notebook_code_cells_are_valid_python_and_self_contained() -> None:
    nb: dict[str, Any] = json.loads(NOTEBOOK_PATH.read_text(encoding="utf-8"))
    code_sources: list[str] = []
    for idx, cell in enumerate(nb["cells"]):
        if cell.get("cell_type") != "code":
            continue
        source_text = "".join(cell.get("source", []))
        compile(source_text, f"cell_{idx}", "exec")
        code_sources.append(source_text)

    combined = "\n".join(code_sources)
    for required_symbol in (
        "MultinomialNB",
        "LogisticRegression",
        "GridSearchCV",
        "TfidfVectorizer",
        "confusion_matrix",
    ):
        assert required_symbol in combined, f"Notebook missing runnable symbol: {required_symbol}"


def test_readmes_document_measured_ai02_evaluation_metrics() -> None:
    metadata: dict[str, Any] = json.loads(
        (
            AI_SERVICE_ROOT / "app" / "ml" / "relevance" / "artifacts" / "relevance_metadata.json"
        ).read_text(encoding="utf-8")
    )
    f1_050 = f"{float(metadata['metricsByThreshold']['0.50']['f1Score']):.4f}"
    acc_050 = f"{float(metadata['metricsByThreshold']['0.50']['accuracy']):.4f}"
    f1_060 = f"{float(metadata['metricsByThreshold']['0.60']['f1Score']):.4f}"

    root_readme = README_PATH.read_text(encoding="utf-8")
    for token in (
        "AI-02",
        "MultinomialNB",
        "LogisticRegression",
        f1_050,
        f1_060,
        "is_synthetic",
        "04_relevance_classification.ipynb",
    ):
        assert token in root_readme, f"apps/ai-service/README.md missing: {token}"

    mod_readme = MODULE_README_PATH.read_text(encoding="utf-8")
    assert f1_050 in mod_readme and acc_050 in mod_readme and f1_060 in mod_readme
