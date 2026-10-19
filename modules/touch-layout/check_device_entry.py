"""Actual entry and pinned official MouseArea; synthetic palette services only."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import tempfile
from layout_probe import block
from bar_compat import patched

here=Path(__file__).resolve().parent
official=Path(os.environ.get('U2B_OFFICIAL_ROOT','/official'))
button=(official/'Ui/WidgetButton.qml').read_text()
pins=json.loads((here/'host-source.json').read_text())
assert hashlib.sha256(button.encode()).hexdigest()==pins['Ui/WidgetButton.qml']
entry=(here.parent/'control-center/DeviceEntry.qml').read_text()
with tempfile.TemporaryDirectory(prefix='device-entry-') as temp:
    root=Path(temp);commons=root/'Commons';commons.mkdir()
    (root/'DeviceEntry.qml').write_text(entry.replace('import qs.Ui as Ui','import "." as Ui').replace('import qs.Commons','import "Commons"'))
    (root/'WidgetButton.qml').write_text(button.replace('import qs.Commons','import "Commons"'))
    (commons/'qmldir').write_text('module Commons\nsingleton Style 1.0 Style.qml\nsingleton Color 1.0 Color.qml\n')
    (commons/'Style.qml').write_text('pragma Singleton\nimport QtQuick\nQtObject {property var font:({body:12,family:"sans-serif"});property var bar:({sizeHorizontal:26});function spaceReal(n){return n} function space(n){return n}}')
    (commons/'Color.qml').write_text('pragma Singleton\nimport QtQuick\nQtObject {property var shellValues:({});property color foreground:"white";property color urgent:"orange"}')
    test_qml='''import QtQuick
import QtTest
import "Commons"
TestCase {
 id:root;visible:true;when:windowShown;name:"ActualDeviceEntry";width:300;height:200
 property int calls:0
 property var shell:null
 property var barDragTarget:null
 property bool barDragAfter:false
 function clearBarDrag(){}
 function moduleClickTargetAt(slot,x,y){return entry}
 function pressModuleClickTarget(slot,button,x,y){if(typeof entry.triggerPress!=="function")return false;entry.triggerPress(button);return true}
 function targetWindow(item){return null}
 QtObject {id:bar;property int barSize:56;property bool vertical:false;property string fontFamily:"sans-serif";property color barForeground:"white";property color urgent:"orange";property bool foregroundAnimationEnabled:false;function hideTooltip(item){} function showTooltip(item,text){} function registerClickTarget(item){} function unregisterClickTarget(item){}}
 Item {id:slot;width:entry.width;height:entry.height;property var activeItem:entry
 DeviceEntry {id:entry;bar:bar;width:Math.max(48,implicitWidth);height:bar.barSize;contextKey:"screen1";onActivated:root.calls++}
 HOST_POINTER
 }
 function init(){bar.barSize=56;entry.contextKey="screen1";calls=0;wait(1)}
 function test_centers_and_edges(){for(const p of [[24,28],[1,28],[47,28],[24,1],[24,55]]){mousePress(entry,p[0],p[1]);mouseRelease(entry,p[0],p[1]);}compare(calls,5)}
 function test_resize_cancels(){mousePress(entry,24,20);bar.barSize=70;wait(1);mouseRelease(entry,24,20);compare(calls,0)}
 function test_identity_cancels(){mousePress(entry,24,20);entry.contextKey="screen2";wait(1);mouseRelease(entry,24,20);compare(calls,0)}
 function test_drag_out_cancels(){mousePress(entry,24,20);mouseMove(entry,200,150);mouseRelease(entry,200,150);compare(calls,0)}
 function test_theme_change_cancels(){mousePress(entry,24,20);Color.shellValues={newTheme:true};wait(1);mouseRelease(entry,24,20);compare(calls,0)}
 function test_keyboard_once(){entry.forceActiveFocus();keyClick(Qt.Key_Return);compare(calls,1)}
 function test_compact_height(){bar.barSize=26;wait(1);compare(entry.implicitHeight,26)}
}
'''
    pointer=block(patched((official/'Touch/Bar.qml').read_text()),'    MouseArea {\n      id: modulePointer')
    (root/'tst_entry.qml').write_text(test_qml.replace('HOST_POINTER',pointer))
    result=subprocess.run(['/usr/lib/qt6/bin/qmltestrunner','-input',str(root/'tst_entry.qml')],capture_output=True,text=True,timeout=20)
    print(result.stdout+result.stderr);raise SystemExit(result.returncode)
