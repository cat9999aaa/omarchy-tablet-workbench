"""Transactional local history; only latest raw process counters are retained."""
import sqlite3,json,os,datetime
from pathlib import Path
from sessions import update_cache,rank_apps

def encode(value):return json.dumps(value,separators=(',',':'),ensure_ascii=False)

def add_activity(conn,sample_id,previous,snapshot):
    if previous is None:return
    for a in rank_apps([previous,snapshot],'all'):
        conn.execute('INSERT INTO activity VALUES(?,?,?,?,?,?,?)',(sample_id,a['name'],a['cpu_seconds'],a['observed_seconds'],a['visible_samples'],a['background_samples'],a['unknown_samples']))

def open_store(path):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    if path.parent.name=='pcadmin-battery':path.parent.chmod(0o700)
    if not path.exists():
        fd=os.open(path,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600);os.close(fd)
    path.chmod(0o600)
    c=sqlite3.connect(path,timeout=2);c.execute('PRAGMA foreign_keys=ON')
    version=c.execute('PRAGMA user_version').fetchone()[0]
    if version not in (0,1,2):c.close();raise sqlite3.DatabaseError('unsupported schema')
    with c:
        c.execute('CREATE TABLE IF NOT EXISTS sample (id INTEGER PRIMARY KEY AUTOINCREMENT,wall_time TEXT NOT NULL,boot_id TEXT,boottime_s REAL,monotonic_s REAL,payload_json TEXT NOT NULL)')
        c.execute('CREATE INDEX IF NOT EXISTS sample_time ON sample(wall_time)')
        c.execute('CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY,value TEXT NOT NULL)')
        c.execute('CREATE TABLE IF NOT EXISTS activity (sample_id INTEGER REFERENCES sample(id) ON DELETE CASCADE,name TEXT,cpu_seconds REAL,observed_seconds REAL,visible_samples INTEGER,background_samples INTEGER,unknown_samples INTEGER,PRIMARY KEY(sample_id,name))')
        if version==1:
            previous=None;cache=None
            for sid,payload in c.execute('SELECT id,payload_json FROM sample ORDER BY id').fetchall():
                s=json.loads(payload);add_activity(c,sid,previous,s)
                cache=update_cache(previous,s,cache)
                if previous is None or previous['boot_id']!=s['boot_id'] or previous['external_power']!=s['external_power']:cache['_session_start_id']=sid
                compact={**s,'processes':[]};c.execute('UPDATE sample SET payload_json=? WHERE id=?',(encode(compact),sid));previous=s
            if previous:
                c.execute("INSERT OR REPLACE INTO metadata VALUES('last_processes',?)",(encode(previous['processes']),))
                c.execute("INSERT OR REPLACE INTO metadata VALUES('status',?)",(encode(cache),))
        c.execute('PRAGMA user_version=2')
    return c

def open_reader(path):
    c=sqlite3.connect(Path(path).resolve().as_uri()+'?mode=ro',uri=True,timeout=2)
    if c.execute('PRAGMA user_version').fetchone()[0]!=2:c.close();raise sqlite3.DatabaseError('unsupported schema')
    return c

def read_cache(conn):
    row=conn.execute("SELECT value FROM metadata WHERE key='status'").fetchone()
    return json.loads(row[0]) if row else None

def append_sample(conn,snapshot):
    cutoff=(datetime.datetime.fromisoformat(snapshot['wall_time'])-datetime.timedelta(days=90)).isoformat()
    with conn:
        previous_row=conn.execute('SELECT payload_json FROM sample ORDER BY id DESC LIMIT 1').fetchone()
        previous=json.loads(previous_row[0]) if previous_row else None
        raw=conn.execute("SELECT value FROM metadata WHERE key='last_processes'").fetchone()
        if previous:previous['processes']=json.loads(raw[0]) if raw else []
        cache=update_cache(previous,snapshot,read_cache(conn))
        compact={**snapshot,'processes':[]}
        cur=conn.execute('INSERT INTO sample(wall_time,boot_id,boottime_s,monotonic_s,payload_json) VALUES(?,?,?,?,?)',
             (snapshot['wall_time'],snapshot['boot_id'],snapshot['boottime_s'],snapshot['monotonic_s'],encode(compact)))
        sid=cur.lastrowid
        if previous is None or previous['boot_id']!=snapshot['boot_id'] or previous['external_power']!=snapshot['external_power']:cache['_session_start_id']=sid
        add_activity(conn,sid,previous,snapshot)
        conn.execute("INSERT OR REPLACE INTO metadata VALUES('last_processes',?)",(encode(snapshot['processes']),))
        conn.execute("INSERT OR REPLACE INTO metadata VALUES('status',?)",(encode(cache),))
        conn.execute('DELETE FROM sample WHERE wall_time < ?',(cutoff,))
    return sid

def read_samples(conn,since_iso=None):
    sql='SELECT payload_json FROM sample';params=()
    if since_iso:sql+=' WHERE wall_time >= ?';params=(since_iso,)
    return [json.loads(row[0]) for row in conn.execute(sql+' ORDER BY id',params)]

def read_history_samples(conn,since_iso):return read_samples(conn,since_iso)

def read_activity(conn,start_id=None,since_iso=None):
    where='a.sample_id > ?' if start_id is not None else 's.wall_time >= ?';arg=start_id if start_id is not None else since_iso
    rows=conn.execute('SELECT a.name,SUM(a.cpu_seconds),SUM(a.observed_seconds),SUM(a.visible_samples),SUM(a.background_samples),SUM(a.unknown_samples) FROM activity a JOIN sample s ON s.id=a.sample_id WHERE '+where+' GROUP BY a.name ORDER BY SUM(a.cpu_seconds) DESC LIMIT 30',(arg,))
    keys=['name','cpu_seconds','observed_seconds','visible_samples','background_samples','unknown_samples']
    return [dict(zip(keys,row)) for row in rows]
