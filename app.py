import sqlite3
from flask import Flask, request, redirect, g
from datetime import datetime

app = Flask(__name__)
DATABASE = "Agent.db"
COLUMNS = ['NAME', 'TENCENT ID', 'DATE HIRED', 'PHONE NAME', 'NBS ID', 'HEADSET SN', 'IBAS', 'DJANGO', 'NT LOG IN', 'Sales Force', 'ZOHO', 'BSS WEB', 'EMAIL', 'BIRTHDAY', 'CONTACT NO.', 'ADDRESS']

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

def init_db():
    db = get_db()
    cols_def = ", ".join([f'"{c}" TEXT' for c in COLUMNS])
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
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

BASE_HTML = """<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1">
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
<link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.0/font/bootstrap-icons.css" rel="stylesheet">
<title>TEAM SHINE M9 - OT & LOSS</title>
<style>
body{background:#0f172a;color:#e2e8f0} .navbar{background:linear-gradient(90deg,#0f172a,#1e293b)!important;border-bottom:1px solid #334155}
.card{background:#1e293b;border:1px solid #334155;border-radius:16px} .table{color:#e2e8f0}
.table thead th{background:#0f172a;color:#94a3b8;border-bottom:2px solid #334155;font-size:11px;text-transform:uppercase;white-space:nowrap}
.table tbody td{border-color:#1e293b;vertical-align:middle;font-size:13px;white-space:nowrap}
.table-hover tbody tr:hover{background:#1e293b!important} .badge-id{background:#0f172a;border:1px solid #334155;color:#94a3b8}
.btn-exec{background:#fbbf24;color:#0f172a;font-weight:700;border:none} .search-box{background:#0f172a;border:1px solid #334155;color:white}
.detail-card{background:#0f172a;border:1px solid #334155} .field-label{color:#64748b;font-size:10px;text-transform:uppercase} .field-value{color:#f1f5f9;font-weight:500}
</style></head><body>
<nav class="navbar navbar-dark p-3 sticky-top"><div class="container-fluid d-flex justify-content-between">
<div class="d-flex align-items-center gap-3"><i class="bi bi-stars fs-4 text-warning"></i><div><div class="fw-bold fs-5">TEAM SHINE M9</div><div style="font-size:11px;color:#94a3b8;letter-spacing:2px">OT + LOSS HOURS TRACKER</div></div><span class="badge bg-warning text-dark ms-3">__COUNT__ AGENTS</span></div>
<div class="d-flex gap-2"><a href="/" class="btn btn-sm btn-outline-light">Dashboard</a><a href="/ot_report" class="btn btn-sm btn-outline-warning">Reports</a><a href="/add" class="btn btn-sm btn-exec">+ Add Agent</a></div>
</div></nav><div class="container-fluid p-4">__CONTENT__</div>
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body></html>"""

def render_page(content, count=0):
    return BASE_HTML.replace("__CONTENT__", content).replace("__COUNT__", str(count))

