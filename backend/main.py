from __future__ import annotations
import os, io, time, uuid, json, threading
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from .engine import AnalysisInput, analyze_field
from .db import init_db, save_observation, recent_observations, save_feedback, save_sensor_reading, latest_sensors, list_fields, get_devices, add_irrigation_event, add_alert, list_alerts, save_farmer_profile, get_farmer_profile, UPLOAD_DIR, connect, field_exists, observation_exists_for_event, get_observation, latest_sensor_for_device, plausible_epoch, recent_sensor_history, list_irrigation_events
from .schemas import AnalyzeRequest, SensorRequest, FeedbackRequest, IrrigationRequest, FarmerProfileRequest
from .services.inference import vision
from .services.sensor_health import assess_sensors
from .services.crop_profiles import list_crops, get_profile
from .services.timeline import field_history, farm_events_timeline
from .services.weather import get_weather
from .services import demo as demo_service

APP_VERSION='3.3.0'
try:
    from .quantum.api import router as quantum_router
    QUANTUM_LAYER_ERROR=None
except Exception as _exc:  # the app must start even if the quantum layer fails to import
    quantum_router=None
    QUANTUM_LAYER_ERROR=f'{type(_exc).__name__}: {_exc}'

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    if quantum_router is not None:
        # Load the trained QML/classical models, or train them in the background on a
        # fresh install (ASTRANEX_AUTO_TRAIN=0 disables). Never blocks or breaks start-up.
        try:
            from .quantum import pipeline as _qp
            _qp.ensure_ready(background=True)
        except Exception:
            pass
    yield

app=FastAPI(title='AstraNex KshetraSaarthi API',version=APP_VERSION,description='Multimodal agricultural early-warning prototype with an experimental hybrid classical-quantum layer.',lifespan=lifespan)
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

PROJECT_ROOT=Path(__file__).resolve().parents[1]
FRONTEND_ROOT=PROJECT_ROOT/'frontend'
FRONTEND_FILE=FRONTEND_ROOT/'index.html'
# The original interface is preserved and still served at /legacy.
LEGACY_FILE=PROJECT_ROOT/'legacy'/'astranex_frontend.html'
ASSET_DIR=PROJECT_ROOT/'assets'
ASSET_DIR.mkdir(parents=True, exist_ok=True)
app.mount('/assets', StaticFiles(directory=ASSET_DIR), name='assets')
if (FRONTEND_ROOT/'assets').exists():
    app.mount('/static', StaticFiles(directory=FRONTEND_ROOT/'assets'), name='static')

@app.get('/')
def frontend():
    if not FRONTEND_FILE.exists(): raise HTTPException(404,'Frontend file not found.')
    return FileResponse(FRONTEND_FILE)

@app.get('/app')
def frontend_alias():
    return frontend()

@app.get('/sw.js')
def service_worker():
    """Offline shell cache. Served from the root so its scope covers the app."""
    sw=FRONTEND_ROOT/'sw.js'
    if not sw.exists(): raise HTTPException(404,'Service worker not found.')
    return FileResponse(sw, media_type='application/javascript')

@app.get('/legacy')
def legacy_frontend():
    """The original AstraNex interface, preserved for reference and comparison."""
    if not LEGACY_FILE.exists(): raise HTTPException(404,'Legacy frontend not found.')
    return FileResponse(LEGACY_FILE)

@app.get('/api/health')
def health():
    quantum={'available':False,'error':QUANTUM_LAYER_ERROR}
    if quantum_router is not None:
        try:
            from .quantum import pipeline as _qp
            st=_qp.quantum_status()
            quantum={'available':True,'backend':st['runtime']['execution_backend'],'execution_label':st['runtime']['execution_label'],'qiskit_execution':st['runtime']['qiskit_execution'],'qiskit_installed':st['runtime']['qiskit_installed'],'qiskit_machine_learning_installed':st['runtime']['qiskit_machine_learning_installed'],'mode':st['runtime']['mode'],'models_trained':st['models_trained'],'layer':'experimental'}
        except Exception as exc:
            quantum={'available':False,'error':type(exc).__name__}
    return {'ok':True,'service':'AstraNex KshetraSaarthi','version':app.version,'model_mode':vision.status()['mode'],'quantum':quantum,'timestamp':time.time()}

@app.get('/api/model-status')
def model_status(): return vision.status()

