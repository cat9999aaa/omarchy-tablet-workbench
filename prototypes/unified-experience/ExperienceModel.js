// SPDX-License-Identifier: GPL-3.0-only
// Pure demo data. No system, network, capture or model access.
function destinations() {
    return [{id:'overview',label:'总览'},{id:'work',label:'工作'},
        {id:'tasks',label:'任务'},{id:'device',label:'设备'},
        {id:'connections',label:'连接'},{id:'settings',label:'设置'}];
}
function initialState(scenarioId) {
    var stale=scenarioId==='stale', missing=scenarioId==='missing-device';
    return {destination:'overview',magiOpen:false,notice:'',modelAvailable:false,
        scenario:scenarioId||'normal',
        windows:[{id:'a1',app:'editor',title:'示例项目 · 设计稿',workspace:'工作区 1',hidden:false},
            {id:'a2',app:'editor',title:'示例项目 · 开发文档',workspace:'工作区 2',hidden:false},
            {id:'b1',app:'browser',title:'示例浏览器 · 文档',workspace:'工作区 1',hidden:false}],
        observations:{temperature:{value:48,unit:'°C',health:stale?'stale':'observed',age:stale?'示例：5 分钟前':'示例：刚刚'},
            light:{value:missing?null:120,unit:'lx',health:missing?'unavailable':'observed',age:'示例读数'}},
        network:scenarioId==='offline'?'离线演示':'连接示例',
        modelReason:'未接模型 · 基础导航仍可使用'};
}
function reduce(state,event) {
    if(!state||!event||typeof event.type!=='string')return state;
    var next;
    if(event.type==='navigate') {
        if(!destinations().some(function(d){return d.id===event.id}))return state;
        next=Object.assign({},state);next.destination=event.id;next.magiOpen=false;return next;
    }
    if(event.type==='toggleMagi') {
        next=Object.assign({},state);next.magiOpen=!state.magiOpen;return next;
    }
    if(['demoHide','demoRestore','demoCloseWindow','demoQuitApplication'].indexOf(event.type)<0)return state;
    var target=state.windows.filter(function(w){return w.id===event.id})[0];
    if(!target)return state;
    next=Object.assign({},state);
    next.windows=state.windows.filter(function(w){
        return event.type==='demoCloseWindow'?w.id!==target.id:
            event.type==='demoQuitApplication'?w.app!==target.app:true;
    }).map(function(w){
        return w.id===target.id&&(event.type==='demoHide'||event.type==='demoRestore')?
            Object.assign({},w,{hidden:event.type==='demoHide'}):w;
    });
    next.notice=event.type==='demoQuitApplication'?'演示：已退出示例应用，未操作真实应用。':
        event.type==='demoCloseWindow'?'演示：仅关闭此示例窗口，其他窗口保留。':
        event.type==='demoHide'?'演示：窗口已隐藏，可在此页恢复。':'演示：窗口已恢复，未操作真实桌面。';
    return next;
}
