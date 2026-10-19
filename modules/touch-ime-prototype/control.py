#!/usr/bin/python3
"""P1 entry: native panel only; retired desktop keyboard never reopens."""
import subprocess

def output(*args):
    try:return subprocess.check_output(args,text=True,stderr=subprocess.DEVNULL,timeout=3).strip()
    except (subprocess.SubprocessError,OSError):return ''
def execute(args):
    try:return subprocess.run(args,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=5).returncode==0
    except (subprocess.SubprocessError,OSError):return False
def main():
    if output('omarchy-shell','lock','isLocked')!='false':return
    if output('omarchy-shell','omtInput','ready')=='true':
        if execute(['omarchy-shell','omtInput','toggle']):return
    execute(['notify-send','触屏输入法','输入服务尚未就绪，请稍后再按 P1；不会切换到旧键盘'])
if __name__=='__main__':main()
