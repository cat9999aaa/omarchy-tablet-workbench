"""Render actual network/history content with synthetic state and no I/O.

Process/Timer blocks and official separator are replaced at the environment
boundary; this is a component-state test, not official Shell integration.
"""
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]


def remove_io(source):
    for kind in ('Process', 'Timer'):
        while (match := re.search(r'\b'+kind+r'\s*\{',source)):
            end=match.end();depth=1
            while depth:
                if source[end]=='{':depth+=1
                elif source[end]=='}':depth-=1
                end+=1
            source=source[:match.start()]+source[end:]
    source='\n'.join(line for line in source.splitlines() if not line.startswith(('import Quickshell','import qs.')) and 'property string helper:' not in line)
    return source.replace('Color.','testColor.').replace('Style.','testStyle.').replace('Ui.PanelSeparator {foreground:testColor.foreground}', 'Rectangle {height:1;width:parent.width;color:testColor.foreground}')


ENV = '''
 width:480;height:640
 QtObject {id:testColor;property color foreground:'#e7e9df';property color accent:'#ffb454';property color muted:'#99a6af';property color urgent:'#ff6778';property var popups:({background:'#0c1014'})}
 QtObject {id:testStyle;property var font:({family:'sans-serif',body:12});property int cornerRadius:8;function space(n){return n}}
'''
NETWORK = '''
 QtObject {id:action;property bool running:false;property var command:[]}
 QtObject {id:entertainment;property bool running:false}
 TestCase {
  name:'NetworkThemeState';when:windowShown
  function findButtons(item,out){if(item.minimumTouchHeight!==undefined)out.push(item);for(const child of item.children)findButtons(child,out)}
  function test_theme_keeps_unknown_and_confirmation() {
   verify('themeTokens' in hub,'network themeTokens API missing');hub.observedAt=100;hub.now=100;hub.selectedTab='cell';hub.confirmFlight=true
   const snapshot={wifi_enabled:false,wwan:true,signal:null,traffic:{day:null,month:null},policy:{proxy_enabled:false,mode:'auto'},health:{internet:'unknown'},wifi_connection:'合成中文网络'.repeat(20)}
   hub.state=snapshot;const oldState=hub.state
   verify(hub.page.info.indexOf('信号：未知')>=0);verify(hub.proxyState.indexOf('已手动关闭')>=0)
   for(const [health,label] of [['unknown','检测中'],['stale','检测中'],['unavailable','未联网'],['failed','联网检测失败'],['ok','可上网']]) {
    snapshot.health={internet:health};hub.state=Object.assign({},snapshot)
    compare(hub.internetState,label);const page=JSON.stringify(hub.page);testStyle.font={family:'sans-serif',body:18};testColor.accent='#00ffff';hub.themeTokens=Theme.resolve({schemaVersion:1,fontScale:1.5,foreground:testColor.foreground,accent:testColor.accent});wait(10)
    compare(JSON.stringify(hub.page),page);compare(hub.selectedTab,'cell');verify(hub.confirmFlight);verify(!action.running)
   }
   let buttons=[];findButtons(hub,buttons);verify(buttons.length>0);compare(buttons[0].font.pixelSize,24)
   body.contentY=100;wait(10);const position=body.contentY;verify(position>0);hub.themeTokens=Theme.resolve({schemaVersion:1,fontScale:1.5,foreground:'#ffffff',accent:'#ffb454'});wait(10);compare(body.contentY,position);compare(hub.selectedTab,'cell');verify(hub.confirmFlight);
   hub.now=200;verify(!hub.stateFresh);compare(hub.page.status,'待读取')
  }
 }
'''
BATTERY = '''
 TestCase {
  name:'BatteryThemeState';when:windowShown
  function texts(item,out){if(item.text!==undefined)out.push(item);for(const child of item.children)texts(child,out)}
  function test_theme_keeps_missing_bays_tabs_and_scroll() {
   verify('themeTokens' in view,'history themeTokens API missing')
   view.statusData={available:true,batteries:{},current_session:null};view.selected=0;wait(10)
   let labels=[];texts(view,labels);verify(labels.some(x=>x.text.indexOf('BAT0')>=0));verify(labels.some(x=>x.text.indexOf('未知')>=0))
   const snapshot=view.statusData;view.selected=1;view.appData={available:false,apps:[]}
   view.themeTokens=Theme.resolve({schemaVersion:1,fontScale:1.5,foreground:'#e7e9df',accent:'#ffb454'});wait(10)
   compare(view.statusData,snapshot);compare(view.selected,1);compare(view.current,null)
   labels=[];texts(view,labels);const message=labels.find(x=>x.text==='活动记录暂不可用');verify(message!==undefined);compare(message.font.pixelSize,24)
   view.selected=2;view.historyData={available:false,sessions:Array.from({length:40},()=>({kind:'discharge',elapsed_s:100,observed_start:null,start_percent_by_bay:{BAT0:null,BAT1:null},end_percent_by_bay:{BAT0:null,BAT1:null}})),points:[]};wait(10);scroll.contentY=100;wait(10);verify(scroll.contentY>0)
   const position=scroll.contentY;view.themeTokens=Theme.resolve({schemaVersion:1,fontScale:1.5,foreground:'#ffffff',accent:'#00ffff'});wait(10)
   compare(view.selected,2);compare(scroll.contentY,position);compare(view.historyData.points.length,0)
  }
 }
'''


def main():
    runner=shutil.which('qmltestrunner') or '/usr/lib/qt6/bin/qmltestrunner'
    with tempfile.TemporaryDirectory(prefix='status-theme-') as tmp:
        out=Path(tmp)
        shutil.copytree(ROOT/'modules/workbench-ui',out/'Workbench',ignore=shutil.ignore_patterns('tests','*.cjs','README.md'))
        shutil.copyfile(ROOT/'modules/battery-manager/panel/Details.js',out/'Details.js')
        for name,path,tests in [('network','modules/network-center/TravelControls.qml',NETWORK),('battery','modules/battery-manager/panel/BatteryHistory.qml',BATTERY)]:
            source=remove_io((ROOT/path).read_text())
            source='import QtTest\nimport "Workbench/Theme.js" as Theme\n'+source
            start=source.index('Item {')+len('Item {')
            source=source[:start]+ENV+source[start:]
            source=source.rstrip()[:-1]+tests+'}\n'
            (out/f'tst_{name}.qml').write_text(source)
        subprocess.run([runner,'-platform','offscreen','-input',str(out)],check=True)

if __name__=='__main__':main()
