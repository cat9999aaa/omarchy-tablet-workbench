const assert=require('node:assert/strict'),fs=require('node:fs');
assert(fs.existsSync(__dirname+'/NavigationSession.js'),'navigation session reducer missing');
const {initial,reduce}=require('./NavigationSession.js');
const snapshot={ok:true,output:'TEST-1',target:{address:'0xab',pid:12},bindings:{P1:'keyboard'}};
const ev=(type,more={})=>({type,...more});
function send(s,e){const before=JSON.stringify(s),input=JSON.stringify(e),r=reduce(s,e);assert.equal(JSON.stringify(s),before);assert.equal(JSON.stringify(e),input);return r;}
function opened(){let s=send(initial(),ev('OPEN',{page:'开始'})).state;return send(s,ev('READ_OK',{generation:s.generation,data:snapshot})).state;}
let a=send(initial(),ev('OPEN',{page:'开始'}));assert.equal(a.state.phase,'loading');assert.deepEqual(a.effects,[{type:'read',generation:1,page:'开始'}]);
let closed=send(a.state,ev('CLOSE'));assert.equal(closed.state.phase,'closed');assert(closed.effects.some(x=>x.type==='cancel-read'));
assert.deepEqual(send(closed.state,ev('READ_OK',{generation:1,data:snapshot})).state,closed.state);
let b=send(a.state,ev('OPEN',{page:'桌面'}));assert.equal(b.state.generation,2);assert.equal(b.effects[0].type,'cancel-read');
assert.deepEqual(send(b.state,ev('READ_OK',{generation:1,data:snapshot})).state,b.state);
let ready=send(b.state,ev('READ_OK',{generation:2,data:snapshot})).state;assert.equal(ready.phase,'open');assert.equal(ready.page,'桌面');
assert.deepEqual(send(ready,ev('OPEN',{page:'invalid'})),{state:ready,effects:[]});
let acting=send(ready,ev('ACT_STARTED',{generation:2,id:'one'})).state;assert.equal(acting.phase,'acting');
assert.deepEqual(send(acting,ev('ACT_STARTED',{generation:2,id:'two'})),{state:acting,effects:[]});
let error=send(acting,ev('ACT_RESULT',{generation:2,id:'one',result:{ok:false,reason:'目标已变化'}})).state;
assert.equal(error.phase,'open');assert.equal(error.feedback,'目标已变化');
assert.deepEqual(send(error,ev('READ_ERROR',{generation:1,code:'timeout'})).state,error);
let canceled=send(acting,ev('CLOSE'));assert(!canceled.effects.some(x=>/action/.test(x.type)));
let newer=send(acting,ev('OPEN',{page:'窗口'}));assert.equal(newer.state.phase,'loading');assert.deepEqual(newer.effects,[{type:'read',generation:3,page:'窗口'}]);
for(const result of [{ok:true},{ok:false,reason:'old'}])assert.deepEqual(send(newer.state,ev('ACT_RESULT',{generation:2,id:'one',result})).state,newer.state);
assert.deepEqual(send(acting,ev('ACT_RESULT',{generation:2,id:'wrong',result:{ok:true}})).state,acting);
let saved=send(acting,ev('ACT_RESULT',{generation:2,id:'one',result:{ok:true,bindings:{P1:'voice'}}}));assert.equal(saved.state.phase,'open');assert.equal(saved.state.data.bindings.P1,'voice');assert.equal(acting.data.bindings.P1,'keyboard');
let success=send(acting,ev('ACT_RESULT',{generation:2,id:'one',result:{ok:true}}));assert.equal(success.state.phase,'closed');assert(success.effects.some(x=>x.type==='close'));
for(const type of ['LOCKED','OUTPUT_LOST']){let r=send(opened(),ev(type));assert.equal(r.state.phase,'closed');assert.equal(r.state.output,null);assert.equal(r.state.data,null);}
let invalid=send(a.state,ev('READ_OK',{generation:1,data:{ok:true}}));assert.equal(invalid.state.phase,'closed');assert.equal(invalid.state.feedback,'invalid-data');
console.log('navigation session lifecycle cases passed');

// A preparation failure must stay readable without exposing actions or window data.
let pending=send(initial(),ev('OPEN',{page:'窗口'})).state;
let failed=send(pending,ev('READ_ERROR',{generation:pending.generation,code:'timeout',output:'TEST-1'})).state;
assert.equal(failed.phase,'error');assert.equal(failed.output,'TEST-1');assert.equal(failed.data,null);
assert.match(failed.feedback,/超时/);
assert.deepEqual(send(failed,ev('ACT_STARTED',{generation:failed.generation,id:'unsafe'})).state,failed);
assert.equal(send(failed,ev('OPEN',{page:'窗口'})).state.phase,'loading');
for(const code of ['locked','lock-unknown','output-unavailable','unexpected'])
 assert.equal(send(pending,ev('READ_ERROR',{generation:pending.generation,code,output:'TEST-1'})).state.phase,'closed');
for(const type of ['LOCKED','OUTPUT_LOST','CLOSE'])assert.equal(send(failed,ev(type)).state.phase,'closed');
assert.equal(send(pending,ev('READ_ERROR',{generation:pending.generation,code:'timeout'})).state.phase,'closed');

const layoutSaved=send(acting,ev('ACT_RESULT',{generation:2,id:'one',result:{ok:true,touch_layout:{profile:'touch',health:'ready',reason:''}}}));assert.equal(layoutSaved.state.phase,'open');assert.equal(layoutSaved.state.data.touch_layout.profile,'touch');assert.equal(acting.data.touch_layout,undefined);
