from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any, Final

from app.contracts import RagUserRole
from app.ml.relevance.inference import (
    ModelArtifactMissingError,
    RelevanceClassifierService,
)
from app.rag.schemas import (
    GuardrailCategory,
    GuardrailVerdict,
    RelevanceDecision,
    RelevanceLabel,
)

security_logger = logging.getLogger("smart_catering.ai_service.security")

_PROMPT_INJECTION_PATTERNS: Final[tuple[re.Pattern[str], ...]] = (
    re.compile(
        r"\b(abaikan|lupakan|hiraukan|lewati)\s+(semua\s+)?(aturan|instruksi|perintah|batasan)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(ignore|disregard|forget|bypass|override)\s+(all\s+)?(previous|prior|system)\s+"
        r"(instructions?|rules?|prompts?|guardrails?)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(tampilkan|ungkapkan|bocorkan|reveal|print|show)\s+(isi\s+)?"
        r"(system\s*prompt|prompt\s*sistem|instruksi\s*sistem)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(bertindak\s+sebagai|act\s+as|pretend\s+to\s+be|you\s+are\s+now)\s+"
        r"(admin|root|superuser|dan|developer\s+mode)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(ubah\s+peran|switch\s+role|elevate\s+privilege|mode\s+tanpa\s+batas|jailbreak)\b",
        re.IGNORECASE,
    ),
)

_SQL_ATTEMPT_PATTERNS: Final[tuple[re.Pattern[str], ...]] = (
    re.compile(
        r"\b(select\s+.+\s+from|drop\s+table|delete\s+from|insert\s+into|"
        r"update\s+\w+\s+set|alter\s+table|truncate\s+table|union\s+select)\b",
        re.IGNORECASE,
    ),
    re.compile(r"\b(jalankan|eksekusi|run|execute)\s+(query\s+)?sql\b", re.IGNORECASE),
    re.compile(r"(;\s*--|'\s+or\s+'1'='1|\b1=1\b)", re.IGNORECASE),
)

_DATA_EXFILTRATION_PATTERNS: Final[tuple[re.Pattern[str], ...]] = (
    re.compile(
        r"\b(password|kata\s*sandi|api[\s_-]*key|secret[\s_-]*key|internal[\s_-]*token|"
        r"database[\s_-]*url|\.env|kredensial|gaji\s+karyawan|data\s+gaji)\b",
        re.IGNORECASE,
    ),
)

_INDIRECT_INJECTION_LINE: Final[re.Pattern[str]] = re.compile(
    r"(ignore\s+previous|abaikan\s+aturan|system\s*prompt|override\s+role|"
    r"execute\s+sql|drop\s+table|jailbreak|tampilkan\s+password)",
    re.IGNORECASE,
)

_CATERING_DOMAIN_KEYWORDS: Final[frozenset[str]] = frozenset(
    {
        "catering",
        "katering",
        "kembar",
        "menu",
        "nasi",
        "box",
        "kotak",
        "prasmanan",
        "tumpeng",
        "ayam",
        "rendang",
        "liwet",
        "lauk",
        "paket",
        "porsi",
        "harga",
        "pesan",
        "pesanan",
        "pemesanan",
        "order",
        "ord-",
        "invoice",
        "inv-",
        "tagihan",
        "bayar",
        "pembayaran",
        "dp",
        "uang muka",
        "lunas",
        "pelunasan",
        "piutang",
        "jadwal",
        "produksi",
        "masak",
        "dapur",
        "antar",
        "pengantaran",
        "pengiriman",
        "acara",
        "sop",
        "faq",
        "halal",
        "kebersihan",
        "batal",
        "pembatalan",
        "minimal order",
        "lead time",
        "resep",
        "bahan",
        "bumbu",
        "staf",
        "klien",
        "pelanggan",
    }
)

_CATERING_CODE_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"\b(ord|inv)-\d{4,8}-\d{1,6}\b",
    re.IGNORECASE,
)

_OUT_OF_DOMAIN_HINT_PATTERNS: Final[tuple[re.Pattern[str], ...]] = (
    re.compile(
        r"\b(python|javascript|typescript|react|html|css|coding|kode\s+program|algoritma|"
        r"presiden|pemilu|politik|partai|saham|bitcoin|kripto|crypto|cuaca|hujan|gempa|"
        r"sepak\s*bola|liga|skor\s+pertandingan|puisi|pantun|cerpen|terjemahkan|translate|"
        r"rumus\s+fisika|integral|turunan|sejarah\s+dunia|planet|galaksi)\b",
        re.IGNORECASE,
    ),
)


def detect_input_guardrail(text: str) -> GuardrailVerdict:
    """Inspect user input for prompt injection, SQL injection/free-SQL, or secret exfiltration."""
    normalized = text.strip()
    for pattern in _SQL_ATTEMPT_PATTERNS:
        if pattern.search(normalized):
            return GuardrailVerdict(
                blocked=True,
                category="sql_injection",
                reason="Permintaan query SQL bebas atau manipulasi database tidak diizinkan.",
            )
    for pattern in _PROMPT_INJECTION_PATTERNS:
        if pattern.search(normalized):
            return GuardrailVerdict(
                blocked=True,
                category="prompt_injection",
                reason="Upaya pengabaian aturan atau manipulasi instruksi sistem ditolak.",
            )
    for pattern in _DATA_EXFILTRATION_PATTERNS:
        if pattern.search(normalized):
            return GuardrailVerdict(
                blocked=True,
                category="data_exfiltration",
                reason="Permintaan kredensial, rahasia sistem, atau data gaji ditolak.",
            )
    return GuardrailVerdict(blocked=False, category="ok", reason=None)


