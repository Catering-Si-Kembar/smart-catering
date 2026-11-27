from __future__ import annotations

import json
import math
import re
from typing import Final

from pydantic import ValidationError

from app.contracts import InsightGenerateRequest
from app.insight.ports import InsightValidationError
from app.insight.schemas import DerivedKPIFacts, NumericValidationResult, SLMInsightPayload

_OPERATIONAL_SHORTHAND_RE: Final[re.Pattern[str]] = re.compile(r"\bH[-+]\d+\b", re.IGNORECASE)
_CODE_FENCE_RE: Final[re.Pattern[str]] = re.compile(
    r"^\s*```(?:json)?\s*(?P<body>.*?)\s*```\s*$",
    re.DOTALL | re.IGNORECASE,
)
_NUMERIC_TOKEN_RE: Final[re.Pattern[str]] = re.compile(
    r"(?P<currency>Rp\.?\s*)?"
    r"(?P<number>\d+(?:[.,]\d+)*)"
    r"(?:\s*(?P<scale>miliar|milyar|juta|ribu)\b|(?P<percent>%))?",
    re.IGNORECASE,
)
_ID_THOUSANDS_RE: Final[re.Pattern[str]] = re.compile(r"^\d{1,3}(?:\.\d{3})+(?:,\d+)?$")
_EN_THOUSANDS_RE: Final[re.Pattern[str]] = re.compile(r"^\d{1,3}(?:,\d{3})+(?:\.\d+)?$")
_LEAKAGE_MARKERS: Final[tuple[str, ...]] = (
    "<verified_kpi_data>",
    "</verified_kpi_data>",
    "<derived_kpi_table>",
    "</derived_kpi_table>",
    "modal_api_key",
    "x-internal-token",
    "bearer ",
)


def parse_slm_insight_payload(raw_content: str) -> SLMInsightPayload:
    """Parse and strictly validate JSON output from the Modal vLLM SLM."""
    stripped = raw_content.strip()
    if not stripped:
        raise InsightValidationError("SLM returned empty content.")

    fence_match = _CODE_FENCE_RE.match(stripped)
    candidate = fence_match.group("body").strip() if fence_match else stripped

    if not candidate.startswith("{"):
        start = candidate.find("{")
        end = candidate.rfind("}")
        if start != -1 and end != -1 and end > start:
            candidate = candidate[start : end + 1]

    try:
        parsed = json.loads(candidate)
    except ValueError as exc:
        raise InsightValidationError("SLM response is not valid JSON.") from exc

    if not isinstance(parsed, dict):
        raise InsightValidationError("SLM response JSON root must be an object.")

    try:
        return SLMInsightPayload.model_validate(parsed)
    except ValidationError as exc:
        raise InsightValidationError("SLM JSON failed strict schema validation.") from exc


def _parse_number_string(
    raw_num: str,
    *,
    is_percent: bool,
    scale_word: str | None,
) -> float | None:
    multiplier = 1.0
    if scale_word:
        lower_scale = scale_word.lower()
        if lower_scale == "ribu":
            multiplier = 1_000.0
        elif lower_scale == "juta":
            multiplier = 1_000_000.0
        elif lower_scale in {"miliar", "milyar"}:
            multiplier = 1_000_000_000.0

    normalized: str
    if is_percent or scale_word:
        if "." in raw_num and "," in raw_num:
            if raw_num.rfind(",") > raw_num.rfind("."):
                normalized = raw_num.replace(".", "").replace(",", ".")
            else:
                normalized = raw_num.replace(",", "")
        elif "," in raw_num:
            normalized = raw_num.replace(",", ".")
        else:
            normalized = raw_num
    elif _ID_THOUSANDS_RE.match(raw_num):
        normalized = raw_num.replace(".", "").replace(",", ".")
    elif _EN_THOUSANDS_RE.match(raw_num):
        normalized = raw_num.replace(",", "")
    elif "," in raw_num and "." not in raw_num:
        normalized = raw_num.replace(",", ".")
    else:
        normalized = raw_num

    try:
        return float(normalized) * multiplier
    except ValueError:
        return None


def extract_numeric_tokens(text: str) -> list[tuple[str, float, bool]]:
    """Extract numeric tokens as (raw_token, parsed_float, is_percent) from narrative text."""
    masked = _OPERATIONAL_SHORTHAND_RE.sub(" ", text)
    results: list[tuple[str, float, bool]] = []
    for match in _NUMERIC_TOKEN_RE.finditer(masked):
        raw_num = match.group("number")
        scale_word = match.group("scale")
        is_percent = bool(match.group("percent"))
        parsed = _parse_number_string(raw_num, is_percent=is_percent, scale_word=scale_word)
        if parsed is None:
            continue
        raw_token = match.group(0).strip()
        results.append((raw_token, parsed, is_percent))
    return results


