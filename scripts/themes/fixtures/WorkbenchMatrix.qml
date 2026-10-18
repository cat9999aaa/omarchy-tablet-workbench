import QtQuick
import QtQuick.Window
import Quickshell
import qs.Commons
import "Workbench/Theme.js" as Theme
import "Cases.js" as Cases
import "Contrast.js" as Contrast
ShellRoot {
 id:root
 property int index:-1
 property var passed:[]
 property var current:null
 property int textChecks:0
 property int borderChecks:0
 property real minimumTextContrast:100
 property real minimumBorderContrast:100
 property var hotSnapshot:null
 property var hotButton:null
 function fail(message){console.error('C1_FAIL:'+message);Qt.quit();throw new Error(message)}
 function check(value,message){if(!value)fail(message)}
 function visibleThrough(item,stop){let p=item;while(p&&p!==stop){if(!p.visible)return false;p=p.parent}return true}
 function buttons(item,out){if(((item.text!==undefined||item.iconText!==undefined)&&typeof item.clicked==='function'||typeof item.toggled==='function')&&visibleThrough(item,scene))out.push(item);for(const child of item.children)buttons(child,out)}
 function texts(item,out){if(item.text!==undefined)out.push(item.text);for(const child of item.children)texts(child,out)}
 function layers(item){
  const result=[]
  for(let p=item;p;p=p.parent){
   let color=Qt.rgba(0,0,0,0)
   if(p.background&&p.background.color!==undefined&&p.background.visible)color=Qt.rgba(p.background.color.r,p.background.color.g,p.background.color.b,p.background.color.a*p.background.opacity)
   else if(p.color!==undefined&&p.color.r!==undefined)color=p.color
   result.push({color:color,opacity:p.opacity})
   if(p===scene)break
  }
  return result
 }
 function checkContrast(item,expectedFailure){
  if(!item.visible)return 0
  let failures=0
  if(item.paintedWidth!==undefined&&item.color!==undefined&&item.text){
   check(item.paintedHeight<=item.height+1&&item.paintedWidth<=item.width+1,'text-clipped:'+current.name+':'+String(item.text).slice(0,40))
   const samples=Contrast.samples(item.color,item.opacity,layers(item.parent))
   const ratio=Contrast.ratio(samples.foreground,samples.background)
   if(ratio<4.5)failures++
   if(!expectedFailure){
    check(ratio>=4.5,'text-contrast:'+current.name+':'+String(item.text).slice(0,40)+':'+ratio)
    textChecks++;minimumTextContrast=Math.min(minimumTextContrast,ratio)
   }
  }
  for(const child of item.children)failures+=checkContrast(child,expectedFailure)
  return failures
 }
 function find(item,name){if(item.objectName===name)return item;for(const child of item.children){const result=find(child,name);if(result)return result}return null}
 function hotUpdate(){
  current=Object.assign({},current,{surface:'control'})
  control.confirmation={name:'flight-on',params:{}}
  network.confirmFlight=true;network.selectedTab='proxy'
  hotPrepare.start()
 }
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
   const surface=b.background&&b.background.border!==undefined?b.background:b
   if(surface.border!==undefined&&surface.border.width>0){
    const samples=Contrast.samples(surface.border.color,surface===b?1:surface.opacity,layers(b))
    const ratio=Contrast.ratio(samples.foreground,samples.background)
    check(ratio>=3,'border-contrast:'+current.name+':'+b.text+':'+ratio)
    borderChecks++;minimumBorderContrast=Math.min(minimumBorderContrast,ratio)
   }
  }
 }
 function next(){
  if(++index>=Cases.rows.length){hotUpdate();return}
  current=Cases.rows[index];win.width=current.width;win.height=current.height
  Color.loadColors(current.high?Cases.colors.replace(/#0C1014/g,'#000000').replace(/#E7E9DF/g,'#FFFFFF'):Cases.colors)
  Color.loadShell(current.high?Cases.shell.replace(/#0C1014/g,'#000000').replace(/#E7E9DF/g,'#FFFFFF'):Cases.shell)
  Color.loadUserShell('[font]\nbase-size='+12*current.scale)
  control.appliedMode=current.mode;control.suggestedMode=current.mode
  control.expanded=current.surface==='control'&&!!current.view&&current.view!=='flight'
  control.page=control.expanded?current.view:'设备'
  control.flight={entertainment:current.surface==='control'&&current.view==='flight',verified:false}
  control.contractReadings.beginOpen()
  check(control.contractReadings.accept(control.contractReadings.startRequest(),{schema_version:1,legacy:{locked:false},contracts:{version:'0.1.0',status:'ok',states:[reading(true),reading(false)]}}),'contract-fixture:'+current.name)
  control.confirmation=current.state==='error'?{name:'flight-on',params:{}}:null
  control.feedback=current.state==='error'?'合成失败状态，请检查设备。'.repeat(8):''
  navigation.page=current.surface==='navigation'&&current.view?current.view:'窗口';navigation.feedback=current.state==='error'?'合成失败状态，原窗口保持':''
  network.state={wifi_enabled:false,wifi_connection:current.view==='wifi'?'合成中文热点名称'.repeat(20):'',wwan:true,signal:null,traffic:{day:null},policy:{proxy_enabled:false,mode:'auto'},health:{internet:current.state==='observed'?'ok':current.state==='error'?'failed':current.state}}
  if(network.wifiPanel!==undefined){
   const wifi=network.wifiPanel,ssid='合成中文热点名称'.repeat(12)
   wifi.info={type:'wifi',ssid:ssid,iface:'synthetic0'};wifi.travelPrimary='wifi'
   wifi.wifiStationAvailable=true;wifi.bandAvailable=['2.4','5'];wifi.bandCurrent='5';wifi.bandSelected='5';wifi.dnsProvider='DHCP'
   wifi.wifiNetworks=[{ssid:ssid,signal:70,security:'Wpa2Eap',known:true,connected:false}]
   wifi.passwordSsid=ssid;wifi.passwordText='';wifi.identityText=''
  }
  network.now=100;network.observedAt=current.state==='unknown'?0:current.state==='stale'?1:100;network.selectedTab=current.surface==='network'&&current.view?current.view:'cell';network.confirmFlight=current.state==='error'
  power.power=current.state==='observed'?{onBattery:true,displayDevice:{isPresent:true,percentage:.72,state:2,timeToEmpty:3600},devices:{values:[]}}:{onBattery:false,displayDevice:null,devices:{values:[]}}
  power.historyView.historyData={available:true,sessions:[],points:[
   {axis_time:0,time:1792339200000,BAT0:82,BAT1:76,net_discharge_w:12},
   {axis_time:60000,time:1792339260000,BAT0:81.8,BAT1:75.8,net_discharge_w:14},
   {axis_time:120000,time:1792339320000,BAT0:null,BAT1:null,net_discharge_w:null},
   {axis_time:180000,time:1792339380000,BAT0:81.2,BAT1:75.2,net_discharge_w:15},
   {axis_time:240000,time:1792339440000,BAT0:81,BAT1:75,net_discharge_w:14}]}
  power.historyView.selected=current.surface==='power'&&current.view?current.view:0
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
 Timer {id:hotPrepare;interval:50;onTriggered:{
  root.hotButton=root.find(control,'quick-keyboard');root.check(root.hotButton!==null,'hot-button-missing')
  root.hotButton.forceActiveFocus()
  const wifiInput=root.find(network,'wifi-pwField');root.check(wifiInput!==null,'hot-wifi-input-missing');wifiInput.text='synthetic-only'
  root.hotSnapshot={wifiInput:wifiInput,window:win,button:root.hotButton,confirmation:control.confirmation,mode:control.modeChoice,actions:JSON.stringify([control.actions,navigation.actions,network.actions,power.actions])}
  Color.loadColors(Cases.colors.replace(/#FFB454/g,'#00FFFF'))
  Color.loadUserShell('[font]\nbase-size=15')
  hotVerify.start()
 }}
 Timer {id:hotVerify;interval:200;onTriggered:{
  root.check(win===root.hotSnapshot.window&&win.visible,'hot-window-recreated')
  root.check(root.find(control,'quick-keyboard')===root.hotSnapshot.button&&root.hotButton.activeFocus,'hot-button-focus-lost')
  root.check(control.confirmation===root.hotSnapshot.confirmation&&control.modeChoice===root.hotSnapshot.mode,'hot-confirmation-or-mode-reset')
  root.check(network.confirmFlight&&network.selectedTab==='proxy','hot-network-state-reset')
  root.check(root.find(network,'wifi-pwField')===root.hotSnapshot.wifiInput&&root.hotSnapshot.wifiInput.text==='synthetic-only','hot-wifi-input-reset')
  root.check(JSON.stringify([control.actions,navigation.actions,network.actions,power.actions])===root.hotSnapshot.actions,'hot-action-triggered')
  root.check([control,navigation,network,power].every(item=>item.themeTokens.font.body===20),'hot-official-font-not-bound')
  Color.loadColors(Cases.colors.replace(/#E7E9DF/g,'#0C1014'))
  lowContrastVerify.start()
 }}
 Timer {id:lowContrastVerify;interval:200;onTriggered:{
  root.check(root.checkContrast(control,true)>0,'low-contrast-override-not-detected')
  Color.loadColors(Cases.colors);Color.loadShell(Cases.shell);Color.loadUserShell('')
  console.log('C1_RESULT:'+JSON.stringify({passed:root.passed,failed:[],textChecks:root.textChecks,borderChecks:root.borderChecks,minimumTextContrast:root.minimumTextContrast,minimumBorderContrast:root.minimumBorderContrast,hotUpdate:'preserved',lowContrastOverride:'detected-without-file-write'}));Qt.quit()
 }}
 Timer {id:settle;interval:120;onTriggered:{
  const item=root.current.surface==='control'?control:root.current.surface==='navigation'?navigation:root.current.surface==='network'?network:power
  root.check(Style.normalBorderAlpha===1&&Style.normalFillAlpha===.05,'candidate-shell-not-loaded')
  if(root.current.surface==='control') {
   const expected={observed:'42 °C',unknown:'未知',error:'读取失败',stale:'待读取',unavailable:'不可用'}[root.current.state]
   root.check(control.contractReadings.temperatureText===expected,'contract-health:'+root.current.name)
  }
  if(root.current.surface==='power'&&root.current.state!=='observed') {
   let labels=[];root.texts(item,labels);root.check(labels.indexOf('0%')<0,'unknown-battery-shown-as-zero')
   root.check(!power.chargeIndicator.visible,'unknown-battery-shown-as-charge')
  }
  if(root.current.surface==='network'&&root.current.view==='wifi') {
   root.check(network.wifiPanel!==undefined,'wifi-product-content-missing')
   const viewport=root.find(network,'workbenchScroll');root.check(viewport!==null,'wifi-scroll-missing')
   viewport.contentY=network.wifiPanel.mapToItem(viewport.contentItem,0,0).y
   const header=root.find(network,'wifi-bandHeader'),autoRow=root.find(network,'wifi-bandAutoRow')
   root.check(header!==null&&autoRow!==null,'wifi-band-content-missing')
   const a=header.mapToItem(scene,0,0),b=autoRow.mapToItem(scene,0,0)
   root.check(a.x+header.width<=b.x+.5||a.y+header.height<=b.y+.5||b.y+autoRow.height<=a.y+.5,'wifi-band-header-overlap')
   for(const name of ['wifi-rowMouse','wifi-rightMouse','wifi-idField','wifi-pwField','wifi-connectPwBtn']){
    const target=root.find(network,name);root.check(target!==null,'wifi-target-missing:'+name)
    root.check(target.width>=48&&target.height>=48,'wifi-target-small:'+name+':'+target.width+'x'+target.height)
   }
  }
  if(root.current.surface==='power'&&root.current.view===2){
   const plot=power.historyView.plotSurface,labels=plot.labels
   const outer=root.find(power,'workbenchScroll');root.check(outer!==null,'history-scroll-missing')
   outer.contentY=power.historyView.mapToItem(outer.contentItem,0,0).y
   let inner=plot.parent;while(inner&&inner.contentY===undefined)inner=inner.parent
   root.check(inner!==null,'history-inner-scroll-missing');inner.contentY=plot.mapToItem(inner.contentItem,0,0).y
   root.check(labels.length>=4,'history-labels-not-painted')
   for(let i=0;i<labels.length;i++){
    const a=labels[i];root.check(a.width>0&&isFinite(a.height),'history-measurement-invalid');root.check(a.x>=0&&a.x+a.width<=plot.width&&a.y>=0&&a.y<=plot.height,'history-label-outside:'+a.text)
    for(let j=i+1;j<labels.length;j++){
     const b=labels[j]
     root.check(Math.abs(a.y-b.y)>=Math.max(a.height,b.height)||a.x+a.width<=b.x||b.x+b.width<=a.x,'history-label-overlap:'+a.text+':'+b.text)
    }
   }
  }
  root.checkGeometry(item)
  root.checkContrast(item)
  const name=root.current.name
  const accepted=scene.grabToImage(function(result){
   root.check(result.saveToFile(Quickshell.env('C1_OUTPUT')+'/'+name+'.png'),'screenshot:'+name)
   root.passed.push(name);root.next()
  });root.check(accepted,'capture:'+name)
 }}
}
