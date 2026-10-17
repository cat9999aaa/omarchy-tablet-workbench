const fs=require('fs'),vm=require('vm'),assert=require('assert');
const c={};vm.createContext(c);vm.runInContext(fs.readFileSync(__dirname+'/Gesture.js','utf8'),c);
assert.equal(c.route('bottom',0,-80,false),'desktops');
assert.equal(c.route('top',0,80,false),'quickstatus');
for(const v of [['bottom',0,20,false],['top',0,-80,false],['bottom',100,-80,false],['bottom',0,-25,false],['top',0,90,true]]) assert.equal(c.route(...v),'');
console.log('PASS: edge direction, distance, horizontal rejection and cancellation');
