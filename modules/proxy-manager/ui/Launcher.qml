import QtQuick
import Quickshell
import Quickshell.Io
ShellRoot {
 ShellTheme{id:theme}
 ProxyModel{id:backendModel;readOnly:Quickshell.env("OMT_PROXY_READONLY")==="1"}
 Transport {model:backendModel}
 FloatingWindow {
  id:window;implicitWidth:Math.min(1000,Quickshell.screens[0].width-48);implicitHeight:Math.min(780,Quickshell.screens[0].height-80);title:"代理工作台"
  Main {id:panel;anchors.fill:parent;model:backendModel;foreground:theme.foreground;background:theme.background;accent:theme.accent;onCloseRequested:Qt.quit()}
 }
 IpcHandler {target:"omt.proxy.ui";function page(index:int):void{panel.choosePage(index)}
 function geometry(width:int,height:int):void{window.width=width;window.height=height}
 function state():string{return JSON.stringify({page:panel.page,width:window.width,height:window.height,physical:backendModel.physicalLabel,proxy:backendModel.proxyLabel,tun:backendModel.tunLabel,pending:backendModel.pending})}}
}
