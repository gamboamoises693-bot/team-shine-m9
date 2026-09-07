
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
        created_at TEXT,
        FOREIGN KEY(agent_id) REFERENCES agents(id)
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
<title>TEAM SHINE M9 - OT</title>
<style>
body{background:#0f172a;color:#e2e8f0} .navbar{background:linear-gradient(90deg,#0f172a,#1e293b)!important;border-bottom:1px solid #334155}
.card{background:#1e293b;border:1px solid #334155;border-radius:16px} .table{color:#e2e8f0}
.table thead th{background:#0f172a;color:#94a3b8;border-bottom:2px solid #334155;font-size:11px;text-transform:uppercase;white-space:nowrap}
.table tbody td{border-color:#1e293b;vertical-align:middle;font-size:13px;white-space:nowrap}
.table-hover tbody tr:hover{background:#1e293b!important} .badge-id{background:#0f172a;border:1px solid #334155;color:#94a3b8}
.btn-exec{background:#fbbf24;color:#0f172a;font-weight:700;border:none} .search-box{background:#0f172a;border:1px solid #334155;color:white}
.detail-card{background:#0f172a;border:1px solid #334155} .field-label{color:#64748b;font-size:10px;text-transform:uppercase;letter-spacing:.8px} .field-value{color:#f1f5f9;font-weight:500}
</style></head><body>
<nav class="navbar navbar-dark p-3 sticky-top"><div class="container-fluid d-flex justify-content-between">
<div class="d-flex align-items-center gap-3"><i class="bi bi-stars fs-4 text-warning"></i><div><div class="fw-bold fs-5">TEAM SHINE M9</div><div style="font-size:11px;color:#94a3b8;letter-spacing:2px">OT TRACKER EXECUTIVE</div></div><span class="badge bg-warning text-dark ms-3">__COUNT__ AGENTS</span></div>
<div class="d-flex gap-2"><a href="/" class="btn btn-sm btn-outline-light">Dashboard</a><a href="/ot_report" class="btn btn-sm btn-outline-warning"><i class="bi bi-graph-up"></i> OT Report</a><a href="/add" class="btn btn-sm btn-exec">+ Add Agent</a></div>
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
    ot_summary = {}
    cur2 = db.execute('SELECT agent_id, SUM(hours) as total FROM ot_logs GROUP BY agent_id')
    for r in cur2.fetchall():
        ot_summary[r['agent_id']] = r['total']
    rows=""
    for a in agents:
        total = ot_summary.get(a['id'], 0)
        rows+=f"<tr><td><span class='badge badge-id'>{a['id']}</span></td><td><a href='/view/{a['id']}' class='text-decoration-none'><div class='fw-bold text-white'>{a['NAME'] or ''}</div><div style='font-size:11px;color:#94a3b8'>{a['NBS ID'] or ''}</div></a></td><td>{a['TENCENT ID'] or ''}</td><td>{a['PHONE NAME'] or ''}</td><td>{a['CONTACT NO.'] or ''}</td><td><span class='badge bg-warning text-dark'>{total:.1f}h OT</span></td><td><a href='/view/{a['id']}' class='btn btn-sm btn-warning fw-bold'><i class='bi bi-clock'></i> OT</a></td></tr>"
    content=f"<div class='card p-3 mb-3'><form class='d-flex gap-2' method='get'><input name='q' value='{q}' class='form-control search-box' placeholder='Search agent...'><button class='btn btn-light'>Search</button></form></div><div class='card p-0 overflow-hidden'><div class='table-responsive'><table class='table table-hover mb-0'><thead><tr><th>ID</th><th>Agent</th><th>Tencent</th><th>Phone</th><th>Contact</th><th>OT Total</th><th>Action</th></tr></thead><tbody>{rows if rows else '<tr><td colspan=7 class=text-center p-5>Empty</td></tr>'}</tbody></table></div></div>"
    return render_page(content, len(agents))

@app.route("/view/<int:aid>")
def view(aid):
    init_db()
    db=get_db()
    a=db.execute('SELECT * FROM agents WHERE id=?',(aid,)).fetchone()
    if not a: return redirect("/")
    logs = db.execute('SELECT * FROM ot_logs WHERE agent_id=? ORDER BY ot_date DESC', (aid,)).fetchall()
    total = db.execute('SELECT SUM(hours) as t, SUM(CASE WHEN ot_type="RDOT" THEN hours ELSE 0 END) as rdot, SUM(CASE WHEN ot_type="REGULAR" THEN hours ELSE 0 END) as reg FROM ot_logs WHERE agent_id=?', (aid,)).fetchone()
    t = total['t'] or 0
    rdot = total['rdot'] or 0
    reg = total['reg'] or 0
    fields=""
    for c in COLUMNS:
        fields+=f"<div class='col-md-6 mb-2'><div class='detail-card p-2 rounded-3'><div class='field-label'>{c}</div><div class='field-value'>{a[c] or '-'} </div></div></div>"
    ot_rows=""
    for log in logs:
        badge = "bg-danger" if log['ot_type']=="RDOT" else "bg-success"
        ot_rows+=f"<tr><td>{log['ot_date']}</td><td><span class='badge {badge}'>{log['ot_type']}</span></td><td><b>{log['hours']}h</b></td><td>{log['remarks'] or ''}</td><td><form method='post' action='/delete_ot/{log['id']}'><button class='btn btn-sm btn-outline-danger'>X</button></form></td></tr>"
    today = datetime.now().strftime("%Y-%m-%d")
    content=f"""
    <a href='/' class='btn btn-sm btn-outline-light mb-3'>Back</a>
    <div class='row'>
        <div class='col-md-4'>
            <div class='card p-4 text-center'>
                <div style='width:70px;height:70px;background:linear-gradient(135deg,#fbbf24,#f59e0b);border-radius:16px;display:flex;align-items:center;justify-content:center;margin:0 auto 12px;font-size:28px;font-weight:800;color:#0f172a'>{(a['NAME'] or 'A')[0]}</div>
                <div class='fw-bold fs-5 text-white'>{a['NAME']}</div>
                <div class='row mt-3 g-2'>
                    <div class='col-4'><div class='detail-card p-2 rounded'><div class='field-label'>TOTAL</div><div class='fw-bold text-warning'>{t:.1f}h</div></div></div>
                    <div class='col-4'><div class='detail-card p-2 rounded'><div class='field-label'>REG OT</div><div class='fw-bold text-success'>{reg:.1f}h</div></div></div>
                    <div class='col-4'><div class='detail-card p-2 rounded'><div class='field-label'>RDOT</div><div class='fw-bold text-danger'>{rdot:.1f}h</div></div></div>
                </div>
                <hr style='border-color:#334155'>
                <div class='row text-start'>{fields}</div>
            </div>
        </div>
        <div class='col-md-8'>
            <div class='card p-4 mb-3' style='border:1px solid #fbbf24'>
                <h5 class='fw-bold text-white'>Add Rendered OT</h5>
                <form method='post' action='/add_ot/{a['id']}' class='row g-2 mt-2'>
                    <div class='col-md-3'><label class='field-label'>Date</label><input type='date' name='ot_date' value='{today}' class='form-control' style='background:#0f172a;border:1px solid #334155;color:white' required></div>
                    <div class='col-md-3'><label class='field-label'>OT Type</label><select name='ot_type' class='form-select' style='background:#0f172a;border:1px solid #334155;color:white'><option value='REGULAR'>REGULAR OT</option><option value='RDOT'>REST DAY OT (RDOT)</option></select></div>
                    <div class='col-md-2'><label class='field-label'>Hours</label><input type='number' step='0.5' name='hours' class='form-control' style='background:#0f172a;border:1px solid #334155;color:white' placeholder='2.5' required></div>
                    <div class='col-md-4'><label class='field-label'>Remarks</label><input name='remarks' class='form-control' style='background:#0f172a;border:1px solid #334155;color:white' placeholder='Reason'></div>
                    <div class='col-12'><button class='btn btn-warning fw-bold w-100'>Save OT for {a['NAME']}</button></div>
                </form>
            </div>
            <div class='card p-0 overflow-hidden'><div class='p-3 d-flex justify-content-between'><h6 class='fw-bold mb-0'>OT History</h6><span class='badge bg-dark'>{len(logs)} records</span></div><div class='table-responsive'><table class='table mb-0'><thead><tr><th>Date</th><th>Type</th><th>Hours</th><th>Remarks</th><th></th></tr></thead><tbody>{ot_rows if ot_rows else '<tr><td colspan=5 class=text-center p-4>No OT yet</td></tr>'}</tbody></table></div></div>
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

@app.route("/delete_ot/<int:oid>", methods=["POST"])
def delete_ot(oid):
    init_db()
    db=get_db()
    cur=db.execute('SELECT agent_id FROM ot_logs WHERE id=?',(oid,)).fetchone()
    aid = cur['agent_id'] if cur else 0
    db.execute('DELETE FROM ot_logs WHERE id=?',(oid,))
    db.commit()
    return redirect(f"/view/{aid}" if aid else "/")

@app.route("/ot_report")
def ot_report():
    init_db()
    db=get_db()
    cur=db.execute('SELECT a.id, a.NAME, a."TENCENT ID", SUM(o.hours) as total, SUM(CASE WHEN o.ot_type="REGULAR" THEN o.hours ELSE 0 END) as reg, SUM(CASE WHEN o.ot_type="RDOT" THEN o.hours ELSE 0 END) as rdot FROM agents a LEFT JOIN ot_logs o ON a.id=o.agent_id GROUP BY a.id HAVING total>0 ORDER BY total DESC')
    rows=cur.fetchall()
    tr="".join([f"<tr><td>{r['id']}</td><td><a href='/view/{r['id']}' class='text-white fw-bold'>{r['NAME']}</a></td><td class='text-warning fw-bold'>{r['total']:.1f}h</td><td>{r['reg'] or 0:.1f}h</td><td>{r['rdot'] or 0:.1f}h</td></tr>" for r in rows])
    gtotal=db.execute('SELECT SUM(hours) as t FROM ot_logs').fetchone()
    content=f"<h4 class='fw-bold'>OT Report</h4><div class='card p-3 mb-3'><div class='fs-2 fw-bold text-warning'>Grand Total: {gtotal['t'] or 0:.1f} hours</div></div><div class='card p-0 overflow-hidden'><table class='table mb-0'><thead><tr><th>ID</th><th>Agent</th><th>Total</th><th>Regular</th><th>RDOT</th></tr></thead><tbody>{tr if tr else '<tr><td colspan=5 class=text-center>No OT</td></tr>'}</tbody></table></div>"
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
    f=""
    for c in COLUMNS:
        v=ag[c] if ag else ""
        f+=f"<div class='col-md-6 mb-3'><label class='field-label'>{c}</label><input name='{c}' value='{v}' class='form-control' style='background:#0f172a;border:1px solid #334155;color:white'></div>"
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
    db.commit()
    return redirect("/")

if __name__=="__main__":
    import os
    port=int(os.environ.get("PORT",5000))
    app.run(host="0.0.0.0",port=port)
