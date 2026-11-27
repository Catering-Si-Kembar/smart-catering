from __future__ import annotations

import json
import time
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.conftest import UUID_REGEX

AI_SERVICE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
METADATA_PATH = (
    AI_SERVICE_ROOT / "app" / "ml" / "sentiment" / "artifacts" / "sentiment_metadata.json"
)
NOTEBOOK_PATH = REPO_ROOT / "notebooks" / "05_sentiment_analysis.ipynb"
SERVICE_README_PATH = AI_SERVICE_ROOT / "README.md"
MODULE_README_PATH = AI_SERVICE_ROOT / "app" / "ml" / "sentiment" / "README.md"


def test_predict_sentiment_positive_negative_and_mixed_return_200_envelope(
    make_client: Callable[[Mapping[str, str | None] | None], TestClient],
) -> None:
    client = make_client({"APP_ENV": "test"})
    incoming_id = "01941234-5678-7abc-8def-0123456789cd"

    pos_text = "Nasi liwetnya wangi pulen, ayam bakarnya meresap dan datang tepat waktu!"
    t0 = time.perf_counter()
    pos_res = client.post(
        "/api/v1/ml/predict-sentiment",
        json={"text": pos_text},
        headers={"X-Request-Id": incoming_id},
    )
    elapsed_ms = (time.perf_counter() - t0) * 1000.0

    assert pos_res.status_code == 200
    assert pos_res.headers["x-request-id"] == incoming_id
    assert "x-process-time-ms" in pos_res.headers
    pos_body = pos_res.json()
    assert pos_body["meta"]["requestId"] == incoming_id
    pos_data = pos_body["data"]
    assert pos_data["text"] == pos_text
    assert pos_data["sentiment"] == "positive"
    assert pos_data["needsAttention"] is False
    assert 0.5 <= float(pos_data["score"]) <= 1.0
    probs = pos_data["probabilities"]
    assert abs(float(probs["positive"]) + float(probs["negative"]) - 1.0) <= 0.005
    assert elapsed_ms < 250.0

    neg_text = "Pengantaran terlambat satu jam, kemasan dus penyok, dan sayur agak basi."
    neg_res = client.post("/api/v1/ml/predict-sentiment", json={"text": neg_text})
    assert neg_res.status_code == 200
    neg_data = neg_res.json()["data"]
    assert neg_data["sentiment"] == "negative"
    assert neg_data["needsAttention"] == (float(neg_data["score"]) >= 0.75)

    mixed_text = "Makanannya enak dan bumbunya pas, tapi pengantarannya terlambat 40 menit."
    mixed_res = client.post("/api/v1/ml/predict-sentiment", json={"text": mixed_text})
    assert mixed_res.status_code == 200
    mixed_data = mixed_res.json()["data"]
    assert mixed_data["sentiment"] in {"positive", "negative"}
    assert isinstance(mixed_data["needsAttention"], bool)


@pytest.mark.parametrize("bad_text", ["", "   ", "a", "ab", "!!!", "...", "-- --", "a! b?"])
def test_predict_sentiment_rejects_empty_or_short_text_with_422_rfc9457(
    make_client: Callable[[Mapping[str, str | None] | None], TestClient],
    bad_text: str,
) -> None:
    client = make_client({"APP_ENV": "test"})
    res = client.post("/api/v1/ml/predict-sentiment", json={"text": bad_text})

    assert res.status_code == 422
    assert res.headers["content-type"].startswith("application/problem+json")
    assert UUID_REGEX.match(res.headers["x-request-id"])
    problem = res.json()
    assert problem["status"] == 422
    assert problem["instance"] == "/api/v1/ml/predict-sentiment"
    assert any(err["path"] == "text" for err in problem["errors"])

    batch_res = client.post(
        "/api/v1/ml/predict-sentiment/batch",
        json={"items": [{"id": "rev_bad", "text": bad_text}]},
    )
    assert batch_res.status_code == 422
    assert batch_res.headers["content-type"].startswith("application/problem+json")
    batch_problem = batch_res.json()
    assert batch_problem["status"] == 422
    assert any(err["path"] == "items.0.text" for err in batch_problem["errors"])


def test_predict_sentiment_batch_returns_200_ordered_and_rejects_invalid_batch(
    make_client: Callable[[Mapping[str, str | None] | None], TestClient],
) -> None:
    client = make_client({"APP_ENV": "test"})

    payload = {
        "items": [
            {"id": "rev_01", "text": "Makanan lezat, porsi pas, dan kemasan sangat rapi."},
            {
                "id": "rev_02",
                "text": "Pengantaran terlambat lama, lauk asin, dan dus penyok mengecewakan.",
            },
            {
                "id": "rev_03",
                "text": "Ayam bakarnya mantap sekali, cuma sayang porsi nasinya sedikit.",
            },
        ]
    }
    res = client.post("/api/v1/ml/predict-sentiment/batch", json=payload)
    assert res.status_code == 200
    body = res.json()
    assert UUID_REGEX.match(body["meta"]["requestId"])
    items = body["data"]
    assert [item["id"] for item in items] == ["rev_01", "rev_02", "rev_03"]
    assert items[0]["sentiment"] == "positive" and items[0]["needsAttention"] is False
    assert items[1]["sentiment"] == "negative"
    assert items[1]["needsAttention"] == (float(items[1]["score"]) >= 0.75)
    assert items[2]["sentiment"] in {"positive", "negative"}

    empty_res = client.post("/api/v1/ml/predict-sentiment/batch", json={"items": []})
    assert empty_res.status_code == 422
    assert empty_res.headers["content-type"].startswith("application/problem+json")

    too_many = {"items": [{"id": f"r_{i}", "text": "Makanan enak sekali."} for i in range(101)]}
    overflow_res = client.post("/api/v1/ml/predict-sentiment/batch", json=too_many)
    assert overflow_res.status_code == 422
    assert overflow_res.headers["content-type"].startswith("application/problem+json")


