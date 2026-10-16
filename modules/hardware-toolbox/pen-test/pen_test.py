#!/usr/bin/python3
"""GTK/Wayland pen test. Only count/range summaries are saved; ink stays in RAM."""
import gi
gi.require_version('Gtk','3.0')
from gi.repository import Gtk,Gdk,GLib
import json,time,datetime,os
from pathlib import Path
from metrics import Metrics

class PenTest(Gtk.Window):
 def __init__(self):
  super().__init__(title='触控笔独立测试 · 只用自带笔')
  self.set_default_size(850,640)
  self.phase='idle';self.deadline=0;self.metrics=Metrics();self.ink=[];self.current={};self.latest={};self.saved=False
  self.result=Path(os.environ.get('XDG_STATE_HOME',str(Path.home()/'.local/state')))/'pcadmin-pen-test/latest.json'
  box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=10);box.set_border_width(16);self.add(box)
  self.banner=Gtk.Label(label='先点“开始”，等3秒提示后，只用自带笔在下面画线。');self.banner.set_line_wrap(True);self.banner.set_xalign(0);box.pack_start(self.banner,False,False,0)
  note=Gtk.Label(label='从轻到重画几条线，再斜握笔画线。只有收到真实笔轴数据才显示压力／倾斜。');note.set_line_wrap(True);note.set_xalign(0);box.pack_start(note,False,False,0)
  self.readout=Gtk.Label(label='输入通道：等待输入\n压力：未提供　倾斜：未提供　接触：0');self.readout.set_xalign(0);self.readout.set_line_wrap(True);box.pack_start(self.readout,False,False,0)
  self.bar=Gtk.ProgressBar();self.bar.set_show_text(True);self.bar.set_text('压力：未提供');box.pack_start(self.bar,False,False,0)
  self.area=Gtk.DrawingArea();self.area.set_size_request(240,200);self.area.set_hexpand(True);self.area.set_vexpand(True)
  self.area.add_events(Gdk.EventMask.BUTTON_PRESS_MASK|Gdk.EventMask.BUTTON_RELEASE_MASK|Gdk.EventMask.POINTER_MOTION_MASK|Gdk.EventMask.TOUCH_MASK|Gdk.EventMask.PROXIMITY_IN_MASK|Gdk.EventMask.PROXIMITY_OUT_MASK)
  self.area.connect('event',self.input_event);self.area.connect('draw',self.draw);box.pack_start(self.area,True,True,0)
  row=Gtk.Box(spacing=12);self.start=Gtk.Button(label='开始仅笔测试（30秒）');self.start.set_size_request(-1,48);self.start.connect('clicked',self.arm);row.pack_start(self.start,True,True,0)
  end=Gtk.Button(label='结束本次测试');end.set_size_request(-1,48);end.connect('clicked',lambda _:self.finish(False));row.pack_start(end,True,True,0)
  close=Gtk.Button(label='关闭');close.set_size_request(-1,48);close.connect('clicked',lambda _:self.close());row.pack_start(close,False,False,0);box.pack_start(row,False,False,0)
  self.connect('delete-event',self.closing);GLib.timeout_add(100,self.tick)
 def arm(self,_):
  self.metrics=Metrics();self.ink=[];self.current={};self.latest={};self.saved=False;self.phase='prepare';self.deadline=time.monotonic()+3;self.start.set_sensitive(False);self.area.queue_draw();self.update_readout('等待输入')
 def tick(self):
  if self.phase=='prepare':
   left=self.deadline-time.monotonic();self.banner.set_text('准备：%d 秒后开始。请放开手指，拿好自带笔。'%max(1,int(left)+1))
   if left<=0:self.phase='running';self.deadline=time.monotonic()+30
  elif self.phase=='running':
   left=self.deadline-time.monotonic();self.banner.set_text('现在只用自带笔在画板内画线；剩余 %d 秒。不要用手指画。'%max(0,int(left)+1))
   if left<=0:self.finish(True)
  return True
 def source(self,event):
  dev=event.get_source_device() or event.get_device()
  source=dev.get_source() if dev else None
  name={Gdk.InputSource.PEN:'pen',Gdk.InputSource.ERASER:'eraser',Gdk.InputSource.TOUCHSCREEN:'touch',Gdk.InputSource.MOUSE:'mouse'}.get(source,'other')
  axes={k:None for k in ('pressure','xtilt','ytilt')}
  if name in ('pen','eraser') and dev:
   flags=dev.get_axes()
   for key,use,flag in [('pressure',Gdk.AxisUse.PRESSURE,Gdk.AxisFlags.PRESSURE),('xtilt',Gdk.AxisUse.XTILT,Gdk.AxisFlags.XTILT),('ytilt',Gdk.AxisUse.YTILT,Gdk.AxisFlags.YTILT)]:
    if flags&flag:
     ok,value=event.get_axis(use)
     if ok:axes[key]=value
  return name,axes
 def input_event(self,widget,event):
  typ=event.type
  relevant=(Gdk.EventType.TOUCH_BEGIN,Gdk.EventType.TOUCH_UPDATE,Gdk.EventType.TOUCH_END,Gdk.EventType.TOUCH_CANCEL,Gdk.EventType.BUTTON_PRESS,Gdk.EventType.BUTTON_RELEASE,Gdk.EventType.MOTION_NOTIFY,Gdk.EventType.PROXIMITY_IN,Gdk.EventType.PROXIMITY_OUT)
  if typ not in relevant:return False
  if self.phase!='running':return True
  name,axes=self.source(event)
  # Real touch events are processed directly; ignore their duplicate emulated mouse stream.
  touch=typ in (Gdk.EventType.TOUCH_BEGIN,Gdk.EventType.TOUCH_UPDATE,Gdk.EventType.TOUCH_END,Gdk.EventType.TOUCH_CANCEL)
  if name=='touch' and not touch:return True
  begin=typ in (Gdk.EventType.TOUCH_BEGIN,Gdk.EventType.BUTTON_PRESS)
  ending=typ in (Gdk.EventType.TOUCH_END,Gdk.EventType.TOUCH_CANCEL,Gdk.EventType.BUTTON_RELEASE,Gdk.EventType.PROXIMITY_OUT)
  self.metrics.add(name,begin,axes);self.latest=axes;self.update_readout(name)
  ok,x,y=event.get_coords()
  # This is a single-pen canvas: boxed event-sequence wrapper identities can vary.
  key='touch' if touch else 'pointer'
  if begin:
   stroke=[];self.ink.append(stroke);self.current[key]=stroke
  if ok and key in self.current:
   stroke=self.current[key]
   if sum(len(s) for s in self.ink)<12000:stroke.append((x,y,axes['pressure']))
  if ending:self.current.pop(key,None)
  self.area.queue_draw();return True
 def update_readout(self,name):
  label={'pen':'主动笔通道','eraser':'笔橡皮通道','touch':'触摸通道（手指／无源笔不能由系统区分）','mouse':'鼠标／兼容指针通道'}.get(name,name)
  p=self.latest.get('pressure');x=self.latest.get('xtilt');y=self.latest.get('ytilt')
  self.readout.set_text('输入通道：%s\n压力：%s　倾斜X/Y（归一值）：%s / %s\n接触：%d　事件：%d'%(label,'未提供' if p is None else '%.3f'%p,'未提供' if x is None else '%.3f'%x,'未提供' if y is None else '%.3f'%y,self.metrics.contacts,self.metrics.events))
  self.bar.set_fraction(0 if p is None else max(0,min(1,p)));self.bar.set_text('压力：未提供' if p is None else '压力 %.3f'%p)
 def draw(self,widget,cr):
  cr.set_source_rgb(.07,.09,.12);cr.paint();cr.set_line_cap(1);cr.set_line_join(1)
  cr.set_source_rgba(.5,.6,.7,.25);cr.set_line_width(1);w=widget.get_allocated_width();h=widget.get_allocated_height();cr.move_to(w/2,0);cr.line_to(w/2,h);cr.move_to(0,h/2);cr.line_to(w,h/2);cr.stroke()
  cr.set_source_rgb(.6,.95,.65)
  for stroke in self.ink:
   for i,point in enumerate(stroke):
    x,y,p=point;cr.set_line_width(3 if p is None else 1+6*max(0,min(1,p)))
    if i==0:cr.arc(x,y,1.5,0,6.284);cr.fill()
    else:cr.move_to(stroke[i-1][0],stroke[i-1][1]);cr.line_to(x,y);cr.stroke()
 def finish(self,complete):
  if self.phase not in ('running','prepare'):return
  self.phase='finished';self.current={};self.start.set_sensitive(True)
  result=self.metrics.summary();result.update(observed_at=datetime.datetime.now().astimezone().isoformat(),complete=complete,protocol='pen-test/1',declared_input='user instructed to use factory pen only inside canvas',privacy='counts and axis ranges only; no ink coordinates stored')
  self.result.parent.mkdir(parents=True,exist_ok=True);tmp=self.result.with_suffix('.tmp');tmp.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');tmp.chmod(0o600);tmp.replace(self.result);self.saved=True
  message='收到 %d 次接触，%d 个事件。'%(self.metrics.contacts,self.metrics.events)
  if self.metrics.events==0:message+='画板没有收到输入信号。'
  elif self.metrics.axes['pressure'] is None:message+='本次没有真实压力数据。'
  self.banner.set_text('测试结束：'+message+' 可以重新测试，结果已保存（不含笔迹）。')
 def closing(self,*_):
  self.finish(False);Gtk.main_quit();return False

if __name__=='__main__':
 GLib.set_prgname('pcadmin-pen-test');window=PenTest();window.show_all();Gtk.main()
