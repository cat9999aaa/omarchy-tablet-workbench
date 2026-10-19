import QtQuick
import QtTest
import ".." as Control
import "../Workbench" as UI
import "../ControlActions.js" as Actions
TestCase {
 id:suite;name:"ReadingActions";when:windowShown;visible:true;width:480;height:600
 Control.ContractState {id:state}
 readonly property var entry:Actions.quick({touch:state.touchText,touchValue:state.touchValue,tun:{},proxy:{},zero:{}}).touch
 UI.ActionGrid {id:grid;width:400;columns:1;items:[{id:'touch',label:entry.label,action:entry.action}];onTriggered:(action,payload)=>suite.calls.push(action)}
 property var calls:[]
 function response(mode){
  return {schema_version:1,legacy:{locked:false},contracts:{version:'0.1.0',status:'ok',states:[
   {contract_version:'0.1.0',capability_id:'dashen.device.temperature',resource_id:'thermal-summary',output_id:'local',read_permission:'device.temperature.read',state:{available:true,actual:42,health:'observed',observed_at:100}},
   {contract_version:'0.1.0',capability_id:'dashen.device.touch-mode',resource_id:'touch-mode',output_id:'local',read_permission:'device.touch-mode.read',state:{available:true,actual:mode,health:'observed',observed_at:100,boot_default:1}}]}}
 }
 function init(){state.closeSession();state.beginOpen();calls=[]}
 function test_history_never_selects_reverse_action(){
  state.accept(state.startRequest(),response(1));compare(entry.action,'touch-normal');const token=state.startRequest();verify(state.touchText.includes('上次'));compare(entry.action,'touch-refresh')
  state.fail(token,'read_timeout');compare(entry.action,'touch-refresh');state.accept(state.startRequest(),response(0));compare(entry.action,'touch-glove')
 }
 function test_pressed_action_cancelled_on_refresh(){
  state.accept(state.startRequest(),response(1));wait(20);const b=findChild(grid,'action-touch');const point=b.mapToItem(suite,b.width/2,b.height/2)
  mousePress(suite,point.x,point.y);state.startRequest();wait(20);compare(entry.action,'touch-refresh');mouseRelease(suite,point.x,point.y);compare(calls.length,0)
  mouseClick(b,b.width/2,b.height/2);compare(calls.length,1);compare(calls[0],'touch-refresh')
 }
}
