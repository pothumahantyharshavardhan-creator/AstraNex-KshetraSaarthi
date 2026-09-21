"""API tests.

Skipped automatically when FastAPI's test client stack (fastapi + httpx) is not
installed, so the rest of the suite still runs in a minimal environment.
"""
import pytest

fastapi = pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from backend.main import app  # noqa: E402

client = TestClient(app)


# ---------------- existing endpoints must keep working ----------------
def test_health_reports_service_and_quantum_state():
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert "quantum" in body


def test_existing_analyze_contract_is_unchanged():
    r = client.post("/api/analyze", json={"crop": "tomato", "condition": "diseaseA",
                                          "soil_moisture": 70, "humidity": 82, "temperature": 29})
    assert r.status_code == 200
    body = r.json()
    for key in ("issue", "confidence", "risks", "risk_bands", "health_score",
                "recommendation", "irrigation", "evidence", "guardrails"):
        assert key in body


def test_history_and_alerts_still_respond():
    assert client.get("/api/history").status_code == 200
    assert client.get("/api/alerts").status_code == 200
    assert client.get("/api/fields").status_code == 200


def test_sensor_ingest_and_validation():
    r = client.post("/api/sensors", json={"device_id": "test-esp32", "soil_moisture": 40,
                                          "temperature": 28, "humidity": 60})
    assert r.status_code == 200
    assert r.json()["ok"] is True
    assert client.get("/api/validation").status_code == 200


def test_frontend_and_legacy_are_both_served():
    assert client.get("/").status_code == 200
    assert client.get("/legacy").status_code in (200, 404)  # 404 only if legacy file removed


# ---------------- quantum endpoints ----------------
def test_quantum_status_endpoint():
    body = client.get("/api/quantum/status").json()
    assert body["available"] is True
    assert body["runtime"]["hardware_execution"] is False


def test_quantum_circuit_endpoint_returns_gates():
    body = client.get("/api/quantum/circuit").json()
    assert body["available"] is True
    assert body["qubits"] == 4
    assert len(body["qubit_map"]) == 4
    assert any(op["kind"] == "encoding" for op in body["operations"])


def test_quantum_analyze_returns_both_models():
    r = client.post("/api/quantum/analyze", json={"crop": "paddy", "condition": "diseaseA",
                                                  "soil_moisture": 72, "humidity": 86,
                                                  "temperature": 30, "persist": False})
    assert r.status_code == 200
    body = r.json()
    assert "classical_analysis" in body
    q = body["quantum"]
    if q.get("available"):
        assert "not Qiskit execution" in q["quantum"]["backend"] or q["quantum"]["backend"].startswith("Qiskit")
    else:
        assert q["status"] in {"model_unavailable", "model_validation_failed"}
        assert q["inference_enabled"] is False
    assert q["early_warning"]["level"] in {"STABLE", "MONITOR", "EARLY WARNING"}


def test_quantum_benchmark_is_never_fabricated():
    body = client.get("/api/quantum/benchmark").json()
    if body["status"] == "awaiting_benchmark":
        assert body["display"] == "Awaiting experimental benchmark"
        assert all(v is None for v in body["quantum"]["metrics"].values())
    else:
        assert "Demonstration" in body["evaluation_label"]
        assert body["quantum"]["metrics"]["accuracy"] is not None


def test_quantum_failure_does_not_break_classical_analysis(monkeypatch):
    """If the quantum layer raises, /api/analyze must still succeed."""
    from backend.quantum import pipeline

    def boom(*a, **k):
        raise RuntimeError("simulated quantum failure")

    monkeypatch.setattr(pipeline, "_ensure_models", boom)
    out = pipeline.hybrid_analyze({"risks": {"disease": 50}}, {})
    assert out["available"] is False
    assert "Classical agricultural analysis continues normally" in out["message"]

    r = client.post("/api/analyze", json={"crop": "tomato", "condition": "healthy"})
    assert r.status_code == 200
    assert "risks" in r.json()


# ---------------- demo and institutional endpoints ----------------
def test_demo_fields_are_labelled_as_simulation():
    body = client.get("/api/demo/fields").json()
    assert body["data_label"] == "Simulation Data"
    assert len(body["items"]) >= 1
    assert "analysis" in body["items"][0]


