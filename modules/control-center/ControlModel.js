function layout(width,height) {
 return {width:Math.max(1,Math.min(760,width-24)),height:Math.max(1,Math.floor(height*.7)),columns:width<620?2:3,tileHeight:64,gap:8};
}
function displayField(f,now) {
 if(!f || !f.available)return "不可用";
 if(now-f.observed_at>f.stale_after)return "待读取";
 if(f.actual===null || f.actual===undefined)return "未知";
 return String(f.actual);
}
function canOpen(locked,imeHidden) {return locked===false && imeHidden===true;}
function commitSlider(n) {return Number.isFinite(n)&&n>=0&&n<=100?Math.round(n):null;}
function booleanState(f,now) {
 const label=displayField(f,now),known=label==="true"||label==="false";
 return {known:known,label:known?(label==="true"?"运行":"关闭"):label,value:known?f.actual:null};
}
if(typeof module!=="undefined")module.exports={layout,displayField,canOpen,commitSlider,booleanState};
