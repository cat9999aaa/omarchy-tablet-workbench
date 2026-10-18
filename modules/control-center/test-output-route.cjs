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
