const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),{webcrypto}=require('node:crypto');
async function test(failHash=false){
 const files={'index.html':'new release','game.pck':'fixture pack'};
 const hashes=Object.fromEntries(await Promise.all(Object.entries(files).map(async([k,v])=>[k,Buffer.from(await webcrypto.subtle.digest('SHA-256',Buffer.from(v))).toString('hex')])));
 const manifest={release_id:'qa-new',game_build:'qa-new',files:Object.entries(files).map(([path,v])=>({path,size:Buffer.byteLength(v),sha256:failHash?'0'.repeat(64):hashes[path]}))};
 const cachesData=new Map([['AFB-Release-v1-qa-old',new Map([['index.html','old release']])]]);const meta={active_release:'qa-old',active_cache:'AFB-Release-v1-qa-old',pending:false};const calls=[];let updateRequests=0;
 const worker={postMessage(p,ports){calls.push(p.type);if(p.type==='AFB_ACTIVATE_RELEASE'){meta.previous_cache=meta.active_cache;meta.active_cache=p.cache_name;meta.active_release=p.release_id;meta.pending=true;}if(p.type==='AFB_LAUNCHER_OK')meta.launcher_ok=true;if(p.type==='AFB_CONFIRM_RELEASE')meta.pending=false;setImmediate(()=>ports[0].peer.onmessage({data:{ok:true,meta:{...meta}}}));}};
 class Channel{constructor(){this.port1={};this.port2={peer:this.port1};}}
 const context={window:null,crypto:webcrypto,URL,Headers,Response,Request,MessageChannel:Channel,console,Date,Promise,Uint8Array,Number,String,Error,Math,JSON,Set,
 document:{hidden:false,getElementById:()=>null,addEventListener:()=>{}},location:{href:'https://example.test/mobile/index.html',replace:()=>{}},
 navigator:{serviceWorker:{register:async()=>({active:worker,update:async()=>{}}),ready:Promise.resolve({active:worker}),controller:worker}},
 caches:{keys:async()=>[...cachesData.keys()],delete:async k=>cachesData.delete(k),open:async k=>{if(!cachesData.has(k))cachesData.set(k,new Map());return {put:async(u,v)=>cachesData.get(k).set(u,v)};}},
 setTimeout:(f,ms)=>ms>2000?0:setImmediate(f),clearTimeout:()=>{},fetch:async url=>String(url).startsWith('version.json')?new Response(JSON.stringify(manifest)):new Response(files[String(url).split('?')[0]])};
 context.window=context;context.addEventListener=()=>{};vm.runInNewContext(fs.readFileSync('shared/afb-updater.js','utf8'),context);
 const boot=context.AFB_UPDATER.boot();await new Promise(r=>setTimeout(r,80));
 assert.equal(cachesData.has('AFB-Release-v1-qa-old'),true);
 if(failHash){await boot;assert.equal(cachesData.has('AFB-Release-v1-qa-new'),false);assert.equal(meta.active_release,'qa-old');assert.equal(calls.includes('AFB_ACTIVATE_RELEASE'),false);}
 else{assert.equal(cachesData.get('AFB-Release-v1-qa-new').size,2);assert.equal(meta.active_release,'qa-new');assert.equal(meta.previous_cache,'AFB-Release-v1-qa-old');assert.equal(meta.pending,true);context.AFB_INSTALLED_RELEASE='qa-old';context.AFB_GAME_RUNNING=true;context.AFB_CLOUD={requestUpdate:()=>updateRequests++};await context.AFB_UPDATER.checkOnResume();assert.equal(updateRequests,1);context.document.hidden=true;await context.AFB_UPDATER.checkOnResume();assert.equal(updateRequests,1);}
}
(async()=>{await test();await test(true);console.log('UPDATER_TEST_RESULT: PASS (all files verified before activation, corrupt update discarded, previous release retained, visible-app resume requests safe save)');})().catch(e=>{console.error(e);process.exitCode=1});