def test_analytics_summary_shape():
    body = client.get("/api/analytics/summary").json()
    assert "distributions" in body and "warnings" in body
    assert "Simulation" in body["data_label"] or "prototype" in body["data_label"].lower()


def test_insurer_view_makes_no_financial_recommendation():
    body = client.get("/api/insurer/evidence").json()
    assert "disclaimer" in body
    assert "no financial" in body["disclaimer"].lower()


def test_status_endpoint_reports_backend_provenance():
    body = client.get("/api/quantum/status").json()
    rt = body["runtime"]
    assert rt["mode"] in {"qiskit_machine_learning", "qiskit_statevector", "fallback_simulation"}
    assert "execution_label" in rt
    if not rt["qiskit_execution"]:
        assert "not Qiskit execution" in rt["execution_label"]


def test_health_reports_quantum_execution_mode():
    q = client.get("/api/health").json()["quantum"]
    if q.get("available"):
        assert q["mode"] in {"qiskit_machine_learning", "qiskit_statevector", "fallback_simulation"}
        assert "execution_label" in q


# ---------------- system health and provenance (§54, §55) ----------------
def test_system_health_endpoint_reports_every_component():
    body = client.get("/api/system/health").json()
    assert body["overall"] in {"ok", "degraded"}
    for key in ("backend", "database", "vision_model", "sensor_system",
                "weather_context", "offline_queue_and_sync", "qiskit",
                "qiskit_machine_learning", "classical_model", "qml_model", "benchmark"):
        assert key in body["components"], key
        assert "ok" in body["components"][key]


def test_system_health_database_component_is_real():
    body = client.get("/api/system/health").json()
    assert body["components"]["database"]["ok"] is True


def test_quantum_health_endpoint():
    body = client.get("/api/quantum/health").json()
    assert body["overall"] in {"ok", "degraded"}
    assert "qiskit" in body["components"]


def test_model_provenance_endpoint_never_invents_qiskit():
    body = client.get("/api/quantum/provenance").json()
    qm = body["quantum_model"]
    assert qm["engine"] in {"qiskit_machine_learning", "builtin_vqc"}
    if qm["engine"] != "qiskit_machine_learning":
        assert qm["feature_map"] != "ZZFeatureMap"
    assert body["quantum_advantage_claimed"] is False
    assert "Not field validated" in body["validation"]


# ---------------- database isolation (§37) ----------------
def test_database_endpoints_work_with_no_manual_setup():
    """This is the regression test for §37: a bare `pytest` run, with no
    developer having pre-created backend/astranex.db, must still pass."""
    for path in ("/api/history", "/api/alerts", "/api/fields", "/api/sensors/latest"):
        r = client.get(path)
        assert r.status_code == 200, path


def test_invalid_field_id_is_rejected_before_database_write():
    r = client.post('/api/analyze', json={'field_id': 999999, 'crop': 'tomato', 'condition': 'healthy'})
    assert r.status_code == 422


def test_duplicate_client_event_is_idempotent_and_does_not_duplicate_alerts():
    event = 'idempotency-test-001'
    before = len(client.get('/api/alerts').json()['items'])
    payload = {'field_id': 1, 'crop': 'tomato', 'condition': 'diseaseA',
               'soil_moisture': 70, 'humidity': 85, 'temperature': 29,
               'client_event_id': event}
    first = client.post('/api/analyze', json=payload)
    second = client.post('/api/analyze', json=payload)
    assert first.status_code == second.status_code == 200
    assert first.json()['observation_id'] == second.json()['observation_id']
    after = len(client.get('/api/alerts').json()['items'])
    assert after - before == 1


def test_invalid_image_bytes_are_rejected():
    r = client.post('/api/analyze-image', files={'file': ('fake.jpg', b'not-an-image', 'image/jpeg')})
    assert r.status_code == 422


def test_sync_batch_limit_and_alert_path():
    payload = {'field_id': 1, 'crop': 'tomato', 'condition': 'diseaseA',
               'soil_moisture': 70, 'humidity': 85, 'temperature': 29,
               'client_event_id': 'sync-idempotency-001'}
    r = client.post('/api/sync', json=[payload])
    assert r.status_code == 200
    assert r.json()['synced'] == 1

