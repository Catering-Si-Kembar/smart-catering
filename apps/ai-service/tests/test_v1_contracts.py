from __future__ import annotations

from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from tests.conftest import UUID_REGEX

POST_ENDPOINTS: tuple[str, ...] = (
    "/api/v1/ml/predict-relevance",
    "/api/v1/ml/predict-sentiment",
    "/api/v1/ml/predict-sentiment/batch",
    "/api/v1/rag/chat",
    "/api/v1/insight/generate",
)

POST_STUB_ENDPOINTS: tuple[str, ...] = (
    "/api/v1/ml/predict-relevance",
    "/api/v1/ml/predict-sentiment",
    "/api/v1/ml/predict-sentiment/batch",
    "/api/v1/rag/chat",
)

GET_STUB_ENDPOINTS: tuple[str, ...] = ("/api/v1/ml/relevance/metadata",)

VALID_POST_PAYLOADS: dict[str, dict[str, Any]] = {
    "/api/v1/ml/predict-relevance": {
        "text": "Apakah ada paket nasi box ayam bakar untuk acara kantor 100 orang?",
    },
    "/api/v1/ml/predict-sentiment": {
        "text": "Nasi liwetnya wangi pulen, ayam bakarnya enak dan tepat waktu.",
    },
    "/api/v1/ml/predict-sentiment/batch": {
        "items": [
            {"id": "rev_01", "text": "Makanan lezat dan porsi sangat memuaskan."},
            {"id": "rev_02", "text": "Pengantaran terlambat 30 menit dari jadwal."},
        ]
    },
    "/api/v1/rag/chat": {
        "message": "Apakah Catering Si Kembar menerima pesanan 50 nasi box untuk lusa?",
        "conversation_id": "conv_staf_01",
        "user_role": "STAFF",
    },
    "/api/v1/insight/generate": {
        "period": "November 2026",
        "metrics": {
            "total_orders": 38,
            "total_revenue": 24500000,
            "completed_orders": 34,
            "unpaid_invoices": 4,
            "top_menus": [
                {"name": "Nasi Box Ayam Lengkuas", "portions": 620},
                {"name": "Nasi Box Rendang Daging", "portions": 310},
            ],
            "forecast_next_week_portions": 450,
        },
    },
}


def _resolve_response_spec(document: dict[str, Any], raw_spec: dict[str, Any]) -> dict[str, Any]:
    if "$ref" in raw_spec:
        ref_name = str(raw_spec["$ref"]).rsplit("/", 1)[-1]
        resolved: dict[str, Any] = document["components"]["responses"][ref_name]
        return resolved
    return raw_spec


def test_ai_service_readme_documents_problem_and_architecture() -> None:
    readme_path = Path(__file__).resolve().parents[1] / "README.md"
    assert readme_path.is_file(), "apps/ai-service/README.md must exist for AI-01"
    content = readme_path.read_text(encoding="utf-8").lower()
    for keyword in ("catering si kembar", "fastapi", "/api/v1/health", "openapi", "rfc 9457"):
        assert keyword in content, f"Missing expected section/term in README.md: {keyword}"


def test_api_v1_health_supports_get_head_and_rejects_post(
    make_client: Callable[[Mapping[str, str | None] | None], TestClient],
) -> None:
    client = make_client({"APP_ENV": "test"})
    incoming_id = "01941234-5678-7abc-8def-0123456789ab"

    get_res = client.get("/api/v1/health", headers={"X-Request-Id": incoming_id})
    assert get_res.status_code == 200
    assert get_res.headers["x-request-id"] == incoming_id
    assert get_res.json() == {
        "data": {"status": "ok", "service": "ai-service"},
        "meta": {"requestId": incoming_id},
    }

    head_res = client.head("/api/v1/health", headers={"X-Request-Id": incoming_id})
    assert head_res.status_code == 200
    assert head_res.content == b""
    assert head_res.headers["x-request-id"] == incoming_id

    post_res = client.post("/api/v1/health")
    assert post_res.status_code == 405
    assert post_res.headers["content-type"].startswith("application/problem+json")


