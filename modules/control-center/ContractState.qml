import QtQuick
import "ContractModel.js" as Model

QtObject {
    property bool sessionOpen: false
    property int generation: 0
    property int requestSequence: 0
    property string pendingToken: ""
    property string requestState: "idle"
    property bool ready: false
    property var currentTemperature: null
    property var currentTouch: null
    property var lastTemperature: null
    property var lastTouch: null
    property string unavailableLabel: "状态暂不可用"
    readonly property var temperatureDisplay: display(currentTemperature, lastTemperature)
    readonly property var touchDisplay: display(currentTouch, lastTouch)
    readonly property string temperatureText: text(temperatureDisplay)
    readonly property string touchText: text(touchDisplay)
    property var touchValue: null
    property string bootDefaultLabel: "未知"
    property var legacy: ({})

    function display(current, previous) {
        if (current && current.known)
            return {valueText:current.label, statusText:"本次采样", observedAt:current.observedAt, historical:false}
        let status = unavailableLabel
        if (requestState === "loading") status = previous ? "更新中" : "读取中"
        else if (requestState === "error") status = "本次读取失败"
        else if (current) status = ({stale:"已过期",error:"读取失败",unavailable:"不可用",unknown:"未知"})[current.health] || "未知"
        return {valueText:previous ? "上次 " + previous.label : "", statusText:status,
                observedAt:previous ? previous.observedAt : null, historical:previous !== null}
    }
    function text(view) {
        if (!view.valueText) return view.statusText
        return view.historical ? view.valueText + " · " + view.statusText : view.valueText
    }
    function invalidate(label) {
        ready = false; currentTemperature = null; currentTouch = null
        touchValue = null; bootDefaultLabel = "未知"; unavailableLabel = label
    }
    function clearHistory() { lastTemperature = null; lastTouch = null }
    function beginOpen() {
        generation++; sessionOpen = true; pendingToken = ""; legacy = ({})
        clearHistory(); requestState = "idle"; invalidate("读取中")
    }
    function closeSession() {
        generation++; sessionOpen = false; pendingToken = ""; legacy = ({})
        clearHistory(); requestState = "idle"; invalidate("状态暂不可用")
    }
    function startRequest() {
        if (!sessionOpen || pendingToken !== "") return null
        requestSequence++; pendingToken = String(generation) + ":" + String(requestSequence)
        invalidate("读取中"); requestState = "loading"
        return pendingToken
    }
    function current(token) { return sessionOpen && typeof token === "string" && token !== "" && token === pendingToken }
    function fail(token, code) {
        if (!current(token)) return
        // Only identified transport failures may retain trusted historical display.
        if (["read_timeout", "start_failed", "read_failed"].indexOf(code) < 0) clearHistory()
        pendingToken = ""; invalidate("状态暂不可用"); requestState = "error"
    }
    function copyReading(reading) {
        return {known:reading.known, value:reading.value, label:reading.label,
                health:reading.health, observedAt:reading.observedAt, bootDefaultLabel:reading.bootDefaultLabel}
    }
    function accept(token, response) {
        if (!current(token)) return false
        if (!response || !response.legacy || response.legacy.locked !== false) {
            closeSession(); return false
        }
        const value = Model.snapshot(response)
        if (!value.valid) { fail(token, "invalid_response"); return false }
        pendingToken = ""; legacy = value.legacy; requestState = "idle"
        invalidate("不可用"); ready = value.ready
        if (ready) {
            currentTemperature = value.temperature; currentTouch = value.touch
            if (value.temperature.known) lastTemperature = copyReading(value.temperature)
            if (value.touch.known) lastTouch = copyReading(value.touch)
            touchValue = value.touch.known ? value.touch.value : null
            bootDefaultLabel = value.touch.bootDefaultLabel
        }
        return true
    }
    function finish(token, raw, exitCode, complete) {
        if (!current(token)) return false
        if (complete !== true || typeof raw !== "string" || Model.utf8Size(raw) > 65536) {
            fail(token, "invalid_transport"); return false
        }
        if (exitCode !== 0) { fail(token, "read_failed"); return false }
        try { return accept(token, JSON.parse(raw)) }
        catch (e) { fail(token, "invalid_json"); return false }
    }
}
