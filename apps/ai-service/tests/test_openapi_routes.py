from urllib.parse import urljoin

from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.main import create_app


class ContractPayload(BaseModel):
    quantity: int


def test_openapi_tracks_registered_routes_and_pydantic_validation_contract() -> None:
    application = create_app(env={"APP_ENV": "test"})

    @application.post("/_test/contracts", response_model=ContractPayload)
    async def contract_endpoint(payload: ContractPayload) -> ContractPayload:
        return payload

    document = TestClient(application).get("/openapi.json").json()
    operation = document["paths"]["/_test/contracts"]["post"]
    body_schema = operation["requestBody"]["content"]["application/json"]["schema"]
    model_name = body_schema["$ref"].rsplit("/", 1)[-1]
    model = document["components"]["schemas"][model_name]
    assert model["properties"]["quantity"]["type"] == "integer"
    assert "quantity" in model["required"]
    validation_response = operation["responses"]["422"]
    if "$ref" in validation_response:
        name = validation_response["$ref"].rsplit("/", 1)[-1]
        validation_response = document["components"]["responses"][name]
    assert "application/problem+json" in validation_response["content"]


def test_documented_server_keeps_requests_on_the_current_backend_origin() -> None:
    application = create_app(env={"APP_ENV": "test"})
    document = TestClient(application).get("/openapi.json").json()
    resolved_server = urljoin(
        "https://internal.example/openapi.json", document["servers"][0]["url"]
    )
    assert resolved_server == "https://internal.example/"
