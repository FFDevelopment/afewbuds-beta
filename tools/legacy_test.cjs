const vm=require('node:vm'),fs=require('node:fs'),assert=require('node:assert/strict');
function element(){return {children:[],appendChild(x){this.children.push(x)},remove(){this.removed=true},style:{}};}
const body=element(),context={window:{},document:{body,createElement:element},localStorage:{},Promise,Number,String,Array,JSON,Error};vm.runInNewContext(fs.readFileSync('shared/afb-legacy-save.js','utf8'),context);
(async()=>{
 const api=context.window.AFB_LEGACY,cloud={cash:100,saved_unix:100};
 const legacy={matches:true,done:false,lastSynced:999,save:{cash:999,saved_unix:200}};
 const choice=api.choose(legacy,cloud);assert.equal(body.children.length,1,'unreliable old upload marker cannot suppress recovery');
 const card=body.children[0].children[0];card.children[3].onclick();assert.equal((await choice).cash,999);
 assert.equal(await api.choose({...legacy,matches:false},cloud),null);
 assert.equal(await api.choose({...legacy,done:true},cloud),null);
 assert.equal(await api.choose(legacy,{cash:555,saved_unix:300}),null);
 console.log('LEGACY_SAVE_TEST_RESULT: PASS (rejected legacy upload marker, explicit recovery, account ownership, completed migration, newer cloud)');
})().catch(e=>{console.error(e);process.exitCode=1});
