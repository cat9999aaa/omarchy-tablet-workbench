import gi,json
from pathlib import Path
gi.require_version('Qmi','1.0')
from gi.repository import Qmi,Gio,GLib
usb=Path('/sys/class/usbmisc/cdc-wdm0/device').resolve().parent
assert (usb/'idVendor').read_text().strip()=='413c' and (usb/'idProduct').read_text().strip()=='81d7'
loop=GLib.MainLoop();device=None;client=None

def done(o,r,*_):
 try:
  out=o.get_transport_network_registration_status_finish(r);out.get_result();status=out.get_registration_status();print(json.dumps({'sms_transport_registration':status.value_nick}),flush=True)
 except Exception as e:print(json.dumps({'query_error':str(e)}),flush=True)
 finally:device.release_client(client,Qmi.DeviceReleaseClientFlags.RELEASE_CID,10,None,released,None)
def released(o,r,*_):
 try:o.release_client_finish(r)
 finally:loop.quit()
def allocated(o,r,*_):
 global client
 try:
  client=o.allocate_client_finish(r);client.get_transport_network_registration_status(Qmi.MessageWmsGetTransportNetworkRegistrationStatusInput.new(),10,None,done,None)
 except Exception as e:print(json.dumps({'allocation_error':str(e)}),flush=True);loop.quit()
def opened(o,r,*_):
 try:o.open_finish(r);o.allocate_client(Qmi.Service.WMS,Qmi.CID_NONE,10,None,allocated,None)
 except Exception as e:print(json.dumps({'open_error':str(e)}),flush=True);loop.quit()
def created(o,r,*_):
 global device
 try:device=Qmi.Device.new_finish(r);device.open(Qmi.DeviceOpenFlags.MBIM|Qmi.DeviceOpenFlags.PROXY,10,None,opened,None)
 except Exception as e:print(json.dumps({'create_error':str(e)}),flush=True);loop.quit()
Qmi.Device.new(Gio.File.new_for_path('/dev/cdc-wdm0'),None,created,None)
GLib.timeout_add_seconds(45,lambda:(loop.quit(),False)[1]);loop.run()