# ---------------- location hardening ----------------
def test_selected_location_is_persisted_in_analysis_result():
    r = client.post('/api/analyze', json={
        'crop':'paddy','condition':'healthy','latitude':18.6224,'longitude':84.1444,
        'location_name':'Srikakulam, Andhra Pradesh, India'
    })
    assert r.status_code == 200
    loc = r.json()['location']
    assert loc['latitude'] == 18.6224
    assert loc['longitude'] == 84.1444
    assert 'Srikakulam' in loc['name']


def test_partial_location_is_rejected():
    r = client.post('/api/analyze', json={'crop':'tomato','condition':'healthy','latitude':18.6})
    assert r.status_code == 422


def test_outside_india_location_is_rejected():
    r = client.post('/api/analyze', json={'crop':'tomato','condition':'healthy','latitude':51.5,'longitude':-0.1})
    assert r.status_code == 422


def test_readiness_exposes_explicit_release_gates():
    body = client.get('/api/readiness').json()
    assert body['demo_ready'] is True
    assert body['checks']['location_services']['ready'] is True
    assert 'field_validation_dataset' in body['checks']


# ---------------- v3.2 regression tests ----------------
def test_sync_isolates_invalid_records_and_keeps_location():
    good = {"crop": "tomato", "condition": "healthy", "client_event_id": "v32-good-1",
            "latitude": 17.385, "longitude": 78.487, "location_name": "Hyderabad"}
    bad_field = {"crop": "tomato", "condition": "healthy", "client_event_id": "v32-bad-field", "field_id": 99999}
    bad_shape = {"crop": "tomato", "soil_moisture": "not-a-number", "client_event_id": "v32-bad-shape"}
    r = client.post("/api/sync", json=[good, bad_field, bad_shape])
    assert r.status_code == 200                      # one bad record must NOT reject the batch
    body = r.json()
    assert body["synced"] == 1 and len(body["failed"]) == 2 and body["ok"] is False
    by_event = {f["client_event_id"]: f for f in body["failed"]}
    assert by_event["v32-bad-field"]["retryable"] is False and by_event["v32-bad-shape"]["retryable"] is False
    stored = client.get("/api/history", params={"limit": 50}).json()["items"]
    mine = [o for o in stored if o.get("client_event_id") == "v32-good-1"]
    assert mine and mine[0]["result"]["location"]["latitude"] == 17.385      # location used to be dropped on sync
    again = client.post("/api/sync", json=[good]).json()                     # replay is idempotent
    assert again["observation_ids"] == body["observation_ids"]


def test_sensor_uptime_timestamp_is_not_stored_as_epoch():
    r = client.post("/api/sensors", json={"device_id": "esp32-uptime", "field_id": 1, "soil_moisture": 40,
                                          "temperature": 30, "humidity": 60, "timestamp": 15.0})   # millis()/1000 after 15 s
    assert r.status_code == 200
    rows = client.get("/api/sensors/latest", params={"limit": 5}).json()["items"]
    row = next(x for x in rows if x["device_id"] == "esp32-uptime")
    assert row["recorded_at"] > 1_000_000_000


def test_sensor_jump_is_flagged_noisy_using_previous_reading():
    client.post("/api/sensors", json={"device_id": "esp32-noisy", "field_id": 1, "soil_moisture": 30, "temperature": 30, "humidity": 60})
    r = client.post("/api/sensors", json={"device_id": "esp32-noisy", "field_id": 1, "soil_moisture": 85, "temperature": 30, "humidity": 60})
    assert r.json()["sensor_health"]["sensors"]["soil_moisture"]["status"] == "noisy"


def test_simulate_endpoint_contract_and_validation():
    ok = client.get("/api/quantum/simulate", params={"x0": 0.8, "x1": 0.6, "x2": 0.4, "x3": 0.5, "shots": 256, "seed": 9})
    assert ok.status_code == 200
    body = ok.json()
    assert body["available"] is True and len(body["state"]["qubits"]) == 4
    assert body["state"]["shots"]["shots"] == 256
    assert client.get("/api/quantum/simulate", params={"x0": 1.5, "x1": 0, "x2": 0, "x3": 0}).status_code == 422
    assert client.get("/api/quantum/simulate", params={"x0": 0.5, "x1": 0.5, "x2": 0.5, "x3": 0.5, "shots": 0}).status_code == 422
    fr = client.get("/api/quantum/feature-ranges").json()
    assert fr["available"] is True and len(fr["features"]) == 4


