const assert=require('node:assert/strict'),fs=require('node:fs');
assert(fs.existsSync(__dirname+'/Layout.js'),'shared layout is not implemented');
const L=require('./Layout.js'),S=require('./State.js');
for(const [w,h] of [[1536,829],[829,1536],[480,800],[320,240],[24,24]]) {
 const p=L.panelSize(w,h);
 assert(p.width>0&&p.width<=w,'panel stays inside screen width');
 assert(p.height>0&&p.height<=h,'panel stays inside screen height');
 assert.deepEqual(p,L.panelSize(w,h),'page contents cannot change geometry');
}
for(const bad of [NaN,Infinity,-1,undefined]) {
 const p=L.panelSize(bad,bad);assert(Number.isFinite(p.width)&&p.width>0);assert(Number.isFinite(p.height)&&p.height>0);
}
assert.equal(S.fieldState(undefined,100).known,false);
assert.equal(S.fieldState({available:false},100).known,false);
for(const field of [
 {available:true,actual:false},
 {available:true,actual:false,observed_at:100},
 {available:true,actual:false,observed_at:20,stale_after:45},
 {available:true,actual:false,observed_at:110,stale_after:45},
 {available:true,actual:false,observed_at:100,stale_after:-1},
 {available:true,actual:false,observed_at:NaN,stale_after:45}])assert.equal(S.fieldState(field,100).known,false,'invalid or stale time must not appear off');
assert.deepEqual(S.fieldState({available:true,actual:false,observed_at:100,stale_after:45},100),{known:true,value:false,label:'关闭'});
assert.equal(S.fieldState({available:true,actual:0,observed_at:100,stale_after:45},100).value,0);
assert.equal(S.fieldState({available:true,actual:true,observed_at:100,stale_after:45},100).label,'运行');
assert.equal(S.fieldState({available:true,actual:null,observed_at:100,stale_after:45},100).known,false);
assert.equal(S.freshSnapshot({},100,30),false);
assert.equal(S.freshSnapshot({observed_at:99},100,30),true);
assert.equal(S.freshSnapshot({observed_at:1},100,30),false);
console.log('shared geometry and unknown/fresh/stale state checks passed');
