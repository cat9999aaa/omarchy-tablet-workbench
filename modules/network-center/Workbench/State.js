function freshSnapshot(data,now,maxAge) {
 return !!data&&Number.isFinite(now)&&Number.isFinite(data.observed_at)
  &&Number.isFinite(maxAge)&&maxAge>=0&&now-data.observed_at>=-5&&now-data.observed_at<=maxAge;
}
function fieldState(field,now) {
 if(!field||field.available!==true)return {known:false,value:null,label:"不可用"};
 // Missing health is the legacy field format; an explicit status is authoritative.
 if(field.health!==undefined && field.health!=="observed") {
  const label=field.health==="error"?"读取失败":field.health==="stale"?"已过期":field.health==="unavailable"?"不可用":"未知";
  return {known:false,value:null,label:label};
 }
 if(!freshSnapshot(field,now,field.stale_after))return {known:false,value:null,label:"待读取"};
 const value=field.actual;
 if(value===null||value===undefined||(typeof value==="number"&&!Number.isFinite(value)))return {known:false,value:null,label:"未知"};
 return {known:true,value:value,label:value===true?"运行":value===false?"关闭":String(value)};
}
if(typeof module!=="undefined")module.exports={freshSnapshot,fieldState};
