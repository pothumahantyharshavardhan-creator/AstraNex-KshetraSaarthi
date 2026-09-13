from __future__ import annotations
import os, time, uuid, json
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from .engine import AnalysisInput, analyze_field
from .db import init_db, save_observation, recent_observations, save_feedback, save_sensor_reading, latest_sensors, list_fields, get_devices, add_irrigation_event, add_alert, list_alerts, save_farmer_profile, get_farmer_profile, UPLOAD_DIR
from .schemas import AnalyzeRequest, SensorRequest, FeedbackRequest, IrrigationRequest, FarmerProfileRequest
from .services.inference import vision
from .services.sensor_health import assess_sensors

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app=FastAPI(title='AstraNex KshetraSaarthi API',version='1.0.0',description='Multimodal agricultural decision-support prototype.',lifespan=lifespan)
# The app is intentionally credential-free.  For local SIH development we allow
# localhost/127.0.0.1 on any port (VS Code Live Server, Vite, etc.) and also
# permit the explicit origins supplied through ASTRANEX_CORS_ORIGINS.
_origin_env=[x.strip() for x in os.getenv('ASTRANEX_CORS_ORIGINS','').split(',') if x.strip()]
origins=list(dict.fromkeys(_origin_env + ['http://127.0.0.1:8000','http://localhost:8000','null']))
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r'^https?://(localhost|127\.0\.0\.1)(:\d+)?$',
    allow_credentials=False,
    allow_methods=['*'],
    allow_headers=['*'],
    expose_headers=['Content-Length','Content-Type'],
    max_age=600,
)
MAX_UPLOAD=2*1024*1024
ALLOWED={'image/jpeg','image/png','image/webp'}

FRONTEND_ROOT=Path(__file__).resolve().parents[1]
FRONTEND_FILE=FRONTEND_ROOT/'astranex_frontend.html'
ASSET_DIR=FRONTEND_ROOT/'assets'
ASSET_DIR.mkdir(exist_ok=True)
app.mount('/assets', StaticFiles(directory=ASSET_DIR), name='assets')

@app.get('/')
def frontend():
    if not FRONTEND_FILE.exists(): raise HTTPException(404,'Frontend file not found.')
    return FileResponse(FRONTEND_FILE)

@app.get('/app')
def frontend_alias():
    return frontend()

@app.get('/api/health')
def health():
    return {'ok':True,'service':'AstraNex KshetraSaarthi','version':app.version,'model_mode':vision.status()['mode'],'timestamp':time.time()}

@app.get('/api/model-status')
def model_status(): return vision.status()

def _store_result(payload: dict, result: dict, image_ref=None, source='simulator', metrics=None):
    oid=save_observation(payload,result,image_ref=image_ref,source=source)
    result['observation_id']=oid
    result['model']=vision.status()
    result['metrics']=metrics or {}
    if result['color'] in {'red','amber'}:
        sev='HIGH' if result['color']=='red' else 'MODERATE'
        add_alert(payload.get('field_id'),oid,sev,result['issue'], '; '.join(result['reason']), result['next_check'])
    return result

@app.post('/api/analyze')
def analyze(req:AnalyzeRequest):
    started=time.perf_counter()
    x=AnalysisInput(**req.model_dump(exclude={'field_id','image_ref','source','client_event_id'}))
    result=analyze_field(x)
    result['metrics']={'fusion_ms':round((time.perf_counter()-started)*1000,3),'inference_ms':0,'total_ms':round((time.perf_counter()-started)*1000,3)}
    return _store_result(req.model_dump(),result,image_ref=req.image_ref,source=req.source,metrics=result.get('metrics'))

