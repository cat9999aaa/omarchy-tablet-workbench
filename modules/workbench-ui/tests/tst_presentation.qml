import QtQuick
import QtTest
import "../Theme.js" as Theme
TestCase {
 name:"SharedPresentation";when:windowShown;visible:true;width:640;height:700
 function make(name,props) {
  const c=Qt.createComponent('../'+name+'.qml')
  compare(c.status,Component.Ready,c.errorString())
  const o=c.createObject(this,props||{});verify(o!==null);return o
 }
 function tokens(scale) {return Theme.resolve({schemaVersion:1,fontScale:scale||1,foreground:'#eeeeee',background:'#111111',accent:'#ffaa44',urgent:'#ff6677',muted:'#aabbcc'})}
 function entries() {return [{id:'files',label:'文件',action:'files',payload:{kind:'file'},enabled:true,selected:true,tone:'normal'},{id:'close',label:'关闭窗口',action:'close',payload:{target:1},enabled:false,selected:false,tone:'urgent'}]}
 function test_text_roles() {
  const t=make('StyledText',{width:180,text:'很长的中文说明需要自动换行以避免裁切',themeTokens:tokens(1.5)})
  compare(t.font.pixelSize,24);verify(t.implicitHeight>24)
  t.role='title';compare(t.font.pixelSize,32);t.tone='urgent';compare(t.color,Qt.color('#ff6677'))
  t.role='bad';t.tone='bad';compare(t.font.pixelSize,24);compare(t.color,Qt.color('#eeeeee'));t.destroy()
 }
 function test_grid_models_and_guarding() {
  const g=make('ActionGrid',{width:320,themeTokens:tokens(),items:entries()});wait(20)
  compare(g.modelError,'');const a=findChild(g,'action-files'),b=findChild(g,'action-close');verify(a&&b)
  verify(a.height>=48);verify(a.selected);compare(b.accent,Qt.color('#ff6677'))
  let calls=[];g.triggered.connect(function(action,payload){calls.push([action,payload])})
  mouseClick(a,a.width/2,a.height/2);compare(calls.length,1);compare(calls[0][0],'files');compare(calls[0][1].kind,'file')
  mouseClick(b,b.width/2,b.height/2);compare(calls.length,1)
  g.busy=true;mouseClick(a,a.width/2,a.height/2);compare(calls.length,1);g.busy=false
  g.items=[{id:'desktop',label:'桌面一',action:'switch',payload:{workspace:1}}];wait(20)
  const d=findChild(g,'action-desktop');verify(d);mouseClick(d,d.width/2,d.height/2);compare(calls.length,2);compare(calls[1][1].workspace,1);g.destroy()
 }
 function test_model_update_preserves_delegate_but_cancels_pending_action() {
  const g=make('ActionGrid',{width:320,themeTokens:tokens(),items:entries()});wait(20)
  const a=findChild(g,'action-files');let calls=[];g.triggered.connect(function(action,payload){calls.push(payload)})
  a.forceActiveFocus();mousePress(a,a.width/2,a.height/2)
  g.items=[{id:'files',label:'文件新目标',action:'files',payload:{kind:'new'},enabled:true},{id:'close',label:'关闭窗口',action:'close',enabled:false}];wait(20)
  compare(findChild(g,'action-files'),a);verify(a.activeFocus)
  mouseRelease(a,a.width/2,a.height/2);compare(calls.length,0)
  mouseClick(a,a.width/2,a.height/2);compare(calls.length,1);compare(calls[0].kind,'new');g.destroy()
 }
 function test_pending_action_cancelled_by_reorder_disable_shrink_or_invalid_model() {
  for(const mode of ['reorder','disable','shrink','invalid']) {
   const g=make('ActionGrid',{width:320,themeTokens:tokens(),items:entries()});wait(20)
   const a=findChild(g,'action-files');let calls=0;g.triggered.connect(function(){calls++})
   mousePress(a,a.width/2,a.height/2)
   if(mode==='reorder') {let next=entries().reverse();next[0].enabled=true;next[1].enabled=true;g.items=next}
   if(mode==='disable') {let next=entries();next[0].enabled=false;g.items=next}
   if(mode==='shrink')g.items=[]
   if(mode==='invalid')g.items=[{}]
   wait(20)
   mouseRelease(g,20,20);compare(calls,0)
   if(mode==='disable') {compare(findChild(g,'action-files'),a);verify(!a.enabled)}
   if(mode==='reorder')compare(findChild(g,'action-close'),a)
   g.destroy();wait(10)
  }
 }
 function test_invalid_models() {
  const g=make('ActionGrid',{width:320,themeTokens:tokens()})
  for(const value of [null,{},{length:1,0:{id:"x",label:"X",action:"go"}},[{}],[{id:'x',label:'X',action:'go'},{id:'x',label:'Y',action:'go'}],[{id:'x',label:'X',action:'go',enabled:'yes'}]]) {
   g.items=value;wait(10);verify(g.modelError.length>0);verify(!findChild(g,'action-x'))
  }
  g.items=[];compare(g.modelError,'');g.destroy()
 }
 function test_theme_update_keeps_identity_press_focus() {
  const g=make('ActionGrid',{width:320,themeTokens:tokens(),items:entries()});wait(20)
  const a=findChild(g,'action-files');let calls=0;g.triggered.connect(function(){calls++})
  a.forceActiveFocus();mousePress(a,a.width/2,a.height/2);verify(a.down)
  g.themeTokens=tokens(1.5);wait(20);compare(findChild(g,'action-files'),a);verify(a.activeFocus);verify(a.down)
  mouseRelease(a,a.width/2,a.height/2);compare(calls,1)
  for(const width of [320,480,640]) {g.width=width;wait(10);verify(a.width>=48);verify(a.height>=48);verify(a.x+a.width<=g.width)}
  g.destroy()
 }
}
