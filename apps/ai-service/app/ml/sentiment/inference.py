"""Inference service for customer feedback sentiment classification with dual-artifact support."""

from __future__ import annotations

import importlib
import json
import math
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from app.contracts import (
    SentimentBatchItemRequest,
    SentimentBatchItemResult,
    SentimentLabel,
    SentimentPredictData,
    SentimentProbabilities,
)
from app.ml.sentiment.preprocess import tokenize_sentiment_text


class SentimentArtifactMissingError(RuntimeError):
    """Raised when required sentiment model artifacts cannot be loaded from disk."""


class SentimentClassifierService:
    """Service providing customer feedback sentiment prediction with dual-artifact fallback."""

    def __init__(
        self,
        *,
        artifacts_dir: Path | None = None,
        prefer_joblib: bool = True,
    ) -> None:
        self.artifacts_dir = (
            artifacts_dir
            if artifacts_dir is not None
            else Path(__file__).resolve().parent / "artifacts"
        )
        self.prefer_joblib = prefer_joblib
        self.joblib_path = self.artifacts_dir / "sentiment_model.joblib"
        self.weights_path = self.artifacts_dir / "sentiment_model_weights.json"
        self.metadata_path = self.artifacts_dir / "sentiment_metadata.json"

        self._joblib_pipeline: Any | None = None
        self._weights: dict[str, Any] | None = None
        self._available = False
        self._needs_attention_threshold: float = 0.75
        self._model_version: str = "sentiment_lr_v1.0"

        self._load_artifacts()

    def _load_artifacts(self) -> None:
        if self.weights_path.is_file():
            try:
                w = json.loads(self.weights_path.read_text(encoding="utf-8"))
                self._needs_attention_threshold = float(w.get("needs_attention_threshold", 0.75))
                self._model_version = str(w.get("model_version", "sentiment_lr_v1.0"))
            except Exception:  # pragma: no cover
                pass
        elif self.metadata_path.is_file():
            try:
                m = json.loads(self.metadata_path.read_text(encoding="utf-8"))
                self._needs_attention_threshold = float(m.get("needsAttentionThreshold", 0.75))
                self._model_version = str(
                    m.get("modelVersion", m.get("version", "sentiment_lr_v1.0"))
                )
            except Exception:  # pragma: no cover
                pass

        if self.prefer_joblib and self.joblib_path.is_file():
            try:
                joblib_module = importlib.import_module("joblib")
                self._joblib_pipeline = joblib_module.load(self.joblib_path)
                self._available = True
                return
            except Exception:  # pragma: no cover
                self._joblib_pipeline = None

        if self.weights_path.is_file():
            try:
                self._weights = json.loads(self.weights_path.read_text(encoding="utf-8"))
                self._available = True
                return
            except Exception:  # pragma: no cover
                self._weights = None

        self._available = False

    def get_metadata(self) -> dict[str, Any]:
        """Load and return sentiment evaluation metadata."""
        if not self.metadata_path.is_file():
            raise SentimentArtifactMissingError(
                f"Metadata artifact not found at {self.metadata_path}"
            )

        try:
            return json.loads(self.metadata_path.read_text(encoding="utf-8"))  # type: ignore[no-any-return]
        except Exception as exc:  # pragma: no cover
            raise SentimentArtifactMissingError(f"Failed to read metadata artifact: {exc}") from exc

    def predict(self, text: str) -> SentimentPredictData:
        """Classify customer feedback text as positive or negative."""
        if not self._available:
            raise SentimentArtifactMissingError(
                f"No usable model artifacts found in {self.artifacts_dir}"
            )

        stripped = text.strip()
        if len(stripped) < 3:
            raise ValueError("Input review text must contain at least 3 meaningful characters.")

        if self._joblib_pipeline is not None:
            return self._predict_with_joblib(text, stripped)

        if self._weights is not None:
            return self._predict_with_portable_weights(text, stripped)

        raise SentimentArtifactMissingError("Classifier model artifacts are unavailable.")

    def _predict_with_joblib(self, original_text: str, cleaned_text: str) -> SentimentPredictData:
        pipeline = self._joblib_pipeline
        assert pipeline is not None

        classes = list(getattr(pipeline, "classes_", ["negative", "positive"]))
        proba = pipeline.predict_proba([cleaned_text])[0]
        prob_dict = {str(cls_name): float(p) for cls_name, p in zip(classes, proba, strict=False)}

        p_pos_raw = prob_dict.get("positive", 0.0)
        p_pos = round(p_pos_raw, 4)
        p_neg = round(1.0 - p_pos, 4)

        sentiment: SentimentLabel = "positive" if p_pos >= p_neg else "negative"
        score = p_pos if sentiment == "positive" else p_neg
        needs_attention = (sentiment == "negative") and (score >= self._needs_attention_threshold)

        return SentimentPredictData(
            text=original_text,
            sentiment=sentiment,
            score=score,
            probabilities=SentimentProbabilities(positive=p_pos, negative=p_neg),
            needsAttention=needs_attention,
        )

    def _predict_with_portable_weights(
        self, original_text: str, cleaned_text: str
    ) -> SentimentPredictData:
        weights = self._weights
        assert weights is not None

        vec_meta = weights["vectorizer"]
        vocab: dict[str, int] = vec_meta["vocabulary"]
        idf_list: list[float] = vec_meta["idf"]
        ngram_min, ngram_max = vec_meta.get("ngram_range", [1, 1])
        sublinear_tf: bool = bool(vec_meta.get("sublinear_tf", False))
        norm_type: str = str(vec_meta.get("norm", "l2"))

        tokens = tokenize_sentiment_text(cleaned_text)

        counts: dict[int, int] = {}
        n_tokens = len(tokens)
        for n in range(ngram_min, ngram_max + 1):
            for i in range(n_tokens - n + 1):
                ngram = " ".join(tokens[i : i + n])
                if ngram in vocab:
                    idx = vocab[ngram]
                    counts[idx] = counts.get(idx, 0) + 1

        features: dict[int, float] = {}
        for idx, count in counts.items():
            tf = (1.0 + math.log(count)) if (sublinear_tf and count > 0) else float(count)
            features[idx] = tf * idf_list[idx]

        if norm_type == "l2" and features:
            sum_sq = sum(v * v for v in features.values())
            norm_val = math.sqrt(sum_sq)
            if norm_val > 0.0:
                features = {idx: v / norm_val for idx, v in features.items()}

        clf_meta = weights["classifier"]
        clf_type = clf_meta.get("type", "logistic_regression")

        if clf_type == "logistic_regression":
            coef: list[float] = clf_meta["coef"]
            intercept: float = float(clf_meta["intercept"])
            dot_product = sum(features[idx] * coef[idx] for idx in features if idx < len(coef))
            z = dot_product + intercept
            if z >= 40.0:
                p_pos_raw = 1.0
            elif z <= -40.0:
                p_pos_raw = 0.0
            else:
                p_pos_raw = 1.0 / (1.0 + math.exp(-z))
        elif clf_type == "multinomial_nb":  # pragma: no cover
            feature_log_prob: list[list[float]] = clf_meta["feature_log_prob"]
            class_log_prior: list[float] = clf_meta["class_log_prior"]
            classes: list[str] = clf_meta.get("classes", ["negative", "positive"])

            log_probs: list[float] = []
            for class_idx in range(len(classes)):
                lp = class_log_prior[class_idx]
                class_feat_lp = feature_log_prob[class_idx]
                for idx, val in features.items():
                    if idx < len(class_feat_lp):
                        lp += val * class_feat_lp[idx]
                log_probs.append(lp)

            max_lp = max(log_probs)
            exp_probs = [math.exp(lp - max_lp) for lp in log_probs]
            sum_exp = sum(exp_probs)
            probs = [ep / sum_exp for ep in exp_probs]
            prob_map = {cls_name: probs[i] for i, cls_name in enumerate(classes)}
            p_pos_raw = prob_map.get("positive", 0.0)
        else:  # pragma: no cover
            raise NotImplementedError(f"Unsupported classifier type: {clf_type}")

        p_pos = round(p_pos_raw, 4)
        p_neg = round(1.0 - p_pos, 4)

        sentiment: SentimentLabel = "positive" if p_pos >= p_neg else "negative"
        score = p_pos if sentiment == "positive" else p_neg
        needs_attention = (sentiment == "negative") and (score >= self._needs_attention_threshold)

        return SentimentPredictData(
            text=original_text,
            sentiment=sentiment,
            score=score,
            probabilities=SentimentProbabilities(positive=p_pos, negative=p_neg),
            needsAttention=needs_attention,
        )

    def predict_batch(
        self, items: Sequence[SentimentBatchItemRequest]
    ) -> list[SentimentBatchItemResult]:
        """Perform batch sentiment classification on customer feedback items."""
        if not items:
            raise ValueError("Batch request items must not be empty.")
        if len(items) > 100:
            raise ValueError("Batch request items must not exceed 100 items.")

        results: list[SentimentBatchItemResult] = []
        for item in items:
            pred = self.predict(item.text)
            results.append(
                SentimentBatchItemResult(
                    id=item.id,
                    sentiment=pred.sentiment,
                    score=pred.score,
                    needsAttention=pred.needsAttention,
                )
            )
        return results
