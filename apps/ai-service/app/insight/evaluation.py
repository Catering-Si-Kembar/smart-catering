from __future__ import annotations

import asyncio
import json
from typing import Final

from app.config import load_settings
from app.contracts import InsightGenerateRequest, InsightMetricsInput, InsightTopMenu
from app.insight.guardrails import validate_insight_numbers
from app.insight.prompts import compute_derived_kpi_facts
from app.insight.schemas import EvaluationSuiteSummary, ReportEvaluationRow, SLMInsightPayload
from app.insight.service import BusinessInsightService, build_default_insight_service

# 10 synthetic non-PII catering reports (is_synthetic = True) covering diverse operational regimes
# for the AI-06 numeric fidelity & latency evaluation benchmark.
TEN_SAMPLE_REPORTS: Final[tuple[tuple[str, InsightGenerateRequest], ...]] = (
    (
        "RPT-01",
        InsightGenerateRequest(
            period="November 2026",
            metrics=InsightMetricsInput(
                total_orders=38,
                total_revenue=24_500_000,
                completed_orders=34,
                unpaid_invoices=4,
                top_menus=[
                    InsightTopMenu(name="Nasi Box Ayam Lengkuas", portions=620),
                    InsightTopMenu(name="Nasi Box Rendang Daging", portions=310),
                ],
                forecast_next_week_portions=450,
            ),
        ),
    ),
    (
        "RPT-02",
        InsightGenerateRequest(
            period="Oktober 2026",
            metrics=InsightMetricsInput(
                total_orders=52,
                total_revenue=41_250_000,
                completed_orders=50,
                unpaid_invoices=2,
                top_menus=[
                    InsightTopMenu(name="Prasmanan Paket A", portions=1200),
                    InsightTopMenu(name="Nasi Liwet Komplit", portions=540),
                    InsightTopMenu(name="Snack Box Premium", portions=420),
                ],
                forecast_next_week_portions=680,
            ),
        ),
    ),
    (
        "RPT-03",
        InsightGenerateRequest(
            period="September 2026",
            metrics=InsightMetricsInput(
                total_orders=25,
                total_revenue=14_750_000,
                completed_orders=25,
                unpaid_invoices=0,
                top_menus=[
                    InsightTopMenu(name="Nasi Box Ayam Bakar Madu", portions=480),
                ],
                forecast_next_week_portions=300,
            ),
        ),
    ),
    (
        "RPT-04",
        InsightGenerateRequest(
            period="Agustus 2026",
            metrics=InsightMetricsInput(
                total_orders=64,
                total_revenue=58_900_000,
                completed_orders=56,
                unpaid_invoices=11,
                top_menus=[
                    InsightTopMenu(name="Tumpeng Nusantara 30 Porsi", portions=900),
                    InsightTopMenu(name="Nasi Box Empal Gentong", portions=750),
                ],
                forecast_next_week_portions=820,
            ),
        ),
    ),
    (
        "RPT-05",
        InsightGenerateRequest(
            period="Minggu 1 Desember 2026",
            metrics=InsightMetricsInput(
                total_orders=12,
                total_revenue=7_800_000,
                completed_orders=10,
                unpaid_invoices=3,
                top_menus=[
                    InsightTopMenu(name="Nasi Box Ayam Geprek", portions=210),
                    InsightTopMenu(name="Nasi Box Ikan Dori Saus Tartar", portions=140),
                ],
                forecast_next_week_portions=None,
            ),
        ),
    ),
    (
        "RPT-06",
        InsightGenerateRequest(
            period="Juli 2026",
            metrics=InsightMetricsInput(
                total_orders=0,
                total_revenue=0,
                completed_orders=0,
                unpaid_invoices=0,
                top_menus=[],
                forecast_next_week_portions=150,
            ),
        ),
    ),
    (
        "RPT-07",
        InsightGenerateRequest(
            period="Juni 2026",
            metrics=InsightMetricsInput(
                total_orders=45,
                total_revenue=33_600_000,
                completed_orders=41,
                unpaid_invoices=6,
                top_menus=[
                    InsightTopMenu(name="Nasi Kuning Kotak Spesial", portions=880),
                    InsightTopMenu(name="Prasmanan Tradisional", portions=640),
                    InsightTopMenu(name="Coffee Break Kantor", portions=320),
                ],
                forecast_next_week_portions=520,
            ),
        ),
    ),
    (
        "RPT-08",
        InsightGenerateRequest(
            period="Mei 2026",
            metrics=InsightMetricsInput(
                total_orders=80,
                total_revenue=76_400_000,
                completed_orders=78,
                unpaid_invoices=5,
                top_menus=[
                    InsightTopMenu(name="Prasmanan Pernikahan Gold", portions=2400),
                    InsightTopMenu(name="Nasi Box VIP Rendang", portions=1100),
                ],
                forecast_next_week_portions=950,
            ),
        ),
    ),
    (
        "RPT-09",
        InsightGenerateRequest(
            period="April 2026",
            metrics=InsightMetricsInput(
                total_orders=19,
                total_revenue=11_400_000,
                completed_orders=15,
                unpaid_invoices=7,
                top_menus=[
                    InsightTopMenu(name="Nasi Box Bento Anak", portions=350),
                ],
                forecast_next_week_portions=260,
            ),
        ),
    ),
    (
        "RPT-10",
        InsightGenerateRequest(
            period="Q4 2026",
            metrics=InsightMetricsInput(
                total_orders=115,
                total_revenue=98_500_000,
                completed_orders=109,
                unpaid_invoices=9,
                top_menus=[
                    InsightTopMenu(name="Nasi Box Ayam Lengkuas", portions=1950),
                    InsightTopMenu(name="Prasmanan Korporat", portions=1450),
                    InsightTopMenu(name="Snack Box Rapat", portions=890),
                    InsightTopMenu(name="Tumpeng Mini", portions=410),
                ],
                forecast_next_week_portions=1100,
            ),
        ),
    ),
)


