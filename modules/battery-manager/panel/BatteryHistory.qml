import QtQuick
import Quickshell
import Quickshell.Io
import "Details.js" as Details
import "Workbench" as WB

Item {
  id: view
  property var themeTokens:null
  onThemeTokensChanged:plot.requestPaint()
  onForegroundChanged:plot.requestPaint()
  onFontFamilyChanged:plot.requestPaint()
  property bool active: false
  property color foreground: themeTokens?themeTokens.colors.foreground:"white"
  property string fontFamily: themeTokens?themeTokens.font.family:"sans-serif"
  property string helper: Quickshell.env("HOME") + "/Projects/pcadmin/tools/battery-manager/battery.py"
  property int selected: 0
  property string period: "session"
  property var statusData: ({available:false})
  property var appData: ({apps:[]})
  property var historyData: ({sessions:[],points:[]})
  readonly property var current: statusData.current_session || null
  implicitHeight: 340
  function stamp(value) { return value ? Qt.formatDateTime(new Date(value), "MM-dd HH:mm") : "未知" }
  function refresh() {
    if (!active) return
    if (!statusProc.running) statusProc.running = true
    if (selected === 1 && !appProc.running) { appProc.command=["/usr/bin/python3",helper,"apps","--period",period];appProc.running=true }
    if (selected === 2 && !historyProc.running) historyProc.running=true
  }
  onActiveChanged: if (active) refresh()
  onSelectedChanged: refresh()
  onPeriodChanged: refresh()
  Timer { interval:60000;running:view.active;repeat:true;onTriggered:view.refresh() }
  Process {
    id:statusProc;command:["/usr/bin/python3",view.helper,"status"]
    stdout:SplitParser { onRead:line=>{try{view.statusData=JSON.parse(line)}catch(e){view.statusData={available:false}}} }
    onExited:(code,status)=>{if(code!==0)view.statusData={available:false}}
  }
  Process {
    id:appProc
    stdout:SplitParser {onRead:line=>{try{view.appData=JSON.parse(line)}catch(e){view.appData={available:false,apps:[]}}}}
    onExited:(code,status)=>{if(code!==0)view.appData={available:false,apps:[]}}
  }
  Process {
    id:historyProc;command:["/usr/bin/python3",view.helper,"history","--days","7"]
    stdout:SplitParser {onRead:line=>{try{view.historyData=JSON.parse(line);plot.requestPaint()}catch(e){view.historyData={available:false,sessions:[],points:[]}}}}
    onExited:(code,status)=>{if(code!==0)view.historyData={available:false,sessions:[],points:[]}}
  }
  Column {
    anchors.fill:parent;spacing:8
    Row {
      id:tabs;width:parent.width;spacing:6
      Repeater {
        model:["本次计时","后台活动","历史"]
        delegate:Choice {
          required property string modelData
          required property int index
          width:(tabs.width-12)/3;label:modelData;chosen:view.selected===index
          onClicked:view.selected=index
        }
      }
    }
    Flickable {
      id:scroll;width:parent.width;height:parent.height-tabs.height-8
      clip:true;contentHeight:body.implicitHeight;boundsBehavior:Flickable.StopAtBounds
      Column {
        id:body;width:scroll.width;spacing:7
        Column {
          width:parent.width;spacing:7;visible:view.selected===0
          Line {text:!view.statusData.available ? "记录暂不可用；实时电量仍由系统提供" : Details.sessionLabel(view.current);font.bold:true}
          Line {visible:view.statusData.available;text:"观察开始："+view.stamp(view.current ? view.current.observed_start : null)}
          Line {visible:view.statusData.available;text:"已记录："+Details.elapsedLabel(view.current ? view.current.elapsed_s : null)+(view.statusData.stale ? " · 数据已过期" : "")}
          Line {visible:view.current && view.current.kind==="discharge";text:"运行 "+Details.elapsedLabel(view.current ? view.current.awake_s : null)+" · 休眠 "+Details.elapsedLabel(view.current ? view.current.sleep_s : null)}
          Line {visible:view.current && view.current.kind==="discharge";text:Details.screenLabel(view.current)+" · 平均 "+(view.current && view.current.average_power_w!==null ? view.current.average_power_w+"W" : "未知")}
          Repeater {
            model:["BAT0","BAT1"]
            delegate:Column {
              required property string modelData
              visible: view.statusData.available === true
              width:parent.width;spacing:3
              Line {text:modelData+"  "+Details.batteryChange(view.current,modelData)+" · "+Details.observedBatteryState((view.statusData.batteries || {})[modelData])}
              Line {visible:view.current && view.current.kind==="charge";text:"实际充电已记录："+Details.elapsedLabel(view.current ? view.current.charging_s_by_bay[modelData] : null);opacity:0.7}
            }
          }
          Line {visible:!!view.statusData.last_charge;text:"上次接电："+view.stamp(view.statusData.last_charge ? view.statusData.last_charge.observed_start : null)+" · "+Details.elapsedLabel(view.statusData.last_charge ? view.statusData.last_charge.elapsed_s : null)}
          Line {visible:!!view.statusData.last_charge;text:"BAT0 "+Details.batteryChange(view.statusData.last_charge,"BAT0")+"；BAT1 "+Details.batteryChange(view.statusData.last_charge,"BAT1")}
          Line {visible:!!view.current && (view.current.unknown_s>0 || view.current.quality_flags.length>0);text:"记录含缺口或状态边界；可确认时间之外不补算。";opacity:0.7}
          Line {text:"每分钟记录 · 观察到的插拔时间约有一分钟误差\n休眠、关机或断采样期间误差可能更长。\n充电途中开始记录，不代表实际插电时刻。";opacity:0.65}
        }
        Column {
          width:parent.width;spacing:7;visible:view.selected===1
          Row {
            width:parent.width;spacing:6
            Choice {width:(parent.width-6)/2;label:"本次";chosen:view.period==="session";onClicked:view.period="session"}
            Choice {width:(parent.width-6)/2;label:"最近24小时";chosen:view.period==="24h";onClicked:view.period="24h"}
          }
          Line {text:"CPU活动排行 · 非精确耗电\nCPU秒数可超过实际时间；短进程可能漏采。";opacity:0.7}
          Line {visible:view.appData.available===false;text:"活动记录暂不可用"}
          Line {visible:!view.appData.apps || view.appData.apps.length===0;text:"正在积累活动记录，请稍后查看"}
          Repeater {
            model:view.appData.apps || []
            delegate:Line {
              required property var modelData
              text:modelData.name+"  ·  "+Number(modelData.cpu_seconds).toFixed(1)+" CPU秒"+(modelData.background_samples>0 ? " · 曾无可见窗口" : modelData.unknown_samples>0 ? " · 窗口归属未知" : "")
            }
          }
        }
        Column {
          width:parent.width;spacing:7;visible:view.selected===2
          Line {text:"最近7天 · 电量与电池端放电功率";font.bold:true}
          Line {text:"BAT0 蓝色 · BAT1 橙色 · 功率绿色\n缺口断线；当前只有记录启动后的数据。";opacity:0.7}
          Canvas {
            id:plot;width:parent.width;height:170
            onWidthChanged:requestPaint()
            onVisibleChanged:if(visible)requestPaint()
            onPaint:{
              var ctx=getContext("2d");ctx.clearRect(0,0,width,height)
              var pts=view.historyData.points || [];if(pts.length===0)return
              var textSize=view.themeTokens?view.themeTokens.font.subtitle:11
              ctx.font=textSize+"px "+view.fontFamily
              var firstTime=view.stamp(pts[0].time)
              var lastTime=Qt.formatDateTime(new Date(pts[pts.length-1].time),"HH:mm")
              var left=Math.ceil(ctx.measureText("100%").width)+8,right=width-8,top=textSize+8
              var endWidth=ctx.measureText(lastTime).width
              var separateTimes=width>250 && left+ctx.measureText(firstTime).width+8>right-endWidth
              var footerLine=textSize+8,bottom=height-7-footerLine*(separateTimes?2:1)
              ctx.strokeStyle=Qt.rgba(view.foreground.r,view.foreground.g,view.foreground.b,0.25);ctx.lineWidth=1
              ctx.beginPath();ctx.moveTo(left,top);ctx.lineTo(left,bottom);ctx.lineTo(right,bottom);ctx.stroke()
              ctx.fillStyle=view.foreground;ctx.fillText("100%",0,top);ctx.fillText("0",left-ctx.measureText("0").width-8,bottom)
              var start=pts[0].axis_time,end=pts[pts.length-1].axis_time,span=Math.max(60000,end-start)
              var maxW=10;for(var j=0;j<pts.length;j++)if(pts[j].net_discharge_w!==null)maxW=Math.max(maxW,pts[j].net_discharge_w)
              ctx.fillText(Math.ceil(maxW)+"W 上限",left+8,top)
              var keys=["BAT0","BAT1","net_discharge_w"],colors=["#60a5fa","#f5aa55","#7adba0"]
              for(var k=0;k<3;k++){
                ctx.strokeStyle=colors[k];ctx.lineWidth=2;ctx.beginPath();var started=false
                for(var i=0;i<pts.length;i++){
                  var val=pts[i][keys[k]];if(val===null || val===undefined){started=false;continue}
                  var x=left+(pts[i].axis_time-start)/span*(right-left),y=bottom-val/(k===2 ? maxW : 100)*(bottom-top)
                  if(started)ctx.lineTo(x,y);else ctx.moveTo(x,y);started=true
                  if(pts.length===1){ctx.lineTo(x+3,y)}
                }ctx.stroke()
              }
              ctx.fillStyle=view.foreground;ctx.fillText(firstTime,left,height-7-(separateTimes?footerLine:0))
              if(width>250)ctx.fillText(lastTime,right-endWidth,height-7)
            }
          }
          Line {visible:view.historyData.available===false;text:"历史记录暂不可用"}
          Repeater {
            model:(view.historyData.sessions || []).slice().reverse()
            delegate:Line {
              required property var modelData
              text:view.stamp(modelData.observed_start)+" · "+Details.sessionLabel(modelData)+"\n"+Details.elapsedLabel(modelData.elapsed_s)+"；BAT0 "+Details.batteryChange(modelData,"BAT0")+"；BAT1 "+Details.batteryChange(modelData,"BAT1")
            }
          }
        }
      }
    }
  }
  component Line:Text {
    width:parent.width;color:view.foreground;font.family:view.fontFamily;font.pixelSize:view.themeTokens?view.themeTokens.font.body:13
    textFormat:Text.PlainText;wrapMode:Text.Wrap
  }
  component Choice:WB.TouchButton {
    themeTokens:view.themeTokens
    property string label:""
    property bool chosen:false
    text:label;selected:chosen;foreground:view.foreground;accent:view.foreground
    font.family:view.fontFamily;font.pixelSize:view.themeTokens?view.themeTokens.font.body:13
  }
}
