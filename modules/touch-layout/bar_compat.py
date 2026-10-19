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

def patched(source):
    if NEW in source:return source
    if source.count(OLD)!=1:raise ValueError('unsupported-bar-source')
    return source.replace(OLD,NEW)

def restored(source):
    if source.count(NEW)!=1:raise ValueError('bar-patch-conflict')
    return source.replace(NEW,OLD)
