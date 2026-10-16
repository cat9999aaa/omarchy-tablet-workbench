function duration(seconds) {
  var minutes = Math.ceil(Number(seconds) / 60)
  if (!(minutes > 0) || !isFinite(minutes)) return "暂无法估计"
  return "约 " + (minutes >= 60 ? Math.floor(minutes / 60) + "小时 " : "") + minutes % 60 + "分钟"
}
function state(device, states) {
  if (!device || !device.isPresent) return "未检测到"
  if (device.state === states.Charging) return "充电中"
  if (device.state === states.Discharging) return "放电中"
  if (device.state === states.FullyCharged) return "已充满"
  if (device.state === states.PendingCharge) return "等待充电"
  return "未充电／状态待确认"
}
function remaining(device, states) {
  if (!device) return "暂无法估计"
  if (device.state === states.Charging) return duration(device.timeToFull)
  if (device.state === states.Discharging) return duration(device.timeToEmpty)
  if (device.state === states.FullyCharged) return "已充满"
  return "等待稳定充放电"
}
function elapsedLabel(seconds) {
  if (seconds === null || seconds === undefined || !isFinite(Number(seconds)) || Number(seconds) < 0) return "未知"
  var minutes = Math.floor(Number(seconds)/60)
  return (minutes >= 60 ? Math.floor(minutes/60) + "小时 " : "") + minutes%60 + "分钟"
}
function sessionLabel(session) {
  if (!session) return "记录尚未开始"
  var label = session.kind === "charge" ? "本次接电" : session.kind === "discharge" ? "本次使用" : "供电状态未知"
  return label + (session.partial_start ? " · 从首次记录起" : "")
}
function batteryChange(session,bay) {
  if (!session || !session.start_percent_by_bay || !session.end_percent_by_bay) return "未知"
  var a=session.start_percent_by_bay[bay],b=session.end_percent_by_bay[bay]
  if (a === null || a === undefined || b === null || b === undefined) return "未知"
  return a + "% → " + b + "%"
}
function observedBatteryState(battery) {
  if (!battery || !battery.present && battery.present !== undefined) return "未检测到"
  if (battery.status === "Charging") return "正在充电"
  if (battery.status === "Discharging") return "正在放电"
  if (battery.status === "Full") return "已充满"
  if (battery.status === "Not charging" && battery.charge_end_threshold !== null && battery.charge_end_threshold !== undefined && battery.charge_end_threshold < 100 && battery.percent >= battery.charge_end_threshold) return "已到设置上限（"+battery.charge_end_threshold+"%）"
  return "等待／未充电"
}
function screenLabel(session) {
  if (!session) return "亮屏时长未知"
  var known=Number(session.screen_on_s || 0),unknown=Number(session.screen_unknown_s || 0)
  if (known===0 && unknown>0) return "亮屏时长未知（"+elapsedLabel(unknown)+"未能确认）"
  return "亮屏采样约 "+elapsedLabel(known)+(unknown>0 ? "；另有"+elapsedLabel(unknown)+"未知" : "")
}
if (typeof module !== "undefined") module.exports = {duration:duration,state:state,remaining:remaining,elapsedLabel:elapsedLabel,sessionLabel:sessionLabel,batteryChange:batteryChange,observedBatteryState:observedBatteryState,screenLabel:screenLabel}
