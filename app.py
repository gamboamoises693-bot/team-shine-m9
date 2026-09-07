
import os
import sqlite3
from flask import Flask, request, redirect, g, send_file, Response
from datetime import datetime
import io
import csv

app = Flask(__name__)

# DATABASE LOGIC: Use Postgres if DATABASE_URL exists, else SQLite
# For Render free, you can add free Postgres and set DATABASE_URL env var
DATABASE_URL = os.environ.get("DATABASE_URL")
USE_POSTGRES = DATABASE_URL is not None

if USE_POSTGRES:
    try:
        import psycopg2
        import psycopg2.extras
    except:
        USE_POSTGRES = False

# For SQLite fallback - persistent path
SQLITE_PATH = "/tmp/Agent.db"  # /tmp is okay for fallback, but we will copy from repo if exists
# Actually use Agent.db in repo as source, but copy to /tmp on first run for persistence during runtime

def get_db():
    if USE_POSTGRES:
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    else:
        db = getattr(g, '_sqlite_db', None)
        if db is None:
            # On first run, if /tmp/Agent.db doesn't exist but Agent.db in repo exists, copy it
            if not os.path.exists(SQLITE_PATH) and os.path.exists("Agent.db"):
                import shutil
                shutil.copy("Agent.db", SQLITE_PATH)
            db = g._sqlite_db = sqlite3.connect(SQLITE_PATH)
            db.row_factory = sqlite3.Row
        return db

