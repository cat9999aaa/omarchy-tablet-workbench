import Quickshell
import Quickshell.Io
import Quickshell.Wayland
import QtQuick
import "EdgePolicy.js" as Policy

Item {
    id: root
    property string barPosition: ""
    property string hostPosition: ""
    onHostPositionChanged: generation++
    property bool configKnown: false
    property int generation: 0
    function hasOutput(output) {
        for (let i = 0; i < Quickshell.screens.length; i++)
            if (Quickshell.screens[i] === output) return true
        return false
    }
    function invalidate() { configKnown = false; generation++ }
    function loadConfig(text) {
        invalidate()
        try {
            const value = JSON.parse(text)
            const bar = value.bar
            if (!bar || typeof bar.id !== "string" || !bar.id
                || ["top","bottom","left","right"].indexOf(bar.position) < 0) return
            barPosition = bar.position; configKnown = true
        } catch (e) { /* Invalid or partial writes leave all capture disabled. */ }
    }
    FileView {
        id: config
        path: Quickshell.env("HOME") + "/.config/omarchy/shell.json"
        watchChanges: true
        printErrors: false
        onLoaded: root.loadConfig(text())
        onLoadFailed: root.invalidate()
        onFileChanged: { root.invalidate(); reload() }
    }
    Variants {
        model: Quickshell.screens
        delegate: Item {
            required property var modelData
            EdgeStrip { screen: modelData; edge: "top" }
            EdgeStrip { screen: modelData; edge: "bottom" }
        }
    }
    component EdgeStrip: PanelWindow {
        id: strip
        required property string edge
        readonly property bool outputValid: !!screen && screen.width > 128 && screen.height > 0
            && root.hasOutput(screen)
        readonly property bool captureEnabled: Policy.enabled(edge, root.hostPosition, root.configKnown, outputValid)
        visible: captureEnabled
        anchors { top: strip.edge === "top"; bottom: strip.edge === "bottom"; left: true; right: true }
        margins { left: 64; right: 64 }
        implicitHeight: 12
        color: "transparent"
        exclusionMode: ExclusionMode.Ignore
        WlrLayershell.namespace: "pcadmin-edge-" + edge
        WlrLayershell.layer: WlrLayer.Top
        WlrLayershell.keyboardFocus: WlrKeyboardFocus.None
        onScreenChanged: input.contextGeneration++
        Connections {
            target: root
            function onGenerationChanged() { input.contextGeneration++ }
        }
        Process { id: launch }
        Rectangle {
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.top: strip.edge === "top" ? parent.top : undefined
            anchors.bottom: strip.edge === "bottom" ? parent.bottom : undefined
            width: 72; height: 3; radius: 2; color: "#80aaaaaa"
        }
        EdgeInput {
            id: input
            anchors.fill: parent
            edge: strip.edge
            available: strip.captureEnabled
            onRouted: route => {
                if (!strip.captureEnabled || launch.running) return
                launch.command = ["python3", Qt.resolvedUrl("edge_menu.py").toString().replace(/^file:\/\//, ""), route]
                launch.running = true
            }
        }
    }
}
