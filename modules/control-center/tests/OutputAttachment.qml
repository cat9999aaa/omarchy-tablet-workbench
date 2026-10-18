// SPDX-License-Identifier: GPL-3.0-only
import QtQuick
import Quickshell
import "OutputRoute.js" as Route

ShellRoot {
    id: test
    property var slots: []
    property var removedSlot: null
    property var remainingSlot: null
    property string removedName: ""
    property int phase: 0
    function check(ok, label) {
        if (!ok) { console.log("B2_FAIL:" + label); Qt.quit(); return false; }
        console.log("B2_PASS:" + label); return true;
    }
    function candidates() {
        return slots.filter(s => s !== null).map(s => ({id:s.slotId,
            screenName:s.boundScreen ? s.boundScreen.name : "",
            attached:s.boundScreen !== null, visibleSlot:s.width > 0 && s.height > 0}));
    }
    Component {
        id: extraSlot
        Item {
            width: 48; height: 48
            property string slotId: "duplicate"
            readonly property var boundScreen: {
                const w = this.QsWindow.window;
                return w && Quickshell.screens.indexOf(w.screen) >= 0 ? w.screen : null;
            }
        }
    }
    Variants {
        model: Quickshell.screens
        PanelWindow {
            id: window
            required property var modelData
            screen: modelData
            anchors { top: true; left: true; right: true }
            implicitHeight: 48
            Item {
                id: slot
                anchors.fill: parent
                property string slotId: modelData.name
                readonly property var boundScreen: {
                    const w = slot.QsWindow.window;
                    return w && Quickshell.screens.indexOf(w.screen) >= 0 ? w.screen : null;
                }
                Component.onCompleted: test.slots = test.slots.concat([slot])
            }
        }
    }
    Timer {
        interval: 100; running: true; repeat: true
        onTriggered: {
            const live = test.slots.filter(s => s !== null && s.boundScreen !== null);
            if(test.phase === 0 && live.length === 2) {
                if (!test.check(live.every(s => s.boundScreen.name === s.slotId), "attachment")) return;
                if (!test.check(live[0].boundScreen !== live[1].boundScreen, "two-outputs")) return;
                test.removedSlot = live.find(s => s.boundScreen.name === "HEADLESS-2");
                test.remainingSlot = live.find(s => s.boundScreen.name === "HEADLESS-1");
                if (!test.removedSlot || !test.remainingSlot) { test.check(false,"output-names"); return; }
                const duplicate = extraSlot.createObject(live[0].parent);
                if (!test.check(duplicate.boundScreen === live[0].boundScreen,"duplicate-attachment")) return;
                test.slots = test.slots.concat([duplicate]);
                if (!test.check(Route.pickTarget(test.candidates(),live[0].boundScreen.name) === null,"ambiguous")) return;
                duplicate.destroy();
                test.phase = 1;
                console.log("B2_READY_REMOVE");
            } else if(test.phase === 1 && Quickshell.screens.length === 1) {
                if (!test.check(test.removedSlot === null || test.removedSlot.boundScreen === null,"destroy")) return;
                if (!test.check(test.remainingSlot !== null && test.remainingSlot.boundScreen.name === "HEADLESS-1","no-migration")) return;
                console.log("B2_COMPLETE"); Qt.quit();
            }
        }
    }
    Timer { interval: 12000; running: true; onTriggered: { console.log("B2_FAIL:timeout"); Qt.quit(); } }
}
