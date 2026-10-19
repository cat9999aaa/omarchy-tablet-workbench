import QtQuick
import QtTest
import ".."
TestCase {
    id:test
    name:"EdgeInputOwnership"
    visible:true;width:300;height:300;when:windowShown
    property int routes:0
    EdgeInput {id:input;width:300;height:300;edge:"top";onRouted: test.routes++}
    function init(){input.available=true;input.contextGeneration++;routes=0}
    function test_pressed_then_disabled(){
        mousePress(input,100,20);verify(input.pressed);input.available=false;wait(1)
        mouseRelease(input,100,150);compare(routes,0);verify(!input.enabled)
    }
    function test_output_removed_no_route(){
        mousePress(input,100,20);verify(input.pressed);input.contextGeneration++;input.available=false
        mouseRelease(input,100,150);compare(routes,0)
    }
    function test_configuration_changed_cancels(){
        mousePress(input,100,20);verify(input.pressed);input.contextGeneration++
        mouseRelease(input,100,150);compare(routes,0)
    }
    function test_valid_once(){verify(input.visible); verify(input.enabled); mousePress(input,100,20); verify(input.pressed);compare(input.pressedGeneration,input.contextGeneration);mouseRelease(input,100,150);compare(routes,1)}
}
