from __future__ import annotations
from dataclasses import dataclass
from .services.fusion import clamp, fuse, risk_band
from .services.irrigation import decide as irrigation_decide

@dataclass
class AnalysisInput:
    crop: str='tomato'; condition: str='healthy'; soil_moisture: float=45; temperature: float=29; humidity: float=55
    weather: str='normal'; growth_stage: str='vegetative'; sensor_reliability: float=1.0; image_quality: float=1.0
    connectivity: str='offline'; recent_rainfall_mm: float=0; recent_irrigation_hours: float=24
    history_signal: float=0.0

def _normalise_issue_from_vision(vision: dict, crop: str):
    if not vision:
        return None, None, .0, []
    status=vision.get('status')
    if status in {'not_a_plant_image','uncertain','crop_mismatch','model_unavailable','inference_error','visual_screening'}:
        return 'unknown', None, float(vision.get('confidence') or 0), [vision.get('message','Visual evidence is unavailable.')]
    pred=str(vision.get('prediction') or '').strip()
    conf=float(vision.get('confidence') or 0)
    if not pred or pred.lower()=='unknown':
        return 'unknown', None, conf, ['The vision model did not produce a reliable class.']
    if 'healthy' in pred.lower():
        return 'healthy', None, conf, ['Vision model found a healthy-leaf pattern.']
    disease=pred.replace('___',' / ').replace('_',' ')
    key='diseaseA' if 'early blight' in disease.lower() or 'leaf spot' in disease.lower() else 'diseaseB'
    return key, disease, conf, [f'Vision model pattern: {disease}.']

