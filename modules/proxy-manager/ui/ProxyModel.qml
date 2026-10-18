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
 property var catalog:({nodes:[],revision:0,current:null})
 property var preview:({})
 property bool catalogPending:false
 property string catalogFeedback:""
 signal catalogRequested(var command)
 signal editRoutingRequested()
 function catalogAction(command){if(catalogPending)return;catalogPending=true;catalogFeedback="正在处理…";catalogRequested(command)}
 function acceptCatalog(value){
  catalogPending=false
  if(value.error_code){catalogFeedback=({migration_unsupported:"旧配置包含尚未支持的字段，原客户端保持可用",unsupported_field:"包含未支持的参数，未导入",unsupported_protocol:"尚不支持这个协议，未导入",https_subscription_required:"订阅必须使用 HTTPS",catalog_revision_conflict:"目录已变化，请重新预览",preview_conflict:"预览已变化，请重新导入",flight_active:"飞行模式下暂停在线更新"})[value.error_code]||"处理未完成，请检查格式或权限";return}
  if(value.preview_id){preview=value;catalogFeedback="预览已准备，确认后才保存"}
  else if(value.draft){catalogFeedback="草稿已校验并保存，尚未应用"}
  else if(value.nodes){catalog=value;preview={};catalogFeedback="本机目录已读回，运行网络未改变"}
 }
 function commitPreview(confirmed){if(!preview.preview_id)return;catalogAction({action:"commit",preview_id:preview.preview_id,confirmed:!!confirmed})}
 function selectNode(id){draft=Object.assign({},draft,{node_id:id,dirty:true,mode:draft.mode||"rules",base_revision:catalog.revision,rules:draft.rules||[]})}
 function selectMode(mode){if(["rules","global","direct"].indexOf(mode)<0)return;draft=Object.assign({},draft,{mode:mode,dirty:true,base_revision:catalog.revision,rules:draft.rules||[]})}
 function saveRoutingDraft(){if(!draft.node_id)return;catalogAction({action:"routing-preview",draft:{mode:draft.mode,node_id:draft.node_id,base_revision:catalog.revision,rules:draft.rules||[]}})}
 property var updates:({observed_at:null,proposals:[],checks:[]})
 property bool updatesPending:false
 property string updatesFeedback:""
 signal updatesRequested(var command)
 function updateAction(action){if(updatesPending)return;updatesPending=true;updatesFeedback="正在读取更新信息…";updatesRequested({action:action})}
 function acceptUpdates(value){updatesPending=false;if(value.error_code){updatesFeedback=({metered_or_unknown:"4G 或出口未知，已延后在线检查",flight_or_unknown:"飞行模式或状态未知，已暂停检查",update_check_failed:"未能获取上游信息，保留当前版本"})[value.error_code]||"更新信息暂不可用";return}updates=value;updatesFeedback="只生成更新提案；核心仍按 Omarchy → Arch 渠道维护"}
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