@app.route("/")
def index():
    init_db()
    q = request.args.get("q","").strip()
    db = get_db()
    if q:
        like = f"%{q}%"
        where = " OR ".join([f'"{c}" LIKE ?' for c in COLUMNS])
        cur = db.execute(f'SELECT * FROM agents WHERE {where} ORDER BY id DESC', [like]*len(COLUMNS))
    else:
        cur = db.execute('SELECT * FROM agents ORDER BY id DESC')
    agents = cur.fetchall()
    ot_sum = {}
    loss_sum = {}
    for r in db.execute('SELECT agent_id, SUM(hours) as t FROM ot_logs GROUP BY agent_id').fetchall():
        ot_sum[r['agent_id']] = r['t']
    for r in db.execute('SELECT agent_id, SUM(hours) as t FROM loss_logs GROUP BY agent_id').fetchall():
        loss_sum[r['agent_id']] = r['t']
    rows=""
    for a in agents:
        ot = ot_sum.get(a['id'], 0) or 0
        loss = loss_sum.get(a['id'], 0) or 0
        net = ot - loss
        rows+=f"<tr><td><span class='badge badge-id'>{a['id']}</span></td><td><a href='/view/{a['id']}' class='text-decoration-none'><div class='fw-bold text-white'>{a['NAME'] or ''}</div><div style='font-size:11px;color:#94a3b8'>{a['NBS ID'] or ''} • {a['TENCENT ID'] or ''}</div></a></td><td>{a['TENCENT ID'] or ''}</td><td>{a['PHONE NAME'] or ''}</td><td><span class='badge bg-success'>{ot:.1f}h OT</span></td><td><span class='badge bg-danger'>{loss:.1f}h LOSS</span></td><td><span class='badge bg-warning text-dark'>{net:+.1f}h NET</span></td><td><a href='/view/{a['id']}' class='btn btn-sm btn-warning fw-bold'><i class='bi bi-clock-history'></i> Manage</a></td></tr>"
    content=f"<div class='card p-3 mb-3'><form class='d-flex gap-2' method='get'><input name='q' value='{q}' class='form-control search-box' placeholder='Search agent...'><button class='btn btn-light'>Search</button></form></div><div class='card p-0 overflow-hidden'><div class='table-responsive'><table class='table table-hover mb-0'><thead><tr><th>ID</th><th>Agent</th><th>Tencent</th><th>Phone</th><th>OT</th><th>LOSS</th><th>NET</th><th>Action</th></tr></thead><tbody>{rows if rows else '<tr><td colspan=8 class=text-center p-5>Empty</td></tr>'}</tbody></table></div></div>"
    return render_page(content, len(agents))

