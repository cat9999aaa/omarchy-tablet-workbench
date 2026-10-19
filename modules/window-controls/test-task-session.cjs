const assert=require('node:assert/strict'),fs=require('node:fs');
assert(fs.existsSync(__dirname+'/TaskSession.js'),'task session missing');
const T=require('./TaskSession.js');
const id=n=>'00000000-0000-4000-8000-'+String(n).padStart(12,'0');
const rows=Array.from({length:21},(_,i)=>({agent_id:id(i),status:i===0?'idle':'running'}));
let s=T.initial();function send(e){const old=JSON.stringify(s);const r=T.reduce(s,e);assert.equal(JSON.stringify(s),old);s=r.state;return r.effects;}
function result(value){return send({type:'RESULT',generation:s.generation,requestId:s.pending.id,value});}
function snapshot(){return {schema:1,ok:true,output:'TEST',rows,source_reason:'',dnd:false,elapsed_ms:100,sampled_boottime_ms:1000,observed_at:'2026-01-01T00:00:00Z'};}
send({type:'OPEN',output:'TEST'});let generation=s.generation,requestId=s.pending.id;send({type:'CLOSE'});send({type:'RESULT',generation,requestId,value:snapshot()});assert.equal(s.phase,'closed');
send({type:'OPEN',output:'TEST'});result(snapshot());assert.equal(s.rows.length,20);assert(s.truncated);assert.equal(s.remainingMs,4900);assert(s.rows.every(r=>r.pending_permission_count===null));assert(!s.rows.some(r=>r.kind==='done'));
const key=s.rows[0].agent_id,ordinal=s.rows[0].ordinal;
send({type:'DETAIL',agent_id:key});assert.equal(send({type:'DETAIL',agent_id:key}).length,0);result({schema:1,ok:true,output:'TEST',agent_id:key,detail:{status:'idle',pending_permission_count:2,source_updated_at:null},elapsed_ms:200,sampled_boottime_ms:1200,observed_at:'2026-01-01T00:00:01Z'});assert.equal(s.rows.find(r=>r.agent_id===key).kind,'needs_permission');assert.equal(s.remainingMs,4700);
send({type:'TICK',now:16200});assert.equal(s.rows.find(r=>r.agent_id===key).stale,false);send({type:'TICK',now:16201});assert.equal(s.rows.find(r=>r.agent_id===key).stale,true);
send({type:'REFRESH'});result(snapshot());assert.equal(s.rows.find(r=>r.agent_id===key).ordinal,ordinal);assert.equal(s.rows.find(r=>r.agent_id===key).pending_permission_count,null);
for(let n=0;n<5;n++){const agent_id=s.rows[n].agent_id;send({type:'DETAIL',agent_id});result({schema:1,ok:false,reason_code:'read-failed',elapsed_ms:100});}
assert.equal(send({type:'DETAIL',agent_id:s.rows[6].agent_id}).length,0);
send({type:'REFRESH'});result({...snapshot(),elapsed_ms:-1});assert.equal(s.phase,'closed');
send({type:'OPEN',output:'TEST'});result({...snapshot(),output:'OTHER'});assert.equal(s.phase,'closed');
send({type:'OPEN',output:'TEST'});result({...snapshot(),rows:null,source_reason:'read-failed'});assert.equal(s.phase,'open');assert.equal(s.rows.length,0);assert.equal(s.sourceReason,'read-failed');
for(const type of ['LOCKED','OUTPUT_LOST']){send({type:'OPEN',output:'TEST'});send({type});assert.equal(s.phase,'closed');}
console.log('task session boundaries passed');

send({type:'OPEN',output:'TEST'});result(snapshot());send({type:'TICK',now:16001});assert.equal(s.stale,true);
send({type:'REFRESH'});result({...snapshot(),observed_at:'bad'});assert.equal(s.phase,'closed');
