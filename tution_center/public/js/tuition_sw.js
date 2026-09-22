// Josh Tuition Centre - Service Worker
// Cache-first shell, network-first data (Frappe API calls are never cached).
const APP_SHELL = "mobile-shell-v1";
const ASSET_CACHE = "mobile-assets-v1";

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(APP_SHELL).then((cache) => cache.addAll(["/mobile"]))
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys.filter((k) => ![APP_SHELL, ASSET_CACHE].includes(k)).map((k) => caches.delete(k))
      )
    ).then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);
  if (event.request.method !== "GET") return;

  // Never cache API responses or auth endpoints (always live data)
  if (
    url.pathname.startsWith("/api/") ||
    url.pathname.startsWith("/api/method") ||
    url.pathname.includes("login") ||
    url.pathname.includes("logout")
  ) {
    return;
  }

  // App shell (the /mobile page): network first, fall back to cache when offline
  if (url.pathname === "/mobile") {
    event.respondWith(
      fetch(event.request)
        .then((res) => {
          const copy = res.clone();
          caches.open(APP_SHELL).then((c) => c.put(event.request, copy));
          return res;
        })
        .catch(() => caches.match(event.request).then((r) => r || caches.match("/mobile")))
    );
    return;
  }

  // Static assets: cache-first
  if (
    url.pathname.startsWith("/assets/tution_center/") ||
    url.pathname.endsWith(".png") ||
    url.pathname.endsWith(".css") ||
    url.pathname.endsWith(".js")
  ) {
    event.respondWith(
      caches.match(event.request).then(
        (hit) =>
          hit ||
          fetch(event.request).then((res) => {
            const copy = res.clone();
            caches.open(ASSET_CACHE).then((c) => c.put(event.request, copy));
            return res;
          })
      )
    );
  }
});
