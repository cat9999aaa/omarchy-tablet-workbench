#!/usr/bin/python3
"""Observe ONLY the verified Dell touchscreen; never grab/inject/read keyboard.

Raw coordinates stay in memory. Only a fixed gesture token reaches the user.
"""
import fcntl
import json
import os
from pathlib import Path
import select
import socket
import struct
import sys
import time
from gesture_model import TouchFrames

NAME='eGalax Inc. eGalaxTouch P80H84 0710 vA1_N k47_45'
EVENT=struct.Struct('llHHi')

def device():
    for p in Path('/sys/class/input').glob('event*'):
        try:
            if (p/'device/name').read_text().strip()!=NAME:continue
            for parent in (p/'device').resolve().parents:
                if (parent/'idVendor').exists():
                    if (parent/'idVendor').read_text().strip()=='0eef' and (parent/'idProduct').read_text().strip()=='c003':return '/dev/input/'+p.name
                    break
        except OSError:continue
    return None

def axis(fd,code):
    value=struct.unpack('iiiiii',fcntl.ioctl(fd,0x80000000|(24<<16)|(ord('E')<<8)|(0x40+code),bytes(24)))
    if value[2]<=value[1]:raise ValueError('No valid multitouch axis')
    return value[1],value[2]

def status(connected,count):
    p=Path('/run/pcadmin-gesture/state.json');tmp=p.with_suffix('.tmp')
    tmp.write_text(json.dumps({'connected':connected,'recognized':count,'observed_at':time.time()}));tmp.chmod(0o644);os.replace(tmp,p)

def main():
    if os.geteuid()!=0 or len(sys.argv)!=2 or not sys.argv[1].isdigit() or int(sys.argv[1])<=0:raise ValueError('Dedicated root service with fixed non-root recipient UID required')
    address=f'/run/user/{int(sys.argv[1])}/pcadmin-control-center/gesture.sock'
    count=0;sock=socket.socket(socket.AF_UNIX,socket.SOCK_DGRAM)
    while True:
        target=device()
        if not target:status(False,count);time.sleep(5);continue
        fd=None
        try:
            fd=os.open(target,os.O_RDONLY|os.O_NONBLOCK)
            xmin,xmax=axis(fd,53);ymin,ymax=axis(fd,54)
            stream=TouchFrames(xmin,xmax,ymin,ymax);buffer=b''
            status(True,count)
            while True:
                if not select.select([fd],[],[],5)[0]:status(True,count);continue
                chunk=os.read(fd,EVENT.size*64)
                if not chunk:break
                buffer+=chunk
                while len(buffer)>=EVENT.size:
                    _,_,kind,code,value=EVENT.unpack(buffer[:EVENT.size]);buffer=buffer[EVENT.size:]
                    if stream.event(kind,code,value,time.monotonic()):
                        count+=1;status(True,count)
                        try:sock.sendto(b'three-finger-down',address)
                        except OSError:pass
        except (OSError,ValueError):status(False,count);time.sleep(2)
        finally:
            if fd is not None:os.close(fd)

if __name__=='__main__':main()
