'use strict';

const AFB_META_CACHE = 'AFB-Updater-Meta-v1';
const AFB_RELEASE_PREFIX = 'AFB-Release-v1-';

async function clearOldAfbCaches() {
  const keys = await caches.keys();
  await Promise.all(keys.map((key) => {
    if (key === AFB_META_CACHE || key.startsWith(AFB_RELEASE_PREFIX) || key.startsWith('AFewBuds Beta v0-sw-cache-')) {
      return caches.delete(key);
    }
    return Promise.resolve(false);
  }));
}

self.addEventListener('install', (event) => {
  event.waitUntil(self.skipWaiting());
});

self.addEventListener('activate', (event) => {
  event.waitUntil((async () => {
    await clearOldAfbCaches();
    await self.clients.claim();
    const clients = await self.clients.matchAll({ type: 'window', includeUncontrolled: true });
    for (const client of clients) {
      try {
        const url = new URL(client.url);
        if (!url.searchParams.has('afb_fresh')) {
          url.searchParams.set('afb_fresh', String(Date.now()));
          await client.navigate(url.toString());
        }
      } catch (_) {}
    }
  })());
});

self.addEventListener('fetch', (event) => {
  if (event.request.method !== 'GET') return;
  const url = new URL(event.request.url);
  const scope = new URL(self.registration.scope);
  if (url.origin !== scope.origin || !url.pathname.startsWith(scope.pathname)) return;

  event.respondWith((async () => {
    try {
      return await fetch(event.request, { cache: 'no-store' });
    } catch (error) {
      const cached = await caches.match(event.request);
      if (cached) return cached;
      throw error;
    }
  })());
});

self.addEventListener('message', (event) => {
  const port = event.ports && event.ports[0];
  const type = event.data && event.data.type;
  event.waitUntil((async () => {
    if (type === 'AFB_RESET_APP_CACHES') {
      await clearOldAfbCaches();
      if (port) port.postMessage({ ok: true, meta: {} });
      return;
    }
    if (type === 'AFB_GET_STATE') {
      if (port) port.postMessage({ ok: true, meta: {} });
      return;
    }
    if (port) port.postMessage({ ok: true, meta: {} });
  })());
});
