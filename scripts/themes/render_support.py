"""Fail-closed support for isolated native theme/render gates."""
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import struct
import subprocess
import time
import zlib

REQUIRED = ('Commons/Color.qml','Commons/Style.qml','Commons/Util.qml','Commons/BorderGeometry.js',
            'bin/omarchy-theme-set','bin/omarchy-theme-set-templates','bin/omarchy-theme-color','default/themed/shell.toml.tpl')


def verify_official(root):
    try:
        hashes=json.loads((root/'hashes.json').read_text())
        if not isinstance(hashes,dict) or not all(k in hashes for k in REQUIRED):
            raise ValueError('missing official source')
        for name,digest in hashes.items():
            relative=Path(name)
            if relative.is_absolute() or '..' in relative.parts:
                raise ValueError('invalid source path')
            path=root/relative
            if path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest()!=digest:
                raise ValueError('official source hash mismatch')
        return hashes
    except (OSError,ValueError,TypeError) as exc:
        raise RuntimeError('official-source-unavailable-or-changed') from exc


def run_checked(argv, env=None, timeout=20):
    try:
        proc=subprocess.Popen(argv,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,start_new_session=True)
    except OSError as exc:
        raise RuntimeError('dependency-unavailable') from exc
    try:
        output,_=proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        os.killpg(proc.pid,signal.SIGKILL);output,_=proc.communicate()
        raise RuntimeError('render-timeout: '+output.decode(errors='replace')[-6000:]) from exc
    text=output.decode(errors='replace')
    if proc.returncode:
        raise RuntimeError('process-failed: '+text[-6000:])
    return text


def verify_png(data):
    if len(data)<33 or data[:8]!=b'\x89PNG\r\n\x1a\n':
        raise ValueError('missing screenshot')
    offset=8;compressed=bytearray();size=None;ended=False
    while offset+12<=len(data):
        length=struct.unpack('>I',data[offset:offset+4])[0]
        kind=data[offset+4:offset+8];end=offset+12+length
        if end>len(data):raise ValueError('truncated screenshot')
        payload=data[offset+8:offset+8+length]
        if zlib.crc32(kind+payload)!=struct.unpack('>I',data[end-4:end])[0]:raise ValueError('screenshot crc')
        if size is None:
            if kind!=b'IHDR' or length!=13:raise ValueError('missing image header')
            w,h,depth,color,compression,filtering,interlace=struct.unpack('>IIBBBBB',payload)
            if not 1<=w<=4096 or not 1<=h<=4096 or depth!=8 or color not in (2,6) or compression or filtering or interlace:
                raise ValueError('unsupported screenshot format')
            size=(w,h);channels=3 if color==2 else 4
        elif kind==b'IHDR':raise ValueError('duplicate image header')
        if kind==b'IDAT':compressed.extend(payload)
        if kind==b'IEND':
            if length or end!=len(data):raise ValueError('invalid image end')
            ended=True;break
        offset=end
    if not ended or not compressed:raise ValueError('incomplete screenshot')
    expected=(size[0]*channels+1)*size[1]
    decoder=zlib.decompressobj();pixels=decoder.decompress(bytes(compressed),expected+1)
    if len(pixels)!=expected or not decoder.eof or decoder.unused_data:raise ValueError('invalid screenshot pixels')
    stride=size[0]*channels+1
    if any(pixels[n]>4 for n in range(0,len(pixels),stride)):raise ValueError('invalid row filter')
    return size


def verify_outputs(output, required_cases, required_images):
    try:
        receipt=json.loads((output/'results.json').read_text())
        if receipt.get('failed') or not set(required_cases)<=set(receipt.get('passed',[])):
            raise ValueError('missing assertion')
        hashes=receipt.get('source_sha256')
        if not isinstance(hashes,dict) or not hashes or any(not isinstance(v,str) or len(v)!=64 for v in hashes.values()):
            raise ValueError('missing source provenance')
        for name in required_images:
            path=output/name
            if Path(name).name!=name or path.is_symlink():
                raise ValueError('unsafe screenshot')
            data=path.read_bytes()
            size=verify_png(data)
            if isinstance(required_images,dict) and tuple(required_images[name])!=size:
                raise ValueError('screenshot size mismatch')
        return receipt
    except (OSError,ValueError,TypeError,KeyError,zlib.error) as exc:
        raise RuntimeError('render-output-incomplete') from exc


@contextmanager
def compositor(root):
    if os.environ.get('C1_ISOLATED_TEST')!='1':
        raise RuntimeError('isolated-namespace-required')
    for tool in ('sway','qs'):
        if not shutil.which(tool):raise RuntimeError('missing-dependency:'+tool)
    runtime=root/'runtime';runtime.mkdir(mode=0o700)
    config=root/'sway.conf';config.write_text('output HEADLESS-1 resolution 1280x1600\nfor_window [app_id=".*"] floating enable\n')
    env={**os.environ,'XDG_RUNTIME_DIR':str(runtime),'WLR_BACKENDS':'headless','WLR_HEADLESS_OUTPUTS':'1','WLR_RENDERER':'pixman','QT_QPA_PLATFORM':'wayland','QT_QUICK_BACKEND':'software'}
    for key in ('SWAYSOCK','WAYLAND_DISPLAY','DISPLAY','DBUS_SESSION_BUS_ADDRESS','HYPRLAND_INSTANCE_SIGNATURE'):env.pop(key,None)
    with (root/'sway.log').open('w') as log:
        proc=subprocess.Popen(['sway','-c',str(config)],env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        try:
            end=time.monotonic()+10
            while time.monotonic()<end:
                displays=[p for p in runtime.glob('wayland-*') if not p.name.endswith('.lock')]
                if displays:break
                if proc.poll() is not None:raise RuntimeError('compositor-failed')
                time.sleep(.05)
            else:raise RuntimeError('compositor-startup-timeout')
            env['WAYLAND_DISPLAY']=displays[0].name
            yield env
        finally:
            if proc.poll() is None:
                os.killpg(proc.pid,signal.SIGTERM)
                try:proc.wait(timeout=3)
                except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait()
