/* Page renderers. Each render function is idempotent and safe to call again. */
window.AX_PAGES = (function () {
  const V = window.AX_VIZ, API = window.AX_API, D = window.AX_DATA, T = window.AX_I18N;
  const esc = V.esc, num = V.num;
  const $ = id => document.getElementById(id);

  const loading = msg => `<div class="card"><span class="mono">${esc(msg || 'loading…')}</span></div>`;

  /* ======================= HOME fragments ======================= */
  /* engine issue codes -> readable labels (never show raw snake_case to a farmer) */
  const ISSUE_LABELS = {
    healthy: 'Healthy', unclear: 'Unclear image', water_stress: 'Water stress', pest: 'Pest signal',
    diseaseA: 'Leaf disease pattern A', diseaseA_mild: 'Leaf disease pattern A (mild)', diseaseA_severe: 'Leaf disease pattern A (severe)',
    diseaseB: 'Leaf disease pattern B', diseaseB_mild: 'Leaf disease pattern B (mild)', diseaseB_severe: 'Leaf disease pattern B (severe)',
    heat_stress: 'Heat stress', excess_water: 'Excess water', nutrient: 'Nutrient deficiency signal', unknown: 'Needs verification'
  };
  const issueLabel = k => ISSUE_LABELS[k] || String(k || 'Field warning').replace(/_/g, ' ');

  function home() {
    const flow = $('homeFlow');
    if (flow && !flow.dataset.done) {
      flow.innerHTML = D.FLOW.map(([t, b], i) => `<div class="card lift">
        <span class="mono">stage ${i + 1}</span><h3 style="margin-top:.4rem">${esc(t)}</h3>
        <p class="dim" style="font-size:.9rem;margin:0">${esc(b)}</p></div>`).join('');
      flow.dataset.done = '1';
    }
    const badges = $('statusBadges');
    if (badges && !badges.dataset.done) {
      badges.innerHTML = D.STATUS_BADGES.map(([name, state, tone]) => `<div class="badge-row">
        <b>${esc(name)}</b><span class="${tone === 'ok' ? 'badge-ok' : tone === 'exp' ? 'badge-exp' : 'badge-future'}">${tone === 'ok' ? '✓ ' : ''}${esc(state)}</span></div>`).join('');
      badges.dataset.done = '1';
    }
    const road = $('homeRoadmap');
    if (road && !road.dataset.done) {
      road.dataset.done = '1';
      road.innerHTML = D.ROADMAP.map(([phase, what, state, tone]) => `<div class="card lift">
        <span class="mono">${esc(phase)}</span>
        <p style="margin:.4rem 0 .6rem;font-size:.98rem">${esc(what)}</p>
        <span class="${tone === 'ok' ? 'badge-ok' : tone === 'exp' ? 'badge-exp' : 'badge-future'}">${esc(state)}</span></div>`).join('');
    }
    const map = $('homeMapWrap');
    if (map && !map.dataset.done) {
      map.dataset.done = '1';
      API.demoFields().then(d => {
        const nodes = (d.items || []).map(x => ({
          code: x.field.code, name: x.field.name + ' · ' + x.field.district,
          short: x.field.state, lat: x.field.lat, lon: x.field.lon, color: x.analysis.color
        }));
        map.innerHTML = V.indiaMap(nodes);
      });
    }
  }

  /* ======================= FARMER DASHBOARD ======================= */
  async function farmer() {
    const body=$('farmerBody'); body.innerHTML=loading('loading your field…');
    const [hist,demo,alerts,profileWrap]=await Promise.all([API.history(),API.demoFields(),API.alerts(),API.safe(()=>API.get('/api/farmer-profile'),{})]);
    const profile=profileWrap && profileWrap.profile ? profileWrap.profile : (profileWrap || {});
    const local=API.readHistory();
    const latest=(hist.items||[])[0] || local[0];
    const source=latest ? (latest.result||latest) : ((demo.items||[])[0] ? demo.items[0].analysis : null);
    const crop=latest?.crop || (demo.items||[])[0]?.field?.crop || 'tomato';
    if(!source){ body.innerHTML='<div class="card"><h3>Welcome to AstraNex 🌾</h3><p class="dim">Set your field location and run a scan to start building your farmer dashboard.</p><button class="btn" data-go="scan">Scan my field</button></div>'; return; }
    const r=source, risks=r.risks||{}, recent=[...local].reverse().slice(-7);
    const score=v=>typeof v==='number'?v:0;
    body.innerHTML=`
      <div class="farmer-hero card">
        <div><span class="mono">${esc(profile?.field_name || 'My field')}</span><h3 style="font-size:1.8rem;margin:.25rem 0">${esc(T.cropName(crop))} · ${esc(r.health_status||'Current condition')}</h3><p class="dim" style="margin:0">${esc(profile?.district||profile?.state||'Field location not set')}</p></div>
        <div class="farmer-health"><span>FIELD HEALTH</span><b>${num(r.health_score,'',0)}</b><small>/ 100 · ${esc(r.health_status||'')}</small></div>
      </div>
      <div class="grid g4">
        ${(() => {
          const soil = latest?.soil_moisture ?? latest?.inputs?.soil_moisture;
          const tone = { green: ['Adequate', 'Adequate'], amber: ['Watch', 'Watch'], red: ['Attention', 'Attention'] };
          /* direction matters: for HEALTH high is good; for RISK high is bad; soil is best near the middle */
          return [['🌱', 'Crop health', r.health_score, '/100', V.bandGood(r.health_score), { green: 'Good', amber: 'Fair', red: 'Attention' }],
                  ['🪨', 'Soil moisture', soil, '%', V.band(Math.abs(50 - Number(soil)) * 2), tone],
                  ['💧', 'Water risk', risks.water, '%', V.band(risks.water), tone],
                  ['🌤️', 'Heat risk', risks.heat, '%', V.band(risks.heat), tone]]
            .map(([icon, k, v, u, band, labels]) => `<div class="farmer-kpi card"><span class="farmer-icon">${icon}</span><span>${esc(k)}</span><b>${num(v, u, 0)}</b><small class="${Number.isFinite(Number(v)) ? band : ''}">${Number.isFinite(Number(v)) ? labels[band][0] : 'No data yet'}</small></div>`).join('');
        })()}
      </div>
      <div class="split">
        <div class="stack">
          <div class="card"><div class="row" style="justify-content:space-between"><div><span class="mono">NEXT ACTION</span><h3 style="margin:.3rem 0">${esc(r.recommendation||r.next_check||'Continue routine scouting')}</h3></div><span class="tag ${r.color||'amber'}">${esc(r.health_status||'MONITOR')}</span></div><p class="dim" style="margin:.5rem 0 0">Next check: ${esc(r.next_check||'Review after the next field observation.')}</p></div>
          <div class="card"><h3>⚠️ Early warnings</h3>${(alerts.items||[]).slice(0,3).map(a=>`<div class="badge-row"><b>${esc(issueLabel(a.kind))}</b><span class="tag ${a.severity==='HIGH'?'red':'amber'}">${esc(a.severity||'MONITOR')}</span></div>`).join('')||'<p class="dim">No stored warnings. Keep monitoring.</p>'}<button class="btn small ghost" data-go="warnings" style="margin-top:.7rem">Open warnings</button></div>
        </div>
        <div class="card"><h3>📈 Field health trend</h3><p class="dim" style="font-size:.86rem">Only scans stored on this device are plotted.</p>${V.sparkline(recent.map(h=>score(h.result?.health_score)), 'green')}<div class="row" style="margin-top:.6rem"><span class="tag">${recent.length} local scans</span><span class="tag ${navigator.onLine?'green':'amber'}">${navigator.onLine?'Online':'Offline'}</span></div></div>
      </div>
      <div class="card location-profile-card"><div class="row" style="justify-content:space-between"><div><span class="mono">FIELD PROFILE</span><h3 style="margin:.3rem 0">📍 ${esc(profile?.field_name||'My Field')}</h3><p class="dim" style="margin:0">${esc([profile?.district,profile?.state].filter(Boolean).join(', ')||'Location can be added from Field scan')}</p></div><button class="btn small" data-go="scan">Update / scan</button></div></div>
      <div class="row"><button class="btn" data-go="scan">📷 Scan field</button><button class="btn ghost" data-go="intelligence">See detailed intelligence</button><button class="btn ghost" data-go="library">Disease library</button></div>`;
  }

  /* ======================= INTELLIGENCE ======================= */
  async function intelligence() {
    const body = $('intelBody');
    body.innerHTML = loading('reading the latest field state…');
    const [hist, demo, alerts, sensors] = await Promise.all([
      API.history(), API.demoFields(), API.alerts(), API.sensorsLatest()]);
    const latest = (hist.items || [])[0];
    const local = API.readHistory()[0];
    const source = latest ? { result: latest.result, label: 'Latest stored scan', when: latest.created_at * 1000, crop: latest.crop }
      : local ? { result: local.result, label: 'Latest scan on this device', when: local.at, crop: local.crop }
        : (demo.items || [])[0] ? { result: demo.items[0].analysis, label: 'Demonstration field · ' + demo.items[0].field.name, when: null, crop: demo.items[0].field.crop, sim: true }
          : null;

    if (!source) { body.innerHTML = `<div class="card"><h3>No scans yet</h3><p class="dim">Run a field scan to populate this view.</p><button class="btn" data-go="scan">Go to field scan</button></div>`; return; }
    const r = source.result, risks = r.risks || {};
    const q = await API.quantumOver(r, { crop: source.crop });

    body.innerHTML = `
      <div class="row" style="justify-content:space-between">
        <div><span class="mono">${esc(source.label)}</span>${source.sim ? ' <span class="tag sim">Simulation data</span>' : ''}
        <h3 style="margin:.3rem 0 0">${esc(T.cropName(source.crop || 'tomato'))} · ${esc(r.health_status || '')}</h3></div>
        <span class="tag ${r.color}">${esc(T.t('status.' + r.color, r.health_status))}</span>
      </div>
      <div class="split">
        <div class="card">
          <h3>Field intelligence</h3>
          ${V.metric(T.t('cropHealth'), r.health_score, num(r.health_score) + ' / 100', V.band(100 - r.health_score))}
          ${V.metric(T.t('diseaseRisk'), risks.disease, (r.risk_bands || {}).disease + ' · ' + num(risks.disease, '%', 1))}
          ${V.metric(T.t('waterStatus'), risks.water, (r.risk_bands || {}).water + ' · ' + num(risks.water, '%', 1))}
          ${V.metric(T.t('heatStress'), risks.heat, (r.risk_bands || {}).heat + ' · ' + num(risks.heat, '%', 1))}
          ${V.metric('Excess water', risks.excess_water, (r.risk_bands || {}).excess_water + ' · ' + num(risks.excess_water, '%', 1))}
          ${V.metric(T.t('sensorConfidence'), r.sensor_trust, num(r.sensor_trust, '%', 1), V.band(100 - (r.sensor_trust || 0)))}
        </div>
        <div class="stack">
          <div class="card">
            <span class="mono">${esc(T.t('recommended'))}</span>
            <h3 style="margin:.4rem 0">${esc(r.recommendation || r.next_check || '')}</h3>
            <p class="dim" style="font-size:.9rem;margin:0">${esc(T.t('nextCheck'))}: ${esc(r.next_check || '')}</p>
            ${r.status === 'needs_verification' ? `<div class="notice" style="margin-top:.8rem">${esc(T.t('verify'))}</div>` : ''}
          </div>
          <div class="card">
            <h3>Model provenance</h3>
            <div class="badge-row"><b>Overall confidence</b><span class="mono">${num(r.confidence, '%', 1)}</span></div>
            <div class="badge-row"><b>Vision confidence</b><span class="mono">${num(r.vision_confidence, '%', 1)}</span></div>
            <div class="badge-row"><b>Context confidence</b><span class="mono">${num(r.context_confidence, '%', 1)}</span></div>
            <div class="badge-row"><b>Quantum layer</b><span class="mono">${q.available ? num(q.quantum.risk_probability, '% risk', 1) : 'unavailable'}</span></div>
            <div class="badge-row"><b>Classical baseline</b><span class="mono">${q.available && q.classical.risk_probability !== null ? num(q.classical.risk_probability, '% risk', 1) : 'unavailable'}</span></div>
          </div>
        </div>
      </div>
      <div class="split">
        <div class="card">
          <h3>Field sensors and weather context</h3>
          <p class="dim" style="font-size:.88rem">ESP32 soil-moisture, temperature and humidity readings, or the sensor simulator when no device has reported. These values enter the multimodal feature vector directly.</p>
          <div class="grid g3" style="margin-top:.8rem">
            ${[['Soil moisture', sensorVal(sensors, 'soil_moisture', local, source), '%'],
               ['Temperature', sensorVal(sensors, 'temperature', local, source), '\u00b0C'],
               ['Humidity', sensorVal(sensors, 'humidity', local, source), '%']]
              .map(([k, val, unit]) => `<div class="card" style="padding:.8rem"><div class="kpi">
                <b style="font-size:1.5rem">${val === null ? '\u2014' : num(val, unit, 1)}</b><span>${esc(k)}</span></div>
                ${val === null ? '' : V.meter(k === 'Temperature' ? (val / 50) * 100 : val, 'green')}</div>`).join('')}
          </div>
          <div class="row" style="margin-top:.7rem">
            <span class="tag ${sensors && (sensors.items || []).length ? 'green' : 'sim'}">${sensors && (sensors.items || []).length ? 'Device reading' : 'Simulation data'}</span>
            <span class="tag">sensor trust ${num(r.sensor_trust, '%', 0)}</span>
            <span class="tag">${esc((r.evidence || {}).weather || 'weather context applied')}</span>
          </div>
          <div class="mono" style="margin-top:.6rem">sensors \u2192 fusion \u2192 risk engine \u2192 feature vector \u2192 classical + quantum models</div>
        </div>
        <div class="card">
          <h3>Why this reading</h3>
          <ul class="dim" style="font-size:.92rem">${(r.reason || []).map(x => `<li>${esc(x)}</li>`).join('') || '<li>No specific factors recorded.</li>'}</ul>
        </div>
        <div class="card">
          <h3>Open warnings</h3>
          ${(alerts.items || []).slice(0, 4).map(a => `<div class="badge-row"><b>${esc(issueLabel(a.kind))}</b><span class="tag ${a.severity === 'HIGH' ? 'red' : 'amber'}">${esc(a.severity)}</span></div>`).join('')
        || '<p class="dim" style="font-size:.9rem">No stored warnings yet.</p>'}
          <button class="btn small ghost" data-go="warnings" style="margin-top:.7rem">Open early-warning centre</button>
        </div>
      </div>`;
  }

  function sensorVal(sensors, key, local, source) {
    const latest = sensors && Array.isArray(sensors.items) ? sensors.items[0] : null;
    if (latest && typeof latest[key] === 'number') return latest[key];
    const ev = ((source && source.result) || {}).evidence || {};
    if (typeof ev[key] === 'number') return ev[key];
    if (local && local.inputs && typeof local.inputs[key] === 'number') return local.inputs[key];
    return null;
  }

  /* ======================= QUANTUM LAB ======================= */
  async function quantum() {
    const body = $('quantumBody');
    body.innerHTML = loading('loading circuit and benchmark…');
    const lastScan = (API.readHistory() || [])[0];
    const lastAngles = lastScan && lastScan.quantum && lastScan.quantum.features && lastScan.quantum.features.angles_rad;
    const [status, circuit, bench] = await Promise.all([API.quantumStatus(), API.circuit(lastAngles), API.benchmark()]);

    if (!status.available) {
      body.innerHTML = `<div class="notice red"><b>Quantum layer unavailable.</b> Classical agricultural analysis continues normally. Install Qiskit or check the backend log, then reload this page.</div>`;
      return;
    }
    const rt = status.runtime || {};
    const qmap = circuit.qubit_map || [];

    body.innerHTML = `
      <div class="grid g4">
        ${[['Qubits', circuit.qubits || 4], ['Layers · depth', `${circuit.layers || 2} · ${circuit.circuit_depth ?? '—'}`], ['Encoding', circuit.encoding_label || circuit.encoding || '—'],
      ['Backend', rt.execution_backend || 'Unavailable']]
        .map(([k, v]) => `<div class="card"><span class="mono">${esc(k)}</span><div class="kpi"><b style="font-size:1.5rem">${esc(v)}</b></div></div>`).join('')}
      </div>

      <div class="notice ${rt.qiskit_execution ? 'green' : ''}"><b>${esc(rt.execution_label || '')}.</b> ${esc(rt.note || '')}</div>
      ${(status.training && status.training.training) ? `<div class="notice"><b>Training in progress…</b> The quantum and classical models are being trained on the labelled demonstration dataset${status.training.progress ? ` (iteration ${esc(status.training.progress.iteration)}/${esc(status.training.progress.iterations)})` : ''}. This page refreshes automatically.</div>` : ''}
      ${(!status.models_trained && !(status.training && status.training.training)) ? `<div class="notice amber"><b>QML STATUS · Model: Not trained · Inference: Disabled</b><br>${esc(status.inference_message || 'Training required before QML inference')}${(status.training && status.training.last_error) ? `<br><span class="mono">last error: ${esc(status.training.last_error)}</span>` : ''}</div>` : ''}

      <div class="split">
        <div class="card">
          <h3>Quantum layer status</h3>
          <div class="badge-row"><b>Qiskit</b><span class="${rt.qiskit_installed ? 'badge-ok' : 'badge-future'}">${rt.qiskit_installed ? '\u25cf Available \u00b7 ' + esc(rt.qiskit_version) : '\u25cf Not installed'}</span></div>
          <div class="badge-row"><b>Qiskit Machine Learning</b><span class="${rt.qiskit_machine_learning_installed ? 'badge-ok' : 'badge-future'}">${rt.qiskit_machine_learning_installed ? '\u25cf Available \u00b7 ' + esc(rt.qiskit_machine_learning_version) : '\u25cf Not installed'}</span></div>
          <div class="badge-row"><b>QML model</b><span class="${status.models_trained ? 'badge-ok' : 'badge-future'}">${status.models_trained ? '\u25cf Trained' : '\u25cf Not trained · inference disabled'}</span></div>
          <div class="badge-row"><b>Qubits</b><span class="mono">${esc(circuit.qubits || 4)}</span></div>
          <div class="badge-row"><b>Feature encoding</b><span class="mono" style="max-width:60%;text-align:right">${esc(circuit.encoding || '')}</span></div>
          <div class="badge-row"><b>Ansatz</b><span class="mono" style="max-width:60%;text-align:right">${esc(circuit.ansatz || '')}</span></div>
          <div class="badge-row"><b>Backend</b><span class="mono" style="max-width:60%;text-align:right">${esc(rt.execution_backend || '')}</span></div>
          <div class="badge-row"><b>Execution</b><span class="mono">Simulation${rt.hardware_execution ? '' : ' \u00b7 no hardware'}</span></div>
          <div class="badge-row"><b>Circuit depth · gates</b><span class="mono">${esc(circuit.circuit_depth ?? '—')} · ${esc(circuit.gate_count ?? '—')}</span></div>
          ${rt.qiskit_runtime_errors ? `<div class="badge-row"><b>Qiskit runtime errors</b><span class="badge-future">${esc(rt.qiskit_runtime_errors)} · fell back to built-in simulator</span></div>` : ''}
          ${rt.import_error ? `<div class="badge-row"><b>Qiskit note</b><span class="mono" style="max-width:60%;text-align:right">${esc(rt.import_error)}</span></div>` : ''}
          <div class="badge-row"><b>Status</b><span class="badge-exp">Experimental</span></div>
        </div>
        <div class="card">
          <h3>Features from the latest scan</h3>
          <p class="dim" style="font-size:.88rem">The values actually encoded onto the qubits for the most recent analysis on this device.</p>
          <div id="qLabFeatures"><span class="mono">no scan on this device yet \u2014 run a field scan or demo mode</span></div>
        </div>
      </div>

      <div class="card">
        <div class="row" style="justify-content:space-between">
          <h3 style="margin:0">Variational circuit</h3>
          <span class="tag amber">Experimental</span>
        </div>
        <p class="dim" style="font-size:.9rem">Hover or focus any gate for its role, its qubit and its angle in radians.</p>
        <div class="circuit-shell" id="circuitShell">${V.circuitSVG(circuit)}</div>
        <div class="row" style="margin-top:.8rem">
          <span class="tag">Gates ${esc(circuit.gate_count || 0)}</span>
          <span class="tag">Trainable parameters ${esc(circuit.parameters || 0)}</span>
          <span class="tag">Read-out parameters ${esc(circuit.readout_parameters || 0)}</span>
          <span class="tag">${esc(circuit.entanglement || '')}</span>
          <span class="tag ${circuit.trained ? 'green' : 'amber'}">${circuit.trained ? 'Trained parameters loaded' : 'Untrained parameters'}</span>
        </div>
      </div>

      <div class="grid g4">
        ${qmap.map(q => `<div class="qubit-card" data-qubit="${q.qubit}">
          <b>QUBIT ${String(q.qubit + 1).padStart(2, '0')}</b>
          <div class="feat">${esc(q.label || '—')}</div>
          <div class="mono">encoded parameter ${Number.isFinite(Number(q.angle_rad)) ? Number(q.angle_rad).toFixed(3) : '—'} rad</div>
          <div class="dim" style="font-size:.82rem;margin-top:.3rem">Feature encoded</div>
        </div>`).join('')}
      </div>

      ${circuit.state ? `<div class="card qstates">
        <div class="row" style="justify-content:space-between"><h3 style="margin:0">|ψ⟩ Qubit states · Bloch spheres</h3><span class="tag violet">${lastAngles ? 'latest scan' : 'default inputs'}</span></div>
        <p class="dim" style="font-size:.9rem">Each sphere shows one qubit's real reduced state, computed from the state vector this circuit prepares. A short arrow means the qubit is <b>entangled</b> with the others (a mixed reduced state); a full-length arrow means it is independent.</p>
        <div class="bloch-row">${circuit.state.qubits.map(b => V.blochSVG(b.bloch, 'q' + b.qubit + ' · ' + (((qmap[b.qubit] || {}).feature || '').replace(/_/g, ' ')), b.entanglement_entropy)).join('')}</div>
        <div class="row" style="margin-top:.6rem">
          <span class="tag violet">Meyer–Wallach entanglement ${num(circuit.state.meyer_wallach, '', 3)}</span>
          <span class="tag">mean entropy ${num(circuit.state.mean_entropy, '', 3)} bit</span>
          <span class="tag">state norm ${num(circuit.state.state_norm, '', 4)}</span>
        </div>
      </div>` : ''}

      <div class="card qplay" id="qPlay"><span class="mono">loading the quantum playground…</span></div>

      <div class="split">
        <div class="card">
          <h3>Classical versus quantum</h3>
          <p class="dim" style="font-size:.9rem">${bench.status === 'complete'
        ? 'Computed on a held-out split of a labelled demonstration dataset. Same features, same split, both models.'
        : 'No experimental benchmark has been run in this environment yet.'}</p>
          ${benchTable(bench)}
          <div class="row" style="margin-top:1rem">
            <button class="btn small" id="runBenchBtn">Run experimental benchmark</button>
            <span class="mono" id="benchState"></span>
          </div>
          ${bench.status === 'complete' ? `<div class="notice" style="margin-top:.9rem">${esc((bench.comparison || {}).verdict || '')}</div>
            ${metricBars(bench)}
            <div class="grid g2" style="margin-top:1rem">
              ${confusion('Classical', (bench.classical.metrics || {}).confusion)}
              ${confusion('Quantum', (bench.quantum.metrics || {}).confusion)}
            </div>
            <div class="row" style="margin-top:.8rem">
              <span class="tag">Backend ${esc(bench.execution_label || '')}</span>
              <span class="tag">qiskit_installed: ${String(bench.qiskit_installed)}</span>
              <span class="tag">agreement ${num((bench.comparison || {}).prediction_agreement, '%', 2)}</span>
            </div>` : ''}
        </div>
        <div class="stack">
          <div class="card">
            <h3>Feature ranking</h3>
            <p class="dim" style="font-size:.88rem">${esc((bench.features || {}).method || 'Ranking is computed during a benchmark run.')}</p>
            <table><thead><tr><th>Feature</th><th class="num">|r|</th><th class="num">Score</th><th>Encoded</th></tr></thead><tbody>
            ${((bench.features || {}).ranking || []).map(f => `<tr><td>${esc(f.label)}</td><td class="num">${num(f.correlation, '', 3)}</td><td class="num">${num(f.score, '', 3)}</td><td>${(bench.features.selected || []).includes(f.feature) ? '<span class="tag green">qubit</span>' : '<span class="dim">—</span>'}</td></tr>`).join('')
        || '<tr><td colspan="4" class="dim">Run a benchmark to compute the ranking.</td></tr>'}
            </tbody></table>
          </div>
          <div class="card">
            <h3>Measurement distribution</h3>
            <p class="dim" style="font-size:.88rem">Basis-state probabilities for the currently displayed angles.</p>
            ${(circuit.measurement_distribution || []).slice(0, 6).map(m => `
              <div class="metric"><div class="metric-top"><span class="mono">|${esc(m.state)}⟩</span>
              <span class="metric-val">${(m.probability * 100).toFixed(2)}%</span></div>${V.meter(m.probability * 100, 'green')}</div>`).join('')}
          </div>
        </div>
      </div>

      <div class="card">
        <h3>Hybrid training loop</h3>
        <div class="grid g4" style="margin-top:.7rem">
          ${(circuit.engine === 'qiskit_machine_learning'
            ? ['Agricultural features', 'ZZFeatureMap encoding', 'RealAmplitudes ansatz', 'EstimatorQNN measurement', 'Loss', 'SPSA optimiser', 'Updated trained parameters', 'Back to the circuit']
            : ['Agricultural features', 'Angle encoding (RY)', 'RY/RZ + CX variational layers', '⟨Z⟩ measurement + linear read-out', 'Loss', 'SPSA optimiser', 'Updated trained parameters', 'Back to the circuit'])
        .map((s, i) => `<div class="card" style="padding:.7rem"><span class="mono">${String(i + 1).padStart(2, '0')}</span><div style="font-size:.92rem">${esc(s)}</div></div>`).join('')}
        </div>
        ${(bench.quantum && bench.quantum.training && bench.quantum.training.loss_history)
        ? `<div style="margin-top:1rem"><span class="mono">loss history · ${esc(bench.quantum.training.optimizer || '')}</span>${lossChart(bench.quantum.training.loss_history)}</div>` : ''}
      </div>`;

    const last = (API.readHistory() || [])[0];
    const host = $('qLabFeatures');
    if (host && last && last.quantum && last.quantum.features) {
      host.innerHTML = last.quantum.features.vector.filter(f => f.encoded).map(f => `
        <div class="metric"><div class="metric-top"><span class="metric-name">${esc(f.label)}</span>
        <span class="metric-val">${num(f.raw, f.unit, 1)} \u2192 q${f.qubit} \u00b7 ${f.angle_rad.toFixed(3)} rad</span></div>
        ${V.meter(f.normalised * 100, 'green')}</div>`).join('');
    }

    const btn = $('runBenchBtn');
    if (btn) btn.addEventListener('click', runBenchmark);
    playground(circuit, lastScan);
    /* keep the page fresh while the models train in the background (e.g. first start) */
    if (status.training && status.training.training) {
      setTimeout(() => { if ((location.hash || '').includes('quantum')) quantum(); }, 3500);
    }

    // qubit card ↔ circuit highlight
    body.querySelectorAll('.qubit-card').forEach(card => {
      card.addEventListener('mouseenter', () => highlightQubit(card.dataset.qubit, true));
      card.addEventListener('mouseleave', () => highlightQubit(card.dataset.qubit, false));
    });
  }

  /* ---- interactive playground: hand-set the encoded features and watch the real circuit respond ---- */
  async function playground(circuit, lastScan) {
    const host = $('qPlay'); if (!host) return;
    const fr = await API.featureRanges();
    if (!fr.available || !(fr.features || []).length) { host.innerHTML = '<span class="mono">playground unavailable</span>'; return; }
    /* start from the latest scan's encoded values, else the circuit's default angles */
    const enc = ((lastScan && lastScan.quantum && lastScan.quantum.features && lastScan.quantum.features.vector) || []).filter(f => f.encoded);
    const xs = fr.features.map((f, i) => {
      const hit = enc.find(e => e.qubit === i);
      if (hit && Number.isFinite(hit.normalised)) return hit.normalised;
      const a = ((circuit.qubit_map || [])[i] || {}).angle_rad;
      return Number.isFinite(a) ? Math.max(0, Math.min(1, a / Math.PI)) : 0.5;
    });
    let shots = 1024, timer = null, seq = 0;
    host.innerHTML = `
      <div class="row" style="justify-content:space-between"><h3 style="margin:0">⟨ψ| Quantum playground |ψ⟩</h3><span class="tag violet">live simulation</span></div>
      <p class="dim" style="font-size:.9rem">Move a slider to change one encoded feature. The circuit is re-run on the server and everything below — the qubit states, the measurement statistics, both risk predictions — is recomputed from the real state vector. Nothing here is stored.</p>
      <div class="split">
        <div id="playSliders"></div>
        <div id="playRisk"></div>
      </div>
      <div id="playOut"></div>`;
    $('playSliders').innerHTML = fr.features.map((f, i) => `
      <label class="pslider"><span class="row" style="justify-content:space-between"><b>q${i} · ${esc(f.label)}</b><span class="mono" id="pv${i}"></span></span>
        <input type="range" min="0" max="100" step="1" value="${Math.round(xs[i] * 100)}" data-i="${i}" aria-label="${esc(f.label)}"></label>`).join('') + `
      <label class="pslider"><span class="row" style="justify-content:space-between"><b>Measurement shots</b>
        <select id="playShots" aria-label="Number of measurement shots"><option>256</option><option selected>1024</option><option>4096</option><option>8192</option></select></span></label>`;
    const label = i => { const f = fr.features[i]; const v = f.min + xs[i] * (f.max - f.min); $('pv' + i).textContent = `${v.toFixed(f.max <= 50 ? 1 : 0)}  ·  θ=${(xs[i] * Math.PI).toFixed(2)} rad`; };
    fr.features.forEach((_, i) => label(i));

    const paint = out => {
      if (!out || !out.available) { $('playOut').innerHTML = '<div class="notice red">Simulation unavailable.</div>'; return; }
      const st = out.state, q = out.quantum, c = out.classical, ew = out.early_warning;
      $('playRisk').innerHTML = out.trained ? `
        <div class="badge-row"><b>Quantum risk</b><span class="mono">${num(q.risk_probability, '%', 1)}</span></div>${V.meter(q.risk_probability)}
        <div class="badge-row" style="margin-top:.5rem"><b>Classical baseline</b><span class="mono">${c.risk_probability == null ? '—' : num(c.risk_probability, '%', 1)}</span></div>${c.risk_probability == null ? '' : V.meter(c.risk_probability, 'amber')}
        ${ew ? `<div class="notice ${ew.color === 'red' ? 'red' : ew.color === 'green' ? 'green' : ''}" style="margin-top:.7rem"><b>${esc(ew.level)}.</b> ${esc(ew.action)}</div>` : ''}
        <div class="row" style="margin-top:.5rem"><span class="tag">circuit depth ${esc(out.circuit_depth ?? '—')}</span><span class="tag">${esc(out.runtime.execution_label)}</span></div>`
        : `<div class="notice amber">${esc(out.message || 'Model not trained yet.')}</div><div class="row" style="margin-top:.5rem"><span class="tag">circuit depth ${esc(out.circuit_depth ?? '—')}</span><span class="tag">${esc(out.runtime.execution_label)}</span></div>`;
      $('playOut').innerHTML = `
        <div class="bloch-row" style="margin-top:1rem">${st.qubits.map(b => V.blochSVG(b.bloch, 'q' + b.qubit, b.entanglement_entropy)).join('')}</div>
        <div class="row"><span class="tag violet">Meyer–Wallach entanglement ${num(st.meyer_wallach, '', 3)}</span>
          <span class="tag">${st.probabilities.filter(p => p.probability > 0.001).length} of ${st.probabilities.length} basis states populated</span></div>
        <div class="split" style="margin-top:1rem">
          <div><span class="mono">exact probabilities · top states</span>${V.stateBars(st.top_states, { label: 'Exact basis-state probabilities' })}</div>
          <div><span class="mono">${esc(st.shots.shots)} simulated shots (seed ${esc(st.shots.seed)}) · ${esc(st.shots.distinct_outcomes)} distinct outcomes</span>${V.stateBars(st.shots.counts, { key: 'count', label: 'Sampled measurement counts' })}</div>
        </div>
        ${out.noise_sweep ? `<div style="margin-top:1rem"><span class="mono">noise robustness · ${esc(out.noise_sweep.model)}</span>${V.noiseChart(out.noise_sweep.points)}
          <p class="dim" style="font-size:.82rem;margin:.3rem 0 0">${esc(out.noise_sweep.note)} The dashed line is the 50% decision threshold; a prediction that crosses it as noise grows is fragile on real NISQ hardware.</p></div>` : ''}
        <p class="dim" style="font-size:.8rem;margin-top:.8rem">${esc(st.note)}</p>`;
    };
    const run = async () => {
      const my = ++seq;
      const out = await API.simulate(xs, shots);
      if (my === seq) paint(out);        /* ignore stale responses */
    };
    host.querySelectorAll('input[type=range]').forEach(inp => inp.addEventListener('input', () => {
      xs[Number(inp.dataset.i)] = Number(inp.value) / 100; label(Number(inp.dataset.i));
      clearTimeout(timer); timer = setTimeout(run, 140);
    }));
    $('playShots').addEventListener('change', e => { shots = Number(e.target.value); run(); });
    run();
  }

  function highlightQubit(q, on) {
    document.querySelectorAll(`#circuitShell .gate[data-qubit="${q}"] rect`).forEach(r => {
      r.style.stroke = on ? '#5FE3B4' : '';
      r.style.fill = on ? 'rgba(95,227,180,.24)' : '';
    });
  }

  function lossChart(history) {
    if (!history || history.length < 2) return '';
    const w = 520, h = 110, pad = 8;
    const losses = history.map(p => p.loss);
    const lo = Math.min(...losses), hi = Math.max(...losses);
    const pts = history.map((p, i) => {
      const x = pad + (i / (history.length - 1)) * (w - pad * 2);
      const y = h - pad - ((p.loss - lo) / (hi - lo || 1)) * (h - pad * 2);
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    }).join(' ');
    return `<svg viewBox="0 0 ${w} ${h}" style="width:100%;height:auto" role="img" aria-label="Training loss history">
      <polyline points="${pts}" fill="none" stroke="#5FE3B4" stroke-width="2"/>
      <text x="${pad}" y="14" font-family="IBM Plex Mono,monospace" font-size="9" fill="#7C8F84">${hi.toFixed(3)}</text>
      <text x="${pad}" y="${h - 2}" font-family="IBM Plex Mono,monospace" font-size="9" fill="#7C8F84">${lo.toFixed(3)}</text></svg>`;
  }

  function metricBars(b) {
    const c = b.classical.metrics || {}, q = b.quantum.metrics || {};
    const rows = [['Accuracy', 'accuracy'], ['Precision', 'precision'], ['Recall', 'recall'], ['F1', 'f1']];
    return `<div style="margin-top:1rem"><span class="mono">experimental benchmark \u00b7 demonstration dataset</span>
      ${rows.map(([label, key]) => `
        <div class="metric"><div class="metric-top"><span class="metric-name">${esc(label)}</span>
        <span class="metric-val">classical ${num(c[key], '%', 1)} \u00b7 quantum ${num(q[key], '%', 1)}</span></div>
        <div class="meter"><i style="width:${Math.max(2, Math.min(100, c[key] || 0))}%"></i></div>
        <div class="meter amber" style="margin-top:3px"><i style="width:${Math.max(2, Math.min(100, q[key] || 0))}%"></i></div>
        </div>`).join('')}</div>`;
  }

  function confusion(title, c) {
    if (!c) return '';
    return `<div class="card" style="padding:.9rem"><span class="mono">${esc(title)} \u00b7 confusion matrix</span>
      <table style="margin-top:.5rem"><thead><tr><th></th><th class="num">pred 0</th><th class="num">pred 1</th></tr></thead>
      <tbody>
        <tr><td class="mono">true 0</td><td class="num">${c.tn}</td><td class="num">${c.fp}</td></tr>
        <tr><td class="mono">true 1</td><td class="num">${c.fn}</td><td class="num">${c.tp}</td></tr>
      </tbody></table></div>`;
  }

  function benchTable(b) {
    const rows = [['Accuracy', 'accuracy', '%'], ['Precision', 'precision', '%'], ['Recall', 'recall', '%'],
    ['F1 score', 'f1', '%'], ['Inference time', 'inference_ms_per_sample', ' ms/sample']];
    const c = (b.classical || {}).metrics || {}, q = (b.quantum || {}).metrics || {};
    const pending = b.status !== 'complete';
    return `<table><thead><tr><th>Metric</th><th class="num">Classical</th><th class="num">Quantum</th></tr></thead><tbody>
      ${rows.map(([label, key, unit]) => {
      const cv = c[key], qv = q[key];
      const fmt = v => (v === null || v === undefined) ? '<span class="dim">Awaiting experimental benchmark</span>'
        : num(v, unit, key === 'inference_ms_per_sample' ? 4 : 2);
      return `<tr><td>${esc(label)}</td><td class="num">${fmt(cv)}</td><td class="num">${fmt(qv)}</td></tr>`;
    }).join('')}
      </tbody></table>
      <div class="row" style="margin-top:.7rem">
        <span class="tag sim">${esc(b.evaluation_label || 'Demonstration / Experimental Evaluation')}</span>
        ${pending ? '<span class="tag amber">Awaiting experimental benchmark</span>'
        : `<span class="tag">${esc((b.dataset || {}).train || 0)} train · ${esc((b.dataset || {}).test || 0)} test</span>`}
      </div>`;
  }

  async function runBenchmark() {
    const btn = $('runBenchBtn'), state = $('benchState');
    if (!btn) return;
    btn.disabled = true; btn.textContent = 'Training…';
    const started = await API.runBenchmark({ dataset_size: 360, iterations: 120, background: true });
    if (!started.ok) { btn.disabled = false; btn.textContent = 'Run experimental benchmark'; V.toast(started.message || 'Benchmark failed to start', true); return; }
    const poll = setInterval(async () => {
      const t = await API.training();
      if (t.training) {
        const p = t.progress || {};
        state.textContent = `iteration ${p.iteration || 0}/${p.iterations || 0}${p.loss !== null && p.loss !== undefined ? ' · loss ' + p.loss : ''}`;
      } else {
        clearInterval(poll);
        state.textContent = t.last_error ? 'failed' : 'complete';
        btn.disabled = false; btn.textContent = 'Run experimental benchmark';
        V.toast(t.last_error ? 'Benchmark failed' : 'Benchmark complete — metrics updated', !!t.last_error);
        quantum();
      }
    }, 1200);
  }

  /* ======================= EARLY WARNINGS ======================= */
  async function warnings() {
    const body = $('warningsBody');
    body.innerHTML = loading('collecting warnings…');
    const [alerts, demo] = await Promise.all([API.alerts(), API.demoFields()]);

    const stored = (alerts.items || []).map(a => ({
      title: 'Field ' + (a.field_id || '—'), kind: a.kind, severity: a.severity,
      color: a.severity === 'HIGH' ? 'red' : 'amber', reason: a.reason, next: a.next_step,
      when: a.created_at ? new Date(a.created_at * 1000).toLocaleString() : '', sim: false
    }));
    const demoCards = (demo.items || []).filter(x => x.analysis.color !== 'green').map(x => ({
      title: x.field.name, kind: x.analysis.issue, severity: x.analysis.color === 'red' ? 'HIGH' : 'MODERATE',
      color: x.analysis.color, reason: (x.analysis.reason || []).slice(0, 2).join(' · '),
      next: x.analysis.next_check, confidence: x.analysis.confidence,
      risks: x.analysis.risks, when: x.field.district + ', ' + x.field.state, sim: true
    }));
    const all = stored.concat(demoCards);

    body.innerHTML = `
      <div class="grid g4">
        ${[['Early warnings', all.filter(a => a.color === 'red').length], ['Monitor', all.filter(a => a.color === 'amber').length],
      ['Stored alerts', stored.length], ['Demonstration fields', (demo.items || []).length]]
        .map(([k, v]) => `<div class="card"><div class="kpi"><b>${v}</b><span>${esc(k)}</span></div></div>`).join('')}
      </div>
      <div class="stack">
        ${all.length ? all.map(a => `<div class="warn-card ${a.color}">
          <div class="warn-top">
            <div>
              <h3 style="margin:0 0 .2rem">${esc(a.title)}</h3>
              <span class="mono">${esc(a.when || '')}</span>
            </div>
            <div class="row" style="gap:.4rem">
              ${a.sim ? '<span class="tag sim">Simulation data</span>' : ''}
              <span class="tag ${a.color}">${a.color === 'red' ? 'EARLY WARNING' : 'MONITOR'}</span>
            </div>
          </div>
          <p style="margin:.6rem 0 .3rem"><b>${esc(issueLabel(a.kind))}</b>${a.confidence !== undefined ? ` · confidence ${num(a.confidence, '%', 1)}` : ''}</p>
          <p class="dim" style="font-size:.9rem;margin:0 0 .4rem">${esc(a.reason || '')}</p>
          ${a.risks ? `<div class="row">${Object.entries(a.risks).map(([k, v]) => `<span class="tag ${V.band(v)}">${esc(k.replace(/_/g, ' '))} ${num(v, '%', 0)}</span>`).join('')}</div>` : ''}
          <p style="margin:.6rem 0 0;font-size:.92rem"><span class="mono">next check</span> ${esc(a.next || '')}</p>
        </div>`).join('')
        : '<div class="card"><h3>No warnings</h3><p class="dim">Nothing has crossed a warning threshold. Run a scan or open Demo mode.</p></div>'}
      </div>
      <div class="notice">Warnings are decision support. Confirm symptoms in the field and follow local agricultural guidance before any treatment.</div>`;
  }

  /* ======================= FIELD NETWORK ======================= */
  async function network() {
    const body = $('networkBody');
    body.innerHTML = loading('loading demonstration field network…');
    const demo = await API.demoFields();
    const items = demo.items || [];
    const nodes = items.map(x => ({
      code: x.field.code, name: x.field.name, short: x.field.state,
      lat: x.field.lat, lon: x.field.lon, color: x.analysis.color
    }));

    body.innerHTML = `
      <div class="map-wrap">${V.indiaMap(nodes)}</div>
      <div class="stack" id="netList">
        <div class="row"><span class="tag sim">Simulation data</span><span class="dim" style="font-size:.86rem">${esc(demo.note || '')}</span></div>
        ${items.map(x => `<div class="card lift" data-code="${esc(x.field.code)}" tabindex="0">
          <div class="row" style="justify-content:space-between">
            <div><span class="mono">${esc(x.field.code)}</span><h3 style="margin:.2rem 0 0;font-size:1.1rem">${esc(x.field.name)}</h3>
            <span class="dim" style="font-size:.86rem">${esc(x.field.district)}, ${esc(x.field.state)} · ${esc(T.cropName(x.field.crop))}</span></div>
            <span class="tag ${x.analysis.color}">${esc(x.analysis.health_status)}</span>
          </div>
          <div class="row" style="margin-top:.6rem">
            ${Object.entries(x.analysis.risks).map(([k, v]) => `<span class="tag ${V.band(v)}">${esc(k.replace(/_/g, ' '))} ${num(v, '%', 0)}</span>`).join('')}
          </div>
          <div id="net-${esc(x.field.code)}" class="hide" style="margin-top:.8rem"></div>
        </div>`).join('')}
      </div>`;

    const openDetail = async code => {
      const host = document.getElementById('net-' + code);
      if (!host) return;
      if (!host.classList.contains('hide')) { host.classList.add('hide'); return; }
      host.classList.remove('hide');
      host.innerHTML = '<span class="mono">running hybrid analysis…</span>';
      const d = await API.demoField(code);
      if (!d) { host.innerHTML = '<span class="mono">detail unavailable</span>'; return; }
      const q = d.quantum || { available: false };
      host.innerHTML = `
        <div class="badge-row"><b>Recommended action</b><span class="dim" style="max-width:60%;text-align:right">${esc(d.analysis.recommendation)}</span></div>
        <div class="badge-row"><b>Model confidence</b><span class="mono">${num(d.analysis.confidence, '%', 1)}</span></div>
        <div class="badge-row"><b>Quantum risk probability</b><span class="mono">${q.available ? num(q.quantum.risk_probability, '%', 1) : 'unavailable'}</span></div>
        <div class="badge-row"><b>Classical risk probability</b><span class="mono">${q.available && q.classical.risk_probability !== null ? num(q.classical.risk_probability, '%', 1) : 'unavailable'}</span></div>
        <div class="badge-row"><b>Early-warning level</b><span class="tag ${q.available ? q.early_warning.color : ''}">${q.available ? esc(q.early_warning.level) : '—'}</span></div>`;
    };

    body.querySelectorAll('#netList .card[data-code]').forEach(c => {
      c.addEventListener('click', () => openDetail(c.dataset.code));
      c.addEventListener('keydown', e => { if (e.key === 'Enter') openDetail(c.dataset.code); });
    });
    body.querySelectorAll('.node').forEach(n => {
      n.addEventListener('click', () => {
        const card = body.querySelector(`#netList .card[data-code="${n.dataset.code}"]`);
        if (card) { card.scrollIntoView({ behavior: 'smooth', block: 'center' }); openDetail(n.dataset.code); }
      });
    });
  }

  /* ======================= ANALYTICS ======================= */
  async function analytics() {
    const body = $('analyticsBody');
    body.innerHTML = loading('aggregating…');
    const [a, insurer] = await Promise.all([API.analytics(), API.insurer()]);
    if (!a) { body.innerHTML = `<div class="notice red">Analytics unavailable — the backend is not reachable.</div>`; return; }
    const dist = a.distributions || {};

    body.innerHTML = `
      <div class="grid g4">
        ${[['Fields monitored', a.fields_monitored], ['Stored observations', a.stored_observations],
      ['Early warnings', (a.warnings || {}).HIGH || 0], ['Monitor-level', (a.warnings || {}).MODERATE || 0]]
        .map(([k, v]) => `<div class="card"><div class="kpi"><b>${esc(v)}</b><span>${esc(k)}</span></div></div>`).join('')}
      </div>
      <div class="row"><span class="tag sim">${esc(a.data_label)}</span><span class="dim" style="font-size:.86rem">${esc(a.note)}</span></div>

      <div class="card">
        <h3>Trends from scans on this device</h3>
        <p class="dim" style="font-size:.9rem">Built from your own scan history stored locally. No historical values are invented; with fewer than two scans the charts say so.</p>
        <div class="grid g2" style="margin-top:.8rem">
          ${[['Crop health', h => h.result.health_score, 'green'],
             ['Disease risk', h => (h.result.risks || {}).disease, 'amber'],
             ['Water risk', h => (h.result.risks || {}).water, 'green'],
             ['Heat risk', h => (h.result.risks || {}).heat, 'red']]
            .map(([label, pick, tone]) => `<div class="card" style="padding:.9rem">
              <span class="mono">${esc(label)}</span>
              ${V.sparkline(API.readHistory().slice().reverse().map(pick), tone)}</div>`).join('')}
        </div>
      </div>

      <div class="split">
        <div class="card">
          <h3>Risk distribution across monitored fields</h3>
          ${Object.entries(dist).map(([k, d]) => `
            <div class="metric">
              <div class="metric-top"><span class="metric-name">${esc(k.replace(/_/g, ' '))}</span>
              <span class="metric-val">mean ${num(d.mean, '%', 1)} · n=${d.samples}</span></div>
              <div class="meter" style="background:none">
                <i style="width:${pct(d.low, d.samples)}%;background:var(--phosphor)"></i>
                <i style="width:${pct(d.moderate, d.samples)}%;background:var(--harvest)"></i>
                <i style="width:${pct(d.high, d.samples)}%;background:var(--alert)"></i>
              </div>
              <div class="mono" style="margin-top:.3rem">low ${d.low} · moderate ${d.moderate} · high ${d.high}</div>
            </div>`).join('')}
        </div>
        <div class="stack">
          <div class="card">
            <h3>Department view</h3>
            <p class="dim" style="font-size:.9rem">Field-level rows a district office would work from: condition, risk profile and the recommended next check per block.</p>
            <table><thead><tr><th>Field</th><th>State</th><th class="num">Health</th><th>Status</th></tr></thead><tbody>
              ${(a.demo_fields || []).map(f => `<tr><td>${esc(f.name)}</td><td>${esc(f.state)}</td>
                <td class="num">${esc(f.health_score)}</td><td><span class="tag ${f.color}">${esc(f.risk_bands.disease)}</span></td></tr>`).join('')}
            </tbody></table>
          </div>
          <div class="card">
            <h3>Insurer view</h3>
            <p class="dim" style="font-size:.9rem">${esc(insurer.purpose || 'Evidence trail for crop-insurance workflows.')}</p>
            ${(insurer.items || []).length ? `<table><thead><tr><th>Scan</th><th>Crop</th><th class="num">Confidence</th><th class="num">Disease risk</th></tr></thead><tbody>
              ${(insurer.items || []).slice(0, 8).map(i => `<tr><td class="mono">#${esc(i.observation_id)}</td><td>${esc(i.crop)}</td>
                <td class="num">${num(i.confidence, '%', 1)}</td><td class="num">${num((i.risks || {}).disease, '%', 1)}</td></tr>`).join('')}
            </tbody></table>` : '<p class="dim" style="font-size:.9rem">No stored scans yet — run a field scan to build an evidence trail.</p>'}
            <div class="notice" style="margin-top:.8rem">${esc(insurer.disclaimer || 'No financial recommendation is produced by this prototype.')}</div>
          </div>
        </div>
      </div>`;
  }
  const pct = (v, total) => total ? Math.round((v / total) * 100) : 0;

  /* ======================= DISEASE LIBRARY ======================= */
  function library() {
    const chips = $('libCrops');
    if (chips && !chips.dataset.done) {
      chips.dataset.done = '1';
      chips.innerHTML = `<button class="chip" data-crop="all" aria-pressed="true">All crops</button>` +
        D.CROPS.map(c => `<button class="chip" data-crop="${c.id}" aria-pressed="false">${c.icon} ${esc(c.en)}</button>`).join('');
      chips.addEventListener('click', e => {
        const b = e.target.closest('.chip'); if (!b) return;
        chips.querySelectorAll('.chip').forEach(x => x.setAttribute('aria-pressed', String(x === b)));
        renderLib();
      });
      $('libSearch').addEventListener('input', renderLib);
    }
    renderLib();
  }

  function renderLib() {
    const q = ($('libSearch').value || '').toLowerCase().trim();
    const active = document.querySelector('#libCrops .chip[aria-pressed="true"]');
    const crop = active ? active.dataset.crop : 'all';
    const lang = T.lang();
    const rows = D.DISEASES.filter(d =>
      (crop === 'all' || d.crop === crop) &&
      (!q || (d.name + ' ' + d.crop + ' ' + d.signs.join(' ') + ' ' + d.te + ' ' + d.hi).toLowerCase().includes(q)));
    $('libraryBody').innerHTML = rows.length ? rows.map(d => `
      <article class="dis-card">
        <div class="dis-art">${d.icon}</div>
        <div class="dis-body">
          <h4>${esc(d.name)}</h4>
          ${lang !== 'en' ? `<div class="dis-native">${esc(d[lang])}</div>` : `<div class="dim" style="font-size:.84rem">${esc(d.te)} · ${esc(d.hi)}</div>`}
          <span class="tag">${esc(T.cropName(d.crop))}</span>
          <div><b style="font-size:.86rem">Identification signs</b><ul>${d.signs.map(s => `<li>${esc(s)}</li>`).join('')}</ul></div>
          <div><b style="font-size:.86rem">Risk factors</b><ul>${d.risk.map(s => `<li>${esc(s)}</li>`).join('')}</ul></div>
          <div><b style="font-size:.86rem">Prevention and precautions</b><ul>${d.prevent.map(s => `<li>${esc(s)}</li>`).join('')}</ul></div>
          <div><b style="font-size:.86rem">Recommended monitoring</b><p class="dim" style="font-size:.86rem;margin:.2rem 0 0">${esc(d.monitor)}</p></div>
        </div>
      </article>`).join('') + `<div class="card" style="grid-column:1/-1"><span class="mono">safety</span><p class="dim" style="font-size:.9rem;margin:.4rem 0 0">${esc(D.SAFETY_NOTE)}</p></div>`
      : `<div class="card" style="grid-column:1/-1"><h3>No match</h3><p class="dim">Try a crop name, a symptom, or clear the search.</p></div>`;
  }

  /* ======================= RESEARCH ======================= */
  function research() {
    const body = $('researchBody');
    if (body.dataset.done) return;
    body.dataset.done = '1';
    body.innerHTML = `
      <nav class="row" style="margin-bottom:1rem">${D.RESEARCH.map(s => `<button class="tag" type="button" data-jump="${s.id}" style="cursor:pointer;border:0">${esc(s.title)}</button>`).join('')}</nav>
      ${D.RESEARCH.map(s => `<article class="card" id="${s.id}">
        <h3>${esc(s.title)}</h3>
        ${s.body.map(p => `<p>${esc(p)}</p>`).join('')}
      </article>`).join('')}
      <article class="card">
        <h3>Reproducing the numbers</h3>
        <p>Every metric in the Quantum lab comes from <code>backend/quantum/benchmark.py</code>. Run it directly:</p>
        <pre class="mono" style="white-space:pre-wrap">python -c "from backend.quantum.benchmark import run_benchmark; r=run_benchmark(); print(r['classical']['metrics'], r['quantum']['metrics'])"</pre>
        <p>The dataset seed, split seed and optimiser seed are fixed, so a rerun on the same machine reproduces the same table.</p>
      </article>`;
    /* in-page jumps: a plain #anchor would change location.hash and the router would leave this page */
    body.querySelectorAll('[data-jump]').forEach(b => b.addEventListener('click', () => {
      const el = document.getElementById(b.dataset.jump);
      if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }));
  }

  /* ======================= ABOUT ======================= */
  async function about() {
    const body = $('aboutBody');
    if (!body.dataset.done) {
    body.dataset.done = '1';
    body.innerHTML = `
      <div class="split">
        <div class="card">
          <h3>Prototype status: functional proof-of-concept</h3>
          <p>The prototype demonstrates an end-to-end agricultural early-warning workflow combining crop imagery, field and context data, classical feature processing and an experimental Qiskit-based QML layer. Real-world multispectral deployment, large-scale field validation and practical quantum advantage remain future validation stages.</p>
          ${D.STATUS_BADGES.map(([n, s, tone]) => `<div class="badge-row"><b>${esc(n)}</b>
            <span class="${tone === 'ok' ? 'badge-ok' : tone === 'exp' ? 'badge-exp' : 'badge-future'}">${tone === 'ok' ? '✓ ' : ''}${esc(s)}</span></div>`).join('')}
        </div>
        <div class="stack">
          <div class="card">
            <h3>What this prototype does not claim</h3>
            <ul class="dim" style="font-size:.92rem">
              <li>No quantum advantage, and no claim that the quantum model is more accurate.</li>
              <li>No quantum-hardware execution — the circuit runs on a simulator.</li>
              <li>No real multispectral or drone processing today.</li>
              <li>No deployment, no nationwide monitoring, no validated outbreak prediction.</li>
              <li>No pesticide prescription and no insurance or financial recommendation.</li>
            </ul>
          </div>
          <div class="card">
            <h3>Offline and rural context</h3>
            <p class="dim" style="font-size:.92rem">Scans run against a local backend; when it is unreachable the scan is stored on the device and queued. Queued scans sync to <code>/api/sync</code> when the connection returns. Language, low bandwidth and intermittent sensors are treated as normal operating conditions, not error states.</p>
          </div>
        </div>
      </div>
      <div class="card">
        <h3>Technology stack</h3>
        <table><tbody>${D.TECH_STACK.map(([k, v]) => `<tr><td style="width:190px"><b>${esc(k)}</b></td><td class="dim">${esc(v)}</td></tr>`).join('')}</tbody></table>
        <p class="dim" style="font-size:.86rem;margin-top:.8rem">Only technologies actually implemented are listed as implemented. Future inputs are marked as such.</p>
      </div>
      <div class="split">
        <div class="card">
          <h3>System health</h3>
          <p class="dim" style="font-size:.88rem">Every row below is measured on this page load \u2014 nothing here is a hard-coded "OK".</p>
          <div id="systemHealthBody"><span class="mono">checking every subsystem\u2026</span></div>
        </div>
        <div class="card">
          <h3>Model provenance</h3>
          <p class="dim" style="font-size:.88rem">Where the numbers shown elsewhere in this prototype actually come from.</p>
          <div id="provenanceBody"><span class="mono">loading\u2026</span></div>
        </div>
      </div>

      <div class="card">
        <h3>API surface</h3>
        <p class="dim" style="font-size:.92rem">Existing AstraNex endpoints are unchanged. The quantum layer is additive.</p>
        <div class="grid g2">
          <div><span class="mono">existing</span><ul class="dim" style="font-size:.88rem">
            <li>/api/analyze · /api/analyze-image · /api/analyze-multimodal</li>
            <li>/api/sensors · /api/devices · /api/history · /api/alerts</li>
            <li>/api/sync · /api/fields · /api/farmer-profile · /api/irrigation</li>
            <li>/api/model-status · /api/model-capabilities · /api/validation</li></ul></div>
          <div><span class="mono">added</span><ul class="dim" style="font-size:.88rem">
            <li>/api/quantum/status · /circuit · /features · /simulate · /feature-ranges</li>
            <li>/api/quantum/analyze · /analyze-result</li>
            <li>/api/quantum/benchmark · /training · /runs</li>
            <li>/api/demo/fields · /api/analytics/summary · /api/insurer/evidence</li></ul></div>
        </div>
      </div>`;
    }
    /* the shell above is static; health and provenance are re-measured on EVERY visit */
    const [health, provenance, readiness] = await Promise.all([API.systemHealth(), API.provenance(), API.readiness()]);
    const healthHost = $('systemHealthBody');
    if (healthHost) {
      const rows = Object.entries((health || {}).components || {});
      healthHost.innerHTML = rows.length ? rows.map(([name, info]) =>
        `<div class="badge-row"><b>${esc(name.replace(/_/g,' '))}</b><span class="${info.ok ? 'badge-ok' : 'badge-future'}">${info.ok ? '✓ ready' : '○ ' + esc(info.detail || 'not ready')}</span></div>`).join('')
        : '<span class="mono">Health data unavailable</span>';
    }
    const provHost = $('provenanceBody');
    if (provHost) {
      const qm = (provenance || {}).quantum_model || {};
      const ds = (provenance || {}).dataset || {};
      provHost.innerHTML = `<div class="badge-row"><b>Quantum engine</b><span class="mono">${esc(qm.engine || '—')}</span></div>
        <div class="badge-row"><b>Feature map</b><span class="mono">${esc(qm.feature_map || '—')}</span></div>
        <div class="badge-row"><b>Dataset</b><span class="mono">${esc(ds.label || '—')}</span></div>
        <div class="badge-row"><b>Validation</b><span class="mono" style="max-width:62%;text-align:right">${esc(provenance.validation || '—')}</span></div>`;
    }
    const readyHost = document.createElement('div');
    readyHost.className = 'card';
    readyHost.style.marginTop = '1rem';
    readyHost.innerHTML = `<h3>Deployment readiness</h3><div class="row" style="margin-top:.6rem"><span class="tag ${readiness && readiness.demo_ready ? 'green' : 'amber'}">Demo ${readiness && readiness.demo_ready ? 'ready' : 'blocked'}</span><span class="tag ${readiness && readiness.qml_production_ready ? 'green' : 'amber'}">QML production ${readiness && readiness.qml_production_ready ? 'ready' : 'prerequisites pending'}</span></div><p class="dim" style="font-size:.86rem;margin:.6rem 0 0">${esc(((readiness || {}).next_steps || []).join(' · ') || 'All readiness checks passed.')}</p>`;
    body.appendChild(readyHost);
  }

  return { home, farmer, intelligence, quantum, warnings, network, analytics, library, research, about, benchTable };
})();