@app.route("/view/<int:aid>")
def view(aid):
    init_db()
    db=get_db()
    a=db.execute('SELECT * FROM agents WHERE id=?',(aid,)).fetchone()
    if not a: return redirect("/")
    ot_logs = db.execute('SELECT * FROM ot_logs WHERE agent_id=? ORDER BY ot_date DESC', (aid,)).fetchall()
    loss_logs = db.execute('SELECT * FROM loss_logs WHERE agent_id=? ORDER BY loss_date DESC', (aid,)).fetchall()
    ot_total = db.execute('SELECT SUM(hours) as t, SUM(CASE WHEN ot_type="RDOT" THEN hours ELSE 0 END) as rdot, SUM(CASE WHEN ot_type="REGULAR" THEN hours ELSE 0 END) as reg FROM ot_logs WHERE agent_id=?', (aid,)).fetchone()
    loss_total = db.execute('SELECT SUM(hours) as t FROM loss_logs WHERE agent_id=?', (aid,)).fetchone()
    ot_t = ot_total['t'] or 0
    rdot = ot_total['rdot'] or 0
    reg = ot_total['reg'] or 0
    loss_t = loss_total['t'] or 0
    net = ot_t - loss_t
    fields="".join([f"<div class='col-md-4 mb-2'><div class='detail-card p-2 rounded-3'><div class='field-label'>{c}</div><div class='field-value'>{a[c] or '-'}</div></div></div>" for c in COLUMNS])
    ot_rows="".join([f"<tr><td>{l['ot_date']}</td><td><span class='badge {'bg-danger' if l['ot_type']=='RDOT' else 'bg-success'}'>{l['ot_type']}</span></td><td><b>{l['hours']}h</b></td><td>{l['remarks'] or ''}</td><td><form method='post' action='/delete_ot/{l['id']}'><button class='btn btn-sm btn-outline-danger'>X</button></form></td></tr>" for l in ot_logs])
    loss_rows="".join([f"<tr><td>{l['loss_date']}</td><td><span class='badge bg-danger'>{l['loss_type']}</span></td><td><b>{l['hours']}h</b></td><td>{l['remarks'] or ''}</td><td><form method='post' action='/delete_loss/{l['id']}'><button class='btn btn-sm btn-outline-danger'>X</button></form></td></tr>" for l in loss_logs])
    today = datetime.now().strftime("%Y-%m-%d")
    content=f"""
    <a href='/' class='btn btn-sm btn-outline-light mb-3'>Back Dashboard</a>
    <div class='row'>
        <div class='col-md-3'>
            <div class='card p-3 text-center sticky-top' style='top:80px'>
                <div style='width:60px;height:60px;background:linear-gradient(135deg,#fbbf24,#f59e0b);border-radius:14px;display:flex;align-items:center;justify-content:center;margin:0 auto 10px;font-size:24px;font-weight:800;color:#0f172a'>{(a['NAME'] or 'A')[0]}</div>
                <div class='fw-bold text-white'>{a['NAME']}</div><div class='field-label mb-3'>{a['NBS ID'] or ''}</div>
                <div class='row g-2'>
                    <div class='col-6'><div class='detail-card p-2 rounded'><div class='field-label'>TOTAL OT</div><div class='fw-bold text-success'>{ot_t:.1f}h</div><small style='font-size:10px'>Reg:{reg:.1f} RD:{rdot:.1f}</small></div></div>
                    <div class='col-6'><div class='detail-card p-2 rounded'><div class='field-label'>LOSS HRS</div><div class='fw-bold text-danger'>{loss_t:.1f}h</div></div></div>
                    <div class='col-12'><div class='detail-card p-2 rounded' style='border:1px solid #fbbf24'><div class='field-label'>NET (OT - LOSS)</div><div class='fs-4 fw-bold text-warning'>{net:+.1f}h</div></div></div>
                </div>
                <div class='row mt-3 text-start'>{fields}</div>
            </div>
        </div>
        <div class='col-md-9'>
            <div class='row g-3'>
                <div class='col-md-6'>
                    <div class='card p-3' style='border:1px solid #22c55e'>
                        <h6 class='fw-bold text-success'><i class='bi bi-plus-circle'></i> Add OT (Rendered OT)</h6>
                        <form method='post' action='/add_ot/{a['id']}' class='row g-2 mt-1'>
                            <div class='col-4'><label class='field-label'>Date</label><input type='date' name='ot_date' value='{today}' class='form-control form-control-sm' style='background:#0f172a;border:1px solid #334155;color:white' required></div>
                            <div class='col-4'><label class='field-label'>Type</label><select name='ot_type' class='form-select form-select-sm' style='background:#0f172a;border:1px solid #334155;color:white'><option value='REGULAR'>NORMAL OT</option><option value='RDOT'>REST DAY OT</option></select></div>
                            <div class='col-4'><label class='field-label'>Hours</label><input type='number' step='0.5' name='hours' class='form-control form-control-sm' style='background:#0f172a;border:1px solid #334155;color:white' placeholder='2.5' required></div>
                            <div class='col-12'><input name='remarks' class='form-control form-control-sm' style='background:#0f172a;border:1px solid #334155;color:white' placeholder='Remarks - e.g. high volume'></div>
                            <div class='col-12'><button class='btn btn-success btn-sm w-100 fw-bold'>Save OT</button></div>
                        </form>
                        <div class='table-responsive mt-3'><table class='table table-sm mb-0'><thead><tr><th>Date</th><th>Type</th><th>Hrs</th><th>Remarks</th><th></th></tr></thead><tbody>{ot_rows if ot_rows else '<tr><td colspan=5 class=text-center>No OT yet</td></tr>'}</tbody></table></div>
                    </div>
                </div>
                <div class='col-md-6'>
                    <div class='card p-3' style='border:1px solid #ef4444'>
                        <h6 class='fw-bold text-danger'><i class='bi bi-dash-circle'></i> Add LOSS Hours</h6>
                        <form method='post' action='/add_loss/{a['id']}' class='row g-2 mt-1'>
                            <div class='col-4'><label class='field-label'>Date</label><input type='date' name='loss_date' value='{today}' class='form-control form-control-sm' style='background:#0f172a;border:1px solid #334155;color:white' required></div>
                            <div class='col-4'><label class='field-label'>Type</label><select name='loss_type' class='form-select form-select-sm' style='background:#0f172a;border:1px solid #334155;color:white'><option value='LATE'>LATE</option><option value='UNDERTIME'>UNDERTIME</option><option value='ABSENT'>ABSENT (Hours)</option><option value='LOSS'>LOSS / NO LOG</option><option value='OTHERS'>OTHERS</option></select></div>
                            <div class='col-4'><label class='field-label'>Hours</label><input type='number' step='0.5' name='hours' class='form-control form-control-sm' style='background:#0f172a;border:1px solid #334155;color:white' placeholder='1.5' required></div>
                            <div class='col-12'><input name='remarks' class='form-control form-control-sm' style='background:#0f172a;border:1px solid #334155;color:white' placeholder='Remarks - e.g. late 30 mins, system issue'></div>
                            <div class='col-12'><button class='btn btn-danger btn-sm w-100 fw-bold'>Save LOSS Hours</button></div>
                        </form>
                        <div class='table-responsive mt-3'><table class='table table-sm mb-0'><thead><tr><th>Date</th><th>Type</th><th>Hrs</th><th>Remarks</th><th></th></tr></thead><tbody>{loss_rows if loss_rows else '<tr><td colspan=5 class=text-center>No Loss yet</td></tr>'}</tbody></table></div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    """
    cnt=db.execute('SELECT COUNT(*) FROM agents').fetchone()[0]
    return render_page(content, cnt)

