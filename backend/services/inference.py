from __future__ import annotations
import os, time, json, threading
from pathlib import Path

PLANTVILLAGE_LABELS = [
    "Apple___Apple_scab","Apple___Black_rot","Apple___Cedar_apple_rust","Apple___healthy",
    "Blueberry___healthy","Cherry_(including_sour)___Powdery_mildew","Cherry_(including_sour)___healthy",
    "Corn_(maize)___Cercospora_leaf_spot Gray_leaf_spot","Corn_(maize)___Common_rust_","Corn_(maize)___Northern_Leaf_Blight","Corn_(maize)___healthy",
    "Grape___Black_rot","Grape___Esca_(Black_Measles)","Grape___Leaf_blight_(Isariopsis_Leaf_Spot)","Grape___healthy",
    "Orange___Haunglongbing_(Citrus_greening)","Peach___Bacterial_spot","Peach___healthy","Pepper,_bell___Bacterial_spot","Pepper,_bell___healthy",
    "Potato___Early_blight","Potato___Late_blight","Potato___healthy","Raspberry___healthy","Soybean___healthy","Squash___Powdery_mildew",
    "Strawberry___Leaf_scorch","Strawberry___healthy","Tomato___Bacterial_spot","Tomato___Early_blight","Tomato___Late_blight","Tomato___Leaf_Mold",
    "Tomato___Septoria_leaf_spot","Tomato___Spider_mites Two-spotted_spider_mite","Tomato___Target_Spot","Tomato___Tomato_Yellow_Leaf_Curl_Virus",
    "Tomato___Tomato_mosaic_virus","Tomato___healthy"
]

RECOMMENDATIONS = {
    "healthy": "No disease pattern was detected by the model. Continue routine scouting and monitor new growth.",
    "Early_blight": "Remove badly affected leaves, improve airflow and avoid prolonged leaf wetness. Confirm locally before applying any crop-protection product.",
    "Late_blight": "Isolate affected plants where practical, remove severely affected tissue and reduce leaf wetness. Confirm urgently with local agricultural guidance.",
    "Bacterial_spot": "Avoid working plants while foliage is wet, remove heavily affected material and use sanitation practices. Confirm the disease before treatment.",
    "Leaf_Mold": "Improve ventilation and reduce prolonged high humidity/leaf wetness. Confirm the diagnosis before treatment.",
    "Septoria_leaf_spot": "Remove infected lower leaves and improve airflow. Avoid overhead watering where practical and confirm the diagnosis locally.",
    "Target_Spot": "Remove severely affected tissue, improve canopy airflow and monitor nearby plants. Confirm the diagnosis before treatment.",
    "Tomato_Yellow_Leaf_Curl_Virus": "Inspect for whitefly pressure and affected plants; manage vectors using locally approved integrated pest-management guidance and confirm the diagnosis.",
    "Tomato_mosaic_virus": "Remove suspect plants/material carefully, sanitize tools and avoid spreading sap between plants. Confirm with local guidance.",
}

def pretty_label(label: str):
    crop, _, disease = label.partition("___")
    crop = crop.replace("_(maize)", "").replace(",_bell", "").replace("_(including_sour)", "")
    crop = crop.replace("_", " ").strip()
    disease = disease.replace("_", " ").replace("  ", " ").strip()
    if disease.lower() == "healthy": disease = "Healthy leaf"
    return crop, disease

