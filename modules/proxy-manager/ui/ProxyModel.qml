import QtQuick
QtObject {
 id:root
 property var snapshot:({})
 property bool readOnly:false
 property bool pending:false
 property string pendingId:""
 property var draft:({dirty:false,mode:"rules"})
 property string lastError:""
 property double now:Date.now()/1000
 property Timer freshness:Timer {interval:10000;running:true;repeat:true;onTriggered:root.now=Date.now()/1000}
 readonly property bool online:known(snapshot.health)&&snapshot.health.value==="ok"
 readonly property string physicalLabel:known(snapshot.physical)?({"4g":"4G 蜂窝","wifi":"Wi-Fi","ethernet":"有线网络","none":"未连接"}[snapshot.physical.value]||"未知"):"未知"
 readonly property string proxyLabel:known(snapshot.proxy)?(snapshot.proxy.value?"开启":"关闭"):"未知"
 readonly property string tunLabel:known(snapshot.tun)?(snapshot.tun.value?"开启":"关闭"):"未知"
 signal requested(var command)
 function known(field){return !!field&&field.health==="observed"&&field.value!==null&&now-field.observed_at>=0&&now-field.observed_at<=45}
 function allowed(action){return !readOnly&&!pending&&(snapshot.capabilities||[]).indexOf(action)>=0}
 function submit(action,confirmed){
  if(pending||!allowed(action))return
  pending=true;pendingId="ui-"+Date.now()+"-"+Math.floor(Math.random()*100000);lastError=""
  requested({id:pendingId,expected_revision:snapshot.revision||0,action:action,confirmed:!!confirmed})
 }
 function refresh(){if(pending)return;requested({id:"status-"+Date.now(),expected_revision:0,action:"status",confirmed:false})}
 function accept(value){
  now=Date.now()/1000
  if(value.error_code){snapshot={};pending=false;lastError=errorText(value.error_code);return}
  if(value.snapshot && (value.snapshot.revision||0)>=(snapshot.revision||0))snapshot=value.snapshot
  if(value.outcome && value.outcome.id===pendingId){pending=false;lastError=value.outcome.verified?"":errorText(value.outcome.error_code||value.outcome.stage)}
 }
 function errorText(code){return ({service_unavailable:"管理服务暂不可用，状态未知",ownership_conflict:"控制归属待确认，保留当前连接",revision_conflict:"状态已变化，请核对后再操作",authorization_cancelled:"已取消系统授权，修改未生效",locked_or_unknown:"锁屏中或无法确认桌面状态",flight_or_unknown:"飞行状态不允许启动",busy:"另一项操作正在进行",timeout:"操作超时，请检查诊断",not_verified:"操作未通过读回确认"})[code]||"操作未完成，请查看诊断"}
}
