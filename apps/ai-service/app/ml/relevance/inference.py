"""Inference service for domain relevance classification with dual-artifact support."""

from __future__ import annotations

import importlib
import json
import math
import re
from pathlib import Path
from typing import Any

from app.contracts import (
    RelevanceLabel,
    RelevanceMetadataData,
    RelevanceModelMetrics,
    RelevancePredictData,
)
from app.ml.relevance.preprocess import tokenize_indonesian_text

_TOKEN_PATTERN = re.compile(r"(?u)\b\w+\b")


class ModelArtifactMissingError(RuntimeError):
    """Raised when required model artifacts cannot be loaded from disk."""


class RelevanceClassifierService:
    """Service providing domain relevance prediction with dual-artifact fallback."""

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
        self.joblib_path = self.artifacts_dir / "relevance_model.joblib"
        self.weights_path = self.artifacts_dir / "relevance_model_weights.json"
        self.metadata_path = self.artifacts_dir / "relevance_metadata.json"

        self._joblib_pipeline: Any | None = None
        self._weights: dict[str, Any] | None = None
        self._available = False
        self._confidence_threshold: float = 0.60
        self._model_version: str = "relevance_lr_v1.0"

        self._load_artifacts()

    def _load_artifacts(self) -> None:
        if self.weights_path.is_file():
            try:
                w = json.loads(self.weights_path.read_text(encoding="utf-8"))
                self._confidence_threshold = float(w.get("confidence_threshold", 0.60))
                self._model_version = str(w.get("model_version", "relevance_lr_v1.0"))
            except Exception:  # pragma: no cover
                pass
        elif self.metadata_path.is_file():
            try:
                m = json.loads(self.metadata_path.read_text(encoding="utf-8"))
                self._model_version = str(
                    m.get("modelVersion", m.get("version", "relevance_lr_v1.0"))
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

    def get_metadata(self) -> RelevanceMetadataData:
        """Load and return model evaluation metadata."""
        if not self.metadata_path.is_file():
            raise ModelArtifactMissingError(f"Metadata artifact not found at {self.metadata_path}")

        try:
            raw = json.loads(self.metadata_path.read_text(encoding="utf-8"))
            metrics_raw = raw.get("metrics", {})
            metrics = RelevanceModelMetrics(
                f1Score=float(metrics_raw.get("f1Score", 0.0)),
                accuracy=float(metrics_raw.get("accuracy", 0.0)),
            )
            return RelevanceMetadataData(
                modelName=str(raw.get("modelName", "relevance_classifier")),
                version=str(raw.get("version", "1.0.0")),
                algorithm=str(raw.get("algorithm", "Unknown")),
                classes=list(raw.get("classes", ["relevant", "out_of_domain"])),
                metrics=metrics,
                isSynthetic=bool(raw.get("isSynthetic", True)),
            )
        except Exception as exc:  # pragma: no cover
            raise ModelArtifactMissingError(f"Failed to read metadata artifact: {exc}") from exc

    def predict(self, text: str) -> RelevancePredictData:
        """Classify customer input text as relevant or out_of_domain."""
        if not self._available:
            raise ModelArtifactMissingError(
                f"No usable model artifacts found in {self.artifacts_dir}"
            )

        stripped = text.strip()
        if not stripped:
            raise ValueError("Input text must not be empty.")

        if self._joblib_pipeline is not None:
            return self._predict_with_joblib(stripped)

        if self._weights is not None:
            return self._predict_with_portable_weights(stripped)

        raise ModelArtifactMissingError("Classifier model artifacts are unavailable.")

    def _predict_with_joblib(self, text: str) -> RelevancePredictData:
        pipeline = self._joblib_pipeline
        assert pipeline is not None

        classes = list(getattr(pipeline, "classes_", ["out_of_domain", "relevant"]))
        proba = pipeline.predict_proba([text])[0]
        prob_dict = {str(cls_name): float(p) for cls_name, p in zip(classes, proba, strict=False)}

        p_relevant = prob_dict.get("relevant", 0.0)
        p_out_of_domain = prob_dict.get("out_of_domain", 1.0 - p_relevant)

        threshold = self._confidence_threshold
        model_version = self._model_version

        is_relevant = p_relevant >= threshold
        label: RelevanceLabel = "relevant" if is_relevant else "out_of_domain"
        confidence = round(p_relevant if is_relevant else p_out_of_domain, 4)

        return RelevancePredictData(
            text=text,
            label=label,
            is_relevant=is_relevant,
            confidence=confidence,
            model_version=model_version,
        )

    def _predict_with_portable_weights(self, text: str) -> RelevancePredictData:
        weights = self._weights
        assert weights is not None

        vec_meta = weights["vectorizer"]
        vocab: dict[str, int] = vec_meta["vocabulary"]
        idf_list: list[float] = vec_meta["idf"]
        ngram_min, ngram_max = vec_meta.get("ngram_range", [1, 1])
        sublinear_tf: bool = bool(vec_meta.get("sublinear_tf", False))
        norm_type: str = str(vec_meta.get("norm", "l2"))

        # Tokenize and extract n-grams
        tokens = tokenize_indonesian_text(text)

        counts: dict[int, int] = {}
        n_tokens = len(tokens)
        for n in range(ngram_min, ngram_max + 1):
            for i in range(n_tokens - n + 1):
                ngram = " ".join(tokens[i : i + n])
                if ngram in vocab:
                    idx = vocab[ngram]
                    counts[idx] = counts.get(idx, 0) + 1

        # Calculate TF-IDF features
        features: dict[int, float] = {}
        for idx, count in counts.items():
            tf = (1.0 + math.log(count)) if (sublinear_tf and count > 0) else float(count)
            features[idx] = tf * idf_list[idx]

        # Apply vector normalization
        if norm_type == "l2" and features:
            sum_sq = sum(v * v for v in features.values())
            norm_val = math.sqrt(sum_sq)
            if norm_val > 0.0:
                features = {idx: v / norm_val for idx, v in features.items()}

        # Classification inference
        clf_meta = weights["classifier"]
        clf_type = clf_meta.get("type", "logistic_regression")
        threshold = self._confidence_threshold
        model_version = self._model_version

        if clf_type == "logistic_regression":
            coef: list[float] = clf_meta["coef"]
            intercept: float = float(clf_meta["intercept"])
            dot_product = sum(features[idx] * coef[idx] for idx in features if idx < len(coef))
            z = dot_product + intercept
            # Avoid overflow in exp
            if z >= 40.0:
                p_relevant = 1.0
            elif z <= -40.0:
                p_relevant = 0.0
            else:
                p_relevant = 1.0 / (1.0 + math.exp(-z))
            p_out_of_domain = 1.0 - p_relevant
        elif clf_type == "multinomial_nb":  # pragma: no cover
            feature_log_prob: list[list[float]] = clf_meta["feature_log_prob"]
            class_log_prior: list[float] = clf_meta["class_log_prior"]
            classes: list[str] = clf_meta.get("classes", ["out_of_domain", "relevant"])

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
            p_relevant = prob_map.get("relevant", 0.0)
            p_out_of_domain = prob_map.get("out_of_domain", 1.0 - p_relevant)
        else:  # pragma: no cover
            raise NotImplementedError(f"Unsupported classifier type: {clf_type}")

        is_relevant = p_relevant >= threshold
        label: RelevanceLabel = "relevant" if is_relevant else "out_of_domain"
        confidence = round(p_relevant if is_relevant else p_out_of_domain, 4)

        return RelevancePredictData(
            text=text,
            label=label,
            is_relevant=is_relevant,
            confidence=confidence,
            model_version=model_version,
        )
