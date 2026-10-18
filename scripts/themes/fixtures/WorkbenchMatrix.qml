import QtQuick
import QtQuick.Window
import Quickshell
import qs.Commons
import "Workbench/Theme.js" as Theme
import "Cases.js" as Cases
ShellRoot {
 id:root
 property int index:-1
 property var passed:[]
 property var current:null
 function fail(message){console.error('C1_FAIL:'+message);Qt.quit();throw new Error(message)}
 function check(value,message){if(!value)fail(message)}
 function visibleThrough(item,stop){let p=item;while(p&&p!==stop){if(!p.visible)return false;p=p.parent}return true}
 function buttons(item,out){if(item.text!==undefined&&typeof item.clicked==='function'&&visibleThrough(item,scene))out.push(item);for(const child of item.children)buttons(child,out)}
 function texts(item,out){if(item.text!==undefined)out.push(item.text);for(const child of item.children)texts(child,out)}
 function reading(temperature){
  return {contract_version:'0.1.0',capability_id:temperature?'dashen.device.temperature':'dashen.device.touch-mode',resource_id:temperature?'thermal-summary':'touch-mode',output_id:'local',read_permission:temperature?'device.temperature.read':'device.touch-mode.read',state:{available:current.state!=='unavailable',actual:current.state==='observed'?(temperature?42:0):null,health:current.state,boot_default:1}}
 }
 function checkGeometry(item){
  let list=[];buttons(item,list);check(list.length>0,'no-buttons:'+current.name)
  for(const b of list){
   const p=b.mapToItem(scene,0,0)
   check(b.width>=47.9&&b.height>=47.9,'touch-target:'+current.name+':'+b.text+':'+b.width+'x'+b.height)
   check(p.x>=-.5&&p.x+b.width<=scene.width+.5,'horizontal-overflow:'+current.name+':'+b.text)
   let scroll=b.parent;while(scroll&&scroll!==item&&scroll.contentY===undefined)scroll=scroll.parent
   if(scroll&&scroll.contentY!==undefined)check(scroll.height>=48,'no-scroll-viewport:'+current.name)
   else check(p.y>=-.5&&p.y+b.height<=scene.height+.5,'header-unreachable:'+current.name+':'+b.text)
  }
 }
 function next(){
  if(++index>=Cases.rows.length){console.log('C1_RESULT:'+JSON.stringify({passed:passed,failed:[]}));Qt.quit();return}
  current=Cases.rows[index];win.width=current.width;win.height=current.height
  Color.loadColors('background = "'+(current.high?'#000000':'#0c1014')+'"\nforeground = "'+(current.high?'#ffffff':'#e7e9df')+'"\naccent = "#ffb454"\nred = "#ff6778"')
  Color.loadShell('');Color.loadUserShell('[font]\nbase-size='+12*current.scale)
  control.themeScale=current.scale;navigation.themeScale=current.scale
  control.appliedMode=current.mode;control.suggestedMode=current.mode
  control.contractReadings.beginOpen()
  check(control.contractReadings.accept(control.contractReadings.startRequest(),{schema_version:1,legacy:{locked:false},contracts:{version:'0.1.0',status:'ok',states:[reading(true),reading(false)]}}),'contract-fixture:'+current.name)
  control.confirmation=current.state==='error'?{name:'flight-on',params:{}}:null
  control.feedback=current.state==='error'?'合成失败状态，请检查设备。'.repeat(8):''
  navigation.page='窗口';navigation.feedback=current.state==='error'?'合成失败状态，原窗口保持':''
  network.themeTokens=Theme.resolve({schemaVersion:1,foreground:Color.foreground,accent:Color.accent,fontScale:current.scale,fontFamily:Style.font.family})
  network.state={wifi_enabled:false,wwan:true,signal:null,traffic:{day:null},policy:{proxy_enabled:false,mode:'auto'},health:{internet:current.state==='observed'?'ok':current.state==='error'?'failed':current.state}}
  network.now=100;network.observedAt=current.state==='unknown'?0:current.state==='stale'?1:100;network.selectedTab='cell';network.confirmFlight=current.state==='error'
  power.power=current.state==='observed'?{onBattery:true,displayDevice:{isPresent:true,percentage:.72,state:2,timeToEmpty:3600},devices:{values:[]}}:{onBattery:false,displayDevice:null,devices:{values:[]}}
  settle.start()
 }
 Window {
  id:win;visible:true;width:640;height:480
  Rectangle {
   id:scene;anchors.fill:parent;color:Color.background
   ControlSurface {id:control;anchors.fill:parent;visible:root.current&&root.current.surface==='control'}
   NavigationSurface {id:navigation;anchors.fill:parent;visible:root.current&&root.current.surface==='navigation'}
   NetworkSurface {id:network;anchors.fill:parent;visible:root.current&&root.current.surface==='network'}
   PowerSurface {id:power;anchors.fill:parent;visible:root.current&&root.current.surface==='power'}
  }
 }
 Timer {interval:500;running:true;onTriggered:root.next()}
 Timer {id:settle;interval:120;onTriggered:{
  const item=root.current.surface==='control'?control:root.current.surface==='navigation'?navigation:root.current.surface==='network'?network:power
  if(root.current.surface==='control') {
   const expected={observed:'42 °C',unknown:'未知',error:'读取失败',stale:'待读取',unavailable:'不可用'}[root.current.state]
   root.check(control.contractReadings.temperatureText===expected,'contract-health:'+root.current.name)
  }
  if(root.current.surface==='power'&&root.current.state!=='observed') {
   let labels=[];root.texts(item,labels);root.check(labels.indexOf('0%')<0,'unknown-battery-shown-as-zero')
   root.check(!power.chargeIndicator.visible,'unknown-battery-shown-as-charge')
  }
  root.checkGeometry(item)
  const name=root.current.name
  const accepted=scene.grabToImage(function(result){
   root.check(result.saveToFile(Quickshell.env('C1_OUTPUT')+'/'+name+'.png'),'screenshot:'+name)
   root.passed.push(name);root.next()
  });root.check(accepted,'capture:'+name)
 }}
}
