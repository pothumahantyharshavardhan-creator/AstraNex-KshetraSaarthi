from __future__ import annotations

def decide(soil_moisture, temperature, humidity, weather, rainfall_mm, recent_irrigation_hours, growth_stage, water_risk, excess_water_risk):
    if excess_water_risk>=0.60 or weather=='flood' or rainfall_mm>=20:
        return {'irrigation_required':False,'suggested_duration_minutes':0,'priority':'hold','reason':'Recent or expected water load is high; verify drainage before irrigating.','confidence':0.8,'safety_state':'HOLD'}
    threshold={'seedling':38,'vegetative':40,'flowering':42,'fruiting':44}.get(growth_stage,40)
    if soil_moisture < threshold and water_risk>=0.35:
        duration=12 if soil_moisture<20 else 8 if soil_moisture<30 else 5
        if recent_irrigation_hours<6: duration=0
        return {'irrigation_required':duration>0,'suggested_duration_minutes':duration,'priority':'high' if duration>=8 else 'watch',
                'reason':f'Soil moisture {soil_moisture:.0f}% is below the configured {threshold}% decision threshold; rain and recent irrigation were considered.',
                'confidence':0.65,'safety_state':'DECISION_SUPPORT_ONLY'}
    return {'irrigation_required':False,'suggested_duration_minutes':0,'priority':'normal','reason':'No immediate irrigation signal from the configured field context.','confidence':0.7,'safety_state':'DECISION_SUPPORT_ONLY'}
