/* AFewBuds transactional updater service worker.
 * App releases are staged in versioned CacheStorage buckets. A new release only
 * becomes active after every file has downloaded and verified in the launcher.
 * The previous release is kept for rollback. Save data in IndexedDB/localStorage
 * is never touched by this worker.
 */
'use strict';

const AFB_META_CACHE = 'AFB-Updater-Meta-v1';
const AFB_RELEASE_PREFIX = 'AFB-Release-v1-';
const AFB_META_URL = new URL('__afb_updater_meta__', self.registration.scope).toString();
const AFB_OFFLINE_FALLBACK = 'index.offline.html';
const AFB_PENDING_ROLLBACK_MS = 90 * 1000;

function cleanReleaseId(value) {
  return String(value || '').replace(/[^A-Za-z0-9._-]/g, '_').slice(0, 120);
}

function releaseCacheName(releaseId) {
  return AFB_RELEASE_PREFIX + cleanReleaseId(releaseId);
}

function scopeUrl(path) {
  return new URL(String(path || '').replace(/^\/+/, ''), self.registration.scope).toString();
}

function requestFor(path) {
  return new Request(scopeUrl(path), { method: 'GET' });
}

async function readMeta() {
  const cache = await caches.open(AFB_META_CACHE);
  const response = await cache.match(AFB_META_URL);
  if (!response) {
    return {
      active_release: '',
      active_cache: '',
      previous_release: '',
      previous_cache: '',
      pending: false,
      launcher_ok: false,
      pending_nav_count: 0,
      activated_at: 0,
      confirmed_at: 0,
      rollback_reason: ''
    };
  }
  try {
    return Object.assign({
      active_release: '', active_cache: '', previous_release: '', previous_cache: '',
      pending: false, launcher_ok: false, pending_nav_count: 0, activated_at: 0, confirmed_at: 0, rollback_reason: ''
    }, await response.json());
  } catch (_) {
    return {
      active_release: '', active_cache: '', previous_release: '', previous_cache: '',
      pending: false, launcher_ok: false, pending_nav_count: 0, activated_at: 0, confirmed_at: 0, rollback_reason: 'meta_parse_failed'
    };
  }
}

