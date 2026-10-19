import QtQuick
import QtTest
import ".." as Control
import "../Workbench" as WB
TestCase {
 id: suite; name:"ContractState";when:windowShown;visible:true;width:640;height:600
 Component {id:stateComponent;Control.ContractState {}}
 Component {id:cardComponent;Rectangle {
  height:400
  WB.PanelHeader {id:header;width:parent.width;title:"最近一次采样结果"}
  Text {anchors.top:header.bottom;width:parent.width;wrapMode:Text.Wrap;text:"状态暂不可用，等待下一次读取。非常长的中文说明不会附加温度单位或挤掉关闭入口。"}
  WB.TouchButton {objectName:"refreshTouch";anchors.bottom:parent.bottom;width:parent.width;text:"刷新触摸模式"}
 }}
 function envelope(kind,value) {
  const t=kind==="temperature"
  return {contract_version:"0.1.0",capability_id:"dashen.device."+(t?"temperature":"touch-mode"),resource_id:t?"thermal-summary":"touch-mode",output_id:"local",read_permission:t?"device.temperature.read":"device.touch-mode.read",state:{available:true,actual:value,health:"observed",observed_at:100,boot_default:1}}
 }
 function response(value) {return {schema_version:1,legacy:{locked:false},contracts:{version:"0.1.0",status:"ok",states:[envelope("temperature",value),envelope("touch",0)]}}}
 function create(){return createTemporaryObject(stateComponent,suite)}
 function test_close_reopen_late_result() {
  const s=create();compare(s.startRequest(),null);s.beginOpen();const a=s.startRequest();s.closeSession();s.beginOpen();const b=s.startRequest()
  verify(!s.accept(a,response(99)));verify(s.accept(b,response(0)));compare(s.temperatureText,"0 °C");compare(s.touchText,"普通触摸");verify(s.ready)
  verify(!s.accept(a,response(99)));compare(s.temperatureText,"0 °C")
  s.closeSession();verify(!s.ready);compare(s.startRequest(),null)
 }
 function test_pending_keeps_history_but_invalidates_actions() {
  const s=create();s.beginOpen();compare(s.temperatureText,"读取中");verify(s.accept(s.startRequest(),response(42)))
  const next=s.startRequest();verify(!s.ready);compare(s.touchValue,null);compare(s.requestState,"loading")
  verify(s.temperatureDisplay.valueText.includes("42"));verify(s.temperatureDisplay.valueText.includes("上次"));compare(s.temperatureDisplay.observedAt,100)
  compare(s.startRequest(),null);s.fail(next,"read_timeout");compare(s.requestState,"error");verify(s.temperatureDisplay.historical)
  verify(s.temperatureDisplay.statusText.includes("失败"));verify(!s.accept(next,response(99)))
  verify(s.accept(s.startRequest(),response(0)));compare(s.temperatureDisplay.valueText,"0 °C");verify(!s.temperatureDisplay.historical);compare(s.touchValue,0)
 }
 function test_partial_observations_are_independent_data() {return [{tag:"temperature",index:0},{tag:"touch",index:1}]}
 function test_partial_observations_are_independent(d) {
  const s=create();s.beginOpen();s.accept(s.startRequest(),response(42));const r=response(0);r.contracts.states[d.index].state.health="error"
  s.accept(s.startRequest(),r)
  if(d.index===0){verify(s.temperatureDisplay.historical);verify(s.temperatureDisplay.valueText.includes("42"));compare(s.touchValue,0);verify(!s.touchDisplay.historical)}
  else {compare(s.temperatureDisplay.valueText,"0 °C");verify(s.touchDisplay.historical);compare(s.touchValue,null)}
  const missing={schema_version:1,legacy:{locked:false},contracts:{version:"0.1.0",status:"unavailable",states:[]}}
  s.accept(s.startRequest(),missing);verify(!s.ready);compare(s.touchValue,null);verify(s.temperatureDisplay.historical);verify(s.temperatureDisplay.statusText.includes("不可用"))
 }
 function test_bad_response_clears_good_history_data() {return ["identity","duplicate","json","oversize","truncated","locked"].map(x=>({tag:x,mode:x}))}
 function test_bad_response_clears_good_history(d) {
  const s=create();s.beginOpen();s.accept(s.startRequest(),response(42));const token=s.startRequest(),r=response(99)
  if(d.mode==="identity"){r.contracts.states[0].output_id="remote";verify(!s.accept(token,r))}
  else if(d.mode==="duplicate"){r.contracts.states[1]=r.contracts.states[0];verify(!s.accept(token,r))}
  else if(d.mode==="locked"){r.legacy.locked=true;verify(!s.accept(token,r));verify(!s.sessionOpen)}
  else verify(!s.finish(token,d.mode==="json"?"{":d.mode==="oversize"?"x".repeat(65537):JSON.stringify(r),0,d.mode!=="truncated"))
  compare(s.lastTemperature,null);compare(s.lastTouch,null);compare(s.touchValue,null);verify(!s.ready);verify(!s.temperatureText.includes("42"));verify(!s.accept(token,response(77)))
 }
 function test_transport_failure_keeps_only_labeled_history_data(){return ["read_timeout","start_failed","nonzero"].map(x=>({tag:x,mode:x}))}
 function test_transport_failure_keeps_only_labeled_history(d){
  const s=create();s.beginOpen();s.accept(s.startRequest(),response(42));const token=s.startRequest()
  if(d.mode==="nonzero")verify(!s.finish(token,"",1,true));else s.fail(token,d.mode)
  verify(s.temperatureDisplay.historical);verify(s.temperatureText.includes("上次"));compare(s.touchValue,null);verify(!s.ready)
 }
 function test_history_is_copied_and_cleared_with_session(){
  const s=create();s.beginOpen();const r=response(42);s.accept(s.startRequest(),r);r.contracts.states[0].state.actual=99;r.contracts.states[0].state.observed_at=999
  const old=s.startRequest();compare(s.temperatureDisplay.observedAt,100);verify(s.temperatureText.includes("42"))
  s.closeSession();compare(s.lastTemperature,null);compare(s.lastTouch,null);s.beginOpen();const fresh=s.startRequest()
  verify(!s.accept(old,response(99)));verify(s.accept(fresh,response(0)));verify(!s.accept(fresh,response(88)));compare(s.temperatureText,"0 °C")
 }
 function test_transport_and_lock_fail_closed() {
  for(const mode of ["read_timeout","nonzero","parse","truncated","locked"]){
   const s=create();s.beginOpen();const token=s.startRequest();let r=response(42)
   if(mode==="locked"){r.legacy.locked=true;verify(!s.accept(token,r));verify(!s.sessionOpen)}
   else if(mode==="read_timeout")s.fail(token,mode)
   else verify(!s.finish(token,mode==="parse"?"{":JSON.stringify(r),mode==="nonzero"?1:0,mode!=="truncated"))
   verify(!s.ready);verify(s.temperatureText.indexOf("°C")<0);verify(!s.accept(token,response(42)))
  }
 }
 function test_wrong_identity_no_legacy_fallback() {
  const s=create();s.beginOpen();const r=response(0);r.legacy.temperature={available:true,actual:99,health:"observed"};r.contracts.states[0].output_id="remote"
  verify(!s.accept(s.startRequest(),r));verify(!s.ready);verify(s.temperatureText.indexOf("99")<0)
 }
 function test_geometry_and_touch_recovery() {
  for(const w of [640,480,320]){
   const card=createTemporaryObject(cardComponent,suite,{width:w});wait(10);compare(card.width,w);compare(card.height,400)
   const close=findChild(card,"workbenchClose"),refresh=findChild(card,"refreshTouch");verify(close!==null);verify(refresh!==null)
   const point=close.mapToItem(card,0,0);verify(point.x>=0);verify(point.x+close.width<=w);verify(close.height>=48);verify(refresh.height>=48)
  }
 }
}
