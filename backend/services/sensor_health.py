from __future__ import annotations
from math import isfinite

RANGES = {
    'soil_moisture': (0, 100),
    'temperature': (-20, 70),
    'humidity': (0, 100),
}

def assess_sensors(values: dict, previous: dict | None = None) -> dict:
    statuses={}; score=1.0
    for name,(lo,hi) in RANGES.items():
        v=values.get(name)
        if v is None:
            statuses[name]={'status':'disconnected','valid':False}; score*=0.7; continue
        if not isfinite(float(v)) or v<lo or v>hi:
            statuses[name]={'status':'invalid','valid':False}; score*=0.35; continue
        noisy=False
        if previous and previous.get(name) is not None:
            noisy=abs(float(v)-float(previous[name])) > (20 if name!='temperature' else 12)
        statuses[name]={'status':'noisy' if noisy else 'healthy','valid':True}
        if noisy: score*=0.8
    if previous and values.get('recorded_at') and values['recorded_at'] < previous.get('recorded_at',0):
        score*=0.5
    return {'overall':round(max(0,min(1,score)),3),'sensors':statuses}