def _validate_field_id(field_id: int | None):
    if field_id is None:
        return
    if not field_exists(field_id):
        raise HTTPException(422, 'Unknown field_id.')


def _validate_observation_id(observation_id: int | None):
    if observation_id is None:
        return
    if get_observation(observation_id) is None:
        raise HTTPException(422, 'Unknown observation_id.')


MAX_IMAGE_PIXELS=25_000_000

def _assess_image(data: bytes) -> float:
    """Validate an upload and return a 0-1 quality score (Pillow heuristics; no forced diagnosis)."""
    try:
        from PIL import Image, ImageStat, ImageFilter
    except ImportError:
        raise HTTPException(503,'Image analysis needs Pillow, which is not installed on the server. Remove the photo to continue with sensor evidence only.')
    try:
        Image.open(io.BytesIO(data)).verify()
        im=Image.open(io.BytesIO(data))
        if im.width*im.height>MAX_IMAGE_PIXELS:
            raise HTTPException(413,'Image dimensions are too large; please upload a photo under 25 megapixels.')
        im=im.convert('RGB')
        quality=1.0
        if min(im.size)<160: quality*=.55
        gray=im.convert('L')
        brightness=ImageStat.Stat(gray).mean[0]
        edge=ImageStat.Stat(gray.filter(ImageFilter.FIND_EDGES)).mean[0]
        if brightness<35 or brightness>235: quality*=.65
        if edge<4: quality*=.65
        return quality
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(422, f'Uploaded file is not a valid readable image: {type(exc).__name__}')


def _attach_location(result: dict, latitude=None, longitude=None, location_name=None):
    try:
        lat = float(latitude) if latitude is not None else None
        lon = float(longitude) if longitude is not None else None
    except (TypeError, ValueError):
        lat = lon = None
    if lat is not None and lon is not None:
        result['location'] = {'latitude': round(lat, 6), 'longitude': round(lon, 6),
                              'name': str(location_name or 'Selected field location')[:240],
                              'source': 'user_selected'}
    else:
        result['location'] = None
    return result

def _store_result(payload: dict, result: dict, image_ref=None, source='simulator', metrics=None):
    _validate_field_id(payload.get('field_id'))
    event_id=payload.get('client_event_id')
    duplicate=observation_exists_for_event(event_id)
    oid=save_observation(payload,result,image_ref=image_ref,source=source)
    result['observation_id']=oid
    result['model']=vision.status()
    result['metrics']=metrics or {}
    if not duplicate and result['color'] in {'red','amber'}:
        sev='HIGH' if result['color']=='red' else 'MODERATE'
        structured=(result.get('alerts') or [None])[0]
        add_alert(payload.get('field_id'),oid,sev,result['issue'], '; '.join(result['reason']), result['next_check'],
                  level=result.get('alert_level'), detail=structured)
    return result

@app.post('/api/analyze')
def analyze(req:AnalyzeRequest):
    started=time.perf_counter()
    x=AnalysisInput(**req.model_dump(exclude={'field_id','image_ref','source','client_event_id','latitude','longitude','location_name'}))
    result=analyze_field(x)
    _attach_location(result, req.latitude, req.longitude, req.location_name)
    result['metrics']={'fusion_ms':round((time.perf_counter()-started)*1000,3),'inference_ms':0,'total_ms':round((time.perf_counter()-started)*1000,3)}
    return _store_result(req.model_dump(),result,image_ref=req.image_ref,source=req.source,metrics=result.get('metrics'))

