import QtQuick
import QtQuick.Controls
import qs.Ui as Ui
import qs.Commons

// Official bar rendering, with one native button owning input and cancellation.
AbstractButton {
    id: entry
    property var bar: null
    property var contextKey: null
    readonly property string contextGeometry: contextKey && typeof contextKey === "object"
        ? [contextKey.width, contextKey.height, contextKey.devicePixelRatio].join(":") : ""
    readonly property var themeKey: Color.shellValues
    property int epoch: 0
    property int pressEpoch: -1
    property var registeredBar: null
    signal activated()
    text: "设备"
    implicitWidth: Math.max(visual.barSize, visual.implicitWidth)
    implicitHeight: visual.implicitHeight
    padding: 0
    activeFocusOnTab: true
    function cancelPendingPress() { epoch++ }
    function capturePressIdentity() { return epoch }
    // The existing bar owns drag/reorder input and calls this after identity checks.
    function triggerPress(button) { if (enabled && button === Qt.LeftButton) activated() }
    function syncRegistration() {
        if (registeredBar && registeredBar.unregisterClickTarget) registeredBar.unregisterClickTarget(entry)
        registeredBar = bar
        if (registeredBar && registeredBar.registerClickTarget) registeredBar.registerClickTarget(entry)
    }
    onContextKeyChanged: cancelPendingPress()
    onContextGeometryChanged: cancelPendingPress()
    onThemeKeyChanged: cancelPendingPress()
    onBarChanged: { cancelPendingPress(); syncRegistration() }
    Component.onCompleted: syncRegistration()
    Component.onDestruction: if (registeredBar && registeredBar.unregisterClickTarget) registeredBar.unregisterClickTarget(entry)
    onWidthChanged: cancelPendingPress()
    onHeightChanged: cancelPendingPress()
    onPressedChanged: if (pressed) pressEpoch = epoch
    onClicked: if (pressEpoch === epoch) activated()
    contentItem: Ui.WidgetButton {
        id: visual
        bar: entry.bar
        text: entry.text
        tooltipText: "设备控制台"
        interactive: false
        onFontSizeChanged: entry.cancelPendingPress()
    }
    background: Rectangle {
        color: visual.foreground
        opacity: entry.down ? 0.12 : 0
    }
    Keys.onPressed: event => {
        if (enabled && !event.isAutoRepeat
            && (event.key === Qt.Key_Return || event.key === Qt.Key_Enter)) {
            event.accepted = true
            activated()
        }
    }
}
