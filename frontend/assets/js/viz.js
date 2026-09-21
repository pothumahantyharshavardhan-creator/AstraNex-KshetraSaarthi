/* Shared visual components. */
window.AX_VIZ = (function () {

  const esc = s => String(s === null || s === undefined ? '' : s)
    .replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

  const band = v => v >= 70 ? 'red' : v >= 45 ? 'amber' : 'green';
  const num = (v, unit = '', dp = 0) => (v === null || v === undefined || v === '' || !Number.isFinite(Number(v))) ? '—' : Number(v).toFixed(dp) + unit;
  /* colour band for metrics where HIGH is GOOD (health score, sensor trust, confidence) */
  const bandGood = v => v >= 70 ? 'green' : v >= 45 ? 'amber' : 'red';

  /* horizontal block meter, as in the brief's field-intelligence sketch */
  function blocks(value, tone) {
    const filled = Math.max(0, Math.min(10, Math.round((Number(value) || 0) / 10)));
    const cls = tone || band(value);
    return `<div class="blocks ${cls === 'green' ? '' : cls}">${
      Array.from({ length: 10 }, (_, i) => `<span class="${i < filled ? 'on' : ''}"></span>`).join('')}</div>`;
  }

  function metric(name, value, label, tone) {
    const cls = tone || band(value);
    return `<div class="metric">
      <div class="metric-top"><span class="metric-name">${esc(name)}</span>
      <span class="metric-val">${esc(label !== undefined ? label : num(value, '%'))}</span></div>
      ${blocks(value, cls)}
    </div>`;
  }

  function meter(value, tone) {
    const cls = tone || band(value);
    return `<div class="meter ${cls === 'green' ? '' : cls}"><i style="width:${Math.max(2, Math.min(100, Number(value) || 0))}%"></i></div>`;
  }

  function toast(message, isError) {
    const el = document.createElement('div');
    el.className = 'toast' + (isError ? ' err' : '');
    el.setAttribute('role', isError ? 'alert' : 'status');
    el.textContent = message;
    document.body.appendChild(el);
    setTimeout(() => { el.style.opacity = '0'; el.style.transition = 'opacity .4s'; }, 3000);
    setTimeout(() => el.remove(), 3600);
  }

  /* ---------------- quantum circuit ---------------- */
  function circuitSVG(info) {
    const ops = (info.operations || []).filter(o => o.gate !== 'measure');
    const nq = info.qubits || 4;
    const colW = 58, left = 178, top = 42, rowH = 54;   /* left: room for the qubit labels */
    const clip = t => { t = String(t || ''); return t.length > 17 ? t.slice(0, 16) + '…' : t; };
    // assign each op a column: single-qubit ops advance their own wire, CX advances all
    const cursor = Array(nq).fill(0);
    const placed = ops.map(op => {
      let col;
      if (op.qubits.length > 1) {
        col = Math.max(...op.qubits.map(q => cursor[q]));
        op.qubits.forEach(q => { cursor[q] = col + 1; });
        for (let q = Math.min(...op.qubits); q <= Math.max(...op.qubits); q++) cursor[q] = Math.max(cursor[q], col + 1);
      } else {
        col = cursor[op.qubits[0]];
        cursor[op.qubits[0]] = col + 1;
      }
      return { ...op, col };
    });
    const cols = Math.max(...cursor, 1);
    const W = left + cols * colW + 86, H = top + nq * rowH + 18;
    const x = c => left + c * colW + colW / 2;
    const y = q => top + q * rowH;

    const wires = Array.from({ length: nq }, (_, q) =>
      `<line class="wire" x1="${left - 34}" y1="${y(q)}" x2="${W - 58}" y2="${y(q)}"/>
       <text class="qubit-label" x="8" y="${y(q) + 3}">q${q} · ${esc(clip(info.qubit_map && info.qubit_map[q] && info.qubit_map[q].label))}</text>`).join('');

    const gates = placed.map(op => {
      if (op.qubits.length > 1) {
        const [c, t] = op.qubits;
        return `<g class="gate entangle"><line x1="${x(op.col)}" y1="${y(c)}" x2="${x(op.col)}" y2="${y(t)}" stroke="#5FE3B4" stroke-opacity=".8"/>
          <circle cx="${x(op.col)}" cy="${y(c)}" r="4.5" fill="#5FE3B4"/>
          <circle cx="${x(op.col)}" cy="${y(t)}" r="8" fill="none" stroke="#5FE3B4" stroke-width="1.6"/>
          <line x1="${x(op.col) - 8}" y1="${y(t)}" x2="${x(op.col) + 8}" y2="${y(t)}" stroke="#5FE3B4" stroke-width="1.6"/>
          <title>${esc((op.label || 'CX').toUpperCase())} · control q${c} → target q${t}</title></g>`;
      }
      const q = op.qubits[0];
      const thetaValue = Number(op.theta);
      const theta = Number.isFinite(thetaValue) ? ` = ${thetaValue.toFixed(3)} rad` : '';
      const kind = op.kind === 'encoding' ? 'encoding' : 'variational';
      const feature = (info.qubit_map && info.qubit_map[q] && info.qubit_map[q].label) || '';
      const qiskitML = info.engine === 'qiskit_machine_learning';
      const detail = op.kind === 'encoding'
        ? (qiskitML ? `ZZFeatureMap encoding for ${feature}${theta}` : `Angle encoding of ${feature}${theta}`)
        : (qiskitML ? `RealAmplitudes trainable gate${theta}` : `Trainable variational rotation${theta}`);
      return `<g class="gate ${kind}" tabindex="0" data-qubit="${q}">
        <rect x="${x(op.col) - 19}" y="${y(q) - 15}" width="38" height="30" rx="6"/>
        <text x="${x(op.col)}" y="${y(q) + 4}" text-anchor="middle">${esc(op.label)}</text>
        <title>${esc(op.label)} on q${q} — ${esc(detail)}</title></g>`;
    }).join('');

    const meas = Array.from({ length: nq }, (_, q) =>
      `<g class="gate"><rect x="${W - 54}" y="${y(q) - 15}" width="38" height="30" rx="6"/>
       <text x="${W - 35}" y="${y(q) + 4}" text-anchor="middle">⟨Z⟩</text>
       <title>Measure ⟨Z⟩ on q${q}</title></g>`).join('');

    return `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Variational quantum circuit">
      <text x="8" y="20" font-family="IBM Plex Mono,monospace" font-size="10" fill="#7C8F84">ENCODING</text>
      <text x="${left + colW * Math.max(1, Math.floor(cols / 3))}" y="20" font-family="IBM Plex Mono,monospace" font-size="10" fill="#7C8F84">VARIATIONAL LAYERS</text>
      ${wires}${gates}${meas}</svg>`;
  }

  /* ---------------- India map (calibrated) ----------------
     assets/india_map.png is a plate-carree plot: x=0 is 67.013°E, y=0 is 38.01°N, 31.8 px per degree,
     1018 x 1050 px. Calibrated against the image's own 5° graticule and known coastal points. */
  const GEO = { lon0: 67.013, lat0: 38.01, ppd: 31.8, w: 1018, h: 1050 };
  const geoToPx = (lat, lon) => ({ x: (lon - GEO.lon0) * GEO.ppd, y: (GEO.lat0 - lat) * GEO.ppd });
  const pxToGeo = (x, y) => ({ lat: GEO.lat0 - y / GEO.ppd, lon: GEO.lon0 + x / GEO.ppd });
  /* fractions (0..1) of the image, for HTML overlays */
  const geoToFrac = (lat, lon) => { const p = geoToPx(lat, lon); return { fx: p.x / GEO.w, fy: p.y / GEO.h }; };
  const fracToGeo = (fx, fy) => pxToGeo(fx * GEO.w, fy * GEO.h);
  const project = geoToPx;

  function indiaMap(nodes, opts = {}) {
    const pts = (nodes || []).map(n => {
      const p = geoToPx(n.lat, n.lon);
      const tone = n.color === 'red' ? 'red' : n.color === 'amber' ? 'amber' : '';
      const flip = p.x > GEO.w * 0.72;          /* keep labels inside the frame */
      return `<g class="node ${tone}" data-code="${esc(n.code || '')}" tabindex="0" role="button" aria-label="${esc(n.name || '')}">
        <circle class="halo" cx="${p.x.toFixed(1)}" cy="${p.y.toFixed(1)}" r="20"/>
        <circle class="core" cx="${p.x.toFixed(1)}" cy="${p.y.toFixed(1)}" r="8"/>
        <text x="${(p.x + (flip ? -24 : 24)).toFixed(1)}" y="${(p.y + 6).toFixed(1)}" text-anchor="${flip ? 'end' : 'start'}">${esc(n.short || n.name || '')}</text>
        <title>${esc(n.name || '')}</title></g>`;
    }).join('');
    return `<svg class="india-svg" viewBox="0 0 ${GEO.w} ${GEO.h}" role="img" aria-label="Map of India with monitored demonstration fields">
      <image href="/assets/india_map.png" x="0" y="0" width="${GEO.w}" height="${GEO.h}" preserveAspectRatio="none"/>
      ${pts}
      ${opts.caption === false ? '' : `<text x="16" y="${GEO.h - 16}" font-family="IBM Plex Mono,monospace" font-size="17" fill="#8FA598">DEMONSTRATION FIELDS ONLY · NO DEPLOYMENT IS REPRESENTED</text>`}
    </svg>`;
  }

  /* ---------------- quantum state visuals ---------------- */
  /* Bloch sphere: orthographic view, azimuth 28°, elevation 18°. State vector (x,y,z) is the real
     reduced-state Bloch vector of the qubit, computed server-side from the circuit's state vector. */
  function blochSVG(b, label, entropy) {
    const R = 52, cx = 70, cy = 66, az = 28 * Math.PI / 180, el = 18 * Math.PI / 180;
    const P = (x, y, z) => {                       /* Bloch (x,y,z) -> screen; z is up */
      const X = x * Math.cos(az) - y * Math.sin(az);
      const Y = x * Math.sin(az) + y * Math.cos(az);
      return { sx: cx + R * X, sy: cy - R * (z * Math.cos(el) + Y * Math.sin(el)) };
    };
    const ring = (fn) => Array.from({ length: 65 }, (_, i) => { const t = i / 64 * 2 * Math.PI; const q = fn(t); const p = P(q[0], q[1], q[2]); return `${i ? 'L' : 'M'}${p.sx.toFixed(1)} ${p.sy.toFixed(1)}`; }).join('');
    const eq = ring(t => [Math.cos(t), Math.sin(t), 0]);
    const m1 = ring(t => [Math.cos(t), 0, Math.sin(t)]);
    const m2 = ring(t => [0, Math.cos(t), Math.sin(t)]);
    const tip = P(b.x, b.y, b.z), o = P(0, 0, 0);
    const zp = P(0, 0, 1), zm = P(0, 0, -1), xp = P(1, 0, 0), yp = P(0, 1, 0);
    const len = Math.max(0, Math.min(1, b.length));
    return `<svg viewBox="0 0 140 160" class="bloch" role="img" aria-label="Bloch sphere for ${esc(label)}: x ${b.x.toFixed(2)}, y ${b.y.toFixed(2)}, z ${b.z.toFixed(2)}">
      <circle cx="${cx}" cy="${cy}" r="${R}" class="b-sphere"/>
      <path d="${eq}" class="b-ring"/><path d="${m1}" class="b-ring faint"/><path d="${m2}" class="b-ring faint"/>
      <line x1="${zm.sx.toFixed(1)}" y1="${zm.sy.toFixed(1)}" x2="${zp.sx.toFixed(1)}" y2="${zp.sy.toFixed(1)}" class="b-axis"/>
      <line x1="${o.sx.toFixed(1)}" y1="${o.sy.toFixed(1)}" x2="${xp.sx.toFixed(1)}" y2="${xp.sy.toFixed(1)}" class="b-axis"/>
      <line x1="${o.sx.toFixed(1)}" y1="${o.sy.toFixed(1)}" x2="${yp.sx.toFixed(1)}" y2="${yp.sy.toFixed(1)}" class="b-axis"/>
      <text x="${(zp.sx + 4).toFixed(1)}" y="${(zp.sy - 2).toFixed(1)}" class="b-lbl">|0⟩</text>
      <text x="${(zm.sx + 4).toFixed(1)}" y="${(zm.sy + 9).toFixed(1)}" class="b-lbl">|1⟩</text>
      <text x="${(xp.sx + 3).toFixed(1)}" y="${(xp.sy + 3).toFixed(1)}" class="b-lbl dim">x</text>
      <text x="${(yp.sx + 3).toFixed(1)}" y="${(yp.sy + 3).toFixed(1)}" class="b-lbl dim">y</text>
      <line x1="${o.sx.toFixed(1)}" y1="${o.sy.toFixed(1)}" x2="${tip.sx.toFixed(1)}" y2="${tip.sy.toFixed(1)}" class="b-vec" style="opacity:${(0.45 + 0.55 * len).toFixed(2)}"/>
      <circle cx="${tip.sx.toFixed(1)}" cy="${tip.sy.toFixed(1)}" r="4.5" class="b-tip"/>
      <text x="70" y="142" text-anchor="middle" class="b-cap">${esc(label)}</text>
      <text x="70" y="154" text-anchor="middle" class="b-cap dim">|r|=${len.toFixed(2)} · S=${(entropy ?? 0).toFixed(2)} bit</text>
    </svg>`;
  }

  /* horizontal bar histogram of basis-state probabilities (16 states) or shot counts */
  function stateBars(rows, opts = {}) {
    if (!rows || !rows.length) return '<div class="mono">no state data</div>';
    const key = opts.key || 'probability';
    const max = Math.max(...rows.map(r => Number(r[key]) || 0), 1e-9);
    return `<div class="sbars" role="img" aria-label="${esc(opts.label || 'Measurement outcome probabilities')}">${rows.map(r => {
      const v = Number(r[key]) || 0;
      const shown = key === 'count' ? `${r.count} · ${(r.frequency * 100).toFixed(1)}%` : `${(v * 100).toFixed(1)}%`;
      return `<div class="sbar"><span class="ket">|${esc(r.state)}⟩</span><span class="track"><i style="width:${Math.max(1, v / max * 100).toFixed(1)}%"></i></span><span class="pv">${shown}</span></div>`;
    }).join('')}</div>`;
  }

  /* risk-vs-noise curve */
  function noiseChart(points) {
    const pts = (points || []).filter(p => Number.isFinite(p.risk_probability));
    if (pts.length < 2) return '<div class="mono">no noise data</div>';
    const w = 520, h = 190, l = 40, r = 14, t = 16, b = 34;
    const X = p => l + (p.noise / pts[pts.length - 1].noise) * (w - l - r);
    const Y = v => t + (1 - v / 100) * (h - t - b);
    const line = pts.map((p, i) => `${i ? 'L' : 'M'}${X(p).toFixed(1)} ${Y(p.risk_probability).toFixed(1)}`).join('');
    const grid = [0, 25, 50, 75, 100].map(v => `<line x1="${l}" y1="${Y(v)}" x2="${w - r}" y2="${Y(v)}" class="n-grid"/><text x="${l - 6}" y="${Y(v) + 3}" text-anchor="end" class="n-lbl">${v}</text>`).join('');
    const ticks = pts.filter((_, i) => i % 2 === 0).map(p => `<text x="${X(p).toFixed(1)}" y="${h - 14}" text-anchor="middle" class="n-lbl">${(p.noise * 100).toFixed(0)}%</text>`).join('');
    const dots = pts.map(p => `<circle cx="${X(p).toFixed(1)}" cy="${Y(p.risk_probability).toFixed(1)}" r="3.5" class="n-dot"><title>noise ${(p.noise * 100).toFixed(0)}% → risk ${p.risk_probability.toFixed(1)}%</title></circle>`).join('');
    return `<svg viewBox="0 0 ${w} ${h}" class="trend-svg" role="img" aria-label="Predicted risk versus simulated depolarising noise">
      ${grid}<line x1="${l}" y1="${Y(50)}" x2="${w - r}" y2="${Y(50)}" class="n-thresh"/>
      <path d="${line}" class="n-line"/>${dots}${ticks}
      <text x="${(l + w - r) / 2}" y="${h - 1}" text-anchor="middle" class="n-lbl">simulated depolarising noise strength</text></svg>`;
  }

  /* small trend sparkline for analytics */
  function sparkline(values, tone) {
    const vals = (values || []).filter(v => typeof v === 'number');
    if (vals.length < 2) return '<div class="mono">not enough history yet</div>';
    const w = 480, h = 90, pad = 8;
    const lo = Math.min(...vals), hi = Math.max(...vals);
    const color = tone === 'amber' ? '#E9B44C' : tone === 'red' ? '#E8613C' : '#5FE3B4';
    const pts = vals.map((v, i) => {
      const x = pad + (i / (vals.length - 1)) * (w - pad * 2);
      const y = h - pad - ((v - lo) / (hi - lo || 1)) * (h - pad * 2);
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    }).join(' ');
    return `<svg viewBox="0 0 ${w} ${h}" style="width:100%;height:auto" role="img" aria-label="Trend">
      <polyline points="${pts}" fill="none" stroke="${color}" stroke-width="2"/>
      <text x="${pad}" y="13" font-family="IBM Plex Mono,monospace" font-size="9" fill="#7C8F84">${hi.toFixed(1)}</text>
      <text x="${pad}" y="${h - 2}" font-family="IBM Plex Mono,monospace" font-size="9" fill="#7C8F84">${lo.toFixed(1)}</text></svg>`;
  }

  function trendLine(values, opts={}) {
    const vals=(values||[]).filter(v=>typeof v==='number'&&Number.isFinite(v));
    if(vals.length<2) return '<div class="mono">not enough history yet</div>';
    const w=520,h=150,p=18,lo=Math.min(...vals),hi=Math.max(...vals),range=hi-lo||1;
    const pts=vals.map((v,i)=>`${(p+i*(w-2*p)/(vals.length-1)).toFixed(1)},${(h-p-(v-lo)*(h-2*p)/range).toFixed(1)}`).join(' ');
    return `<svg viewBox="0 0 ${w} ${h}" class="trend-svg" role="img" aria-label="Field health trend"><line x1="${p}" y1="${h-p}" x2="${w-p}" y2="${h-p}" stroke="rgba(206,232,212,.18)"/><polyline points="${pts}" fill="none" stroke="#5FE3B4" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>${vals.map((v,i)=>{const x=p+i*(w-2*p)/(vals.length-1),y=h-p-(v-lo)*(h-2*p)/range;return `<circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="4" fill="#101A15" stroke="#5FE3B4" stroke-width="2"><title>${v.toFixed(0)}</title></circle>`}).join('')}<text x="${p}" y="13" class="chart-label">${hi.toFixed(0)}</text><text x="${p}" y="${h-2}" class="chart-label">${lo.toFixed(0)}</text></svg>`;
  }
  return { esc, band, bandGood, num, blocks, metric, meter, toast, circuitSVG, indiaMap, project, GEO, geoToPx, pxToGeo, geoToFrac, fracToGeo, blochSVG, stateBars, noiseChart, sparkline, trendLine };
})();
