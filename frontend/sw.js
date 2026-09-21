/* Offline-first shell cache. API calls are never cached: stale agricultural
   advice is worse than no advice, so they fail fast and the app queues locally.

   Strategy: navigations and app code are NETWORK-FIRST (so a new release is picked up immediately)
   and fall back to the cache when offline; images/fonts are cache-first. Only navigations fall
   back to the app shell -- a failed script or image must fail, not silently become HTML. */
const CACHE = 'astranex-shell-v3.3.0';
const SHELL = [
  '/', '/static/css/astranex.css', '/static/js/data.js', '/static/js/i18n.js',
  '/static/js/api.js', '/static/js/viz.js', '/static/js/pages.js', '/static/js/quantum-bg.js',
  '/static/js/app.js', '/assets/india_map.png'
];

self.addEventListener('install', e => {
  /* one missing file must not abort the whole install, so cache each entry independently */
  e.waitUntil(caches.open(CACHE)
    .then(c => Promise.all(SHELL.map(u => c.add(u).catch(() => null))))
    .then(() => self.skipWaiting()));
});

self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(keys =>
    Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim()));
});

const isCode = p => p === '/' || p.startsWith('/static/') || p === '/app';

self.addEventListener('fetch', e => {
  const req = e.request, url = new URL(req.url);
  if (req.method !== 'GET' || url.origin !== location.origin) return;
  if (url.pathname.startsWith('/api/') || url.pathname.startsWith('/docs') || url.pathname === '/openapi.json' || url.pathname.startsWith('/legacy')) return;

  if (req.mode === 'navigate' || isCode(url.pathname)) {
    e.respondWith(fetch(req).then(res => {
      if (res.ok) { const copy = res.clone(); caches.open(CACHE).then(c => c.put(req, copy)); }
      return res;
    }).catch(() => caches.match(req).then(hit => hit || (req.mode === 'navigate' ? caches.match('/') : Response.error()))));
    return;
  }
  e.respondWith(caches.match(req).then(hit => hit || fetch(req).then(res => {
    if (res.ok) { const copy = res.clone(); caches.open(CACHE).then(c => c.put(req, copy)); }
    return res;
  })));
});
