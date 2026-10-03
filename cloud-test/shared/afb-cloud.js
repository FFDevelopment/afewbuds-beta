(function(){
  'use strict';

  const DB_NAME = '/userfs';
  const DB_VERSION = 21;
  const SAVE_BASENAME = 'bud_empire_beta_save.json';
  const STORE_NAME = 'FILE_DATA';
  const SAVE_KEY = '/userfs/' + SAVE_BASENAME;
  const FILE_MODE = 33206; // regular file + rw-rw-rw- (Emscripten/Godot IDBFS)
  const MARK_ACCOUNT = 'afb_cloud_account';
  const MARK_UNIX = 'afb_cloud_last_sync_unix';
  const MARK_UPDATED = 'afb_cloud_last_sync_at';
  const AUTO_SYNC_MS = 30000;

  let syncTimer = null;
  let syncing = false;
  let lastUploadedUnix = 0;
  let gamePushQueue = Promise.resolve();

  function api(){ return window.AFB_API || null; }
  function session(){ const a=api(); return a && a.getPlayerSession ? a.getPlayerSession() : null; }
  function unixOf(save){ const n=Number(save && save.saved_unix || 0); return Number.isFinite(n) ? Math.max(0, Math.floor(n)) : 0; }
  function salesOf(save){ const s=save && save.advancement_stats; return Number(s && s.sales || 0) || 0; }
  function summary(save){
    if(!save || typeof save !== 'object') return 'No career on this device';
    const day=Math.max(1, Number(save.game_day||1)||1);
    const cash=Math.max(0, Number(save.cash||0)||0);
    const earned=Math.max(0, Number(save.lifetime_revenue||0)||0);
    const sales=Math.max(0, salesOf(save));
    const when=unixOf(save) ? new Date(unixOf(save)*1000).toLocaleString() : 'Unknown save time';
    return `Day ${day} • $${Math.round(cash).toLocaleString()} cash • $${Math.round(earned).toLocaleString()} earned • ${Math.round(sales)} sales • ${when}`;
  }

  function setMarker(save, player){
    try {
      localStorage.setItem(MARK_ACCOUNT, String(player && (player.account_id || player.username) || '').toLowerCase());
      localStorage.setItem(MARK_UNIX, String(unixOf(save)));
      localStorage.setItem(MARK_UPDATED, String(Date.now()));
    } catch(_){}
    lastUploadedUnix = unixOf(save);
  }

  function getMarker(player){
    try {
      const account=String(localStorage.getItem(MARK_ACCOUNT)||'');
      const expected=String(player && (player.account_id || player.username) || '').toLowerCase();
      if(!account || account!==expected) return 0;
      return Number(localStorage.getItem(MARK_UNIX)||0)||0;
    } catch(_){ return 0; }
  }

  function openNamedDb(name, createIfMissing){
    return new Promise((resolve,reject)=>{
      if(!('indexedDB' in window)){ reject(new Error('indexeddb_unavailable')); return; }
      let req;
      try { req=createIfMissing ? indexedDB.open(name,DB_VERSION) : indexedDB.open(name); } catch(e){ reject(e); return; }
      if(createIfMissing){
        req.onupgradeneeded=(event)=>{
          const db=event.target.result;
          const tx=event.target.transaction;
          let store;
          if(db.objectStoreNames.contains(STORE_NAME)) store=tx.objectStore(STORE_NAME);
          else store=db.createObjectStore(STORE_NAME);
          if(!store.indexNames.contains('timestamp')) store.createIndex('timestamp','timestamp',{unique:false});
        };
      }
      req.onsuccess=()=>resolve(req.result);
      req.onerror=()=>reject(req.error || new Error('indexeddb_open_failed'));
    });
  }

  async function detectDbName(){
    if(typeof indexedDB.databases === 'function'){
      try{
        const infos=await indexedDB.databases();
        const names=(infos||[]).map(x=>x&&x.name).filter(Boolean);
        const preferred=[DB_NAME,'userfs','/home/web_user'];
        for(const name of preferred){ if(names.includes(name)) return name; }
        for(const name of names){
          let db=null;
          try{
            db=await openNamedDb(name,false);
            if(!db.objectStoreNames.contains(STORE_NAME)){ db.close(); continue; }
            const keys=await new Promise((resolve,reject)=>{
              const tx=db.transaction([STORE_NAME],'readonly');
              const req=tx.objectStore(STORE_NAME).getAllKeys();
              req.onsuccess=()=>resolve(req.result||[]);
              req.onerror=()=>reject(req.error||new Error('save_keys_failed'));
            });
            if(keys.some(k=>String(k).endsWith('/'+SAVE_BASENAME)||String(k)===SAVE_BASENAME)){ db.close(); return name; }
          }catch(_){ }
          try{db&&db.close();}catch(_){ }
        }
      }catch(_){ }
    }
    return DB_NAME;
  }

  async function openDb(createIfMissing=true){
    const name=await detectDbName();
    return openNamedDb(name,createIfMissing);
  }

  async function findSaveRecord(db, mode){
    return new Promise((resolve,reject)=>{
      let tx,store;
      try { tx=db.transaction([STORE_NAME],mode); store=tx.objectStore(STORE_NAME); } catch(e){ reject(e); return; }
      const direct=store.get(SAVE_KEY);
      direct.onsuccess=()=>{
        if(direct.result){ resolve({key:SAVE_KEY,record:direct.result,store,tx}); return; }
        const keys=store.getAllKeys();
        keys.onsuccess=()=>{
          const match=(keys.result||[]).find(k=>String(k).endsWith('/bud_empire_beta_save.json'));
          if(!match){ resolve({key:SAVE_KEY,record:null,store,tx}); return; }
          const fallback=store.get(match);
          fallback.onsuccess=()=>resolve({key:match,record:fallback.result||null,store,tx});
          fallback.onerror=()=>reject(fallback.error || new Error('save_read_failed'));
        };
        keys.onerror=()=>reject(keys.error || new Error('save_keys_failed'));
      };
      direct.onerror=()=>reject(direct.error || new Error('save_read_failed'));
    });
  }

  function decodeContents(contents){
    if(contents == null) return '';
    let bytes;
    if(contents instanceof Uint8Array) bytes=contents;
    else if(contents instanceof ArrayBuffer) bytes=new Uint8Array(contents);
    else if(ArrayBuffer.isView(contents)) bytes=new Uint8Array(contents.buffer,contents.byteOffset,contents.byteLength);
    else if(Array.isArray(contents)) bytes=new Uint8Array(contents);
    else return '';
    return new TextDecoder('utf-8').decode(bytes);
  }

  async function readLocalSave(){
    let db;
    try {
      db=await openDb();
      const found=await findSaveRecord(db,'readonly');
      if(!found.record) return null;
      const text=decodeContents(found.record.contents);
      if(!text) return null;
      const data=JSON.parse(text);
      return data && typeof data==='object' && !Array.isArray(data) ? data : null;
    } catch(e){
      console.warn('AFB cloud: could not inspect local save:',e);
      return null;
    } finally { try{ db && db.close(); }catch(_){} }
  }

  async function writeLocalSave(save){
    if(!save || typeof save!=='object' || Array.isArray(save)) throw new Error('cloud_save_invalid');
    const text=JSON.stringify(save);
    const bytes=new TextEncoder().encode(text);
    let db=await openDb();
    try {
      await new Promise((resolve,reject)=>{
        const tx=db.transaction([STORE_NAME],'readwrite');
        const store=tx.objectStore(STORE_NAME);
        const stamp=unixOf(save) ? new Date(unixOf(save)*1000) : new Date();
        store.put({timestamp:stamp,mode:FILE_MODE,contents:bytes},SAVE_KEY);
        tx.oncomplete=()=>resolve();
        tx.onerror=()=>reject(tx.error || new Error('cloud_save_write_failed'));
        tx.onabort=()=>reject(tx.error || new Error('cloud_save_write_aborted'));
      });
    } finally { try{db.close();}catch(_){} }
  }

  async function getCloud(player){
    const a=api();
    if(!a || !a.enabled || !player || !player.session_token) return null;
    const raw=await a.rpc('afb_get_save',{p_session_token:player.session_token});
    let data=Array.isArray(raw)?raw[0]:raw;
    if(data && data.value && typeof data.value==='object') data=data.value;
    if(!data || data.exists!==true || !data.save_json || typeof data.save_json!=='object') return null;
    return data.save_json;
  }

  async function putCloud(player,save){
    const a=api();
    if(!a || !a.enabled || !player || !player.session_token) throw new Error('cloud_account_unavailable');
    await a.rpc('afb_set_save',{p_session_token:player.session_token,p_save_json:save});
    setMarker(save,player);
    return true;
  }

  function ensureOverlay(){
    let root=document.getElementById('afb-cloud-overlay');
    if(root) return root;
    root=document.createElement('div');
    root.id='afb-cloud-overlay';
    root.hidden=true;
    root.innerHTML=`<div class="afb-cloud-card" role="dialog" aria-modal="true" aria-labelledby="afb-cloud-title">
      <div class="afb-cloud-logo">AFB</div>
      <h2 id="afb-cloud-title">AFewBuds Cloud Career</h2>
      <p id="afb-cloud-text">Checking your career…</p>
      <div id="afb-cloud-choices" hidden>
        <button type="button" id="afb-cloud-device" class="afb-cloud-choice"><strong>Use this device</strong><span id="afb-cloud-device-summary"></span></button>
        <button type="button" id="afb-cloud-online" class="afb-cloud-choice"><strong>Use cloud career</strong><span id="afb-cloud-online-summary"></span></button>
      </div>
      <p class="afb-cloud-note" id="afb-cloud-note">Your existing save is never deleted during a cloud check.</p>
    </div>`;
    const style=document.createElement('style');
    style.textContent=`
      #afb-cloud-overlay{position:fixed;inset:0;z-index:12000;background:rgba(7,11,10,.94);display:flex;align-items:center;justify-content:center;padding:18px;font-family:system-ui,-apple-system,Segoe UI,sans-serif;color:#eef7ee}
      #afb-cloud-overlay[hidden]{display:none!important}.afb-cloud-card{width:min(560px,100%);background:#111a17;border:1px solid #2b4737;border-radius:24px;padding:24px;box-shadow:0 18px 60px rgba(0,0,0,.45)}
      .afb-cloud-logo{width:56px;height:56px;border-radius:16px;display:grid;place-items:center;background:#1f6f42;color:white;font-weight:900;font-size:22px;margin-bottom:14px}.afb-cloud-card h2{margin:0 0 8px;font-size:24px}.afb-cloud-card p{color:#b9c9bf;line-height:1.45}.afb-cloud-choice{width:100%;min-height:72px;margin-top:12px;border-radius:16px;border:1px solid #355b43;background:#16231d;color:#f4fbf5;text-align:left;padding:14px 16px;font:inherit;cursor:pointer}.afb-cloud-choice strong{display:block;font-size:17px;margin-bottom:4px}.afb-cloud-choice span{display:block;color:#b7cbbd;font-size:13px;line-height:1.35}.afb-cloud-choice:focus{outline:3px solid #61c981;outline-offset:2px}.afb-cloud-note{font-size:12px;margin-bottom:0}
    `;
    document.head.appendChild(style);
    document.body.appendChild(root);
    return root;
  }

  function showStatus(title,text){
    const root=ensureOverlay();
    root.hidden=false;
    document.getElementById('afb-cloud-title').textContent=title;
    document.getElementById('afb-cloud-text').textContent=text||'';
    document.getElementById('afb-cloud-choices').hidden=true;
  }
  function hideStatus(){ const root=document.getElementById('afb-cloud-overlay'); if(root) root.hidden=true; }
  function sleep(ms){ return new Promise(r=>setTimeout(r,ms)); }

  async function chooseConflict(localSave,cloudSave,player){
    const root=ensureOverlay();
    root.hidden=false;
    document.getElementById('afb-cloud-title').textContent='Choose which career to continue';
    document.getElementById('afb-cloud-text').textContent='Both this device and your AFewBuds account have different careers. Nothing will be overwritten until you choose.';
    document.getElementById('afb-cloud-device-summary').textContent=summary(localSave);
    document.getElementById('afb-cloud-online-summary').textContent=summary(cloudSave);
    const choices=document.getElementById('afb-cloud-choices'); choices.hidden=false;
    return new Promise((resolve)=>{
      const device=document.getElementById('afb-cloud-device');
      const online=document.getElementById('afb-cloud-online');
      const cleanup=()=>{device.onclick=null;online.onclick=null;choices.hidden=true;};
      device.onclick=async()=>{
        device.disabled=true;online.disabled=true;
        try{showStatus('Backing up this device…','Saving this career to your AFewBuds account.');await putCloud(player,localSave);await sleep(450);resolve({action:'uploaded',save:localSave});}
        catch(e){console.warn(e);resolve({action:'local_fallback',save:localSave,error:e});}
        finally{cleanup();device.disabled=false;online.disabled=false;hideStatus();}
      };
      online.onclick=async()=>{
        device.disabled=true;online.disabled=true;
        try{showStatus('Restoring cloud career…','Copying your account career onto this device.');await writeLocalSave(cloudSave);setMarker(cloudSave,player);await sleep(450);resolve({action:'restored',save:cloudSave});}
        catch(e){console.warn(e);resolve({action:'local_fallback',save:localSave,error:e});}
        finally{cleanup();device.disabled=false;online.disabled=false;hideStatus();}
      };
    });
  }

  async function prepareBeforeLaunch(){
    const player=session();
    if(!player || !player.session_token) return {action:'guest'};
    if(syncing) return {action:'busy'};
    syncing=true;
    try{
      showStatus('Checking your career…','Comparing this device with your AFewBuds cloud save.');
      const [localSave,cloudSave]=await Promise.all([readLocalSave(),getCloud(player)]);
      if(!localSave && !cloudSave){ hideStatus(); return {action:'none'}; }
      if(localSave && !cloudSave){
        await putCloud(player,localSave);
        showStatus('Career backed up','Your current browser career is now attached to '+(player.username||'your account')+'. You can open the Home Screen app and sign in there to restore it.');
        await sleep(650); hideStatus(); return {action:'uploaded',save:localSave};
      }
      if(!localSave && cloudSave){
        await writeLocalSave(cloudSave); setMarker(cloudSave,player);
        showStatus('Career restored','Your AFewBuds cloud career was copied onto this app before the game started.');
        await sleep(650); hideStatus(); return {action:'restored',save:cloudSave};
      }

      const localUnix=unixOf(localSave), cloudUnix=unixOf(cloudSave), marker=getMarker(player);
      if(localUnix && cloudUnix && localUnix===cloudUnix){ setMarker(localSave,player); hideStatus(); return {action:'same',save:localSave}; }
      if(marker && cloudUnix===marker && localUnix!==marker){
        await putCloud(player,localSave); hideStatus(); return {action:'uploaded',save:localSave};
      }
      if(marker && localUnix===marker && cloudUnix!==marker){
        await writeLocalSave(cloudSave); setMarker(cloudSave,player); hideStatus(); return {action:'restored',save:cloudSave};
      }
      return await chooseConflict(localSave,cloudSave,player);
    } catch(e){
      console.warn('AFB cloud sync skipped:',e);
      showStatus('Cloud check unavailable','Starting the career stored on this device. Your save was not changed.');
      await sleep(850); hideStatus(); return {action:'local_fallback',error:e};
    } finally { syncing=false; }
  }

  async function reconcileLatestSilently(){
    const player=session();
    if(!player || !player.session_token) return {action:'guest'};
    if(syncing) return {action:'busy'};
    syncing=true;
    try{
      const [localSave,cloudSave]=await Promise.all([readLocalSave(),getCloud(player)]);
      if(!localSave && !cloudSave) return {action:'none'};
      if(localSave && !cloudSave){
        await putCloud(player,localSave);
        return {action:'uploaded',save:localSave};
      }
      if(!localSave && cloudSave){
        await writeLocalSave(cloudSave);
        setMarker(cloudSave,player);
        return {action:'restored',save:cloudSave};
      }

      const localUnix=unixOf(localSave);
      const cloudUnix=unixOf(cloudSave);

      if(cloudUnix > localUnix){
        await writeLocalSave(cloudSave);
        setMarker(cloudSave,player);
        return {action:'restored',save:cloudSave};
      }
      if(localUnix > cloudUnix){
        await putCloud(player,localSave);
        return {action:'uploaded',save:localSave};
      }
      if(localUnix > 0 && localUnix === cloudUnix){
        setMarker(localSave,player);
        return {action:'same',save:localSave};
      }

      // If timestamps are unavailable, an existing account cloud save is canonical.
      // This prevents a device-specific local career from silently creating a fork.
      await writeLocalSave(cloudSave);
      setMarker(cloudSave,player);
      return {action:'restored',save:cloudSave};
    } catch(e){
      console.warn('AFB silent career reconcile skipped:',e&&e.message||e);
      return {action:'local_fallback',error:e};
    } finally {
      syncing=false;
    }
  }

  async function syncLatest(){
    const player=session();
    if(!player || !player.session_token || syncing || document.hidden) return;
    syncing=true;
    try{
      const local=await readLocalSave();
      if(!local) return;
      const u=unixOf(local);
      if(u && u===lastUploadedUnix) return;
      const cloud=await getCloud(player);
      const cloudUnix=unixOf(cloud);
      if(cloud && cloudUnix > u){
        window.AFB_CLOUD_STATUS={state:'cloud_newer',saved_unix:cloudUnix,at:Date.now()};
        return;
      }
      await putCloud(player,local);
    } catch(e){ console.warn('AFB cloud autosync:',e && e.message || e); }
    finally{ syncing=false; }
  }

  function normalizeGameSave(payload){
    let save=payload;
    if(typeof save==='string'){
      try{save=JSON.parse(save);}catch(_){throw new Error('game_save_json_invalid');}
    }
    if(!save || typeof save!=='object' || Array.isArray(save)) throw new Error('game_save_invalid');
    return save;
  }

  function pushFromGame(payload){
    const player=session();
    if(!player || !player.session_token) return Promise.resolve({ok:false,reason:'not_signed_in'});
    let save;
    try{save=normalizeGameSave(payload);}catch(error){return Promise.reject(error);}
    // Serialize uploads so rapid local saves cannot arrive out of order. Each queued
    // upload uses the exact JSON Godot just wrote to user://.
    gamePushQueue=gamePushQueue.catch(()=>{}).then(async()=>{
      const incomingUnix=unixOf(save);
      const cloud=await getCloud(player);
      const cloudUnix=unixOf(cloud);
      if(cloud && cloudUnix > incomingUnix){
        window.AFB_CLOUD_STATUS={state:'cloud_newer',saved_unix:cloudUnix,at:Date.now()};
        return {ok:false,reason:'cloud_newer',saved_unix:cloudUnix};
      }
      await putCloud(player,save);
      try{
        window.AFB_CLOUD_STATUS={state:'synced',saved_unix:incomingUnix,at:Date.now()};
        window.dispatchEvent(new CustomEvent('afb-cloud-status',{detail:window.AFB_CLOUD_STATUS}));
      }catch(_){}
      return {ok:true,saved_unix:incomingUnix};
    }).catch((error)=>{
      try{
        window.AFB_CLOUD_STATUS={state:'local_only',error:String(error&&error.message||error),at:Date.now()};
        window.dispatchEvent(new CustomEvent('afb-cloud-status',{detail:window.AFB_CLOUD_STATUS}));
      }catch(_){}
      console.warn('AFB exact-save upload:',error&&error.message||error);
      return {ok:false,error:String(error&&error.message||error)};
    });
    return gamePushQueue;
  }

  function startAutoSync(){
    if(syncTimer) return;
    const player=session();
    if(!player || !player.session_token) return;
    lastUploadedUnix=getMarker(player);
    syncTimer=setInterval(syncLatest,AUTO_SYNC_MS);
    document.addEventListener('visibilitychange',()=>{ if(!document.hidden) syncLatest(); });
    window.addEventListener('pagehide',()=>{ syncLatest(); });
  }

  window.AFB_CLOUD={prepareBeforeLaunch,reconcileLatestSilently,startAutoSync,syncLatest,pushFromGame,readLocalSave,writeLocalSave,summary};
  // Called directly by Godot after _load_game() and every successful _save_game().
  // Keep this global tiny: Godot passes a JSON string and networking stays here.
  window.afbCloudPushSave=function(payload){
    pushFromGame(payload).catch((error)=>console.warn('AFB cloud bridge:',error&&error.message||error));
    return true;
  };
})();
