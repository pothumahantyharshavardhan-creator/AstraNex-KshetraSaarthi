"""Demo Mode (v3.3, spec sections 29-31).

Demo scenarios run the real analysis engine in-memory — the same
`backend.engine.analyze_field` a live sensor reading would go through — but
never write to the real database, so RESET DEMO has nothing to undo and no
demo reading can ever be confused with real farmer data. Every scenario
result is tagged ``"demo": True`` and every field/value used is labelled
DEMO DATA wherever it's displayed.
"""
from __future__ import annotations
from ..engine import AnalysisInput, analyze_field

SCENARIOS = {
    1: {
        "title": "Healthy field",
        "description": "A well-watered, disease-free tomato field under normal conditions.",
        "input": AnalysisInput(crop="tomato", condition="healthy", soil_moisture=55, temperature=27, humidity=55, growth_stage="vegetative"),
    },
    2: {
        "title": "Low moisture",
        "description": "Soil moisture has dropped below the configured threshold during fruiting.",
        "input": AnalysisInput(crop="tomato", condition="healthy", soil_moisture=18, temperature=31, humidity=40, growth_stage="fruiting"),
    },
    3: {
        "title": "Disease-risk image",
        "description": "A plant image with a visual pattern consistent with early blight, in a humid context.",
        "input": AnalysisInput(crop="tomato", condition="diseaseA", soil_moisture=62, temperature=28, humidity=78, growth_stage="vegetative"),
    },
    4: {
        "title": "Sensor anomaly",
        "description": "A soil-moisture sensor reporting an impossible value.",
        "input": AnalysisInput(crop="tomato", condition="healthy", soil_moisture=45, temperature=29, humidity=55, sensor_reliability=0.2),
        "sensor_anomaly_demo": {"soil_moisture": 187, "temperature": 29, "humidity": 55},
    },
    5: {
        "title": "Environmental stress",
        "description": "Extreme heat combined with low humidity during flowering.",
        "input": AnalysisInput(crop="tomato", condition="healthy", soil_moisture=38, temperature=39, humidity=18, growth_stage="flowering"),
    },
    6: {
        "title": "Quantum analysis",
        "description": "A representative feature vector for the experimental quantum layer's Quantum Lab.",
        "input": AnalysisInput(crop="tomato", condition="diseaseB", soil_moisture=58, temperature=33, humidity=62, growth_stage="fruiting"),
    },
}


def list_scenarios() -> list[dict]:
    return [{"id": sid, "title": s["title"], "description": s["description"], "demo": True} for sid, s in SCENARIOS.items()]


def run_scenario(scenario_id: int) -> dict:
    scenario = SCENARIOS.get(scenario_id)
    if scenario is None:
        return {"available": False, "demo": True, "message": f"No demo scenario #{scenario_id}. Valid ids: {sorted(SCENARIOS)}."}
    result = analyze_field(scenario["input"])
    result["demo"] = True
    result["demo_scenario"] = {"id": scenario_id, "title": scenario["title"], "description": scenario["description"]}
    if "sensor_anomaly_demo" in scenario:
        from .sensor_health import assess_sensors
        result["demo_sensor_health"] = assess_sensors(scenario["sensor_anomaly_demo"])
    return result


def reset() -> dict:
    """Demo scenarios are computed in-memory and never persisted, so there is
    nothing to delete — this call exists to give the UI an explicit, honest
    RESET DEMO action rather than silently doing nothing."""
    return {"ok": True, "demo": True, "message": "Demo state reset. No real farmer data was touched (demo scenarios are never persisted)."}
