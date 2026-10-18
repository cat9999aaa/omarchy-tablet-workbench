import QtQuick
import QtTest
import ".." as WB
import "../Theme.js" as Theme
TestCase {
 name:'WorkbenchRenderedContrast';visible:true;when:windowShown;width:480;height:300
 Component {id:button;WB.TouchButton {text:'未知 · 需要确认';width:220}}
 function mix(f,b,a){return Qt.rgba(f.r*a+b.r*(1-a),f.g*a+b.g*(1-a),f.b*a+b.b*(1-a),1)}
 function luminance(c){function linear(v){return v<=.04045?v/12.92:Math.pow((v+.055)/1.055,2.4)}return .2126*linear(c.r)+.7152*linear(c.g)+.0722*linear(c.b)}
 function ratio(a,b){const x=luminance(a),y=luminance(b);return (Math.max(x,y)+.05)/(Math.min(x,y)+.05)}
 function test_final_colors_data(){return ['normal','selected','pressed','disabled','focus'].map(s=>({tag:s,state:s}))}
 function test_final_colors(d){
  const bg=Qt.color('#0c1014'),t=Theme.resolve({schemaVersion:1,foreground:Qt.color('#e7e9df'),accent:Qt.color('#ffb454')})
  const b=createTemporaryObject(button,this,{themeTokens:t});verify(b!==null);b.focus=false
  if(d.state==='selected')b.selected=true
  if(d.state==='pressed')b.down=true
  if(d.state==='disabled')b.enabled=false
  if(d.state==='focus')b.forceActiveFocus()
  wait(10)
  const fill=mix(b.background.color,bg,b.background.color.a)
  const text=mix(b.contentItem.color,fill,b.contentItem.color.a*b.contentItem.opacity)
  const border=mix(b.background.border.color,fill,b.background.border.color.a)
  verify(ratio(text,fill)>=4.5,'text contrast '+ratio(text,fill))
  verify(ratio(border,fill)>=3,'border contrast '+ratio(border,fill))
 }
}
