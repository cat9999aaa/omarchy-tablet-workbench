import QtQuick
import QtTest
import "../OutputRoute.js" as Route
TestCase {
    id:suite;name:"OutputOwnership";when:windowShown
    Component {id:slot;QtObject {
        property int routeEpoch:0
        property bool transferPending:false
        property bool opened:false
        property var callback:null
        function closeForTransfer(cb){opened=false;callback=cb}
        function requestOpen(){opened=true}
        function reaped(){const f=callback;callback=null;if(f)f()}
    }}
    function test_transfer_waits_and_old_request_cannot_open() {
        const a=createTemporaryObject(slot,suite),b=createTemporaryObject(slot,suite)
        const peers=[a,b]
        verify(Route.handoff(peers,b,()=>true));a.reaped();verify(!b.opened);b.reaped();verify(b.opened)
        verify(Route.handoff(peers,a,()=>true));const old=a.callback
        verify(Route.handoff(peers,b,()=>true));old();a.reaped();b.reaped();verify(b.opened);verify(!a.opened)
    }
    function test_removed_target_cannot_open() {
        const a=createTemporaryObject(slot,suite),b=createTemporaryObject(slot,suite)
        let present=true;Route.handoff([a,b],b,()=>present);present=false;a.reaped();b.reaped();verify(!b.opened)
    }
}
