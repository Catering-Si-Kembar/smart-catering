from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class HealthData(BaseModel):
    """Liveness payload for GET /health."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    status: Literal["ok"] = Field(
        default="ok",
        description="Service liveness status indicator.",
    )
    service: Literal["ai-service"] = Field(
        default="ai-service",
        description="Identifier of the responding backend service.",
    )


class PaginationMeta(BaseModel):
    """Standard pagination metadata inside meta.pagination."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    page: int = Field(
        ge=1,
        le=9_007_199_254_740_991,
        description="Current 1-based page number.",
    )
    limit: int = Field(
        ge=1,
        le=100,
        description="Maximum items per page (1..100).",
    )
    total: int = Field(
        ge=0,
        le=9_007_199_254_740_991,
        description="Total matching records across all pages.",
    )
    totalPages: int = Field(
        ge=0,
        le=9_007_199_254_740_991,
        description="Total pages (ceil(total / limit), or 0 when total is 0).",
    )


class ApiMeta(BaseModel):
    """Standard metadata envelope attached to every 200/201 response."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    requestId: str = Field(
        description="Canonical lowercase UUID correlated with the X-Request-Id header.",
        examples=["01941234-5678-7abc-8def-0123456789ab"],
    )
    pagination: PaginationMeta | None = Field(
        default=None,
        description="Optional pagination metadata for paginated list responses.",
    )


class ApiSuccess[T](BaseModel):
    """Cross-backend 200/201 success envelope."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    data: T
    meta: ApiMeta


class HealthResponse(BaseModel):
    """Concrete OpenAPI schema model for 200 GET /health."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    data: HealthData
    meta: ApiMeta


class ValidationIssue(BaseModel):
    """Sanitized field-level validation issue inside RFC 9457 ProblemDetails."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    path: str = Field(
        description="Dot-delimited field path (without source prefix) or '$' for root.",
        examples=["portions"],
    )
    code: Literal["invalid_value"] = Field(
        default="invalid_value",
        description="Stable machine-readable validation issue code.",
    )
    message: Literal["Invalid value"] = Field(
        default="Invalid value",
        description="Safe public validation message.",
    )


class ProblemDetails(BaseModel):
    """RFC 9457 Problem Details response body (application/problem+json)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    type: Literal["about:blank"] = Field(
        default="about:blank",
        description="Problem type URI (default 'about:blank' per RFC 9457).",
    )
    title: str = Field(
        description="Standard HTTP status phrase (422 is 'Unprocessable Content').",
        examples=["Unprocessable Content"],
    )
    status: int = Field(
        ge=400,
        le=599,
        description="Actual HTTP response status code.",
        examples=[422],
    )
    detail: str = Field(
        description="Safe human-readable public description with no internal details.",
        examples=["Request validation failed."],
    )
    instance: str = Field(
        description="Request URL pathname only (query string stripped).",
        examples=["/health"],
    )
    requestId: str = Field(
        description="Canonical lowercase UUID matching the X-Request-Id response header.",
        examples=["01941234-5678-7abc-8def-0123456789ab"],
    )
    errors: list[ValidationIssue] | None = Field(
        default=None,
        description="Optional sanitized field validation issues for 422 responses.",
    )
