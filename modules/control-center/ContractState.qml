import QtQuick
import "ContractModel.js" as Model

QtObject {
    property bool sessionOpen: false
    property int generation: 0
    property int requestSequence: 0
    property string pendingToken: ""
    property bool ready: false
    property string temperatureText: "状态暂不可用"
    property string touchText: "状态暂不可用"
    property var touchValue: null
    property string bootDefaultLabel: "未知"
    property var legacy: ({})
    function invalidate(label) {
        ready = false; temperatureText = label; touchText = label
        touchValue = null; bootDefaultLabel = "未知"
    }
    function beginOpen() {
        generation++; sessionOpen = true; pendingToken = ""; legacy = ({})
        invalidate("读取中")
    }
    function closeSession() {
        generation++; sessionOpen = false; pendingToken = ""; legacy = ({})
        invalidate("状态暂不可用")
    }
    function startRequest() {
        if (!sessionOpen || pendingToken !== "") return null
        requestSequence++; pendingToken = String(generation) + ":" + String(requestSequence)
        invalidate("读取中")
        return pendingToken
    }
    function current(token) { return sessionOpen && typeof token === "string" && token !== "" && token === pendingToken }
    function fail(token, code) {
        if (!current(token)) return
        pendingToken = ""; invalidate("状态暂不可用")
    }
    function accept(token, response) {
        if (!current(token)) return false
        if (!response || !response.legacy || response.legacy.locked !== false) {
            closeSession(); return false
        }
        const value = Model.snapshot(response)
        if (!value.valid) { fail(token, "invalid_response"); return false }
        pendingToken = ""; legacy = value.legacy; ready = value.ready
        if (ready) {
            temperatureText = value.temperature.label; touchText = value.touch.label
            touchValue = value.touch.known ? value.touch.value : null
            bootDefaultLabel = value.touch.bootDefaultLabel
        } else invalidate("状态暂不可用")
        return true
    }
    function finish(token, text, exitCode, complete) {
        if (!current(token)) return false
        if (exitCode !== 0 || complete !== true || typeof text !== "string" || Model.utf8Size(text) > 65536) {
            fail(token, "read_failed"); return false
        }
        try { return accept(token, JSON.parse(text)) }
        catch (e) { fail(token, "invalid_json"); return false }
    }
}
