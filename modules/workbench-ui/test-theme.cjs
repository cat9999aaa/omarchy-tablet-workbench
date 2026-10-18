const assert = require('node:assert/strict');
const fs = require('node:fs');
assert(fs.existsSync(__dirname+'/Theme.js'), 'shared theme resolver missing');
const {resolve} = require('./Theme.js');
const defaults = resolve();
for (const value of [null, undefined, {}, {schemaVersion:2,fontScale:2}, {schemaVersion:'1',fontScale:2}]) {
  assert.deepEqual(resolve(value),defaults,'unsupported or absent schema returns compatibility defaults');
}
for (const value of [NaN,Infinity,-1,0,'2']) {
  const result=resolve({schemaVersion:1,fontScale:value});
  assert.equal(result.font.body,16);assert.equal(result.metrics.minimumTouchHeight,48);
}
for (const [scale,expected] of [[.1,12],[1,16],[1.5,24],[100,32]]) {
 const t=resolve({schemaVersion:1,fontScale:scale});assert.equal(t.font.body,expected);assert.equal(t.metrics.minimumTouchHeight,48);
}
const rgba={r:.5,g:.4,b:.3,a:.2};
const input={schemaVersion:1,foreground:rgba,fontFamily:'Noto Sans CJK SC',fontScale:1.5,cornerRadius:0};
const before=JSON.stringify(input),t=resolve(input);
assert.strictEqual(t.colors.foreground,rgba,'typed QML colors preserve alpha and identity');
assert.equal(t.font.family,'Noto Sans CJK SC');assert.equal(t.metrics.radius,0);
assert.equal(t.metrics.paddingX,18);assert.equal(t.metrics.paddingY,15);
assert.equal(t.states.focusBorderWidth,2);assert.equal(JSON.stringify(input),before);
for(const value of [-1,25,NaN,Infinity,'4'])assert.equal(resolve({schemaVersion:1,cornerRadius:value}).metrics.radius,8);
assert.equal(resolve({schemaVersion:1,fontFamily:'  '}).font.family,'sans-serif');
console.log('shared theme validation passed');