async function writeMeta(meta) {
  const cache = await caches.open(AFB_META_CACHE);
  await cache.put(AFB_META_URL, new Response(JSON.stringify(meta), {
    headers: { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' }
  }));
  return meta;
}

async function maybeAutoRollback(meta) {
  if (!meta.pending || meta.launcher_ok || !meta.previous_cache || !meta.activated_at) return meta;
  if ((Date.now() - Number(meta.activated_at)) < AFB_PENDING_ROLLBACK_MS) return meta;
  const badCache = meta.active_cache;
  const rolled = Object.assign({}, meta, {
    active_release: meta.previous_release || '',
    active_cache: meta.previous_cache || '',
    previous_release: '',
    previous_cache: '',
    pending: false,
    launcher_ok: false,
    pending_nav_count: 0,
    activated_at: 0,
    rollback_reason: 'pending_release_not_confirmed'
  });
  await writeMeta(rolled);
  if (badCache && badCache !== rolled.active_cache && badCache.startsWith(AFB_RELEASE_PREFIX)) {
    await caches.delete(badCache);
  }
  return rolled;
}

async function matchActive(meta, relativePath) {
  if (!meta.active_cache) return null;
  const cache = await caches.open(meta.active_cache);
  return cache.match(requestFor(relativePath));
}

function relativePathFromUrl(url) {
  const scope = new URL(self.registration.scope);
  const parsed = new URL(url);
  let rel = parsed.pathname.startsWith(scope.pathname)
    ? parsed.pathname.slice(scope.pathname.length)
    : parsed.pathname.replace(/^\/+/, '');
  if (!rel || rel.endsWith('/')) rel += 'index.html';
  return rel.replace(/^\/+/, '');
}

self.addEventListener('install', (event) => {
  event.waitUntil(self.skipWaiting());
});

self.addEventListener('activate', (event) => {
  event.waitUntil(self.clients.claim());
});

self.addEventListener('fetch', (event) => {
  if (event.request.method !== 'GET') return;
  const url = new URL(event.request.url);
  const scope = new URL(self.registration.scope);
  if (url.origin !== scope.origin || !url.pathname.startsWith(scope.pathname)) return;

  // cloud-test is an isolated test channel. Never serve it from the stable
  // root release cache; always let the browser fetch the current test files.
  const relativePath = url.pathname.slice(scope.pathname.length);
  if (relativePath.startsWith('cloud-test/')) {
    event.respondWith(fetch(event.request, { cache: 'no-store' }));
    return;
  }

  // Staging requests and the tiny version manifest must always hit the network.
  if (url.searchParams.has('afb_stage') || url.pathname.endsWith('/version.json') || url.pathname.endsWith('/index.service.worker.js')) {
    event.respondWith(fetch(event.request, { cache: 'no-store' }));
    return;
  }

  event.respondWith((async () => {
    let meta = await readMeta();
    meta = await maybeAutoRollback(meta);
    if (event.request.mode === 'navigate' && meta.pending && !meta.launcher_ok && meta.previous_cache) {
      const attempts = Number(meta.pending_nav_count || 0);
      if (attempts >= 1) {
        const failedCache = meta.active_cache;
        meta = {
          active_release: meta.previous_release || '',
          active_cache: meta.previous_cache || '',
          previous_release: '',
          previous_cache: '',
          pending: false,
          launcher_ok: true,
          pending_nav_count: 0,
          activated_at: 0,
          confirmed_at: Date.now(),
          rollback_reason: 'pending_release_failed_before_launcher_ready'
        };
        await writeMeta(meta);
        if (failedCache && failedCache !== meta.active_cache && failedCache.startsWith(AFB_RELEASE_PREFIX)) {
          await caches.delete(failedCache);
        }
      } else {
        meta.pending_nav_count = 1;
        await writeMeta(meta);
      }
    }
    const relative = relativePathFromUrl(event.request.url);
    const activeHit = await matchActive(meta, relative);
    if (activeHit) return activeHit;

    try {
      return await fetch(event.request);
    } catch (error) {
      const offline = await matchActive(meta, AFB_OFFLINE_FALLBACK);
      if (event.request.mode === 'navigate' && offline) return offline;
      throw error;
    }
  })());
});

async function pruneReleaseCaches(meta) {
  const keep = new Set([meta.active_cache, meta.previous_cache, AFB_META_CACHE].filter(Boolean));
  const keys = await caches.keys();
  await Promise.all(keys.map((key) => {
    if (key.startsWith(AFB_RELEASE_PREFIX) && !keep.has(key)) return caches.delete(key);
    return Promise.resolve(false);
  }));
}

async function handleMessage(data) {
  const type = data && data.type;
  let meta = await readMeta();
  meta = await maybeAutoRollback(meta);

  if (type === 'AFB_GET_STATE') {
    return { ok: true, meta };
  }
  if (type === 'AFB_ACTIVATE_RELEASE') {
    const releaseId = cleanReleaseId(data.release_id);
    const cacheName = String(data.cache_name || releaseCacheName(releaseId));
    if (!releaseId || !cacheName.startsWith(AFB_RELEASE_PREFIX)) throw new Error('invalid_release');
    const keys = await caches.keys();
    if (!keys.includes(cacheName)) throw new Error('staged_cache_missing');
    if (meta.active_cache === cacheName && meta.active_release === releaseId) {
      return { ok: true, meta };
    }
    const next = {
      active_release: releaseId,
      active_cache: cacheName,
      previous_release: meta.active_release || '',
      previous_cache: meta.active_cache || '',
      pending: true,
      launcher_ok: false,
      pending_nav_count: 0,
      activated_at: Date.now(),
      confirmed_at: 0,
      rollback_reason: ''
    };
    await writeMeta(next);
    await pruneReleaseCaches(next);
    return { ok: true, meta: next };
  }
  if (type === 'AFB_LAUNCHER_OK') {
    if (meta.active_release && (!data.release_id || cleanReleaseId(data.release_id) === meta.active_release)) {
      meta.launcher_ok = true;
      meta.pending_nav_count = Number(meta.pending_nav_count || 0);
      await writeMeta(meta);
    }
    return { ok: true, meta };
  }
  if (type === 'AFB_CONFIRM_RELEASE') {
    if (meta.active_release && (!data.release_id || cleanReleaseId(data.release_id) === meta.active_release)) {
      meta.pending = false;
      meta.launcher_ok = true;
      meta.pending_nav_count = 0;
      meta.confirmed_at = Date.now();
      meta.rollback_reason = '';
      await writeMeta(meta);
      await pruneReleaseCaches(meta);
    }
    return { ok: true, meta };
  }
  if (type === 'AFB_ROLLBACK') {
    if (!meta.previous_cache) return { ok: false, error: 'no_previous_release', meta };
    const failedCache = meta.active_cache;
    const rolled = {
      active_release: meta.previous_release || '',
      active_cache: meta.previous_cache || '',
      previous_release: '',
      previous_cache: '',
      pending: false,
      launcher_ok: false,
      pending_nav_count: 0,
      activated_at: 0,
      confirmed_at: Date.now(),
      rollback_reason: String(data.reason || 'manual_rollback')
    };
    await writeMeta(rolled);
    if (failedCache && failedCache !== rolled.active_cache && failedCache.startsWith(AFB_RELEASE_PREFIX)) {
      await caches.delete(failedCache);
    }
    return { ok: true, meta: rolled };
  }
  if (type === 'AFB_RESET_APP_CACHES') {
    const keys = await caches.keys();
    await Promise.all(keys.map((key) => {
      if (key === AFB_META_CACHE || key.startsWith(AFB_RELEASE_PREFIX) || key.startsWith('AFewBuds Beta v0-sw-cache-')) {
        return caches.delete(key);
      }
      return Promise.resolve(false);
    }));
    return { ok: true, meta: await readMeta() };
  }
  return { ok: false, error: 'unknown_message', meta };
}

self.addEventListener('message', (event) => {
  const port = event.ports && event.ports[0];
  event.waitUntil((async () => {
    try {
      const response = await handleMessage(event.data || {});
      if (port) port.postMessage(response);
    } catch (error) {
      if (port) port.postMessage({ ok: false, error: String(error && error.message || error) });
    }
  })());
});
