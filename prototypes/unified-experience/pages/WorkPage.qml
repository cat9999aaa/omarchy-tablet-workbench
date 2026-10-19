import QtQuick
import "../../../modules/workbench-ui" as UI
Column {
    id:root;property var modelState;property var themeTokens;signal eventRequested(var event)
    spacing:themeTokens.metrics.gap
    UI.StyledText {width:parent.width;themeTokens:root.themeTokens;role:"title";text:"应用与窗口"}
    UI.StyledText {width:parent.width;themeTokens:root.themeTokens;tone:"muted";text:"关闭一个窗口与退出整个应用是两件事。以下均为可恢复的演示状态。"}
    UI.StyledText {width:parent.width;themeTokens:root.themeTokens;visible:root.modelState.notice!=="";text:root.modelState.notice;color:root.themeTokens.colors.accent}
    Repeater {model:root.modelState.windows.length
        Rectangle {required property int index;readonly property var modelData:root.modelState.windows[index]||({id:"",title:"",workspace:"",hidden:false});width:root.width;height:info.implicitHeight+root.themeTokens.metrics.paddingY*2;color:"transparent";border.color:root.themeTokens.colors.muted
            Column {id:info;x:root.themeTokens.metrics.paddingX;y:root.themeTokens.metrics.paddingY;width:parent.width-x*2;spacing:root.themeTokens.metrics.gap
                UI.StyledText {width:parent.width;themeTokens:root.themeTokens;text:modelData.title}
                UI.StyledText {width:parent.width;themeTokens:root.themeTokens;tone:"muted";text:modelData.workspace+" · "+(modelData.hidden?"已隐藏 · 可在此恢复":"可见")}
                UI.ActionGrid {width:parent.width;columns:width<480?1:3;themeTokens:root.themeTokens
                    items:[{id:(modelData.hidden?'restore-':'hide-')+modelData.id,label:modelData.hidden?'恢复窗口':'隐藏窗口',action:modelData.hidden?'demoRestore':'demoHide',payload:modelData.id},
                        {id:'close-'+modelData.id,label:'关闭此窗口',action:'demoCloseWindow',payload:modelData.id},
                        {id:'quit-'+modelData.id,label:'退出此应用',action:'demoQuitApplication',payload:modelData.id,tone:'urgent'}]
                    onTriggered:(action,payload)=>root.eventRequested({type:action,id:payload})}

            }
        }
    }
    UI.StyledText {width:parent.width;themeTokens:root.themeTokens;tone:"muted";text:"退出应用影响它的所有示例窗口；强制结束不在本原型开放。"}
    UI.StyledText {width:parent.width;themeTokens:root.themeTokens;text:"会议记录 · 规划中"}
    UI.StyledText {width:parent.width;themeTokens:root.themeTokens;tone:"muted";text:"主动开始、按需处理。本原型不会启用麦克风。"}
}
