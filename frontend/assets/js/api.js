/* API client.
   Rules: never throw into the UI, always report why, and never lose a scan
   because the backend was unreachable. */
window.AX_API = (function () {

  const BASE = (location.protocol === 'file:') ? 'http://127.0.0.1:8000' : '';
  const QUEUE_KEY = 'ax_offline_queue';
  const HISTORY_KEY = 'ax_local_history';

  const state = {
    backend: 'checking', vision: 'checking', quantum: 'checking',
    quantumDetail: null, health: null, online: navigator.onLine
  };

  async function req(path, opts = {}, timeout = 25000) {
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), timeout);
    try {
      let res;
      try {
        res = await fetch(BASE + path, { signal: ctrl.signal, ...opts });
      } catch (e) {
        /* fetch itself failed: the server was never reached (offline, refused, timed out) */
        const err = new Error(e && e.name === 'AbortError' ? 'The request timed out' : 'The server could not be reached');
        err.network = true; throw err;
      }
      const text = await res.text();
      let body;
      try { body = text ? JSON.parse(text) : {}; } catch { body = { raw: text }; }
      if (!res.ok) {
        const raw = body && body.detail ? body.detail : `Request failed (${res.status})`;
        const detail = typeof raw === 'string' ? raw : (Array.isArray(raw) ? raw.map(d => d.msg || JSON.stringify(d)).join('; ') : JSON.stringify(raw));
        const err = new Error(detail); err.status = res.status; err.body = body; throw err;
      }
      return body;
    } finally { clearTimeout(timer); }
  }

  /* true only when the request never reached a working server; validation errors (4xx) and
     server-side rejections must NOT be treated as "offline" or they poison the sync queue */
  const isNetworkError = e => !!e && (e.network === true || e.status === 502 || e.status === 504);

  const get = p => req(p);
  const post = (p, body) => req(p, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body)
  });
  const postForm = (p, form) => req(p, { method: 'POST', body: form }, 60000);

  /* ---------------- health ---------------- */
  async function refreshHealth() {
    try {
      const h = await get('/api/health');
      state.health = h;
      state.backend = 'online';
      state.vision = h.model_mode === 'real-vision' ? 'ONNX model ready'
        : h.model_mode === 'context-only' ? 'context screening'
          : (h.model_mode || 'screening');
      state.quantum = h.quantum && h.quantum.available
        ? (h.quantum.mode === 'qiskit_machine_learning' ? 'Qiskit ML execution'
          : h.quantum.mode === 'qiskit_statevector' ? 'Qiskit state-vector'
            : 'built-in simulator (not Qiskit)')
        : 'unavailable';
      state.quantumDetail = h.quantum || null;
    } catch (e) {
      state.backend = 'offline';
      state.vision = 'unavailable';
      state.quantum = 'unavailable';
    }
    state.online = navigator.onLine;
    window.dispatchEvent(new CustomEvent('ax:health', { detail: state }));
    return state;
  }

  /* ---------------- offline queue ---------------- */
  const readQueue = () => { try { return JSON.parse(localStorage.getItem(QUEUE_KEY) || '[]'); } catch { return []; } };
  const writeQueue = q => { try { localStorage.setItem(QUEUE_KEY, JSON.stringify(q.slice(-60))); return true; } catch { return false; } };
  function enqueue(payload) {
    const q = readQueue();
    q.push({ ...payload, client_event_id: payload.client_event_id || ('off-' + Date.now() + '-' + Math.random().toString(36).slice(2, 8)), queued_at: Date.now() });
    const stored = writeQueue(q);
    window.dispatchEvent(new CustomEvent('ax:queue', { detail: q.length }));
    return stored ? q.length : -1;   /* -1: browser storage is full or blocked */
  }
  function queueSize() { return readQueue().length; }

  async function syncQueue() {
    const q = readQueue();
    if (!q.length) return { ok: true, synced: 0, dropped: 0, message: 'Nothing queued.' };
    const payloads = q.map(({ queued_at, local_result, ...rest }) => ({ ...rest, source: 'offline_sync' }));
    try {
      const out = await post('/api/sync', payloads);
      /* The server handles every record independently. Stored ones are done; records it rejected as
         invalid can never succeed, so drop them too; only genuinely retryable failures stay queued. */
      const retry = new Set((out.failed || []).filter(f => f.retryable).map(f => f.client_event_id).filter(Boolean));
      const keep = q.filter(item => retry.has(item.client_event_id));
      writeQueue(keep);
      window.dispatchEvent(new CustomEvent('ax:queue', { detail: keep.length }));
      const dropped = (out.failed || []).filter(f => !f.retryable).length;
      return { ok: true, synced: out.synced || 0, dropped, pending: keep.length,
               message: dropped ? `${dropped} queued scan(s) were invalid and were discarded.` : undefined };
    } catch (e) {
      return { ok: false, synced: 0, message: e.message };
    }
  }

  /* ---------------- local history (works offline) ---------------- */
  const readHistory = () => { try { return JSON.parse(localStorage.getItem(HISTORY_KEY) || '[]'); } catch { return []; } };
  function pushHistory(entry) {
    const h = readHistory();
    h.unshift({ ...entry, at: Date.now() });
    try { localStorage.setItem(HISTORY_KEY, JSON.stringify(h.slice(0, 40))); }
    catch { try { localStorage.setItem(HISTORY_KEY, JSON.stringify(h.slice(0, 10))); } catch { /* storage unavailable */ } }
  }

  /* ---------------- analysis ---------------- */
  async function analyze(payload, file) {
    if (file) {
      const fd = new FormData();
      fd.append('file', file);
      Object.entries(payload).forEach(([k, v]) => { if (v !== null && v !== undefined) fd.append(k, String(v)); });
      return { result: await postForm('/api/analyze-multimodal', fd), mode: 'multimodal' };
    }
    return { result: await post('/api/analyze', payload), mode: 'context' };
  }

  async function quantumOver(result, raw) {
    try {
      const out = await post('/api/quantum/analyze-result', { result, raw });
      return out.quantum;
    } catch (e) {
      return { available: false, error: e.message, message: 'Quantum layer unavailable. Classical agricultural analysis continues normally.' };
    }
  }

  const safe = async (fn, fallback) => { try { return await fn(); } catch (e) { return fallback; } };

  return {
    state, get, post, postForm, refreshHealth, analyze, quantumOver, safe, isNetworkError,
    enqueue, queueSize, syncQueue, pushHistory, readHistory,
    quantumStatus: () => safe(() => get('/api/quantum/status'), { available: false }),
    circuit: angles => safe(() => get('/api/quantum/circuit' + ((angles && angles.length === 4 && angles.every(Number.isFinite)) ? `?a0=${angles[0]}&a1=${angles[1]}&a2=${angles[2]}&a3=${angles[3]}` : '')), { available: false }),
    benchmark: () => safe(() => get('/api/quantum/benchmark'), { status: 'awaiting_benchmark', display: 'Awaiting experimental benchmark' }),
    runBenchmark: body => safe(() => post('/api/quantum/benchmark', body), { ok: false, message: 'Benchmark could not be started.' }),
    training: () => safe(() => get('/api/quantum/training'), { training: false }),
    featureRanges: () => safe(() => get('/api/quantum/feature-ranges'), { available: false }),
    simulate: (x, shots = 1024, seed) => safe(() => get(`/api/quantum/simulate?x0=${x[0]}&x1=${x[1]}&x2=${x[2]}&x3=${x[3]}&shots=${shots}` + (seed != null ? `&seed=${seed}` : '')), { available: false }),
    demoFields: () => safe(() => get('/api/demo/fields'), { items: [] }),
    demoField: code => safe(() => get('/api/demo/field/' + encodeURIComponent(code)), null),
    analytics: () => safe(() => get('/api/analytics/summary'), null),
    alerts: () => safe(() => get('/api/alerts?limit=40'), { items: [] }),
    history: () => safe(() => get('/api/history?limit=25'), { items: [] }),
    sensorsLatest: () => safe(() => get('/api/sensors/latest'), null),
    systemHealth: () => safe(() => get('/api/system/health'), null),
    provenance: () => safe(() => get('/api/quantum/provenance'), null),
    readiness: () => safe(() => get('/api/readiness'), null),
    fields: () => safe(() => get('/api/fields'), { items: [] }),
    insurer: () => safe(() => get('/api/insurer/evidence?limit=12'), { items: [] }),
    modelCapabilities: () => safe(() => get('/api/model-capabilities'), null),
    prepareModel: () => safe(() => post('/api/model/prepare', {}), { ok: false }),
    validation: () => safe(() => get('/api/validation'), null)
  };
})();
