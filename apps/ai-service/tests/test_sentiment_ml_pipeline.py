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
DATASET_PATH = REPO_ROOT / "data" / "synthetic" / "sentiment_dataset.csv"
NOTEBOOK_PATH = REPO_ROOT / "notebooks" / "05_sentiment_analysis.ipynb"
ARTIFACTS_DIR = AI_SERVICE_ROOT / "app" / "ml" / "sentiment" / "artifacts"
JOBLIB_PATH = ARTIFACTS_DIR / "sentiment_model.joblib"
WEIGHTS_JSON_PATH = ARTIFACTS_DIR / "sentiment_model_weights.json"
METADATA_JSON_PATH = ARTIFACTS_DIR / "sentiment_metadata.json"

HAS_ML_EXTRA = (
    importlib.util.find_spec("joblib") is not None
    and importlib.util.find_spec("sklearn") is not None
)

POSITIVE_PROBES: tuple[str, ...] = (
    "Nasi liwetnya wangi pulen, ayam bakarnya meresap dan datang tepat waktu!",
    "Alhamdulillah 100 nasi box untuk rapat kantor sangat memuaskan, porsinya pas.",
    "Rendangnya empuk bumbunya mantap, tamu lamaran semua memuji makanannya.",
    "Pengantaran cepat sebelum jam acara, kemasan rapi, makanan masih hangat.",
    "Admin responsif banget bantu hitung porsi, snack box enak dan segar.",
    "Prasmanan Catering Si Kembar selalu jadi langganan kantor, bersih dan halal.",
    "Nasi tumpeng syukuran tampilannya cantik dan rasanya juara, terima kasih!",
    "Sayur asem dan ayam lengkuasnya segar, tidak berminyak, sangat recommended.",
    "Pelayanan ramah, harga sesuai kualitas, semua peserta seminar suka makanannya.",
    "Pesanan 150 box aman tanpa kurang satu pun, rasa konsisten enak banget.",
)

NEGATIVE_PROBES: tuple[str, ...] = (
    "Pengantaran terlambat hampir satu jam sampai tamu rapat sudah bubar, kecewa.",
    "Nasinya agak keras dan dingin waktu sampai, lauk ayamnya juga terlalu asin.",
    "Jumlah nasi box kurang 5 porsi dari pesanan yang sudah dibayar lunas.",
    "Kemasan dus banyak yang penyok dan kuah sayur tumpah ke mana-mana.",
    "Sayur sudah agak basi berbau asam saat dibuka, sangat mengecewakan.",
    "Admin susah dihubungi waktu mau konfirmasi jam kirim, pelayanan lambat.",
    "Porsi lauknya terlalu kecil dan tidak sesuai foto katalog yang dijanjikan.",
    "Sambalnya pedas sekali dan ayam gorengnya masih kurang matang di dalam.",
    "Invoice salah hitung dan pengantaran tidak sesuai alamat yang diberikan.",
    "Makanan kurang higienis, ada sendok plastik yang tidak masuk di beberapa box.",
)

MIXED_SENTIMENT_PROBES: tuple[str, ...] = (
    "Makanannya enak dan bumbunya pas, tapi pengantarannya terlambat 40 menit.",
    "Ayam bakarnya mantap sekali, cuma sayang porsi nasinya terlalu sedikit.",
    "Datang tepat waktu dan rapi, namun rasa sayurnya agak hambar dan dingin.",
    "Harga terjangkau dan admin ramah, tetapi kemasan beberapa dus penyok.",
)


def _norm_key(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^0-9a-zA-Z\s]", " ", text.lower())).strip()


def test_synthetic_sentiment_dataset_schema_labeling_and_zero_leakage() -> None:
    assert DATASET_PATH.is_file(), f"Missing dataset: {DATASET_PATH}"

    with DATASET_PATH.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        assert reader.fieldnames is not None
        required_cols = {"id", "text", "sentiment", "category", "is_synthetic", "split"}
        assert required_cols.issubset(set(reader.fieldnames))
        rows = list(reader)

    assert len(rows) >= 300, f"Expected >= 300 dataset rows, got {len(rows)}"

    train_keys: set[str] = set()
    test_keys: set[str] = set()
    all_keys: set[str] = set()
    label_counts: dict[str, int] = {"positive": 0, "negative": 0}
    mixed_count = 0

    for row in rows:
        assert row["is_synthetic"].strip().lower() == "true", "All synthetic rows must be labeled"
        label = row["sentiment"].strip()
        assert label in {"positive", "negative"}, f"Unexpected sentiment label: {label}"
        label_counts[label] += 1

        split = row["split"].strip()
        assert split in {"train", "test"}, f"Unexpected split: {split}"

        if "mixed" in row["category"].strip().lower():
            mixed_count += 1

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
    assert label_counts["positive"] >= 120
    assert label_counts["negative"] >= 90
    assert label_counts["positive"] != label_counts["negative"], (
        "Dataset should include realistic class imbalance so imbalance handling is exercised"
    )
    assert mixed_count >= 12, f"Expected >= 12 mixed-sentiment examples, got {mixed_count}"


