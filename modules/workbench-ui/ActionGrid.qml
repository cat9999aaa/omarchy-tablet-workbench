import QtQuick
import QtQuick.Layouts
import "Theme.js" as Theme
Column {
 id:root
 property var themeTokens:null
 property var items:[]
 property int columns:2
 property bool busy:false
 // Replace items to notify updates; deep in-place mutations are unsupported.
 property int modelRevision:0
 onItemsChanged:modelRevision++
 readonly property var resolved:themeTokens||Theme.resolve()
 readonly property string modelError:validate(items)
 signal triggered(string action,var payload)
 spacing:resolved.metrics.gap
 function validate(value) {
  // createObject properties can arrive as a QVariantList, not a JS Array.
  // JSON normalization distinguishes such lists from arbitrary array-like objects.
  if(!Array.isArray(value)) {
   try {value=JSON.parse(JSON.stringify(value))}catch(error){return "invalid-model"}
   if(!Array.isArray(value))return "invalid-model"
  }
  var ids=Object.create(null)
  for(var i=0;i<value.length;i++) {
   var item=value[i]
   if(!item||typeof item!=="object"||Array.isArray(item))return "invalid-item"
   for(var j=0;j<3;j++) {
    var key=["id","label","action"][j]
    if(typeof item[key]!=="string"||!item[key].trim())return "invalid-item"
   }
   if(ids[item.id])return "duplicate-id"
   ids[item.id]=true
   if(item.enabled!==undefined&&typeof item.enabled!=="boolean")return "invalid-item"
   if(item.selected!==undefined&&typeof item.selected!=="boolean")return "invalid-item"
   if(item.tone!==undefined&&item.tone!=="normal"&&item.tone!=="urgent")return "invalid-item"
  }
  return ""
 }
 StyledText {
  width:parent.width;visible:root.modelError!==""
  themeTokens:root.resolved;tone:"urgent";text:visible?"操作列表不可用":""
 }
 GridLayout {
  width:parent.width;columns:Math.max(1,root.columns)
  rowSpacing:root.resolved.metrics.gap;columnSpacing:root.resolved.metrics.gap
  Repeater {
   model:root.modelError===""?root.items.length:0
   TouchButton {
    required property int index
    readonly property var modelData:root.modelError===""&&index>=0&&index<root.items.length?root.items[index]:({id:"",label:"",action:"",enabled:false})
    property int pressedRevision:-1
    objectName:"action-"+modelData.id
    Layout.fillWidth:true;Layout.minimumWidth:48
    themeTokens:root.resolved;text:modelData.label
    selected:modelData.selected===true
    accent:modelData.tone==="urgent"?root.resolved.colors.urgent:root.resolved.colors.accent
    enabled:!root.busy&&root.modelError===""&&modelData.enabled!==false
    onPressed:pressedRevision=root.modelRevision
    onClicked:if(enabled&&pressedRevision===root.modelRevision)root.triggered(modelData.action,modelData.payload===undefined?null:modelData.payload)
   }
  }
 }
}
