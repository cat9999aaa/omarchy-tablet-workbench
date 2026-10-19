import QtQuick
import "../../modules/workbench-ui" as UI
Column {
    id:root;property var themeTokens
    property string summary:"先把当前工作整理清楚，再考虑更多自动化。"
    property string evidence:"演示依据：统一入口、可恢复窗口、按需处理。这里未读取实际桌面或会议。"
    property string availability:"未接模型 · 只读建议示例"
    spacing:themeTokens.metrics.gap
    Repeater {model:[{tag:'01 / 理解',body:root.summary},{tag:'02 / 依据与边界',body:root.evidence},{tag:'03 / 下一步',body:'你可以查看工作页的窗口演示。MAGI 不修改代码、系统或权限，也不代发开发任务。'}]
        Column {required property var modelData;width:root.width;spacing:root.themeTokens.metrics.gapSmall
            UI.StyledText {width:parent.width;themeTokens:root.themeTokens;role:"subtitle";color:root.themeTokens.colors.accent;text:modelData.tag}
            UI.StyledText {width:parent.width;themeTokens:root.themeTokens;text:modelData.body}
        }
    }
    UI.StyledText {objectName:"magiAvailability";width:parent.width;themeTokens:root.themeTokens;tone:"muted";text:root.availability}
    UI.StyledText {width:parent.width;themeTokens:root.themeTokens;role:"subtitle";text:"麦克风关闭 · 无上传 · 无工具调用"}
}
