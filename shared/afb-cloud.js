(function () {
 'use strict';
 const PREFIX='afb_public_career_v1:';
 const player=()=>window.AFB_API?.getPlayerSession?.() || null;
 const key=()=>PREFIX+(player()?.account_id || 'guest');
 const normalize=d=>Array.isArray(d)?normalize(d[0]):(d?.value && typeof d.value==='object'?d.value:d);
 const clone=d=>JSON.parse(JSON.stringify(d));
 let lastReported=0;
 let updating=false,updateSerial=0;
 let activeKey=null, account=null, playId=null, revision=0, queue=Promise.resolve(), timer=null, stopped=false, handingOff=false, lastContact=Date.now(), heartbeatBusy=false, pending=null;
 const read=()=>{try{return JSON.parse(localStorage.getItem(key())||'null');}catch(_){return null;}};
 const summary=s=>s?`Day ${s.game_day||1} · $${s.cash||0}`:'New career';
 function event(state){window.AFB_CLOUD_EVENT=state;window.AFB_CLOUD_STATUS={state,at:Date.now()};}
 function sameAccount(){return activeKey===key() && (account?.session_token||null)===(player()?.session_token||null);}
 async function rpc(name,args){
  const result=normalize(await window.AFB_API.rpc(name,args));
  if(result?.error)throw Error(result.error);
  return result;
 }
 function args(){return {p_session_token:account.session_token,p_play_id:playId};}
 // Browser tabs share login storage. Fence this play session without logging out the new tab.
 function replaced(){stopped=true;event('replaced');}
 async function reconcileLatestSilently(){
  account=player();activeKey=key();stopped=false;handingOff=false;pending=null;
  let cached=read(),save={};
  const legacy=window.AFB_LEGACY?await window.AFB_LEGACY.prepare(account):null;
  if(account?.session_token){
   playId=crypto.randomUUID();
   for(let attempt=0;attempt<45;attempt++){
    const r=await rpc('afb_begin_play',args());
    if(!sameAccount())throw Error('Account changed. Sign in again.');
    if(r.state==='active'){
     revision=Number(r.revision);save=r.save_json||{};
     if(Number(save.save_schema||0)>2)throw Error('This career needs a newer game version.');
     if(legacy && !legacy.done && !cached?.dirty){
      const recovered=await window.AFB_LEGACY.choose(legacy,save);
      if(!sameAccount())throw Error('Account changed. Sign in again.');
      const verified=await rpc('afb_play_heartbeat',args());
      if(verified.state!=='active')throw Error('Your account opened on another device. Sign in again.');
      if(recovered){
       const result=await rpc('afb_save_career',{...args(),p_revision:revision,p_save_json:recovered});
       if(!result.ok)throw Error(result.reason||'Could not restore device progress.');
       revision=Number(result.revision);save=recovered;
      }
      localStorage.setItem(legacy.doneKey,'1');
     }
     if(cached?.dirty){
      localStorage.setItem(activeKey+':backup',JSON.stringify(cached));
      if(Number(cached.revision)===revision){save=cached.save;pending=clone(save);}
     }
     localStorage.setItem(activeKey,JSON.stringify({save,revision,dirty:!!pending}));
     window.AFB_CLOUD_BOOT_SAVE=JSON.stringify(save);lastContact=Date.now();event('active');
     return {action:'cloud',save};
    }
    if(r.state!=='waiting')throw Error('Could not open the shared career.');
    if(window.afbMessage)window.afbMessage('afb-login-msg','Closing the other play session and loading its latest save…');
    await new Promise(resolve=>setTimeout(resolve,500));
   }
   throw Error('Another device switch is still finishing. Please try again.');
  }
  save=cached?.save||((legacy && !legacy.owner)?legacy.save:{});if(!cached)localStorage.setItem(activeKey,JSON.stringify({save,revision:0,dirty:false}));window.AFB_CLOUD_BOOT_SAVE=JSON.stringify(save);event('guest');return {action:'guest',save};
 }
 function pushFromGame(payload){
  if(!sameAccount() || stopped)return Promise.reject(Error('session_replaced'));
  const save=typeof payload==='string'?JSON.parse(payload):clone(payload);
  if(!save || typeof save!=='object' || Array.isArray(save))return Promise.reject(Error('save_invalid'));
  localStorage.setItem(activeKey,JSON.stringify({save,revision,dirty:!!account?.session_token}));
  if(!account?.session_token)return Promise.resolve({ok:true,guest:true});
  pending=save;
  const expectedKey=activeKey,expectedPlay=playId;
  queue=queue.catch(()=>{}).then(async()=>{
   if(stopped || !sameAccount() || expectedKey!==activeKey || expectedPlay!==playId)throw Error('session_replaced');
   const r=await rpc('afb_save_career',{...args(),p_revision:revision,p_save_json:save});
   if(!r?.ok){
    if(['session_replaced','session_invalid','save_conflict'].includes(r?.reason))replaced();
    throw Error(r?.reason||'Cloud save was rejected.');
   }
   revision=Number(r.revision);lastContact=Date.now();
   if(pending===save){pending=null;localStorage.setItem(activeKey,JSON.stringify({save,revision,dirty:false}));}
   else {const current=JSON.parse(localStorage.getItem(activeKey));current.revision=revision;localStorage.setItem(activeKey,JSON.stringify(current));}
   window.AFB_CLOUD_STATUS={state:'synced',at:Date.now()};
   if(Date.now()-lastReported>30000){lastReported=Date.now();rpc('afb_leaderboard_report',{p_session_token:account.session_token}).catch(()=>{});}
   return {ok:true,revision};
  });
  return queue;
 }
 async function heartbeat(){
  if(heartbeatBusy || stopped || handingOff || !account?.session_token)return;
  heartbeatBusy=true;
  try{
   if(!sameAccount()){replaced();return;}
   const r=await rpc('afb_play_heartbeat',args());lastContact=Date.now();
   if(r.state==='handoff'){handingOff=true;event('handoff');}
   else if(r.state==='active'){if(window.AFB_CLOUD_EVENT==='offline'){event('active');if(pending)syncLatest().catch(()=>{});}}
   else replaced();
  }catch(e){if(Date.now()-lastContact>12000)event('offline');}
  finally{heartbeatBusy=false;}
 }
 async function syncLatest(){if(pending && !stopped && !handingOff)return pushFromGame(pending);}
 async function finishHandoff(){
  if(updating){
   try{await queue;if(Number(window.AFB_SAVE_SERIAL||0)<=updateSerial || window.AFB_QUIT_SAVE_STATE!=='saved')throw Error('Latest save is not confirmed.');await releasePlay();window.location.replace('./index.html?afb_update='+Date.now());}
   catch(error){updating=false;handingOff=false;event('offline');window.AFB_UPDATER?.updateSaveFailed?.(error);}
   return;
  }
  try{await queue; if(account?.session_token && sameAccount())await rpc('afb_release_play',args());}
  finally{replaced();}
 }
 async function releasePlay(){
  await queue;
  if(pending)throw Error('Cloud save is still pending.');
  if(account?.session_token){const r=await rpc('afb_release_play',args());if(!r.ok)throw Error('Could not close play session.');}
  stopped=true;return {ok:true};
 }
 function requestUpdate(){
  if(stopped){window.location.replace('./index.html?afb_update='+Date.now());return;}
  if(updating)return;
  updateSerial=Number(window.AFB_SAVE_SERIAL||0);updating=true;handingOff=true;event('handoff');
 }
 function startAutoSync(){
  if(timer)clearInterval(timer);
  timer=setInterval(()=>{
   if(account?.session_token && !stopped && !handingOff && Date.now()-lastContact>15000)event('offline');
   heartbeat();
  },5000);
  if(pending)syncLatest().catch(()=>{});
 }
 window.AFB_CLOUD={reconcileLatestSilently,prepareBeforeLaunch:reconcileLatestSilently,startAutoSync,syncLatest,pushFromGame,finishHandoff,releasePlay,heartbeat,requestUpdate,
  readLocalSave:async()=>read()?.save||null,writeLocalSave:pushFromGame,summary};
})();
