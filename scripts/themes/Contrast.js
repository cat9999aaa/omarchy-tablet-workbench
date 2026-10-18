// Test-side source-over composition of actual QML color/opacity properties.
function opacity(color, value) {
    return {r:color.r,g:color.g,b:color.b,a:color.a*value}
}
function over(front, back) {
    const a=front.a+back.a*(1-front.a)
    if (!a) return {r:0,g:0,b:0,a:0}
    function channel(key) {return (front[key]*front.a+back[key]*back.a*(1-front.a))/a}
    return {r:channel('r'),g:channel('g'),b:channel('b'),a:a}
}
function samples(text, textOpacity, layers) {
    let foreground=opacity(text,textOpacity),background={r:0,g:0,b:0,a:0}
    for (const layer of layers) {
        foreground=opacity(over(foreground,layer.color),layer.opacity)
        background=opacity(over(background,layer.color),layer.opacity)
    }
    return {foreground:foreground,background:background}
}
function luminance(color) {
    function linear(v) {return v<=.04045?v/12.92:Math.pow((v+.055)/1.055,2.4)}
    return .2126*linear(color.r)+.7152*linear(color.g)+.0722*linear(color.b)
}
function ratio(a,b) {
    if (a.a<.999999||b.a<.999999) throw new Error('contrast requires opaque final samples')
    const x=luminance(a),y=luminance(b)
    return (Math.max(x,y)+.05)/(Math.min(x,y)+.05)
}
if (typeof module!=='undefined') module.exports={over:over,samples:samples,ratio:ratio}
