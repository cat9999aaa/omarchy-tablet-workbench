// SPDX-License-Identifier: GPL-3.0-only
import QtQuick
import "Theme.js" as Theme
Column {
    id:root
    property var themeTokens:null
    property string label:""
    property string valueText:""
    property string statusText:""
    property var observedAt:null
    readonly property var resolved:themeTokens || Theme.resolve()
    readonly property string timeText: {
        if (typeof observedAt !== "number" || !Number.isFinite(observedAt) || observedAt < 0)
            return "采样时间未知"
        const date = new Date(observedAt * 1000)
        if (!Number.isFinite(date.getTime())) return "采样时间未知"
        return "采样（本地时间）：" + Qt.formatDateTime(date,"yyyy-MM-dd HH:mm:ss")
    }
    spacing:resolved.metrics.gapSmall
    StyledText {width:parent.width;themeTokens:root.resolved;role:"subtitle";text:root.label}
    StyledText {objectName:"readoutValue";width:parent.width;themeTokens:root.resolved;text:root.valueText;visible:text!==""}
    StyledText {objectName:"readoutStatus";width:parent.width;themeTokens:root.resolved;text:root.statusText;visible:text!==""}
    StyledText {objectName:"readoutTime";width:parent.width;themeTokens:root.resolved;role:"subtitle";tone:"muted";text:root.timeText}
}
