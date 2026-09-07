
import os
import sqlite3
from flask import Flask, request, redirect, g, Response
from datetime import datetime
import io
import csv
import json

app = Flask(__name__)

# FIREBASE SETUP - Free permanent DB
# If FIREBASE_CRED env var exists (JSON string), use Firebase, else SQLite fallback
FIREBASE_ENABLED = False
FIREBASE_CRED_JSON = os.environ.get("FIREBASE_CREDENTIALS")  # JSON string of service account
FIREBASE_DB = None

if FIREBASE_CRED_JSON:
    try:
        import firebase_admin
        from firebase_admin import credentials, firestore
        import json as js
        cred_dict = js.loads(FIREBASE_CRED_JSON)
        cred = credentials.Certificate(cred_dict)
        if not firebase_admin._apps:
            firebase_admin.initialize_app(cred)
        FIREBASE_DB = firestore.client()
        FIREBASE_ENABLED = True
        print("Firebase enabled - permanent DB")
    except Exception as e:
        print(f"Firebase init failed: {e}, using SQLite fallback")
        FIREBASE_ENABLED = False

SQLITE_PATH = "/tmp/Agent.db"

def get_sqlite_db():
    db = getattr(g, '_sqlite_db', None)
    if db is None:
        if not os.path.exists(SQLITE_PATH) and os.path.exists("Agent.db"):
            import shutil
            shutil.copy("Agent.db", SQLITE_PATH)
        db = g._sqlite_db = sqlite3.connect(SQLITE_PATH)
        db.row_factory = sqlite3.Row
    return db

