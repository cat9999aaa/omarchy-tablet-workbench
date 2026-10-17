#!/usr/bin/python3
"""P1 entry: native panel only; retired desktop keyboard never reopens."""
from pathlib import Path
import json, subprocess

OLD=str(Path.home()/'.local/bin/pcadmin-keyboard')
def output(*args):
    try:return subprocess.check_output(args,text=True,stderr=subprocess.DEVNULL,timeout=3).strip()
    except (subprocess.SubprocessError,OSError):return ''
def execute(args):
    try:return subprocess.run(args,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=5).returncode==0
    except (subprocess.SubprocessError,OSError):return False
def old_visible():
    try:
        return any(s.get('namespace')=='wvkbd' for m in json.loads(output('hyprctl','layers','-j')).values() for group in m['levels'].values() for s in group)
    except (ValueError,KeyError,TypeError):return False
def main():
    if output('omarchy-shell','lock','isLocked')=='true':return
    if output('omarchy-shell','omtInput','ready')=='true':
        if old_visible() and not execute([OLD,'hide']):return
        if execute(['omarchy-shell','omtInput','toggle']):return
    execute(['notify-send','触屏输入法','输入服务尚未就绪，请稍后再按 P1；不会切换到旧键盘'])
if __name__=='__main__':main()
