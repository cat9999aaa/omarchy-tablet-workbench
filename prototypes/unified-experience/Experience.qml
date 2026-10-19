import QtQuick
import "../../modules/workbench-ui" as UI
import "ExperienceModel.js" as Model
import "PreviewTokens.js" as Tokens
import "pages"
Rectangle {
    id:root
    property var modelState:Model.initialState('normal')
    property var themeTokens:Tokens.resolve()
    property bool dashboardOpen:true
    property bool navigationOpen:false
    property string scene:"dashboard"
    readonly property bool narrow:width<themeTokens.preview.narrowBreakpoint
    readonly property real inset:themeTokens.metrics.paddingX
    signal eventRequested(var event)
    readonly property color accentColor:themeTokens.colors.accent
    onSceneChanged: {
        dashboardOpen=scene==='dashboard'||scene==='windows';navigationOpen=false;
        if(scene==='windows')eventRequested({type:'navigate',id:'work'});
    }
    color:themeTokens.colors.background
    Image {anchors.fill:parent;source:"assets/wallpaper.svg";fillMode:Image.PreserveAspectCrop;opacity:.65}

    function navItems() {return Model.destinations().map(function(d,i){return {id:'nav-'+d.id,label:'0'+(i+1)+'  '+d.label,action:'navigate',payload:d.id,selected:root.modelState.destination===d.id}})}
    Column {
        id:top; x:root.inset;y:root.inset;width:parent.width-root.inset*2;spacing:root.themeTokens.metrics.gapSmall
        UI.StyledText {objectName:"prototypeNotice";width:parent.width;themeTokens:root.themeTokens;role:"subtitle";text:"设计原型 · 演示数据 · 不操作系统";color:root.themeTokens.colors.accent}
        UI.StyledText {width:parent.width;themeTokens:root.themeTokens;role:"title";font.bold:true;text:root.narrow?"DASHEN // OVERDRIVE":"DASHEN // OVERDRIVE     大神 · 超频计划"}
    }
    Item {
        id:body;x:root.inset;y:top.y+top.height+root.themeTokens.metrics.gap
        width:parent.width-root.inset*2;height:Math.max(0,bar.y-y-root.themeTokens.metrics.gap)
        visible:root.dashboardOpen
        Rectangle {
            id:sidebar;width:root.narrow?0:root.themeTokens.preview.navigationWidth;height:parent.height
            visible:!root.narrow;color:Qt.rgba(root.accentColor.r,root.accentColor.g,root.accentColor.b,.04)
            border.color:root.themeTokens.colors.muted;border.width:1
            Flickable {anchors.fill:parent;anchors.margins:root.inset;clip:true;contentHeight:nav.implicitHeight;contentWidth:width
                UI.ActionGrid {id:nav;width:parent.width;columns:1;themeTokens:root.themeTokens;items:root.narrow?[]:root.navItems()
                    onTriggered:(action,payload)=>root.eventRequested({type:'navigate',id:payload})}
            }
        }
        Item {
            id:main;x:root.narrow?0:sidebar.width+root.themeTokens.metrics.gap;width:parent.width-x;height:parent.height
            UI.TouchButton {id:menu;objectName:"categoryButton";visible:root.narrow;width:parent.width;height:visible?Math.max(48,implicitHeight):0;themeTokens:root.themeTokens;text:root.navigationOpen?"返回内容":"分类 · "+Model.destinations().filter(d=>d.id===root.modelState.destination)[0].label
                onClicked:root.navigationOpen=!root.navigationOpen}
            Rectangle {
                id:surface;y:menu.height+(root.narrow?root.themeTokens.metrics.gap:0);width:parent.width;height:Math.max(0,parent.height-y)
                color:root.themeTokens.colors.background;border.color:root.themeTokens.colors.muted;border.width:1
                UI.PanelBody {
                    id:panel;anchors.fill:parent;anchors.margins:root.inset;themeTokens:root.themeTokens
                    title:Model.destinations().filter(d=>d.id===root.modelState.destination)[0].label
                    subtitle:"一个入口 · 明确状态 · 可控操作"
                    onCloseRequested:root.dashboardOpen=false
                    OverviewPage {width:parent.width;visible:root.modelState.destination==='overview';height:visible?implicitHeight:0;modelState:root.modelState;themeTokens:root.themeTokens;onEventRequested:event=>root.eventRequested(event)}
                    WorkPage {width:parent.width;visible:root.modelState.destination==='work';height:visible?implicitHeight:0;modelState:root.modelState;themeTokens:root.themeTokens;onEventRequested:event=>root.eventRequested(event)}
                    CollectionPage {width:parent.width;visible:['overview','work'].indexOf(root.modelState.destination)<0;height:visible?implicitHeight:0;modelState:root.modelState;themeTokens:root.themeTokens;onEventRequested:event=>root.eventRequested(event)}
                }
            }
            Rectangle {visible:root.narrow&&root.navigationOpen;z:3;y:surface.y;width:parent.width;height:surface.height;color:root.themeTokens.colors.background;border.color:root.themeTokens.colors.accent
                Flickable {anchors.fill:parent;anchors.margins:root.inset;contentWidth:width;contentHeight:mobileNav.implicitHeight;clip:true
                    UI.ActionGrid {id:mobileNav;width:parent.width;columns:1;themeTokens:root.themeTokens;items:root.narrow?root.navItems():[]
                        onTriggered:(action,payload)=>{root.eventRequested({type:'navigate',id:payload});root.navigationOpen=false}}
                }
            }
        }
    }
    Column {visible:!root.dashboardOpen&&root.scene!=='lock-preview';x:root.inset*2;y:top.y+top.height+60;width:parent.width-root.inset*4;spacing:root.themeTokens.metrics.gap
        UI.StyledText {width:parent.width;themeTokens:root.themeTokens;role:"subtitle";color:root.themeTokens.colors.accent;text:"DESIGN STUDY / U1"}
        UI.StyledText {width:parent.width;themeTokens:root.themeTokens;role:"title";font.pixelSize:root.narrow?32:56;font.bold:true;text:"工作由你掌控。"}
        UI.StyledText {width:Math.min(parent.width,540);themeTokens:root.themeTokens;text:"一个工作界面。清晰的能力边界。\n属于开发者的原生指挥中心。"}
        UI.StyledText {width:Math.min(parent.width,540);themeTokens:root.themeTokens;tone:"muted";text:"使用底部「指挥台」返回。壁纸为原创几何设计，当前没有更改你的桌面。"}
    }
    Column {visible:root.scene==='lock-preview';x:root.inset*2;y:top.y+top.height+40;width:parent.width-root.inset*4;spacing:root.themeTokens.metrics.gap
        UI.StyledText {width:parent.width;themeTokens:root.themeTokens;role:"subtitle";text:"LOCK SCREEN / VISUAL STUDY";color:root.themeTokens.colors.accent}
        UI.StyledText {width:parent.width;themeTokens:root.themeTokens;role:"title";font.pixelSize:root.narrow?48:88;text:"13:30"}
        UI.StyledText {width:parent.width;themeTokens:root.themeTokens;text:"时间示例 · 工作可以暂时停下。"}
        UI.StyledText {objectName:"lockPreviewNotice";width:parent.width;themeTokens:root.themeTokens;tone:"muted";text:"不是真实锁屏 · 无认证能力\n不收集密码，也不改变你的解锁方式。"}
    }
    Rectangle {
        id:magiSurface;visible:root.modelState.magiOpen;z:5
        x:root.narrow?root.inset:root.width*.55;y:body.y;width:root.width-x-root.inset;height:body.height
        color:root.themeTokens.colors.background;border.color:root.themeTokens.colors.accent;border.width:2
        UI.PanelBody {objectName:"magiPanel";anchors.fill:parent;anchors.margins:root.inset;themeTokens:root.themeTokens;title:"MAGI";subtitle:"建议有依据，操作有边界"
            onCloseRequested:root.eventRequested({type:'toggleMagi'})
            MagiPane {width:parent.width;themeTokens:root.themeTokens}
        }
    }
    Rectangle {
        id:bar;x:root.inset;y:root.height-height-root.inset;width:root.width-root.inset*2;height:Math.max(root.themeTokens.preview.barHeight,entry.implicitHeight)
        color:root.themeTokens.colors.background;border.color:root.themeTokens.colors.accent
        UI.TouchButton {id:entry;objectName:"dashboardEntry";anchors.left:parent.left;anchors.top:parent.top;anchors.bottom:parent.bottom;width:parent.width/2-root.themeTokens.metrics.gapSmall;themeTokens:root.themeTokens;text:"指挥台";selected:root.dashboardOpen;onClicked:{if(root.scene==='desktop'||root.scene==='lock-preview'){root.scene='dashboard';root.dashboardOpen=true}else root.dashboardOpen=!root.dashboardOpen}}
        UI.TouchButton {objectName:"magiEntry";anchors.right:parent.right;anchors.top:parent.top;anchors.bottom:parent.bottom;width:parent.width/2-root.themeTokens.metrics.gapSmall;themeTokens:root.themeTokens;text:"MAGI";onClicked:root.eventRequested({type:'toggleMagi'})}
    }
}
