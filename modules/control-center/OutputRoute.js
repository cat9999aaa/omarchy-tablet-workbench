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
if (typeof module !== 'undefined') module.exports = {pickTarget: pickTarget};