@app.route("/add_ot/<int:aid>", methods=["POST"])
def add_ot(aid):
    init_db()
    db=get_db()
    db.execute('INSERT INTO ot_logs (agent_id, ot_date, ot_type, hours, remarks, created_at) VALUES (?,?,?,?,?,?)',
               (aid, request.form.get('ot_date'), request.form.get('ot_type'), float(request.form.get('hours',0)), request.form.get('remarks',''), datetime.now().isoformat()))
    db.commit()
    return redirect(f"/view/{aid}")

@app.route("/add_loss/<int:aid>", methods=["POST"])
def add_loss(aid):
    init_db()
    db=get_db()
    db.execute('INSERT INTO loss_logs (agent_id, loss_date, loss_type, hours, remarks, created_at) VALUES (?,?,?,?,?,?)',
               (aid, request.form.get('loss_date'), request.form.get('loss_type'), float(request.form.get('hours',0)), request.form.get('remarks',''), datetime.now().isoformat()))
    db.commit()
    return redirect(f"/view/{aid}")

@app.route("/delete_ot/<int:oid>", methods=["POST"])
def delete_ot(oid):
    init_db()
    db=get_db()
    cur=db.execute('SELECT agent_id FROM ot_logs WHERE id=?',(oid,)).fetchone()
    aid = cur['agent_id'] if cur else 0
    db.execute('DELETE FROM ot_logs WHERE id=?',(oid,))
    db.commit()
    return redirect(f"/view/{aid}" if aid else "/")

@app.route("/delete_loss/<int:oid>", methods=["POST"])
def delete_loss(oid):
    init_db()
    db=get_db()
    cur=db.execute('SELECT agent_id FROM loss_logs WHERE id=?',(oid,)).fetchone()
    aid = cur['agent_id'] if cur else 0
    db.execute('DELETE FROM loss_logs WHERE id=?',(oid,))
    db.commit()
    return redirect(f"/view/{aid}" if aid else "/")