def test_openapi_documents_official_api_v1_ai_endpoints_and_protocol_responses(
    make_client: Callable[[Mapping[str, str | None] | None], TestClient],
) -> None:
    client = make_client({"APP_ENV": "test", "DOCS_ENABLED": "true"})
    spec_res = client.get("/openapi.json")
    assert spec_res.status_code == 200
    document = spec_res.json()
    assert document["openapi"] == "3.1.0"

    tag_names = {tag["name"] for tag in document.get("tags", [])}
    assert {"System", "Relevance", "Sentiment", "Insights", "RAG"}.issubset(tag_names)

    security_schemes = document["components"]["securitySchemes"]
    assert "DocsBasicAuth" in security_schemes
    assert "InternalTokenAuth" in security_schemes
    assert security_schemes["InternalTokenAuth"]["type"] == "apiKey"
    assert security_schemes["InternalTokenAuth"]["in"] == "header"
    assert security_schemes["InternalTokenAuth"]["name"] == "X-Internal-Token"

    assert "/health" in document["paths"]
    assert "/api/v1/health" in document["paths"]
    assert document["paths"]["/api/v1/health"]["get"]["security"] == []

    schemas = document["components"]["schemas"]
    for expected_schema in (
        "HealthData",
        "PaginationMeta",
        "ApiMeta",
        "HealthResponse",
        "ValidationIssue",
        "ProblemDetails",
        "RelevancePredictRequest",
        "RelevancePredictData",
        "RelevancePredictResponse",
        "RelevanceModelMetrics",
        "RelevanceMetadataData",
        "RelevanceMetadataResponse",
        "SentimentPredictRequest",
        "SentimentProbabilities",
        "SentimentPredictData",
        "SentimentPredictResponse",
        "SentimentBatchItemRequest",
        "SentimentBatchRequest",
        "SentimentBatchItemResult",
        "SentimentBatchResponse",
        "RagChatRequest",
        "RagSourceItem",
        "RagChatData",
        "RagChatResponse",
        "InsightTopMenu",
        "InsightMetricsInput",
        "InsightGenerateRequest",
        "InsightGenerateData",
        "InsightGenerateResponse",
    ):
        assert expected_schema in schemas, f"Missing OpenAPI schema: {expected_schema}"

    for resp_name in ("ServiceUnavailableProblem", "GatewayTimeoutProblem"):
        assert resp_name in document["components"]["responses"]
        assert (
            "application/problem+json" in document["components"]["responses"][resp_name]["content"]
        )

    for path in POST_ENDPOINTS:
        assert path in document["paths"], f"Missing OpenAPI path: {path}"
        operation = document["paths"][path]["post"]
        param_refs = [p.get("$ref") for p in operation.get("parameters", []) if isinstance(p, dict)]
        assert "#/components/parameters/RequestIdHeader" in param_refs
        assert "requestBody" in operation

        responses = operation["responses"]
        assert "200" in responses
        ok_resp = responses["200"]
        assert "X-Request-Id" in ok_resp.get("headers", {})
        ok_json = ok_resp["content"]["application/json"]
        assert "example" in ok_json
        assert "data" in ok_json["example"]
        assert "meta" in ok_json["example"]

        for code in ("400", "401", "405", "422", "500", "503"):
            assert code in responses, f"Missing response {code} on {path}"
            resolved = _resolve_response_spec(document, responses[code])
            assert "application/problem+json" in resolved["content"]

    insight_op = document["paths"]["/api/v1/insight/generate"]["post"]
    insight_param_refs = [
        p.get("$ref") for p in insight_op.get("parameters", []) if isinstance(p, dict)
    ]
    assert "#/components/parameters/ActorRoleHeader" in insight_param_refs
    assert "403" in insight_op["responses"]
    assert "504" in insight_op["responses"]

    meta_op = document["paths"]["/api/v1/ml/relevance/metadata"]["get"]
    meta_param_refs = [p.get("$ref") for p in meta_op.get("parameters", []) if isinstance(p, dict)]
    assert "#/components/parameters/RequestIdHeader" in meta_param_refs
    assert "200" in meta_op["responses"]
    assert "503" in meta_op["responses"]


@pytest.mark.parametrize("path", POST_STUB_ENDPOINTS)
def test_api_v1_valid_post_requests_return_honest_503_problem_details(
    make_client: Callable[[Mapping[str, str | None] | None], TestClient],
    path: str,
) -> None:
    client = make_client({"APP_ENV": "test"})
    incoming_id = "01941234-5678-7abc-8def-0123456789ab"

    response = client.post(
        path,
        json=VALID_POST_PAYLOADS[path],
        headers={"X-Request-Id": incoming_id},
    )

    assert response.status_code == 503
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.headers["x-request-id"] == incoming_id
    assert response.headers["cache-control"] == "no-store"

    problem = response.json()
    assert problem["type"] == "about:blank"
    assert problem["title"] == "Service Unavailable"
    assert problem["status"] == 503
    assert problem["instance"] == path
    assert problem["requestId"] == incoming_id
    assert isinstance(problem["detail"], str) and len(problem["detail"]) >= 10
    assert "errors" not in problem