@app.post('/api/analyze-multimodal')
async def analyze_multimodal(
    file: UploadFile|None=File(None), crop:str=Form('tomato'), field_id:int|None=Form(None), growth_stage:str=Form('vegetative'),
    latitude:float|None=Form(None), longitude:float|None=Form(None), location_name:str|None=Form(None),
    soil_moisture:float=Form(45), temperature:float=Form(29), humidity:float=Form(55), weather:str=Form('normal'),
    recent_rainfall_mm:float=Form(0), recent_irrigation_hours:float=Form(24), connectivity:str=Form('online'), sensor_reliability:float=Form(1.0), client_event_id:str|None=Form(None),
):
    started=time.perf_counter(); image_ref=None; vision_result=None; image_quality=1.0; inference_ms=0.0; validation_ms=0.0
    _validate_field_id(field_id)
    crop=crop.strip().lower()[:80]
    growth_stage=growth_stage.strip().lower()[:80]
    weather=weather.strip().lower()[:80]
    connectivity=connectivity.strip().lower()[:80]
    if not 0<=soil_moisture<=100 or not 0<=humidity<=100 or not -20<=temperature<=70 or not 0<=sensor_reliability<=1:
        raise HTTPException(422,'One or more sensor values are outside the allowed range.')
    if (latitude is None) != (longitude is None):
        raise HTTPException(422,'Latitude and longitude must be supplied together.')
    if latitude is not None and not (6 <= latitude <= 38 and 68 <= longitude <= 98):
        raise HTTPException(422,'Coordinates are outside the supported India map area.')
    if file is not None:
        if file.content_type not in ALLOWED: raise HTTPException(415,'Only JPEG, PNG or WebP images are accepted.')
        data=await file.read(MAX_UPLOAD+1)
        if len(data)>MAX_UPLOAD: raise HTTPException(413,'Image exceeds the 2 MB limit.')
        image_quality=_assess_image(data)
        validation_ms=round((time.perf_counter()-started)*1000,3)
        ext={'image/jpeg':'.jpg','image/png':'.png','image/webp':'.webp'}[file.content_type]
        safe_name=f'{int(time.time())}_{uuid.uuid4().hex}{ext}'
        path=UPLOAD_DIR/safe_name; path.write_bytes(data); image_ref=str(path.relative_to(UPLOAD_DIR))
        t0=time.perf_counter(); vision_result=vision.analyze(data,expected_crop=crop); inference_ms=round((time.perf_counter()-t0)*1000,3)
        if image_quality<.60:
            vision_result={'status':'low_quality','prediction':'unknown','confidence':0,'message':'Image quality is insufficient. Capture a closer, well-lit leaf image.','real_inference':False}
    x=AnalysisInput(crop=crop,growth_stage=growth_stage,soil_moisture=soil_moisture,temperature=temperature,humidity=humidity,weather=weather,recent_rainfall_mm=recent_rainfall_mm,recent_irrigation_hours=recent_irrigation_hours,connectivity=connectivity,sensor_reliability=sensor_reliability,image_quality=image_quality)
    t1=time.perf_counter(); result=analyze_field(x,vision=vision_result) if vision_result is not None else analyze_field(x); fusion_ms=round((time.perf_counter()-t1)*1000,3)
    _attach_location(result, latitude, longitude, location_name)
    result['image_ref']=image_ref; result['image_quality']=image_quality; result['vision']=vision_result or {'status':'not_provided','real_inference':False,'message':'No image supplied; analysis uses sensor/context evidence.'}
    result['model']=vision.status(); result['metrics']={'preprocess_and_validation_ms':validation_ms,'inference_ms':inference_ms,'fusion_ms':fusion_ms,'total_ms':round((time.perf_counter()-started)*1000,3)}
    payload={'crop':crop,'field_id':field_id,'growth_stage':growth_stage,'soil_moisture':soil_moisture,'temperature':temperature,'humidity':humidity,'weather':weather,'recent_rainfall_mm':recent_rainfall_mm,'recent_irrigation_hours':recent_irrigation_hours,'connectivity':connectivity,'sensor_reliability':sensor_reliability,'image_quality':image_quality,'condition':'vision' if vision_result else 'context','image_name':file.filename if file else None,'image_mime':file.content_type if file else None,'image_size':len(data) if file is not None else None,'client_event_id':client_event_id,'latitude':latitude,'longitude':longitude,'location_name':location_name}
    return _store_result(payload,result,image_ref=image_ref,source='multimodal',metrics=result['metrics'])

@app.post('/api/analyze-image')
async def analyze_image(file:UploadFile=File(...), crop:str|None=Form(None)):
    if file.content_type not in ALLOWED: raise HTTPException(415,'Only JPEG, PNG or WebP images are accepted.')
    data=await file.read(MAX_UPLOAD+1)
    if len(data)>MAX_UPLOAD: raise HTTPException(413,'Image exceeds the 2 MB limit.')
    quality=_assess_image(data)
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


_GEO_CACHE: dict[str, tuple[float, object]] = {}
_GEO_LOCK = threading.Lock()
_GEO_LAST = [0.0]
_GEO_TTL = 900
_GEO_UA = f'AstraNex-KshetraSaarthi/{APP_VERSION} (agri early-warning prototype)'


