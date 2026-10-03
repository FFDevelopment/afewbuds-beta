(function(){
  if(!window.AFB_API || !AFB_API.enabled) return;
  const player=AFB_API.getPlayerSession();
  const device=AFB_API.deviceId();
  let playId=null,last=Date.now(),timer=null;
  const token=player && player.session_token || null;
  async function open(){try{const r=await AFB_API.rpc('afb_open_session',{p_session_token:token,p_device_id:device,p_build_version:AFB_API.cfg.gameBuild||''});playId=r.play_session_id;last=Date.now();timer=setInterval(ping,60000)}catch(e){console.warn('AFB telemetry disabled:',e.message)}}
  async function ping(){if(!playId||document.hidden)return;const now=Date.now();const seconds=Math.max(0,Math.min(180,Math.round((now-last)/1000)));last=now;if(!seconds)return;try{await AFB_API.rpc('afb_heartbeat',{p_play_session_id:playId,p_session_token:token,p_device_id:device,p_seconds:seconds})}catch(e){console.warn('AFB heartbeat:',e.message)}}
  function end(){if(!playId)return;try{navigator.sendBeacon&&navigator.sendBeacon('about:blank',new Blob([]))}catch(_){} AFB_API.rpc('afb_end_session',{p_play_session_id:playId,p_session_token:token,p_device_id:device}).catch(()=>{})}
  document.addEventListener('visibilitychange',()=>{if(document.hidden)ping();else last=Date.now()});window.addEventListener('pagehide',end);open();
}());