def _collect_allowed_values(
    request: InsightGenerateRequest,
    facts: DerivedKPIFacts,
) -> tuple[set[float], set[float]]:
    """Build exact allowlists for general numeric values and derived percentages."""
    allowed_exact: set[float] = {
        float(facts.total_orders),
        float(facts.total_revenue),
        float(facts.completed_orders),
        float(facts.uncompleted_orders),
        float(facts.unpaid_invoices),
        float(facts.settled_orders_estimate),
        float(facts.average_order_value),
        float(facts.total_top_menu_portions),
        float(len(request.metrics.top_menus)),
    }
    if facts.forecast_next_week_portions is not None:
        allowed_exact.add(float(facts.forecast_next_week_portions))

    for item in request.metrics.top_menus:
        allowed_exact.add(float(item.portions))
        for _, num_val, _ in extract_numeric_tokens(item.name):
            allowed_exact.add(num_val)

    for _, period_num, _ in extract_numeric_tokens(request.period):
        allowed_exact.add(period_num)

    allowed_percentages: set[float] = {
        facts.completion_rate_pct,
        facts.completion_rate_floor_pct,
        float(round(facts.completion_rate_pct)),
        facts.settled_rate_pct,
        facts.settled_rate_floor_pct,
        float(round(facts.settled_rate_pct)),
    }
    if facts.total_orders > 0:
        exact_rate = (facts.completed_orders / facts.total_orders) * 100.0
        allowed_percentages.add(round(exact_rate, 2))
        exact_settled_rate = (facts.settled_orders_estimate / facts.total_orders) * 100.0
        allowed_percentages.add(round(exact_settled_rate, 2))
        uncompleted_rate = (facts.uncompleted_orders / facts.total_orders) * 100.0
        allowed_percentages.add(round(uncompleted_rate, 1))
        allowed_percentages.add(math.floor(uncompleted_rate * 10.0) / 10.0)
        allowed_percentages.add(float(round(uncompleted_rate)))

        unpaid_rate = (facts.unpaid_invoices / facts.total_orders) * 100.0
        if unpaid_rate <= 100.0:
            allowed_percentages.add(round(unpaid_rate, 1))
            allowed_percentages.add(math.floor(unpaid_rate * 10.0) / 10.0)
            allowed_percentages.add(float(round(unpaid_rate)))

    for share in facts.top_menu_shares:
        allowed_percentages.add(share.share_pct)
        if facts.total_top_menu_portions > 0:
            exact_share = (share.portions / facts.total_top_menu_portions) * 100.0
            allowed_percentages.add(math.floor(exact_share * 10.0) / 10.0)
            allowed_percentages.add(round(exact_share, 2))
            allowed_percentages.add(float(round(exact_share)))

    return allowed_exact, allowed_percentages


def _matches_any(value: float, candidates: set[float], *, tolerance: float = 1e-6) -> bool:
    return any(abs(value - candidate) <= tolerance for candidate in candidates)


def validate_insight_numbers(
    request: InsightGenerateRequest,
    facts: DerivedKPIFacts,
    payload: SLMInsightPayload,
    *,
    secret_values: tuple[str, ...] = (),
) -> NumericValidationResult:
    """Verify 100% numeric fidelity and zero secret/prompt leakage on generated insight text."""
    combined_text = "\n".join(
        [
            payload.executive_summary,
            *payload.key_highlights,
            *payload.operational_recommendations,
        ]
    )
    lower_combined = combined_text.lower()

    for marker in _LEAKAGE_MARKERS:
        if marker in lower_combined:
            return NumericValidationResult(
                is_valid=False,
                reason=f"Prompt or internal marker leaked in output: {marker}",
            )

    for secret in secret_values:
        if secret and len(secret) >= 6 and secret in combined_text:
            return NumericValidationResult(
                is_valid=False,
                reason="Sensitive runtime secret leaked in output.",
            )

    allowed_exact, allowed_percentages = _collect_allowed_values(request, facts)
    extracted = extract_numeric_tokens(combined_text)

    checked_tokens: list[str] = []
    unexpected_tokens: list[str] = []
    parsed_values: list[float] = []

    for raw_token, numeric_value, is_percent in extracted:
        checked_tokens.append(raw_token)
        parsed_values.append(numeric_value)
        if is_percent:
            if not _matches_any(numeric_value, allowed_percentages, tolerance=0.05):
                unexpected_tokens.append(raw_token)
        elif not _matches_any(numeric_value, allowed_exact, tolerance=1e-6):
            unexpected_tokens.append(raw_token)

    missing_core: list[str] = []
    if not any(abs(val - float(facts.total_orders)) <= 1e-6 for val in parsed_values):
        missing_core.append("total_orders")
    if not any(abs(val - float(facts.total_revenue)) <= 1e-6 for val in parsed_values):
        missing_core.append("total_revenue")

    if unexpected_tokens:
        return NumericValidationResult(
            is_valid=False,
            checked_tokens=checked_tokens,
            unexpected_tokens=unexpected_tokens,
            missing_core_metrics=missing_core,
            reason="Detected unverified or hallucinated numeric values in generated insight.",
        )

    if missing_core:
        return NumericValidationResult(
            is_valid=False,
            checked_tokens=checked_tokens,
            unexpected_tokens=[],
            missing_core_metrics=missing_core,
            reason="Generated insight omitted core input KPI metrics (total_orders/total_revenue).",
        )

    return NumericValidationResult(
        is_valid=True,
        checked_tokens=checked_tokens,
        unexpected_tokens=[],
        missing_core_metrics=[],
        reason=None,
    )