def test_predict_sentiment_endpoints_enforce_internal_token_guard(
    make_client: Callable[[Mapping[str, str | None] | None], TestClient],
) -> None:
    secret = "sentiment-internal-secret-value-999"
    client = make_client({"APP_ENV": "test", "INTERNAL_SERVICE_SECRET": secret})

    unauth_single = client.post(
        "/api/v1/ml/predict-sentiment",
        json={"text": "Nasi liwet enak dan tepat waktu."},
    )
    assert unauth_single.status_code == 401
    assert secret not in unauth_single.text

    unauth_batch = client.post(
        "/api/v1/ml/predict-sentiment/batch",
        json={"items": [{"id": "r1", "text": "Nasi liwet enak dan tepat waktu."}]},
    )
    assert unauth_batch.status_code == 401
    assert secret not in unauth_batch.text

    ok_single = client.post(
        "/api/v1/ml/predict-sentiment",
        json={"text": "Nasi liwet enak dan tepat waktu."},
        headers={"X-Internal-Token": secret},
    )
    assert ok_single.status_code == 200
    assert ok_single.json()["data"]["sentiment"] == "positive"

    ok_batch = client.post(
        "/api/v1/ml/predict-sentiment/batch",
        json={"items": [{"id": "r1", "text": "Nasi liwet enak dan tepat waktu."}]},
        headers={"X-Internal-Token": secret},
    )
    assert ok_batch.status_code == 200
    assert ok_batch.json()["data"][0]["sentiment"] == "positive"


def test_predict_sentiment_returns_honest_503_when_artifacts_missing(tmp_path: Path) -> None:
    from app.main import create_app
    from app.ml.sentiment.inference import SentimentClassifierService

    broken_service = SentimentClassifierService(
        artifacts_dir=tmp_path / "missing_sentiment_artifacts",
        prefer_joblib=False,
    )
    app = create_app(env={"APP_ENV": "test"}, sentiment_service=broken_service)
    client = TestClient(app)

    res_single = client.post(
        "/api/v1/ml/predict-sentiment",
        json={"text": "Nasi liwetnya enak dan pengantaran tepat waktu."},
    )
    assert res_single.status_code == 503
    assert res_single.headers["content-type"].startswith("application/problem+json")
    assert res_single.json()["status"] == 503

    res_batch = client.post(
        "/api/v1/ml/predict-sentiment/batch",
        json={"items": [{"id": "r1", "text": "Nasi liwetnya enak dan tepat waktu."}]},
    )
    assert res_batch.status_code == 503
    assert res_batch.headers["content-type"].startswith("application/problem+json")
    assert res_batch.json()["status"] == 503


def test_openapi_examples_and_docs_document_ai03_evaluation_and_needs_attention(
    make_client: Callable[[Mapping[str, str | None] | None], TestClient],
) -> None:
    client = make_client({"APP_ENV": "test", "DOCS_ENABLED": "true"})
    spec_res = client.get("/openapi.json")
    assert spec_res.status_code == 200
    doc: dict[str, Any] = spec_res.json()

    single_ex = doc["paths"]["/api/v1/ml/predict-sentiment"]["post"]["responses"]["200"]["content"][
        "application/json"
    ]["example"]["data"]
    assert "needsAttention" in single_ex

    batch_ex = doc["paths"]["/api/v1/ml/predict-sentiment/batch"]["post"]["responses"]["200"][
        "content"
    ]["application/json"]["example"]["data"]
    assert isinstance(batch_ex, list) and "needsAttention" in batch_ex[0]

    metadata: dict[str, Any] = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
    actual_latency = f"{float(metadata['avgInferenceLatencyMs']):.3f}"

    module_readme = MODULE_README_PATH.read_text(encoding="utf-8")
    assert actual_latency in module_readme, (
        f"Expected actual latency {actual_latency} ms in app/ml/sentiment/README.md"
    )

    service_readme = SERVICE_README_PATH.read_text(encoding="utf-8").lower()
    for term in (
        "ai-03",
        "multinomialnb",
        "logisticregression",
        "is_synthetic",
        "05_sentiment_analysis.ipynb",
        "mixed",
        "needsattention",
    ):
        assert term in service_readme, f"Missing AI-03 evaluation term in README.md: {term}"

    nb_text = NOTEBOOK_PATH.read_text(encoding="utf-8")
    assert "LogisticRegression menunjukkan akurasi dan F1 yang unggul." not in nb_text, (
        "Notebook cell 3 must transparently state MultinomialNB had higher baseline F1 while "
        "LogisticRegression was selected for probability calibration (needsAttention >= 0.75)."
    )

    nb_json: dict[str, Any] = json.loads(nb_text)
    code_cells = [c for c in nb_json["cells"] if c.get("cell_type") == "code"]
    mixed_cell_output = "".join(
        "".join(out.get("text", [])) for out in code_cells[4].get("outputs", [])
    )
    for example in metadata["errorAnalysis"]["mixedSentimentExamples"]:
        expected_pred = f"Prediksi: {example['predicted']}"
        expected_att = f"needsAttention: {example['needsAttention']}"
        assert expected_pred in mixed_cell_output
        assert expected_att in mixed_cell_output
