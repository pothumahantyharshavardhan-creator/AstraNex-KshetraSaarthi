from backend.services.sensor_health import assess_sensors


def test_healthy_reading_has_no_anomalies():
    h = assess_sensors({'soil_moisture': 40, 'temperature': 29, 'humidity': 55})
    assert h['anomaly_detected'] is False
    assert h['anomalies'] == []


def test_impossible_value_is_flagged_invalid():
    h = assess_sensors({'soil_moisture': 250, 'temperature': 29, 'humidity': 55})
    assert h['sensors']['soil_moisture']['status'] == 'invalid'
    assert h['anomaly_detected'] is True
    assert any('outside the physically plausible range' in a for a in h['anomalies'])


def test_impossible_negative_temperature_is_flagged():
    h = assess_sensors({'soil_moisture': 40, 'temperature': -100, 'humidity': 55})
    assert h['sensors']['temperature']['status'] == 'invalid'


def test_missing_value_flagged_disconnected():
    h = assess_sensors({'soil_moisture': 40, 'temperature': None, 'humidity': 55})
    assert h['sensors']['temperature']['status'] == 'disconnected'
    assert h['anomaly_detected'] is True


def test_sudden_jump_flagged_noisy():
    h = assess_sensors({'soil_moisture': 85, 'temperature': 30, 'humidity': 60},
                        previous={'soil_moisture': 30, 'temperature': 30, 'humidity': 60})
    assert h['sensors']['soil_moisture']['status'] == 'noisy'


def test_repeated_identical_readings_flagged_stuck():
    history = [{'soil_moisture': 40.0}, {'soil_moisture': 40.0}, {'soil_moisture': 40.0}]
    h = assess_sensors({'soil_moisture': 40.0, 'temperature': 29, 'humidity': 55}, recent_history=history)
    assert h['sensors']['soil_moisture']['status'] == 'stuck'
    assert h['overall'] < 1.0


def test_out_of_order_timestamp_reduces_overall_score():
    h = assess_sensors({'soil_moisture': 40, 'temperature': 29, 'humidity': 55, 'recorded_at': 100},
                        previous={'soil_moisture': 40, 'temperature': 29, 'humidity': 55, 'recorded_at': 200})
    assert h['overall'] < 1.0
    assert any('out-of-order' in a.lower() for a in h['anomalies'])


def test_non_numeric_value_is_flagged_not_silently_used():
    h = assess_sensors({'soil_moisture': 'not-a-number', 'temperature': 29, 'humidity': 55})
    assert h['sensors']['soil_moisture']['status'] == 'invalid'