@pytest.mark.parametrize("path", GET_STUB_ENDPOINTS)
def test_api_v1_valid_get_stub_returns_honest_503_problem_details(
    make_client: Callable[[Mapping[str, str | None] | None], TestClient],
    path: str,
) -> None:
    client = make_client({"APP_ENV": "test"})
    response = client.get(path)

    assert response.status_code == 503
    assert response.headers["content-type"].startswith("application/problem+json")
    problem = response.json()
    assert problem["title"] == "Service Unavailable"
    assert problem["status"] == 503
    assert problem["instance"] == path


def test_internal_service_secret_protects_api_v1_endpoints_without_blocking_health(
    make_client: Callable[[Mapping[str, str | None] | None], TestClient],
) -> None:
    secret = "internal-token-secret-value-123456"
    client = make_client({"APP_ENV": "test", "INTERNAL_SERVICE_SECRET": secret})

    assert client.get("/health").status_code == 200
    assert client.get("/api/v1/health").status_code == 200

    unauth = client.post(
        "/api/v1/ml/predict-relevance",
        json=VALID_POST_PAYLOADS["/api/v1/ml/predict-relevance"],
    )
    assert unauth.status_code == 401
    assert unauth.headers["content-type"].startswith("application/problem+json")
    assert secret not in unauth.text

    wrong = client.get(
        "/api/v1/ml/relevance/metadata",
        headers={"X-Internal-Token": "wrong-token"},
    )
    assert wrong.status_code == 401
    assert secret not in wrong.text

    authorized = client.post(
        "/api/v1/ml/predict-relevance",
        json=VALID_POST_PAYLOADS["/api/v1/ml/predict-relevance"],
        headers={"X-Internal-Token": secret},
    )
    assert authorized.status_code == 503


