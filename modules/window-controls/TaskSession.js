// Pure state machine. Source data stays anonymous; no provider content is accepted.
function initial(){return {phase:'closed',generation:0,serial:0,pending:null,output:null,scope:null,rows:[],remainingMs:5000,detailsRead:[],anonymousIds:{},nextOrdinal:1,truncated:false,sourceReason:'',observedAt:'',sampledBoottimeMs:0,stale:false,dnd:null,dndReason:'',feedback:''}}
function kind(status,pending){if(pending>0)return 'needs_permission';return ['initializing','idle','running','error','closed'].indexOf(status)>=0?status:'unknown'}
function ordered(rows){var order={needs_permission:0,error:1,running:2,initializing:3};return rows.slice().sort((a,b)=>(order[a.kind]===undefined?4:order[a.kind])-(order[b.kind]===undefined?4:order[b.kind])||a.ordinal-b.ordinal)}
function validId(id){return typeof id==='string'&&/^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$/.test(id)}
function reduce(s,e){
 var none={state:s,effects:[]};if(!e||typeof e.type!=='string')return none;
 function close(){return {state:Object.assign(initial(),{generation:s.generation+1,serial:s.serial}),effects:[{type:'cancel-read'},{type:'close'}]}}
 function read(type,output,extra){var id=s.serial+1,pending=Object.assign({id:id,kind:type},extra||{});return {state:Object.assign({},s,{serial:id,generation:s.generation+1,pending:pending,output:output,phase:type==='snapshot'?'loading':s.phase,feedback:''},type==='snapshot'?{rows:[],remainingMs:5000,detailsRead:[],sourceReason:'',dnd:null}:{}),effects:[{type:'cancel-read'},{type:'read-'+type,generation:s.generation+1,requestId:id,output:output,agent_id:pending.agent_id,scope:s.scope,remaining_ms:type==='snapshot'?5000:s.remainingMs}]}}
 if(['CLOSE','LOCKED','OUTPUT_LOST'].indexOf(e.type)>=0)return close();
 if(e.type==='OPEN'){
  if(typeof e.output!=='string'||!e.output.trim()||e.output.length>256||/[\x00-\x1f\x7f]/.test(e.output))return close();
  return read('snapshot',e.output);
 }
 if(e.type==='REFRESH'&&s.phase==='open')return read('snapshot',s.output);
 if(e.type==='DETAIL'&&s.phase==='open'&&!s.pending){
  if(!s.rows.some(r=>r.agent_id===e.agent_id)||s.detailsRead.indexOf(e.agent_id)>=0)return none;
  if(s.detailsRead.length>=5||s.remainingMs<1500)return {state:Object.assign({},s,{feedback:'本轮读取额度已用完，请刷新或打开 Paseo'}),effects:[]};
  var r=read('detail',s.output,{agent_id:e.agent_id});r.state.detailsRead=s.detailsRead.concat([e.agent_id]);return r;
 }
 if(e.type==='TICK'&&s.phase==='open'&&Number.isFinite(e.now))return {state:Object.assign({},s,{stale:s.stale||e.now<s.sampledBoottimeMs||e.now-s.sampledBoottimeMs>15000,rows:s.rows.map(r=>Object.assign({},r,{stale:r.stale||e.now<r.sampled_boottime_ms||e.now-r.sampled_boottime_ms>15000}))}),effects:[]};
 if(e.type!=='RESULT'||!s.pending||e.generation!==s.generation||e.requestId!==s.pending.id)return none;
 var v=e.value;
 if(!v||v.schema!==1||!Number.isInteger(v.elapsed_ms)||v.elapsed_ms<0||v.elapsed_ms>s.remainingMs)return close();
 var next=Object.assign({},s,{pending:null,remainingMs:s.remainingMs-v.elapsed_ms});
 if(v.ok!==true){
  if(s.pending.kind==='snapshot'||['locked','lock-unknown','context-changed','output-unavailable'].indexOf(v.reason_code)>=0)return close();
  next.rows=s.rows.map(r=>r.agent_id===s.pending.agent_id?Object.assign({},r,{kind:'unknown',pending_permission_count:null,stale:true,detailReason:'读取失败，请刷新后重试'}):r);return {state:next,effects:[]};
 }
 if(v.output!==s.output||!Number.isFinite(v.sampled_boottime_ms)||v.sampled_boottime_ms<0||typeof v.observed_at!=='string'||!Number.isFinite(Date.parse(v.observed_at)))return close();
 if(s.pending.kind==='snapshot'){
  if(v.rows!==null&&(!Array.isArray(v.rows)||typeof v.scope!=='string'||!/^[0-9a-f]{64}$/.test(v.scope)))return close();
  var ids=Object.assign({},s.anonymousIds),ordinal=s.nextOrdinal,seen={};
  var rows=[];
  for(var item of v.rows||[]){
   if(!item||!validId(item.agent_id)||seen[item.agent_id])return close();seen[item.agent_id]=true;
   if(!ids[item.agent_id])ids[item.agent_id]=ordinal++;
   rows.push({agent_id:item.agent_id,ordinal:ids[item.agent_id],status:kind(item.status,null),kind:kind(item.status,null),pending_permission_count:null,source_updated_at:null,observed_at:v.observed_at,sampled_boottime_ms:v.sampled_boottime_ms,stale:false,detailReason:''});
  }
  // Bound retained IDs as well as displayed rows; unseen IDs need no history.
  rows=ordered(rows);next.truncated=rows.length>20;next.rows=rows.slice(0,20);
  var retained={};for(var row of next.rows)retained[row.agent_id]=row.ordinal;
  next.anonymousIds=retained;next.nextOrdinal=ordinal;next.phase='open';next.scope=v.scope;next.observedAt=v.observed_at;next.sampledBoottimeMs=v.sampled_boottime_ms;next.stale=false;next.sourceReason=v.rows===null?(v.source_reason||'read-failed'):'';next.dnd=typeof v.dnd==='boolean'?v.dnd:null;next.dndReason=next.dnd===null?'暂时无法读取':'';
 }else{
  var d=v.detail;
  if(v.agent_id!==s.pending.agent_id||!d||(d.pending_permission_count!==null&&(!Number.isInteger(d.pending_permission_count)||d.pending_permission_count<0)))return close();
  next.rows=ordered(s.rows.map(r=>r.agent_id===v.agent_id?Object.assign({},r,{status:kind(d.status,null),kind:kind(d.status,d.pending_permission_count),pending_permission_count:d.pending_permission_count,source_updated_at:typeof d.source_updated_at==='string'?d.source_updated_at:null,observed_at:v.observed_at,sampled_boottime_ms:v.sampled_boottime_ms,stale:false}):r));
 }
 return {state:next,effects:[]};
}
function label(value){return ({needs_permission:'等你授权',error:'出错了',running:'正在运行',initializing:'正在准备',idle:'暂无运行',closed:'会话已关闭',unknown:'状态未知'})[value]||'状态未知'}
if(typeof module!=='undefined')module.exports={initial:initial,reduce:reduce,label:label};
