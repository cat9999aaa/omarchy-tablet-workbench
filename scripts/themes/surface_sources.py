"""Extract product UI bodies; inject only synthetic device/I/O boundaries.

No replacement layouts. Official Ui and Commons remain real in the renderer.
"""
from pathlib import Path
import runpy
import shutil
from check_status_surfaces import remove_io
ROOT=Path(__file__).resolve().parents[2]


def block(source, marker):
    start=source.index(marker);end=source.index('{',start)+1;depth=1
    while depth:
        if source[end]=='{':depth+=1
        elif source[end]=='}':depth-=1
        end+=1
    return source[start:end]


def write_sources(output):
    shutil.copytree(ROOT/'modules/workbench-ui',output/'Workbench',ignore=shutil.ignore_patterns('tests','*.cjs','README.md'))
    for name in ['ControlActions.js','ControlModel.js','ContractModel.js','ContractState.qml']:
        shutil.copy2(ROOT/'modules/control-center'/name,output/name)
    for name in ['Details.js','Model.js']:
        shutil.copy2(ROOT/'modules/battery-manager/panel'/name,output/name)
    ctl=runpy.run_path(str(ROOT/'modules/control-center/check_panel_layout.py'))
    nav=runpy.run_path(str(ROOT/'modules/window-controls/test_navigation_layout.py'))
    prefix=ctl['prefix'].replace('import QtTest','import qs.Commons')
    for name,value in [('fg','Color.foreground'),('bg','Color.popups.background'),('purple','Color.accent'),('green','Color.accent'),('orange','Color.urgent')]:
        import re
        prefix=re.sub(r'property color '+name+r':"[^"]+"','property color '+name+':'+value,prefix)
    body=block(ctl['source'],'   ColumnLayout {').replace('root.data','root.snapshot')
    button=block(ctl['source'],' component CButton:')
    (output/'ControlSurface.qml').write_text(prefix+'property alias contractReadings: readings\n'+body+button+'}\n')
    prefix=nav['prefix'].replace('import QtTest','import qs.Commons').replace('property color fg:"#eeeeee"','property color fg:Color.foreground').replace('property color bg:"#202020"','property color bg:Color.popups.background')
    body=block(nav['source'],'   ColumnLayout {').replace('root.data','root.snapshot')
    (output/'NavigationSurface.qml').write_text(prefix+body+'}\n')
    # Source functions/status labels stay intact; replace unavailable host I/O only.
    network=remove_io((ROOT/'modules/network-center/TravelControls.qml').read_text()).replace('testColor.','Color.').replace('testStyle.','Style.')
    network=network.replace('Rectangle {height:1;width:parent.width;color:Color.foreground}', 'Ui.PanelSeparator {foreground:Color.foreground}')
    network='import qs.Commons\nimport qs.Ui as Ui\n'+network
    network=network.replace('id: hub','id: hub\n property var actions:[]\n QtObject {id:action;property bool running:false;property var command:[]}\n QtObject {id:entertainment;property bool running:false}',1)
    (output/'NetworkSurface.qml').write_text(network)
    history=remove_io((ROOT/'modules/battery-manager/panel/BatteryHistory.qml').read_text())
    (output/'BatteryHistory.qml').write_text(history)
    source=(ROOT/'modules/battery-manager/panel/Panel.qml').read_text()
    body=block(source,'      WB.PanelBody {').replace('UPower.','power.')
    components='\n'.join(block(source,'  component '+name+':') for name in ['InfoPair','InfoLabel','InfoValue'])
    prefix='''import QtQuick
import qs.Commons
import qs.Ui
import "Workbench" as WB
import "Workbench/Theme.js" as Theme
import "Details.js" as Details
import "Model.js" as Model
Item {
 id:root
 property var themeTokens:Theme.resolve({schemaVersion:1,foreground:Color.foreground,accent:Color.accent,fontFamily:Style.font.family,fontScale:Style.font.body/12})
 property var bar:({foreground:Color.foreground,fontFamily:Style.font.family})
 property var power:({onBattery:false,displayDevice:null,devices:{values:[]}})
 property var profiles:['power-saver','balanced','performance']
 property string activeProfile:'balanced'
 property bool cursorActive:false
 property int profileIndex:0
 property bool opened:false
 property bool charging:false
 property bool fullyCharged:false
 property bool discharging:true
 property bool batteryPresent:!!power.displayDevice
 property real batteryFraction:Model.batteryFraction(power.displayDevice)
 property color batteryFillColor:Color.foreground
 property string heroStatusText:power.displayDevice?'合成设备状态':'设备状态未知'
 property var actions:[]
 function close(){}
 function setProfile(value){actions=actions.concat([value])}
 function profileIcon(name){return Model.profileIcon(name)}
 function upowerStates(){return {Charging:1,Discharging:2,FullyCharged:4,PendingCharge:5}}
 function batteryIcon(){return Model.batteryIcon(power.displayDevice,discharging,upowerStates())}
'''
    (output/'PowerSurface.qml').write_text(prefix+body+components+'}\n')
