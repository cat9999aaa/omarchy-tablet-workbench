import QtQuick
import QtQuick.Controls
import "../../modules/workbench-ui" as UI
import "ExperienceModel.js" as Model
import "PreviewTokens.js" as Tokens
ApplicationWindow {
    id:host;visible:true;width:1280;height:800;minimumWidth:320;minimumHeight:480
    title:"DASHEN // OVERDRIVE · U1 设计原型"
    readonly property var scenes:['dashboard','desktop','windows','lock-preview']
    header:ToolBar {
        height:selectors.implicitHeight
        Flow {id:selectors;width:parent.width;spacing:4
            readonly property real cellWidth:(width-4*(width>=640?3:1))/(width>=640?4:2)
            ComboBox {id:sceneChoice;objectName:"sceneSelector";width:selectors.cellWidth;height:52;Accessible.name:"预览场景";model:['指挥台','桌面','窗口','锁屏预览'];onCurrentIndexChanged:if(experience&&currentIndex>=0)experience.scene=host.scenes[currentIndex]}
            ComboBox {id:dataChoice;objectName:"scenarioSelector";width:selectors.cellWidth;height:52;Accessible.name:"演示数据";model:['常规示例','过期示例','离线示例','缺硬件'];onCurrentIndexChanged: {
                if(experience&&currentIndex>=0) {
                    var next=Model.initialState(['normal','stale','offline','missing-device'][currentIndex]);
                    next.destination=experience.modelState.destination;
                    experience.modelState=next;
                }
            }}
            ComboBox {id:themeChoice;width:selectors.cellWidth;height:52;Accessible.name:"原型配色";model:['暗色','浅色']}
            UI.TouchButton {objectName:"exitPreview";width:selectors.cellWidth;height:52;themeTokens:experience.themeTokens;text:"退出预览";onClicked:host.close()}
        }
    }
    Experience {id:experience;objectName:"experience";anchors.fill:parent
        themeTokens:Tokens.resolve(themeChoice.currentIndex===1?{background:'#F3F0E7',foreground:'#182024',accent:'#805000',muted:'#47565C'}:{})
        modelState:Model.initialState('normal')
        onSceneChanged: {var index=host.scenes.indexOf(scene);if(index>=0&&sceneChoice.currentIndex!==index)sceneChoice.currentIndex=index}
        onEventRequested:event=>modelState=Model.reduce(modelState,event)}
}
