const assert=require('node:assert/strict'), M=require('./ControlModel.js');
for(const [w,h] of [[500,800],[1536,829],[500,600]]) {
 const l=M.layout(w,h);assert(l.width<=Math.min(760,w));assert(l.height<=h*.7);assert(l.tileHeight>=64);assert(l.gap>=8);
}
assert.equal(M.displayField({available:false,actual:null},100),'不可用');
assert.equal(M.displayField({available:true,actual:null,observed_at:100,stale_after:45},100),'未知');
assert.equal(M.displayField({available:true,actual:1,observed_at:1,stale_after:45},100),'待读取');
assert.equal(M.canOpen(false,true),true);assert.equal(M.canOpen(null,true),false);assert.equal(M.canOpen(false,false),false);
assert.equal(M.commitSlider(20.8),21);assert.equal(M.commitSlider(NaN),null);
console.log('layout/state/input guards passed');
assert.deepEqual(M.booleanState({available:true,actual:true,observed_at:1,stale_after:45},100),{known:false,label:"待读取",value:null});
assert.equal(M.booleanState({available:true,actual:false,observed_at:100,stale_after:45},100).value,false);

assert.equal(M.flightView({flight_saved:true,flight_active:true,flight_observed_at:99},100).verified,true);
assert.equal(M.flightView({flight_saved:true,flight_active:true,flight_observed_at:10},100).verified,false);
assert.equal(M.flightView({flight_saved:true,flight_active:false,flight_observed_at:99},100).entertainment,true);
