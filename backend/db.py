from __future__ import annotations
from pathlib import Path
import json, sqlite3, time
from typing import Any

DB_PATH = Path(__file__).resolve().parent / "astranex.db"
UPLOAD_DIR = Path(__file__).resolve().parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _ensure_column(conn, table: str, column: str, definition: str):
    cols = {r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    if column not in cols:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def init_db():
    conn = get_conn()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS farmer_profiles (
      id INTEGER PRIMARY KEY CHECK (id=1),
      name TEXT NOT NULL,
      crops_json TEXT NOT NULL,
      state TEXT,
      district TEXT,
      latitude REAL,
      longitude REAL,
      location_source TEXT DEFAULT 'manual',
      field_name TEXT DEFAULT 'My Field',
      area_acres REAL,
      soil_type TEXT DEFAULT 'unknown',
      created_at REAL NOT NULL,
      updated_at REAL NOT NULL
    );
    CREATE TABLE IF NOT EXISTS fields (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      field_code TEXT UNIQUE NOT NULL,
      name TEXT NOT NULL,
      crop TEXT,
      area_acres REAL,
      created_at REAL NOT NULL,
      updated_at REAL NOT NULL
    );
    CREATE TABLE IF NOT EXISTS crop_cycles (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      field_id INTEGER NOT NULL,
      crop TEXT NOT NULL,
      variety TEXT,
      growth_stage TEXT,
      started_at REAL,
      ended_at REAL,
      FOREIGN KEY(field_id) REFERENCES fields(id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS observations (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      created_at REAL NOT NULL,
      field_id INTEGER,
      crop TEXT NOT NULL,
      condition TEXT,
      growth_stage TEXT,
      soil_moisture REAL,
      temperature REAL,
      humidity REAL,
      weather TEXT,
      connectivity TEXT,
      sensor_reliability REAL,
      image_quality REAL,
      image_ref TEXT,
      result_json TEXT NOT NULL,
      source TEXT DEFAULT 'simulator',
      sync_status TEXT DEFAULT 'synced',
      client_event_id TEXT,
      FOREIGN KEY(field_id) REFERENCES fields(id) ON DELETE SET NULL
    );
    CREATE TABLE IF NOT EXISTS images (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      observation_id INTEGER,
      field_id INTEGER,
      path TEXT NOT NULL,
      original_name TEXT,
      mime_type TEXT,
      size_bytes INTEGER,
      created_at REAL NOT NULL,
      FOREIGN KEY(observation_id) REFERENCES observations(id) ON DELETE SET NULL,
      FOREIGN KEY(field_id) REFERENCES fields(id) ON DELETE SET NULL
    );
    CREATE TABLE IF NOT EXISTS sensor_readings (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      device_id TEXT,
      field_id INTEGER,
      soil_moisture REAL,
      temperature REAL,
      humidity REAL,
      recorded_at REAL NOT NULL,
      received_at REAL NOT NULL,
      health_json TEXT,
      FOREIGN KEY(field_id) REFERENCES fields(id) ON DELETE SET NULL
    );
    CREATE TABLE IF NOT EXISTS devices (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      device_id TEXT UNIQUE NOT NULL,
      field_id INTEGER,
      last_seen REAL,
      connection_state TEXT DEFAULT 'unknown',
      sensor_health_json TEXT DEFAULT '{}',
      firmware_version TEXT,
      battery REAL,
      FOREIGN KEY(field_id) REFERENCES fields(id) ON DELETE SET NULL
    );
    CREATE TABLE IF NOT EXISTS irrigation_events (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      field_id INTEGER,
      observation_id INTEGER,
      requested_at REAL NOT NULL,
      duration_min REAL DEFAULT 0,
      status TEXT NOT NULL,
      reason TEXT,
      simulated INTEGER NOT NULL DEFAULT 1,
      FOREIGN KEY(field_id) REFERENCES fields(id) ON DELETE SET NULL,
      FOREIGN KEY(observation_id) REFERENCES observations(id) ON DELETE SET NULL
    );
    CREATE TABLE IF NOT EXISTS alerts (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      field_id INTEGER,
      observation_id INTEGER,
      severity TEXT NOT NULL,
      kind TEXT NOT NULL,
      reason TEXT NOT NULL,
      next_step TEXT,
      created_at REAL NOT NULL,
      resolved_at REAL,
      FOREIGN KEY(field_id) REFERENCES fields(id) ON DELETE SET NULL,
      FOREIGN KEY(observation_id) REFERENCES observations(id) ON DELETE SET NULL
    );
    CREATE TABLE IF NOT EXISTS feedback (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      created_at REAL NOT NULL,
      observation_id INTEGER,
      useful INTEGER NOT NULL,
      label TEXT DEFAULT '',
      note TEXT DEFAULT '',
      FOREIGN KEY(observation_id) REFERENCES observations(id) ON DELETE SET NULL
    );
    CREATE TABLE IF NOT EXISTS sync_queue (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      created_at REAL NOT NULL,
      payload_json TEXT NOT NULL,
      status TEXT NOT NULL DEFAULT 'PENDING',
      retry_count INTEGER NOT NULL DEFAULT 0,
      last_attempt REAL,
      error TEXT,
      client_event_id TEXT UNIQUE
    );
    """)
    # Backward-compatible upgrades for the original observations/feedback schema.
    _ensure_column(conn, "observations", "field_id", "INTEGER")
    _ensure_column(conn, "observations", "image_ref", "TEXT")
    _ensure_column(conn, "observations", "source", "TEXT DEFAULT 'simulator'")
    _ensure_column(conn, "observations", "sync_status", "TEXT DEFAULT 'synced'")
    _ensure_column(conn, "feedback", "label", "TEXT DEFAULT ''")
    _ensure_column(conn, "sync_queue", "status", "TEXT DEFAULT 'PENDING'")
    _ensure_column(conn, "sync_queue", "retry_count", "INTEGER DEFAULT 0")
    _ensure_column(conn, "sync_queue", "last_attempt", "REAL")
    _ensure_column(conn, "sync_queue", "error", "TEXT")
    _ensure_column(conn, "sync_queue", "client_event_id", "TEXT")
    _ensure_column(conn, "observations", "client_event_id", "TEXT")
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_observations_client_event ON observations(client_event_id) WHERE client_event_id IS NOT NULL")
    conn.commit()
    # Seed one demo field only if none exists.
    if conn.execute("SELECT COUNT(*) FROM fields").fetchone()[0] == 0:
        now = time.time()
        conn.execute("INSERT INTO fields(field_code,name,crop,created_at,updated_at) VALUES(?,?,?,?,?)",
                     ("FIELD-001", "Demo Field A", "tomato", now, now))
        conn.commit()
    conn.close()


def _json(v: Any) -> str:
    return json.dumps(v, separators=(",", ":"), ensure_ascii=False)


def save_observation(payload: dict, result: dict, *, image_ref: str | None = None,
                     source: str = "simulator", sync_status: str = "synced") -> int:
    conn = get_conn()
    field_id = payload.get('field_id')
    event_id = payload.get('client_event_id')
    if event_id:
        existing = conn.execute("SELECT id FROM observations WHERE client_event_id=?", (event_id,)).fetchone()
        if existing:
            conn.close()
            return int(existing['id'])
    cur = conn.execute("""INSERT INTO observations
      (created_at,field_id,crop,condition,growth_stage,soil_moisture,temperature,humidity,weather,connectivity,sensor_reliability,image_quality,image_ref,result_json,source,sync_status,client_event_id)
      VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
        time.time(), field_id, payload.get('crop', 'tomato'), payload.get('condition'), payload.get('growth_stage'),
        payload.get('soil_moisture'), payload.get('temperature'), payload.get('humidity'), payload.get('weather'),
        payload.get('connectivity'), payload.get('sensor_reliability', 1), payload.get('image_quality', 1),
        image_ref or payload.get('image_ref'), _json(result), source, sync_status, event_id
    ))
    oid = cur.lastrowid
    ref = image_ref or payload.get('image_ref')
    if ref:
        conn.execute("INSERT INTO images(observation_id,field_id,path,original_name,mime_type,size_bytes,created_at) VALUES(?,?,?,?,?,?,?)",
                     (oid, field_id, ref, payload.get('image_name'), payload.get('image_mime'), payload.get('image_size'), time.time()))
    conn.commit(); conn.close()
    return oid


def recent_observations(limit=30, field_id=None):
    conn = get_conn()
    if field_id:
        rows = conn.execute("SELECT * FROM observations WHERE field_id=? ORDER BY id DESC LIMIT ?", (field_id, limit)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM observations ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    conn.close()
    out=[]
    for r in rows:
        d=dict(r); d['result']=json.loads(d.pop('result_json')); out.append(d)
    return out


def save_feedback(observation_id, useful, note='', label=''):
    conn=get_conn(); conn.execute("INSERT INTO feedback(created_at,observation_id,useful,label,note) VALUES(?,?,?,?,?)",
                                   (time.time(),observation_id,int(bool(useful)),label,note)); conn.commit(); conn.close()


def save_sensor_reading(data: dict, health: dict):
    conn=get_conn(); now=time.time()
    field_id=data.get('field_id')
    conn.execute("""INSERT INTO sensor_readings(device_id,field_id,soil_moisture,temperature,humidity,recorded_at,received_at,health_json)
                    VALUES(?,?,?,?,?,?,?,?)""", (data.get('device_id'),field_id,data.get('soil_moisture'),data.get('temperature'),data.get('humidity'),data.get('timestamp') or now,now,_json(health)))
    conn.execute("""INSERT INTO devices(device_id,field_id,last_seen,connection_state,sensor_health_json,firmware_version,battery)
                    VALUES(?,?,?,?,?,?,?) ON CONFLICT(device_id) DO UPDATE SET field_id=excluded.field_id,last_seen=excluded.last_seen,
                    connection_state=excluded.connection_state,sensor_health_json=excluded.sensor_health_json,firmware_version=excluded.firmware_version,battery=excluded.battery""",
                 (data.get('device_id','unknown'),field_id,now,'connected',_json(health),data.get('firmware_version'),data.get('battery')))
    conn.commit(); conn.close()


def latest_sensors(field_id=None, limit=50):
    conn=get_conn()
    if field_id: rows=conn.execute("SELECT * FROM sensor_readings WHERE field_id=? ORDER BY id DESC LIMIT ?",(field_id,limit)).fetchall()
    else: rows=conn.execute("SELECT * FROM sensor_readings ORDER BY id DESC LIMIT ?",(limit,)).fetchall()
    conn.close()
    return [dict(r) | {'health': json.loads(r['health_json'] or '{}')} for r in rows]


def list_fields():
    conn=get_conn(); rows=conn.execute("SELECT * FROM fields ORDER BY id").fetchall(); conn.close(); return [dict(r) for r in rows]


def get_devices():
    conn=get_conn(); rows=conn.execute("SELECT * FROM devices ORDER BY last_seen DESC").fetchall(); conn.close()
    return [dict(r) | {'sensor_health': json.loads(r['sensor_health_json'] or '{}')} for r in rows]


def add_irrigation_event(data: dict):
    conn=get_conn(); cur=conn.execute("INSERT INTO irrigation_events(field_id,observation_id,requested_at,duration_min,status,reason,simulated) VALUES(?,?,?,?,?,?,?)",
                                       (data.get('field_id'),data.get('observation_id'),time.time(),data.get('duration_min',0),data.get('status','SIMULATED'),data.get('reason',''),1))
    conn.commit(); iid=cur.lastrowid; conn.close(); return iid


def add_alert(field_id, observation_id, severity, kind, reason, next_step):
    conn=get_conn(); cur=conn.execute("INSERT INTO alerts(field_id,observation_id,severity,kind,reason,next_step,created_at) VALUES(?,?,?,?,?,?,?)",
                                       (field_id,observation_id,severity,kind,reason,next_step,time.time())); conn.commit(); aid=cur.lastrowid; conn.close(); return aid


def list_alerts(limit=50, field_id=None):
    conn=get_conn()
    if field_id: rows=conn.execute("SELECT * FROM alerts WHERE field_id=? ORDER BY id DESC LIMIT ?",(field_id,limit)).fetchall()
    else: rows=conn.execute("SELECT * FROM alerts ORDER BY id DESC LIMIT ?",(limit,)).fetchall()
    conn.close(); return [dict(r) for r in rows]


def save_farmer_profile(data: dict):
    conn=get_conn(); now=time.time()
    conn.execute("""INSERT INTO farmer_profiles(id,name,crops_json,state,district,latitude,longitude,location_source,field_name,area_acres,soil_type,created_at,updated_at)
                   VALUES(1,?,?,?,?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(id) DO UPDATE SET name=excluded.name,crops_json=excluded.crops_json,state=excluded.state,district=excluded.district,latitude=excluded.latitude,longitude=excluded.longitude,location_source=excluded.location_source,field_name=excluded.field_name,area_acres=excluded.area_acres,soil_type=excluded.soil_type,updated_at=excluded.updated_at""",
                 (data['name'],_json(data.get('crops',[])),data.get('state',''),data.get('district',''),data.get('latitude'),data.get('longitude'),data.get('location_source','manual'),data.get('field_name','My Field'),data.get('area_acres'),data.get('soil_type','unknown'),now,now))
    # Keep the primary demo field aligned with the farmer profile.
    row=conn.execute("SELECT id FROM fields ORDER BY id LIMIT 1").fetchone()
    if row:
        conn.execute("UPDATE fields SET name=?,crop=?,area_acres=?,updated_at=? WHERE id=?",
                     (data.get('field_name','My Field'), (data.get('crops') or ['tomato'])[0], data.get('area_acres'), now, row['id']))
    conn.commit(); conn.close()

def get_farmer_profile():
    conn=get_conn(); row=conn.execute("SELECT * FROM farmer_profiles WHERE id=1").fetchone()
    field=conn.execute("SELECT id FROM fields ORDER BY id LIMIT 1").fetchone()
    conn.close()
    if not row: return None
    d=dict(row); d['crops']=json.loads(d.pop('crops_json') or '[]'); d['field_id']=int(field['id']) if field else 1; return d