@app.post('/api/analyze-multimodal')
async def analyze_multimodal(
    file: UploadFile|None=File(None), crop:str=Form('tomato'), field_id:int|None=Form(None), growth_stage:str=Form('vegetative'),
    soil_moisture:float=Form(45), temperature:float=Form(29), humidity:float=Form(55), weather:str=Form('normal'),
    recent_rainfall_mm:float=Form(0), recent_irrigation_hours:float=Form(24), connectivity:str=Form('online'), sensor_reliability:float=Form(1.0), client_event_id:str|None=Form(None),
):
    started=time.perf_counter(); image_ref=None; vision_result=None; image_quality=1.0; inference_ms=0.0
    if not 0<=soil_moisture<=100 or not 0<=humidity<=100 or not -20<=temperature<=70 or not 0<=sensor_reliability<=1:
        raise HTTPException(422,'One or more sensor values are outside the allowed range.')
    if file is not None:
        if file.content_type not in ALLOWED: raise HTTPException(415,'Only JPEG, PNG or WebP images are accepted.')
        data=await file.read(MAX_UPLOAD+1)
        if len(data)>MAX_UPLOAD: raise HTTPException(413,'Image exceeds the 2 MB limit.')
        import io
        try:
            from PIL import Image, ImageStat, ImageFilter
            im=Image.open(io.BytesIO(data)).convert('RGB')
            if min(im.size)<160: image_quality*=.55
            brightness=ImageStat.Stat(im.convert('L')).mean[0]
            edge=ImageStat.Stat(im.convert('L').filter(ImageFilter.FIND_EDGES)).mean[0]
            if brightness<35 or brightness>235: image_quality*=.65
            if edge<4: image_quality*=.65
        except Exception:
            image_quality=.75
        ext={'image/jpeg':'.jpg','image/png':'.png','image/webp':'.webp'}[file.content_type]
        safe_name=f'{int(time.time())}_{uuid.uuid4().hex}{ext}'
        path=UPLOAD_DIR/safe_name; path.write_bytes(data); image_ref=str(path.relative_to(UPLOAD_DIR))
        t0=time.perf_counter(); vision_result=vision.analyze(data,expected_crop=crop); inference_ms=round((time.perf_counter()-t0)*1000,3)
        if image_quality<.60:
            vision_result={'status':'low_quality','prediction':'unknown','confidence':0,'message':'Image quality is insufficient. Capture a closer, well-lit leaf image.','real_inference':False}
    x=AnalysisInput(crop=crop,growth_stage=growth_stage,soil_moisture=soil_moisture,temperature=temperature,humidity=humidity,weather=weather,recent_rainfall_mm=recent_rainfall_mm,recent_irrigation_hours=recent_irrigation_hours,connectivity=connectivity,sensor_reliability=sensor_reliability,image_quality=image_quality)
    t1=time.perf_counter(); result=analyze_field(x,vision=vision_result) if vision_result is not None else analyze_field(x); fusion_ms=round((time.perf_counter()-t1)*1000,3)
    result['image_ref']=image_ref; result['image_quality']=image_quality; result['vision']=vision_result or {'status':'not_provided','real_inference':False,'message':'No image supplied; analysis uses sensor/context evidence.'}
    result['model']=vision.status(); result['metrics']={'preprocess_and_validation_ms':round(max(0,fusion_ms),3),'inference_ms':inference_ms,'fusion_ms':fusion_ms,'total_ms':round((time.perf_counter()-started)*1000,3)}
    payload={'crop':crop,'field_id':field_id,'growth_stage':growth_stage,'soil_moisture':soil_moisture,'temperature':temperature,'humidity':humidity,'weather':weather,'recent_rainfall_mm':recent_rainfall_mm,'recent_irrigation_hours':recent_irrigation_hours,'connectivity':connectivity,'sensor_reliability':sensor_reliability,'image_quality':image_quality,'condition':'vision' if vision_result else 'context','image_name':file.filename if file else None,'image_mime':file.content_type if file else None,'image_size':len(data) if file is not None else None,'client_event_id':client_event_id}
    return _store_result(payload,result,image_ref=image_ref,source='multimodal',metrics=result['metrics'])

@app.post('/api/analyze-image')
async def analyze_image(file:UploadFile=File(...), crop:str|None=Form(None)):
    if file.content_type not in ALLOWED: raise HTTPException(415,'Only JPEG, PNG or WebP images are accepted.')
    data=await file.read(MAX_UPLOAD+1)
    if len(data)>MAX_UPLOAD: raise HTTPException(413,'Image exceeds the 2 MB limit.')
    # Lightweight quality heuristics; no forced diagnosis.
    quality=1.0
    try:
        from PIL import Image, ImageStat, ImageFilter
        import io
        im=Image.open(io.BytesIO(data)).convert('RGB')
        if min(im.size)<160: quality*=0.55
        gray=im.convert('L').filter(ImageFilter.FIND_EDGES)
        edge=ImageStat.Stat(gray).mean[0]
        brightness=ImageStat.Stat(im.convert('L')).mean[0]
        if brightness<35 or brightness>235: quality*=0.65
        if edge<4: quality*=0.65
    except Exception as exc:
        # Pillow is a required dependency for this endpoint. If image-quality
        # analysis fails for an unexpected reason, do not silently classify a
        # perfectly valid upload as blurry. Keep the upload available and mark
        # quality as unverified instead.
        quality=0.75
    image_id=f'{int(time.time())}_{uuid.uuid4().hex}.img'
    # Extension follows validated MIME, not user-provided name.
    ext={'image/jpeg':'.jpg','image/png':'.png','image/webp':'.webp'}[file.content_type]
    path=UPLOAD_DIR/(Path(image_id).stem+ext)
    path.write_bytes(data)
    model=vision.analyze(data, expected_crop=crop)
    status='usable' if quality>=.60 else 'low_quality'
    if status!='usable':
        model={'status':'low_quality','prediction':'unknown','confidence':0,'message':'Image quality is insufficient. Please capture a clearer close-up of the affected leaf/plant.'}
    elif model.get('status') in {'not_a_plant_image','crop_mismatch','uncertain'}:
        status='needs_verification'
    return {'image_ref':str(path.relative_to(UPLOAD_DIR)),'image_quality':round(quality,3),'status':status,'vision':model,'selected_crop':crop,'max_size_bytes':MAX_UPLOAD}

