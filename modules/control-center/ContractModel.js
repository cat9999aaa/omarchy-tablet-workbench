// Read-only presentation. No clock can promote an explicit health value.
var temperatureId = "dashen.device.temperature"
var touchId = "dashen.device.touch-mode"
function object(value) { return value !== null && typeof value === "object" && !Array.isArray(value) }
function utf8Size(text) {
    try { return encodeURIComponent(text).replace(/%[A-F\d]{2}/g, "x").length }
    catch (e) { return Infinity }
}
function identity(e, id) {
    const temperature = id === temperatureId
    return (temperature || id === touchId) && object(e) && e.contract_version === "0.1.0"
        && e.capability_id === id && e.output_id === "local"
        && e.resource_id === (temperature ? "thermal-summary" : "touch-mode")
        && e.read_permission === (temperature ? "device.temperature.read" : "device.touch-mode.read")
        && object(e.state) && typeof e.state.available === "boolean"
        && ["observed", "unknown", "error", "stale", "unavailable"].indexOf(e.state.health) >= 0
}
function touchName(value) { return value === 0 ? "普通触摸" : value === 1 ? "手套／原装笔" : value === 2 ? "笔模式" : "未知" }
function reading(e, id) {
    const result = {known:false, value:null, label:"状态暂不可用", bootDefaultLabel:"未知"}
    if (!identity(e, id)) return result
    const s = e.state, value = s.actual, temperature = id === temperatureId
    if (!temperature) result.bootDefaultLabel = touchName(s.boot_default)
    result.label = ({unknown:"未知", error:"读取失败", stale:"待读取", unavailable:"不可用"})[s.health] || "未知"
    const valid = typeof value === "number" && Number.isFinite(value)
        && (temperature ? value >= -20 && value <= 150 : Number.isInteger(value) && value >= 0 && value <= 2)
    if (s.available && s.health === "observed" && valid) {
        result.known = true; result.value = value
        result.label = temperature ? String(value) + " °C" : touchName(value)
    }
    return result
}
function snapshot(response) {
    const invalid = {valid:false}
    try {
        if (utf8Size(JSON.stringify(response)) > 65536 || !object(response) || response.schema_version !== 1
            || !object(response.legacy) || response.legacy.locked !== false || !object(response.contracts)) return invalid
        const c = response.contracts
        if (c.version !== "0.1.0" || !Array.isArray(c.states)) return invalid
        if (c.status === "unavailable" && c.states.length === 0)
            return {valid:true, ready:false, legacy:response.legacy}
        if (c.status !== "ok" || c.states.length !== 2) return invalid
        const temperatures = c.states.filter(function(e) {return object(e) && e.capability_id === temperatureId})
        const touches = c.states.filter(function(e) {return object(e) && e.capability_id === touchId})
        if (temperatures.length !== 1 || touches.length !== 1 || !identity(temperatures[0], temperatureId) || !identity(touches[0], touchId)) return invalid
        return {valid:true, ready:true, legacy:response.legacy,
                temperature:reading(temperatures[0], temperatureId), touch:reading(touches[0], touchId)}
    } catch (e) { return invalid }
}
function parse(text) {
    if (typeof text !== "string" || utf8Size(text) > 65536) return {valid:false}
    try { return snapshot(JSON.parse(text)) } catch (e) { return {valid:false} }
}
if (typeof module !== "undefined") module.exports = {reading:reading, snapshot:snapshot, parse:parse, utf8Size:utf8Size}
