// Pure navigation session state. Effects are instructions, never executed here.
function initial() {
 return {generation:0,phase:'closed',page:'窗口',output:null,data:null,feedback:''};
}
function reduce(state,event) {
 var unchanged={state:state,effects:[]};
 if(!event||typeof event.type!=='string')return unchanged;
 function closed(feedback) {
  var effects=state.phase==='loading'?[{type:'cancel-read',generation:state.generation}]:[];
  effects.push({type:'close'});
  return {state:Object.assign({},state,{generation:state.generation+1,phase:'closed',output:null,data:null,feedback:feedback||'',actionId:null}),effects:effects};
 }
 if(event.type==='CLOSE'||event.type==='LOCKED'||event.type==='OUTPUT_LOST')return closed('');
 if(event.type==='OPEN') {
  if(['开始','桌面','窗口','按键'].indexOf(event.page)<0)return unchanged;
  var generation=state.generation+1;
  var effects=state.phase==='loading'?[{type:'cancel-read',generation:state.generation}]:[];
  effects.push({type:'read',generation:generation,page:event.page});
  return {state:{generation:generation,phase:'loading',page:event.page,output:null,data:null,feedback:'',actionId:null},effects:effects};
 }
 if(event.generation!==state.generation)return unchanged;
 if(event.type==='READ_OK'&&state.phase==='loading') {
  var data=event.data;
  if(!data||data.ok!==true||typeof data.output!=='string'||!data.output)return closed('invalid-data');
  return {state:Object.assign({},state,{phase:'open',data:data,output:data.output,feedback:''}),effects:[]};
 }
 if(event.type==='READ_ERROR'&&state.phase==='loading')return closed(event.code||'invalid-data');
 if(event.type==='ACT_STARTED'&&state.phase==='open') {
  if(typeof event.id!=='string'||!event.id)return unchanged;
  return {state:Object.assign({},state,{phase:'acting',actionId:event.id,feedback:''}),effects:[]};
 }
 if(event.type==='ACT_RESULT'&&state.phase==='acting'&&event.id===state.actionId) {
  var result=event.result;
  if(!result||result.ok!==true)return {state:Object.assign({},state,{phase:'open',actionId:null,feedback:result&&typeof result.reason==='string'?result.reason:'action-failed'}),effects:[]};
  if(result.bindings)return {state:Object.assign({},state,{phase:'open',actionId:null,data:Object.assign({},state.data,{bindings:result.bindings}),feedback:'按键设置已保存'}),effects:[]};
  return closed('');
 }
 return unchanged;
}
if(typeof module!=='undefined')module.exports={initial:initial,reduce:reduce};
