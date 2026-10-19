import QtQuick
import QtTest
TestCase {
    id:test;name:"UnifiedCapture";when:windowShown;visible:true;width:1536;height:1536
    function test_captureScenarios_data() {
        var rows=[];for(var scene of ['desktop','dashboard','windows','lock-preview'])for(var size of [[1536,864],[864,1536]])
            rows.push({tag:scene+'-'+size.join('x'),scene:scene,w:size[0],h:size[1]});
        rows.push({tag:'magi-1536x864',scene:'magi',w:1536,h:864});
        rows.push({tag:'narrow-320x640',scene:'dashboard',w:320,h:640});
        return rows;
    }
    function test_captureScenarios(row) {
        var c=Qt.createComponent('SceneCapture.qml');compare(c.status,Component.Ready,c.errorString());
        var o=c.createObject(test,{width:row.w,height:row.h,scene:row.scene});verify(o!==null);wait(100);
        var saved=false;verify(o.grabToImage(function(image){saved=image.saveToFile('/evidence/u1-'+row.tag+'.png')}));
        tryVerify(function(){return saved},3000);o.destroy();
    }
    function test_entrypointSelection() {
        var c=Qt.createComponent('../Main.qml');compare(c.status,Component.Ready,c.errorString());
        var o=c.createObject(null,{visible:false});verify(o!==null);
        var scene=findChild(o,'sceneSelector');verify(scene!==null);scene.currentIndex=3;
        compare(findChild(o,'experience').scene,'lock-preview');
        var data=findChild(o,'scenarioSelector');verify(data!==null);data.currentIndex=2;
        compare(findChild(o,'experience').modelState.network,'离线演示');o.destroy();
    }
}