class VisionInference:
    """Real PlantVillage ONNX inference with optional PlantDoc model override.

    The bundled application does not ship large model weights. On first inference,
    if no local model is configured, it downloads the published CropGuard PlantVillage
    ONNX model and class map through huggingface_hub. A separately trained PlantDoc
    model can be supplied with ASTRANEX_PLANTDOC_MODEL_PATH and a JSON class list.
    """
    def __init__(self):
        self.model_path = os.getenv('ASTRANEX_MODEL_PATH','').strip() or str(Path(__file__).resolve().parents[1]/'models'/'cropguard.onnx')
        self.dataset = 'PlantVillage'
        self.model_repo = os.getenv('ASTRANEX_MODEL_REPO','AbhiCommits/cropguard-models')
        self.model_filename = os.getenv('ASTRANEX_MODEL_FILENAME','cropguard.onnx')
        self.session = None
        self.runtime = 'not_loaded'
        self.labels = PLANTVILLAGE_LABELS
        self.temperature = 0.591
        self._attempted = False
        self._lock = threading.RLock()
        self.labels_source = 'built-in PlantVillage-38 list'

    @property
    def ready(self):
        self._ensure_loaded()
        return self.session is not None

    def _ensure_loaded(self):
        if self.session is not None or self._attempted:
            return
        with self._lock:
            if self.session is not None or self._attempted:
                return
            self._attempted = True
            path = self.model_path
            if path and Path(path).exists():
                self._load(path)
                return
            auto = os.getenv('ASTRANEX_AUTO_DOWNLOAD_MODEL','0').lower() not in {'0','false','no'}
            if not auto:
                return
            try:
                from huggingface_hub import hf_hub_download
                path = hf_hub_download(self.model_repo, self.model_filename)
                self._load(path)
            except Exception as exc:
                self.runtime = f'model_download_unavailable: {type(exc).__name__}'

    def prepare(self):
        """Explicitly prepare the model, optionally downloading it once."""
        with self._lock:
            self._attempted = True
            if self.session is not None:
                return True
            path=self.model_path
            if path and Path(path).exists():
                self._load(path)
                return self.session is not None
            try:
                from huggingface_hub import hf_hub_download
                path=hf_hub_download(self.model_repo, self.model_filename)
                self._load(path)
                return self.session is not None
            except Exception as exc:
                self.runtime=f'model_download_unavailable: {type(exc).__name__}'
                return False

    def _load(self, path):
        try:
            import onnxruntime as ort
            session = ort.InferenceSession(path, providers=['CPUExecutionProvider'])
            labels = self._labels_next_to(path)
            # The class list must match the network's output width, otherwise every
            # prediction would be mislabelled. Refuse to serve rather than guess.
            out_shape = session.get_outputs()[0].shape
            width = out_shape[-1] if out_shape and isinstance(out_shape[-1], int) else None
            if width is not None and width != len(labels):
                self.session = None
                self.runtime = f'model_class_mismatch: network has {width} outputs, class list has {len(labels)}'
                return
            self.labels = labels
            self.session = session
            self.model_path = str(path)
            self.runtime = 'onnxruntime-cpu'
        except Exception as exc:
            self.session = None
            self.runtime = f'model_runtime_unavailable: {type(exc).__name__}'

    def _labels_next_to(self, model_path):
        """Prefer the class map published with the weights (classes.json) over the built-in list."""
        cand = Path(model_path).with_name('classes.json')
        if cand.exists():
            try:
                data = json.loads(cand.read_text(encoding='utf-8'))
                if isinstance(data, dict):
                    data = data.get('classes') or data.get('labels') or list(data.values())
                if isinstance(data, list) and data and all(isinstance(x, str) for x in data):
                    self.labels_source = 'classes.json'
                    return [str(x) for x in data]
            except Exception:
                pass
        self.labels_source = 'built-in PlantVillage-38 list'
        return PLANTVILLAGE_LABELS

    def supported_crop_names(self):
        names=set()
        for label in self.labels:
            crop,_,_=label.partition('___')
            crop=crop.replace('_(maize)','').replace(',_bell','').replace('_(including_sour)','').replace('_',' ').strip().lower()
            names.add(crop)
        return sorted(names)

    def status(self):
        # Status must never trigger a network/model download. Image analysis
        # performs lazy model preparation when needed.
        model_file_exists=bool(self.model_path and Path(self.model_path).exists())
        onnx_runtime_available=self.runtime == 'onnxruntime-cpu' or bool(self.session)
        return {
            'mode':'real-vision' if self.session else 'context-only',
            'model_name':'CropGuard ResNet50 ONNX (FP32)',
            'model_version':'PlantVillage-38class',
            'model_source':self.model_repo,
            'model_file':Path(self.model_path).name if self.model_path else self.model_filename,
            'dataset':self.dataset,
            'supported_crops':len(self.supported_crop_names()),
            'download_target':'cropguard.onnx (FP32) — the published serving model',
            'classes':len(self.labels),
            'class_map_source':self.labels_source,
            'input_resolution':'224x224',
            'runtime':self.runtime,
            'state':'ready' if self.session else 'context-only; run POST /api/model/prepare or configure ASTRANEX_MODEL_PATH',
            'real_inference':bool(self.session),
            'model_file_present':model_file_exists,
            'onnxruntime_ready':onnx_runtime_available,
            'inference_ready':bool(self.session),
            'note':'PlantVillage-trained screening model; field images can be out-of-distribution.'
        }

    def _preprocess(self, data):
        from PIL import Image
        import io, numpy as np
        im=Image.open(io.BytesIO(data)).convert('RGB')
        # Training recipe: resize short side to 256, center crop 224, ImageNet normalization.
        w,h=im.size
        scale=256/min(w,h)
        im=im.resize((round(w*scale),round(h*scale)),Image.Resampling.BILINEAR)
        left=(im.width-224)//2; top=(im.height-224)//2
        im=im.crop((left,top,left+224,top+224))
        arr=np.asarray(im,dtype=np.float32)/255.0
        mean=np.array([0.485,0.456,0.406],dtype=np.float32)
        std=np.array([0.229,0.224,0.225],dtype=np.float32)
        arr=(arr-mean)/std
        return np.transpose(arr,(2,0,1))[None,...]

    def _plant_likelihood(self, data: bytes):
        """Conservative pre-inference gate for obvious non-plant uploads.

        This intentionally sits before PlantVillage inference. PlantVillage is a
        crop/leaf classifier, not a general-purpose image classifier, so sending
        portraits, documents, rooms, vehicles, etc. straight to it can produce a
        confident but meaningless crop/disease label. This gate is heuristic only;
        it does not claim to be a trained plant detector.
        """
        try:
            from PIL import Image
            import io, numpy as np
            im=Image.open(io.BytesIO(data)).convert('RGB').resize((192,192))
            a=np.asarray(im,dtype=np.float32)
            r,g,b=a[:,:,0],a[:,:,1],a[:,:,2]
            green=((g>42)&(g>r*1.08)&(g>b*1.03)&(g-r>7)).astype(np.float32)
            yellow=((r>78)&(g>72)&(b<135)&(np.abs(r-g)<85)&(g>b*1.05)).astype(np.float32)
            skin=((r>92)&(g>48)&(b>35)&(r>g*1.16)&(r>b*1.28)&((r-g)>18)).astype(np.float32)
            overall_green=float(green.mean()); overall_yellow=float(yellow.mean()); skin_ratio=float(skin.mean())
            c=a[48:144,48:144]
            cr,cg,cb=c[:,:,0],c[:,:,1],c[:,:,2]
            center_green=float(((cg>42)&(cg>cr*1.08)&(cg>cb*1.03)&(cg-cr>7)).mean())
            center_yellow=float(((cr>78)&(cg>72)&(cb<135)&(np.abs(cr-cg)<85)&(cg>cb*1.05)).mean())
            vegetation=0.55*overall_green + 0.25*center_green + 0.20*overall_yellow + 0.10*center_yellow
            # Portrait-like images with little vegetation should be rejected even
            # when a green background is present.
            portrait_penalty=max(0.0, skin_ratio-0.18)*0.8 if overall_green<0.08 else 0.0
            score=max(0.0,min(1.0,(vegetation*3.2)-portrait_penalty))
            return round(float(score),3), round(overall_green,3), round(overall_yellow,3), round(center_green,3), round(skin_ratio,3)
        except Exception:
            # The heuristic itself failed. That says nothing about the photo, so do not
            # reject it as "not a plant" -- report "unverified" and let the model decide.
            return None


    def _visual_screening(self, data: bytes):
        """Lightweight, dependency-free visual evidence when no trained model is available.

        This is deliberately NOT a disease classifier. It extracts conservative image
        evidence so the upload workflow remains useful offline and never pretends to
        have model-level diagnostic accuracy.
        """
        try:
            from PIL import Image, ImageStat, ImageFilter
            import io, numpy as np
            im=Image.open(io.BytesIO(data)).convert('RGB').resize((224,224))
            a=np.asarray(im,dtype=np.float32)
            r,g,b=a[:,:,0],a[:,:,1],a[:,:,2]
            green=((g>38)&(g>r*1.04)&(g>b*1.02)&((g-r)>4)).mean()
            yellow=((r>75)&(g>68)&(b<150)&(g>b*1.02)&(np.abs(r-g)<95)).mean()
            dark=((r<45)&(g<45)&(b<45)).mean()
            bright=((r>240)&(g>240)&(b>240)).mean()
            edge=float(ImageStat.Stat(im.convert('L').filter(ImageFilter.FIND_EDGES)).mean[0])
            vegetation=float(min(1.0, green*2.2 + yellow*1.2))
            quality=float(max(0.0,min(1.0, 0.55 + vegetation*0.35 + min(edge/35,1)*0.15 - dark*0.35 - bright*0.25)))
            if vegetation>=0.10:
                label='Leaf/vegetation evidence detected'
                msg='The image contains visible green/yellow vegetation. Trained disease-model weights are unavailable, so this result is visual screening only.'
            elif vegetation>=0.04:
                label='Possible plant evidence — verify image'
                msg='Some plant-like color evidence was detected, but it is too weak for a reliable crop assessment.'
            else:
                label='Insufficient plant evidence'
                msg='The image does not contain enough visible plant/leaf evidence for a useful visual screen.'
            return {'status':'visual_screening','prediction':'unknown','confidence':round(min(0.45,0.18+vegetation*0.8),3),
                    'message':msg,'real_inference':False,'visual_label':label,'plant_image_score':round(vegetation,3),
                    'green_ratio':round(float(green),3),'yellow_ratio':round(float(yellow),3),'edge_score':round(edge,2),
                    'image_quality_estimate':round(quality,3)}
        except Exception as exc:
            return {'status':'visual_screening','prediction':'unknown','confidence':0.0,'real_inference':False,
                    'visual_label':'Visual screening unavailable','message':f'Image was received, but visual screening is unavailable: {type(exc).__name__}'}

    def analyze(self, image_bytes: bytes, expected_crop: str|None=None):
        self._ensure_loaded()
        gate = self._plant_likelihood(image_bytes)
        gate_ok = gate is not None
        plant_score, green_ratio, yellow_ratio, center_green, skin_ratio = gate if gate_ok else (0.0, 0.0, 0.0, 0.0, 0.0)
        # Reject only images that are very unlikely to contain plant evidence.
        # The previous gate was too aggressive for close-up leaves with shadows,
        # brown disease lesions, indoor lighting, or non-green foliage.
        if gate_ok and ((plant_score < 0.055 and green_ratio < 0.025 and yellow_ratio < 0.018 and skin_ratio > 0.30) or (plant_score < 0.035 and green_ratio < 0.012 and yellow_ratio < 0.010)):
            return {'status':'not_a_plant_image','prediction':'unknown','confidence':0.0,
                    'message':'Very little plant/leaf evidence was found. Capture a closer image with the leaf filling most of the frame.',
                    'real_inference':False,'plant_image_score':plant_score,'green_ratio':green_ratio,'yellow_ratio':yellow_ratio,'center_green_ratio':center_green}
        if not self.session:
            fallback=self._visual_screening(image_bytes)
            fallback['model_available']=False
            fallback['model_message']='No trained ONNX weights are installed. Set ASTRANEX_MODEL_PATH or run the model preparation script on a networked machine.'
            return fallback
        started=time.perf_counter()
        try:
            import numpy as np
            batch=self._preprocess(image_bytes)
            inp=self.session.get_inputs()[0].name
            out=self.session.get_outputs()[0].name
            logits=self.session.run([out],{inp:batch})[0][0]
            logits=np.asarray(logits,dtype=np.float32)
            # Published serving temperature for this model.
            logits=logits/self.temperature
            logits=logits-logits.max()
            probs=np.exp(logits); probs=probs/probs.sum()
            order=np.argsort(probs)[::-1][:8]
            top=[]
            for i in order:
                crop,disease=pretty_label(self.labels[int(i)])
                top.append({'label':self.labels[int(i)],'crop':crop,'disease':disease,'confidence':float(probs[int(i)])})
            if expected_crop:
                wanted=str(expected_crop).strip().lower()
                aliases={'paddy':'rice','chilli':'pepper','maize':'corn','brinjal':'eggplant'}
                wanted_alias=aliases.get(wanted,wanted)
                matching=[x for x in top if wanted_alias in x['crop'].lower() or wanted in x['crop'].lower()]
                if matching:
                    top=matching[:3]
                else:
                    # Do not throw away a real model result merely because the
                    # selected crop is not present in the top-8. PlantVillage is
                    # a closed 38-class classifier, so a field image can be
                    # out-of-scope. Return the model evidence as an explicit
                    # verification state instead of silently forcing a crop.
                    # (Always return this branch explicitly — a falsy 0.0
                    # confidence must not silently fall through to the
                    # unfiltered top-8 list below as if the crop had matched.)
                    best_conf=float(top[0]['confidence']) if top else 0.0
                    best_crop=top[0]['crop'] if top else 'an unsupported crop'
                    return {'status':'crop_mismatch','prediction':top[0]['disease'] if top else 'unknown',
                            'crop':top[0]['crop'] if top else None,'confidence':best_conf,
                            'message':f'The model sees {best_crop}, while {expected_crop} is selected. This model covers PlantVillage crops only; choose the detected crop or use a validated field model.',
                            'real_inference':True,'verification_required':True,'plant_image_score':plant_score,'green_ratio':green_ratio,'yellow_ratio':yellow_ratio,'center_green_ratio':center_green,'skin_ratio':skin_ratio,'top_predictions':top[:3],
                            'dataset':'PlantVillage','model_name':'CropGuard ResNet50 ONNX'}
            top=top[:3]
            best=top[0]
            _, raw_disease=pretty_label(best['label'])
            key=best['label'].split('___',1)[-1]
            rec=RECOMMENDATIONS.get(key, 'Verify the predicted condition with field symptoms and local agricultural guidance before taking treatment action.')
            if best['confidence'] < 0.55:
                return {'status':'uncertain','prediction':'uncertain crop condition','confidence':float(best['confidence']),
                        'message':'The model signal is too uncertain to name a disease reliably. Capture a close-up leaf image with good lighting and verify the symptoms in the field.',
                        'real_inference':True,'plant_image_score':plant_score,'green_ratio':green_ratio,'yellow_ratio':yellow_ratio,'center_green_ratio':center_green,'skin_ratio':skin_ratio,'top_predictions':top[:3],
                        'dataset':'PlantVillage','model_name':'CropGuard ResNet50 ONNX'}
            return {'status':'ok','prediction':raw_disease,'crop':best['crop'],'confidence':best['confidence'],
                    'top_predictions':top,'recommendation':rec,'latency_ms':round((time.perf_counter()-started)*1000,2),
                    'real_inference':True,'dataset':'PlantVillage','model_name':'CropGuard ResNet50 ONNX','plant_image_score':plant_score,'green_ratio':green_ratio,'yellow_ratio':yellow_ratio,'center_green_ratio':center_green,'skin_ratio':skin_ratio}
        except Exception as exc:
            return {'status':'inference_error','prediction':'unknown','confidence':0.0,'real_inference':False,
                    'message':f'Model inference failed: {type(exc).__name__}: {exc}'}

vision=VisionInference()
