"""Disposable real GTK target for touch acceptance; no user document is opened."""
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib
from pathlib import Path
import os

window=Gtk.Window(title='触屏输入法 · 独立测试输入框')
window.set_default_size(620, 330)
box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
box.set_border_width(24)
window.add(box)
box.pack_start(Gtk.Label(label='请点下面输入框，再用右侧九宫格输入“你好”。\n这是独立测试窗口，不会发送聊天消息。'), False, False, 0)
entry=Gtk.Entry(); entry.set_placeholder_text('点这里输入中文')
box.pack_start(entry, False, False, 0)
entry.connect('changed', lambda e: Path('/tmp/omt-test-editor-result').write_text(e.get_text()))
button=Gtk.Button(label='关闭测试窗口')
button.connect('clicked',lambda _: Gtk.main_quit())
box.pack_end(button, False, False, 0)
window.connect('destroy',lambda _: Gtk.main_quit())
window.show_all(); entry.grab_focus()
Gtk.main()
