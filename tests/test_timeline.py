import time
from backend.services.timeline import field_history, farm_events_timeline


def test_insufficient_data_is_reported_not_fabricated():
    now = time.time()
    sensors = [{'recorded_at': now - 100, 'soil_moisture': 40, 'temperature': 29, 'humidity': 55}]
    fh = field_history(sensors, [], window='24h', now=now)
    assert 'soil_moisture' in fh['insufficient_data_for']
    assert 'Not enough historical data' in fh['message']


def test_enough_points_are_not_flagged_insufficient():
    now = time.time()
    sensors = [
        {'recorded_at': now - 100, 'soil_moisture': 40, 'temperature': 29, 'humidity': 55},
        {'recorded_at': now - 200, 'soil_moisture': 41, 'temperature': 28, 'humidity': 54},
    ]
    fh = field_history(sensors, [], window='24h', now=now)
    assert 'soil_moisture' not in fh['insufficient_data_for']


def test_out_of_window_points_are_excluded():
    now = time.time()
    sensors = [{'recorded_at': now - 100000, 'soil_moisture': 40, 'temperature': 29, 'humidity': 55}]
    fh = field_history(sensors, [], window='24h', now=now)
    assert fh['series']['soil_moisture'] == []


def test_unknown_window_falls_back_to_24h():
    fh = field_history([], [], window='bogus')
    assert fh['window'] == '24h'


def test_timeline_merges_and_sorts_chronologically():
    now = time.time()
    obs = [{'created_at': now, 'result': {'health_status': 'GOOD', 'issue': 'healthy'}}]
    sensors = [{'recorded_at': now - 500, 'health': {'anomaly_detected': True}}]
    alerts = [{'created_at': now - 250, 'severity': 'HIGH', 'kind': 'water_stress'}]
    events = farm_events_timeline(obs, sensors, alerts, [])
    timestamps = [e['ts'] for e in events]
    assert timestamps == sorted(timestamps)
    assert any(e['kind'] == 'sensor_anomaly' for e in events)


def test_timeline_respects_limit():
    now = time.time()
    obs = [{'created_at': now - i, 'result': {'health_status': 'GOOD'}} for i in range(10)]
    events = farm_events_timeline(obs, [], [], [], limit=3)
    assert len(events) == 3
