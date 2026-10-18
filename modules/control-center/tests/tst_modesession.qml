import QtQuick
import QtTest
import "../ModeProtocol.js" as Protocol
TestCase {
    name:"ModeProtocolQt";when:windowShown
    function test_ready_order_and_bounded_buffer() {
        const ready='{"schema_version":1,"event":"ready","seq":0}\n'
        const changed='{"schema_version":1,"event":"changed","seq":1}\n'
        verify(!Protocol.feed("",changed,-1).valid)
        const first=Protocol.feed("",ready,-1);verify(first.valid);compare(first.events[0],"ready")
        const second=Protocol.feed(first.buffer,changed,first.seq);verify(second.valid);compare(second.seq,1)
        verify(!Protocol.feed(second.buffer,changed,second.seq).valid)
        verify(!Protocol.feed("","x".repeat(257),-1).valid)
        verify(!Protocol.feed("","x".repeat(4097),-1).valid)
    }
    function test_lost_terminal_and_generation_restart() {
        const lost='{"schema_version":1,"event":"lost","seq":2}\n'
        verify(Protocol.feed("",lost,1).valid)
        verify(!Protocol.feed("",lost+'{"schema_version":1,"event":"changed","seq":3}\n',1).valid)
        verify(!Protocol.feed("",lost,-1).valid)
    }
}