def _nominatim(endpoint: str, params: dict):
    """Cached, rate-limited (>=1 s apart, per Nominatim's usage policy) upstream lookup."""
    from urllib.parse import urlencode
    from urllib.request import Request as URLRequest, urlopen
    key = endpoint + '?' + urlencode(sorted(params.items()))
    now = time.time()
    with _GEO_LOCK:
        hit = _GEO_CACHE.get(key)
        if hit and now - hit[0] < _GEO_TTL:
            return hit[1]
        wait = 1.0 - (now - _GEO_LAST[0])
        if wait > 0:
            time.sleep(min(wait, 1.0))
        _GEO_LAST[0] = time.time()
        req = URLRequest('https://nominatim.openstreetmap.org/' + endpoint + '?' + urlencode(params),
                         headers={'User-Agent': _GEO_UA, 'Accept': 'application/json'})
        with urlopen(req, timeout=8) as r:
            data = json.loads(r.read().decode('utf-8'))
        if len(_GEO_CACHE) >= 256:
            _GEO_CACHE.pop(next(iter(_GEO_CACHE)))
        _GEO_CACHE[key] = (time.time(), data)
        return data


@app.get('/api/geocode/search')
def geocode_search(q: str):
    """Server-side Nominatim proxy so browser geocoding is same-origin and more reliable."""
    if not q or len(q.strip()) < 2:
        return {'items': []}
    try:
        return {'items': _nominatim('search', {'format':'jsonv2','limit':5,'countrycodes':'in','addressdetails':1,'q':q.strip()[:160]})}
    except Exception as exc:
        raise HTTPException(503,f'Location search temporarily unavailable: {type(exc).__name__}')

@app.get('/api/geocode/reverse')
def geocode_reverse(lat: float, lon: float):
    """Server-side reverse geocoder with strict India bounds."""
    if not (6 <= lat <= 38 and 68 <= lon <= 98):
        raise HTTPException(422,'Coordinates are outside the supported India map area.')
    try:
        data=_nominatim('reverse', {'format':'jsonv2','lat':round(lat,5),'lon':round(lon,5),'zoom':18,'addressdetails':1})
        address=data.get('address') or {}
        if str(address.get('country_code','')).lower() not in {'in','india'}:
            raise HTTPException(422,'The selected coordinate is not resolved inside India.')
        return data
    except HTTPException:
        raise
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
    _validate_field_id(req.field_id)
    vals=req.model_dump()
    now=time.time()
    # Devices often report uptime seconds (millis()/1000), which is not a calendar time.
    vals['timestamp']=plausible_epoch(vals.get('timestamp'),now) or now
    vals['recorded_at']=vals['timestamp']
    health=assess_sensors(vals, latest_sensor_for_device(req.device_id), recent_sensor_history(req.device_id, 5))
    save_sensor_reading(vals,health)
    if health.get('anomaly_detected'):
        add_alert(req.field_id, None, 'MODERATE', 'sensor_anomaly',
                  '; '.join(health['anomalies']), 'Inspect the flagged sensor(s) before trusting this reading.',
                  level='WARNING' if len(health['anomalies'])>1 else 'WATCH', detail={'anomalies':health['anomalies'],'device_id':req.device_id})
    return {'ok':True,'device_id':req.device_id,'sensor_health':health,'received_at':time.time()}

@app.get('/api/devices')
def devices(): return {'items':get_devices()}

@app.get('/api/crops')
def crops():
    """Configurable crop profiles (v3.3). See config/crops/*.json — NOT externally validated agronomic data."""
    return {'items':[get_profile(c) for c in list_crops()]}

@app.get('/api/field-history')
def field_history_endpoint(window:str='24h', field_id:int|None=None):
    """Time-series soil moisture / temperature / humidity / health-score for a window (v3.3 section 11)."""
    sensors=latest_sensors(field_id, 2000)
    observations=recent_observations(2000, field_id)
    return field_history(sensors, observations, window=window)

