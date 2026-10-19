"""Small reversible patch to an existing user bar, never the packaged host.

This host version exposes iconSlot but drops icon-slot in applyShellValues.
Use the official merged theme dictionary to size the existing Loader region.
No second host, global Style mutation, extra input surface, or polling.
"""
OLD = 'implicitWidth: activeItem && activeItem.visible ? (root.vertical ? root.barSize : activeItem.implicitWidth) : 0'
NEW = '''// DASHEN U2B: honor the explicit theme slot minimum in the existing Loader.
    readonly property real touchSlotMinimum: {
      const raw = Color.shellValues["bar.icon-slot"]
      const value = Number(raw)
      return !root.vertical && /^[0-9]+$/.test(String(raw)) && value >= 16 && value <= 128
        ? value * (Style.barScaleWithFont ? Style.fontScale : 1) : 0
    }
    implicitWidth: activeItem && activeItem.visible ? (root.vertical ? root.barSize : Math.max(activeItem.implicitWidth, touchSlotMinimum)) : 0'''

PRESS_OLD = '''      property bool suppressClick: false
      property real pressedX: 0'''
PRESS_NEW = '''      property bool suppressClick: false
      // Opt-in scoped entry identity; legacy widgets retain their existing path.
      property var pressedTarget: null
      property var pressedIdentity: null
      property real pressedX: 0'''
CAPTURE_OLD = '''        pressedY = mouse.y
        root.clearBarDrag()'''
CAPTURE_NEW = '''        pressedY = mouse.y
        pressedTarget = root.moduleClickTargetAt(slot, mouse.x, mouse.y)
        pressedIdentity = pressedTarget && typeof pressedTarget.capturePressIdentity === "function"
          ? pressedTarget.capturePressIdentity() : null
        root.clearBarDrag()'''
CLICK_OLD = '''        if (!root.pressModuleClickTarget(slot, mouse.button, mouse.x, mouse.y)) mouse.accepted = false'''
CLICK_NEW = '''        var currentTarget = root.moduleClickTargetAt(slot, mouse.x, mouse.y)
        var scoped = (pressedTarget && typeof pressedTarget.capturePressIdentity === "function")
          || (currentTarget && typeof currentTarget.capturePressIdentity === "function")
        if (scoped && (pressedTarget !== currentTarget || !currentTarget
            || pressedIdentity !== currentTarget.capturePressIdentity())) {
          mouse.accepted = true
          return
        }
        if (!root.pressModuleClickTarget(slot, mouse.button, mouse.x, mouse.y)) mouse.accepted = false'''
REPLACEMENTS = [(OLD, NEW), (PRESS_OLD, PRESS_NEW), (CAPTURE_OLD, CAPTURE_NEW), (CLICK_OLD, CLICK_NEW)]

def patched(source):
    for old,new in REPLACEMENTS:
        if new in source:continue
        if source.count(old)!=1:raise ValueError('unsupported-bar-source')
        source=source.replace(old,new)
    return source

def restored(source):
    for old,new in reversed(REPLACEMENTS):
        if source.count(new)!=1:raise ValueError('bar-patch-conflict')
        source=source.replace(new,old)
    return source
