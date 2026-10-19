import QtQuick
import QtTest
import "../ExperienceModel.js" as Model
import "../PreviewTokens.js" as Tokens
TestCase {
    id:test; name:"UnifiedExperience"; when:windowShown; visible:true; width:1536;height:1536
    function make(w,h,scale,scenario) {
        var c=Qt.createComponent('../Experience.qml');compare(c.status,Component.Ready,c.errorString());
        var o=c.createObject(test,{width:w||1280,height:h||800,themeTokens:Tokens.resolve({fontScale:scale||1}),modelState:Model.initialState(scenario||'normal')});
        verify(o!==null);o.eventRequested.connect(function(e){o.modelState=Model.reduce(o.modelState,e)});wait(30);return o;
    }
    function reachable(o,item) {
        verify(item!==null);verify(item.visible);var pos=item.mapToItem(o,0,0);
        verify(pos.x>=0&&pos.y>=0,'negative position '+item.objectName);
        verify(pos.x+item.width<=o.width+1&&pos.y+item.height<=o.height+1,'outside '+item.objectName);
    }
    function test_navigationUnique() {
        var o=make();
        for(var d of Model.destinations()) {var b=findChild(o,'action-nav-'+d.id);verify(b!==null);mouseClick(b,b.width/2,b.height/2);compare(o.modelState.destination,d.id)}
        o.destroy();
    }
    function test_narrowCloseReachable_data() {
        var rows=[];for(var size of [[320,640],[480,800],[864,1536],[1536,864]])for(var scale of [1,1.25,1.5])
            rows.push({tag:size.join('x')+'-'+scale,w:size[0],h:size[1],scale:scale});return rows;
    }
    function test_narrowCloseReachable(row) {
        var o=make(row.w,row.h,row.scale);
        reachable(o,findChild(o,'prototypeNotice'));reachable(o,findChild(o,'workbenchClose'));
        var b=findChild(o,'workbenchClose');mouseClick(b,b.width/2,b.height/2);verify(!o.dashboardOpen);
        b=findChild(o,'dashboardEntry');reachable(o,b);mouseClick(b,b.width/2,b.height/2);verify(o.dashboardOpen);
        o.destroy();
    }
    function test_fontScaleOverflow() {
        var o=make(320,640,1.5);o.modelState=Model.reduce(o.modelState,{type:'navigate',id:'work'});wait(30);
        var scroll=findChild(o,'workbenchScroll');verify(scroll.contentHeight>scroll.height);
        scroll.contentY=scroll.contentHeight-scroll.height;wait(20);reachable(o,findChild(o,'workbenchClose'));o.destroy();
    }
    function test_stalePreservesValue() {
        var o=make(960,800,1,'stale');var value=findChild(o,'temperatureValue');verify(value.text.indexOf('48')>=0);
        verify(findChild(o,'temperatureAge').text.indexOf('过期')>=0);o.destroy();
    }
    function test_unknownCapability() {
        var o=make(960,800,1,'missing-device');o.modelState=Model.reduce(o.modelState,{type:'navigate',id:'device'});wait(20);
        verify(findChild(o,'capability-light').text.indexOf('不支持')>=0);o.destroy();
    }
}