@app.get('/api/timeline')
def timeline_endpoint(field_id:int|None=None, limit:int=40):
    """Chronological farm-events timeline merging analyses, sensors, alerts and irrigation (v3.3 section 12)."""
    events=farm_events_timeline(
        recent_observations(200, field_id), latest_sensors(field_id, 200),
        list_alerts(200, field_id), list_irrigation_events(200, field_id), limit=max(1,min(limit,200)),
    )
    return {'items':events}

@app.get('/api/weather')
def weather_endpoint(latitude:float|None=None, longitude:float|None=None):
    """Weather with graceful degradation (v3.3 section 14). Never fabricates a live reading."""
    return get_weather(latitude, longitude)

@app.get('/api/demo/scenarios')
def demo_scenarios():
    """List one-click Demo Mode scenarios (v3.3 sections 29-30). Never touches real data."""
    return {'items':demo_service.list_scenarios()}

@app.post('/api/demo/run/{scenario_id}')
def demo_run(scenario_id:int):
    return demo_service.run_scenario(scenario_id)

@app.post('/api/demo/reset')
def demo_reset():
    """RESET DEMO (v3.3 section 31) — demo scenarios are never persisted, so nothing real is deleted."""
    return demo_service.reset()

@app.get('/api/alerts')
def alerts(limit:int=50,field_id:int|None=None): return {'items':list_alerts(max(1,min(limit,100)),field_id)}

@app.post('/api/feedback')
def feedback(req:FeedbackRequest):
    _validate_observation_id(req.observation_id)
    save_feedback(req.observation_id,req.useful,req.note,req.label); return {'ok':True}

@app.post('/api/irrigation')
def irrigation(req:IrrigationRequest):
    _validate_field_id(req.field_id)
    _validate_observation_id(req.observation_id)
    if not req.simulate: raise HTTPException(409,'Physical actuation is disabled in this prototype; use simulated actuation.')
    iid=add_irrigation_event(req.model_dump() | {'status':'SIMULATED'})
    return {'ok':True,'event_id':iid,'status':'SIMULATED','message':'Irrigation command simulated; no pump or valve was activated.'}

@app.post('/api/sync')
def sync(payloads:list[dict]):
    """Replay offline scans. Each item is processed independently, so one invalid record can
    never block the rest (it is reported in ``failed`` and the client drops it)."""
    if len(payloads)>60:
        raise HTTPException(413,'A sync batch may contain at most 60 observations.')
    ids=[]; failed=[]; results=[]
    for i,item in enumerate(payloads):
        event=item.get('client_event_id') if isinstance(item,dict) else None
        try:
            req=AnalyzeRequest(**item)
            x=AnalysisInput(**req.model_dump(exclude={'field_id','image_ref','source','client_event_id','latitude','longitude','location_name'})); result=analyze_field(x)
            _attach_location(result,req.latitude,req.longitude,req.location_name)
            stored=_store_result(req.model_dump(),result,image_ref=req.image_ref,source='offline_sync',metrics={})
            ids.append(stored['observation_id'])
            results.append({'index':i,'client_event_id':event,'ok':True,'observation_id':stored['observation_id']})
        except HTTPException as exc:
            failed.append({'index':i,'client_event_id':event,'error':str(exc.detail),'retryable':False})
            results.append({'index':i,'client_event_id':event,'ok':False,'error':str(exc.detail)})
        except Exception as exc:
            invalid=hasattr(exc,'errors')            # request-validation problem: can never succeed
            msg=(exc.errors()[0].get('msg') if invalid and exc.errors() else str(exc)) or type(exc).__name__
            failed.append({'index':i,'client_event_id':event,'error':str(msg),'retryable':not invalid})
            results.append({'index':i,'client_event_id':event,'ok':False,'error':str(msg),'retryable':not invalid})
    return {'ok':not failed,'synced':len(ids),'observation_ids':ids,'failed':failed,'results':results,'synced_at':time.time()}

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


# ---------------------------------------------------------------------------
# Demo mode and institutional analytics (additive endpoints).
# Every value returned here is computed by the real engine over clearly
# labelled demonstration scenarios. Nothing is presented as field data.
# ---------------------------------------------------------------------------

