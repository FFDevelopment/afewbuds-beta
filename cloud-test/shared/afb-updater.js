(function(){
  'use strict';
  function byId(id){ return document.getElementById(id); }
  function setVisible(show){
    const overlay = byId('afb-prelaunch');
    if (overlay) overlay.hidden = !show;
  }
  function setStatus(title, detail){
    const titleEl = byId('afb-prelaunch-title');
    const detailEl = byId('afb-prelaunch-detail');
    const bar = byId('afb-prelaunch-progress');
    if (titleEl) titleEl.textContent = title || '';
    if (detailEl) detailEl.textContent = detail || '';
    if (bar) { bar.removeAttribute('data-indeterminate'); bar.value = 1; }
  }
  async function clearCaches(){
    if (!('caches' in window)) return;
    const keys = await caches.keys();
    await Promise.all(keys.map((key) => {
      if (key === 'AFB-Updater-Meta-v1' || key.startsWith('AFB-Release-v1-') || key.startsWith('AFewBuds Beta v0-sw-cache-')) {
        return caches.delete(key);
      }
      return Promise.resolve(false);
    }));
  }
  async function boot(){
    setVisible(true);
    setStatus('Loading cloud test…', 'Using the newest test build from GitHub.');
    try {
      await clearCaches();
      if ('serviceWorker' in navigator) {
        const reg = await navigator.serviceWorker.register('index.service.worker.js', { scope:'./', updateViaCache:'none' });
        try { await reg.update(); } catch (_) {}
        await navigator.serviceWorker.ready;
      }
      await clearCaches();
    } catch (e) {
      console.warn('Cloud-test cache reset:', e);
    }
    setVisible(false);
  }
  window.AFB_UPDATER = {
    boot,
    rollback: async()=>false,
    notifyGameStarting: ()=>{},
    markGameReady: ()=>{},
    markGameFailure: ()=>{},
    getState: ()=>({}),
    getLiveVersion: ()=>null
  };
})();
