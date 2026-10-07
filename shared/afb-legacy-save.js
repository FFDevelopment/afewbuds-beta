/* Read-only migration from the public beta's original Godot save. Never deletes IndexedDB. */
(function(){
 'use strict';
 const normalize=s=>String(s||'').toLowerCase();
 const unix=s=>Number(s?.saved_unix||0);
 async function readExisting(){
  if(!window.indexedDB)return null;
  let names=['/userfs','userfs','/home/web_user'];
  if(indexedDB.databases){const databases=await indexedDB.databases();names=databases.map(x=>x.name).filter(Boolean);}
  for(const name of names){
   const db=await new Promise((resolve,reject)=>{const req=indexedDB.open(name);req.onupgradeneeded=()=>req.transaction.abort();req.onsuccess=()=>resolve(req.result);req.onerror=()=>resolve(null);req.onblocked=()=>reject(Error('Close the other AFewBuds tab and try again.'));});
   if(!db)continue;
   try{
    if(!db.objectStoreNames.contains('FILE_DATA'))continue;
    const record=await new Promise((resolve,reject)=>{const tx=db.transaction('FILE_DATA','readonly');const store=tx.objectStore('FILE_DATA');const req=store.openCursor();req.onerror=()=>reject(req.error);req.onsuccess=()=>{const c=req.result;if(!c)return resolve(null);if(String(c.key).endsWith('/bud_empire_beta_save.json')||c.key==='bud_empire_beta_save.json')return resolve(c.value);c.continue();};});
    if(record?.contents){const data=record.contents;const bytes=ArrayBuffer.isView(data)?new Uint8Array(data.buffer,data.byteOffset,data.byteLength):new Uint8Array(data);const save=JSON.parse(new TextDecoder().decode(bytes));if(save && typeof save==='object' && !Array.isArray(save))return save;}
   }finally{db.close();}
  }
  return null;
 }
 async function prepare(account){
  const save=await readExisting();if(!save)return null;
  const owner=normalize(localStorage.getItem('afb_cloud_account'));
  const snapshot={save,owner,lastSynced:Number(localStorage.getItem('afb_cloud_last_sync_unix')||0)};
  const backupKey='afb_legacy_backup_v1:'+(owner||'guest');
  const previous=JSON.parse(localStorage.getItem(backupKey)||'null');
  if(!previous || unix(save)>unix(previous.save))localStorage.setItem(backupKey,JSON.stringify(snapshot));
  snapshot.matches=!!account && !!owner && [normalize(account.account_id),normalize(account.username)].includes(owner);
  snapshot.doneKey='afb_public_migration_v1:'+(account?.account_id||'guest');
  snapshot.done=!!localStorage.getItem(snapshot.doneKey);
  return snapshot;
 }
 function choose(snapshot,cloud){
  if(!snapshot?.matches || snapshot.done || unix(snapshot.save)<=snapshot.lastSynced || (cloud && Object.keys(cloud).length && unix(snapshot.save)<=unix(cloud)))return Promise.resolve(null);
  return new Promise(resolve=>{
   const overlay=document.createElement('div');overlay.id='afb-career-choice';overlay.style.cssText='position:fixed;inset:0;z-index:13000;background:#08120ff5;display:grid;place-items:center;padding:20px;color:#f4f0df;font-family:system-ui;overflow:auto';
   const card=document.createElement('div');card.style.cssText='max-width:480px;background:#17251f;padding:24px;border:1px solid #689c50;border-radius:18px';overlay.appendChild(card);
   const title=document.createElement('h2');title.textContent='Choose your latest progress';card.appendChild(title);
   const text=document.createElement('p');text.textContent='This device has progress that may not have reached your account. Both versions are backed up. Restoring this device will replace the current cloud career.';card.appendChild(text);
   for(const [label,save,value] of [['Continue cloud career',cloud,null],['Restore this device’s progress',snapshot.save,snapshot.save]]){
    const button=document.createElement('button');button.style.cssText='display:block;width:100%;min-height:64px;margin-top:14px;background:#438d31;color:white;border:0;border-radius:10px;padding:12px;font:inherit';button.textContent=label+' — Day '+(save?.game_day||1)+' · $'+(save?.cash||0);button.onclick=()=>{overlay.remove();resolve(value);};card.appendChild(button);
   }
   document.body.appendChild(overlay);
  });
 }
 window.AFB_LEGACY={prepare,choose,readExisting};
})();
