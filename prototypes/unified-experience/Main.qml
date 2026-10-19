import QtQuick
import QtQuick.Controls
import "ExperienceModel.js" as Model
import "PreviewTokens.js" as Tokens
ApplicationWindow {
    visible:true;width:1280;height:800;minimumWidth:320;minimumHeight:480
    title:"DASHEN // OVERDRIVE · U1 设计原型"
    Experience {anchors.fill:parent;themeTokens:Tokens.resolve();modelState:Model.initialState('normal')
        onEventRequested:event=>modelState=Model.reduce(modelState,event)}
}
