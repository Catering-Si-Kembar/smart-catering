from __future__ import annotations

from typing import Final

from app.contracts import InsightGenerateData, InsightGenerateRequest
from app.insight.prompts import sanitize_prompt_text
from app.insight.schemas import DerivedKPIFacts

DETERMINISTIC_FALLBACK_MODEL: Final[str] = "deterministic-template-fallback"


def build_deterministic_insight(
    request: InsightGenerateRequest,
    facts: DerivedKPIFacts,
    *,
    model_used: str = DETERMINISTIC_FALLBACK_MODEL,
    latency_ms: int = 0,
) -> InsightGenerateData:
    """Build an executive-ready deterministic insight guaranteed 100% numerically faithful."""
    period = sanitize_prompt_text(request.period)

    if facts.total_orders == 0:
        executive_summary = (
            f"Pada periode {period}, tercatat 0 pesanan dengan total omzet "
            f"{facts.formatted_revenue} dan {facts.unpaid_invoices} invoice belum lunas."
        )
        zero_highlights = [
            f"Belum terdapat pesanan selesai (0 dari 0 pesanan) sepanjang {period}.",
            f"Jumlah invoice belum lunas tercatat sebanyak {facts.unpaid_invoices} invoice.",
        ]
        if facts.forecast_next_week_portions is not None:
            zero_highlights.append(
                "Proyeksi kebutuhan produksi minggu depan sebesar "
                f"{facts.forecast_next_week_portions} porsi."
            )

        zero_recommendations = [
            "Evaluasi saluran promosi dan tindak lanjuti penawaran ke klien korporat maupun acara.",
            "Verifikasi pencatatan pesanan dan jadwal dapur agar data periode berikutnya lengkap.",
        ]
        if facts.unpaid_invoices > 0:
            zero_recommendations.insert(
                0,
                f"Tindak lanjuti penagihan H-1 untuk {facts.unpaid_invoices} invoice belum lunas "
                "dari periode berjalan maupun sebelumnya.",
            )
        if facts.forecast_next_week_portions is not None and facts.forecast_next_week_portions > 0:
            zero_recommendations.append(
                "Siapkan perencanaan bahan baku lebih awal untuk mengantisipasi proyeksi "
                f"{facts.forecast_next_week_portions} porsi pada minggu depan."
            )

        return InsightGenerateData(
            period=request.period,
            executive_summary=executive_summary,
            key_highlights=zero_highlights,
            operational_recommendations=zero_recommendations,
            model_used=model_used,
            latency_ms=max(0, latency_ms),
            is_fallback=True,
        )

    executive_summary = (
        f"Sepanjang {period}, Catering Si Kembar mencatat {facts.total_orders} pesanan "
        f"dengan total omzet {facts.formatted_revenue} dan tingkat penyelesaian "
        f"{facts.completion_rate_pct}% ({facts.completed_orders} dari {facts.total_orders} "
        f"pesanan selesai)."
    )

    key_highlights = [
        (
            f"Rata-rata nilai pesanan mencapai {facts.formatted_average_order_value} per pesanan "
            f"dari total {facts.total_orders} pesanan."
        ),
        (
            f"Terdapat {facts.unpaid_invoices} invoice belum lunas serta "
            f"{facts.uncompleted_orders} pesanan yang masih dalam proses penyelesaian."
        ),
    ]

    if facts.top_menu_shares:
        top_item = facts.top_menu_shares[0]
        key_highlights.append(
            f"Menu terlaris adalah {top_item.name} dengan {top_item.portions} porsi "
            f"({top_item.share_pct}% dari {facts.total_top_menu_portions} porsi menu unggulan)."
        )

    if facts.forecast_next_week_portions is not None:
        key_highlights.append(
            "Proyeksi permintaan produksi minggu depan diperkirakan sebesar "
            f"{facts.forecast_next_week_portions} porsi."
        )

    operational_recommendations: list[str] = []
    if facts.unpaid_invoices > 0:
        operational_recommendations.append(
            f"Lakukan penagihan pelunasan H-1 secara proaktif untuk {facts.unpaid_invoices} "
            "invoice belum lunas guna menjaga arus kas operasional."
        )
    else:
        operational_recommendations.append(
            "Pertahankan disiplin konfirmasi DP dan pelunasan karena 0 invoice belum lunas "
            f"pada periode {period}."
        )

    if facts.uncompleted_orders > 0:
        operational_recommendations.append(
            f"Pantau ketat jadwal produksi dan pengantaran untuk {facts.uncompleted_orders} "
            "pesanan yang belum selesai agar tetap tepat waktu."
        )
    else:
        operational_recommendations.append(
            f"Pertahankan standar eksekusi dapur setelah seluruh {facts.completed_orders} "
            "pesanan terselesaikan."
        )

    if facts.top_menu_shares:
        top_item = facts.top_menu_shares[0]
        operational_recommendations.append(
            f"Prioritaskan ketersediaan bahan baku utama untuk {top_item.name} "
            f"({top_item.portions} porsi) sebagai kontributor permintaan tertinggi."
        )

    if facts.forecast_next_week_portions is not None:
        operational_recommendations.append(
            "Sesuaikan jadwal pembelian bahan baku dan kapasitas tim dapur untuk target "
            f"proyeksi minggu depan sebesar {facts.forecast_next_week_portions} porsi."
        )

    return InsightGenerateData(
        period=request.period,
        executive_summary=executive_summary,
        key_highlights=key_highlights,
        operational_recommendations=operational_recommendations,
        model_used=model_used,
        latency_ms=max(0, latency_ms),
        is_fallback=True,
    )
