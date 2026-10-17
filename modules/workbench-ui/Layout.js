// Shared content envelope. Page data must never participate in geometry.
function panelSize(width,height) {
 const w=Number.isFinite(width)&&width>0?width:480;
 const h=Number.isFinite(height)&&height>0?height:800;
 return {width:Math.max(1,Math.min(640,w-24)),height:Math.max(1,Math.floor(h*0.7))};
}
if(typeof module!=="undefined")module.exports={panelSize};
