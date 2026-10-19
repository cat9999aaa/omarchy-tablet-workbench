import QtQuick
import QtTest
import ".." as UI
import "../Theme.js" as Theme
TestCase {
 id:suite;name:"Readout";when:windowShown;visible:true;width:1600;height:1600
 Component {id:cardComponent;UI.PanelBody {
  id:card;width:320;height:320;title:"观测";themeTokens:Theme.resolve({schemaVersion:1,fontScale:1.5})
  UI.Readout {width:parent.width;themeTokens:card.themeTokens;label:"触摸";valueText:"上次 普通触摸";statusText:"本次读取失败，历史仅供参考。".repeat(40)}
  UI.TouchButton {objectName:"refreshReadout";width:parent.width;themeTokens:card.themeTokens;text:"刷新状态"}
 }}
 function test_scroll_keeps_close_and_refresh_reachable(){
  const panel=createTemporaryObject(cardComponent,suite);wait(20);const scroll=findChild(panel,'workbenchScroll'),close=findChild(panel,'workbenchClose'),refresh=findChild(panel,'refreshReadout')
  verify(scroll.contentHeight>scroll.height);panel.contentY=scroll.contentHeight-scroll.height;wait(20)
  const point=refresh.mapToItem(panel,0,0);verify(point.y>=0&&point.y+refresh.height<=panel.height+1);verify(refresh.height>=48&&close.height>=48)
  let hits=0,closed=0;refresh.clicked.connect(function(){hits++});panel.closeRequested.connect(function(){closed++});mouseClick(refresh,refresh.width/2,refresh.height/2);compare(hits,1);mouseClick(close,close.width/2,close.height/2);compare(closed,1)
 }
 function make(w,scale,light) {
  const c=Qt.createComponent('../Readout.qml');compare(c.status,Component.Ready,c.errorString())
  return c.createObject(suite,{width:w,themeTokens:Theme.resolve({schemaVersion:1,fontScale:scale,foreground:light?'#182024':'#eeeeee',background:light?'#f3f0e7':'#101518',muted:light?'#47565c':'#b1b9ba'}),label:'温度',valueText:'上次 42 °C',statusText:'更新中：上次观测仅供参考，当前状态仍待确认。'.repeat(4),observedAt:100})
 }
 function test_layout_data(){let r=[];for(const w of [320,480,864,1536])for(const scale of [1,1.25,1.5])for(const light of [false,true])r.push({tag:w+'-'+scale+'-'+light,w:w,scale:scale,light:light});return r}
 function test_layout(d){
  const o=make(d.w,d.scale,d.light);wait(20);let bottom=0
  for(const child of o.children){if(!child.visible)continue;compare(child.textFormat,Text.PlainText);compare(child.wrapMode,Text.Wrap);verify(child.paintedWidth<=child.width+1);bottom=Math.max(bottom,child.y+child.height)}
  verify(o.implicitHeight>=bottom);verify(o.implicitHeight>0);compare(findChild(o,'readoutValue').text,'上次 42 °C');o.destroy()
 }
 function test_empty_and_plain_text(){
  const o=make(320,1,false);o.valueText='';wait(10);verify(!findChild(o,'readoutValue').visible);verify(findChild(o,'readoutStatus').visible)
  o.valueText='<b>0 °C</b>';wait(10);compare(findChild(o,'readoutValue').textFormat,Text.PlainText);verify(findChild(o,'readoutValue').visible);o.destroy()
 }
 function test_source_time_only(){
  const o=make(320,1,false);const t=findChild(o,'readoutTime');verify(t.text.includes('1970-01-01'));verify(t.text.includes('本地时间'));const original=t.text
  o.statusText='本次读取失败';compare(t.text,original)
  for(const value of [null,undefined,true,-1,NaN,Infinity,8640000000001]){o.observedAt=value;compare(t.text,'采样时间未知')}
  o.destroy()
 }
}
