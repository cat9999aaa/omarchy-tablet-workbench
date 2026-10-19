import QtQuick
import QtQuick.Window
import Quickshell
import Quickshell.Io
import qs.Commons as Official
ShellRoot {
 id:root
 property var passed:[]
 property int tries:0
 function check(value,name){if(!value){console.error('C1_FAIL:'+name);Qt.quit();throw new Error(name)}passed.push(name)}
 FileView {id:palette;path:Quickshell.env('C1_PALETTE')}
 FileView {id:shell;path:Quickshell.env('C1_SHELL')}
 Window {
  id:win;visible:true;width:640;height:480
  Rectangle {
   id:surface;anchors.fill:parent;color:Official.Color.popups.background
   Column {anchors.centerIn:parent;spacing:24
    Text {text:'DASHEN // OVERDRIVE';color:Official.Color.foreground;font.pixelSize:28}
    Text {text:'官方主题解析 · 用户覆盖 · 恢复';color:Official.Color.accent;font.pixelSize:20}
    Rectangle {width:420;height:64;color:Official.Style.normalFill;border.color:Official.Style.focusBorderColor;border.width:Official.Style.focusBorderWidth
     Text {anchors.centerIn:parent;text:'中文状态可读性检查';color:Official.Color.foreground;font.pixelSize:18}}
   }
  }
 }
 Timer {
  interval:100;repeat:true;running:true
  onTriggered:{
   if(++root.tries>50){root.check(false,'startup-timeout');return}
   if(Official.Color.foreground.toString()!=='#e7e9df'||Official.Style.font.body!==18)return
   stop()
   root.check(Official.Color.popups.background.toString()==='#182028','user-color-override')
   root.check(Official.Style.font.body===18,'user-font-override')
   root.check(Official.Color.accent.toString()==='#ffb454','palette-loaded')
   const component=Qt.createComponent('Workbench/ThemeContext.qml')
   root.check(component.status===Component.Ready,'shared-theme-adapter')
   const adapter=component.createObject(root)
   root.check(adapter!==null&&adapter.tokens.font.body===24&&adapter.tokens.colors.accent.toString()==='#ffb454','shared-theme-update')
   const identity=surface
   Official.Color.loadUserShell('')
   root.check(Official.Style.font.body===12&&adapter.tokens.font.body===16,'override-removal')
   root.check(Official.Color.popups.background.toString()==='#0c1014','theme-surface')
   Official.Color.loadColors('background = "#000000"\nforeground = "#ffffff"\naccent = "#00ffff"\nred = "#ff0000"')
   Official.Color.loadShell('')
   root.check(Official.Color.popups.background.toString()==='#000000','old-theme-fallback')
   palette.reload();palette.waitForJob();shell.reload();shell.waitForJob()
   Official.Color.loadColors(palette.text());Official.Color.loadShell(shell.text())
   root.check(Official.Color.popups.background.toString()==='#0c1014'&&Official.Color.foreground.toString()==='#e7e9df','theme-restored')
   root.check(surface===identity&&win.visible,'window-survived')
   capture.start()
  }
 }
 Timer {id:capture;interval:100;onTriggered:{
  const accepted=surface.grabToImage(function(result){
   root.check(result.saveToFile(Quickshell.env('C1_OUTPUT')+'/shell.png'),'screenshot-saved')
   console.log('C1_RESULT:'+JSON.stringify({passed:root.passed,failed:[]}));Qt.quit()
  });root.check(accepted,'capture-requested')
 }}
}