def test_preprocess_normalizes_indonesian_feedback_deterministically() -> None:
    from app.ml.sentiment.preprocess import normalize_sentiment_text

    raw = "  Makanannya ENAK bgt!! Ga nyesel, tp dtg agak telat :(  "
    cleaned = normalize_sentiment_text(raw)
    assert cleaned == cleaned.lower()
    assert "enak" in cleaned
    assert "!!" not in cleaned
    assert "  " not in cleaned
    assert normalize_sentiment_text(cleaned) == cleaned


def test_sentiment_metadata_and_portable_weights_artifacts_complete() -> None:
    assert WEIGHTS_JSON_PATH.is_file(), f"Missing portable weights artifact: {WEIGHTS_JSON_PATH}"
    assert METADATA_JSON_PATH.is_file(), f"Missing metadata artifact: {METADATA_JSON_PATH}"

    metadata: dict[str, Any] = json.loads(METADATA_JSON_PATH.read_text(encoding="utf-8"))
    assert metadata["modelName"] == "sentiment_classifier"
    assert isinstance(metadata["version"], str) and len(metadata["version"]) >= 3
    assert isinstance(metadata["algorithm"], str) and len(metadata["algorithm"]) >= 3
    assert metadata["classes"] == ["positive", "negative"]
    assert metadata["isSynthetic"] is True
    assert float(metadata["needsAttentionThreshold"]) == pytest.approx(0.75, abs=0.05)

    metrics = metadata["metrics"]
    assert float(metrics["f1Score"]) >= 0.85
    assert float(metrics["precision"]) >= 0.82
    assert float(metrics["recall"]) >= 0.82
    assert float(metrics["accuracy"]) >= 0.85

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
    assert cm["labels"] == ["positive", "negative"]
    matrix = cm["matrix"]
    assert len(matrix) == 2 and len(matrix[0]) == 2 and len(matrix[1]) == 2
    assert sum(matrix[0]) + sum(matrix[1]) >= 60

    error_analysis = metadata["errorAnalysis"]
    assert isinstance(error_analysis, dict)
    mixed_examples = error_analysis.get("mixedSentimentExamples", [])
    assert isinstance(mixed_examples, list) and len(mixed_examples) >= 3
    assert isinstance(error_analysis.get("summary"), str) and len(error_analysis["summary"]) >= 20

    weights: dict[str, Any] = json.loads(WEIGHTS_JSON_PATH.read_text(encoding="utf-8"))
    assert set(weights["classes"]) == {"positive", "negative"}
    assert "vectorizer" in weights and "vocabulary" in weights["vectorizer"]
    assert "classifier" in weights and weights["classifier"]["type"] in {
        "logistic_regression",
        "multinomial_nb",
    }


