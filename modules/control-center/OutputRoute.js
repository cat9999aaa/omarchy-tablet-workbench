// SPDX-License-Identifier: GPL-3.0-only
// Slot identities are ephemeral, never persisted or exposed over IPC.
function pickTarget(candidates, focusedName) {
    if (!Array.isArray(candidates) || typeof focusedName !== 'string' || !focusedName.length)
        return null;
    var matches = candidates.filter(function(c) {
        return c && typeof c.id === 'string' && c.id.length > 0
            && typeof c.screenName === 'string' && c.screenName === focusedName
            && c.attached === true && c.visibleSlot === true;
    });
    return matches.length === 1 ? matches[0].id : null;
}
// Every peer is asked to close; the barrier also includes asynchronous reap.
function handoff(peers, target, current) {
    if (!Array.isArray(peers) || peers.indexOf(target)<0 || typeof current!=='function')return false;
    peers.forEach(function(peer){peer.routeEpoch++;peer.transferPending=false;});
    const epoch=target.routeEpoch;
    target.transferPending=true;
    let waiting=peers.length;
    peers.forEach(function(peer){
        let called=false;
        peer.closeForTransfer(function(){
            if(called)return;called=true;waiting--;
            if(waiting!==0)return;
            try {
                if(target.routeEpoch!==epoch || !target.transferPending)return;
                target.transferPending=false;
                if(current())target.requestOpen();
            } catch(e) { /* A destroyed target cannot be opened. */ }
        });
    });
    return true;
}
if (typeof module !== 'undefined') module.exports = {pickTarget:pickTarget,handoff:handoff};
