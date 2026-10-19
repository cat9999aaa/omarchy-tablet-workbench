import QtQuick
import "../../../modules/workbench-ui" as UI
Column {
    id:root;property var modelState;property var themeTokens;signal eventRequested(var event)
    spacing:themeTokens.metrics.gap
    UI.StyledText {width:parent.width;themeTokens:root.themeTokens;role:"title";text:"应用与窗口"}
    UI.StyledText {width:parent.width;themeTokens:root.themeTokens;tone:"muted";text:"关闭一个窗口与退出整个应用是两件事。以下均为可恢复的演示状态。"}
    Repeater {model:root.modelState.windows
        Rectangle {required property var modelData;width:root.width;height:info.implicitHeight+root.themeTokens.metrics.paddingY*2;color:"transparent";border.color:root.themeTokens.colors.muted
            Column {id:info;x:root.themeTokens.metrics.paddingX;y:root.themeTokens.metrics.paddingY;width:parent.width-x*2;spacing:root.themeTokens.metrics.gap
                UI.StyledText {width:parent.width;themeTokens:root.themeTokens;text:modelData.title}
                UI.StyledText {width:parent.width;themeTokens:root.themeTokens;tone:"muted";text:modelData.workspace+" · "+(modelData.hidden?"已隐藏":"可见")}
            }
        }
    }
    UI.StyledText {width:parent.width;themeTokens:root.themeTokens;text:"会议记录 · 规划中"}
    UI.StyledText {width:parent.width;themeTokens:root.themeTokens;tone:"muted";text:"主动开始、按需处理。本原型不会启用麦克风。"}
}
