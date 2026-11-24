from __future__ import annotations

import csv
import importlib.util
import json
import re
import time
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
AI_SERVICE_ROOT = Path(__file__).resolve().parents[1]
DATASET_PATH = REPO_ROOT / "data" / "synthetic" / "relevance_dataset.csv"
NOTEBOOK_PATH = REPO_ROOT / "notebooks" / "04_relevance_classification.ipynb"
ARTIFACTS_DIR = AI_SERVICE_ROOT / "app" / "ml" / "relevance" / "artifacts"
JOBLIB_PATH = ARTIFACTS_DIR / "relevance_model.joblib"
WEIGHTS_JSON_PATH = ARTIFACTS_DIR / "relevance_model_weights.json"
METADATA_JSON_PATH = ARTIFACTS_DIR / "relevance_metadata.json"

HAS_ML_EXTRA = (
    importlib.util.find_spec("joblib") is not None
    and importlib.util.find_spec("sklearn") is not None
)

RELEVANT_PROBES: tuple[str, ...] = (
    "Apakah ada paket nasi box ayam bakar untuk acara kantor 100 orang?",
    "Berapa harga prasmanan untuk acara lamaran 80 porsi di Bandung?",
    "Minimal order nasi tumpeng untuk syukuran keluarga berapa porsi ya?",
    "Untuk pembayaran DP katering apakah minimal 60 persen sebelum hari H?",
    "Bisa pesan snack box dan nasi liwet untuk rapat hari Jumat pagi?",
    "Kapan batas akhir konfirmasi pesanan dan pelunasan invoice katering?",
    "Apakah semua menu ayam lengkuas dan rendang di Catering Si Kembar halal?",
    "Kalau mau ubah jumlah porsi dari 50 jadi 75 nasi box H-3 masih bisa?",
    "Berapa estimasi biaya paket nasi box menu ayam goreng dan sayur asem?",
    "Apakah pengantaran pesanan prasmanan sudah termasuk alat saji?",
)

OUT_OF_DOMAIN_PROBES: tuple[str, ...] = (
    "Tolong buatkan kode Python untuk algoritma sorting quicksort.",
    "Siapa presiden Indonesia yang memenangkan pemilu terakhir?",
    "Berapakah hasil integral dari x pangkat dua terhadap dx?",
    "Bagaimana prakiraan cuaca hujan di kota Bandung besok sore?",
    "Apakah harga saham bank dan bitcoin sedang naik minggu ini?",
    "Berapa jadwal dan skor pertandingan sepak bola Liga Inggris semalam?",
    "Buatkan puisi cinta singkat tentang senja di tepi pantai.",
    "Bagaimana cara memperbaiki error TypeScript pada komponen React?",
    "Saya mau pesan hotel murah dekat stasiun untuk liburan akhir pekan.",
    "Bagaimana prosedur batal tiket pesawat domestik agar dapat refund?",
)


def _norm_key(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^0-9a-zA-Z\s]", " ", text.lower())).strip()


def test_synthetic_relevance_dataset_schema_labeling_and_zero_leakage() -> None:
    assert DATASET_PATH.is_file(), f"Missing dataset: {DATASET_PATH}"

    with DATASET_PATH.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        assert reader.fieldnames is not None
        required_cols = {"id", "text", "label", "category", "is_synthetic", "split"}
        assert required_cols.issubset(set(reader.fieldnames))
        rows = list(reader)

    assert len(rows) >= 300, f"Expected >= 300 dataset rows, got {len(rows)}"

    train_keys: set[str] = set()
    test_keys: set[str] = set()
    all_keys: set[str] = set()
    label_counts: dict[str, int] = {"relevant": 0, "out_of_domain": 0}

    for row in rows:
        assert row["is_synthetic"].strip().lower() == "true", "All synthetic rows must be labeled"
        label = row["label"].strip()
        assert label in {"relevant", "out_of_domain"}, f"Unexpected label: {label}"
        label_counts[label] += 1

        split = row["split"].strip()
        assert split in {"train", "test"}, f"Unexpected split: {split}"

        text = row["text"].strip()
        assert len(text) >= 5, f"Text too short: {text!r}"
        key = _norm_key(text)
        assert key not in all_keys, f"Duplicate normalized text found: {text!r}"
        all_keys.add(key)

        if split == "train":
            train_keys.add(key)
        else:
            test_keys.add(key)

    assert train_keys.isdisjoint(test_keys), "Data leakage detected between train and test splits"
    assert len(train_keys) >= 240
    assert len(test_keys) >= 60
    assert label_counts["relevant"] >= 100
    assert label_counts["out_of_domain"] >= 80
    assert label_counts["relevant"] != label_counts["out_of_domain"], (
        "Dataset should include realistic class imbalance so imbalance handling is exercised"
    )


