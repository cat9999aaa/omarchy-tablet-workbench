const assert=require('node:assert/strict'),m=require('./Model.js');
const states={Charging:1,Discharging:2,FullyCharged:4,PendingCharge:5};
const d={isPresent:true,percentage:.25,state:1,timeToFull:9*3600,changeRate:6};
assert.match(m.batteryIcon(d,false,states),/ϟ/,'Charging needs explicit lightning even with long ETA');
d.state=5;assert.doesNotMatch(m.batteryIcon(d,false,states),/ϟ/,'Pending charge must not claim current flowing');
d.state=2;assert.doesNotMatch(m.batteryIcon(d,false,states),/ϟ/,'Plugged but discharging must not claim charging');
console.log('PASS charging long ETA / pending / plugged discharge icons');
