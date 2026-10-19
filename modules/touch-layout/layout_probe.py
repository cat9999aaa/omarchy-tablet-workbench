"""Bounded isolated geometry probe using pinned host sections and official buttons.

External widgets are explicit text/icon/bounds inputs, never executable modules.
This probe is not physical acceptance and does not run the user's shell.
"""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import tempfile


def block(source, marker):
    start=source.index(marker);end=source.index('{',start)+1;depth=1
    while depth:
        if source[end]=='{':depth+=1
        elif source[end]=='}':depth-=1
        end+=1
    return source[start:end]


def measure_layout(config, profile, viewport, font_scale):
    if profile not in ('touch','compact') or font_scale not in (1,1.25,1.5):raise ValueError('unsupported-profile-or-scale')
    if len(viewport)!=2 or any(type(v) is not int or not 240<=v<=8192 for v in viewport):raise ValueError('invalid-viewport')
    layout=config.get('layout',{})
    if set(layout)!= {'left','center','right'} or sum(len(v) for v in layout.values())>64:raise ValueError('invalid-layout')
    ids=[]
    for group in layout.values():
        for entry in group:
            if not isinstance(entry,dict) or entry.get('kind') not in ('icon','text','fixed') or not isinstance(entry.get('id'),str):raise ValueError('invalid-entry')
            if len(entry['id'])>128 or len(entry.get('text',''))>4096:raise ValueError('entry-too-large')
            if entry['kind']=='fixed' and (type(entry.get('width')) not in (int,float) or not 0<entry['width']<=8192):raise ValueError('invalid-width')
            ids.append(entry['id'])
    if len(set(ids))!=len(ids):raise ValueError('duplicate-id')
    official=Path(os.environ.get('U2B_OFFICIAL_ROOT','/official'))
    required=['Touch/Bar.qml','Touch/BarModel.js','Ui/WidgetButton.qml','Ui/BarIconButton.qml','Ui/OpticalGlyph.qml','Commons/Style.qml','Commons/Color.qml','Commons/Util.qml','Commons/BorderGeometry.js']
    hashes=json.loads((official/'hashes.json').read_text())
    for rel in required:
        p=official/rel
        if p.is_symlink() or hashlib.sha256(p.read_bytes()).hexdigest()!=hashes.get(rel):raise ValueError('source-changed:'+rel)
    source=(official/'Touch/Bar.qml').read_text()
    panel=Path(__file__).resolve().parents[1]/'control-center/Panel.qml'
    device=block(panel.read_text(),' Ui.BarIconButton { id:barButton').replace('Ui.BarIconButton','BarIconButton').replace('bar:root.bar','bar:root.barApi')
    sections='\n'.join(block(source,m) for m in ('  component LeftModules:','  component RightModules:','  component CenterModules:','  component ModuleList:','    Component {\n      id: horizontalBar'))
    with tempfile.TemporaryDirectory(prefix='u2b-layout-') as tmp:
        path=Path(tmp);(path/'Commons').mkdir()
        for rel in required:
            if rel.startswith('Commons/'):shutil.copy2(official/rel,path/rel)
            elif rel.startswith('Ui/'):shutil.copy2(official/rel,path/Path(rel).name)
        shutil.copy2(official/'Touch/BarModel.js',path/'BarModel.js')
        (path/'Commons/qmldir').write_text('module qs.Commons\nsingleton Style 1.0 Style.qml\nsingleton Color 1.0 Color.qml\nsingleton Util 1.0 Util.qml\n')
        qml='''import QtQuick
import QtQuick.Window
import Quickshell
import "Commons"
import "BarModel.js" as BarModel
ShellRoot {
 Window {visible:true;width:VIEW_WIDTH;height:Style.bar.sizeHorizontal
 Item {
  id:root;anchors.fill:parent
  property var config:CONFIG
  property bool vertical:false
  property string centerAnchor:config.centerAnchor || ""
  property var slots:[]
  property var barApi:QtObject {
   property bool vertical:false
   property int barSize:Style.bar.sizeHorizontal
   property string fontFamily:Style.font.family
   property color barForeground:Color.foreground
   property color urgent:Color.urgent
   property bool foregroundAnimationEnabled:false
   function hideTooltip(item){}
   function showTooltip(item,text){}
   function registerClickTarget(item){}
   function unregisterClickTarget(item){}
  }
  function layoutEntries(region){return config.layout[region]}
  function entryIndex(entries,name){return BarModel.entryIndex(entries,name)}
  function entriesBefore(entries,name){return BarModel.entriesBefore(entries,name)}
  function entriesAfter(entries,name){return BarModel.entriesAfter(entries,name)}
  function findCenterAnchorEntry(){const a=layoutEntries("center");const i=entryIndex(a,centerAnchor);return i<0?null:a[i]}
  function setCenterSectionHovered(value){}
  function toggle(){}
  component CenterGestureArea:Item {}
  component ModuleSlot:Item {
   id:slot
   required property var entry
   property string region:""
   implicitWidth:loader.item?loader.item.implicitWidth:0
   implicitHeight:loader.item?loader.item.implicitHeight:0
   width:implicitWidth;height:implicitHeight
   Component.onCompleted:root.slots=root.slots.concat([slot])
   Loader {id:loader;anchors.fill:parent;sourceComponent:slot.entry&&slot.entry.primary===true?deviceButton:slot.entry&&slot.entry.kind==="text"?textButton:iconButton}
   Component {id:deviceButton;DEVICE_ENTRY}
   Component {id:iconButton;BarIconButton {bar:root.barApi;text:"▣";fixedWidth:slot.entry&&slot.entry.kind==="fixed"?slot.entry.width*Style.fontScale:Style.bar.iconSlot}}
   Component {id:textButton;WidgetButton {bar:root.barApi;text:slot.entry?slot.entry.text:""}}
  }
  Loader {anchors.fill:parent;sourceComponent:horizontalBar}
SECTIONS
 }
 }
 Timer {interval:100;running:true;onTriggered:{Style.fontBaseSize=FONT_SIZE;Style.barOverrides=TOKENS;measure.start()}}
 Timer {id:measure;interval:100;onTriggered:{
  const rows=[]
  for(let i=0;i<root.slots.length;i++) {const slot=root.slots[i];if(!slot.visible||!slot.entry||slot.width<=0)continue;const p=slot.mapToItem(root,0,0);rows.push({id:slot.entry.id,x:p.x,y:p.y,width:slot.width,height:slot.height,primary:slot.entry.primary===true})}
  console.log("U2B_GEOMETRY:"+JSON.stringify({bar_height:root.height,targets:rows}));Qt.quit()
 }}
}
'''
        qml=qml.replace('VIEW_WIDTH',str(viewport[0])).replace('CONFIG',json.dumps(config)).replace('FONT_SIZE',str(round(12*font_scale))).replace('TOKENS',json.dumps({'size-horizontal':56,'icon-slot':48} if profile=='touch' else {})).replace('SECTIONS',sections).replace('DEVICE_ENTRY',device)
        (path/'shell.qml').write_text(qml)
        env={**os.environ,'HOME':str(path/'home'),'QT_QPA_PLATFORM':'offscreen','QT_QUICK_BACKEND':'software'}
        for key in ('WAYLAND_DISPLAY','DISPLAY','DBUS_SESSION_BUS_ADDRESS','HYPRLAND_INSTANCE_SIGNATURE'):env.pop(key,None)
        result=subprocess.run(['qs','-p',str(path/'shell.qml')],capture_output=True,text=True,env=env,timeout=8)
        output=result.stdout+result.stderr
        lines=[s.split('U2B_GEOMETRY:',1)[1] for s in output.splitlines() if 'U2B_GEOMETRY:' in s]
        if result.returncode or len(lines)!=1:raise RuntimeError('layout-probe-failed:'+output[-3500:])
        receipt=json.loads(lines[0]);rows=receipt['targets']
        fits=len(rows)==len(ids) and all(0<=v['x'] and v['x']+v['width']<=viewport[0] and 0<=v['y'] and v['y']+v['height']<=receipt['bar_height'] for v in rows)
        ordered=sorted(rows,key=lambda v:v['x'])
        if any(a['x']+a['width']>b['x']+.5 for a,b in zip(ordered,ordered[1:])):fits=False
        receipt.update(fits=fits,reason='ok' if fits else 'layout-overflow',source_sha256={**{rel:hashes[rel] for rel in required},'control-center/Panel.qml':hashlib.sha256(panel.read_bytes()).hexdigest()},kind='isolated-host-layout',physical_acceptance='not-run')
        return receipt
