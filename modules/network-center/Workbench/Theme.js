// Internal schema 1. Pure value composition; no I/O or state inference.
function resolve(options) {
    var o = options && options.schemaVersion === 1 ? options : {};
    var scale = typeof o.fontScale === 'number' && isFinite(o.fontScale) && o.fontScale > 0
        ? Math.min(2, Math.max(.75, o.fontScale)) : 1;
    var radius = typeof o.cornerRadius === 'number' && isFinite(o.cornerRadius)
        && o.cornerRadius >= 0 && o.cornerRadius <= 24 ? o.cornerRadius : 8;
    function color(name, fallback) {return o[name] === undefined || o[name] === null ? fallback : o[name];}
    return {
        schemaVersion: 1,
        colors: {foreground:color('foreground','white'), background:color('background','#0C1014'),
                 accent:color('accent','white'), urgent:color('urgent','#FF6778'), muted:color('muted','#99A6AF')},
        font: {family:typeof o.fontFamily === 'string' && o.fontFamily.trim() ? o.fontFamily : 'sans-serif',
               body:16*scale, subtitle:13*scale, title:21*scale},
        metrics: {minimumTouchHeight:48, paddingX:12*scale, paddingY:10*scale, gap:12*scale, gapSmall:6*scale, radius:radius},
        states: {normalAlpha:.05, selectedAlpha:.18, pressedAlpha:.28, disabledTextAlpha:.65, focusBorderWidth:2}
    };
}
if (typeof module !== 'undefined') module.exports = {resolve:resolve};
