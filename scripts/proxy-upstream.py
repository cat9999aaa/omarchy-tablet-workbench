#!/usr/bin/python3
"""Allowlisted public release metadata; never downloads or installs cores."""
import argparse
import json
import os
from pathlib import Path
import re
import time
import urllib.error
import urllib.request
SOURCES={'XTLS/Xray-core':('core','Xray-linux-64.zip'),'SagerNet/sing-box':('core',None),'Loyalsoldier/v2ray-rules-dat':('rules','geosite.dat'),'cat9999aaa/omarchy-tablet-workbench':('application',None)}
class NoRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,*args,**kwargs):return None

def normalize(repo,value,now):
 if repo not in SOURCES or not isinstance(value,dict):raise ValueError('unsupported_source')
 version=value.get('tag_name','')
 if value.get('prerelease') is not False or value.get('draft') is not False or not re.fullmatch(r'[A-Za-z0-9._+-]{1,80}',version) or any(s in version.lower() for s in ('-rc','beta','alpha','nightly','preview')):raise ValueError('not_stable')
 base='https://github.com/'+repo
 if value.get('html_url')!=base+'/releases/tag/'+version:raise ValueError('source_mismatch')
 assets=value.get('assets',[])
 if not isinstance(assets,list) or len(assets)>256:raise ValueError('invalid_assets')
 wanted=SOURCES[repo][1];selected=[]
 for a in assets:
  if not isinstance(a,dict):raise ValueError('invalid_asset')
  name=a.get('name','');url=a.get('browser_download_url','')
  if not isinstance(name,str) or not re.fullmatch(r'[A-Za-z0-9._+-]{1,160}',name):continue
  if url!=base+'/releases/download/'+version+'/'+name:raise ValueError('source_mismatch')
  if name==wanted or repo=='SagerNet/sing-box' and name.endswith('-linux-amd64.tar.gz'):selected.append(a)
 digest=None
 if len(selected)==1:
  declared=selected[0].get('digest')
  if declared is not None:
   if not re.fullmatch(r'sha256:[0-9a-fA-F]{64}',declared):raise ValueError('invalid_digest')
   digest=declared[7:].lower()
 return {'kind':SOURCES[repo][0],'source':base,'version':version,'digest':digest,'observed_digest':None,'prerelease':False,'observed_at':now,'compatibility':'unverified'}

def collect():
 now=int(time.time());proposals=[];checks=[]
 opener=urllib.request.build_opener(NoRedirect())
 for repo in SOURCES:
  headers={'Accept':'application/vnd.github+json','User-Agent':'omarchy-tablet-proxy-update-check','X-GitHub-Api-Version':'2022-11-28'}
  token=os.environ.get('GH_TOKEN')
  if token:headers['Authorization']='Bearer '+token
  request=urllib.request.Request('https://api.github.com/repos/'+repo+'/releases/latest',headers=headers)
  try:
   with opener.open(request,timeout=10) as response:data=response.read(1024*1024+1)
   if len(data)>1024*1024:raise ValueError('metadata_too_large')
   proposals.append(normalize(repo,json.loads(data),now));checks.append({'source':repo,'status':'observed'})
  except urllib.error.HTTPError as e:checks.append({'source':repo,'status':'no_release' if e.code==404 else 'unavailable'})
  except (OSError,ValueError,TypeError):checks.append({'source':repo,'status':'unavailable'})
 return {'schema':1,'observed_at':now,'proposals':proposals,'checks':checks}

if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--online',action='store_true',required=True);parser.add_argument('--output',type=Path)
 args=parser.parse_args();data=json.dumps(collect(),ensure_ascii=False,indent=2)+'\n'
 if args.output:
  args.output.parent.mkdir(parents=True,exist_ok=True)
  fd=os.open(args.output,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
  with os.fdopen(fd,'w') as f:f.write(data)
 else:print(data,end='')
