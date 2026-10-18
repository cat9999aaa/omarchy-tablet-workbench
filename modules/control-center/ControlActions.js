// SPDX-License-Identifier: GPL-3.0-only
// Both layouts render this one action catalog and use Panel.act for authorization.
function ids(mode) {
    return mode==='desktop' ? ['network','proxy','zero','touch','nightlight','power-mode','screen-off','keyboard','flight']
        : ['network','proxy','zero','touch','keyboard','nightlight','flight','power-mode','screen-off'];
}
function quick(v) {
    const entries={
        network:{group:'连接',label:'Wi-Fi／4G',sub:v.network,action:'network'},
        proxy:{group:'连接',label:'代理',sub:'TUN · '+v.tun.label,action:v.tun.value===true?'proxy-off':'proxy-on',available:v.tun.known&&v.proxy.known},
        zero:{group:'连接',label:'ZeroTier',sub:v.zero.known?(v.zero.value?'服务在线':'等待连接'):v.zero.label,action:'zero'},
        touch:{group:'设备',label:'触摸模式',sub:v.touch,action:v.touchValue===1?'touch-normal':v.touchValue===0?'touch-glove':'touch-refresh'},
        keyboard:{group:'工作',label:'输入法',sub:'P1 同一入口',action:'keyboard'},
        nightlight:{group:'设备',label:'夜间模式',sub:v.night,action:'nightlight'},
        flight:{group:'旅途',label:'飞行模式',sub:typeof v.flightActive==='boolean'?'关闭无线 · 离线娱乐':'待读取',action:v.flightSaved?'flight-off':'flight-on',available:typeof v.flightActive==='boolean'},
        'power-mode':{group:'设备',label:'电源模式',sub:v.power||'读取中',action:'power-mode'},
        'screen-off':{group:'设备',label:'仅熄屏',sub:'任务继续 · 不挂起',action:'screen-off'}
    };
    Object.keys(entries).forEach(id=>{entries[id].id=id;entries[id].params={};});
    return entries;
}
function group(page) {
    const sets={
        '连接':[['网络与 GPS 详情','network'],['蓝牙','bluetooth']],
        '设备':[['双电池与充放电记录','power'],['夜间模式','nightlight'],['显示设置','monitor'],['省电','power-saver'],['均衡','balanced'],['手套／原装笔','touch-glove'],['普通触摸（本次）','touch-normal'],['刷新触摸模式','touch-refresh'],['锁屏','lock']],
        '工作':[['输入法','keyboard'],['声音设置','audio'],['当前窗口操作','windows']],
        '旅途':[['视频播放器','player'],['音乐播放器','music'],['小说阅读器','reader'],['离线街机','games'],['飞行模式…','flight-on']]
    };
    return (sets[page]||[]).map(x=>({id:x[1],label:x[0],op:x[1],params:{}}));
}
if(typeof module!=='undefined')module.exports={ids:ids,quick:quick,group:group};