DEMO_FIELDS=[
 {'code':'AP-KRS-014','name':'Krishna delta paddy block','crop':'paddy','state':'Andhra Pradesh','district':'Krishna','lat':16.51,'lon':80.65,
  'growth_stage':'flowering','condition':'diseaseA','soil_moisture':72,'temperature':30.5,'humidity':86,'weather':'normal','recent_rainfall_mm':18,'recent_irrigation_hours':10,'sensor_reliability':0.95,'image_quality':0.92},
 {'code':'TG-WGL-006','name':'Warangal cotton plot','crop':'cotton','state':'Telangana','district':'Warangal','lat':17.97,'lon':79.59,
  'growth_stage':'vegetative','condition':'holes','soil_moisture':28,'temperature':37.5,'humidity':41,'weather':'heat','recent_rainfall_mm':0,'recent_irrigation_hours':46,'sensor_reliability':0.82,'image_quality':0.88},
 {'code':'MH-NSK-021','name':'Nashik tomato block','crop':'tomato','state':'Maharashtra','district':'Nashik','lat':19.99,'lon':73.78,
  'growth_stage':'fruiting','condition':'healthy','soil_moisture':48,'temperature':27.5,'humidity':58,'weather':'normal','recent_rainfall_mm':2,'recent_irrigation_hours':18,'sensor_reliability':1.0,'image_quality':0.95},
 {'code':'PB-LDH-003','name':'Ludhiana maize strip','crop':'maize','state':'Punjab','district':'Ludhiana','lat':30.90,'lon':75.85,
  'growth_stage':'vegetative','condition':'yellowing','soil_moisture':33,'temperature':31.0,'humidity':49,'weather':'normal','recent_rainfall_mm':0,'recent_irrigation_hours':60,'sensor_reliability':0.6,'image_quality':0.7},
 {'code':'TN-TJV-009','name':'Thanjavur paddy block','crop':'paddy','state':'Tamil Nadu','district':'Thanjavur','lat':10.79,'lon':79.14,
  'growth_stage':'flowering','condition':'healthy','soil_moisture':81,'temperature':28.0,'humidity':90,'weather':'flood','recent_rainfall_mm':38,'recent_irrigation_hours':4,'sensor_reliability':0.9,'image_quality':0.9},
 {'code':'GJ-RJK-017','name':'Rajkot groundnut plot','crop':'groundnut','state':'Gujarat','district':'Rajkot','lat':22.30,'lon':70.80,
  'growth_stage':'seedling','condition':'diseaseB','soil_moisture':39,'temperature':34.0,'humidity':63,'weather':'normal','recent_rainfall_mm':6,'recent_irrigation_hours':30,'sensor_reliability':0.88,'image_quality':0.85},
]

def _demo_analysis(field: dict):
    keys={'crop','condition','growth_stage','soil_moisture','temperature','humidity','weather','recent_rainfall_mm','recent_irrigation_hours','sensor_reliability','image_quality'}
    payload={k:v for k,v in field.items() if k in keys}
    result=analyze_field(AnalysisInput(**payload))
    return payload,result

@app.get('/api/demo/fields')
def demo_fields():
    """Demonstration field set used by Demo Mode. Simulation data, clearly labelled."""
    items=[]
    for f in DEMO_FIELDS:
        payload,result=_demo_analysis(f)
        items.append({'field':f,'inputs':payload,'analysis':result})
    return {'items':items,'data_label':'Simulation Data','note':'Demonstration scenarios computed by the real AstraNex engine. Not live field measurements.'}

@app.get('/api/demo/field/{code}')
def demo_field(code:str):
    field=next((f for f in DEMO_FIELDS if f['code'].lower()==code.lower()),None)
    if not field: raise HTTPException(404,'Unknown demonstration field.')
    payload,result=_demo_analysis(field)
    out={'field':field,'inputs':payload,'analysis':result,'data_label':'Simulation Data'}
    if quantum_router is not None:
        try:
            from .quantum import pipeline as _qp
            out['quantum']=_qp.hybrid_analyze(result,payload)
        except Exception as exc:
            out['quantum']={'available':False,'error':type(exc).__name__,'message':'Quantum layer unavailable. Classical agricultural analysis continues normally.'}
    return out