def sanitize_untrusted_text(text: str, *, max_chars: int = 1200) -> str:
    """Neutralize potential indirect prompt injection lines inside KB chunks or DB notes."""
    cleaned_lines: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if _INDIRECT_INJECTION_LINE.search(line):
            cleaned_lines.append("[konten instruksi mencurigakan dinetralkan]")
        else:
            cleaned_lines.append(line)
    joined = "\n".join(cleaned_lines)
    if len(joined) > max_chars:
        return joined[:max_chars].rstrip() + "..."
    return joined


def wrap_tool_output(source: str, payload: object) -> str:
    """Wrap untrusted tool output in explicit data delimiters for indirect injection defense."""
    serialized = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    sanitized = sanitize_untrusted_text(serialized, max_chars=2400)
    return f'<TOOL_OUTPUT source="{source}">{sanitized}</TOOL_OUTPUT>'


def log_security_event(
    *,
    category: GuardrailCategory | str,
    user_role: RagUserRole,
    conversation_id: str,
    request_id: str,
    detail: str,
    tool_name: str | None = None,
) -> None:
    """Emit structured JSON security audit log without leaking secrets, PII, or raw payloads."""
    event: dict[str, Any] = {
        "event": "rag_security_event",
        "category": category,
        "userRole": user_role,
        "conversationId": conversation_id,
        "requestId": request_id,
        "blocked": True,
        "detail": detail,
    }
    if tool_name is not None:
        event["toolName"] = tool_name
    security_logger.warning(json.dumps(event, separators=(",", ":")))


class DomainRelevanceClassifier:
    """Two-class relevance gate (AI-02): delegates to RelevanceClassifierService,
    else rule fallback.
    """

    def __init__(
        self,
        *,
        relevance_service: RelevanceClassifierService | None = None,
        artifact_path: Path | None = None,
        confidence_threshold: float | None = None,
    ) -> None:
        if relevance_service is not None:
            self._relevance_service = relevance_service
        else:
            artifacts_dir = artifact_path.parent if artifact_path is not None else None
            self._relevance_service = RelevanceClassifierService(
                artifacts_dir=artifacts_dir,
            )
        self._confidence_threshold = confidence_threshold

    async def classify(self, text: str) -> RelevanceDecision:
        if not text.strip():
            return RelevanceDecision(
                label="out_of_domain",
                is_relevant=False,
                confidence=1.0,
                model_version="fallback_rule_relevance_v0",
            )
        try:
            res = self._relevance_service.predict(text)
        except ModelArtifactMissingError:
            return self._classify_with_fallback_rules(text)

        if self._confidence_threshold is not None:
            p_rel = res.confidence if res.is_relevant else round(1.0 - res.confidence, 4)
            is_rel = p_rel >= self._confidence_threshold
            label: RelevanceLabel = "relevant" if is_rel else "out_of_domain"
            conf = p_rel if is_rel else round(1.0 - p_rel, 4)
            return RelevanceDecision(
                label=label,
                is_relevant=is_rel,
                confidence=round(min(max(conf, 0.0), 1.0), 4),
                model_version=res.model_version,
            )

        return RelevanceDecision(
            label=res.label,
            is_relevant=res.is_relevant,
            confidence=res.confidence,
            model_version=res.model_version,
        )

    def _classify_with_fallback_rules(self, text: str) -> RelevanceDecision:
        lowered = text.lower().strip()
        if not lowered:
            return RelevanceDecision(
                label="out_of_domain",
                is_relevant=False,
                confidence=1.0,
                model_version="fallback_rule_relevance_v0",
            )

        has_order_or_invoice_code = bool(_CATERING_CODE_PATTERN.search(lowered))
        matched_keywords = sum(1 for kw in _CATERING_DOMAIN_KEYWORDS if kw in lowered)
        has_ood_hint = any(p.search(lowered) for p in _OUT_OF_DOMAIN_HINT_PATTERNS)

        if has_order_or_invoice_code or matched_keywords >= 2:
            confidence = min(0.95, 0.75 + 0.05 * matched_keywords)
            return RelevanceDecision(
                label="relevant",
                is_relevant=True,
                confidence=round(confidence, 4),
                model_version="fallback_rule_relevance_v0",
            )
        if matched_keywords == 1 and not has_ood_hint:
            return RelevanceDecision(
                label="relevant",
                is_relevant=True,
                confidence=0.72,
                model_version="fallback_rule_relevance_v0",
            )
        return RelevanceDecision(
            label="out_of_domain",
            is_relevant=False,
            confidence=0.92 if has_ood_hint else 0.8,
            model_version="fallback_rule_relevance_v0",
        )
