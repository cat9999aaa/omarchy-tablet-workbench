// A gesture starts only inside its dedicated screen-edge surface.
function route(edge, dx, dy, cancelled) {
    if (cancelled || Math.abs(dy) < 64 || Math.abs(dx) > Math.abs(dy) * 0.7) return "";
    if (edge === "bottom" && dy < 0) return "desktops";
    if (edge === "top" && dy > 0) return "quickstatus";
    return "";
}