@app.get('/api/images/{name}')
def get_image(name:str):
    safe=Path(name).name
    path=UPLOAD_DIR/safe
    if not path.exists(): raise HTTPException(404,'Image not found')
    return FileResponse(path)


@app.get('/api/geocode/search')
def geocode_search(q: str):
    """Server-side Nominatim proxy so browser geocoding is same-origin and more reliable."""
    from urllib.parse import urlencode
    from urllib.request import Request as URLRequest, urlopen
    if not q or len(q.strip()) < 2:
        return {'items': []}
    params=urlencode({'format':'jsonv2','limit':5,'countrycodes':'in','addressdetails':1,'q':q.strip()})
    req=URLRequest('https://nominatim.openstreetmap.org/search?'+params,headers={'User-Agent':'AstraNex-KshetraSaarthi/10.1 (SIH prototype)','Accept':'application/json'})
    try:
        with urlopen(req,timeout=8) as r:
            data=json.loads(r.read().decode('utf-8'))
        return {'items':data}
    except Exception as exc:
        raise HTTPException(503,f'Location search temporarily unavailable: {type(exc).__name__}')

@app.get('/api/geocode/reverse')
def geocode_reverse(lat: float, lon: float):
    """Server-side reverse geocoder with strict India bounds."""
    if not (6 <= lat <= 38 and 68 <= lon <= 98):
        raise HTTPException(422,'Coordinates are outside the supported India map area.')
    from urllib.parse import urlencode
    from urllib.request import Request as URLRequest, urlopen
    params=urlencode({'format':'jsonv2','lat':lat,'lon':lon,'zoom':18,'addressdetails':1})
    req=URLRequest('https://nominatim.openstreetmap.org/reverse?'+params,headers={'User-Agent':'AstraNex-KshetraSaarthi/10.1 (SIH prototype)','Accept':'application/json'})
    try:
        with urlopen(req,timeout=8) as r:
            data=json.loads(r.read().decode('utf-8'))
        return data
    except Exception as exc:
        raise HTTPException(503,f'Location lookup temporarily unavailable: {type(exc).__name__}')

REGIONAL_CROPS={
 'Andhra Pradesh':['paddy','chilli','groundnut','cotton','maize','turmeric'], 'Telangana':['paddy','cotton','maize','chilli','turmeric'],
 'Karnataka':['maize','cotton','groundnut','paddy','chilli'], 'Tamil Nadu':['paddy','groundnut','cotton','maize','chilli'],
 'Odisha':['paddy','groundnut','maize','turmeric'], 'West Bengal':['paddy','maize'], 'Maharashtra':['cotton','maize','groundnut','chilli'],
 'Gujarat':['cotton','groundnut','maize'], 'Madhya Pradesh':['maize','cotton'], 'Punjab':['paddy','maize'],
 'Haryana':['paddy','maize','cotton'], 'Uttar Pradesh':['paddy','maize','groundnut'], 'Bihar':['paddy','maize'],
 'Kerala':['paddy','turmeric'], 'Assam':['paddy','maize'], 'Chhattisgarh':['paddy','maize'], 'Jharkhand':['paddy','maize'],
 'Rajasthan':['maize','groundnut','cotton']
}

@app.get('/api/farmer-profile')
def farmer_profile():
    profile=get_farmer_profile()
    if not profile: return {'profile':None}
    regional=REGIONAL_CROPS.get(profile.get('state'),[])
    selected=set(profile.get('crops') or [])
    profile['regional_crops']=regional
    profile['regional_match']=[c for c in profile.get('crops',[]) if c in regional]
    profile['regional_note']=('Selected crops match common regional crop context.' if any(c in regional for c in selected) else 'Selected crop is outside the built-in regional shortlist; verify local agronomy before acting.')
    return {'profile':profile}

@app.post('/api/farmer-profile')
def save_profile(req:FarmerProfileRequest):
    data=req.model_dump()
    data['name']=data['name'].strip()
    data['profile_version']='national-final-v2'
    data['source_note']='Farmer-entered profile; regional context is advisory.'
    data['crops']=[str(x).strip().lower() for x in data.get('crops',[]) if str(x).strip()]
    if not data['crops']: raise HTTPException(422,'Select at least one crop.')
    save_farmer_profile(data)
    return {'ok':True,'profile':get_farmer_profile()}