@app.get('/api/analytics/summary')
def analytics_summary(include_demo: bool = True):
    """Institutional view: aggregates stored observations, plus demo fields when asked."""
    observations=recent_observations(100)
    alerts=list_alerts(100)
    buckets={'disease':[], 'water':[], 'heat':[], 'excess_water':[]}
    warnings={'HIGH':0,'MODERATE':0}
    for o in observations:
        r=(o.get('result') or {}).get('risks') or {}
        for k in buckets:
            if r.get(k) is not None: buckets[k].append(float(r[k]))
    demo_rows=[]
    if include_demo:
        for f in DEMO_FIELDS:
            payload,result=_demo_analysis(f)
            demo_rows.append({'code':f['code'],'name':f['name'],'state':f['state'],'district':f['district'],'crop':f['crop'],
                              'lat':f['lat'],'lon':f['lon'],'risks':result['risks'],'risk_bands':result['risk_bands'],
                              'health_score':result['health_score'],'color':result['color'],'confidence':result['confidence'],
                              'issue':result['issue'],'recommendation':result['recommendation']})
            for k in buckets: buckets[k].append(float(result['risks'][k]))
    for a in alerts:
        sev=a.get('severity')
        if sev in warnings: warnings[sev]+=1
    for row in demo_rows:
        if row['color']=='red': warnings['HIGH']+=1
        elif row['color']=='amber': warnings['MODERATE']+=1
    def dist(values):
        return {'low':sum(1 for v in values if v<45),'moderate':sum(1 for v in values if 45<=v<70),'high':sum(1 for v in values if v>=70),
                'mean':round(sum(values)/len(values),1) if values else None,'samples':len(values)}
    return {
      'fields_monitored': len(list_fields())+len(demo_rows if include_demo else []),
      'stored_observations': len(observations),
      'distributions': {k:dist(v) for k,v in buckets.items()},
      'warnings': warnings,
      'demo_fields': demo_rows,
      'data_label': 'Simulation Data' if include_demo else 'Stored prototype observations',
      'note': 'Prototype analytics. Demonstration fields are synthetic scenarios; no real deployment statistics are represented.'
    }

@app.get('/api/insurer/evidence')
def insurer_evidence(limit:int=20):
    """Evidence trail for crop-insurance workflows. No financial recommendations are produced."""
    rows=[]
    for o in recent_observations(max(1,min(limit,100))):
        r=o.get('result') or {}
        rows.append({'observation_id':o.get('id'),'created_at':o.get('created_at'),'field_id':o.get('field_id'),
                     'crop':o.get('crop'),'issue':r.get('issue'),'confidence':r.get('confidence'),
                     'risks':r.get('risks'),'health_score':r.get('health_score'),
                     'image_ref':o.get('image_ref'),'source':o.get('source'),
                     'evidence':r.get('evidence'),'guardrails':r.get('guardrails')})
    return {'items':rows,'purpose':'Demonstrates how field evidence could support crop-insurance assessment workflows.',
            'disclaimer':'No financial, payout or underwriting recommendation is produced by this prototype.'}

@app.get('/api/system/health')
def system_health():
    """§54 — one consolidated, honestly-reported status for every subsystem.

    Every entry reflects a value actually measured on this call. A component
    the app cannot see from here (the frontend rendering correctly, browser
    connectivity) is out of scope for a server-side check by definition.
    """
    components = {}

    components['backend'] = {'ok': True, 'detail': f"AstraNex API v{app.version}"}

    try:
        with connect() as conn: conn.execute('SELECT 1')
        components['database'] = {'ok': True, 'detail': 'SQLite reachable, schema initialised'}
    except Exception as exc:
        components['database'] = {'ok': False, 'detail': f'{type(exc).__name__}: {exc}'}

    vstat = vision.status()
    components['vision_model'] = {'ok': bool(vstat.get('real_inference')), 'ready': bool(vstat.get('real_inference')), 'detail': f"{vstat['mode']} \u00b7 {vstat['model_version']}" + ('' if vstat.get('real_inference') else ' \u00b7 model weights/runtime not ready')}

    try:
        latest = latest_sensors(None, 1)
        components['sensor_system'] = {'ok': True,
            'detail': 'live device reading available' if latest else 'no device has reported \u2014 simulator/manual input in use'}
    except Exception as exc:
        components['sensor_system'] = {'ok': False, 'detail': f'{type(exc).__name__}: {exc}'}

    components['weather_context'] = {'ok': True,
        'detail': 'context-based weather/rainfall input \u2014 no live external weather API is integrated in this prototype'}

    try:
        obs = recent_observations(1)
        components['offline_queue_and_sync'] = {'ok': True,
            'detail': f"/api/sync reachable \u00b7 {len(obs)} recent observation(s) stored"}
    except Exception as exc:
        components['offline_queue_and_sync'] = {'ok': False, 'detail': f'{type(exc).__name__}: {exc}'}

    quantum_block = {'ok': False, 'detail': 'quantum layer failed to import', 'components': {}}
    if quantum_router is not None:
        try:
            from .quantum import pipeline as _qp
            qh = _qp.system_health()
            quantum_block = {'ok': qh['overall'] == 'ok', 'detail': qh['overall'], 'components': qh['components']}
        except Exception as exc:
            quantum_block = {'ok': False, 'detail': f'{type(exc).__name__}: {exc}', 'components': {}}
    else:
        quantum_block = {'ok': False, 'detail': QUANTUM_LAYER_ERROR or 'unavailable', 'components': {}}

    for name, info in quantum_block['components'].items():
        components[name] = info

    overall_ok = all(c.get('ok') for k, c in components.items()
                     if k not in {'qiskit', 'qiskit_machine_learning', 'benchmark'})
    return {
        'overall': 'ok' if overall_ok else 'degraded',
        'components': components,
        'timestamp': time.time(),
        'note': ('Qiskit / Qiskit Machine Learning being unavailable is a supported, clearly-labelled '
                 'state \u2014 the fallback simulator keeps the rest of the system working.'),
    }


