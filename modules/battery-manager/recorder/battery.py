#!/usr/bin/env python3
"""One-shot recorder and read-only JSON interface for the native power panel."""
import argparse,datetime,json,os,sqlite3,sys
from pathlib import Path
from collect import collect_snapshot,clock_snapshot,display_snapshot
from store import open_store,open_reader,append_sample,read_samples,read_cache,read_history_samples,read_activity
from sessions import build_status,build_history,rank_apps,delta

def main():
    parser=argparse.ArgumentParser();parser.add_argument('command',choices=['record','status','history','apps']);parser.add_argument('--db',type=Path,default=Path(os.environ.get('XDG_STATE_HOME',str(Path.home()/'.local/state')))/'pcadmin-battery/history.sqlite3');parser.add_argument('--days',type=int,default=7);parser.add_argument('--period',choices=['session','24h'],default='session');args=parser.parse_args()
    try:
        if args.command=='record':
            s=collect_snapshot(display=display_snapshot())
            with open_store(args.db) as c:sample_id=append_sample(c,s)
            out={'schema':1,'available':True,'recorded_at':s['wall_time'],'sample_id':sample_id}
        elif not args.db.exists():out={'schema':1,'available':False,'reason':'not-started'}
        else:
            with open_reader(args.db) as c:
                if args.command=='status':
                    out=read_cache(c) or {'schema':1,'available':False,'reason':'not-started'}
                    last=c.execute('SELECT boot_id,boottime_s,monotonic_s FROM sample ORDER BY id DESC LIMIT 1').fetchone()
                    age=delta({'boot_id':last[0],'boottime_s':last[1],'monotonic_s':last[2]},clock_snapshot()) if last else None
                    out['stale']=age is None or age[0]>180
                    out={k:v for k,v in out.items() if not k.startswith('_')}
                elif args.command=='apps':
                    cache=read_cache(c)
                    cutoff=(datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8)))-datetime.timedelta(days=1)).isoformat() if args.period=='24h' else cache['current_session']['observed_start'] if cache else None
                    rows=read_activity(c,cache.get('_session_start_id',0) if cache and args.period=='session' else None,cutoff)
                    out={'schema':1,'available':True,'period':args.period,'apps':rows}
                else:
                    days=max(1,min(90,args.days));cutoff=(datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8)))-datetime.timedelta(days=days)).isoformat()
                    out=build_history(read_history_samples(c,cutoff))
        print(json.dumps(out,ensure_ascii=False,separators=(',',':'),allow_nan=False));return 0
    except (sqlite3.Error,OSError,ValueError,KeyError,TypeError) as error:
        reason='database-locked' if isinstance(error,sqlite3.OperationalError) and 'locked' in str(error) else 'database-error' if isinstance(error,sqlite3.Error) else 'record-error'
        print(json.dumps({'schema':1,'available':False,'reason':reason}));return 1
if __name__=='__main__':sys.exit(main())