def test_portable_sentiment_inference_accuracy_batch_and_latency_under_50ms() -> None:
    from app.contracts import SentimentBatchItemRequest
    from app.ml.sentiment.inference import (
        SentimentArtifactMissingError,
        SentimentClassifierService,
    )

    service = SentimentClassifierService(artifacts_dir=ARTIFACTS_DIR, prefer_joblib=False)

    for bad_text in ("", "   ", "ok", "ya", "!!!", "...", "-- --", "a! b?"):
        with pytest.raises(ValueError):
            service.predict(bad_text)

    pos_hits = 0
    neg_hits = 0
    durations_ms: list[float] = []

    for text in POSITIVE_PROBES:
        t0 = time.perf_counter()
        result = service.predict(text)
        durations_ms.append((time.perf_counter() - t0) * 1000.0)
        assert result.text == text
        assert result.sentiment in {"positive", "negative"}
        assert 0.0 <= result.score <= 1.0
        prob_sum = result.probabilities.positive + result.probabilities.negative
        assert abs(prob_sum - 1.0) <= 0.005
        assert result.needsAttention == (result.sentiment == "negative" and result.score >= 0.75)
        if result.sentiment == "positive":
            pos_hits += 1

    for text in NEGATIVE_PROBES:
        t0 = time.perf_counter()
        result = service.predict(text)
        durations_ms.append((time.perf_counter() - t0) * 1000.0)
        assert result.text == text
        assert result.sentiment in {"positive", "negative"}
        assert 0.0 <= result.score <= 1.0
        prob_sum = result.probabilities.positive + result.probabilities.negative
        assert abs(prob_sum - 1.0) <= 0.005
        assert result.needsAttention == (result.sentiment == "negative" and result.score >= 0.75)
        if result.sentiment == "negative":
            neg_hits += 1

    assert pos_hits >= 9, f"Expected >= 9/10 positive probes correct, got {pos_hits}/10"
    assert neg_hits >= 9, f"Expected >= 9/10 negative probes correct, got {neg_hits}/10"
    avg_ms = sum(durations_ms) / len(durations_ms)
    assert avg_ms < 50.0, f"Expected avg latency < 50ms, got {avg_ms:.2f}ms"

    for mixed_text in MIXED_SENTIMENT_PROBES:
        mixed_res = service.predict(mixed_text)
        assert mixed_res.sentiment in {"positive", "negative"}
        assert 0.0 <= mixed_res.score <= 1.0

    batch_items = [
        SentimentBatchItemRequest(id="rev_pos", text=POSITIVE_PROBES[0]),
        SentimentBatchItemRequest(id="rev_neg", text=NEGATIVE_PROBES[0]),
        SentimentBatchItemRequest(id="rev_mix", text=MIXED_SENTIMENT_PROBES[0]),
    ]
    batch_results = service.predict_batch(batch_items)
    assert [item.id for item in batch_results] == ["rev_pos", "rev_neg", "rev_mix"]
    assert batch_results[0].sentiment == "positive"
    assert batch_results[1].sentiment == "negative"
    assert batch_results[1].needsAttention == (batch_results[1].score >= 0.75)

    with pytest.raises(ValueError):
        service.predict_batch([])

    missing_service = SentimentClassifierService(
        artifacts_dir=ARTIFACTS_DIR / "nonexistent_dir",
        prefer_joblib=False,
    )
    with pytest.raises(SentimentArtifactMissingError):
        missing_service.predict("Nasi box enak dan tepat waktu.")


@pytest.mark.skipif(
    not HAS_ML_EXTRA, reason="Optional extra 'ml' not installed in this environment"
)
def test_joblib_sentiment_artifact_exists_and_matches_portable_weights_parity() -> None:
    import importlib

    from app.ml.sentiment.inference import SentimentClassifierService

    joblib = importlib.import_module("joblib")
    assert JOBLIB_PATH.is_file(), f"Missing joblib artifact: {JOBLIB_PATH}"
    pipeline = joblib.load(JOBLIB_PATH)
    assert hasattr(pipeline, "predict")
    assert hasattr(pipeline, "predict_proba")

    svc_joblib = SentimentClassifierService(artifacts_dir=ARTIFACTS_DIR, prefer_joblib=True)
    svc_portable = SentimentClassifierService(artifacts_dir=ARTIFACTS_DIR, prefer_joblib=False)

    for text in (*POSITIVE_PROBES, *NEGATIVE_PROBES, *MIXED_SENTIMENT_PROBES):
        res_j = svc_joblib.predict(text)
        res_p = svc_portable.predict(text)
        assert res_j.sentiment == res_p.sentiment, (
            f"Label mismatch for {text!r}: {res_j} vs {res_p}"
        )
        assert abs(res_j.score - res_p.score) < 1e-3, (
            f"Probability parity drift for {text!r}: {res_j.score} vs {res_p.score}"
        )
        assert res_j.needsAttention == res_p.needsAttention


def test_sentiment_notebook_is_valid_nbformat_compilable_with_executed_metrics() -> None:
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
    for idx, cell in enumerate(code_cells):
        source = "".join(cell.get("source", []))
        compile(source, f"05_sentiment_analysis_cell_{idx}.py", "exec")
        for output in cell.get("outputs", []):
            assert output.get("output_type") != "error", f"Notebook contains error output: {output}"
            text_field = output.get("text", [])
            if isinstance(text_field, list):
                all_output_text.extend(str(item) for item in text_field)
            elif isinstance(text_field, str):
                all_output_text.append(text_field)

    joined_outputs = "\n".join(all_output_text).lower()
    for expected_term in (
        "is_synthetic",
        "f1",
        "confusion",
        "mixed",
        "multinomialnb",
        "logisticregression",
    ):
        assert expected_term in joined_outputs, (
            f"Notebook executed outputs missing expected term: {expected_term}"
        )
