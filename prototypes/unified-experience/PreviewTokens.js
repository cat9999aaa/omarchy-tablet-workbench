.import "../../modules/workbench-ui/Theme.js" as Theme
// Preview choices only. Production theme and component sources stay unchanged.
function resolve(options) {
    var o=Object.assign({schemaVersion:1,foreground:'#E8E5DE',background:'#101518',
        accent:'#F7B34B',urgent:'#FF7788',muted:'#B1B9BA',cornerRadius:4},options||{});
    var tokens=Theme.resolve(o);
    tokens.preview={navigationWidth:224,barHeight:56,narrowBreakpoint:720};
    return tokens;
}
