const assert=require('node:assert/strict'), M=require('./ContractModel.js');
function envelope(kind,actual=0,health='observed') {
 const temperature=kind==='temperature';
 return {contract_version:'0.1.0',capability_id:'dashen.device.'+(temperature?'temperature':'touch-mode'),resource_id:temperature?'thermal-summary':'touch-mode',output_id:'local',read_permission:temperature?'device.temperature.read':'device.touch-mode.read',state:{available:true,actual,health,boot_default:1}};
}
function response(){return {schema_version:1,legacy:{locked:false},contracts:{version:'0.1.0',status:'ok',states:[envelope('temperature'),envelope('touch')]}}}
assert.equal(M.reading(envelope('temperature'),'dashen.device.temperature').label,'0 °C');
for(const health of ['unknown','error','stale','unavailable',undefined]){
 const e=envelope('temperature',42);e.state.health=health;const r=M.reading(e,'dashen.device.temperature');assert.equal(r.known,false);assert(!r.label.includes('°C'));
}
for(const actual of [true,false,NaN,Infinity,-21,151,'42',null])assert.equal(M.reading(envelope('temperature',actual),'dashen.device.temperature').known,false);
for(const [value,label] of [[0,'普通触摸'],[1,'手套／原装笔'],[2,'笔模式']])assert.equal(M.reading(envelope('touch',value),'dashen.device.touch-mode').label,label);
assert.equal(M.reading(envelope('touch',true),'dashen.device.touch-mode').known,false);
assert.equal(M.reading(envelope('touch',0,'unknown'),'dashen.device.touch-mode').bootDefaultLabel,'手套／原装笔');
for(const [key,value] of [['contract_version','0.2.0'],['capability_id','wrong'],['resource_id','wrong'],['output_id','remote'],['read_permission','admin']]){
 const e=envelope('temperature');e[key]=value;assert.equal(M.reading(e,'dashen.device.temperature').known,false);
 delete e[key];assert.equal(M.reading(e,'dashen.device.temperature').known,false);
}
for(const value of [1,'true',null]){const e=envelope('temperature');e.state.available=value;assert(!M.reading(e,e.capability_id).known)}
assert.equal(M.snapshot(response()).valid,true);
for(const states of [[],[envelope('temperature')],[envelope('temperature'),envelope('temperature')],[envelope('temperature'),envelope('touch'),envelope('touch')]]){
 const r=response();r.contracts.states=states;assert.equal(M.snapshot(r).valid,false);
}
const huge=response();huge.legacy.extra='中'.repeat(24000);assert.equal(M.snapshot(huge).valid,false);
assert.equal(M.parse('{').valid,false);assert.equal(M.parse(JSON.stringify(response())).valid,true);
console.log('contract identity, known-only units, zero/default and bounded input passed');
// Missing/invalid source timestamps must never be replaced with receipt time.
for(const kind of ['temperature','touch']) {
 const e=envelope(kind,0);e.state.observed_at=100;
 const r=M.reading(e,e.capability_id);
 assert.equal(r.known,true);assert.equal(r.value,0);assert.equal(r.observedAt,100);assert.equal(r.health,'observed');
 for(const stamp of [undefined,null,true,-1,NaN,Infinity,8640000000001]) {
  e.state.observed_at=stamp;const v=M.reading(e,e.capability_id);
  assert.equal(v.observedAt,null);assert.equal(v.known,true);
 }
 e.output_id='remote';assert.equal(M.reading(e,e.capability_id).known,false);
 assert.equal(M.reading(e,e.capability_id).observedAt,null);
}
console.log('U2A source observation metadata passed');
