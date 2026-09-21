"""FastAPI router for the experimental quantum layer (mounted at /api/quantum).

All endpoints return HTTP 200 with an ``available`` flag rather than raising, so
a browser client can degrade gracefully and keep showing classical results.
"""
from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..engine import AnalysisInput, analyze_field
from . import benchmark as bench
from . import pipeline
from .feature_encoder import FEATURE_LABELS, FEATURE_NAMES, FEATURE_SOURCES

router = APIRouter(prefix="/api/quantum", tags=["quantum"])


class QuantumAnalyzeRequest(BaseModel):
    crop: str = "tomato"
    condition: str = "healthy"
    field_id: Optional[int] = None
    growth_stage: str = "vegetative"
    soil_moisture: float = Field(45, ge=0, le=100)
    temperature: float = Field(29, ge=-20, le=70)
    humidity: float = Field(55, ge=0, le=100)
    weather: str = "normal"
    recent_rainfall_mm: float = Field(0, ge=0, le=500)
    recent_irrigation_hours: float = Field(24, ge=0, le=720)
    sensor_reliability: float = Field(1, ge=0, le=1)
    image_quality: float = Field(1, ge=0, le=1)
    observation_id: Optional[int] = None
    persist: bool = True


class TrainRequest(BaseModel):
    dataset_size: int = Field(360, ge=80, le=1200)
    iterations: int = Field(120, ge=10, le=300)
    background: bool = True


@router.get("/status")
def status() -> dict[str, Any]:
    try:
        return pipeline.quantum_status()
    except Exception as exc:
        return {"available": False, "error": type(exc).__name__,
                "message": "Quantum layer unavailable. Classical agricultural analysis continues normally."}


@router.get("/features")
def features() -> dict[str, Any]:
    st = pipeline.quantum_status()
    return {
        "training_required": not bool(st.get("models_trained")),
        "features": [{"feature": f, "label": FEATURE_LABELS[f], "source": FEATURE_SOURCES[f]}
                     for f in FEATURE_NAMES],
        "selected": st.get("selected_features", []),
        "note": "Features are produced by the existing AstraNex vision, sensor and risk pipeline.",
    }


@router.get("/circuit")
def circuit(a0: float | None = None, a1: float | None = None,
            a2: float | None = None, a3: float | None = None) -> dict[str, Any]:
    try:
        angles = None
        provided = [a0, a1, a2, a3]
        if all(v is not None for v in provided):
            angles = [float(v) for v in provided]  # type: ignore[arg-type]
        return {"available": True, **pipeline.circuit_blueprint(angles)}
    except Exception as exc:
        return {"available": False, "error": type(exc).__name__,
                "message": "Circuit blueprint unavailable."}


@router.get("/feature-ranges")
def feature_ranges() -> dict[str, Any]:
    """Selected features and their physical ranges (drives the playground sliders)."""
    try:
        return {"available": True, **pipeline.feature_ranges()}
    except Exception as exc:
        return {"available": False, "error": type(exc).__name__}


@router.get("/simulate")
def simulate(x0: float, x1: float, x2: float, x3: float, shots: int = 1024,
             seed: int | None = None) -> dict[str, Any]:
    """Run the circuit on hand-chosen normalised features (0..1) and return the exact
    Bloch vectors, entanglement, probabilities, finite-shot counts and a noise sweep.
    Nothing is stored and no farmer data is involved."""
    if not 1 <= shots <= 20000:
        raise HTTPException(422, "shots must be between 1 and 20000")
    for v in (x0, x1, x2, x3):
        if v != v or v < 0 or v > 1:
            raise HTTPException(422, "feature values must be between 0 and 1")
    try:
        return pipeline.simulate([x0, x1, x2, x3], shots=shots, seed=seed)
    except Exception as exc:
        return {"available": False, "error": type(exc).__name__,
                "message": "Simulation unavailable. Classical agricultural analysis is unaffected."}