def init_db():
    if FIREBASE_ENABLED:
        return  # Firebase auto creates collections
    db = get_sqlite_db()
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
<title>TEAM SHINE M9 - Firebase Permanent</title>
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
/* FIXED GRAPH HEIGHT - NO AUTO ADJUST */
.chart-container{position:relative;height:350px;width:100%;}
.chart-container-small{position:relative;height:220px;width:100%;display:flex;align-items:center;justify-content:center}
.chart-container-top10{position:relative;height:300px;width:100%;}
@media (max-width: 992px){.desktop-grid{grid-template-columns:1fr!important}.agent-sidebar{position:static!important}.ot-loss-grid{grid-template-columns:1fr!important}.chart-container{height:300px!important}}
</style></head><body>
<nav class="navbar navbar-dark p-3 sticky-top"><div class="container-fluid d-flex justify-content-between flex-wrap gap-2">
<div class="d-flex align-items-center gap-3"><div style="width:42px;height:42px;background:linear-gradient(135deg,#fbbf24,#f59e0b);border-radius:12px;display:flex;align-items:center;justify-content:center"><i class="bi bi-fire text-dark"></i></div><div><div class="fw-bold fs-5">TEAM SHINE M9</div><div style="font-size:10px;color:#f59e0b;letter-spacing:1px;font-weight:700">● FIREBASE PERMANENT • FIXED GRAPH</div></div><span class="badge bg-warning text-dark ms-2" style="border-radius:10px;padding:8px 12px;font-weight:800">__COUNT__ AGENTS</span></div>
<div class="d-flex gap-2 flex-wrap"><a href="/" class="btn btn-sm btn-outline-light" style="border-radius:10px">Dashboard</a><a href="/ot_report" class="btn btn-sm btn-outline-warning" style="border-radius:10px">Reports</a><a href="/export_csv" class="btn btn-sm btn-success" style="border-radius:10px">Export CSV</a><a href="/add" class="btn btn-sm btn-exec">+ Add Agent</a></div>
</div></nav><div class="container-fluid p-3 p-lg-4">__CONTENT__</div>
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body></html>"""

def render_page(content, count=0):
    return BASE_HTML.replace("__CONTENT__", content).replace("__COUNT__", str(count))

# Helper for SQLite
def get_agents_sqlite(q=None):
    db = get_sqlite_db()
    if q:
        like = f"%{q}%"
        cur = db.execute('SELECT * FROM agents WHERE NAME LIKE ? OR "TENCENT ID" LIKE ? OR "NBS ID" LIKE ? ORDER BY id DESC', (like, like, like))
    else:
        cur = db.execute('SELECT * FROM agents ORDER BY id DESC')
    return cur.fetchall()

def get_ot_loss_sqlite():
    db = get_sqlite_db()
    ot_sum = {r['agent_id']: r['t'] for r in db.execute('SELECT agent_id, SUM(hours) as t FROM ot_logs GROUP BY agent_id').fetchall()}
    loss_sum = {r['agent_id']: r['t'] for r in db.execute('SELECT agent_id, SUM(hours) as t FROM loss_logs GROUP BY agent_id').fetchall()}
    return ot_sum, loss_sum

# Firebase helpers
def get_agents_firebase(q=None):
    agents_ref = FIREBASE_DB.collection('agents')
    docs = agents_ref.stream()
    agents = []
    for doc in docs:
        data = doc.to_dict()
        data['id'] = doc.id
        # Convert numeric id if stored
        agents.append(data)
    if q:
        q_lower = q.lower()
        agents = [a for a in agents if q_lower in (a.get('NAME','').lower() + a.get('TENCENT ID','').lower() + a.get('NBS ID','').lower())]
    # sort by id desc
    agents.sort(key=lambda x: int(x.get('id',0) or 0), reverse=True)
    return agents

def get_ot_loss_firebase():
    ot_sum = {}
    loss_sum = {}
    try:
        ot_docs = FIREBASE_DB.collection('ot_logs').stream()
        for doc in ot_docs:
            data = doc.to_dict()
            aid = str(data.get('agent_id'))
            ot_sum[aid] = ot_sum.get(aid,0) + float(data.get('hours',0))
        loss_docs = FIREBASE_DB.collection('loss_logs').stream()
        for doc in loss_docs:
            data = doc.to_dict()
            aid = str(data.get('agent_id'))
            loss_sum[aid] = loss_sum.get(aid,0) + float(data.get('hours',0))
    except:
        pass
    return ot_sum, loss_sum

@app.route("/")
def index():
    init_db()
    q = request.args.get("q","").strip()
    if FIREBASE_ENABLED:
        agents = get_agents_firebase(q if q else None)
        ot_sum, loss_sum = get_ot_loss_firebase()
        rows=""
        for a in agents:
            aid = a.get('id')
            aname = a.get('NAME','')
            nbs = a.get('NBS ID','')
            tencent = a.get('TENCENT ID','')
            phone = a.get('PHONE NAME','')
            ot = ot_sum.get(str(aid),0) or 0
            loss = loss_sum.get(str(aid),0) or 0
            net = ot - loss
            rows+=f"<tr><td><span class='badge badge-id'>{aid}</span></td><td><a href='/view/{aid}' class='agent-name-dark text-decoration-none'>{aname}<br><small class='agent-sub'>{nbs} • {tencent}</small></a></td><td><span class='badge bg-dark border text-light'>{tencent}</span></td><td style='color:#cbd5e1'>{phone}</td><td><span class='badge bg-success'>{ot:.1f}h</span></td><td><span class='badge bg-danger'>{loss:.1f}h</span></td><td><span class='badge bg-warning text-dark fw-bold'>{net:+.1f}h</span></td><td><a href='/view/{aid}' class='btn btn-sm btn-warning fw-bold' style='border-radius:10px'>Manage</a></td></tr>"
        content=f"<div class='card p-3 mb-3'><form class='d-flex gap-2' method='get'><input name='q' value='{q}' class='form-control search-box' placeholder='Search agent...'><button class='btn btn-light' style='border-radius:12px'>Search</button></form><div class='mt-2 small' style='color:#f59e0b'>● Firebase Permanent DB - Data will NEVER disappear after deploy!</div></div><div class='card p-0 overflow-hidden'><div class='table-responsive'><table class='table table-hover mb-0'><thead><tr><th>ID</th><th>AGENT</th><th>TENCENT</th><th>PHONE</th><th>OT</th><th>LOSS</th><th>NET</th><th>ACTION</th></tr></thead><tbody>{rows if rows else '<tr><td colspan=8 class=text-center p-5>Empty</td></tr>'}</tbody></table></div></div>"
        return render_page(content, len(agents))
    else:
        agents = get_agents_sqlite(q if q else None)
        ot_sum, loss_sum = get_ot_loss_sqlite()
        rows=""
        for a in agents:
            ot = ot_sum.get(a['id'], 0) or 0
            loss = loss_sum.get(a['id'], 0) or 0
            net = ot - loss
            rows+=f"<tr><td><span class='badge badge-id'>{a['id']}</span></td><td><a href='/view/{a['id']}' class='agent-name-dark text-decoration-none'>{a['NAME'] or ''}<br><small class='agent-sub'>{a['NBS ID'] or ''} • {a['TENCENT ID'] or ''}</small></a></td><td><span class='badge bg-dark border text-light'>{a['TENCENT ID'] or ''}</span></td><td style='color:#cbd5e1'>{a['PHONE NAME'] or ''}</td><td><span class='badge bg-success'>{ot:.1f}h</span></td><td><span class='badge bg-danger'>{loss:.1f}h</span></td><td><span class='badge bg-warning text-dark fw-bold'>{net:+.1f}h</span></td><td><a href='/view/{a['id']}' class='btn btn-sm btn-warning fw-bold' style='border-radius:10px'>Manage</a></td></tr>"
        content=f"<div class='card p-3 mb-3'><form class='d-flex gap-2' method='get'><input name='q' value='{q}' class='form-control search-box' placeholder='Search agent...'><button class='btn btn-light' style='border-radius:12px'>Search</button></form><div class='mt-2 small' style='color:#ef4444'>⚠️ SQLite mode - Data will disappear on deploy! Add Firebase for permanent (see instructions)</div></div><div class='card p-0 overflow-hidden'><div class='table-responsive'><table class='table table-hover mb-0'><thead><tr><th>ID</th><th>AGENT</th><th>TENCENT</th><th>PHONE</th><th>OT</th><th>LOSS</th><th>NET</th><th>ACTION</th></tr></thead><tbody>{rows if rows else '<tr><td colspan=8 class=text-center p-5>Empty - upload Agent.db</td></tr>'}</tbody></table></div></div>"
        return render_page(content, len(agents))

@app.route("/view/<int:aid>")
def view(aid):
    init_db()
    if FIREBASE_ENABLED:
        doc = FIREBASE_DB.collection('agents').document(str(aid)).get()
        if not doc.exists:
            return redirect("/")
        a = doc.to_dict()
        a['id'] = doc.id
        # get ot/loss
        ot_logs = []
        loss_logs = []
        ot_q = FIREBASE_DB.collection('ot_logs').where('agent_id','==',aid).stream()
        for d in ot_q:
            dd = d.to_dict(); dd['id']=d.id; ot_logs.append(dd)
        loss_q = FIREBASE_DB.collection('loss_logs').where('agent_id','==',aid).stream()
        for d in loss_q:
            dd = d.to_dict(); dd['id']=d.id; loss_logs.append(dd)
        ot_t = sum([float(x.get('hours',0)) for x in ot_logs])
        loss_t = sum([float(x.get('hours',0)) for x in loss_logs])
        reg = sum([float(x.get('hours',0)) for x in ot_logs if x.get('ot_type')=='REGULAR'])
        rdot = sum([float(x.get('hours',0)) for x in ot_logs if x.get('ot_type')=='RDOT'])
        net = ot_t - loss_t
        fields_html=""
        for col in ['NAME', 'TENCENT ID', 'DATE HIRED', 'PHONE NAME', 'NBS ID', 'HEADSET SN', 'IBAS', 'DJANGO', 'NT LOG IN', 'Sales Force', 'ZOHO', 'BSS WEB', 'EMAIL', 'BIRTHDAY', 'CONTACT NO.', 'ADDRESS']:
            val = a.get(col,'')
            fields_html+=f"<div class='detail-card'><div class='field-label'>{col}</div><div class='field-value'>{val or '<span style=color:#334155>—</span>'}</div></div>"
    else:
        db = get_sqlite_db()
        a=db.execute('SELECT * FROM agents WHERE id=?',(aid,)).fetchone()
        if not a: return redirect("/")
        ot_logs = db.execute('SELECT * FROM ot_logs WHERE agent_id=? ORDER BY ot_date DESC', (aid,)).fetchall()
        loss_logs = db.execute('SELECT * FROM loss_logs WHERE agent_id=? ORDER BY loss_date DESC', (aid,)).fetchall()
        ot_total = db.execute('SELECT SUM(hours) as t, SUM(CASE WHEN ot_type="RDOT" THEN hours ELSE 0 END) as rdot, SUM(CASE WHEN ot_type="REGULAR" THEN hours ELSE 0 END) as reg FROM ot_logs WHERE agent_id=?', (aid,)).fetchone()
        loss_total = db.execute('SELECT SUM(hours) as t FROM loss_logs WHERE agent_id=?', (aid,)).fetchone()
        ot_t = ot_total['t'] or 0; rdot = ot_total['rdot'] or 0; reg = ot_total['reg'] or 0; loss_t = loss_total['t'] or 0; net = ot_t - loss_t
        fields_html="".join([f"<div class='detail-card'><div class='field-label'>{c}</div><div class='field-value'>{a[c] or '<span style=color:#334155>—</span>'}</div></div>" for c in ['NAME', 'TENCENT ID', 'DATE HIRED', 'PHONE NAME', 'NBS ID', 'HEADSET SN', 'IBAS', 'DJANGO', 'NT LOG IN', 'Sales Force', 'ZOHO', 'BSS WEB', 'EMAIL', 'BIRTHDAY', 'CONTACT NO.', 'ADDRESS']])

    # Build ot/loss rows HTML
    if FIREBASE_ENABLED:
        ot_rows="".join([f"<tr><td style='color:#e2e8f0'>{l.get('ot_date','')}</td><td><span class='badge {'bg-danger' if l.get('ot_type')=='RDOT' else 'bg-success'}'>{l.get('ot_type','')}</span></td><td style='color:#22c55e;font-weight:700'>{l.get('hours',0)}h</td><td style='color:#94a3b8'>{l.get('remarks','')}</td><td><form method='post' action='/delete_ot/{l.get('id')}'><button class='btn btn-sm btn-outline-danger'>X</button></form></td></tr>" for l in ot_logs])
        loss_rows="".join([f"<tr><td style='color:#e2e8f0'>{l.get('loss_date','')}</td><td><span class='badge bg-danger'>{l.get('loss_type','')}</span></td><td style='color:#ef4444;font-weight:700'>{l.get('hours',0)}h</td><td style='color:#94a3b8'>{l.get('remarks','')}</td><td><form method='post' action='/delete_loss/{l.get('id')}'><button class='btn btn-sm btn-outline-danger'>X</button></form></td></tr>" for l in loss_logs])
        aname = a.get('NAME','A')
    else:
        ot_rows="".join([f"<tr><td style='color:#e2e8f0'>{l['ot_date']}</td><td><span class='badge {'bg-danger' if l['ot_type']=='RDOT' else 'bg-success'}'>{l['ot_type']}</span></td><td style='color:#22c55e;font-weight:700'>{l['hours']}h</td><td style='color:#94a3b8'>{l['remarks'] or ''}</td><td><form method='post' action='/delete_ot/{l['id']}'><button class='btn btn-sm btn-outline-danger'>X</button></form></td></tr>" for l in ot_logs])
        loss_rows="".join([f"<tr><td style='color:#e2e8f0'>{l['loss_date']}</td><td><span class='badge bg-danger'>{l['loss_type']}</span></td><td style='color:#ef4444;font-weight:700'>{l['hours']}h</td><td style='color:#94a3b8'>{l['remarks'] or ''}</td><td><form method='post' action='/delete_loss/{l['id']}'><button class='btn btn-sm btn-outline-danger'>X</button></form></td></tr>" for l in loss_logs])
        aname = a['NAME'] or 'A'

    today = datetime.now().strftime("%Y-%m-%d")
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
                <div class='card p-4' style='border:1px solid #22c55e'><h6 class='fw-bold text-success'>Add OT - Permanent Firebase</h6>
                <form method='post' action='/add_ot/{aid}' class='row g-2 mt-2'>
                <div class='col-4'><input type='date' name='ot_date' value='{today}' class='form-control input-dark' required></div>
                <div class='col-4'><select name='ot_type' class='form-select input-dark'><option value='REGULAR'>NORMAL OT (1-4)</option><option value='RDOT'>RDOT (5-6)</option></select></div>
                <div class='col-4'><input type='number' step='0.5' name='hours' class='form-control input-dark' placeholder='2.5' required></div>
                <div class='col-12'><input name='remarks' class='form-control input-dark' placeholder='Remarks'></div>
                <div class='col-12'><button class='btn btn-success w-100 fw-bold' style='border-radius:12px'>Save OT - Permanent</button></div></form>
                <div class='table-responsive mt-3' style='max-height:300px'><table class='table table-sm mb-0'><thead><tr><th style='color:#fbbf24'>Date</th><th style='color:#fbbf24'>Type</th><th style='color:#fbbf24'>Hrs</th><th style='color:#fbbf24'>Remarks</th><th></th></tr></thead><tbody>{ot_rows if ot_rows else '<tr><td colspan=5 class=text-center style=color:#475569> No OT yet</td></tr>'}</tbody></table></div></div>
                <div class='card p-4' style='border:1px solid #ef4444'><h6 class='fw-bold text-danger'>Add LOSS - Permanent Firebase</h6>
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
    if FIREBASE_ENABLED:
        cnt = len(list(FIREBASE_DB.collection('agents').stream()))
    else:
        db = get_sqlite_db()
        cnt=db.execute('SELECT COUNT(*) FROM agents').fetchone()[0]
    return render_page(content, cnt)

@app.route("/add_ot/<int:aid>", methods=["POST"])
def add_ot(aid):
    init_db()
    if FIREBASE_ENABLED:
        FIREBASE_DB.collection('ot_logs').add({
            'agent_id': aid,
            'ot_date': request.form.get('ot_date'),
            'ot_type': request.form.get('ot_type'),
            'hours': float(request.form.get('hours',0)),
            'remarks': request.form.get('remarks',''),
            'created_at': datetime.now().isoformat()
        })
    else:
        db = get_sqlite_db()
        db.execute('INSERT INTO ot_logs (agent_id, ot_date, ot_type, hours, remarks, created_at) VALUES (?,?,?,?,?,?)',(aid, request.form.get('ot_date'), request.form.get('ot_type'), float(request.form.get('hours',0)), request.form.get('remarks',''), datetime.now().isoformat()))
        db.commit()
    return redirect(f"/view/{aid}")

@app.route("/add_loss/<int:aid>", methods=["POST"])
def add_loss(aid):
    init_db()
    if FIREBASE_ENABLED:
        FIREBASE_DB.collection('loss_logs').add({
            'agent_id': aid,
            'loss_date': request.form.get('loss_date'),
            'loss_type': request.form.get('loss_type'),
            'hours': float(request.form.get('hours',0)),
            'remarks': request.form.get('remarks',''),
            'created_at': datetime.now().isoformat()
        })
    else:
        db = get_sqlite_db()
        db.execute('INSERT INTO loss_logs (agent_id, loss_date, loss_type, hours, remarks, created_at) VALUES (?,?,?,?,?,?)',(aid, request.form.get('loss_date'), request.form.get('loss_type'), float(request.form.get('hours',0)), request.form.get('remarks',''), datetime.now().isoformat()))
        db.commit()
    return redirect(f"/view/{aid}")

@app.route("/delete_ot/<id>", methods=["POST"])
def delete_ot(id):
    init_db()
    if FIREBASE_ENABLED:
        # id is firestore doc id, need to find agent_id first
        try:
            doc = FIREBASE_DB.collection('ot_logs').document(str(id)).get()
            aid = doc.to_dict().get('agent_id',0) if doc.exists else 0
            FIREBASE_DB.collection('ot_logs').document(str(id)).delete()
        except:
            aid=0
    else:
        db = get_sqlite_db()
        cur=db.execute('SELECT agent_id FROM ot_logs WHERE id=?',(id,)).fetchone()
        aid = cur['agent_id'] if cur else 0
        db.execute('DELETE FROM ot_logs WHERE id=?',(id,)); db.commit()
    return redirect(f"/view/{aid}" if aid else "/")

@app.route("/delete_loss/<id>", methods=["POST"])
def delete_loss(id):
    init_db()
    if FIREBASE_ENABLED:
        try:
            doc = FIREBASE_DB.collection('loss_logs').document(str(id)).get()
            aid = doc.to_dict().get('agent_id',0) if doc.exists else 0
            FIREBASE_DB.collection('loss_logs').document(str(id)).delete()
        except:
            aid=0
    else:
        db = get_sqlite_db()
        cur=db.execute('SELECT agent_id FROM loss_logs WHERE id=?',(id,)).fetchone()
        aid = cur['agent_id'] if cur else 0
        db.execute('DELETE FROM loss_logs WHERE id=?',(id,)); db.commit()
    return redirect(f"/view/{aid}" if aid else "/")

@app.route("/ot_report")
def ot_report():
    init_db()
    if FIREBASE_ENABLED:
        ot_sum, loss_sum = get_ot_loss_firebase()
        agents = get_agents_firebase()
        # Calculate totals
        total_ot = sum(ot_sum.values())
        total_loss = sum(loss_sum.values())
        # Need breakdown for pie
        reg_ot = 0
        rdot_ot = 0
        # fetch all ot for breakdown
        for doc in FIREBASE_DB.collection('ot_logs').stream():
            d = doc.to_dict()
            if d.get('ot_type')=='REGULAR':
                reg_ot+=float(d.get('hours',0))
            else:
                rdot_ot+=float(d.get('hours',0))
        labels=[]
        ot_data=[]
        loss_data=[]
        table_rows=""
        for a in agents:
            aid = str(a.get('id'))
            ot = ot_sum.get(aid,0) or 0
            loss = loss_sum.get(aid,0) or 0
            if ot==0 and loss==0: continue
            labels.append((a.get('NAME','').split(',')[0]))
            ot_data.append(round(ot,1)); loss_data.append(round(loss,1))
            table_rows+=f"<tr><td style='color:#94a3b8'>{aid}</td><td><div class='agent-name-dark'>{a.get('NAME','')}</div><small class='agent-sub'>{a.get('NBS ID','')} • {a.get('TENCENT ID','')}</small></td><td style='color:#22c55e;font-weight:700'>{ot:.1f}h</td><td style='color:#ef4444;font-weight:700'>{loss:.1f}h</td><td style='color:#fbbf24;font-weight:800'>{ot-loss:+.1f}h</td></tr>"
        top_ot = sorted([(a.get('NAME',''), ot_sum.get(str(a.get('id')),0) or 0) for a in agents if ot_sum.get(str(a.get('id')),0)], key=lambda x: x[1], reverse=True)[:10]
        top_loss = sorted([(a.get('NAME',''), loss_sum.get(str(a.get('id')),0) or 0) for a in agents if loss_sum.get(str(a.get('id')),0)], key=lambda x: x[1], reverse=True)[:10]
    else:
        db = get_sqlite_db()
        ot_sum = {r['agent_id']: r['t'] for r in db.execute('SELECT agent_id, SUM(hours) as t FROM ot_logs GROUP BY agent_id').fetchall()}
        loss_sum = {r['agent_id']: r['t'] for r in db.execute('SELECT agent_id, SUM(hours) as t FROM loss_logs GROUP BY agent_id').fetchall()}
        agents = db.execute('SELECT * FROM agents ORDER BY NAME').fetchall()
        g_ot = db.execute('SELECT SUM(hours) as t, SUM(CASE WHEN ot_type="REGULAR" THEN hours ELSE 0 END) as reg, SUM(CASE WHEN ot_type="RDOT" THEN hours ELSE 0 END) as rdot FROM ot_logs').fetchone()
        g_loss = db.execute('SELECT SUM(hours) as t FROM loss_logs').fetchone()
        total_ot = g_ot['t'] or 0; reg_ot = g_ot['reg'] or 0; rdot_ot = g_ot['rdot'] or 0; total_loss = g_loss['t'] or 0
        labels=[]; ot_data=[]; loss_data=[]; table_rows=""
        for a in agents:
            ot = ot_sum.get(a['id'],0) or 0
            loss = loss_sum.get(a['id'],0) or 0
            if ot==0 and loss==0: continue
            labels.append((a['NAME'] or '').split(',')[0])
            ot_data.append(round(ot,1)); loss_data.append(round(loss,1))
            table_rows+=f"<tr><td style='color:#94a3b8'>{a['id']}</td><td><div class='agent-name-dark'>{a['NAME']}</div><small class='agent-sub'>{a['NBS ID'] or ''} • {a['TENCENT ID'] or ''}</small></td><td style='color:#22c55e;font-weight:700'>{ot:.1f}h</td><td style='color:#ef4444;font-weight:700'>{loss:.1f}h</td><td style='color:#fbbf24;font-weight:800'>{ot-loss:+.1f}h</td></tr>"
        top_ot = sorted([(a['NAME'], ot_sum.get(a['id'],0) or 0) for a in agents if ot_sum.get(a['id'],0)], key=lambda x: x[1], reverse=True)[:10]
        top_loss = sorted([(a['NAME'], loss_sum.get(a['id'],0) or 0) for a in agents if loss_sum.get(a['id'],0)], key=lambda x: x[1], reverse=True)[:10]

    content=f"""
    <div class='d-flex justify-content-between align-items-center mb-4 flex-wrap gap-2'>
        <h4 class='fw-bold text-white mb-0'><i class='bi bi-bar-chart-line text-warning'></i> Executive Reports - Fixed Graph Height (No Auto-Adjust)</h4>
        <div class='d-flex gap-2'><a href='/export_csv' class='btn btn-success btn-sm' style='border-radius:10px'>Export CSV</a></div>
    </div>
    <div class='row g-3 mb-4'>
        <div class='col-md-3'><div class='card p-3 text-center' style='border:1px solid #22c55e'><div class='field-label'>TOTAL OT</div><div class='fs-1 fw-bold text-success'>{total_ot:.1f}h</div><div style='font-size:11px;color:#6ee7b7'>Reg {reg_ot:.1f}h • RDOT {rdot_ot:.1f}h</div></div></div>
        <div class='col-md-3'><div class='card p-3 text-center' style='border:1px solid #ef4444'><div class='field-label'>TOTAL LOSS</div><div class='fs-1 fw-bold text-danger'>{total_loss:.1f}h</div></div></div>
        <div class='col-md-3'><div class='card p-3 text-center' style='border:1px solid #fbbf24'><div class='field-label'>NET</div><div class='fs-1 fw-bold text-warning'>{total_ot-total_loss:+.1f}h</div></div></div>
        <div class='col-md-3'><div class='card p-3 text-center'><div class='field-label'>ACTIVE</div><div class='fs-1 fw-bold text-white'>{len(labels)}</div><div class='small' style='color:{"#f59e0b" if FIREBASE_ENABLED else "#ef4444"}'>{'Firebase Permanent' if FIREBASE_ENABLED else 'SQLite - Add Firebase!'}</div></div></div>
    </div>
    <div class='row g-3 mb-4'>
        <div class='col-lg-8'><div class='card p-4'><h6 class='fw-bold mb-3 text-white'>OT vs LOSS Comparison - Fixed Height (No Auto-Adjust)</h6><div class='chart-container'><canvas id='otLossChart'></canvas></div></div></div>
        <div class='col-lg-4'><div class='card p-4'><h6 class='fw-bold mb-3 text-white'>Distribution - Small Pie Fixed</h6><div class='chart-container-small'><canvas id='pieChart'></canvas></div><div class='mt-3 text-center small'><span style='color:#22c55e'>● Regular {reg_ot:.1f}h</span> <span style='color:#f59e0b'>● RDOT {rdot_ot:.1f}h</span> <span style='color:#ef4444'>● LOSS {total_loss:.1f}h</span></div></div></div>
    </div>
    <div class='row g-3 mb-4'>
        <div class='col-md-6'><div class='card p-4'><h6 class='fw-bold text-success'>Top 10 OT</h6><div class='chart-container-top10'><canvas id='topOtChart'></canvas></div></div></div>
        <div class='col-md-6'><div class='card p-4'><h6 class='fw-bold text-danger'>Top 10 LOSS</h6><div class='chart-container-top10'><canvas id='topLossChart'></canvas></div></div></div>
    </div>
    <div class='card p-0 overflow-hidden'><div class='p-3 d-flex justify-content-between' style='background:#0f172a;border-bottom:1px solid #fbbf24'><h6 class='fw-bold mb-0 text-white'>Detailed Ranking - VISIBLE FONTS</h6><span class='badge bg-warning text-dark'>FIXED GRAPH</span></div><div class='table-responsive'><table class='table table-hover mb-0'><thead><tr><th style='color:#fbbf24'>ID</th><th style='color:#fbbf24'>AGENT</th><th style='color:#fbbf24'>OT</th><th style='color:#fbbf24'>LOSS</th><th style='color:#fbbf24'>NET</th></tr></thead><tbody>{table_rows if table_rows else '<tr><td colspan=5 class=text-center style=color:#94a3b8>No data yet</td></tr>'}</tbody></table></div></div>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script>
    new Chart(document.getElementById('otLossChart'), {{
        type:'bar',
        data:{{labels:{json.dumps(labels)}, datasets:[{{label:'OT', data:{json.dumps(ot_data)}, backgroundColor:'#22c55e', borderRadius:6, maxBarThickness:40}}, {{label:'LOSS', data:{json.dumps(loss_data)}, backgroundColor:'#ef4444', borderRadius:6, maxBarThickness:40}}]}},
        options:{{responsive:true, maintainAspectRatio:false, scales:{{x:{{ticks:{{color:'#94a3b8', maxRotation:45}}, grid:{{color:'#1f2937'}}}}, y:{{beginAtZero:true, ticks:{{color:'#94a3b8'}}, grid:{{color:'#1f2937'}}}}}}}}
    }});
    new Chart(document.getElementById('pieChart'), {{
        type:'doughnut',
        data:{{labels:['Regular OT','RDOT','LOSS'], datasets:[{{data:[{reg_ot},{rdot_ot},{total_loss}], backgroundColor:['#22c55e','#f59e0b','#ef4444'], borderWidth:0}}]}},
        options:{{responsive:true, maintainAspectRatio:false, cutout:'60%', plugins:{{legend:{{display:false}}}}}}
    }});
    new Chart(document.getElementById('topOtChart'), {{
        type:'bar',
        data:{{labels:{json.dumps([x[0].split(',')[0] for x in top_ot])}, datasets:[{{data:{json.dumps([x[1] for x in top_ot])}, backgroundColor:'#22c55e', borderRadius:6, maxBarThickness:30}}]}},
        options:{{indexAxis:'y', responsive:true, maintainAspectRatio:false, plugins:{{legend:{{display:false}}}}, scales:{{x:{{beginAtZero:true, ticks:{{color:'#94a3b8'}}}, grid:{{color:'#1f2937'}}}}, y:{{ticks:{{color:'#94a3b8'}}, grid:{{display:false}}}}}}}}
    }});
    new Chart(document.getElementById('topLossChart'), {{
        type:'bar',
        data:{{labels:{json.dumps([x[0].split(',')[0] for x in top_loss])}, datasets:[{{data:{json.dumps([x[1] for x in top_loss])}, backgroundColor:'#ef4444', borderRadius:6, maxBarThickness:30}}]}},
        options:{{indexAxis:'y', responsive:true, maintainAspectRatio:false, plugins:{{legend:{{display:false}}}}, scales:{{x:{{beginAtZero:true, ticks:{{color:'#94a3b8'}}}, grid:{{color:'#1f2937'}}}}, y:{{ticks:{{color:'#94a3b8'}}, grid:{{display:false}}}}}}}}
    }});
    </script>
    """
    if FIREBASE_ENABLED:
        cnt = len(list(FIREBASE_DB.collection('agents').stream()))
    else:
        db = get_sqlite_db()
        cnt=db.execute('SELECT COUNT(*) FROM agents').fetchone()[0]
    return render_page(content, cnt)

@app.route("/export_csv")
def export_csv():
    init_db()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["TEAM SHINE M9 - FIREBASE PERMANENT REPORT", f"Generated {datetime.now()}"])
    writer.writerow([])
    if FIREBASE_ENABLED:
        ot_sum, loss_sum = get_ot_loss_firebase()
        total_ot = sum(ot_sum.values())
        total_loss = sum(loss_sum.values())
        writer.writerow(["Total OT", total_ot])
        writer.writerow(["Total LOSS", total_loss])
        writer.writerow(["NET", total_ot-total_loss])
        writer.writerow([])
        writer.writerow(["ID", "NAME", "OT", "LOSS", "NET"])
        agents = get_agents_firebase()
        for a in agents:
            aid = str(a.get('id'))
            ot = ot_sum.get(aid,0)
            loss = loss_sum.get(aid,0)
            if ot==0 and loss==0: continue
            writer.writerow([aid, a.get('NAME',''), ot, loss, ot-loss])
    else:
        db = get_sqlite_db()
        g_ot = db.execute('SELECT SUM(hours) as t FROM ot_logs').fetchone()
        g_loss = db.execute('SELECT SUM(hours) as t FROM loss_logs').fetchone()
        writer.writerow(["Total OT", g_ot['t'] or 0])
        writer.writerow(["Total LOSS", g_loss['t'] or 0])
        writer.writerow(["NET", (g_ot['t'] or 0) - (g_loss['t'] or 0)])
        writer.writerow([])
        writer.writerow(["ID", "NAME", "NBS ID", "TENCENT", "OT", "LOSS", "NET"])
        ot_map = {r['agent_id']: r['t'] for r in db.execute('SELECT agent_id, SUM(hours) as t FROM ot_logs GROUP BY agent_id').fetchall()}
        loss_map = {r['agent_id']: r['t'] for r in db.execute('SELECT agent_id, SUM(hours) as t FROM loss_logs GROUP BY agent_id').fetchall()}
        for a in db.execute('SELECT * FROM agents ORDER BY NAME').fetchall():
            ot = ot_map.get(a['id'],0) or 0
            loss = loss_map.get(a['id'],0) or 0
            if ot==0 and loss==0: continue
            writer.writerow([a['id'], a['NAME'], a['NBS ID'], a['TENCENT ID'], ot, loss, ot-loss])
    output.seek(0)
    return Response(output.getvalue(), mimetype="text/csv", headers={"Content-Disposition": f"attachment;filename=TeamShineM9_Firebase_{datetime.now().strftime('%Y%m%d')}.csv"})

@app.route("/add", methods=["GET","POST"])
@app.route("/edit/<int:aid>", methods=["GET","POST"])
def add_edit(aid=None):
    init_db()
    if request.method=="POST":
        data = {
            'NAME': request.form.get('NAME'),
            'TENCENT ID': request.form.get('TENCENT ID'),
            'DATE HIRED': request.form.get('DATE HIRED'),
            'PHONE NAME': request.form.get('PHONE NAME'),
            'NBS ID': request.form.get('NBS ID'),
            'HEADSET SN': request.form.get('HEADSET SN'),
            'IBAS': request.form.get('IBAS'),
            'DJANGO': request.form.get('DJANGO'),
            'NT LOG IN': request.form.get('NT LOG IN'),
            'Sales Force': request.form.get('Sales Force'),
            'ZOHO': request.form.get('ZOHO'),
            'BSS WEB': request.form.get('BSS WEB'),
            'EMAIL': request.form.get('EMAIL'),
            'BIRTHDAY': request.form.get('BIRTHDAY'),
            'CONTACT NO.': request.form.get('CONTACT NO.'),
            'ADDRESS': request.form.get('ADDRESS')
        }
        if FIREBASE_ENABLED:
            if aid:
                FIREBASE_DB.collection('agents').document(str(aid)).set(data, merge=True)
            else:
                # generate new id
                new_id = str(int(datetime.now().timestamp()))
                FIREBASE_DB.collection('agents').document(new_id).set(data)
        else:
            db = get_sqlite_db()
            cols = list(data.keys())
            vals=[data[c] for c in cols]
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
    if FIREBASE_ENABLED:
        ag=None
        if aid:
            doc = FIREBASE_DB.collection('agents').document(str(aid)).get()
            ag = doc.to_dict() if doc.exists else None
        f="".join([f"<div class='col-md-6 mb-3'><label class='field-label'>{c}</label><input name='{c}' value='{(ag.get(c,'') if ag else '')}' class='form-control input-dark'></div>" for c in ['NAME', 'TENCENT ID', 'DATE HIRED', 'PHONE NAME', 'NBS ID', 'HEADSET SN', 'IBAS', 'DJANGO', 'NT LOG IN', 'Sales Force', 'ZOHO', 'BSS WEB', 'EMAIL', 'BIRTHDAY', 'CONTACT NO.', 'ADDRESS']])
    else:
        db = get_sqlite_db()
        ag=None
        if aid:
            ag=db.execute('SELECT * FROM agents WHERE id=?',(aid,)).fetchone()
        f="".join([f"<div class='col-md-6 mb-3'><label class='field-label'>{c}</label><input name='{c}' value='{(ag[c] if ag else '') or ''}' class='form-control input-dark'></div>" for c in ['NAME', 'TENCENT ID', 'DATE HIRED', 'PHONE NAME', 'NBS ID', 'HEADSET SN', 'IBAS', 'DJANGO', 'NT LOG IN', 'Sales Force', 'ZOHO', 'BSS WEB', 'EMAIL', 'BIRTHDAY', 'CONTACT NO.', 'ADDRESS']])
    title="Edit Agent" if aid else "Add Agent"
    content=f"<a href='/' class='btn btn-sm btn-outline-light mb-3' style='border-radius:10px'>Back</a><div class='card p-4'><h4 class='fw-bold'>{title} - {'Firebase Permanent' if FIREBASE_ENABLED else 'SQLite'}</h4><form method='post' class='row'>{f}<div class='col-12 mt-3'><button class='btn btn-warning fw-bold'>Save Permanent</button></div></form></div>"
    if FIREBASE_ENABLED:
        cnt = len(list(FIREBASE_DB.collection('agents').stream()))
    else:
        db = get_sqlite_db()
        cnt=db.execute('SELECT COUNT(*) FROM agents').fetchone()[0]
    return render_page(content, cnt)

@app.route("/delete/<int:aid>", methods=["POST"])
def delete(aid):
    init_db()
    if FIREBASE_ENABLED:
        FIREBASE_DB.collection('agents').document(str(aid)).delete()
        # delete ot/loss
        for doc in FIREBASE_DB.collection('ot_logs').where('agent_id','==',aid).stream():
            doc.reference.delete()
        for doc in FIREBASE_DB.collection('loss_logs').where('agent_id','==',aid).stream():
            doc.reference.delete()
    else:
        db = get_sqlite_db()
        db.execute('DELETE FROM agents WHERE id=?',(aid,))
        db.execute('DELETE FROM ot_logs WHERE agent_id=?',(aid,))
        db.execute('DELETE FROM loss_logs WHERE agent_id=?',(aid,))
        db.commit()
    return redirect("/")

if __name__=="__main__":
    port=int(os.environ.get("PORT",5000))
    app.run(host="0.0.0.0",port=port)
