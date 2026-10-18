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
  return {contract_version:"0.1.0",capability_id:"dashen.device."+(t?"temperature":"touch-mode"),resource_id:t?"thermal-summary":"touch-mode",output_id:"local",read_permission:t?"device.temperature.read":"device.touch-mode.read",state:{available:true,actual:value,health:"observed",boot_default:1}}
 }
 function response(value) {return {schema_version:1,legacy:{locked:false},contracts:{version:"0.1.0",status:"ok",states:[envelope("temperature",value),envelope("touch",0)]}}}
 function create(){return createTemporaryObject(stateComponent,suite)}
 function test_close_reopen_late_result() {
  const s=create();compare(s.startRequest(),null);s.beginOpen();const a=s.startRequest();s.closeSession();s.beginOpen();const b=s.startRequest()
  verify(!s.accept(a,response(99)));verify(s.accept(b,response(0)));compare(s.temperatureText,"0 °C");compare(s.touchText,"普通触摸");verify(s.ready)
  verify(!s.accept(a,response(99)));compare(s.temperatureText,"0 °C")
  s.closeSession();verify(!s.ready);compare(s.startRequest(),null)
 }
 function test_pending_and_failure_invalidate_old_values() {
  const s=create();s.beginOpen();verify(s.accept(s.startRequest(),response(42)))
  const next=s.startRequest();verify(!s.ready);verify(s.temperatureText.indexOf("42")<0);compare(s.startRequest(),null)
  s.fail(next,"read_timeout");compare(s.temperatureText,"状态暂不可用");verify(!s.accept(next,response(42)))
  const again=s.startRequest();verify(s.accept(again,response(0)))
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
