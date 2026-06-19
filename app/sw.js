const CACHE = 'trakx-v1';
const PRECACHE = ['/app/', '/app/index.html', '/app/favicon.svg', '/app/manifest.json'];

self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(CACHE).then(c => c.addAll(PRECACHE)).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', e => {
  const url = new URL(e.request.url);

  // Ne pas intercepter les requêtes API ou Supabase
  if (url.hostname.includes('trakx.fr') && url.pathname.startsWith('/app') === false) return;
  if (url.hostname.includes('supabase.co')) return;
  if (url.hostname.includes('api.trakx.fr')) return;
  if (url.hostname.includes('onrender.com')) return;
  if (url.hostname.includes('googletagmanager')) return;
  if (url.hostname.includes('clarity.ms')) return;

  // Stale-while-revalidate pour les assets statiques
  if (e.request.method !== 'GET') return;

  e.respondWith(
    caches.open(CACHE).then(cache =>
      cache.match(e.request).then(cached => {
        const fetched = fetch(e.request).then(res => {
          if (res.ok) cache.put(e.request, res.clone());
          return res;
        }).catch(() => cached);
        return cached || fetched;
      })
    )
  );
});
