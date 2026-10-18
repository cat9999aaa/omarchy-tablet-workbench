// SPDX-License-Identifier: GPL-3.0-only
function size(text) {
    try { return unescape(encodeURIComponent(text)).length; } catch(e) { return Infinity; }
}
function keys(v, names) {
    return v !== null && typeof v === 'object' && !Array.isArray(v)
        && Object.keys(v).sort().join(',') === names.split(',').sort().join(',');
}
function number(v) { return typeof v === 'number' && Number.isFinite(v) && v >= 0 && v <= Number.MAX_SAFE_INTEGER; }
function integer(v) { return number(v) && Math.floor(v) === v; }
function notice(text, previous) {
    if (typeof text !== 'string' || size(text) > 256) return null;
    try {
        const v = JSON.parse(text);
        if (!keys(v,'schema_version,event,seq') || v.schema_version !== 1 || !integer(v.seq)) return null;
        if (previous === -1) return v.event === 'ready' && v.seq === 0 ? v : null;
        return (v.event === 'changed' || v.event === 'lost') && v.seq > previous ? v : null;
    } catch(e) { return null; }
}
function feed(buffer, chunk, previous) {
    const bad = {valid:false,buffer:'',seq:previous,events:[]};
    if (typeof chunk !== 'string' || size(buffer + chunk) > 4096) return bad;
    const lines = (buffer + chunk).split('\n');
    const rest = lines.pop();
    if (size(rest) > 256) return bad;
    const events = [];
    let lost = false;
    for (let i=0;i<lines.length;i++) {
        const v = notice(lines[i],previous);
        if (!v || lost) return bad;
        previous=v.seq;events.push(v.event);lost=v.event==='lost';
    }
    if (lost && rest.length) return bad;
    return {valid:true,buffer:rest,seq:previous,events:events};
}
function response(text) {
    if (typeof text !== 'string' || size(text) > 65536) return null;
    try {
        const v=JSON.parse(text), e=v.evidence, m=v.mode;
        if (!keys(v,'schema_version,evidence,mode,confirm_after_ms') || v.schema_version!==1
            || !keys(e,'schema_version,complete,health,reason_code,physical_keyboard_present,touch_present,tablet_switch_capability,excluded_virtual_count,unclassified_keyboard_count,sample_duration_ms')
            || e.schema_version!==1 || typeof e.complete!=='boolean' || ['observed','unknown','error'].indexOf(e.health)<0
            || ['observed','unclassified_keyboard','device_changed','read_timeout','read_cancelled','read_failed','read_denied','enumeration_failed','invalid_data','limit_exceeded'].indexOf(e.reason_code)<0
            || !integer(e.excluded_virtual_count) || !integer(e.unclassified_keyboard_count) || !number(e.sample_duration_ms)) return null;
        for (const k of ['physical_keyboard_present','touch_present','tablet_switch_capability'])
            if(e[k]!==null && typeof e[k]!=='boolean')return null;
        if (!keys(m,'effective,health,reason_code,pending') || [null,'tablet','desktop'].indexOf(m.effective)<0
            || ['observed','unknown'].indexOf(m.health)<0
            || ['manual','stable','debouncing','time_invalid','observation_gap','unknown_evidence','no_supported_mode'].indexOf(m.reason_code)<0) return null;
        const p=m.pending;
        if(p!==null && (!keys(p,'target,since_ms,last_seen_ms') || ['tablet','desktop'].indexOf(p.target)<0
            || !number(p.since_ms) || !number(p.last_seen_ms) || p.since_ms>p.last_seen_ms))return null;
        if(v.confirm_after_ms!==null && (!integer(v.confirm_after_ms) || v.confirm_after_ms>1000))return null;
        if(m.reason_code==='debouncing' ? p===null || v.confirm_after_ms===null : v.confirm_after_ms!==null)return null;
        if(m.health==='observed' && (m.effective===null || ['stable','manual'].indexOf(m.reason_code)<0))return null;
        return v;
    } catch(e) { return null; }
}
if(typeof module!=='undefined')module.exports={notice:notice,feed:feed,response:response,size:size};
