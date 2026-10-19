import QtQuick
import "../../../modules/workbench-ui" as UI
Column {
    id:root;property var modelState;property var themeTokens;signal eventRequested(var event)
    spacing:themeTokens.metrics.gap
    UI.StyledText {width:parent.width;themeTokens:root.themeTokens;role:"subtitle";color:root.themeTokens.colors.accent;text:"01 / COMMAND OVERVIEW"}
    UI.StyledText {width:parent.width;themeTokens:root.themeTokens;role:"title";font.bold:true;text:"让工作回到一个入口。"}
    UI.StyledText {width:parent.width;themeTokens:root.themeTokens;tone:"muted";text:"工作、任务与设备状态集中呈现。建议由 MAGI 解释，决定仍然属于你。"}
    Rectangle {width:parent.width;height:status.implicitHeight+root.themeTokens.metrics.paddingY*2;color:Qt.rgba(root.themeTokens.colors.accent.r,root.themeTokens.colors.accent.g,root.themeTokens.colors.accent.b,.06);border.color:root.themeTokens.colors.accent
        Column {id:status;x:root.themeTokens.metrics.paddingX;y:root.themeTokens.metrics.paddingY;width:parent.width-x*2;spacing:root.themeTokens.metrics.gapSmall
            UI.StyledText {width:parent.width;themeTokens:root.themeTokens;role:"subtitle";text:"设备观测 / 示例"}
            UI.StyledText {objectName:"temperatureValue";width:parent.width;themeTokens:root.themeTokens;role:"title";text:"温度  "+root.modelState.observations.temperature.value+" °C"}
            UI.StyledText {objectName:"temperatureAge";width:parent.width;themeTokens:root.themeTokens;tone:"muted";text:root.modelState.observations.temperature.age+(root.modelState.observations.temperature.health==='stale'?" · 已过期，保留上次读数":" · 仅为演示，不是设备测量")}
        }
    }
    UI.ActionGrid {width:parent.width;columns:width<500?1:2;themeTokens:root.themeTokens;items:[{id:'open-work',label:'继续工作',action:'navigate',payload:'work'},{id:'open-tasks',label:'查看任务',action:'navigate',payload:'tasks'}];onTriggered:(action,payload)=>root.eventRequested({type:'navigate',id:payload})}
    UI.StyledText {width:parent.width;themeTokens:root.themeTokens;role:"subtitle";text:"AI 可选 / 原型未连接模型或外部服务"}
}
