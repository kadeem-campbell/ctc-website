/* CTC minimal offline cache (Netlify-safe) */
const CACHE_NAME = "ctc-static-v1";
const OFFLINE_URL = "/offline.html";
const CORE_ASSETS = ["/", "/offline.html", "/about/", "/events/", "/team/"];

self.addEventListener("install", (event) => {
  event.waitUntil((async () => {
    const cache = await caches.open(CACHE_NAME);
    await cache.addAll(CORE_ASSETS);
    self.skipWaiting();
  })());
});

self.addEventListener("activate", (event) => {
  event.waitUntil((async () => {
    const keys = await caches.keys();
    await Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)));
    self.clients.claim();
  })());
});

self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET") return;

  event.respondWith((async () => {
    try {
      const fresh = await fetch(req);
      return fresh;
    } catch (e) {
      const cache = await caches.open(CACHE_NAME);
      const cached = await cache.match(req, { ignoreSearch: true });
      return cached || cache.match(OFFLINE_URL, { ignoreSearch: true });
    }
  })());
});
