const assert = require('node:assert/strict');
const {pickTarget} = require('./OutputRoute.js');
const a = {id:'a',screenName:'ONE',attached:true,visibleSlot:true};
const b = {id:'b',screenName:'TWO',attached:true,visibleSlot:true};
for (const value of [null,undefined,{},'bad',[]]) assert.equal(pickTarget(value,'ONE'),null);
assert.equal(pickTarget([a,b],''),null);
assert.equal(pickTarget([a,b],'TWO'),'b');
assert.equal(pickTarget([b,a],'TWO'),'b');
assert.equal(pickTarget([a,b],'ABSENT'),null);
assert.equal(pickTarget([a,{...a,id:'duplicate'}],'ONE'),null);
assert.equal(pickTarget([a,{...a,id:'placeholder',visibleSlot:false}],'ONE'),'a');
assert.equal(pickTarget([{...a,attached:false}],'ONE'),null);
for(const field of ['id','screenName','attached','visibleSlot']) {
 const broken={...a}; delete broken[field]; assert.equal(pickTarget([broken],'ONE'),null);
}
for(const id of [null,{},true,0,'']) assert.equal(pickTarget([{...a,id}],'ONE'),null);
for(const key of ['attached','visibleSlot']) for(const value of [1,'true',null]) assert.equal(pickTarget([{...a,[key]:value}],'ONE'),null);
console.log('strict output selection passed');
const R=require('./OutputRoute.js');
let opened=[], callbacks=[];
function peer(id){return {id,routeEpoch:0,transferPending:false,closeForTransfer(cb){callbacks.push(cb)},requestOpen(){opened.push(id)}}}
const first=peer('first'),second=peer('second'),peers=[first,second];
assert(R.handoff(peers,second,()=>true));assert.deepEqual(opened,[]);
callbacks.shift()();assert.deepEqual(opened,[]);callbacks.shift()();assert.deepEqual(opened,['second']);
opened=[];R.handoff(peers,first,()=>true);const old=callbacks.splice(0);R.handoff(peers,second,()=>true);
old.forEach(f=>f());assert.deepEqual(opened,[]);callbacks.splice(0).forEach(f=>f());assert.deepEqual(opened,['second']);
opened=[];R.handoff(peers,first,()=>false);callbacks.splice(0).forEach(f=>f());assert.deepEqual(opened,[]);
console.log('handoff waits for all old owners and invalidates stale transfers');

assert.equal(first.transferPending,false,'invalid target must release transfer flag');