@app.route("/ot_report")
def ot_report():
    init_db()
    db=get_db()
    ot_map = {r['agent_id']: r['t'] for r in db.execute('SELECT agent_id, SUM(hours) as t FROM ot_logs GROUP BY agent_id').fetchall()}
    loss_map = {r['agent_id']: r['t'] for r in db.execute('SELECT agent_id, SUM(hours) as t FROM loss_logs GROUP BY agent_id').fetchall()}
    agents = db.execute('SELECT * FROM agents ORDER BY NAME').fetchall()
    tr=""
    for a in agents:
        ot = ot_map.get(a['id'],0) or 0
        loss = loss_map.get(a['id'],0) or 0
        if ot==0 and loss==0: continue
        tr+=f"<tr><td>{a['id']}</td><td><a href='/view/{a['id']}' class='text-white fw-bold'>{a['NAME']}</a></td><td class='text-success fw-bold'>{ot:.1f}h</td><td class='text-danger fw-bold'>{loss:.1f}h</td><td class='text-warning fw-bold'>{ot-loss:+.1f}h</td></tr>"
    g_ot = db.execute('SELECT SUM(hours) as t FROM ot_logs').fetchone()['t'] or 0
    g_loss = db.execute('SELECT SUM(hours) as t FROM loss_logs').fetchone()['t'] or 0
    content=f"<h4 class='fw-bold'>Team Report - OT vs LOSS</h4><div class='row g-2 mb-3'><div class='col-4'><div class='card p-3 text-center'><div class='field-label'>Total OT</div><div class='fs-3 fw-bold text-success'>{g_ot:.1f}h</div></div></div><div class='col-4'><div class='card p-3 text-center'><div class='field-label'>Total LOSS</div><div class='fs-3 fw-bold text-danger'>{g_loss:.1f}h</div></div></div><div class='col-4'><div class='card p-3 text-center' style='border:1px solid #fbbf24'><div class='field-label'>NET</div><div class='fs-3 fw-bold text-warning'>{g_ot-g_loss:+.1f}h</div></div></div></div><div class='card p-0 overflow-hidden'><table class='table mb-0'><thead><tr><th>ID</th><th>Agent</th><th>OT</th><th>LOSS</th><th>NET</th></tr></thead><tbody>{tr if tr else '<tr><td colspan=5 class=text-center>No records</td></tr>'}</tbody></table></div>"
    cnt=db.execute('SELECT COUNT(*) FROM agents').fetchone()[0]
    return render_page(content, cnt)

@app.route("/add", methods=["GET","POST"])
@app.route("/edit/<int:aid>", methods=["GET","POST"])
def add_edit(aid=None):
    init_db()
    db=get_db()
    ag=None
    if aid:
        ag=db.execute('SELECT * FROM agents WHERE id=?',(aid,)).fetchone()
    if request.method=="POST":
        vals=[request.form.get(c,"") for c in COLUMNS]
        if aid:
            sc=", ".join([f'"{c}"=?' for c in COLUMNS])
            db.execute(f'UPDATE agents SET {sc} WHERE id=?', vals+[aid])
        else:
            ph=", ".join(["?"]*len(COLUMNS))
            cq=", ".join([f'"{c}"' for c in COLUMNS])
            db.execute(f'INSERT INTO agents ({cq}) VALUES ({ph})', vals)
        db.commit()
        return redirect(f"/view/{aid}" if aid else "/")
    f="".join([f"<div class='col-md-6 mb-3'><label class='field-label'>{c}</label><input name='{c}' value='{ag[c] if ag else ''}' class='form-control' style='background:#0f172a;border:1px solid #334155;color:white'></div>" for c in COLUMNS])
    title="Edit" if aid else "Add Agent"
    content=f"<a href='/' class='btn btn-sm btn-outline-light mb-3'>Back</a><div class='card p-4'><h4>{title}</h4><form method='post' class='row'>{f}<div class='col-12 mt-3'><button class='btn btn-warning fw-bold'>Save</button></div></form></div>"
    cnt=db.execute('SELECT COUNT(*) FROM agents').fetchone()[0]
    return render_page(content, cnt)

@app.route("/delete/<int:aid>", methods=["POST"])
def delete(aid):
    init_db()
    db=get_db()
    db.execute('DELETE FROM agents WHERE id=?',(aid,))
    db.execute('DELETE FROM ot_logs WHERE agent_id=?',(aid,))
    db.execute('DELETE FROM loss_logs WHERE agent_id=?',(aid,))
    db.commit()
    return redirect("/")

if __name__=="__main__":
    import os
    port=int(os.environ.get("PORT",5000))
    app.run(host="0.0.0.0",port=port)
