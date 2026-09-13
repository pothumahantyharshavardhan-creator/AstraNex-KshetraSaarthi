from backend.engine import AnalysisInput, analyze_field


def test_dry_hot_increases_water_heat_risk():
    a=analyze_field(AnalysisInput(soil_moisture=20,temperature=38,weather='normal'))
    assert a['risks']['water'] >= 65
    assert a['risks']['heat'] >= 65


def test_unknown_is_not_forced():
    a=analyze_field(AnalysisInput(condition='unknown'))
    assert a['issue']=='unknown'
    assert a['confidence'] <= 35
    assert a['status']=='needs_verification'


def test_sensor_reliability_reduces_confidence():
    a=analyze_field(AnalysisInput(condition='diseaseA',sensor_reliability=0.4))
    assert a['confidence'] < a['vision_confidence']


def test_context_changes_risk_not_visual_identity():
    dry=analyze_field(AnalysisInput(condition='diseaseA',soil_moisture=35,humidity=40))
    wet=analyze_field(AnalysisInput(condition='diseaseA',soil_moisture=70,humidity=82,recent_rainfall_mm=15))
    assert dry['issue']=='diseaseA_mild'
    assert wet['issue']=='diseaseA_severe'
    assert wet['risks']['disease'] > dry['risks']['disease']


def test_poor_image_forces_verification():
    a=analyze_field(AnalysisInput(condition='diseaseA',image_quality=.35))
    assert a['issue']=='unclear'
    assert a['status']=='needs_verification'
    assert a['confidence'] <= 35


def test_excess_water_holds_irrigation():
    a=analyze_field(AnalysisInput(soil_moisture=85,weather='flood',temperature=29))
    assert a['risks']['excess_water'] >= 70
    assert a['irrigation']['irrigation_required'] is False
    assert a['irrigation']['safety_state']=='HOLD'


def test_growth_stage_affects_irrigation_threshold():
    seedling=analyze_field(AnalysisInput(soil_moisture=39,growth_stage='seedling'))
    fruiting=analyze_field(AnalysisInput(soil_moisture=39,growth_stage='fruiting'))
    assert seedling['irrigation']['irrigation_required'] is False
    assert fruiting['irrigation']['irrigation_required'] is True
