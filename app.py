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
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');
body{background:#0a0e1a;color:#e2e8f0;font-family:'Inter',system-ui;overflow-x:hidden}
.navbar{background:rgba(15,23,42,0.9)!important;backdrop-filter:blur(12px);border-bottom:1px solid #1e293b;position:sticky;top:0;z-index:1000}
.card{background:#111827;border:1px solid #1f2937;border-radius:20px;box-shadow:0 10px 30px rgba(0,0,0,0.3)}
.table{color:#e2e8f0;margin-bottom:0}
.table thead th{background:#0f172a;color:#94a3b8;border-bottom:2px solid #1e293b;font-size:11px;text-transform:uppercase;letter-spacing:1px;white-space:nowrap;padding:14px 12px;font-weight:700}
.table tbody td{border-color:#1f2937;vertical-align:middle;font-size:13px;padding:14px 12px;white-space:nowrap}
.table-hover tbody tr:hover{background:#1e293b!important}
.badge-id{background:#0f172a;border:1px solid #334155;color:#94a3b8;border-radius:8px;padding:6px 10px}
.btn-exec{background:linear-gradient(135deg,#fbbf24,#f59e0b);color:#0f172a;font-weight:800;border:none;border-radius:12px;padding:8px 18px;box-shadow:0 4px 15px rgba(251,191,36,0.3)}
.btn-exec:hover{transform:translateY(-2px);box-shadow:0 6px 20px rgba(251,191,36,0.4);color:#0f172a}
.search-box{background:#0f172a;border:1px solid #1f2937;color:white;border-radius:12px;padding:12px}
.search-box::placeholder{color:#475569}
.detail-card{background:#0f172a;border:1px solid #1e293b;border-radius:14px;padding:14px;transition:0.2s;height:100%;min-height:80px}
.detail-card:hover{border-color:#334155;transform:translateY(-2px)}
.field-label{color:#64748b;font-size:10px;text-transform:uppercase;letter-spacing:1px;font-weight:700;margin-bottom:4px}
.field-value{color:#f1f5f9;font-weight:600;font-size:13px;word-break:break-word;white-space:normal;line-height:1.4}
.agent-avatar{width:80px;height:80px;background:linear-gradient(135deg,#fbbf24,#f59e0b);border-radius:20px;display:flex;align-items:center;justify-content:center;font-size:32px;font-weight:900;color:#0f172a;box-shadow:0 8px 25px rgba(251,191,36,0.3)}
.stat-card{background:#0f172a;border:1px solid #1e293b;border-radius:16px;padding:16px;text-align:center}
.stat-value{font-size:28px;font-weight:800;line-height:1}
.ot-section{border:1px solid #065f46;background:linear-gradient(135deg,#111827,#064e3b0d);border-radius:20px}
.loss-section{border:1px solid #7f1d1d;background:linear-gradient(135deg,#111827,#7f1d1d0d);border-radius:20px}
.input-dark{background:#0a0e1a!important;border:1px solid #1f2937!important;color:white!important;border-radius:10px!important;padding:10px!important}
.input-dark:focus{border-color:#fbbf24!important;box-shadow:0 0 0 3px rgba(251,191,36,0.1)!important}
@media (max-width: 992px){
  .desktop-grid{grid-template-columns:1fr!important}
  .agent-sidebar{position:static!important}
}
.desktop-grid{display:grid;grid-template-columns:340px 1fr;gap:20px;align-items:start}
.agent-sidebar{position:sticky;top:90px}
.details-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:10px}
.ot-loss-grid{display:grid;grid-template-columns:1fr 1fr;gap:20px}
@media (max-width: 768px){
  .ot-loss-grid{grid-template-columns:1fr}
  .details-grid{grid-template-columns:1fr 1fr}
}
</style></head><body>
<nav class="navbar navbar-dark p-3"><div class="container-fluid d-flex justify-content-between align-items-center flex-wrap gap-2">
<div class="d-flex align-items-center gap-3"><div style="width:42px;height:42px;background:linear-gradient(135deg,#fbbf24,#f59e0b);border-radius:12px;display:flex;align-items:center;justify-content:center"><i class="bi bi-stars text-dark fs-5"></i></div><div><div class="fw-bold fs-5" style="letter-spacing:-0.5px">TEAM SHINE M9</div><div style="font-size:10px;color:#64748b;letter-spacing:2px;font-weight:700">OT + LOSS HOURS • EXECUTIVE</div></div><span class="badge bg-warning text-dark ms-2" style="border-radius:10px;padding:8px 12px;font-weight:800">__COUNT__ AGENTS</span></div>
<div class="d-flex gap-2"><a href="/" class="btn btn-sm btn-outline-light" style="border-radius:10px"><i class="bi bi-grid"></i> Dashboard</a><a href="/ot_report" class="btn btn-sm btn-outline-warning" style="border-radius:10px"><i class="bi bi-graph-up"></i> Reports</a><a href="/add" class="btn btn-sm btn-exec"><i class="bi bi-plus-lg"></i> Add Agent</a></div>
</div></nav><div class="container-fluid p-3 p-lg-4">__CONTENT__</div>
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
    fields="".join([f"<div class='detail-card'><div class='field-label'>{c}</div><div class='field-value'>{a[c] or '<span style=color:#334155>— empty —</span>'}</div></div>" for c in COLUMNS])
    ot_rows="".join([f"<tr><td>{l['ot_date']}</td><td><span class='badge {'bg-danger' if l['ot_type']=='RDOT' else 'bg-success'}'>{l['ot_type']}</span></td><td><b>{l['hours']}h</b></td><td>{l['remarks'] or ''}</td><td><form method='post' action='/delete_ot/{l['id']}'><button class='btn btn-sm btn-outline-danger' style='border-radius:8px'>X</button></form></td></tr>" for l in ot_logs])
    loss_rows="".join([f"<tr><td>{l['loss_date']}</td><td><span class='badge bg-danger'>{l['loss_type']}</span></td><td><b>{l['hours']}h</b></td><td>{l['remarks'] or ''}</td><td><form method='post' action='/delete_loss/{l['id']}'><button class='btn btn-sm btn-outline-danger' style='border-radius:8px'>X</button></form></td></tr>" for l in loss_logs])
    today = datetime.now().strftime("%Y-%m-%d")
    content=f"""
    <a href='/' class='btn btn-sm btn-outline-light mb-3' style='border-radius:10px'>← Back to Dashboard</a>
    <div class='desktop-grid'>
        <div class='agent-sidebar'>
            <div class='card p-4 text-center'>
                <div class='agent-avatar mx-auto mb-3'>{(a['NAME'] or 'A')[0]}</div>
                <div class='fw-bold fs-5 text-white' style='word-break:break-word'>{a['NAME']}</div>
                <div class='field-label mb-3'>{a['NBS ID'] or ''} • {a['TENCENT ID'] or ''}</div>
                <div class='row g-2 mb-3'>
                    <div class='col-6'><div class='stat-card'><div class='field-label'>TOTAL OT</div><div class='stat-value text-success'>{ot_t:.1f}h</div><div style='font-size:10px;color:#64748b'>Reg:{reg:.1f} RD:{rdot:.1f}</div></div></div>
                    <div class='col-6'><div class='stat-card'><div class='field-label'>LOSS HRS</div><div class='stat-value text-danger'>{loss_t:.1f}h</div></div></div>
                    <div class='col-12'><div class='stat-card' style='border:1px solid #fbbf24'><div class='field-label'>NET (OT - LOSS)</div><div class='stat-value text-warning' style='font-size:32px'>{net:+.1f}h</div></div></div>
                </div>
                <div class='text-start'>
                    <div class='field-label mb-2'>FULL PROFILE • 16 FIELDS</div>
                    <div class='details-grid'>{fields}</div>
                </div>
                <div class='d-grid gap-2 mt-4'>
                    <a href='/edit/{a['id']}' class='btn btn-outline-light' style='border-radius:12px'>Edit Agent</a>
                    <form method='post' action='/delete/{a['id']}' onsubmit="return confirm('Delete agent?')"><button class='btn btn-outline-danger w-100' style='border-radius:12px'>Delete Agent</button></form>
                </div>
            </div>
        </div>
        <div class='d-flex flex-column gap-3'>
            <div class='ot-loss-grid'>
                <div class='card p-4 ot-section'>
                    <div class='d-flex justify-content-between align-items-center mb-3'><h6 class='fw-bold text-success mb-0'><i class='bi bi-plus-circle'></i> Add OT (Rendered OT)</h6><span class='badge bg-success'>{len(ot_logs)} records</span></div>
                    <form method='post' action='/add_ot/{a['id']}' class='row g-2'>
                        <div class='col-4'><label class='field-label'>Date</label><input type='date' name='ot_date' value='{today}' class='form-control input-dark' required></div>
                        <div class='col-4'><label class='field-label'>Type</label><select name='ot_type' class='form-select input-dark'><option value='REGULAR'>NORMAL OT</option><option value='RDOT'>REST DAY OT</option></select></div>
                        <div class='col-4'><label class='field-label'>Hours</label><input type='number' step='0.5' name='hours' class='form-control input-dark' placeholder='2.5' required></div>
                        <div class='col-12'><label class='field-label'>Remarks</label><input name='remarks' class='form-control input-dark' placeholder='e.g. high volume, extended shift'></div>
                        <div class='col-12'><button class='btn btn-success w-100 fw-bold' style='border-radius:12px'>Save OT - {a['NAME']}</button></div>
                    </form>
                    <div class='table-responsive mt-4' style='max-height:400px;overflow-y:auto'><table class='table table-sm mb-0'><thead><tr><th>Date</th><th>Type</th><th>Hrs</th><th>Remarks</th><th></th></tr></thead><tbody>{ot_rows if ot_rows else '<tr><td colspan=5 class=text-center style=color:#475569;padding:20px>No OT yet - add on top</td></tr>'}</tbody></table></div>
                </div>
                <div class='card p-4 loss-section'>
                    <div class='d-flex justify-content-between align-items-center mb-3'><h6 class='fw-bold text-danger mb-0'><i class='bi bi-dash-circle'></i> Add LOSS Hours</h6><span class='badge bg-danger'>{len(loss_logs)} records</span></div>
                    <form method='post' action='/add_loss/{a['id']}' class='row g-2'>
                        <div class='col-4'><label class='field-label'>Date</label><input type='date' name='loss_date' value='{today}' class='form-control input-dark' required></div>
                        <div class='col-4'><label class='field-label'>Type</label><select name='loss_type' class='form-select input-dark'><option value='LATE'>LATE</option><option value='UNDERTIME'>UNDERTIME</option><option value='ABSENT'>ABSENT</option><option value='LOSS'>LOSS HRS</option><option value='OTHERS'>OTHERS</option></select></div>
                        <div class='col-4'><label class='field-label'>Hours</label><input type='number' step='0.5' name='hours' class='form-control input-dark' placeholder='1.5' required></div>
                        <div class='col-12'><label class='field-label'>Remarks</label><input name='remarks' class='form-control input-dark' placeholder='e.g. late 30 mins, system issue'></div>
                        <div class='col-12'><button class='btn btn-danger w-100 fw-bold' style='border-radius:12px'>Save LOSS Hours</button></div>
                    </form>
                    <div class='table-responsive mt-4' style='max-height:400px;overflow-y:auto'><table class='table table-sm mb-0'><thead><tr><th>Date</th><th>Type</th><th>Hrs</th><th>Remarks</th><th></th></tr></thead><tbody>{loss_rows if loss_rows else '<tr><td colspan=5 class=text-center style=color:#475569;padding:20px>No Loss yet</td></tr>'}</tbody></table></div>
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
