import QtQuick
import QtTest
import "../ControlModel.js" as Model
import "../ControlActions.js" as Actions
TestCase {
 name:"ModeLayout";when:windowShown
 function test_safe_boundary_and_latest_suggestion() {
  let applied="tablet"
  for(const flags of [{confirmation:true},{action:true},{pointer:true}])compare(Model.selectLayout("desktop",applied,flags),"tablet")
  applied=Model.selectLayout("desktop",applied,{})
  compare(applied,"desktop")
  compare(Model.selectLayout("tablet",applied,{pointer:true}),"desktop")
  compare(Model.selectLayout("tablet",applied,{}),"tablet")
 }
 function test_both_modes_keep_same_actions_and_unknown_is_honest() {
  compare(Actions.ids("tablet").slice().sort().join(","),Actions.ids("desktop").slice().sort().join(","))
  compare(Model.modeLabel("auto","unknown","tablet",true),"设备模式待确认")
  verify(Model.modeLabel("tablet","observed","tablet",false).indexOf("未保存")>=0)
 }
}
