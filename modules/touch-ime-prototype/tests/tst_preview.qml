import QtQuick
import QtTest
import "../qml"

Item {
    width: 440; height: 120
    VoicePreview { id: preview; width: 350; height: 95; value: "语音长句测试。".repeat(150) }
    TestCase {
        name: "VoicePreview"; when: windowShown
        function test_long_text_scrolls() {
            verify(preview.contentHeight > preview.height)
            preview.scrollToEnd()
            verify(preview.scrollPosition > 0)
        }
        function test_short_text_fits() {
            preview.value = "你好"
            wait(30)
            verify(preview.contentHeight < preview.height)
        }
    }
}