@pytest.mark.parametrize("path", POST_ENDPOINTS)
def test_api_v1_malformed_json_returns_400_problem_details(
    make_client: Callable[[Mapping[str, str | None] | None], TestClient],
    path: str,
) -> None:
    client = make_client({"APP_ENV": "test"})
    response = client.post(
        path,
        content=b'{"broken": ',
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 400
    assert response.headers["content-type"].startswith("application/problem+json")
    request_id = response.headers["x-request-id"]
    assert UUID_REGEX.match(request_id)
    problem = response.json()
    assert problem["title"] == "Bad Request"
    assert problem["status"] == 400
    assert problem["instance"] == path
    assert problem["requestId"] == request_id


@pytest.mark.parametrize("path", POST_ENDPOINTS)
def test_api_v1_get_on_post_endpoint_returns_405_problem_details(
    make_client: Callable[[Mapping[str, str | None] | None], TestClient],
    path: str,
) -> None:
    client = make_client({"APP_ENV": "test"})
    response = client.get(path)

    assert response.status_code == 405
    assert response.headers["content-type"].startswith("application/problem+json")
    problem = response.json()
    assert problem["title"] == "Method Not Allowed"
    assert problem["status"] == 405
    assert problem["instance"] == path


@pytest.mark.parametrize(
    ("path", "payload", "expected_error_paths"),
    [
        ("/api/v1/ml/predict-relevance", {"text": "   "}, {"text"}),
        ("/api/v1/ml/predict-relevance", {"text": "Halo", "extraField": 123}, {"extraField"}),
        ("/api/v1/ml/predict-sentiment", {"text": ""}, {"text"}),
        ("/api/v1/ml/predict-sentiment", {"text": "ab"}, {"text"}),
        ("/api/v1/ml/predict-sentiment/batch", {"items": []}, {"items"}),
        (
            "/api/v1/ml/predict-sentiment/batch",
            {"items": [{"id": "rev_1", "text": "  "}]},
            {"items.0.text"},
        ),
        (
            "/api/v1/rag/chat",
            {**VALID_POST_PAYLOADS["/api/v1/rag/chat"], "user_role": "CUSTOMER"},
            {"user_role"},
        ),
        (
            "/api/v1/rag/chat",
            {**VALID_POST_PAYLOADS["/api/v1/rag/chat"], "message": "   "},
            {"message"},
        ),
        (
            "/api/v1/insight/generate",
            {
                "period": "November 2026",
                "metrics": {
                    **VALID_POST_PAYLOADS["/api/v1/insight/generate"]["metrics"],
                    "total_orders": -1,
                },
            },
            {"metrics.total_orders"},
        ),
        (
            "/api/v1/insight/generate",
            {
                "period": "   ",
                "metrics": VALID_POST_PAYLOADS["/api/v1/insight/generate"]["metrics"],
            },
            {"period"},
        ),
    ],
)
def test_api_v1_invalid_payloads_return_422_problem_details(
    make_client: Callable[[Mapping[str, str | None] | None], TestClient],
    path: str,
    payload: dict[str, Any],
    expected_error_paths: set[str],
) -> None:
    client = make_client({"APP_ENV": "test"})
    response = client.post(path, json=payload)

    assert response.status_code == 422
    assert response.headers["content-type"].startswith("application/problem+json")
    request_id = response.headers["x-request-id"]
    assert UUID_REGEX.match(request_id)

    problem = response.json()
    assert problem["title"] == "Unprocessable Content"
    assert problem["status"] == 422
    assert problem["detail"] == "Request validation failed."
    assert problem["instance"] == path
    assert problem["requestId"] == request_id
    actual_paths = {item["path"] for item in problem["errors"]}
    assert expected_error_paths.issubset(actual_paths)


def test_api_v1_response_contract_models_validate_and_forbid_extra_fields() -> None:
    from app.contracts import (
        InsightGenerateData,
        InsightGenerateResponse,
        RagChatData,
        RagChatResponse,
        RagSourceItem,
        RelevanceMetadataData,
        RelevanceMetadataResponse,
        RelevanceModelMetrics,
        RelevancePredictData,
        RelevancePredictResponse,
        SentimentBatchItemResult,
        SentimentBatchResponse,
        SentimentPredictData,
        SentimentPredictResponse,
        SentimentProbabilities,
    )
    from app.schemas import ApiMeta

    meta = ApiMeta(requestId="01941234-5678-7abc-8def-0123456789ab")

    rel = RelevancePredictResponse(
        data=RelevancePredictData(
            text="Apakah ada nasi box ayam bakar?",
            label="relevant",
            is_relevant=True,
            confidence=0.942,
            intent=None,
            model_version="relevance_lr_v1.0",
        ),
        meta=meta,
    )
    assert rel.data.label == "relevant"

    rel_meta = RelevanceMetadataResponse(
        data=RelevanceMetadataData(
            modelName="relevance_classifier",
            version="1.0.0",
            algorithm="LogisticRegression",
            classes=["relevant", "out_of_domain"],
            metrics=RelevanceModelMetrics(f1Score=0.935, accuracy=0.941),
        ),
        meta=meta,
    )
    assert rel_meta.data.classes == ["relevant", "out_of_domain"]

    sent = SentimentPredictResponse(
        data=SentimentPredictData(
            text="Nasi liwetnya wangi pulen dan tepat waktu.",
            sentiment="positive",
            score=0.965,
            probabilities=SentimentProbabilities(positive=0.965, negative=0.035),
        ),
        meta=meta,
    )
    assert sent.data.sentiment == "positive"

    sent_batch = SentimentBatchResponse(
        data=[
            SentimentBatchItemResult(id="rev_01", sentiment="positive", score=0.952),
            SentimentBatchItemResult(id="rev_02", sentiment="negative", score=0.884),
        ],
        meta=meta,
    )
    assert len(sent_batch.data) == 2

    rag = RagChatResponse(
        data=RagChatData(
            reply="Catering Si Kembar melayani pesanan 50 nasi box dengan DP minimal 60%.",
            is_relevant=True,
            intent=None,
            tools_called=["search_catering_knowledge"],
            sources=[
                RagSourceItem(
                    source="faq.md",
                    category="pemesanan",
                    chunk_id="faq_order_01_c1",
                )
            ],
            tokens_used=185,
            is_fallback=False,
        ),
        meta=meta,
    )
    assert rag.data.is_fallback is False

    insight = InsightGenerateResponse(
        data=InsightGenerateData(
            period="November 2026",
            executive_summary="Sepanjang November 2026 tercatat 38 pesanan.",
            key_highlights=["Tingkat penyelesaian mencapai 89.4%."],
            operational_recommendations=["Lakukan penagihan pelunasan H-1."],
            model_used="Qwen2.5-7B-Instruct-vLLM-Modal",
            latency_ms=3420,
            is_fallback=False,
        ),
        meta=meta,
    )
    assert insight.data.latency_ms == 3420

    with pytest.raises(ValidationError):
        RelevancePredictData(
            text="Halo",
            label="relevant",
            is_relevant=True,
            confidence=0.94,
            model_version="relevance_lr_v1.0",
            unexpected="forbidden",  # type: ignore[call-arg]
        )
