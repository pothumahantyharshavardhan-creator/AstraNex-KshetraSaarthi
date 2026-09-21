from backend.services.data_quality import compute_data_quality


def test_complete_recent_consistent_reading_is_good():
    dq = compute_data_quality(
        {'soil_moisture': 45, 'temperature': 29, 'humidity': 55, 'weather': 'normal', 'recent_rainfall_mm': 0},
        sensor_reliability=1.0, image_quality=1.0, recorded_at=1000.0, now=1000.0 + 60,
    )
    assert dq['band'] == 'GOOD'
    assert dq['score'] >= 80
    assert dq['label'] == 'data_quality'


def test_missing_fields_reduce_completeness_and_are_named():
    dq = compute_data_quality({'soil_moisture': 45, 'temperature': None, 'humidity': None})
    assert dq['components']['completeness'] < 100
    assert any('temperature' in n.lower() for n in dq['notes'])
    assert any('humidity' in n.lower() for n in dq['notes'])


def test_stale_reading_is_flagged():
    dq = compute_data_quality({'soil_moisture': 45, 'temperature': 29, 'humidity': 55}, recorded_at=0.0, now=3600.0)
    assert dq['components']['freshness'] < 100
    assert any('stale' in n.lower() for n in dq['notes'])


def test_low_sensor_reliability_or_anomalies_reduce_score():
    baseline = compute_data_quality({'soil_moisture': 45, 'temperature': 29, 'humidity': 55}, sensor_reliability=1.0)
    degraded = compute_data_quality(
        {'soil_moisture': 45, 'temperature': 29, 'humidity': 55},
        sensor_reliability=0.3, sensor_anomalies=['Soil moisture is stuck.'],
    )
    assert degraded['score'] < baseline['score']
    assert degraded['components']['reliability'] < baseline['components']['reliability']


def test_inconsistent_environment_is_flagged_not_silently_used():
    dq = compute_data_quality({'soil_moisture': 90, 'temperature': 30, 'humidity': 55, 'weather': 'drought'})
    assert dq['components']['environmental_consistency'] < 100
    assert any('drought' in n.lower() for n in dq['notes'])


def test_poor_band_never_claims_accuracy_language():
    dq = compute_data_quality({'soil_moisture': None, 'temperature': None, 'humidity': None}, sensor_reliability=0.1)
    assert dq['band'] == 'POOR'
    assert 'accuracy' not in dq['explanation'].lower()