def analyze_field(x: AnalysisInput, vision: dict | None = None)->dict:
    m,t,h=x.soil_moisture,x.temperature,x.humidity
    reason=[]; issue='healthy'; disease=None; vision_conf=.90
    condition=x.condition.lower()
    if vision is not None:
        v_issue,v_disease,v_conf,v_reason=_normalise_issue_from_vision(vision,x.crop)
        issue=v_issue or issue; disease=v_disease; vision_conf=v_conf; reason.extend(v_reason)
    elif condition in {'diseasea','diseaseb','yellowing','holes','unknown','unclear'}:
        if condition=='diseasea':
            disease='Early Blight' if x.crop=='tomato' else 'Representative disease A'; issue='diseaseA_severe' if (h>=65 and (m>=55 or x.weather=='flood' or x.recent_rainfall_mm>=10)) else 'diseaseA_mild'; vision_conf=.72; reason.append('visual spotting/discoloration pattern')
            reason.append('humid/wet context raises disease risk' if h>=65 and (m>=55 or x.weather=='flood' or x.recent_rainfall_mm>=10) else 'current context is less favourable for rapid spread')
        elif condition=='diseaseb':
            disease='Late/temperature-linked pattern' if x.crop=='tomato' else 'Representative disease B'; issue='diseaseB_severe' if (t>=32 or x.weather in {'heat','flood'}) else 'diseaseB_mild'; vision_conf=.70; reason.append('visual stress pattern'); reason.append('temperature/weather context increases concern' if t>=32 or x.weather in {'heat','flood'} else 'current temperature is less supportive of rapid spread')
        elif condition=='yellowing':
            issue='water_stress' if m<35 else 'nutrient'; vision_conf=.68 if m<35 else .58; reason.append('lower-leaf yellowing'); reason.append('low moisture supports water-stress hypothesis' if m<35 else 'moisture is adequate, so water stress is less likely')
        elif condition=='holes': issue='pest'; vision_conf=.71; reason.append('chewed edges / holes')
        else: issue=condition; vision_conf=.20; reason.append('visual evidence is insufficient')

    water=0; heat=0; excess=0
    if m<30: water+=.65
    elif m<40: water+=.40
    if x.weather=='drought': water+=.25
    if t>=36: heat+=.80
    elif t>=32: heat+=.50
    if x.weather=='heat': heat+=.25
    if x.weather=='flood': excess+=.70
    if x.recent_rainfall_mm>=20: excess+=.20
    if m>=75: excess+=.25
    water,heat,excess=map(lambda z:clamp(z),[water,heat,excess])
    if x.image_quality<.60:
        issue='unclear'; vision_conf=0.0; reason=['Image quality is too weak for a reliable visual assessment.']
    elif issue=='unknown':
        vision_conf=min(vision_conf,.20)
    fusion=fuse(vision_conf,x.sensor_reliability,x.image_quality,h,m,t,x.weather,x.recent_rainfall_mm,x.history_signal)
    if x.sensor_reliability<.50: reason.append('Sensor reliability is low; contextual evidence is down-weighted.')
    confidence=fusion['overall_confidence']
    if issue in {'unknown','unclear'}: confidence=min(confidence,35.0)
    verification=confidence<45 or issue in {'unknown','unclear'}
    if verification: reason.append('Evidence is weak or outside supported scope; verification is recommended.')
    if issue.startswith('disease') and h>=70: reason.append('High humidity increases the environmental disease-risk signal.')
    if water>=.65: reason.append('Low root-zone moisture increases water-stress risk.')
    if heat>=.65: reason.append('High temperature increases heat-stress risk.')
    if excess>=.65: reason.append('Wet conditions increase excess-water risk; hold irrigation.')

    next_check=('Capture a clearer image and inspect multiple leaves before acting.' if issue in {'unknown','unclear'} else
                'Check soil moisture at the root zone and review recent irrigation/rainfall before watering.' if issue=='water_stress' or water>=.65 else
                'Check drainage and standing water around the root zone.' if excess>=.65 else
                'Check leaf wilting and canopy exposure during the hottest period.' if heat>=.65 else
                'Inspect the underside of several leaves for insects or eggs.' if issue=='pest' else
                'Inspect several leaves and repeat the scan if symptoms spread.')
    irrigation=irrigation_decide(m,t,h,x.weather,x.recent_rainfall_mm,x.recent_irrigation_hours,x.growth_stage,water,excess)
    disease_base=vision_conf if issue.startswith('disease') else 0
    disease_risk=clamp(disease_base + fusion['disease_context_modifier']/100)
    if issue=='healthy': disease_risk=clamp(fusion['disease_context_modifier']/100)
    color='red' if max(water,heat,excess)>=.70 or (issue.startswith('disease') and confidence>=70) else 'amber' if verification or max(water,heat,excess)>=.45 or issue!='healthy' else 'green'
    health_score=round(max(0,min(100,100-(disease_risk*22+water*.28*100+heat*.18*100+excess*.17*100))))
    if issue=='pest': health_score=max(0,health_score-12)
    status_label='GOOD' if health_score>=75 else 'WATCH' if health_score>=50 else 'ACTION NEEDED'
    contributors=[]
    for label,val in [('Disease risk',disease_risk*100),('Water risk',water*100),('Heat risk',heat*100),('Excess-water risk',excess*100)]:
        if val>=45: contributors.append({'factor':label,'value':round(val,1)})
    if x.sensor_reliability<.7: contributors.append({'factor':'Sensor trust','value':round(x.sensor_reliability*100,1)})
    recommendation=('No immediate crop-health action indicated; continue routine scouting.' if issue=='healthy' and color=='green' else next_check)
    if issue.startswith('disease'): recommendation='Treat this as preliminary screening only. Inspect several plants and confirm the disease locally before any crop-protection treatment.'
    return {
      'status':'needs_verification' if verification else 'usable','issue':issue,'disease':disease,'color':color,
      'confidence':confidence,'vision_confidence':fusion['vision_confidence'],'context_confidence':fusion['context_confidence'],'sensor_trust':fusion['sensor_trust'],
      'reason':reason,'next_check':next_check,'recommendation':recommendation,
      'health_score':health_score,'health_status':status_label,'contributors':contributors,
      'risks':{'disease':round(disease_risk*100,1),'water':round(water*100,1),'heat':round(heat*100,1),'excess_water':round(excess*100,1)},
      'risk_bands':{'disease':risk_band(disease_risk*100),'water':risk_band(water*100),'heat':risk_band(heat*100),'excess_water':risk_band(excess*100)},
      'irrigation':irrigation,
      'evidence':{'camera':condition if vision is None else (vision.get('prediction') or 'unknown'),'soil_moisture':m,'temperature':t,'humidity':h,'weather':x.weather,'recent_rainfall_mm':x.recent_rainfall_mm,'recent_irrigation_hours':x.recent_irrigation_hours,'growth_stage':x.growth_stage,'sensor_reliability':round(x.sensor_reliability*100,1),'image_quality':round(x.image_quality*100,1)},
      'explainability':{'visual_evidence':reason[0] if reason else 'No strong visual abnormality','environment':f'{h}% humidity, {t}°C, weather={x.weather}, rainfall={x.recent_rainfall_mm} mm','soil':f'{m}% moisture','sensor_trust':f'{x.sensor_reliability*100:.0f}%','history':'Historical signal included in confidence weighting.'},
      'guardrails':['No forced diagnosis when evidence is weak','Sensor reliability affects contextual confidence','Decision support only; verify before treatment','Chemical treatment is not autonomously prescribed']
    }
