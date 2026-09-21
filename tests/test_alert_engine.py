from backend.engine import AnalysisInput, analyze_field
from backend.services.alert_engine import build_alerts, overall_level, LEVELS


def test_healthy_field_has_info_level_only():
    r = analyze_field(AnalysisInput(soil_moisture=45, temperature=29, humidity=55, condition='healthy'))
    assert r['alert_level'] == 'INFO'
    assert all(a['level'] in LEVELS for a in r['alerts'])


def test_low_moisture_raises_alert_with_all_required_fields():
    r = analyze_field(AnalysisInput(soil_moisture=15, temperature=29, humidity=55, condition='healthy'))
    water_alerts = [a for a in r['alerts'] if 'moisture' in a['title'].lower()]
    assert water_alerts
    for a in water_alerts:
        assert {'level', 'title', 'what', 'why', 'check', 'action'} <= set(a.keys())
        assert a['level'] in LEVELS


def test_severe_disease_raises_critical_or_warning():
    r = analyze_field(AnalysisInput(condition='diseaseA', soil_moisture=70, humidity=85, temperature=29))
    assert r['alert_level'] in {'WARNING', 'CRITICAL'}


def test_overall_level_takes_the_highest_severity():
    alerts = [{'level': 'INFO'}, {'level': 'WARNING'}, {'level': 'WATCH'}]
    assert overall_level(alerts) == 'WARNING'


def test_no_alerts_still_returns_an_info_placeholder_not_empty_list():
    alerts = build_alerts({'risks': {'disease': 0, 'water': 0, 'heat': 0, 'excess_water': 0}, 'issue': 'healthy',
                            'evidence': {'soil_moisture': 45, 'temperature': 29}, 'color': 'green', 'disease': None})
    assert len(alerts) == 1
    assert alerts[0]['level'] == 'INFO'
