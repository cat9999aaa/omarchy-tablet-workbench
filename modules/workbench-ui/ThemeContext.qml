import QtQuick
import qs.Commons
import "Theme.js" as Theme
QtObject {
 readonly property var tokens:Theme.resolve({schemaVersion:1,
  foreground:Color.foreground,background:Color.popups.background,
  accent:Color.accent,urgent:Color.urgent,muted:Color.muted,
  fontFamily:Style.font.family,fontScale:Style.font.body/12,
  cornerRadius:Style.cornerRadius})
}
