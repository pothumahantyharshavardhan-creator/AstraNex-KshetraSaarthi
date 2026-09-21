"""Classical baseline model.

Trained on exactly the same selected feature vector as the quantum classifier,
with the same train/test split, so the comparison shown in the UI is a fair
like-for-like experiment rather than a marketing chart.

Implementation is a dependency-free logistic regression (batch gradient descent
with L2 regularisation). If scikit-learn is installed it is used instead, and the
implementation actually used is reported in the model metadata.
"""
from __future__ import annotations

import json
import math
import time
from pathlib import Path
from typing import Any, Sequence

MODEL_FILE = Path(__file__).resolve().parent / "trained_baseline.json"

SKLEARN_AVAILABLE = False
try:  # pragma: no cover - environment dependent
    from sklearn.linear_model import LogisticRegression  # type: ignore

    SKLEARN_AVAILABLE = True
except Exception:  # pragma: no cover
    LogisticRegression = None  # type: ignore


def _sigmoid(z: float) -> float:
    if z >= 0:
        return 1.0 / (1.0 + math.exp(-min(z, 60)))
    e = math.exp(max(z, -60))
    return e / (1.0 + e)


class ClassicalBaseline:
    """Logistic regression over the selected agricultural features."""

    def __init__(self, seed: int = 3):
        self.weights: list[float] = []
        self.bias: float = 0.0
        self.trained = False
        self.seed = seed
        self.implementation = "scikit-learn" if SKLEARN_AVAILABLE else "bundled gradient descent"
        self.training_info: dict[str, Any] = {}
        self.features: list[str] = []
        self._sk = None

    def fit(self, X: Sequence[Sequence[float]], y: Sequence[int], *, epochs: int = 400,
            lr: float = 0.65, l2: float = 1e-3) -> dict[str, Any]:
        started = time.perf_counter()
        n_features = len(X[0]) if X else 0
        if SKLEARN_AVAILABLE:  # pragma: no cover - environment dependent
            self._sk = LogisticRegression(max_iter=2000, random_state=self.seed)
            self._sk.fit([list(r) for r in X], list(y))
            self.weights = [float(w) for w in self._sk.coef_[0]]
            self.bias = float(self._sk.intercept_[0])
        else:
            self.weights = [0.0] * n_features
            self.bias = 0.0
            n = max(1, len(X))
            for _ in range(epochs):
                gw = [0.0] * n_features
                gb = 0.0
                for row, label in zip(X, y):
                    p = _sigmoid(self.bias + sum(w * v for w, v in zip(self.weights, row)))
                    err = p - label
                    for j, v in enumerate(row):
                        gw[j] += err * v
                    gb += err
                self.weights = [w - lr * (g / n + l2 * w) for w, g in zip(self.weights, gw)]
                self.bias -= lr * gb / n
        self.trained = True
        loss = self._log_loss(X, y)
        self.training_info = {
            "implementation": self.implementation,
            "model": "Logistic regression",
            "epochs": epochs if not SKLEARN_AVAILABLE else None,
            "samples": len(X),
            "final_loss": round(loss, 5),
            "training_seconds": round(time.perf_counter() - started, 3),
        }
        return self.training_info

    def _log_loss(self, X: Sequence[Sequence[float]], y: Sequence[int]) -> float:
        if not X:
            return 0.0
        total = 0.0
        for row, label in zip(X, y):
            p = min(max(self.predict_proba(row), 1e-7), 1 - 1e-7)
            total += -(label * math.log(p) + (1 - label) * math.log(1 - p))
        return total / len(X)

    def predict_proba(self, row: Sequence[float]) -> float:
        return _sigmoid(self.bias + sum(w * v for w, v in zip(self.weights, row)))

    def predict(self, row: Sequence[float], threshold: float = 0.5) -> int:
        return int(self.predict_proba(row) >= threshold)

    def coefficients(self) -> list[dict[str, Any]]:
        names = self.features or [f"f{i + 1}" for i in range(len(self.weights))]
        return [{"feature": n, "weight": round(w, 4)} for n, w in zip(names, self.weights)]

    # -- persistence -------------------------------------------------------
    def to_dict(self) -> dict[str, Any]:
        return {"weights": self.weights, "bias": self.bias, "trained": self.trained,
                "training_info": self.training_info, "features": self.features,
                "implementation": self.implementation, "saved_at": time.time()}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ClassicalBaseline":
        m = cls()
        m.weights = [float(x) for x in data.get("weights", [])]
        m.bias = float(data.get("bias", 0.0))
        m.trained = bool(data.get("trained", False))
        m.training_info = data.get("training_info", {})
        m.features = list(data.get("features", []))
        m.implementation = data.get("implementation", m.implementation)
        return m

    def save(self, path: Path | str = MODEL_FILE) -> None:
        Path(path).write_text(json.dumps(self.to_dict(), indent=1), encoding="utf-8")

    @classmethod
    def load(cls, path: Path | str = MODEL_FILE) -> "ClassicalBaseline | None":
        p = Path(path)
        if not p.exists():
            return None
        try:
            return cls.from_dict(json.loads(p.read_text(encoding="utf-8")))
        except Exception:
            return None
