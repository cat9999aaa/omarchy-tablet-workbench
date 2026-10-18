const assert=require('node:assert/strict'),A=require('./ControlActions.js'),M=require('./ControlModel.js');
const ids=['network','proxy','zero','touch','keyboard','nightlight','flight','power-mode','screen-off'];
assert.deepEqual(A.ids('tablet'),ids);
assert.deepEqual([...A.ids('desktop')].sort(),[...ids].sort());
const view={network:'未知',tun:{known:false,value:null,label:'未知'},proxy:{known:false},zero:{known:false,label:'未知'},touch:'未知',touchValue:null,night:'待确认',flightActive:null,flightSaved:false,power:'读取中'};
const entries=A.quick(view);assert.equal(entries.touch.action,'touch-refresh');assert.equal(entries.keyboard.action,'keyboard');assert.equal(entries.proxy.available,false);
assert.equal(A.quick({...view,touchValue:1}).touch.action,'touch-normal');
assert.equal(A.quick({...view,touchValue:0}).touch.action,'touch-glove');
assert.equal(A.quick({...view,flightSaved:true}).flight.action,'flight-off');
for(const flag of ['confirmation','action','pointer']) {
 const state={confirmation:false,action:false,pointer:false};state[flag]=true;
 assert.equal(M.selectLayout('desktop','tablet',state),'tablet');
}
assert.equal(M.selectLayout('desktop','tablet',{confirmation:false,action:false,pointer:false}),'desktop');
assert.equal(M.selectLayout('bad','tablet',{}),'tablet');
assert.equal(M.modeLabel('auto','unknown','tablet',true),'设备模式待确认');
assert(M.modeLabel('desktop','observed','desktop',false).includes('未保存'));
assert(A.group('工作').some(x=>x.op==='keyboard'));
assert(A.group('设备').some(x=>x.op==='touch-refresh'));
console.log('dual layouts share all actions; unsafe interactions defer changes');
