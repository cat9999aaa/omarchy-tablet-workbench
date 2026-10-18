import QtQuick
import Quickshell
import Quickshell.Io
Item {
 id:root
 required property var model
 property string binary:Quickshell.env("OMT_PROXY_BINARY")||Quickshell.env("HOME")+"/.local/lib/omt-proxy/omt-proxy"
 property string socket:Quickshell.env("OMT_PROXY_SOCKET")||Quickshell.env("XDG_RUNTIME_DIR")+"/omt-proxy/control.sock"
 property bool active:true
 property string store:Quickshell.env("OMT_PROXY_STORE")||Quickshell.env("HOME")+"/.local/state/omt-proxy"
 Component.onCompleted:root.model.catalogAction({action:"list"})
 Connections {target:root.model;function onCatalogRequested(command){if(catalogProcess.running)return;catalogProcess.payload=JSON.stringify(command);catalogProcess.running=true}
 function onRequested(command){if(action.running)return;action.payload=JSON.stringify(command);action.running=true}}
 Process {id:watch;command:[root.binary,"watch",root.socket];running:root.active
  stdout:SplitParser {onRead:function(data){try{root.model.accept(JSON.parse(data))}catch(e){root.model.accept({error_code:"invalid_response"})}}}
  onExited:if(root.active)root.model.accept({error_code:"service_unavailable"})
 }
 Process {id:action;property string payload:"";command:[root.binary,"request",root.socket];stdinEnabled:true
  onStarted:{write(payload);stdinEnabled=false}
  onRunningChanged:if(!running)stdinEnabled=true
  stdout:StdioCollector {onStreamFinished:{try{root.model.accept(JSON.parse(text))}catch(e){root.model.accept({error_code:"invalid_response"})}}}
 }
 Process {id:catalogProcess;property string payload:"";command:[root.binary,"catalog",root.store];stdinEnabled:true
  onStarted:{write(payload);stdinEnabled=false}
  onRunningChanged:if(!running)stdinEnabled=true
  stdout:StdioCollector {onStreamFinished:{try{root.model.acceptCatalog(JSON.parse(text))}catch(e){root.model.acceptCatalog({error_code:"invalid_response"})}}}
 }
}