def test_preprocess_normalizes_indonesian_text_deterministically() -> None:
    from app.ml.relevance.preprocess import normalize_indonesian_text

    raw = "  Halo!!  Ada paket NASI-BOX (100 porsi)???   "
    cleaned = normalize_indonesian_text(raw)
    assert cleaned == cleaned.lower()
    assert "nasi" in cleaned
    assert "100" in cleaned
    assert "!!" not in cleaned
    assert "  " not in cleaned
    assert normalize_indonesian_text(cleaned) == cleaned


def test_relevance_metadata_and_portable_weights_artifacts_complete() -> None:
    assert WEIGHTS_JSON_PATH.is_file(), f"Missing portable weights artifact: {WEIGHTS_JSON_PATH}"
    assert METADATA_JSON_PATH.is_file(), f"Missing metadata artifact: {METADATA_JSON_PATH}"

    metadata: dict[str, Any] = json.loads(METADATA_JSON_PATH.read_text(encoding="utf-8"))
    assert metadata["modelName"] == "relevance_classifier"
    assert isinstance(metadata["version"], str) and len(metadata["version"]) >= 3
    assert isinstance(metadata["algorithm"], str) and len(metadata["algorithm"]) >= 3
    assert metadata["classes"] == ["relevant", "out_of_domain"]
    assert metadata["isSynthetic"] is True
    assert 0.50 <= float(metadata["confidenceThreshold"]) <= 0.80

    metrics = metadata["metrics"]
    assert float(metrics["f1Score"]) >= 0.88
    assert float(metrics["precision"]) >= 0.85
    assert float(metrics["recall"]) >= 0.85
    assert float(metrics["accuracy"]) >= 0.88

    comparison = metadata["modelComparison"]
    assert isinstance(comparison, list) and len(comparison) >= 2
    model_names = {str(item["model"]) for item in comparison}
    assert len(model_names) >= 2
    for item in comparison:
        assert 0.0 <= float(item["holdoutF1"]) <= 1.0
        assert 0.0 <= float(item["holdoutAccuracy"]) <= 1.0

    tuning = metadata["tuningComparison"]
    assert "beforeTuning" in tuning and "afterTuning" in tuning
    assert float(tuning["afterTuning"]["holdoutF1"]) >= float(tuning["beforeTuning"]["holdoutF1"])

    cm = metadata["confusionMatrix"]
    assert cm["labels"] == ["relevant", "out_of_domain"]
    matrix = cm["matrix"]
    assert len(matrix) == 2 and len(matrix[0]) == 2 and len(matrix[1]) == 2
    assert sum(matrix[0]) + sum(matrix[1]) >= 60

    weights: dict[str, Any] = json.loads(WEIGHTS_JSON_PATH.read_text(encoding="utf-8"))
    assert weights["classes"] == ["relevant", "out_of_domain"] or set(weights["classes"]) == {
        "relevant",
        "out_of_domain",
    }
    assert "vectorizer" in weights and "vocabulary" in weights["vectorizer"]
    assert "classifier" in weights and weights["classifier"]["type"] in {
        "logistic_regression",
        "multinomial_nb",
    }


