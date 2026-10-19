// Only known output ownership enables an edge. No fallback to the first screen.
function enabled(edge, barPosition, configKnown, outputValid) {
    const edges = ["top", "bottom", "left", "right"]
    return configKnown === true && outputValid === true
        && edges.indexOf(edge) >= 0 && edges.indexOf(barPosition) >= 0
        && edge !== barPosition
}