async def evaluate_ten_reports(service: BusinessInsightService) -> EvaluationSuiteSummary:
    """Run the 10-report AI-06 benchmark verifying 100% numeric accuracy & recording latency."""
    rows: list[ReportEvaluationRow] = []

    for report_id, request in TEN_SAMPLE_REPORTS:
        response = await service.generate(request, request_id=f"eval-{report_id.lower()}")
        facts = compute_derived_kpi_facts(request)
        payload = SLMInsightPayload(
            executive_summary=response.executive_summary,
            key_highlights=response.key_highlights,
            operational_recommendations=response.operational_recommendations,
        )
        check = validate_insight_numbers(request, facts, payload)
        rows.append(
            ReportEvaluationRow(
                report_id=report_id,
                period=request.period,
                model_used=response.model_used,
                is_fallback=response.is_fallback,
                latency_ms=response.latency_ms,
                numeric_accuracy_passed=check.is_valid,
                checked_numeric_tokens=len(check.checked_tokens),
                unexpected_tokens=check.unexpected_tokens,
                missing_core_metrics=check.missing_core_metrics,
            )
        )

    latencies = [row.latency_ms for row in rows]
    matched = sum(1 for row in rows if row.numeric_accuracy_passed)
    fallbacks = sum(1 for row in rows if row.is_fallback)

    return EvaluationSuiteSummary(
        is_synthetic=True,
        data_source="synthetic_benchmark_non_pii_ai06",
        total_reports=len(rows),
        numeric_match_count=matched,
        numeric_match_rate=round(matched / len(rows), 4),
        fallback_count=fallbacks,
        min_latency_ms=min(latencies),
        avg_latency_ms=round(sum(latencies) / len(latencies), 2),
        max_latency_ms=max(latencies),
        results=rows,
    )


def _main() -> None:
    settings = load_settings()
    service = build_default_insight_service(settings)
    summary = asyncio.run(evaluate_ten_reports(service))
    print(json.dumps(summary.model_dump(), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    _main()