def test_portable_relevance_inference_accuracy_and_latency_under_100ms() -> None:
    from app.ml.relevance.inference import (
        ModelArtifactMissingError,
        RelevanceClassifierService,
    )

    service = RelevanceClassifierService(artifacts_dir=ARTIFACTS_DIR, prefer_joblib=False)
    meta = service.get_metadata()
    assert meta.isSynthetic is True
    assert meta.classes == ["relevant", "out_of_domain"]
    assert meta.metrics.f1Score >= 0.88

    with pytest.raises(ValueError):
        service.predict("   ")

    relevant_hits = 0
    ood_hits = 0
    durations_ms: list[float] = []

    for text in RELEVANT_PROBES:
        t0 = time.perf_counter()
        result = service.predict(text)
        durations_ms.append((time.perf_counter() - t0) * 1000.0)
        assert result.text == text
        assert 0.0 <= result.confidence <= 1.0
        assert result.is_relevant == (result.label == "relevant")
        if result.label == "relevant":
            relevant_hits += 1

    for text in OUT_OF_DOMAIN_PROBES:
        t0 = time.perf_counter()
        result = service.predict(text)
        durations_ms.append((time.perf_counter() - t0) * 1000.0)
        assert result.text == text
        assert 0.0 <= result.confidence <= 1.0
        assert result.is_relevant == (result.label == "relevant")
        if result.label == "out_of_domain":
            ood_hits += 1

    assert relevant_hits >= 9, f"Expected >= 9/10 relevant probes correct, got {relevant_hits}/10"
    assert ood_hits >= 9, f"Expected >= 9/10 out_of_domain probes correct, got {ood_hits}/10"
    avg_ms = sum(durations_ms) / len(durations_ms)
    assert avg_ms < 100.0, f"Expected avg latency < 100ms, got {avg_ms:.2f}ms"

    missing_service = RelevanceClassifierService(
        artifacts_dir=ARTIFACTS_DIR / "nonexistent_dir",
        prefer_joblib=False,
    )
    with pytest.raises(ModelArtifactMissingError):
        missing_service.predict("Apakah ada paket nasi box?")


@pytest.mark.skipif(
    not HAS_ML_EXTRA, reason="Optional extra 'ml' not installed in this environment"
)
def test_joblib_artifact_exists_and_matches_portable_weights_parity() -> None:
    import joblib  # type: ignore[import-untyped]

    from app.ml.relevance.inference import RelevanceClassifierService

    assert JOBLIB_PATH.is_file(), f"Missing joblib artifact: {JOBLIB_PATH}"
    pipeline = joblib.load(JOBLIB_PATH)
    assert hasattr(pipeline, "predict")
    assert hasattr(pipeline, "predict_proba")

    # Verify direct compatibility with AI-05 DomainRelevanceClassifier contract
    sample_pred = str(pipeline.predict(["Apakah ada paket nasi box 100 porsi?"])[0])
    assert sample_pred in {"relevant", "out_of_domain"}

    svc_joblib = RelevanceClassifierService(artifacts_dir=ARTIFACTS_DIR, prefer_joblib=True)
    svc_portable = RelevanceClassifierService(artifacts_dir=ARTIFACTS_DIR, prefer_joblib=False)

    for text in (*RELEVANT_PROBES, *OUT_OF_DOMAIN_PROBES):
        res_j = svc_joblib.predict(text)
        res_p = svc_portable.predict(text)
        assert res_j.label == res_p.label, f"Label mismatch for {text!r}: {res_j} vs {res_p}"
        assert abs(res_j.confidence - res_p.confidence) < 1e-3, (
            f"Probability parity drift for {text!r}: {res_j.confidence} vs {res_p.confidence}"
        )


def test_relevance_notebook_is_valid_nbformat_with_executed_metrics() -> None:
    assert NOTEBOOK_PATH.is_file(), f"Missing notebook: {NOTEBOOK_PATH}"
    nb: dict[str, Any] = json.loads(NOTEBOOK_PATH.read_text(encoding="utf-8"))
    assert nb.get("nbformat") == 4
    cells = nb.get("cells", [])
    assert isinstance(cells, list) and len(cells) >= 8

    markdown_cells = [c for c in cells if c.get("cell_type") == "markdown"]
    code_cells = [c for c in cells if c.get("cell_type") == "code"]
    assert len(markdown_cells) >= 3
    assert len(code_cells) >= 5

    all_output_text: list[str] = []
    for cell in code_cells:
        for output in cell.get("outputs", []):
            assert output.get("output_type") != "error", f"Notebook contains error output: {output}"
            text_field = output.get("text", [])
            if isinstance(text_field, list):
                all_output_text.extend(str(item) for item in text_field)
            elif isinstance(text_field, str):
                all_output_text.append(text_field)

    joined_outputs = "\n".join(all_output_text).lower()
    for expected_term in ("is_synthetic", "f1", "confusion", "multinomialnb", "logisticregression"):
        assert expected_term in joined_outputs, (
            f"Notebook executed outputs missing expected term: {expected_term}"
        )
