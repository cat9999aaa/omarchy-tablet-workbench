import QtQuick
import QtTest
import QtQuick.Controls
import "../Theme.js" as Theme
import ".." as WB
TestCase {
 visible:true;name:"WorkbenchThemeCompatibility";when:windowShown;width:640;height:600
 Component {id:plainComponent;Button {text:"原生按钮"}}
 Component {id:buttonComponent;WB.TouchButton {width:200;text:"确认中文操作"}}
 Component {id:panelComponent;WB.PanelBody {width:320;height:300;title:"这是一个很长的中文控制面板标题";subtitle:"状态未知，请检查设备；此处允许换行";Rectangle {width:parent.width;height:1200}}}
 function tokens() {return {colors:{foreground:"#e7e9df",accent:"#ffb454"},font:{family:"sans-serif",body:24,subtitle:19.5,title:31.5},metrics:{minimumTouchHeight:48,paddingX:18,paddingY:15,gap:18,radius:8},states:{normalAlpha:.05,selectedAlpha:.18,pressedAlpha:.28,disabledTextAlpha:.65,focusBorderWidth:2}}}
 function test_theme_update_preserves_button_and_connection() {
  const b=createTemporaryObject(buttonComponent,this);verify(b!==null)
  verify('themeTokens' in b,'optional themeTokens API missing')
  const label=b.contentItem,background=b.background;let count=0;b.clicked.connect(function(){count++})
  b.themeTokens=tokens();wait(10);compare(b.contentItem,label);compare(b.background,background)
  compare(b.font.pixelSize,24);verify(b.height>=48);compare(b.leftPadding,18)
  b.forceActiveFocus();mousePress(b,b.width/2,b.height/2);verify(b.down)
  const next=tokens();next.colors.accent='#00ffff';b.themeTokens=next;wait(10)
  compare(b.contentItem,label);verify(b.down);verify(b.activeFocus)
  mouseRelease(b,b.width/2,b.height/2);compare(count,1)
  b.font.pixelSize=20;b.themeTokens=tokens();compare(b.font.pixelSize,20)
 }
 function test_null_tokens_preserve_legacy_and_disabled() {
  const b=createTemporaryObject(buttonComponent,this);verify(b!==null)
  verify('themeTokens' in b);compare(b.themeTokens,null);compare(b.leftPadding,12)
  const plain=createTemporaryObject(plainComponent,this);compare(b.font.pixelSize,plain.font.pixelSize);compare(b.font.family,plain.font.family)
  b.enabled=false;compare(b.contentItem.opacity,.45)
  b.themeTokens=tokens();compare(b.contentItem.opacity,.65)
 }
 function test_typed_alpha_and_explicit_properties() {
  const b=createTemporaryObject(buttonComponent,this);verify(b!==null)
  const c=Qt.rgba(.3,.4,.5,.2)
  b.themeTokens=Theme.resolve({schemaVersion:1,foreground:c,accent:c,fontScale:1.5})
  fuzzyCompare(b.foreground.a,.2,.001);fuzzyCompare(b.contentItem.color.a,.2,.001)
  b.foreground='#ffffff';b.leftPadding=30;b.minimumTouchHeight=64
  b.themeTokens=Theme.resolve({schemaVersion:1,foreground:'#000000',fontScale:1})
  compare(b.foreground,Qt.rgba(1,1,1,1));compare(b.leftPadding,30);verify(b.height>=64)
 }
 function test_scaled_panel_close_and_scroll() {
  const p=createTemporaryObject(panelComponent,this);verify(p!==null)
  verify('themeTokens' in p);p.themeTokens=tokens();wait(10)
  const close=findChild(p,'workbenchClose');verify(close!==null)
  for(const w of [320,480,640]) {
   p.width=w;p.contentY=800;wait(10)
   const pos=close.mapToItem(p,0,0);verify(pos.x>=0);verify(pos.x+close.width<=p.width);verify(pos.y>=0);verify(pos.y+close.height<=p.height)
   verify(close.width>=48);verify(close.height>=48)
  }
  let n=0;p.closeRequested.connect(function(){n++});mouseClick(close,close.width/2,close.height/2);compare(n,1)
 }
}
