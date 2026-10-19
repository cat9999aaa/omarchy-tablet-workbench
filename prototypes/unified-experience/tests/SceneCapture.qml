import QtQuick
import ".."
import "../ExperienceModel.js" as Model
import "../PreviewTokens.js" as Tokens
Item {
    id:root;property string scene:"dashboard"
    Experience {id:view;anchors.fill:parent;themeTokens:Tokens.resolve();modelState:Model.initialState('normal')
        onEventRequested:event=>modelState=Model.reduce(modelState,event)}
    Component.onCompleted: {
        view.scene=root.scene==='magi'?'dashboard':root.scene;
        if(root.scene==='magi')view.modelState=Model.reduce(view.modelState,{type:'toggleMagi'});
    }
}
