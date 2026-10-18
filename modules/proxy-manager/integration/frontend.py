"""Preserve installed TUN transport; business routing has one Xray authority."""
from copy import deepcopy
CORE='/opt/v2rayn-bin/bin/xray/xray'
def build(config):
 c=deepcopy(config)
 if not isinstance(c,dict) or len(c.get('inbounds',[]))!=1 or c['inbounds'][0].get('type')!='tun':raise ValueError('unsupported_frontend')
 out={o.get('tag'):o for o in c.get('outbounds',[])}
 proxy=out.get('proxy',{})
 if proxy.get('type')!='socks' or proxy.get('server')!='127.0.0.1' or proxy.get('server_port')!=10808 or any(k in proxy for k in ('username','password')) or out.get('direct',{}).get('type')!='direct':raise ValueError('unsupported_frontend_listener')
 route=c.get('route',{});rules=route.get('rules')
 if not isinstance(rules,list):raise ValueError('unsupported_frontend_rules')
 keep=[];bypass=False;lan=False
 for rule in rules:
  if not isinstance(rule,dict):raise ValueError('unsupported_frontend_rule')
  action=rule.get('action')
  if action is not None:
   if action not in ('reject','sniff','hijack-dns'):raise ValueError('unsupported_frontend_action')
   keep.append(rule);continue
  if 'process_path' in rule:
   if set(rule)-{'process_path','outbound'} or rule.get('outbound')!='direct':raise ValueError('unsupported_process_bypass')
   bypass|=CORE in rule['process_path'];keep.append(rule);continue
  if rule.get('ip_is_private') is True:
   if set(rule)-{'ip_is_private','outbound'} or rule.get('outbound')!='direct':raise ValueError('unsupported_lan_bypass')
   lan=True;keep.append(rule);continue
  # Only the known legacy business-rule shapes can be removed.
  if set(rule)-{'outbound','rule_set','ip_cidr','domain_suffix','clash_mode'} or rule.get('outbound') not in ('proxy','direct'):raise ValueError('unsupported_business_rule')
 if not bypass or not lan:raise ValueError('transport_protection_missing')
 route['rules']=keep;route['final']='proxy';c['route']=route
 return c