def test_benchmark_endpoint_is_usable_in_every_mode():
    body = client.get("/api/quantum/benchmark").json()
    assert body["status"] in {"complete", "awaiting_benchmark"}
    if body["status"] == "complete":
        assert body["mode"] in {"fallback_simulation", "qiskit_statevector", "qiskit_machine_learning"}
        assert isinstance(body["qiskit_execution"], bool)


def test_oversized_image_dimensions_are_rejected():
    io = pytest.importorskip("io")
    PIL = pytest.importorskip("PIL.Image")
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (6000, 6000), (30, 120, 40)).save(buf, "PNG")      # 36 MP but tiny on disk
    data = buf.getvalue()
    if len(data) > 2 * 1024 * 1024:
        pytest.skip("test image unexpectedly large")
    r = client.post("/api/analyze-multimodal", files={"file": ("big.png", data, "image/png")}, data={"crop": "tomato"})
    assert r.status_code == 413


def test_geocode_results_are_cached(monkeypatch):
    import json as _json
    import urllib.request as ur
    from backend import main as m
    calls = {"n": 0}

    class Resp:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def read(self): calls["n"] += 1; return _json.dumps([{"display_name": "X", "lat": "17", "lon": "78"}]).encode()

    monkeypatch.setattr(ur, "urlopen", lambda *a, **k: Resp())
    m._GEO_CACHE.clear()
    a = client.get("/api/geocode/search", params={"q": "cache-test-place"}).json()
    b = client.get("/api/geocode/search", params={"q": "cache-test-place"}).json()
    assert a == b and calls["n"] == 1


def test_health_reports_current_version():
    assert client.get("/api/health").json()["version"] == "3.3.0"


# ---------------- v3.3 additions ----------------
def test_crops_endpoint_lists_seeded_profiles():
    items = client.get("/api/crops").json()["items"]
    names = {c["crop"] for c in items}
    assert {"tomato", "wheat", "rice"} <= names


def test_analyze_result_includes_data_quality_and_alerts():
    r = client.post("/api/analyze", json={"crop": "tomato", "condition": "healthy",
                                           "soil_moisture": 45, "temperature": 29, "humidity": 55}).json()
    assert "data_quality" in r and r["data_quality"]["label"] == "data_quality"
    assert "alerts" in r and "alert_level" in r


def test_field_history_reports_insufficient_data_honestly():
    r = client.get("/api/field-history", params={"window": "24h"}).json()
    assert "insufficient_data_for" in r
    assert r["window"] == "24h"


def test_timeline_endpoint_responds():
    r = client.get("/api/timeline")
    assert r.status_code == 200
    assert "items" in r.json()


def test_weather_endpoint_never_crashes_and_degrades_gracefully():
    r = client.get("/api/weather", params={"latitude": 12.9, "longitude": 77.6}).json()
    assert r["available"] is False
    assert "unavailable" in r["message"].lower()


def test_demo_scenarios_are_labelled_and_never_touch_real_history():
    before = len(client.get("/api/history").json()["items"])
    scenarios = client.get("/api/demo/scenarios").json()["items"]
    assert len(scenarios) == 6
    assert all(s["demo"] is True for s in scenarios)
    run = client.post("/api/demo/run/2").json()
    assert run["demo"] is True
    assert "moisture" in " ".join(run["reason"]).lower() or run["risks"]["water"] > 0
    after = len(client.get("/api/history").json()["items"])
    assert before == after  # demo scenarios must never write to real observation history


def test_demo_invalid_scenario_id_is_handled_not_500():
    r = client.post("/api/demo/run/999")
    assert r.status_code == 200
    assert r.json()["available"] is False


def test_demo_reset_never_errors():
    r = client.post("/api/demo/reset")
    assert r.status_code == 200 and r.json()["ok"] is True


def test_sensor_anomaly_creates_a_structured_alert():
    client.post("/api/sensors", json={"device_id": "esp32-anomaly-test", "field_id": 1,
                                       "soil_moisture": 999, "temperature": 29, "humidity": 55})
    alerts = client.get("/api/alerts").json()["items"]
    assert any(a["kind"] == "sensor_anomaly" for a in alerts)


def test_quantum_feature_sensitivity_endpoint_degrades_gracefully():
    r = client.get("/api/quantum/feature-sensitivity",
                    params={"x0": 0.5, "x1": 0.5, "x2": 0.5, "x3": 0.5})
    assert r.status_code == 200
    body = r.json()
    assert body.get("available") is False or "disclaimer" in body