def init_db():
    db = get_db()
    if USE_POSTGRES:
        cur = db.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS agents (
                id SERIAL PRIMARY KEY,
                NAME TEXT,
                "TENCENT ID" TEXT,
                "DATE HIRED" TEXT,
                "PHONE NAME" TEXT,
                "NBS ID" TEXT,
                "HEADSET SN" TEXT,
                IBAS TEXT,
                DJANGO TEXT,
                "NT LOG IN" TEXT,
                "Sales Force" TEXT,
                ZOHO TEXT,
                "BSS WEB" TEXT,
                EMAIL TEXT,
                BIRTHDAY TEXT,
                "CONTACT NO." TEXT,
                ADDRESS TEXT
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS ot_logs (
                id SERIAL PRIMARY KEY,
                agent_id INTEGER,
                ot_date TEXT,
                ot_type TEXT,
                hours REAL,
                remarks TEXT,
                created_at TEXT
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS loss_logs (
                id SERIAL PRIMARY KEY,
                agent_id INTEGER,
                loss_date TEXT,
                loss_type TEXT,
                hours REAL,
                remarks TEXT,
                created_at TEXT
            )
        """)
        db.commit()
        cur.close()
    else:
        cols = ['NAME', 'TENCENT ID', 'DATE HIRED', 'PHONE NAME', 'NBS ID', 'HEADSET SN', 'IBAS', 'DJANGO', 'NT LOG IN', 'Sales Force', 'ZOHO', 'BSS WEB', 'EMAIL', 'BIRTHDAY', 'CONTACT NO.', 'ADDRESS']
        cols_def = ", ".join([f'"{c}" TEXT' for c in cols])
        db.execute(f'CREATE TABLE IF NOT EXISTS agents (id INTEGER PRIMARY KEY AUTOINCREMENT, {cols_def})')
        db.execute("""CREATE TABLE IF NOT EXISTS ot_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_id INTEGER,
            ot_date TEXT,
            ot_type TEXT,
            hours REAL,
            remarks TEXT,
            created_at TEXT
        )""")
        db.execute("""CREATE TABLE IF NOT EXISTS loss_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_id INTEGER,
            loss_date TEXT,
            loss_type TEXT,
            hours REAL,
            remarks TEXT,
            created_at TEXT
        )""")
        db.commit()

@app.teardown_appcontext
def close_connection(ex):
    db = getattr(g, '_sqlite_db', None)
    if db is not None:
        db.close()

BASE_HTML = """<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1">
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
<link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.0/font/bootstrap-icons.css" rel="stylesheet">
<title>TEAM SHINE M9 - Executive Permanent</title>
<style>
body{background:#080c14;color:#e2e8f0;font-family:system-ui}
.navbar{background:#0f172a!important;border-bottom:1px solid #1e293b}
.card{background:#111827!important;border:1px solid #1f2937!important;border-radius:20px!important}
.table{color:#e2e8f0!important;margin-bottom:0!important}
.table thead th{background:#0f172a!important;color:#fbbf24!important;border-bottom:2px solid #fbbf24!important;font-size:11px!important;text-transform:uppercase!important;padding:14px 12px!important;font-weight:800!important}
.table tbody td{background:#111827!important;border-color:#1f2937!important;padding:14px 12px!important;color:#e2e8f0!important}
.table tbody tr{background:#111827!important}
.table tbody tr:nth-child(even){background:#0f172a!important}
.table tbody tr:nth-child(even) td{background:#0f172a!important}
.table-hover tbody tr:hover{background:#1e293b!important}
.table-hover tbody tr:hover td{background:#1e293b!important}
.badge-id{background:#0f172a;border:1px solid #334155;color:#94a3b8;border-radius:8px;padding:6px 10px}
.btn-exec{background:linear-gradient(135deg,#fbbf24,#f59e0b);color:#0f172a;font-weight:800;border:none;border-radius:12px;padding:8px 18px}
.search-box{background:#0f172a;border:1px solid #1f2937;color:white;border-radius:12px;padding:12px}
.detail-card{background:#0f172a;border:1px solid #1e293b;border-radius:14px;padding:14px;height:100%}
.field-label{color:#64748b;font-size:10px;text-transform:uppercase;font-weight:700;margin-bottom:4px}
.field-value{color:#f1f5f9;font-weight:600;font-size:13px;word-break:break-word;white-space:normal}
.agent-avatar{width:80px;height:80px;background:linear-gradient(135deg,#fbbf24,#f59e0b);border-radius:20px;display:flex;align-items:center;justify-content:center;font-size:32px;font-weight:900;color:#0f172a}
.stat-card{background:#0f172a;border:1px solid #1e293b;border-radius:16px;padding:16px;text-align:center}
.stat-value{font-size:28px;font-weight:800}
.desktop-grid{display:grid;grid-template-columns:340px 1fr;gap:20px}
.agent-sidebar{position:sticky;top:90px}
.details-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.ot-loss-grid{display:grid;grid-template-columns:1fr 1fr;gap:20px}
.input-dark{background:#0a0e1a!important;border:1px solid #1f2937!important;color:white!important;border-radius:10px!important}
.agent-name-dark{color:#f1f5f9!important;font-weight:700!important}
.agent-sub{color:#94a3b8!important;font-weight:400!important;font-size:11px!important}
.text-visible-white{color:#f1f5f9!important}
@media (max-width: 992px){.desktop-grid{grid-template-columns:1fr!important}.agent-sidebar{position:static!important}.ot-loss-grid{grid-template-columns:1fr!important}}
</style></head><body>
<nav class="navbar navbar-dark p-3 sticky-top"><div class="container-fluid d-flex justify-content-between flex-wrap gap-2">
<div class="d-flex align-items-center gap-3"><div style="width:42px;height:42px;background:linear-gradient(135deg,#fbbf24,#f59e0b);border-radius:12px;display:flex;align-items:center;justify-content:center"><i class="bi bi-stars text-dark"></i></div><div><div class="fw-bold fs-5">TEAM SHINE M9</div><div style="font-size:10px;color:#10b981;letter-spacing:1px;font-weight:700">● PERMANENT • FREE POSTGRES READY</div></div><span class="badge bg-warning text-dark ms-2" style="border-radius:10px;padding:8px 12px;font-weight:800">__COUNT__ AGENTS</span></div>
<div class="d-flex gap-2 flex-wrap"><a href="/" class="btn btn-sm btn-outline-light" style="border-radius:10px">Dashboard</a><a href="/ot_report" class="btn btn-sm btn-outline-warning" style="border-radius:10px">Reports</a><a href="/export_csv" class="btn btn-sm btn-success" style="border-radius:10px">Export CSV</a><a href="/add" class="btn btn-sm btn-exec">+ Add Agent</a></div>
</div></nav><div class="container-fluid p-3 p-lg-4">__CONTENT__</div>
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body></html>"""

def render_page(content, count=0):
    return BASE_HTML.replace("__CONTENT__", content).replace("__COUNT__", str(count))

def query_agents(search=None):
    db = get_db()
    if USE_POSTGRES:
        cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        if search:
            like = f"%{search}%"
            cur.execute('SELECT * FROM agents WHERE NAME ILIKE %s OR "TENCENT ID" ILIKE %s OR "NBS ID" ILIKE %s ORDER BY id DESC', (like, like, like))
        else:
            cur.execute('SELECT * FROM agents ORDER BY id DESC')
        rows = cur.fetchall()
        cur.close()
        return rows
    else:
        if search:
            like = f"%{search}%"
            cur = db.execute(f'SELECT * FROM agents WHERE NAME LIKE ? OR "TENCENT ID" LIKE ? OR "NBS ID" LIKE ? ORDER BY id DESC', (like, like, like))
        else:
            cur = db.execute('SELECT * FROM agents ORDER BY id DESC')
        return cur.fetchall()

@app.route("/")
def index():
    init_db()
    q = request.args.get("q","").strip()
    agents = query_agents(q if q else None)
    db = get_db()
    if USE_POSTGRES:
        cur = db.cursor()
        cur.execute('SELECT agent_id, SUM(hours) as t FROM ot_logs GROUP BY agent_id')
        ot_sum = {r[0]: r[1] for r in cur.fetchall()}
        cur.execute('SELECT agent_id, SUM(hours) as t FROM loss_logs GROUP BY agent_id')
        loss_sum = {r[0]: r[1] for r in cur.fetchall()}
        cur.close()
    else:
        ot_sum = {r['agent_id']: r['t'] for r in db.execute('SELECT agent_id, SUM(hours) as t FROM ot_logs GROUP BY agent_id').fetchall()}
        loss_sum = {r['agent_id']: r['t'] for r in db.execute('SELECT agent_id, SUM(hours) as t FROM loss_logs GROUP BY agent_id').fetchall()}
    rows=""
    for a in agents:
        aid = a['id'] if not USE_POSTGRES else a['id']
        name = a['NAME'] if not USE_POSTGRES else a['name'] if 'name' in a else a['NAME']
        # handle dict vs Row
        if USE_POSTGRES:
            aname = a.get('NAME') or a.get('name') or ''
            nbs = a.get('NBS ID') or a.get('nbs id') or ''
            tencent = a.get('TENCENT ID') or a.get('tencent id') or ''
            phone = a.get('PHONE NAME') or a.get('phone name') or ''
        else:
            aname = a['NAME'] or ''
            nbs = a['NBS ID'] or ''
            tencent = a['TENCENT ID'] or ''
            phone = a['PHONE NAME'] or ''
        ot = ot_sum.get(aid, 0) or 0
        loss = loss_sum.get(aid, 0) or 0
        net = (ot or 0) - (loss or 0)
        rows+=f"<tr><td><span class='badge badge-id'>{aid}</span></td><td><a href='/view/{aid}' class='agent-name-dark text-decoration-none'>{aname}<br><small class='agent-sub'>{nbs} • {tencent}</small></a></td><td><span class='badge bg-dark border text-light'>{tencent}</span></td><td style='color:#cbd5e1'>{phone}</td><td><span class='badge bg-success'>{ot:.1f}h</span></td><td><span class='badge bg-danger'>{loss:.1f}h</span></td><td><span class='badge bg-warning text-dark fw-bold'>{net:+.1f}h</span></td><td><a href='/view/{aid}' class='btn btn-sm btn-warning fw-bold' style='border-radius:10px'>Manage</a></td></tr>"
    content=f"<div class='card p-3 mb-3'><form class='d-flex gap-2' method='get'><input name='q' value='{q}' class='form-control search-box' placeholder='Search agent...'><button class='btn btn-light' style='border-radius:12px'>Search</button></form><div class='mt-2 small' style='color:#10b981'>● Using {'Postgres (Permanent!)' if USE_POSTGRES else 'SQLite (/tmp - will reset on deploy, add Postgres for permanent)'} - LOSS/OT will {'NEVER disappear' if USE_POSTGRES else 'disappear on deploy without Postgres'} </div></div><div class='card p-0 overflow-hidden'><div class='table-responsive'><table class='table table-hover mb-0'><thead><tr><th>ID</th><th>AGENT</th><th>TENCENT</th><th>PHONE</th><th>OT</th><th>LOSS</th><th>NET</th><th>ACTION</th></tr></thead><tbody>{rows if rows else '<tr><td colspan=8 class=text-center p-5>Empty - upload Agent.db with OT</td></tr>'}</tbody></table></div></div>"
    count = len(agents)
    return render_page(content, count)

@app.route("/view/<int:aid>")
def view(aid):
    init_db(); db=get_db()
    if USE_POSTGRES:
        cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute('SELECT * FROM agents WHERE id=%s', (aid,))
        a = cur.fetchone()
        if not a:
            cur.close()
            return redirect("/")
        cur.execute('SELECT * FROM ot_logs WHERE agent_id=%s ORDER BY ot_date DESC', (aid,))
        ot_logs = cur.fetchall()
        cur.execute('SELECT * FROM loss_logs WHERE agent_id=%s ORDER BY loss_date DESC', (aid,))
        loss_logs = cur.fetchall()
        cur.execute('SELECT SUM(hours) as t, SUM(CASE WHEN ot_type=%s THEN hours ELSE 0 END) as rdot, SUM(CASE WHEN ot_type=%s THEN hours ELSE 0 END) as reg FROM ot_logs WHERE agent_id=%s', ('RDOT','REGULAR',aid))
        ot_total = cur.fetchone()
        cur.execute('SELECT SUM(hours) as t FROM loss_logs WHERE agent_id=%s', (aid,))
        loss_total = cur.fetchone()
        cur.close()
        ot_t = ot_total['t'] or 0; rdot = ot_total['rdot'] or 0; reg = ot_total['reg'] or 0; loss_t = loss_total['t'] or 0; net = ot_t - loss_t
        # fields
        fields_html=""
        for col in ['NAME', 'TENCENT ID', 'DATE HIRED', 'PHONE NAME', 'NBS ID', 'HEADSET SN', 'IBAS', 'DJANGO', 'NT LOG IN', 'Sales Force', 'ZOHO', 'BSS WEB', 'EMAIL', 'BIRTHDAY', 'CONTACT NO.', 'ADDRESS']:
            val = a.get(col) or a.get(col.lower()) or ''
            fields_html+=f"<div class='detail-card'><div class='field-label'>{col}</div><div class='field-value'>{val or '<span style=color:#334155>—</span>'}</div></div>"
    else:
        a=db.execute('SELECT * FROM agents WHERE id=?',(aid,)).fetchone()
        if not a: return redirect("/")
        ot_logs = db.execute('SELECT * FROM ot_logs WHERE agent_id=? ORDER BY ot_date DESC', (aid,)).fetchall()
        loss_logs = db.execute('SELECT * FROM loss_logs WHERE agent_id=? ORDER BY loss_date DESC', (aid,)).fetchall()
        ot_total = db.execute('SELECT SUM(hours) as t, SUM(CASE WHEN ot_type="RDOT" THEN hours ELSE 0 END) as rdot, SUM(CASE WHEN ot_type="REGULAR" THEN hours ELSE 0 END) as reg FROM ot_logs WHERE agent_id=?', (aid,)).fetchone()
        loss_total = db.execute('SELECT SUM(hours) as t FROM loss_logs WHERE agent_id=?', (aid,)).fetchone()
        ot_t = ot_total['t'] or 0; rdot = ot_total['rdot'] or 0; reg = ot_total['reg'] or 0; loss_t = loss_total['t'] or 0; net = ot_t - loss_t
        cols = ['NAME', 'TENCENT ID', 'DATE HIRED', 'PHONE NAME', 'NBS ID', 'HEADSET SN', 'IBAS', 'DJANGO', 'NT LOG IN', 'Sales Force', 'ZOHO', 'BSS WEB', 'EMAIL', 'BIRTHDAY', 'CONTACT NO.', 'ADDRESS']
        fields_html="".join([f"<div class='detail-card'><div class='field-label'>{c}</div><div class='field-value'>{a[c] or '<span style=color:#334155>—</span>'}</div></div>" for c in cols])
    ot_rows="".join([f"<tr><td style='color:#e2e8f0'>{l['ot_date'] if not USE_POSTGRES else l['ot_date']}</td><td><span class='badge {'bg-danger' if (l['ot_type'] if not USE_POSTGRES else l['ot_type'])=='RDOT' else 'bg-success'}'>{l['ot_type'] if not USE_POSTGRES else l['ot_type']}</span></td><td style='color:#22c55e;font-weight:700'>{l['hours'] if not USE_POSTGRES else l['hours']}h</td><td style='color:#94a3b8'>{l['remarks'] if not USE_POSTGRES else l['remarks'] or ''}</td><td><form method='post' action='/delete_ot/{l['id'] if not USE_POSTGRES else l['id']}'><button class='btn btn-sm btn-outline-danger'>X</button></form></td></tr>" for l in ot_logs])
    loss_rows="".join([f"<tr><td style='color:#e2e8f0'>{l['loss_date'] if not USE_POSTGRES else l['loss_date']}</td><td><span class='badge bg-danger'>{l['loss_type'] if not USE_POSTGRES else l['loss_type']}</span></td><td style='color:#ef4444;font-weight:700'>{l['hours'] if not USE_POSTGRES else l['hours']}h</td><td style='color:#94a3b8'>{l['remarks'] if not USE_POSTGRES else l['remarks'] or ''}</td><td><form method='post' action='/delete_loss/{l['id'] if not USE_POSTGRES else l['id']}'><button class='btn btn-sm btn-outline-danger'>X</button></form></td></tr>" for l in loss_logs])
    today = datetime.now().strftime("%Y-%m-%d")
    aname = (a['NAME'] if not USE_POSTGRES else a.get('NAME') or a.get('name') or '') or 'A'
    content=f"""
    <a href='/' class='btn btn-sm btn-outline-light mb-3' style='border-radius:10px'>← Back Dashboard</a>
    <div class='desktop-grid'>
        <div class='agent-sidebar'>
            <div class='card p-4 text-center'>
                <div class='agent-avatar mx-auto mb-3'>{aname[0]}</div>
                <div class='fw-bold fs-5 text-white' style='word-break:break-word'>{aname}</div>
                <div class='row g-2 my-3'>
                    <div class='col-6'><div class='stat-card'><div class='field-label'>TOTAL OT</div><div class='stat-value text-success'>{ot_t:.1f}h</div><div style='font-size:10px;color:#64748b'>Reg:{reg:.1f} RD:{rdot:.1f}</div></div></div>
                    <div class='col-6'><div class='stat-card'><div class='field-label'>LOSS</div><div class='stat-value text-danger'>{loss_t:.1f}h</div></div></div>
                    <div class='col-12'><div class='stat-card' style='border:1px solid #fbbf24'><div class='field-label'>NET</div><div class='stat-value text-warning' style='font-size:32px'>{net:+.1f}h</div></div></div>
                </div>
                <div class='text-start'><div class='field-label mb-2'>FULL PROFILE</div><div class='details-grid'>{fields_html}</div></div>
            </div>
        </div>
        <div class='d-flex flex-column gap-3'>
            <div class='ot-loss-grid'>
                <div class='card p-4' style='border:1px solid #22c55e'><h6 class='fw-bold text-success'>Add OT - Permanent</h6>
                <form method='post' action='/add_ot/{aid}' class='row g-2 mt-2'>
                <div class='col-4'><input type='date' name='ot_date' value='{today}' class='form-control input-dark' required></div>
                <div class='col-4'><select name='ot_type' class='form-select input-dark'><option value='REGULAR'>NORMAL OT (1-4)</option><option value='RDOT'>RDOT (5-6)</option></select></div>
                <div class='col-4'><input type='number' step='0.5' name='hours' class='form-control input-dark' placeholder='2.5' required></div>
                <div class='col-12'><input name='remarks' class='form-control input-dark' placeholder='Remarks'></div>
                <div class='col-12'><button class='btn btn-success w-100 fw-bold' style='border-radius:12px'>Save OT</button></div></form>
                <div class='table-responsive mt-3' style='max-height:300px'><table class='table table-sm mb-0'><thead><tr><th style='color:#fbbf24'>Date</th><th style='color:#fbbf24'>Type</th><th style='color:#fbbf24'>Hrs</th><th style='color:#fbbf24'>Remarks</th><th></th></tr></thead><tbody>{ot_rows if ot_rows else '<tr><td colspan=5 class=text-center style=color:#475569> No OT yet</td></tr>'}</tbody></table></div></div>
                <div class='card p-4' style='border:1px solid #ef4444'><h6 class='fw-bold text-danger'>Add LOSS - Permanent</h6>
                <form method='post' action='/add_loss/{aid}' class='row g-2 mt-2'>
                <div class='col-4'><input type='date' name='loss_date' value='{today}' class='form-control input-dark' required></div>
                <div class='col-4'><select name='loss_type' class='form-select input-dark'><option value='LATE'>LATE</option><option value='UNDERTIME'>UNDERTIME</option><option value='ABSENT'>ABSENT</option><option value='LOSS'>LOSS</option></select></div>
                <div class='col-4'><input type='number' step='0.5' name='hours' class='form-control input-dark' placeholder='1.5' required></div>
                <div class='col-12'><input name='remarks' class='form-control input-dark' placeholder='Remarks'></div>
                <div class='col-12'><button class='btn btn-danger w-100 fw-bold' style='border-radius:12px'>Save LOSS - Permanent</button></div></form>
                <div class='table-responsive mt-3' style='max-height:300px'><table class='table table-sm mb-0'><thead><tr><th style='color:#fbbf24'>Date</th><th style='color:#fbbf24'>Type</th><th style='color:#fbbf24'>Hrs</th><th style='color:#fbbf24'>Remarks</th><th></th></tr></thead><tbody>{loss_rows if loss_rows else '<tr><td colspan=5 class=text-center style=color:#475569> No Loss yet</td></tr>'}</tbody></table></div></div>
            </div>
        </div>
    </div>
    """
    # count
    if USE_POSTGRES:
        cur = db.cursor()
        cur.execute('SELECT COUNT(*) FROM agents')
        cnt = cur.fetchone()[0]
        cur.close()
    else:
        cnt=db.execute('SELECT COUNT(*) FROM agents').fetchone()[0]
    return render_page(content, cnt)

@app.route("/add_ot/<int:aid>", methods=["POST"])
def add_ot(aid):
    init_db(); db=get_db()
    if USE_POSTGRES:
        cur = db.cursor()
        cur.execute('INSERT INTO ot_logs (agent_id, ot_date, ot_type, hours, remarks, created_at) VALUES (%s,%s,%s,%s,%s,%s)',(aid, request.form.get('ot_date'), request.form.get('ot_type'), float(request.form.get('hours',0)), request.form.get('remarks',''), datetime.now().isoformat()))
        db.commit(); cur.close()
    else:
        db.execute('INSERT INTO ot_logs (agent_id, ot_date, ot_type, hours, remarks, created_at) VALUES (?,?,?,?,?,?)',(aid, request.form.get('ot_date'), request.form.get('ot_type'), float(request.form.get('hours',0)), request.form.get('remarks',''), datetime.now().isoformat()))
        db.commit()
    return redirect(f"/view/{aid}")

@app.route("/add_loss/<int:aid>", methods=["POST"])
def add_loss(aid):
    init_db(); db=get_db()
    if USE_POSTGRES:
        cur = db.cursor()
        cur.execute('INSERT INTO loss_logs (agent_id, loss_date, loss_type, hours, remarks, created_at) VALUES (%s,%s,%s,%s,%s,%s)',(aid, request.form.get('loss_date'), request.form.get('loss_type'), float(request.form.get('hours',0)), request.form.get('remarks',''), datetime.now().isoformat()))
        db.commit(); cur.close()
    else:
        db.execute('INSERT INTO loss_logs (agent_id, loss_date, loss_type, hours, remarks, created_at) VALUES (?,?,?,?,?,?)',(aid, request.form.get('loss_date'), request.form.get('loss_type'), float(request.form.get('hours',0)), request.form.get('remarks',''), datetime.now().isoformat()))
        db.commit()
    return redirect(f"/view/{aid}")

@app.route("/delete_ot/<int:oid>", methods=["POST"])
def delete_ot(oid):
    init_db(); db=get_db()
    if USE_POSTGRES:
        cur = db.cursor()
        cur.execute('SELECT agent_id FROM ot_logs WHERE id=%s',(oid,))
        row = cur.fetchone()
        aid = row[0] if row else 0
        cur.execute('DELETE FROM ot_logs WHERE id=%s',(oid,)); db.commit(); cur.close()
    else:
        cur=db.execute('SELECT agent_id FROM ot_logs WHERE id=?',(oid,)).fetchone()
        aid = cur['agent_id'] if cur else 0
        db.execute('DELETE FROM ot_logs WHERE id=?',(oid,)); db.commit()
    return redirect(f"/view/{aid}" if aid else "/")

@app.route("/delete_loss/<int:oid>", methods=["POST"])
def delete_loss(oid):
    init_db(); db=get_db()
    if USE_POSTGRES:
        cur = db.cursor()
        cur.execute('SELECT agent_id FROM loss_logs WHERE id=%s',(oid,))
        row = cur.fetchone()
        aid = row[0] if row else 0
        cur.execute('DELETE FROM loss_logs WHERE id=%s',(oid,)); db.commit(); cur.close()
    else:
        cur=db.execute('SELECT agent_id FROM loss_logs WHERE id=?',(oid,)).fetchone()
        aid = cur['agent_id'] if cur else 0
        db.execute('DELETE FROM loss_logs WHERE id=?',(oid,)); db.commit()
    return redirect(f"/view/{aid}" if aid else "/")

@app.route("/ot_report")
def ot_report():
    init_db(); db=get_db()
    if USE_POSTGRES:
        cur = db.cursor()
        cur.execute('SELECT agent_id, SUM(hours) as t FROM ot_logs GROUP BY agent_id')
        ot_map = {r[0]: r[1] for r in cur.fetchall()}
        cur.execute('SELECT agent_id, SUM(hours) as t FROM loss_logs GROUP BY agent_id')
        loss_map = {r[0]: r[1] for r in cur.fetchall()}
        cur.execute('SELECT * FROM agents ORDER BY NAME')
        agents_raw = cur.fetchall()
        # convert to dict-like
        agents = []
        for row in agents_raw:
            # row is tuple, need column names
            agents.append({'id': row[0], 'NAME': row[1], 'NBS ID': row[5], 'TENCENT ID': row[2]})
        cur.execute('SELECT SUM(hours) as t, SUM(CASE WHEN ot_type=%s THEN hours ELSE 0 END) as reg, SUM(CASE WHEN ot_type=%s THEN hours ELSE 0 END) as rdot FROM ot_logs', ('REGULAR','RDOT'))
        g_ot_row = cur.fetchone()
        cur.execute('SELECT SUM(hours) as t FROM loss_logs')
        g_loss_row = cur.fetchone()
        cur.close()
        total_ot = g_ot_row[0] or 0; reg_ot = g_ot_row[1] or 0; rdot_ot = g_ot_row[2] or 0; total_loss = g_loss_row[0] or 0
        # need proper fetch for ot_report totals
        # Simplified: use previous totals
    else:
        ot_map = {r['agent_id']: r['t'] for r in db.execute('SELECT agent_id, SUM(hours) as t FROM ot_logs GROUP BY agent_id').fetchall()}
        loss_map = {r['agent_id']: r['t'] for r in db.execute('SELECT agent_id, SUM(hours) as t FROM loss_logs GROUP BY agent_id').fetchall()}
        agents = db.execute('SELECT * FROM agents ORDER BY NAME').fetchall()
        g_ot = db.execute('SELECT SUM(hours) as t, SUM(CASE WHEN ot_type="REGULAR" THEN hours ELSE 0 END) as reg, SUM(CASE WHEN ot_type="RDOT" THEN hours ELSE 0 END) as rdot FROM ot_logs').fetchone()
        g_loss = db.execute('SELECT SUM(hours) as t FROM loss_logs').fetchone()
        total_ot = g_ot['t'] or 0; reg_ot = g_ot['reg'] or 0; rdot_ot = g_ot['rdot'] or 0; total_loss = g_loss['t'] or 0

    if not USE_POSTGRES:
        labels=[]; ot_data=[]; loss_data=[]; table_rows=""
        for a in agents:
            ot = ot_map.get(a['id'],0) or 0
            loss = loss_map.get(a['id'],0) or 0
            if ot==0 and loss==0: continue
            labels.append((a['NAME'] or '').split(',')[0])
            ot_data.append(round(ot,1)); loss_data.append(round(loss,1))
            table_rows+=f"<tr><td style='color:#94a3b8'>{a['id']}</td><td><div class='agent-name-dark'>{a['NAME']}</div><small class='agent-sub'>{a['NBS ID'] or ''} • {a['TENCENT ID'] or ''}</small></td><td style='color:#22c55e;font-weight:700'>{ot:.1f}h</td><td style='color:#ef4444;font-weight:700'>{loss:.1f}h</td><td style='color:#fbbf24;font-weight:800'>{ot-loss:+.1f}h</td></tr>"
        top_ot = sorted([(a['NAME'], ot_map.get(a['id'],0) or 0) for a in agents if ot_map.get(a['id'],0)], key=lambda x: x[1], reverse=True)[:10]
        top_loss = sorted([(a['NAME'], loss_map.get(a['id'],0) or 0) for a in agents if loss_map.get(a['id'],0)], key=lambda x: x[1], reverse=True)[:10]
        import json
        content=f"""
        <div class='d-flex justify-content-between align-items-center mb-4 flex-wrap gap-2'>
            <h4 class='fw-bold text-white mb-0'><i class='bi bi-bar-chart-line text-warning'></i> Executive Reports - Permanent { '• Postgres' if USE_POSTGRES else ''}</h4>
            <div class='d-flex gap-2'><a href='/export_csv' class='btn btn-success btn-sm' style='border-radius:10px'>Export CSV (No Crash)</a></div>
        </div>
        <div class='row g-3 mb-4'>
            <div class='col-md-3'><div class='card p-3 text-center' style='border:1px solid #22c55e'><div class='field-label'>TOTAL OT</div><div class='fs-1 fw-bold text-success'>{total_ot:.1f}h</div><div style='font-size:11px;color:#6ee7b7'>Reg {reg_ot:.1f}h • RDOT {rdot_ot:.1f}h</div></div></div>
            <div class='col-md-3'><div class='card p-3 text-center' style='border:1px solid #ef4444'><div class='field-label'>TOTAL LOSS</div><div class='fs-1 fw-bold text-danger'>{total_loss:.1f}h</div></div></div>
            <div class='col-md-3'><div class='card p-3 text-center' style='border:1px solid #fbbf24'><div class='field-label'>NET</div><div class='fs-1 fw-bold text-warning'>{total_ot-total_loss:+.1f}h</div></div></div>
            <div class='col-md-3'><div class='card p-3 text-center'><div class='field-label'>ACTIVE</div><div class='fs-1 fw-bold text-white'>{len(labels)}</div></div></div>
        </div>
        <div class='row g-3 mb-4'>
            <div class='col-lg-8'><div class='card p-4'><h6 class='fw-bold mb-3 text-white'>OT vs LOSS Comparison</h6><canvas id='otLossChart' height='110'></canvas></div></div>
            <div class='col-lg-4'><div class='card p-4'><h6 class='fw-bold mb-3 text-white'>Distribution - Small Pie</h6><div style='height:220px;display:flex;align-items:center;justify-content:center'><canvas id='pieChart' style='max-height:200px;max-width:200px'></canvas></div><div class='mt-3 text-center small'><span style='color:#22c55e'>● Regular {reg_ot:.1f}h</span> <span style='color:#f59e0b'>● RDOT {rdot_ot:.1f}h</span> <span style='color:#ef4444'>● LOSS {total_loss:.1f}h</span></div></div></div>
        </div>
        <div class='row g-3 mb-4'>
            <div class='col-md-6'><div class='card p-4'><h6 class='fw-bold text-success'>Top 10 OT</h6><canvas id='topOtChart' height='120'></canvas></div></div>
            <div class='col-md-6'><div class='card p-4'><h6 class='fw-bold text-danger'>Top 10 LOSS</h6><canvas id='topLossChart' height='120'></canvas></div></div>
        </div>
        <div class='card p-0 overflow-hidden'><div class='p-3 d-flex justify-content-between' style='background:#0f172a;border-bottom:1px solid #fbbf24'><h6 class='fw-bold mb-0 text-white'>Detailed Ranking - VISIBLE FONTS FIXED</h6><span class='badge bg-warning text-dark'>FIXED WHITE ISSUE</span></div><div class='table-responsive'><table class='table table-hover mb-0'><thead><tr><th style='color:#fbbf24'>ID</th><th style='color:#fbbf24'>AGENT</th><th style='color:#fbbf24'>OT</th><th style='color:#fbbf24'>LOSS</th><th style='color:#fbbf24'>NET</th></tr></thead><tbody>{table_rows if table_rows else '<tr><td colspan=5 class=text-center style=color:#94a3b8>No data yet</td></tr>'}</tbody></table></div></div>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <script>
        new Chart(document.getElementById('otLossChart'), {{type:'bar', data:{{labels:{json.dumps(labels)}, datasets:[{{label:'OT', data:{json.dumps(ot_data)}, backgroundColor:'#22c55e', borderRadius:6}}, {{label:'LOSS', data:{json.dumps(loss_data)}, backgroundColor:'#ef4444', borderRadius:6}}]}}, options:{{responsive:true, maintainAspectRatio:false, scales:{{x:{{ticks:{{color:'#94a3b8', maxRotation:45}}, grid:{{color:'#1f2937'}}}}, y:{{ticks:{{color:'#94a3b8'}}, grid:{{color:'#1f2937'}}}}}}}} }});
        new Chart(document.getElementById('pieChart'), {{type:'doughnut', data:{{labels:['Regular OT','RDOT','LOSS'], datasets:[{{data:[{reg_ot},{rdot_ot},{total_loss}], backgroundColor:['#22c55e','#f59e0b','#ef4444'], borderWidth:0}}]}}, options:{{responsive:true, maintainAspectRatio:false, cutout:'55%', plugins:{{legend:{{display:false}}}}}} }});
        new Chart(document.getElementById('topOtChart'), {{type:'bar', data:{{labels:{json.dumps([x[0].split(',')[0] for x in top_ot])}, datasets:[{{data:{json.dumps([x[1] for x in top_ot])}, backgroundColor:'#22c55e', borderRadius:6}}]}}, options:{{indexAxis:'y', responsive:true, plugins:{{legend:{{display:false}}}}}} }});
        new Chart(document.getElementById('topLossChart'), {{type:'bar', data:{{labels:{json.dumps([x[0].split(',')[0] for x in top_loss])}, datasets:[{{data:{json.dumps([x[1] for x in top_loss])}, backgroundColor:'#ef4444', borderRadius:6}}]}}, options:{{indexAxis:'y', responsive:true, plugins:{{legend:{{display:false}}}}}} }});
        </script>
        """
    else:
        content = "<div class='card p-4'><h4>Postgres mode - Reports simplified</h4><p>Using permanent Postgres, data will never disappear. OT/LOSS reports for Postgres will be added next.</p><a href='/' class='btn btn-warning'>Back</a></div>"

    if USE_POSTGRES:
        cur = db.cursor()
        cur.execute('SELECT COUNT(*) FROM agents')
        cnt = cur.fetchone()[0]
        cur.close()
    else:
        cnt = db.execute('SELECT COUNT(*) FROM agents').fetchone()[0]
    return render_page(content, cnt)

@app.route("/export_csv")
def export_csv():
    init_db(); db=get_db()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["TEAM SHINE M9 - PERMANENT REPORT", f"Generated {datetime.now()} - {'Postgres Permanent' if USE_POSTGRES else 'SQLite'}"])
    writer.writerow([])
    if USE_POSTGRES:
        cur = db.cursor()
        cur.execute('SELECT SUM(hours) as t FROM ot_logs')
        total_ot = cur.fetchone()[0] or 0
        cur.execute('SELECT SUM(hours) as t FROM loss_logs')
        total_loss = cur.fetchone()[0] or 0
        cur.close()
        writer.writerow(["Total OT", total_ot])
        writer.writerow(["Total LOSS", total_loss])
        writer.writerow(["NET", total_ot-total_loss])
    else:
        g_ot = db.execute('SELECT SUM(hours) as t FROM ot_logs').fetchone()
        g_loss = db.execute('SELECT SUM(hours) as t FROM loss_logs').fetchone()
        writer.writerow(["Total OT", g_ot['t'] or 0])
        writer.writerow(["Total LOSS", g_loss['t'] or 0])
        writer.writerow(["NET", (g_ot['t'] or 0) - (g_loss['t'] or 0)])
        writer.writerow([])
        writer.writerow(["AGENT RANKING"])
        writer.writerow(["ID", "NAME", "NBS ID", "TENCENT", "OT", "LOSS", "NET"])
        ot_map = {r['agent_id']: r['t'] for r in db.execute('SELECT agent_id, SUM(hours) as t FROM ot_logs GROUP BY agent_id').fetchall()}
        loss_map = {r['agent_id']: r['t'] for r in db.execute('SELECT agent_id, SUM(hours) as t FROM loss_logs GROUP BY agent_id').fetchall()}
        for a in db.execute('SELECT * FROM agents ORDER BY NAME').fetchall():
            ot = ot_map.get(a['id'],0) or 0
            loss = loss_map.get(a['id'],0) or 0
            if ot==0 and loss==0: continue
            writer.writerow([a['id'], a['NAME'], a['NBS ID'], a['TENCENT ID'], ot, loss, ot-loss])
    output.seek(0)
    return Response(output.getvalue(), mimetype="text/csv", headers={"Content-Disposition": f"attachment;filename=TeamShineM9_Permanent_{datetime.now().strftime('%Y%m%d')}.csv"})

@app.route("/export_excel")
def export_excel():
    # Redirect to CSV for stability, or try lightweight excel
    return redirect("/export_csv")

@app.route("/add", methods=["GET","POST"])
@app.route("/edit/<int:aid>", methods=["GET","POST"])
def add_edit(aid=None):
    init_db(); db=get_db()
    if request.method=="POST":
        if USE_POSTGRES:
            cur = db.cursor()
            if aid:
                cur.execute('UPDATE agents SET NAME=%s, "TENCENT ID"=%s, "DATE HIRED"=%s, "PHONE NAME"=%s, "NBS ID"=%s, "HEADSET SN"=%s, IBAS=%s, DJANGO=%s, "NT LOG IN"=%s, "Sales Force"=%s, ZOHO=%s, "BSS WEB"=%s, EMAIL=%s, BIRTHDAY=%s, "CONTACT NO."=%s, ADDRESS=%s WHERE id=%s',
                    (request.form.get('NAME'), request.form.get('TENCENT ID'), request.form.get('DATE HIRED'), request.form.get('PHONE NAME'), request.form.get('NBS ID'), request.form.get('HEADSET SN'), request.form.get('IBAS'), request.form.get('DJANGO'), request.form.get('NT LOG IN'), request.form.get('Sales Force'), request.form.get('ZOHO'), request.form.get('BSS WEB'), request.form.get('EMAIL'), request.form.get('BIRTHDAY'), request.form.get('CONTACT NO.'), request.form.get('ADDRESS'), aid))
            else:
                cur.execute('INSERT INTO agents (NAME, "TENCENT ID", "DATE HIRED", "PHONE NAME", "NBS ID", "HEADSET SN", IBAS, DJANGO, "NT LOG IN", "Sales Force", ZOHO, "BSS WEB", EMAIL, BIRTHDAY, "CONTACT NO.", ADDRESS) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)',
                    (request.form.get('NAME'), request.form.get('TENCENT ID'), request.form.get('DATE HIRED'), request.form.get('PHONE NAME'), request.form.get('NBS ID'), request.form.get('HEADSET SN'), request.form.get('IBAS'), request.form.get('DJANGO'), request.form.get('NT LOG IN'), request.form.get('Sales Force'), request.form.get('ZOHO'), request.form.get('BSS WEB'), request.form.get('EMAIL'), request.form.get('BIRTHDAY'), request.form.get('CONTACT NO.'), request.form.get('ADDRESS')))
            db.commit(); cur.close()
            return redirect(f"/view/{aid}" if aid else "/")
        else:
            cols = ['NAME', 'TENCENT ID', 'DATE HIRED', 'PHONE NAME', 'NBS ID', 'HEADSET SN', 'IBAS', 'DJANGO', 'NT LOG IN', 'Sales Force', 'ZOHO', 'BSS WEB', 'EMAIL', 'BIRTHDAY', 'CONTACT NO.', 'ADDRESS']
            vals=[request.form.get(c,"") for c in cols]
            if aid:
                sc=", ".join([f'"{c}"=?' for c in cols])
                db.execute(f'UPDATE agents SET {sc} WHERE id=?', vals+[aid])
            else:
                ph=", ".join(["?"]*len(cols))
                cq=", ".join([f'"{c}"' for c in cols])
                db.execute(f'INSERT INTO agents ({cq}) VALUES ({ph})', vals)
            db.commit()
            return redirect(f"/view/{aid}" if aid else "/")
    # GET
    if USE_POSTGRES:
        ag=None
        if aid:
            cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cur.execute('SELECT * FROM agents WHERE id=%s', (aid,))
            ag = cur.fetchone()
            cur.close()
        # form
        f = "".join([f"<div class='col-md-6 mb-3'><label class='field-label'>{c}</label><input name='{c}' value='{(ag.get(c) or ag.get(c.lower()) or '') if ag else ''}' class='form-control input-dark'></div>" for c in ['NAME', 'TENCENT ID', 'DATE HIRED', 'PHONE NAME', 'NBS ID', 'HEADSET SN', 'IBAS', 'DJANGO', 'NT LOG IN', 'Sales Force', 'ZOHO', 'BSS WEB', 'EMAIL', 'BIRTHDAY', 'CONTACT NO.', 'ADDRESS']])
    else:
        ag=None
        if aid:
            ag=db.execute('SELECT * FROM agents WHERE id=?',(aid,)).fetchone()
        f="".join([f"<div class='col-md-6 mb-3'><label class='field-label'>{c}</label><input name='{c}' value='{(ag[c] if ag else '') or ''}' class='form-control input-dark'></div>" for c in ['NAME', 'TENCENT ID', 'DATE HIRED', 'PHONE NAME', 'NBS ID', 'HEADSET SN', 'IBAS', 'DJANGO', 'NT LOG IN', 'Sales Force', 'ZOHO', 'BSS WEB', 'EMAIL', 'BIRTHDAY', 'CONTACT NO.', 'ADDRESS']])
    title="Edit Agent" if aid else "Add Agent"
    content=f"<a href='/' class='btn btn-sm btn-outline-light mb-3' style='border-radius:10px'>Back</a><div class='card p-4'><h4 class='fw-bold'>{title}</h4><form method='post' class='row'>{f}<div class='col-12 mt-3'><button class='btn btn-warning fw-bold'>Save Permanent</button></div></form></div>"
    if USE_POSTGRES:
        cur = db.cursor(); cur.execute('SELECT COUNT(*) FROM agents'); cnt = cur.fetchone()[0]; cur.close()
    else:
        cnt=db.execute('SELECT COUNT(*) FROM agents').fetchone()[0]
    return render_page(content, cnt)

@app.route("/delete/<int:aid>", methods=["POST"])
def delete(aid):
    init_db(); db=get_db()
    if USE_POSTGRES:
        cur = db.cursor()
        cur.execute('DELETE FROM agents WHERE id=%s',(aid,))
        cur.execute('DELETE FROM ot_logs WHERE agent_id=%s',(aid,))
        cur.execute('DELETE FROM loss_logs WHERE agent_id=%s',(aid,))
        db.commit(); cur.close()
    else:
        db.execute('DELETE FROM agents WHERE id=?',(aid,))
        db.execute('DELETE FROM ot_logs WHERE agent_id=?',(aid,))
        db.execute('DELETE FROM loss_logs WHERE agent_id=?',(aid,))
        db.commit()
    return redirect("/")

if __name__=="__main__":
    import os
    port=int(os.environ.get("PORT",5000))
    app.run(host="0.0.0.0",port=port)
