#!/usr/bin/python3
"""Read-only migration stream. Contains secrets: pipe only to the private importer."""
import json
import sqlite3
import sys
from pathlib import Path


def migrate(path):
    db=sqlite3.connect(Path(path).resolve().as_uri()+'?mode=ro',uri=True)
    db.row_factory=sqlite3.Row
    rows=db.execute('SELECT * FROM ProfileItem LIMIT 4097').fetchall()
    if len(rows)>4096:raise ValueError('limit')
    nodes=[]
    for row in rows:
        r=dict(row)
        if r.get('ConfigType')!=5:raise ValueError('unsupported_protocol')
        for key in ['Extra','Cert','CertSha','EchConfigList','VerifyPeerCertByName','Finalmask','Mldsa65Verify']:
            if r.get(key) not in (None,'','{}','[]'):raise ValueError('unsupported_field')
        proto=json.loads(r.get('ProtoExtra') or '{}')
        transport=json.loads(r.get('TransportExtra') or '{}')
        if set(proto)-{'Flow','VlessEncryption'} or set(transport)-{'Host','Path','RawHeaderType'}:raise ValueError('unsupported_extra')
        if proto.get('VlessEncryption') not in (None,'','none') or transport.get('RawHeaderType') not in (None,'','none'):raise ValueError('unsupported_extra')
        if str(r.get('AllowInsecure','')).lower() not in ('','none','false','0'):raise ValueError('insecure_tls')
        if r.get('MuxEnabled') not in (None,False,0):raise ValueError('unsupported_mux')
        nodes.append(dict(id='',name=r.get('Remarks') or '导入节点',server=r['Address'],port=r['Port'],credential=r['Password'],security=r.get('StreamSecurity') or '',transport={'raw':'tcp'}.get(r.get('Network'),r.get('Network') or 'tcp'),path=transport.get('Path') or r.get('Path') or '',host=transport.get('Host') or r.get('RequestHost') or '',sni=r.get('Sni') or '',fingerprint=r.get('Fingerprint') or '',public_key=r.get('PublicKey') or '',short_id=r.get('ShortId') or '',spider_x=r.get('SpiderX') or '',flow=proto.get('Flow') or r.get('Flow') or '',alpn=[a for a in (r.get('Alpn') or '').split(',') if a]))
    return nodes

if __name__=='__main__':
    try:
        if len(sys.argv)!=2:raise ValueError('usage')
        print(json.dumps(migrate(sys.argv[1])))
    except Exception:
        print('{"error_code":"migration_unsupported"}');sys.exit(1)
