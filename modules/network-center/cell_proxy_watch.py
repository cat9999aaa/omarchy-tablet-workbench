#!/usr/bin/python3
"""Network events coordinate a singleton proxy. Periodic health is read-only."""
import gi,subprocess
from pathlib import Path
gi.require_version('Gio','2.0')
from gi.repository import Gio,GLib
from policy import read_policy
process=None;health_process=None
helper=str(Path(__file__).with_name('network.py'))
def check():
 global process
 if (process is None or process.poll() is not None) and read_policy()['proxy_enabled']:
  process=subprocess.Popen(['/usr/bin/python',helper,'proxy-auto-on'])
 return False
def health():
 global health_process
 if health_process is None or health_process.poll() is not None:health_process=subprocess.Popen(['/usr/bin/python',helper,'health'])
 return True
def changed(connection,sender,path,interface,signal,parameters,data):
 values=parameters.unpack()
 if values:
  GLib.timeout_add(1500,lambda:health() and False)
  if values[0]==100:GLib.timeout_add(700,check)
def unit_changed(connection,sender,path,interface,signal,parameters,data):
 values=parameters.unpack()
 if len(values)>1 and values[0]=='org.freedesktop.systemd1.Unit' and values[1].get('ActiveState')=='inactive':
  subprocess.Popen(['/usr/bin/python',helper,'proxy-user-exit'])
bus=Gio.bus_get_sync(Gio.BusType.SYSTEM,None)
bus.signal_subscribe('org.freedesktop.NetworkManager','org.freedesktop.NetworkManager.Device','StateChanged',None,None,Gio.DBusSignalFlags.NONE,changed,None)
def manager_changed(connection,sender,path,interface,signal,parameters,data):
 values=parameters.unpack()
 if len(values)>1 and any(k in values[1] for k in ('PrimaryConnection','Connectivity')):GLib.timeout_add(1000,lambda:health() and False)
bus.signal_subscribe('org.freedesktop.NetworkManager','org.freedesktop.DBus.Properties','PropertiesChanged','/org/freedesktop/NetworkManager',None,Gio.DBusSignalFlags.NONE,manager_changed,None)
userbus=Gio.bus_get_sync(Gio.BusType.SESSION,None)
try:
 userbus.call_sync('org.freedesktop.systemd1','/org/freedesktop/systemd1','org.freedesktop.systemd1.Manager','Subscribe',None,None,Gio.DBusCallFlags.NONE,3000,None)
 unit=userbus.call_sync('org.freedesktop.systemd1','/org/freedesktop/systemd1','org.freedesktop.systemd1.Manager','GetUnit',GLib.Variant('(s)',('app-v2rayN@autostart.service',)),None,Gio.DBusCallFlags.NONE,3000,None).unpack()[0]
 userbus.signal_subscribe('org.freedesktop.systemd1','org.freedesktop.DBus.Properties','PropertiesChanged',unit,None,Gio.DBusSignalFlags.NONE,unit_changed,None)
except GLib.Error:print('client exit tracking unavailable',flush=True)
GLib.idle_add(check);GLib.timeout_add_seconds(3,lambda:health() and False);GLib.timeout_add_seconds(30,health)
GLib.MainLoop().run()
