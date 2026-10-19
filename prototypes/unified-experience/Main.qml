import QtQuick
import QtQuick.Controls
import "ExperienceModel.js" as Model
import "PreviewTokens.js" as Tokens
ApplicationWindow {
    id:host;visible:true;width:1280;height:800;minimumWidth:320;minimumHeight:480
    title:"DASHEN // OVERDRIVE · U1 设计原型"
    header:ToolBar {
        height:52
        Row {anchors.fill:parent;spacing:4
            ComboBox {id:sceneChoice;objectName:"sceneSelector";width:(parent.width-8)/3;height:52;Accessible.name:"预览场景";model:['指挥台','桌面','窗口','锁屏预览'];onActivated:experience.scene=['dashboard','desktop','windows','lock-preview'][currentIndex]}
            ComboBox {id:dataChoice;objectName:"scenarioSelector";width:(parent.width-8)/3;height:52;Accessible.name:"演示数据";model:['常规示例','过期示例','离线示例','缺硬件'];onCurrentIndexChanged:if(experience)experience.modelState=Model.initialState(['normal','stale','offline','missing-device'][currentIndex])}
            ComboBox {id:themeChoice;width:(parent.width-8)/3;height:52;Accessible.name:"原型配色";model:['暗色','浅色']}
        }
    }
    Experience {id:experience;objectName:"experience";anchors.fill:parent
        scene:['dashboard','desktop','windows','lock-preview'][sceneChoice.currentIndex]
        themeTokens:Tokens.resolve(themeChoice.currentIndex===1?{background:'#F3F0E7',foreground:'#182024',accent:'#805000',muted:'#47565C'}:{})
        modelState:Model.initialState('normal')
        onEventRequested:event=>modelState=Model.reduce(modelState,event)}
}
