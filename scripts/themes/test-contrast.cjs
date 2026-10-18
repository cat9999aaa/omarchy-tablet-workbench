const assert = require('node:assert/strict');
const c = require('./Contrast.js');
const black = {r:0,g:0,b:0,a:1}, white = {r:1,g:1,b:1,a:1};
assert.equal(c.ratio(black,white),21);
assert.equal(c.ratio(white,white),1);
assert.deepEqual(c.over({...white,a:.5},black),{r:.5,g:.5,b:.5,a:1});
// Whole-group opacity applies after the child's text and local fill compose.
const samples = c.samples(white,.5,[{color:{...black,a:.5},opacity:.5},{color:black,opacity:1}]);
assert.ok(Math.abs(samples.foreground.r-.25)<1e-10);
assert.equal(samples.background.r,0);
assert.ok(c.ratio(samples.foreground,samples.background)<4.5);
assert.throws(()=>c.ratio({...white,a:.5},black),/opaque/);
console.log('composited contrast: 6 assertions passed');
