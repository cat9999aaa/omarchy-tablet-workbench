import QtQuick
import Quickshell
import Quickshell.Io
Item {
 id:root
 property color foreground:"#d5d8dc"
 property color background:"#161a20"
 property color accent:"#82b788"
 // Follow Omarchy's public current-theme file; do not edit packaged shell files.
 FileView {
  path:Quickshell.env("HOME")+"/.local/state/omarchy/current/theme/colors.toml";watchChanges:true
  onFileChanged:reload()
  onLoaded:{
   const data=text();const fields=["foreground","background","accent"]
   for(const field of fields){const match=data.match(new RegExp("^"+field+"\\s*=\\s*['\"](#[0-9a-fA-F]{6})['\"]","m"));if(match)root[field]=match[1]}
  }
 }
}
