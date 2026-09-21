/* Router, field-scan experience, demo mode and system status. */
(function () {
  const API = window.AX_API, V = window.AX_VIZ, P = window.AX_PAGES, D = window.AX_DATA, T = window.AX_I18N;
  const $ = id => document.getElementById(id);
  const esc = V.esc, num = V.num;

  /* ---------------- routing ---------------- */
  const ROUTES = ['home', 'farmer', 'intelligence', 'scan', 'quantum', 'warnings', 'network', 'analytics', 'library', 'research', 'about'];

  function route() {
    const id = (location.hash.replace('#/', '') || 'home').split('?')[0];
    const page = ROUTES.includes(id) ? id : 'home';
    document.querySelectorAll('.page').forEach(p => p.classList.toggle('active', p.id === 'page-' + page));
    document.querySelectorAll('[data-nav]').forEach(a =>
      a.setAttribute('aria-current', a.dataset.nav === page ? 'page' : 'false'));
    $('nav').classList.remove('open');
    window.scrollTo({ top: 0, behavior: 'auto' });
    const render = { home: P.home, farmer: P.farmer, intelligence: P.intelligence, quantum: P.quantum, warnings: P.warnings,
      network: P.network, analytics: P.analytics, library: P.library, research: P.research, about: P.about };
    if (render[page]) { try { render[page](); } catch (e) { console.error(e); } }
    if (page === 'scan') initScan();
  }
  window.addEventListener('hashchange', route);

  document.addEventListener('click', e => {
    const go = e.target.closest('[data-go]');
    if (go) { location.hash = '#/' + go.dataset.go; }
  });
  $('burger').addEventListener('click', () => {
    const nav = $('nav'); const open = nav.classList.toggle('open');
    $('burger').setAttribute('aria-expanded', String(open));
  });
  document.querySelectorAll('.lang-switch button').forEach(b =>
    b.addEventListener('click', () => T.set(b.dataset.lang)));
  window.addEventListener('ax:lang', () => route());

  /* ---------------- system status ---------------- */
  function paintStatus(s) {
    const set = (dotId, textId, text, tone) => {
      $(textId).textContent = text;
      $(dotId).className = 'dot ' + tone;
    };
    set('stBackendDot', 'stBackend', s.backend, s.backend === 'online' ? 'ok' : 'bad');
    set('stVisionDot', 'stVision', s.vision, s.vision === 'unavailable' ? 'bad' : 'ok');
    set('stQuantumDot', 'stQuantum', s.quantum, s.quantum === 'unavailable' ? 'bad' : s.quantum.toLowerCase().includes('fallback') ? 'warn' : 'ok');
    const qBadge = document.querySelector('[data-runtime-badge]');
    if (qBadge) qBadge.textContent = s.quantum || 'Quantum runtime · checking';
    set('stNetDot', 'stNet', navigator.onLine ? 'online' : 'offline', navigator.onLine ? 'ok' : 'warn');
    const n = API.queueSize();
    $('stQueueWrap').classList.toggle('hide', n === 0);
    $('stQueue').textContent = n;
    const os = $('offlineState');
    if (os) { os.textContent = navigator.onLine && s.backend === 'online' ? 'Online' : 'Offline — scans are queued'; os.className = 'tag ' + (navigator.onLine && s.backend === 'online' ? 'green' : 'amber'); }
  }
  window.addEventListener('ax:health', e => paintStatus(e.detail));
  window.addEventListener('ax:queue', () => paintStatus(API.state));
  window.addEventListener('online', () => API.refreshHealth());
  window.addEventListener('offline', () => API.refreshHealth());

  /* ---------------- field scan ---------------- */
  const WEATHERS = [['normal', 'Normal'], ['heat', 'Heat'], ['drought', 'Drought'], ['flood', 'Flood / heavy rain']];
  const CONDITIONS = [['healthy', 'No visible symptom'], ['diseaseA', 'Spots / discoloration'],
    ['diseaseB', 'Wilting / stress pattern'], ['yellowing', 'Yellowing leaves'],
    ['holes', 'Holes / chewed edges'], ['unknown', 'Not sure']];

  const scan = { file: null, weather: 'normal', condition: 'healthy', busy: false, location: null };

  function initScan() {
    if ($('scanCrop').dataset.done) return;
    $('scanCrop').dataset.done = '1';
    $('scanCrop').innerHTML = D.CROPS.map(c => `<option value="${c.id}">${c.icon} ${esc(c.en)}</option>`).join('');
    $('scanField').innerHTML = '<option value="">Primary field</option>';
    API.fields().then(f => {
      const items = f.items || [];
      if (items.length) $('scanField').innerHTML = items.map(x => `<option value="${x.id}">${esc(x.name)} · ${esc(x.crop || '')}</option>`).join('');
    });
    $('weatherChips').innerHTML = WEATHERS.map(([v, l], i) =>
      `<button class="chip" data-weather="${v}" aria-pressed="${i === 0}">${esc(l)}</button>`).join('');
    $('conditionChips').innerHTML = CONDITIONS.map(([v, l], i) =>
      `<button class="chip" data-condition="${v}" aria-pressed="${i === 0}">${esc(l)}</button>`).join('');
    $('weatherChips').addEventListener('click', e => pickChip(e, 'weather'));
    $('conditionChips').addEventListener('click', e => pickChip(e, 'condition'));

    bindSlider('scanMoisture', 'valMoisture', v => v + '%');
    bindSlider('scanTemp', 'valTemp', v => v + '°C');
    bindSlider('scanHumidity', 'valHumidity', v => v + '%');
    bindSlider('scanRain', 'valRain', v => v + ' mm');

    const dz = $('dropzone'), fi = $('fileInput');
    dz.addEventListener('click', () => fi.click());
    dz.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); fi.click(); } });
    ['dragenter', 'dragover'].forEach(ev => dz.addEventListener(ev, e => { e.preventDefault(); dz.classList.add('drag'); }));
    ['dragleave', 'drop'].forEach(ev => dz.addEventListener(ev, e => { e.preventDefault(); dz.classList.remove('drag'); }));
    dz.addEventListener('drop', e => { if (e.dataTransfer.files[0]) setFile(e.dataTransfer.files[0]); });
    fi.addEventListener('change', () => { if (fi.files[0]) setFile(fi.files[0]); });
    $('clearImage').addEventListener('click', () => {
      scan.file = null; fi.value = ''; $('previewWrap').classList.add('hide'); $('dropzone').classList.remove('hide');
    });
    const prep = $('prepareModelBtn'); if (prep) prep.addEventListener('click', async () => { prep.disabled=true; prep.textContent='Preparing AI model…'; const out=await API.prepareModel(); prep.disabled=false; prep.textContent='Prepare AI model'; V.toast(out.ok ? 'AI model prepared — reload status' : (out.message||'Model preparation failed'), !out.ok); API.refreshHealth(); });
    $('analyzeBtn').addEventListener('click', runScan);
    $('syncNow').addEventListener('click', async () => {
      const out = await API.syncQueue();
      V.toast(out.ok ? `Synced ${out.synced} queued scan(s)` : out.message, !out.ok);
      API.refreshHealth();
    });
    renderStages(-1);
    initLocation();
    renderScanHistory();
  }

  async function initLocation() {
    const input = $('locationInput'), btn = $('locationSearch'), results = $('locationResults'), selected = $('selectedLocation');
    const canvas = $('fieldMapCanvas'), marker = $('fieldMapMarker'), gps = $('useMyLocation'), hint = $('mapHint');
    if (!input || input.dataset.bound) return;
    input.dataset.bound = '1';

    const normalise = loc => {
      const lat = Number(loc?.lat ?? loc?.latitude), lon = Number(loc?.lon ?? loc?.longitude);
      if (!Number.isFinite(lat) || !Number.isFinite(lon)) throw new Error('The selected location has invalid coordinates.');
      if (lat < 6 || lat > 38 || lon < 68 || lon > 98) throw new Error('Please select a location inside India.');
      return {...loc, lat, lon, display_name: loc.display_name || loc.name || 'Selected field location'};
    };
    /* calibrated against the image's own graticule (see viz.js GEO) — the old linear guess was 2–9° off */
    const project = (lat, lon) => {
      const f = V.geoToFrac(lat, lon);
      return {left: Math.max(1, Math.min(99, f.fx * 100)), top: Math.max(1, Math.min(99, f.fy * 100))};
    };
    const setMarker = loc => {
      if (!marker) return;
      const p = project(loc.lat, loc.lon);
      marker.style.left = `${p.left}%`; marker.style.top = `${p.top}%`; marker.classList.remove('hide');
    };
    const showSelected = raw => {
      const loc = normalise(raw);
      scan.location = loc;
      setMarker(loc);
      selected.classList.remove('hide');
      selected.innerHTML = `<div><b>📍 ${esc(loc.display_name)}</b><span class="dim">${loc.lat.toFixed(6)}, ${loc.lon.toFixed(6)}</span></div><button class="btn small ghost" id="clearLocation" type="button">Clear</button>`;
      $('locationStatus').textContent = 'Location selected'; $('locationStatus').className = 'tag green';
      if (hint) hint.textContent = 'Field point selected. You can search again or adjust it on the map.';
      results.classList.add('hide');
      $('clearLocation').onclick = () => {
        scan.location = null; selected.classList.add('hide'); marker?.classList.add('hide');
        $('locationStatus').textContent='Location optional'; $('locationStatus').className='tag';
        if (hint) hint.textContent='Search, click the map, or use GPS.';
      };
    };
    const reverseAt = async (lat, lon) => {
      const out = await API.get(`/api/geocode/reverse?lat=${encodeURIComponent(lat)}&lon=${encodeURIComponent(lon)}`);
      return normalise(out);
    };
    const mapClick = async e => {
      if (!canvas) return;
      const r = canvas.getBoundingClientRect();
      const x = Math.max(0, Math.min(1, (e.clientX-r.left)/r.width));
      const y = Math.max(0, Math.min(1, (e.clientY-r.top)/r.height));
      const {lat, lon} = V.fracToGeo(x, y);
      marker.style.left = `${x*100}%`; marker.style.top = `${y*100}%`; marker.classList.remove('hide');
      if (hint) hint.textContent='Resolving selected point…';
      try { showSelected(await reverseAt(lat, lon)); }
      catch (err) { marker.classList.add('hide'); V.toast(err.message || 'Could not resolve that point.', true); if (hint) hint.textContent='Try a point clearly inside India or search by name.'; }
    };
    canvas?.addEventListener('click', mapClick);
    const search = async () => {
      const q = input.value.trim(); if (q.length < 2) { V.toast('Type at least 2 characters', true); return; }
      btn.disabled = true; btn.textContent = 'Searching…'; results.classList.remove('hide'); results.innerHTML='<span class="mono">finding Indian locations…</span>';
      try {
        const out = await API.get('/api/geocode/search?q=' + encodeURIComponent(q));
        const rows = (out.items || out.results || []).map(r => { try { return normalise(r); } catch { return null; } }).filter(Boolean);
        results.innerHTML = rows.length ? rows.slice(0,6).map((x,i)=>`<button class="location-result" data-i="${i}" type="button"><b>${esc(x.display_name)}</b><span class="mono">${x.lat.toFixed(4)}, ${x.lon.toFixed(4)}</span></button>`).join('') : '<span class="dim">No Indian location found. Try a district, village or landmark.</span>';
        results.querySelectorAll('.location-result').forEach((b,i)=>b.onclick=()=>showSelected(rows[i]));
      } catch(e) { results.innerHTML=`<span class="dim">${esc(e.message || 'Location lookup is unavailable.')}</span>`; }
      btn.disabled=false; btn.textContent='Find location';
    };
    btn.addEventListener('click', search); input.addEventListener('keydown', e=>{ if(e.key==='Enter') search(); });
    gps?.addEventListener('click', () => {
      if (!navigator.geolocation) { V.toast('This browser does not provide GPS location.', true); return; }
      gps.disabled=true; gps.textContent='Locating…'; if (hint) hint.textContent='Waiting for device location…';
      navigator.geolocation.getCurrentPosition(async pos => {
        try { showSelected(await reverseAt(pos.coords.latitude, pos.coords.longitude)); }
        catch (err) { V.toast(err.message || 'GPS point could not be resolved inside India.', true); }
        finally { gps.disabled=false; gps.textContent='Use my location'; }
      }, err => { gps.disabled=false; gps.textContent='Use my location'; if (hint) hint.textContent='GPS unavailable. Search or click the map instead.'; V.toast(err.message || 'Location permission was denied.', true); }, {enableHighAccuracy:true, timeout:10000, maximumAge:60000});
    });
  }

  function renderScanHistory() {
    const host=$('scanHistory'); if(!host) return;
    const local=API.readHistory();
    const latest=local.slice(0,8);
    host.innerHTML=`<div class="section-head" style="margin-bottom:1rem"><p class="mono">Your device history</p><h2 style="font-size:1.7rem">Recent field scans</h2><p class="lede" style="font-size:.95rem">Stored locally so the history remains useful during intermittent connectivity.</p></div>
      ${latest.length ? `<div class="history-grid">${latest.map((h,i)=>{const r=h.result||{};const date=h.at?new Date(h.at).toLocaleString():'';return `<article class="history-card lift"><div class="row" style="justify-content:space-between"><span class="mono">${esc(date)}</span><span class="tag ${r.color||'amber'}">${esc(r.health_status||'Scan')}</span></div><h3 style="margin:.35rem 0">${esc(T.cropName(h.crop||'tomato'))}</h3><div class="history-score"><b>${num(r.health_score, '', 0)}</b><span>/100 health</span></div><div class="row"><span class="tag ${V.band((r.risks||{}).disease)}">Disease ${num((r.risks||{}).disease,'%',0)}</span><span class="tag">Confidence ${num(r.confidence,'%',0)}</span></div><button class="btn small ghost history-open" data-index="${i}" style="margin-top:.7rem">View evidence</button></article>`}).join('')}</div>` : '<div class="card"><h3>No scans stored yet</h3><p class="dim">Run your first field scan and AstraNex will build the history automatically.</p></div>'}`;
    host.querySelectorAll('.history-open').forEach(b=>b.onclick=()=>{const h=local[Number(b.dataset.index)]; if(h&&h.result){renderResult(h.result,h.quantum||{available:false},'local history',h.inputs||{crop:h.crop},{noImage:true}); window.scrollTo({top:$('scanResult').offsetTop-90,behavior:'smooth'});}});
  }

  function pickChip(e, key) {
    const b = e.target.closest('.chip'); if (!b) return;
    e.currentTarget.querySelectorAll('.chip').forEach(x => x.setAttribute('aria-pressed', String(x === b)));
    scan[key] = b.dataset[key];
  }

  function bindSlider(id, out, fmt) {
    const el = $(id);
    const paint = () => { $(out).textContent = fmt(el.value); };
    el.addEventListener('input', paint); paint();
  }

  function setFile(file) {
    if (!/^image\/(jpeg|png|webp)$/.test(file.type)) { V.toast('Use a JPEG, PNG or WebP image', true); return; }
    if (file.size > 2 * 1024 * 1024) { V.toast('Image is larger than 2 MB — take a smaller photo', true); return; }
    scan.file = file;
    if (scan.previewUrl) URL.revokeObjectURL(scan.previewUrl);
    const url = URL.createObjectURL(file);
    scan.previewUrl = url;
    $('previewImg').src = url;
    $('previewMeta').textContent = `${file.name.slice(0, 28)} · ${(file.size / 1024).toFixed(0)} KB`;
    $('previewWrap').classList.remove('hide');
    $('dropzone').classList.add('hide');
  }

  const STAGES = [
    ['Image received', 'Field, crop, growth stage and image accepted'],
    ['Image quality checked', 'Screened before any diagnosis is attempted'],
    ['Sensor context loaded', 'Moisture, temperature, humidity and reliability'],
    ['Weather context loaded', 'Rainfall and weather risk applied'],
    ['Agricultural features extracted', 'Eight multimodal features from the engine'],
    ['Classical baseline evaluated', 'Logistic regression on the selected features'],
    ['Quantum circuit evaluated', '4-qubit QML circuit on the reported backend; inference is blocked until a trained model is available'],
    ['Risk synthesis and recommendation', 'Early-warning level, confidence and next step']
  ];

  function renderStages(activeIndex) {
    $('scanStages').innerHTML = STAGES.map(([t, s], i) => `
      <div class="scan-stage ${i === activeIndex ? 'active' : i < activeIndex ? 'done' : ''}">
        <div class="scan-bead"></div>
        <div><b>${esc(t)}</b><small>${esc(s)}</small></div>
      </div>`).join('');
  }

  function payload() {
    return {
      crop: $('scanCrop').value,
      condition: scan.condition,
      field_id: $('scanField').value ? Number($('scanField').value) : null,
      growth_stage: $('scanStage').value,
      soil_moisture: Number($('scanMoisture').value),
      temperature: Number($('scanTemp').value),
      humidity: Number($('scanHumidity').value),
      weather: scan.weather,
      recent_rainfall_mm: Number($('scanRain').value),
      recent_irrigation_hours: 24,
      connectivity: navigator.onLine ? 'online' : 'offline',
      sensor_reliability: Number($('scanSensorTrust').value),
      source: 'field_scan',
      latitude: scan.location ? scan.location.lat : null,
      longitude: scan.location ? scan.location.lon : null,
      location_name: scan.location ? scan.location.display_name : null
    };
  }

  async function runScan() {
    if (scan.busy) return;
    scan.busy = true;
    const btn = $('analyzeBtn');
    btn.disabled = true; btn.textContent = T.t('analysing');
    $('scanNotice').classList.add('hide');
    const t0 = performance.now();
    const tick = i => { renderStages(i); $('scanTimer').textContent = `stage ${i + 1}/${STAGES.length} · ${((performance.now() - t0) / 1000).toFixed(1)}s`; };
    const body = payload();

    try {
      for (let i = 0; i < 4; i++) { tick(i); await sleep(200); }
      const { result, mode } = await API.analyze(body, scan.file);
      tick(4); await sleep(150);
      tick(5); await sleep(150);
      tick(6);
      const quantum = await API.quantumOver(result, body);
      tick(7);
      $('scanTimer').textContent = `complete · ${((performance.now() - t0) / 1000).toFixed(1)}s`;
      API.pushHistory({ crop: body.crop, inputs: body, result, quantum: quantum.available ? quantum : null, location: scan.location || null });
      renderResult(result, quantum, mode, body);
      renderScanHistory();
      V.toast('Analysis complete');
    } catch (err) {
      renderStages(-1);
      $('scanTimer').textContent = 'stopped';
      const box = $('scanNotice');
      if (API.isNetworkError(err)) {
        /* Only a genuinely unreachable server means "offline". */
        const queued = API.enqueue(body);
        box.className = 'notice';
        if (queued < 0) {
          box.innerHTML = `<b>${esc(T.t('offline'))}.</b> ${esc(err.message)} — and this browser's storage is full or blocked, so the scan could not be queued. Please retry when the connection returns.`;
        } else {
          box.innerHTML = `<b>${esc(T.t('offline'))}.</b> ${esc(err.message || 'Backend unreachable')} — the scan is queued (${queued} waiting) and will sync when the connection returns.${scan.file ? ' The photo is not stored offline, so the queued scan will use sensor and context evidence only.' : ''}`;
        }
        V.toast('Backend unreachable — scan queued offline', true);
      } else {
        /* The server answered and refused, or the page failed to render: this is NOT an offline case
           and must not be queued (it would fail again on every sync). */
        box.className = 'notice red';
        const isRender = !err.status;
        box.innerHTML = isRender
          ? `<b>The result could not be displayed.</b> ${esc(err.message || 'Unexpected error')}. Your scan was analysed; reload the page and open it from Recent field scans.`
          : `<b>The server rejected this scan (${esc(err.status)}).</b> ${esc(err.message)}`;
        V.toast(isRender ? 'Could not display the result' : 'Scan rejected: ' + (err.message || err.status), true);
      }
      box.classList.remove('hide');
    } finally {
      scan.busy = false; btn.disabled = false; btn.textContent = T.t('runScan');
      API.refreshHealth();
    }
  }

  const sleep = ms => new Promise(r => setTimeout(r, ms));

  function renderResult(r, q, mode, body, opts = {}) {
    const host = $('scanResult');
    const risks = r.risks || {}, bands = r.risk_bands || {};
    const vision = r.vision || {};
    const imgSrc = (scan.file && !opts.noImage) ? $('previewImg').src : null;
    const ew = q.available ? q.early_warning : null;

    host.classList.remove('hide');
    host.innerHTML = `
      <div class="row" style="justify-content:space-between;margin-bottom:1rem">
        <div><span class="mono">scan result · ${esc(mode)}</span>
          <h2 style="margin:.2rem 0 0">${esc(T.cropName(body.crop))} · ${esc(r.health_status)}</h2></div>
        <div class="row">
          <span class="tag green">LIVE INPUT</span>
          <span class="tag ${r.color}">${esc(T.t('status.' + r.color, r.health_status))}</span>
          ${ew ? `<span class="tag ${ew.color}">${esc(T.t('level.' + ew.level, ew.level))}</span>` : ''}
        </div>
      </div>

      <div class="split">
        <div class="stack">
          ${imgSrc ? `<div class="preview"><img src="${imgSrc}" alt="Analysed crop image"></div>` : ''}
          <div class="card">
            <h3>Crop condition</h3>
            ${V.metric(T.t('cropHealth'), r.health_score, r.health_score + ' / 100', V.band(100 - r.health_score))}
            ${V.metric('Disease / pest signal', risks.disease, bands.disease + ' · ' + num(risks.disease, '%', 1))}
            ${V.metric('Soil condition', body.soil_moisture, num(body.soil_moisture, '% moisture', 0), V.band(Math.abs(50 - body.soil_moisture) * 2))}
            ${V.metric(T.t('waterStatus'), risks.water, bands.water + ' · ' + num(risks.water, '%', 1))}
            ${V.metric(T.t('heatStress'), risks.heat, bands.heat + ' · ' + num(risks.heat, '%', 1))}
            ${V.metric('Weather / excess water', risks.excess_water, bands.excess_water + ' · ' + num(risks.excess_water, '%', 1))}
            ${V.metric(T.t('modelConfidence'), r.confidence, num(r.confidence, '%', 1), V.band(100 - r.confidence))}
          </div>
        </div>

        <div class="stack">
          <div class="card">
            <span class="mono">${esc(T.t('recommended'))}</span>
            <h3 style="margin:.3rem 0">${esc(r.recommendation)}</h3>
            <p class="dim" style="font-size:.9rem">${esc(T.t('nextCheck'))}: ${esc(r.next_check)}</p>
            ${r.status === 'needs_verification' ? `<div class="notice">${esc(T.t('verify'))}</div>` : ''}
            ${ew ? `<div class="notice ${ew.color === 'red' ? 'red' : ew.color === 'green' ? 'green' : ''}" style="margin-top:.6rem"><b>${esc(ew.level)}.</b> ${esc(ew.action)}</div>` : ''}
          </div>

          <div class="card evidence-card">
            <h3>🔍 Why this result?</h3>
            <div class="evidence-list">
              <div><span>Visual evidence</span><b>${mode === 'multimodal' ? (vision.real_inference ? 'Model-backed' : 'Screening only') : 'Not supplied'}</b></div>
              <div><span>Sensor evidence</span><b>${num(r.sensor_trust,'%',0)} trust</b></div>
              <div><span>Context evidence</span><b>${num(r.context_confidence,'%',0)} confidence</b></div>
              <div><span>Signals used</span><b>${(r.reason||[]).length || 0} recorded factors</b></div>
            </div>
            ${r.reason && r.reason.length ? `<ul class="dim" style="font-size:.88rem;margin:.7rem 0 0">${r.reason.slice(0,5).map(x=>`<li>${esc(x)}</li>`).join('')}</ul>` : ''}
          </div>

          <div class="card">
            <h3>Image and vision evidence</h3>
            ${mode === 'multimodal' ? `
              <div class="badge-row"><b>Image quality</b><span class="mono">${num((r.image_quality || 0) * 100, '%', 0)}</span></div>
              <div class="badge-row"><b>Vision status</b><span class="mono">${esc(vision.status || '—')}</span></div>
              <div class="badge-row"><b>Model prediction</b><span class="mono">${esc(vision.prediction || '—')}</span></div>
              <div class="badge-row"><b>Real inference</b><span class="mono">${vision.real_inference ? 'yes' : 'screening only'}</span></div>
              ${vision.message ? `<p class="dim" style="font-size:.88rem;margin-top:.6rem">${esc(vision.message)}</p>` : ''}`
        : `<p class="dim" style="font-size:.9rem">No image supplied — this analysis used sensor and context evidence only. Add a leaf photo for a vision-backed reading.</p>`}
          </div>

          <div class="card">
            <h3>Hybrid model comparison</h3>
            ${q.available ? `
              <div class="badge-row"><b>Quantum risk probability</b><span class="mono">${num(q.quantum.risk_probability, '%', 1)}</span></div>
              ${V.meter(q.quantum.risk_probability)}
              <div class="badge-row" style="margin-top:.6rem"><b>Classical baseline</b><span class="mono">${q.classical.risk_probability === null ? 'unavailable' : num(q.classical.risk_probability, '%', 1)}</span></div>
              ${q.classical.risk_probability !== null ? V.meter(q.classical.risk_probability, 'amber') : ''}
              <div class="row" style="margin-top:.7rem">
                <span class="tag">${esc(q.circuit.qubits)} qubits · ${esc(q.circuit.layers)} layers</span>
                <span class="tag">${q.comparison.agreement === null ? 'no comparison' : q.comparison.agreement ? 'models agree' : 'models disagree'}</span>
                <span class="tag amber">Experimental</span>
              </div>
              ${!q.models_trained ? `<div class="notice" style="margin-top:.7rem">${esc(q.untrained_note)}</div>` : ''}
              ${q.state ? `<div class="mono" style="margin-top:1rem">qubit states for this field · Bloch spheres</div>
                <div class="bloch-row">${q.state.qubits.map(b => V.blochSVG(b.bloch, 'q' + b.qubit + ' · ' + ((q.features.selected || [])[b.qubit] || '').replace(/_/g, ' '), b.entanglement_entropy)).join('')}</div>
                <p class="dim" style="font-size:.85rem;margin:.4rem 0 0">Entanglement (Meyer–Wallach): <b>${num(q.state.meyer_wallach, '', 3)}</b> — 0 means the qubits are independent, 1 means maximally entangled. Computed from the simulated state vector.</p>` : ''}
              <details style="margin-top:.8rem"><summary class="mono" style="cursor:pointer">encoded features</summary>
                <table style="margin-top:.5rem"><thead><tr><th>Feature</th><th class="num">Value</th><th class="num">Angle</th><th>Qubit</th></tr></thead><tbody>
                ${q.features.vector.map(f => `<tr class="${f.encoded ? 'win' : ''}"><td>${esc(f.label)}</td>
                  <td class="num">${num(f.raw, f.unit, 1)}</td><td class="num">${f.encoded ? f.angle_rad.toFixed(3) : '—'}</td>
                  <td>${f.encoded ? 'q' + f.qubit : '<span class="dim">context</span>'}</td></tr>`).join('')}
                </tbody></table></details>`
        : `<div class="notice red"><b>Quantum layer unavailable.</b> Classical agricultural analysis continues normally.</div>`}
          </div>
        </div>
      </div>

      <div class="split" style="margin-top:1.2rem">
        <div class="card">
          <h3>Why this result</h3>
          <ul class="dim" style="font-size:.92rem">${(r.reason || []).map(x => `<li>${esc(x)}</li>`).join('')}</ul>
          <div class="row" style="margin-top:.6rem">
            <button class="btn small ghost" data-go="quantum">Inspect the circuit</button>
            <button class="btn small ghost" data-go="warnings">Open warnings</button>
          </div>
        </div>
        <div class="card">
          <h3>Guardrails applied</h3>
          <ul class="dim" style="font-size:.92rem">${(r.guardrails || []).map(x => `<li>${esc(x)}</li>`).join('')}</ul>
          <div class="mono">observation #${esc(r.observation_id || '—')} · irrigation ${esc((r.irrigation || {}).priority || '—')}</div>
        </div>
      </div>`;
    host.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  /* ---------------- demo mode ---------------- */
  const DEMO_STEPS = ['Welcome', 'Select a field', 'Field conditions', 'Crop evidence', 'Field analysis',
    'Feature extraction', 'Classical model', 'Quantum model', 'Model comparison', 'Early warning'];
  let demo = { step: 0, fields: [], selected: null, detail: null };

  async function openDemo() {
    demo = { step: 0, fields: [], selected: null, detail: null };
    let el = $('demoOverlay');
    if (!el) {
      el = document.createElement('div');
      el.id = 'demoOverlay'; el.className = 'demo-overlay';
      el.innerHTML = '<div class="demo-panel" id="demoPanel" role="dialog" aria-modal="true" aria-label="Guided demonstration" tabindex="-1"></div>';
      document.body.appendChild(el);
      el.addEventListener('click', e => { if (e.target === el) closeDemo(); });
      document.addEventListener('keydown', e => { if (e.key === 'Escape' && !el.classList.contains('hide')) closeDemo(); });
    }
    el.classList.remove('hide');
    paintDemo('<span class="mono">loading demonstration fields…</span>');
    const d = await API.demoFields();
    demo.fields = d.items || [];
    renderDemo();
  }
  const closeDemo = () => { const el = $('demoOverlay'); if (el) el.classList.add('hide'); };
  const paintDemo = html => { $('demoPanel').innerHTML = html; };

  function demoFrame(inner, opts = {}) {
    return `<div class="row" style="justify-content:space-between">
        <div><span class="tag sim">DEMO MODE \u00b7 SYNTHETIC / SIMULATED INPUTS</span><h3 style="margin:.4rem 0 0">${esc(DEMO_STEPS[demo.step])}</h3></div>
        <button class="btn small ghost" id="demoClose">Close</button>
      </div>
      <div class="demo-steps">${DEMO_STEPS.map((_, i) => `<i class="${i <= demo.step ? 'on' : ''}"></i>`).join('')}</div>
      <div style="margin:1rem 0">${inner}</div>
      <div class="row" style="justify-content:space-between">
        <button class="btn small ghost" id="demoBack" ${demo.step === 0 ? 'disabled' : ''}>Back</button>
        <button class="btn small" id="demoNext">${opts.nextLabel || (demo.step === DEMO_STEPS.length - 1 ? 'Finish' : 'Continue')}</button>
      </div>`;
  }

  function renderDemo() {
    const f = demo.selected, det = demo.detail;
    const a = det ? det.analysis : (f ? f.analysis : null);
    const q = det ? (det.quantum || { available: false }) : null;
    let inner = '';

    switch (demo.step) {
      case 0:
        inner = `<p>This walkthrough runs the complete AstraNex pipeline over demonstration fields — no hardware needed. Every value shown is computed by the real engine over a simulated field scenario.</p>
          <div class="grid g2">
            <div class="card"><h3 style="font-size:1rem">What you will see</h3><p class="dim" style="font-size:.9rem;margin:0">Sensors and weather, crop evidence, feature extraction, both models, and the early warning that results.</p></div>
            <div class="card"><h3 style="font-size:1rem">What is simulated</h3><p class="dim" style="font-size:.9rem;margin:0">The field scenarios and the sensor values. The engine, the features, the circuit and the models are real code paths.</p></div>
          </div>`;
        break;
      case 1:
        inner = `<div class="grid g2">${demo.fields.map((x, i) => `
          <button class="card lift" data-demo-field="${i}" style="text-align:left;cursor:pointer;border-color:${demo.selected === x ? 'var(--phosphor)' : ''}">
            <span class="mono">${esc(x.field.code)}</span>
            <h3 style="font-size:1.05rem;margin:.2rem 0">${esc(x.field.name)}</h3>
            <span class="dim" style="font-size:.86rem">${esc(x.field.district)}, ${esc(x.field.state)} · ${esc(T.cropName(x.field.crop))}</span>
          </button>`).join('')}</div>`;
        break;
      case 2:
        inner = f ? `<div class="grid g3">
            ${[['Soil moisture', f.inputs.soil_moisture + '%'], ['Temperature', f.inputs.temperature + '°C'],
              ['Humidity', f.inputs.humidity + '%'], ['Weather', f.inputs.weather],
              ['Rainfall (48h)', f.inputs.recent_rainfall_mm + ' mm'], ['Sensor reliability', (f.inputs.sensor_reliability * 100) + '%']]
            .map(([k, v]) => `<div class="card"><div class="kpi"><b style="font-size:1.3rem">${esc(v)}</b><span>${esc(k)}</span></div></div>`).join('')}
          </div>` : '';
        break;
      case 3:
        inner = f ? `<div class="card"><h3 style="font-size:1rem">Crop evidence</h3>
            <div class="badge-row"><b>Reported symptom</b><span class="mono">${esc(f.inputs.condition)}</span></div>
            <div class="badge-row"><b>Growth stage</b><span class="mono">${esc(f.inputs.growth_stage)}</span></div>
            <div class="badge-row"><b>Image quality</b><span class="mono">${num(f.inputs.image_quality * 100, '%', 0)}</span></div>
            <p class="dim" style="font-size:.88rem;margin-top:.6rem">In a live scan this is a leaf photo screened for quality and passed to the ONNX vision model. In demo mode the symptom class stands in for that evidence.</p></div>` : '';
        break;
      case 4:
        inner = a ? `<div class="card">${V.metric('Crop health', a.health_score, a.health_score + ' / 100', V.band(100 - a.health_score))}
            ${V.metric('Disease risk', a.risks.disease, a.risk_bands.disease)}
            ${V.metric('Water risk', a.risks.water, a.risk_bands.water)}
            ${V.metric('Heat risk', a.risks.heat, a.risk_bands.heat)}</div>` : '';
        break;
      case 5:
        inner = q && q.available ? `<table><thead><tr><th>Feature</th><th class="num">Value</th><th class="num">Normalised</th><th>Encoded</th></tr></thead><tbody>
            ${q.features.vector.map(x => `<tr class="${x.encoded ? 'win' : ''}"><td>${esc(x.label)}</td><td class="num">${num(x.raw, x.unit, 1)}</td>
            <td class="num">${x.normalised.toFixed(3)}</td><td>${x.encoded ? 'q' + x.qubit : '<span class="dim">context</span>'}</td></tr>`).join('')}
          </tbody></table>` : quantumUnavailable();
        break;
      case 6:
        inner = q && q.available ? `<div class="card"><h3 style="font-size:1rem">Classical baseline</h3>
            <div class="badge-row"><b>Risk probability</b><span class="mono">${q.classical.risk_probability === null ? 'unavailable' : num(q.classical.risk_probability, '%', 1)}</span></div>
            <div class="badge-row"><b>Inference time</b><span class="mono">${num(q.classical.inference_ms, ' ms', 3)}</span></div>
            <p class="dim" style="font-size:.88rem;margin-top:.5rem">Logistic regression over the same four selected features.</p></div>` : quantumUnavailable();
        break;
      case 7:
        inner = q && q.available ? `<div class="card"><h3 style="font-size:1rem">Quantum model</h3>
            <div class="badge-row"><b>Risk probability</b><span class="mono">${num(q.quantum.risk_probability, '%', 1)}</span></div>
            <div class="badge-row"><b>⟨Z⟩ per qubit</b><span class="mono">${q.quantum.expectations.map(e => e.toFixed(3)).join('  ')}</span></div>
            <div class="badge-row"><b>Backend</b><span class="mono" style="max-width:60%;text-align:right">${esc(q.quantum.backend)}</span></div>
            <div class="badge-row"><b>Inference time</b><span class="mono">${num(q.quantum.inference_ms, ' ms', 3)}</span></div></div>` : quantumUnavailable();
        break;
      case 8:
        inner = q && q.available ? `<div class="grid g2">
            <div class="card"><div class="kpi"><b>${num(q.classical.risk_probability, '%', 1)}</b><span>Classical risk</span></div></div>
            <div class="card"><div class="kpi"><b>${num(q.quantum.risk_probability, '%', 1)}</b><span>Quantum risk</span></div></div>
          </div>
          <div class="notice" style="margin-top:.8rem">${q.comparison.agreement ? 'Both models place this field on the same side of the warning threshold.' : 'The models disagree on this field — an early-warning system would surface it for verification rather than act on it.'} No quantum advantage is claimed.</div>` : quantumUnavailable();
        break;
      case 9:
        inner = a ? `<div class="warn-card ${a.color}" style="border-radius:var(--r-m)">
            <div class="warn-top"><h3 style="margin:0">${esc(f.field.name)}</h3>
            <span class="tag ${q && q.available ? q.early_warning.color : a.color}">${q && q.available ? esc(q.early_warning.level) : esc(a.health_status)}</span></div>
            <p style="margin:.7rem 0 .3rem"><b>${esc(a.recommendation)}</b></p>
            <p class="dim" style="font-size:.9rem;margin:0">${esc(a.next_check)}</p>
          </div>
          <div class="row" style="margin-top:.8rem"><span class="tag sim">Simulation data</span>
          <span class="dim" style="font-size:.86rem">Run your own scan from Field scan for a live result.</span></div>` : '';
        break;
    }

    paintDemo(demoFrame(inner));
    $('demoClose').addEventListener('click', closeDemo);
    $('demoBack').addEventListener('click', () => { demo.step = Math.max(0, demo.step - 1); renderDemo(); });
    $('demoNext').addEventListener('click', nextDemo);
    $('demoPanel').querySelectorAll('[data-demo-field]').forEach(b =>
      b.addEventListener('click', () => { demo.selected = demo.fields[Number(b.dataset.demoField)]; demo.detail = null; nextDemo(); }));
  }

  const quantumUnavailable = () => `<div class="notice red"><b>Quantum layer unavailable.</b> Classical agricultural analysis continues normally — the remaining steps still show the classical result.</div>`;

  async function nextDemo() {
    if (demo.step === DEMO_STEPS.length - 1) { closeDemo(); location.hash = '#/scan'; return; }
    if (demo.step === 1 && !demo.selected) { demo.selected = demo.fields[0]; }
    demo.step += 1;
    if (demo.step === 5 && demo.selected && !demo.detail) {
      paintDemo(demoFrame('<span class="mono">running hybrid analysis…</span>'));
      demo.detail = await API.demoField(demo.selected.field.code);
    }
    renderDemo();
  }

  $('demoBtn').addEventListener('click', openDemo);
  const demo2 = $('demoBtn2'); if (demo2) demo2.addEventListener('click', openDemo);

  /* ---------------- offline shell ---------------- */
  if ('serviceWorker' in navigator && location.protocol.startsWith('http')) {
    navigator.serviceWorker.register('/sw.js').catch(() => { /* offline cache is optional */ });
  }

  /* ---------------- boot ---------------- */
  T.set(T.lang());
  route();
  API.refreshHealth();
  setInterval(() => API.refreshHealth(), 45000);
})();
