(function(){
  'use strict';

  const RELEASE_PREFIX = 'AFB-Release-v1-';
  const STATE_TIMEOUT_MS = 5000;
  const GAME_BOOT_TIMEOUT_MS = 30000;
  const VERSION_URL = 'version.json';
  const RELEASE_ID_FALLBACK = '0.7.9-beta.20-cloudpush1';

  const state = {
    registration: null,
    sw: null,
    live: null,
    meta: null,
    pendingAtBoot: false,
    gameBootTimer: null,
    started: false,
    currentRelease: RELEASE_ID_FALLBACK
  };

  function byId(id){ return document.getElementById(id); }
  function setVisible(show){
    const overlay = byId('afb-prelaunch');
    if (overlay) overlay.hidden = !show;
  }
  function setStatus(title, detail, progress){
    const titleEl = byId('afb-prelaunch-title');
    const detailEl = byId('afb-prelaunch-detail');
    const bar = byId('afb-prelaunch-progress');
    if (titleEl) titleEl.textContent = title || '';
    if (detailEl) detailEl.textContent = detail || '';
    if (bar) {
      if (typeof progress === 'number' && Number.isFinite(progress)) {
        bar.removeAttribute('data-indeterminate');
        bar.value = Math.max(0, Math.min(1, progress));
      } else {
        bar.setAttribute('data-indeterminate', 'true');
        bar.removeAttribute('value');
      }
    }
  }
  function sleep(ms){ return new Promise(resolve => setTimeout(resolve, ms)); }
  function safeReleaseId(value){ return String(value || '').replace(/[^A-Za-z0-9._-]/g, '_').slice(0,120); }
  function releaseCacheName(releaseId){ return RELEASE_PREFIX + safeReleaseId(releaseId); }
  function bytesToHex(buffer){
    const bytes = new Uint8Array(buffer);
    let out = '';
    for (let i=0;i<bytes.length;i++) out += bytes[i].toString(16).padStart(2,'0');
    return out;
  }
  async function sha256(buffer){
    const digest = await crypto.subtle.digest('SHA-256', buffer);
    return bytesToHex(digest);
  }

  async function registerWorker(){
    if (!('serviceWorker' in navigator) || !('caches' in window)) return null;
    const reg = await navigator.serviceWorker.register('index.service.worker.js', { scope: './', updateViaCache: 'none' });
    try { await reg.update(); } catch (_) {}
    state.registration = reg;
    if (!reg.active) {
      const candidate = reg.installing || reg.waiting;
      if (candidate) {
        await new Promise((resolve) => {
          if (candidate.state === 'activated') { resolve(); return; }
          const timer = setTimeout(resolve, STATE_TIMEOUT_MS);
          candidate.addEventListener('statechange', () => {
            if (candidate.state === 'activated') { clearTimeout(timer); resolve(); }
          });
        });
      }
    }
    const ready = await navigator.serviceWorker.ready;
    state.sw = reg.active || ready.active || navigator.serviceWorker.controller || null;
    return state.sw;
  }

  function messageWorker(payload){
    return new Promise((resolve, reject) => {
      const worker = state.sw || (state.registration && state.registration.active) || navigator.serviceWorker.controller;
      if (!worker) { reject(new Error('updater_worker_unavailable')); return; }
      const channel = new MessageChannel();
      const timer = setTimeout(() => reject(new Error('updater_worker_timeout')), STATE_TIMEOUT_MS);
      channel.port1.onmessage = (event) => {
        clearTimeout(timer);
        const data = event.data || {};
        if (data.ok === false) reject(new Error(data.error || 'updater_worker_error'));
        else resolve(data);
      };
      worker.postMessage(payload, [channel.port2]);
    });
  }

  async function getState(){
    try {
      const result = await messageWorker({ type:'AFB_GET_STATE' });
      state.meta = result.meta || {};
      return state.meta;
    } catch (_) {
      state.meta = {};
      return state.meta;
    }
  }

  async function fetchManifest(){
    const url = VERSION_URL + '?afb_check=' + Date.now();
    const response = await fetch(url, { cache:'no-store', credentials:'same-origin' });
    if (!response.ok) throw new Error('version_check_http_' + response.status);
    const manifest = await response.json();
    if (!manifest || !manifest.release_id || !Array.isArray(manifest.files) || !manifest.files.length) {
      throw new Error('version_manifest_invalid');
    }
    state.live = manifest;
    state.currentRelease = String(manifest.release_id);
    return manifest;
  }

  async function stageRelease(manifest){
    const releaseId = safeReleaseId(manifest.release_id);
    const cacheName = releaseCacheName(releaseId);
    await caches.delete(cacheName);
    const cache = await caches.open(cacheName);
    let completed = 0;
    let completedBytes = 0;
    const totalBytes = manifest.files.reduce((sum, f) => sum + Number(f.size || 0), 0) || 1;

    try {
      for (const file of manifest.files) {
        const path = String(file.path || '').replace(/^\/+/, '');
        if (!path) throw new Error('manifest_file_path_missing');
        const expectedSize = Number(file.size || 0);
        const expectedHash = String(file.sha256 || '').toLowerCase();
        setStatus('Updating AFewBuds…', 'Downloading ' + path, completedBytes / totalBytes);
        const joiner = path.includes('?') ? '&' : '?';
        const stagedUrl = path + joiner + 'afb_stage=' + encodeURIComponent(releaseId) + '&t=' + Date.now();
        const response = await fetch(stagedUrl, { cache:'no-store', credentials:'same-origin' });
        if (!response.ok) throw new Error(path + ' returned HTTP ' + response.status);
        const buffer = await response.arrayBuffer();
        if (expectedSize && buffer.byteLength !== expectedSize) {
          throw new Error(path + ' size mismatch (' + buffer.byteLength + ' / ' + expectedSize + ')');
        }
        if (expectedHash) {
          const actualHash = await sha256(buffer);
          if (actualHash !== expectedHash) throw new Error(path + ' checksum mismatch');
        }
        const headers = new Headers(response.headers);
        headers.set('Cache-Control','no-store');
        const cleanUrl = new URL(path, location.href).toString();
        await cache.put(cleanUrl, new Response(buffer, { status:200, statusText:'OK', headers }));
        completed += 1;
        completedBytes += buffer.byteLength;
        setStatus('Updating AFewBuds…', completed + ' / ' + manifest.files.length + ' files verified', completedBytes / totalBytes);
      }
      return { cacheName, releaseId };
    } catch (error) {
      await caches.delete(cacheName);
      throw error;
    }
  }

  async function activateRelease(manifest, staged){
    const result = await messageWorker({
      type:'AFB_ACTIVATE_RELEASE',
      release_id: staged.releaseId,
      cache_name: staged.cacheName
    });
    state.meta = result.meta || {};
    return state.meta;
  }

  async function rollback(reason){
    try {
      setVisible(true);
      setStatus('Restoring last working version…', 'The update did not start correctly. Your save data is untouched.', null);
      const result = await messageWorker({ type:'AFB_ROLLBACK', reason: String(reason || 'startup_failed') });
      state.meta = result.meta || {};
      await sleep(800);
      location.replace('./index.html?afb_rollback=' + Date.now());
      return true;
    } catch (error) {
      const detail = byId('afb-prelaunch-detail');
      if (detail) detail.textContent = 'Rollback could not complete automatically. Use afewbuds-update.html to repair the app cache. Save data was not changed.';
      const recover = byId('afb-prelaunch-recover');
      if (recover) { recover.hidden = false; recover.onclick = () => location.href='afewbuds-update.html'; }
      return false;
    }
  }

  async function confirmRelease(){
    if (!state.meta || !state.meta.pending) return;
    try {
      const result = await messageWorker({ type:'AFB_CONFIRM_RELEASE', release_id: state.meta.active_release || state.currentRelease });
      state.meta = result.meta || state.meta;
    } catch (_) {}
  }

  async function boot(){
    if (state.started) return;
    state.started = true;
    setVisible(true);
    setStatus('Checking AFewBuds…', 'Looking for an update before launch.', null);

    let workerAvailable = false;
    try {
      workerAvailable = !!(await registerWorker());
    } catch (_) {
      workerAvailable = false;
    }
    const meta = workerAvailable ? await getState() : {};
    state.pendingAtBoot = !!meta.pending;

    let manifest = null;
    try {
      manifest = await fetchManifest();
    } catch (error) {
      if (meta && meta.active_release) {
        setStatus('Offline / update check unavailable', 'Starting installed AFewBuds ' + meta.active_release + '.', 1);
      } else {
        setStatus('Update check unavailable', 'Starting the installed game. No save data was changed.', 1);
      }
      await sleep(650);
      setVisible(false);
      return;
    }

    if (!workerAvailable) {
      setStatus('Updater unavailable', 'Starting AFewBuds without changing the installed files.', 1);
      await sleep(650);
      setVisible(false);
      return;
    }

    // This page is the newly activated release. Do not stage it again; it is
    // waiting for the game to prove it can boot before we mark it as permanent.
    if (meta.pending && meta.active_release === safeReleaseId(manifest.release_id)) {
      try {
        const result = await messageWorker({ type:'AFB_LAUNCHER_OK', release_id: meta.active_release });
        state.meta = result.meta || meta;
      } catch (_) {}
      setStatus('Update installed', 'Starting AFewBuds ' + manifest.game_build + '…', 1);
      await sleep(450);
      setVisible(false);
      return;
    }

    if (meta.active_release === safeReleaseId(manifest.release_id) && meta.active_cache) {
      setStatus('AFewBuds is up to date', manifest.game_build + ' • Starting…', 1);
      await sleep(300);
      setVisible(false);
      return;
    }

    try {
      const from = meta.active_release || 'first install';
      setStatus('Update available', from + ' → ' + manifest.release_id, 0);
      const staged = await stageRelease(manifest);
      await activateRelease(manifest, staged);
      setStatus('Update verified', 'Switching to ' + manifest.release_id + '…', 1);
      await sleep(500);
      location.replace('./index.html?afb_release=' + encodeURIComponent(manifest.release_id));
      await new Promise(() => {});
    } catch (error) {
      console.warn('AFewBuds update failed; keeping installed release:', error);
      setStatus('Update could not be completed', 'Starting your current version instead. ' + String(error && error.message || error), 1);
      await sleep(1300);
      setVisible(false);
    }
  }

  function notifyGameStarting(){
    if (!state.meta || !state.meta.pending) return;
    clearTimeout(state.gameBootTimer);
    state.gameBootTimer = setTimeout(() => rollback('game_boot_timeout'), GAME_BOOT_TIMEOUT_MS);
  }

  function markGameReady(){
    clearTimeout(state.gameBootTimer);
    state.gameBootTimer = null;
    if (!state.meta || !state.meta.pending) return;
    // Let the main scene settle for a few seconds before committing the release.
    setTimeout(() => confirmRelease(), 4000);
  }

  function markGameFailure(error){
    clearTimeout(state.gameBootTimer);
    state.gameBootTimer = null;
    if (state.meta && state.meta.pending) rollback('game_start_failed:' + String(error && error.message || error || 'unknown'));
  }

  window.AFB_UPDATER = {
    boot,
    rollback,
    notifyGameStarting,
    markGameReady,
    markGameFailure,
    getState: () => state.meta,
    getLiveVersion: () => state.live
  };
})();