@router.get("/feature-sensitivity")
def feature_sensitivity(x0: float, x1: float, x2: float, x3: float, delta: float = 0.15,
                         shots: int = 256) -> dict[str, Any]:
    """Experimental circuit-sensitivity sweep (v3.3, spec section 22).

    NOT scientific feature importance — see the ``disclaimer`` field in the response.
    """
    if not 1 <= shots <= 5000:
        raise HTTPException(422, "shots must be between 1 and 5000")
    if not 0.01 <= delta <= 0.5:
        raise HTTPException(422, "delta must be between 0.01 and 0.5")
    for v in (x0, x1, x2, x3):
        if v != v or v < 0 or v > 1:
            raise HTTPException(422, "feature values must be between 0 and 1")
    try:
        from . import feature_sensitivity as fs
        return fs.feature_sensitivity([x0, x1, x2, x3], delta=delta, shots=shots)
    except Exception as exc:
        return {"available": False, "error": type(exc).__name__,
                "message": "Feature-sensitivity experiment unavailable. Classical agricultural analysis is unaffected."}


@router.post("/analyze")
def analyze(req: QuantumAnalyzeRequest) -> dict[str, Any]:
    """Run the classical engine, then the experimental hybrid layer over it."""
    payload = req.model_dump()
    engine_input = AnalysisInput(**{k: v for k, v in payload.items()
                                   if k in AnalysisInput.__dataclass_fields__})
    classical = analyze_field(engine_input)
    quantum = pipeline.hybrid_analyze(classical, payload)
    if req.persist and quantum.get("available"):
        try:
            from ..db import save_quantum_run
            save_quantum_run({
                "observation_id": req.observation_id,
                "field_id": req.field_id,
                "feature_vector": {f["feature"]: f["normalised"] for f in quantum["features"]["vector"]},
                "selected_features": quantum["features"]["selected"],
                "classical_prediction": quantum["classical"]["risk_probability"],
                "quantum_prediction": quantum["quantum"]["risk_probability"],
                "confidence": classical.get("confidence"),
                "qubits": quantum["circuit"]["qubits"],
                "circuit_depth": quantum["circuit"].get("depth") or quantum["circuit"]["layers"],
                "backend": quantum["circuit"]["backend"],
                "execution_ms": quantum["quantum"]["inference_ms"],
                "warning_level": quantum["early_warning"]["level"],
            })
        except Exception:
            pass
    return {"classical_analysis": classical, "quantum": quantum}


@router.post("/analyze-result")
def analyze_result(body: dict[str, Any]) -> dict[str, Any]:
    """Run the hybrid layer over an analysis result the client already has."""
    result = body.get("result") or body.get("classical_analysis") or {}
    raw = body.get("raw") or body.get("payload") or {}
    return {"quantum": pipeline.hybrid_analyze(result, raw)}


@router.get("/benchmark")
def get_benchmark() -> dict[str, Any]:
    saved = bench.load_result()
    if not saved:
        return bench.awaiting_payload()
    saved["training_state"] = pipeline.training_state()
    return saved


@router.post("/benchmark")
def run_benchmark(req: TrainRequest) -> dict[str, Any]:
    try:
        if req.background:
            started = pipeline.train_in_background(req.dataset_size, req.iterations)
            return {"ok": True, **started, "training_state": pipeline.training_state()}
        out = pipeline.train_now(req.dataset_size, req.iterations)
        return out
    except Exception as exc:
        return {"ok": False, "status": "failed", "error": type(exc).__name__,
                "message": "Experimental benchmark could not be started. Classical analysis is unaffected."}


@router.get("/training")
def training() -> dict[str, Any]:
    return pipeline.training_state()


@router.get("/health")
def health() -> dict[str, Any]:
    """Consolidated, honestly-reported status of every quantum subsystem (§54)."""
    try:
        return pipeline.system_health()
    except Exception as exc:
        return {"overall": "unknown", "error": type(exc).__name__,
                "message": "Health check failed. Classical agricultural analysis is unaffected."}


@router.get("/provenance")
def provenance() -> dict[str, Any]:
    """Where every displayed number actually came from (§55)."""
    try:
        return pipeline.model_provenance()
    except Exception as exc:
        return {"available": False, "error": type(exc).__name__}


@router.get("/runs")
def runs(limit: int = 25) -> dict[str, Any]:
    try:
        from ..db import list_quantum_runs
        return {"items": list_quantum_runs(max(1, min(limit, 100)))}
    except Exception:
        return {"items": []}