def _validation_report_check() -> dict:
    rep_file=PROJECT_ROOT/'validation'/'field_validation_report.json'
    if rep_file.exists():
        try:
            data=json.loads(rep_file.read_text(encoding='utf-8'))
            if data.get('status') in {'complete','field_validated'}:
                return {'ready':True,'detail':'field validation report present'}
        except Exception:
            pass
    return {'ready': False, 'detail': 'No field-labelled validation corpus is bundled; use scripts/validate_field_dataset.py'}


@app.get('/api/readiness')
def readiness():
    """Deployment readiness matrix; missing prerequisites are explicit."""
    v = vision.status()
    checks = {
        'backend_api': {'ready': True, 'detail': f'AstraNex API v{app.version}'},
        'database': {'ready': False, 'detail': 'not checked'},
        'location_services': {'ready': True, 'detail': 'India-bounded search/reverse geocoding + selectable map/GPS UI'},
        'vision_inference': {'ready': bool(v.get('real_inference')), 'detail': v.get('state')},
        'field_validation_dataset': _validation_report_check(),
        'quantum_qiskit_ml': {'ready': False, 'detail': 'not checked'},
        'qml_trained_model': {'ready': False, 'detail': 'not checked'},
        'benchmark': {'ready': False, 'detail': 'not checked'},
    }
    try:
        with connect() as conn: conn.execute('SELECT 1')
        checks['database']={'ready':True,'detail':'SQLite reachable and schema initialised'}
    except Exception as exc:
        checks['database']={'ready':False,'detail':f'{type(exc).__name__}: {exc}'}
    if quantum_router is not None:
        try:
            from .quantum import pipeline as _qp
            qh=_qp.system_health(); rt=qh.get('runtime',{}); qc=qh.get('components',{})
            checks['quantum_qiskit_ml']={'ready':bool(rt.get('qiskit_machine_learning_installed') and rt.get('qiskit_execution')),'detail':rt.get('execution_label','unavailable')}
            checks['qml_trained_model']={'ready':bool(qc.get('qml_model',{}).get('ok')),'detail':qc.get('qml_model',{}).get('detail','not trained')}
            checks['benchmark']={'ready':bool(qc.get('benchmark',{}).get('ok')),'detail':qc.get('benchmark',{}).get('detail','not available')}
        except Exception as exc:
            checks['quantum_qiskit_ml']={'ready':False,'detail':f'{type(exc).__name__}: {exc}'}
    demo_ready=checks['backend_api']['ready'] and checks['database']['ready']
    qml_ready=all(x['ready'] for x in checks.values())
    field_ai_ready=checks['backend_api']['ready'] and checks['database']['ready'] and checks['vision_inference']['ready']
    return {'overall':'ready' if demo_ready else 'blocked','demo_ready':demo_ready,'field_ai_ready':field_ai_ready,'qml_production_ready':qml_ready,'checks':checks,'next_steps':[k for k,x in checks.items() if not x['ready']]}


if quantum_router is not None:
    app.include_router(quantum_router)
