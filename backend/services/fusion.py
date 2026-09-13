from __future__ import annotations

def clamp(v,lo=0,hi=1): return max(lo,min(hi,v))

def risk_band(v):
    return 'HIGH' if v>=70 else 'MODERATE' if v>=45 else 'LOW'

def fuse(vision_conf: float, sensor_trust: float, image_quality: float, humidity: float, moisture: float,
         temperature: float, weather: str, rainfall: float, history_signal: float=0.0):
    disease_context=0.0
    if humidity>=70: disease_context+=0.12
    if rainfall>=10 or weather=='flood': disease_context+=0.12
    if moisture>=60: disease_context+=0.05
    disease_context=clamp(disease_context)
    context_conf=clamp(0.55*sensor_trust + 0.25*image_quality + 0.20*(1-abs(0.5-history_signal)))
    overall=clamp(0.60*vision_conf + 0.25*context_conf + 0.15*sensor_trust)
    return {'vision_confidence':round(vision_conf*100,1),'context_confidence':round(context_conf*100,1),
            'sensor_trust':round(sensor_trust*100,1),'overall_confidence':round(overall*100,1),
            'disease_context_modifier':round(disease_context*100,1)}
