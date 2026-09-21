"""AstraNex — KshetraSaarthi experimental quantum machine-learning layer.

This package adds a hybrid classical-quantum experimental layer on top of the
existing AstraNex agricultural intelligence engine. It never replaces the
classical pipeline: every entry point degrades safely so that field analysis
continues if Qiskit, NumPy or a trained model is unavailable.

Modules
-------
feature_encoder    Multimodal agricultural feature extraction, normalisation,
                   selection and angle encoding.
quantum_classifier Variational quantum classifier (Qiskit when installed,
                   bundled state-vector fallback otherwise).
classical_baseline Logistic-regression baseline on the *same* features.
dataset            Reproducible experimental dataset built from the existing
                   AstraNex rule engine (clearly labelled as demonstration data).
benchmark          Real train/test evaluation of both models.
quantum_state      Bloch vectors, entanglement, shot sampling, noise model, true circuit depth.
pipeline           End-to-end hybrid analysis used by the API layer.
api                FastAPI router mounted at /api/quantum.
"""
from .feature_encoder import (
    FEATURE_NAMES,
    extract_features,
    normalise_features,
    to_angles,
    select_features,
    feature_report,
)
from .quantum_classifier import QuantumClassifier, quantum_runtime_status
from .classical_baseline import ClassicalBaseline
from .pipeline import hybrid_analyze, quantum_status, circuit_blueprint

__all__ = [
    "FEATURE_NAMES", "extract_features", "normalise_features", "to_angles",
    "select_features", "feature_report", "QuantumClassifier", "ClassicalBaseline",
    "quantum_runtime_status", "hybrid_analyze", "quantum_status", "circuit_blueprint",
]

__version__ = "3.2.0-qff"