@app.post('/api/model/prepare')
def prepare_model():
    """Download/load the optional PlantVillage ONNX model on demand.

    This is intentionally separate from image analysis so a first scan never hangs
    while a ~94 MB model is being downloaded. The endpoint is safe to call repeatedly.
    """
    try:
        ok=vision.prepare()
        if not ok:
            raise HTTPException(503, 'Vision model could not be prepared. Check internet access or set ASTRANEX_MODEL_PATH to a local ONNX model.')
        return {'ok':True,'model':vision.status()}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(503, f'Model preparation failed: {type(exc).__name__}')

@app.get('/api/model-capabilities')
def model_capabilities():
    return {'model':vision.status(),'supported_crops':vision.supported_crop_names(),'scope_note':'PlantVillage vision classes are used for preliminary screening; unsupported crops fall back to contextual monitoring.'}

@app.get('/api/regional-context')
def regional_context(state:str, crop:str|None=None):
    crops=REGIONAL_CROPS.get(state,[])
    crop_norm=(crop or '').strip().lower()
    return {'state':state,'crop':crop_norm or None,'regional_crops':crops,'selected_crop_match':bool(crop_norm and crop_norm in crops),'note':'Prototype regional crop knowledge. Confirm local agronomy, crop calendar and advisory services before field deployment.'}

@app.get('/api/fields')
def fields(): return {'items':list_fields()}

@app.get('/api/history')
def history(limit:int=30,field_id:int|None=None): return {'items':recent_observations(max(1,min(limit,100)),field_id)}

@app.get('/api/sensors/latest')
def sensors_latest(limit:int=50,field_id:int|None=None): return {'items':latest_sensors(field_id,max(1,min(limit,200)))}

@app.post('/api/sensors')
def sensors(req:SensorRequest):
    vals=req.model_dump()
    health=assess_sensors(vals)
    save_sensor_reading(vals,health)
    return {'ok':True,'device_id':req.device_id,'sensor_health':health,'received_at':time.time()}

@app.get('/api/devices')
def devices(): return {'items':get_devices()}

@app.get('/api/alerts')
def alerts(limit:int=50,field_id:int|None=None): return {'items':list_alerts(max(1,min(limit,100)),field_id)}

@app.post('/api/feedback')
def feedback(req:FeedbackRequest):
    save_feedback(req.observation_id,req.useful,req.note,req.label); return {'ok':True}

@app.post('/api/irrigation')
def irrigation(req:IrrigationRequest):
    if not req.simulate: raise HTTPException(409,'Physical actuation is disabled in this prototype; use simulated actuation.')
    iid=add_irrigation_event(req.model_dump() | {'status':'SIMULATED'})
    return {'ok':True,'event_id':iid,'status':'SIMULATED','message':'Irrigation command simulated; no pump or valve was activated.'}

@app.post('/api/sync')
def sync(payloads:list[AnalyzeRequest]):
    ids=[]
    for req in payloads:
        x=AnalysisInput(**req.model_dump(exclude={'field_id','image_ref','source','client_event_id'})); result=analyze_field(x)
        ids.append(save_observation(req.model_dump(),result,image_ref=req.image_ref,source='offline_sync',sync_status='synced'))
    return {'ok':True,'synced':len(ids),'observation_ids':ids,'synced_at':time.time()}

@app.get('/api/validation')
def validation():
    cases=[
      ('healthy',{'condition':'healthy','soil_moisture':45,'temperature':29,'humidity':55}),
      ('disease-high-context',{'condition':'diseaseA','soil_moisture':70,'temperature':29,'humidity':82,'recent_rainfall_mm':18}),
      ('disease-low-context',{'condition':'diseaseA','soil_moisture':35,'temperature':27,'humidity':40}),
      ('poor-image',{'condition':'unclear','image_quality':.35}),
      ('unknown',{'condition':'unknown','image_quality':.9}),
      ('sensor-fault',{'condition':'diseaseA','sensor_reliability':.35}),
      ('heat',{'condition':'healthy','temperature':39}),
      ('flood',{'condition':'healthy','weather':'flood','soil_moisture':80}),
    ]
    out=[]
    for name,kw in cases:
        st=time.perf_counter(); r=analyze_field(AnalysisInput(**kw)); out.append({'case':name,'prediction':r['issue'],'confidence':r['confidence'],'status':r['status'],'latency_ms':round((time.perf_counter()-st)*1000,3),'risk':r['risks']})
    return {'model':vision.status(),'cases':out}
