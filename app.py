
import sqlite3
from flask import Flask, request, redirect, g, send_file
from datetime import datetime
import io

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
<title>TEAM SHINE M9 - Executive</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');
body{background:#080c14;color:#e2e8f0;font-family:'Inter',system-ui}
.navbar{background:rgba(15,23,42,0.95)!important;backdrop-filter:blur(16px);border-bottom:1px solid #1e293b}
.card{background:#111827;border:1px solid #1f2937;border-radius:20px}
.table{color:#e2e8f0;margin-bottom:0}
.table thead th{background:#0f172a;color:#fbbf24;border-bottom:2px solid #fbbf24;font-size:11px;text-transform:uppercase;letter-spacing:1px;padding:14px 12px;font-weight:800}
.table tbody td{border-color:#1f2937;vertical-align:middle;font-size:13px;padding:14px 12px;color:#e2e8f0}
.table tbody tr{background:#111827}
.table tbody tr:nth-child(even){background:#0f172a}
.table-hover tbody tr:hover{background:#1e293b!important}
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
.agent-name-dark:hover{color:#fbbf24!important}
@media (max-width: 992px){.desktop-grid{grid-template-columns:1fr!important}.agent-sidebar{position:static!important}.ot-loss-grid{grid-template-columns:1fr!important}}
</style></head><body>
<nav class="navbar navbar-dark p-3 sticky-top"><div class="container-fluid d-flex justify-content-between flex-wrap gap-2">
<div class="d-flex align-items-center gap-3"><div style="width:42px;height:42px;background:linear-gradient(135deg,#fbbf24,#f59e0b);border-radius:12px;display:flex;align-items:center;justify-content:center"><i class="bi bi-stars text-dark fs-5"></i></div><div><div class="fw-bold fs-5">TEAM SHINE M9</div><div style="font-size:10px;color:#64748b;letter-spacing:2px;font-weight:700">EXECUTIVE • OT + LOSS + CHARTS</div></div><span class="badge bg-warning text-dark ms-2" style="border-radius:10px;padding:8px 12px;font-weight:800">__COUNT__ AGENTS</span></div>
<div class="d-flex gap-2 flex-wrap"><a href="/" class="btn btn-sm btn-outline-light" style="border-radius:10px">Dashboard</a><a href="/ot_report" class="btn btn-sm btn-outline-warning" style="border-radius:10px"><i class="bi bi-graph-up"></i> Reports</a><a href="/export_excel" class="btn btn-sm btn-success" style="border-radius:10px"><i class="bi bi-file-earmark-excel"></i> Export Excel</a><a href="/add" class="btn btn-sm btn-exec">+ Add Agent</a></div>
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
    ot_sum = {r['agent_id']: r['t'] for r in db.execute('SELECT agent_id, SUM(hours) as t FROM ot_logs GROUP BY agent_id').fetchall()}
    loss_sum = {r['agent_id']: r['t'] for r in db.execute('SELECT agent_id, SUM(hours) as t FROM loss_logs GROUP BY agent_id').fetchall()}
    rows=""
    for a in agents:
        ot = ot_sum.get(a['id'], 0) or 0
        loss = loss_sum.get(a['id'], 0) or 0
        net = ot - loss
        rows+=f"<tr><td><span class='badge badge-id'>{a['id']}</span></td><td><a href='/view/{a['id']}' class='agent-name-dark text-decoration-none'>{a['NAME'] or ''}<br><small style='color:#94a3b8;font-weight:400'>{a['NBS ID'] or ''} • {a['TENCENT ID'] or ''}</small></a></td><td><span class='badge bg-dark border text-light'>{a['TENCENT ID'] or ''}</span></td><td style='color:#cbd5e1'>{a['PHONE NAME'] or ''}</td><td><span class='badge bg-success'>{ot:.1f}h</span></td><td><span class='badge bg-danger'>{loss:.1f}h</span></td><td><span class='badge bg-warning text-dark fw-bold'>{net:+.1f}h</span></td><td><a href='/view/{a['id']}' class='btn btn-sm btn-warning fw-bold' style='border-radius:10px'>Manage</a></td></tr>"
    content=f"<div class='card p-3 mb-3'><form class='d-flex gap-2' method='get'><input name='q' value='{q}' class='form-control search-box' placeholder='Search agent...'><button class='btn btn-light' style='border-radius:12px'>Search</button></form></div><div class='card p-0 overflow-hidden'><div class='table-responsive'><table class='table table-hover mb-0'><thead><tr><th>ID</th><th>AGENT (VISIBLE NOW!)</th><th>TENCENT</th><th>PHONE</th><th>OT</th><th>LOSS</th><th>NET</th><th>ACTION</th></tr></thead><tbody>{rows if rows else '<tr><td colspan=8 class=text-center p-5>Empty</td></tr>'}</tbody></table></div></div>"
    return render_page(content, len(agents))

@app.route("/view/<int:aid>")
def view(aid):
    init_db(); db=get_db()
    a=db.execute('SELECT * FROM agents WHERE id=?',(aid,)).fetchone()
    if not a: return redirect("/")
    ot_logs = db.execute('SELECT * FROM ot_logs WHERE agent_id=? ORDER BY ot_date DESC', (aid,)).fetchall()
    loss_logs = db.execute('SELECT * FROM loss_logs WHERE agent_id=? ORDER BY loss_date DESC', (aid,)).fetchall()
    ot_total = db.execute('SELECT SUM(hours) as t, SUM(CASE WHEN ot_type="RDOT" THEN hours ELSE 0 END) as rdot, SUM(CASE WHEN ot_type="REGULAR" THEN hours ELSE 0 END) as reg FROM ot_logs WHERE agent_id=?', (aid,)).fetchone()
    loss_total = db.execute('SELECT SUM(hours) as t FROM loss_logs WHERE agent_id=?', (aid,)).fetchone()
    ot_t = ot_total['t'] or 0; rdot = ot_total['rdot'] or 0; reg = ot_total['reg'] or 0; loss_t = loss_total['t'] or 0; net = ot_t - loss_t
    fields="".join([f"<div class='detail-card'><div class='field-label'>{c}</div><div class='field-value'>{a[c] or '<span style=color:#334155>—</span>'}</div></div>" for c in COLUMNS])
    ot_rows="".join([f"<tr style='background:#111827'><td style='color:#e2e8f0'>{l['ot_date']}</td><td><span class='badge {'bg-danger' if l['ot_type']=='RDOT' else 'bg-success'}'>{l['ot_type']}</span></td><td style='color:#22c55e;font-weight:700'>{l['hours']}h</td><td style='color:#94a3b8'>{l['remarks'] or ''}</td><td><form method='post' action='/delete_ot/{l['id']}'><button class='btn btn-sm btn-outline-danger'>X</button></form></td></tr>" for l in ot_logs])
    loss_rows="".join([f"<tr style='background:#111827'><td style='color:#e2e8f0'>{l['loss_date']}</td><td><span class='badge bg-danger'>{l['loss_type']}</span></td><td style='color:#ef4444;font-weight:700'>{l['hours']}h</td><td style='color:#94a3b8'>{l['remarks'] or ''}</td><td><form method='post' action='/delete_loss/{l['id']}'><button class='btn btn-sm btn-outline-danger'>X</button></form></td></tr>" for l in loss_logs])
    from datetime import datetime as dt; today = dt.now().strftime("%Y-%m-%d")
    content=f"""
    <a href='/' class='btn btn-sm btn-outline-light mb-3' style='border-radius:10px'>← Back Dashboard</a>
    <div class='desktop-grid'>
        <div class='agent-sidebar'>
            <div class='card p-4 text-center'>
                <div class='agent-avatar mx-auto mb-3'>{(a['NAME'] or 'A')[0]}</div>
                <div class='fw-bold fs-5 text-white' style='word-break:break-word'>{a['NAME']}</div>
                <div class='row g-2 my-3'>
                    <div class='col-6'><div class='stat-card'><div class='field-label'>TOTAL OT</div><div class='stat-value text-success'>{ot_t:.1f}h</div><div style='font-size:10px;color:#64748b'>Reg:{reg:.1f} RD:{rdot:.1f}</div></div></div>
                    <div class='col-6'><div class='stat-card'><div class='field-label'>LOSS</div><div class='stat-value text-danger'>{loss_t:.1f}h</div></div></div>
                    <div class='col-12'><div class='stat-card' style='border:1px solid #fbbf24'><div class='field-label'>NET</div><div class='stat-value text-warning' style='font-size:32px'>{net:+.1f}h</div></div></div>
                </div>
                <div class='text-start'><div class='field-label mb-2'>FULL PROFILE - 16 FIELDS</div><div class='details-grid'>{fields}</div></div>
            </div>
        </div>
        <div class='d-flex flex-column gap-3'>
            <div class='ot-loss-grid'>
                <div class='card p-4' style='border:1px solid #22c55e'><h6 class='fw-bold text-success'>Add OT</h6>
                <form method='post' action='/add_ot/{a['id']}' class='row g-2 mt-2'>
                <div class='col-4'><input type='date' name='ot_date' value='{today}' class='form-control input-dark' required></div>
                <div class='col-4'><select name='ot_type' class='form-select input-dark'><option value='REGULAR'>NORMAL OT</option><option value='RDOT'>RDOT</option></select></div>
                <div class='col-4'><input type='number' step='0.5' name='hours' class='form-control input-dark' placeholder='2.5' required></div>
                <div class='col-12'><input name='remarks' class='form-control input-dark' placeholder='Remarks'></div>
                <div class='col-12'><button class='btn btn-success w-100 fw-bold' style='border-radius:12px'>Save OT</button></div></form>
                <div class='table-responsive mt-3' style='max-height:300px'><table class='table table-sm mb-0'><thead><tr><th style='color:#fbbf24'>Date</th><th style='color:#fbbf24'>Type</th><th style='color:#fbbf24'>Hrs</th><th style='color:#fbbf24'>Remarks</th><th></th></tr></thead><tbody>{ot_rows if ot_rows else '<tr><td colspan=5 class=text-center style=color:#475569> No OT yet</td></tr>'}</tbody></table></div></div>
                <div class='card p-4' style='border:1px solid #ef4444'><h6 class='fw-bold text-danger'>Add LOSS</h6>
                <form method='post' action='/add_loss/{a['id']}' class='row g-2 mt-2'>
                <div class='col-4'><input type='date' name='loss_date' value='{today}' class='form-control input-dark' required></div>
                <div class='col-4'><select name='loss_type' class='form-select input-dark'><option value='LATE'>LATE</option><option value='UNDERTIME'>UNDERTIME</option><option value='ABSENT'>ABSENT</option><option value='LOSS'>LOSS</option></select></div>
                <div class='col-4'><input type='number' step='0.5' name='hours' class='form-control input-dark' placeholder='1.5' required></div>
                <div class='col-12'><input name='remarks' class='form-control input-dark' placeholder='Remarks'></div>
                <div class='col-12'><button class='btn btn-danger w-100 fw-bold' style='border-radius:12px'>Save LOSS</button></div></form>
                <div class='table-responsive mt-3' style='max-height:300px'><table class='table table-sm mb-0'><thead><tr><th style='color:#fbbf24'>Date</th><th style='color:#fbbf24'>Type</th><th style='color:#fbbf24'>Hrs</th><th style='color:#fbbf24'>Remarks</th><th></th></tr></thead><tbody>{loss_rows if loss_rows else '<tr><td colspan=5 class=text-center style=color:#475569> No Loss yet</td></tr>'}</tbody></table></div></div>
            </div>
        </div>
    </div>
    """
    cnt=db.execute('SELECT COUNT(*) FROM agents').fetchone()[0]
    return render_page(content, cnt)

@app.route("/add_ot/<int:aid>", methods=["POST"])
def add_ot(aid):
    init_db(); db=get_db()
    db.execute('INSERT INTO ot_logs (agent_id, ot_date, ot_type, hours, remarks, created_at) VALUES (?,?,?,?,?,?)',(aid, request.form.get('ot_date'), request.form.get('ot_type'), float(request.form.get('hours',0)), request.form.get('remarks',''), datetime.now().isoformat()))
    db.commit(); return redirect(f"/view/{aid}")

@app.route("/add_loss/<int:aid>", methods=["POST"])
def add_loss(aid):
    init_db(); db=get_db()
    db.execute('INSERT INTO loss_logs (agent_id, loss_date, loss_type, hours, remarks, created_at) VALUES (?,?,?,?,?,?)',(aid, request.form.get('loss_date'), request.form.get('loss_type'), float(request.form.get('hours',0)), request.form.get('remarks',''), datetime.now().isoformat()))
    db.commit(); return redirect(f"/view/{aid}")

@app.route("/delete_ot/<int:oid>", methods=["POST"])
def delete_ot(oid):
    init_db(); db=get_db()
    cur=db.execute('SELECT agent_id FROM ot_logs WHERE id=?',(oid,)).fetchone()
    aid = cur['agent_id'] if cur else 0
    db.execute('DELETE FROM ot_logs WHERE id=?',(oid,)); db.commit()
    return redirect(f"/view/{aid}" if aid else "/")

@app.route("/delete_loss/<int:oid>", methods=["POST"])
def delete_loss(oid):
    init_db(); db=get_db()
    cur=db.execute('SELECT agent_id FROM loss_logs WHERE id=?',(oid,)).fetchone()
    aid = cur['agent_id'] if cur else 0
    db.execute('DELETE FROM loss_logs WHERE id=?',(oid,)); db.commit()
    return redirect(f"/view/{aid}" if aid else "/")

@app.route("/ot_report")
def ot_report():
    init_db(); db=get_db()
    ot_map = {r['agent_id']: r['t'] for r in db.execute('SELECT agent_id, SUM(hours) as t FROM ot_logs GROUP BY agent_id').fetchall()}
    loss_map = {r['agent_id']: r['t'] for r in db.execute('SELECT agent_id, SUM(hours) as t FROM loss_logs GROUP BY agent_id').fetchall()}
    agents = db.execute('SELECT * FROM agents ORDER BY NAME').fetchall()
    labels=[]; ot_data=[]; loss_data=[]
    table_rows=""
    for a in agents:
        ot = ot_map.get(a['id'],0) or 0
        loss = loss_map.get(a['id'],0) or 0
        if ot==0 and loss==0: continue
        labels.append(a['NAME'].split(',')[0])
        ot_data.append(round(ot,1)); loss_data.append(round(loss,1))
        # FIXED: visible font color - dark background table with light text
        table_rows+=f"<tr style='background:#111827'><td style='color:#94a3b8'>{a['id']}</td><td><div class='agent-name-dark'>{a['NAME']}</div><small style='color:#64748b'>{a['NBS ID'] or ''} • {a['TENCENT ID'] or ''}</small></td><td style='color:#22c55e;font-weight:700'>{ot:.1f}h</td><td style='color:#ef4444;font-weight:700'>{loss:.1f}h</td><td style='color:#fbbf24;font-weight:800'>{ot-loss:+.1f}h</td></tr>"
    g_ot = db.execute('SELECT SUM(hours) as t, SUM(CASE WHEN ot_type="REGULAR" THEN hours ELSE 0 END) as reg, SUM(CASE WHEN ot_type="RDOT" THEN hours ELSE 0 END) as rdot FROM ot_logs').fetchone()
    g_loss = db.execute('SELECT SUM(hours) as t FROM loss_logs').fetchone()
    total_ot = g_ot['t'] or 0; reg_ot = g_ot['reg'] or 0; rdot_ot = g_ot['rdot'] or 0; total_loss = g_loss['t'] or 0
    top_ot = sorted([(a['NAME'], ot_map.get(a['id'],0) or 0) for a in agents if ot_map.get(a['id'],0)], key=lambda x: x[1], reverse=True)[:10]
    top_loss = sorted([(a['NAME'], loss_map.get(a['id'],0) or 0) for a in agents if loss_map.get(a['id'],0)], key=lambda x: x[1], reverse=True)[:10]
    import json
    content=f"""
    <div class='d-flex justify-content-between align-items-center mb-4 flex-wrap gap-2'>
        <h4 class='fw-bold text-white mb-0'><i class='bi bi-bar-chart-line text-warning'></i> Executive Reports - FIXED VISIBLE FONTS</h4>
        <a href='/export_excel' class='btn btn-success btn-sm' style='border-radius:10px'><i class='bi bi-file-earmark-excel'></i> Download Executive Excel (No Gridlines + Charts)</a>
    </div>
    <div class='row g-3 mb-4'>
        <div class='col-md-3'><div class='card p-3 text-center' style='border:1px solid #22c55e'><div class='field-label'>TOTAL OT</div><div class='fs-1 fw-bold text-success'>{total_ot:.1f}h</div><div style='font-size:11px;color:#6ee7b7'>Reg {reg_ot:.1f}h • RDOT {rdot_ot:.1f}h</div></div></div>
        <div class='col-md-3'><div class='card p-3 text-center' style='border:1px solid #ef4444'><div class='field-label'>TOTAL LOSS</div><div class='fs-1 fw-bold text-danger'>{total_loss:.1f}h</div></div></div>
        <div class='col-md-3'><div class='card p-3 text-center' style='border:1px solid #fbbf24'><div class='field-label'>NET</div><div class='fs-1 fw-bold text-warning'>{total_ot-total_loss:+.1f}h</div></div></div>
        <div class='col-md-3'><div class='card p-3 text-center'><div class='field-label'>ACTIVE</div><div class='fs-1 fw-bold text-white'>{len(labels)}</div></div></div>
    </div>
    <div class='row g-3 mb-4'>
        <div class='col-lg-8'><div class='card p-4'><h6 class='fw-bold mb-3 text-white'><i class='bi bi-graph-up text-success'></i> OT vs LOSS Comparison</h6><canvas id='otLossChart' height='120'></canvas></div></div>
        <div class='col-lg-4'><div class='card p-4 h-100'><h6 class='fw-bold mb-3 text-white'><i class='bi bi-pie-chart text-warning'></i> Distribution</h6><canvas id='pieChart'></canvas></div></div>
    </div>
    <div class='row g-3 mb-4'>
        <div class='col-md-6'><div class='card p-4'><h6 class='fw-bold text-success'>Top 10 OT</h6><canvas id='topOtChart' height='120'></canvas></div></div>
        <div class='col-md-6'><div class='card p-4'><h6 class='fw-bold text-danger'>Top 10 LOSS</h6><canvas id='topLossChart' height='120'></canvas></div></div>
    </div>
    <div class='card p-0 overflow-hidden'>
        <div class='p-3 d-flex justify-content-between align-items-center' style='background:#0f172a;border-bottom:1px solid #fbbf24'><h6 class='fw-bold mb-0 text-white'>Detailed Ranking - AGENT VISIBLE NOW!</h6><span class='badge bg-warning text-dark'>FIXED FONT COLOR</span></div>
        <div class='table-responsive'><table class='table table-hover mb-0'><thead><tr><th style='color:#fbbf24'>ID</th><th style='color:#fbbf24'>AGENT</th><th style='color:#fbbf24'>OT</th><th style='color:#fbbf24'>LOSS</th><th style='color:#fbbf24'>NET</th></tr></thead><tbody>{table_rows if table_rows else '<tr><td colspan=5 class=text-center style=color:#94a3b8>No data</td></tr>'}</tbody></table></div>
    </div>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script>
    new Chart(document.getElementById('otLossChart'), {{type:'bar', data:{{labels:{json.dumps(labels)}, datasets:[{{label:'OT', data:{json.dumps(ot_data)}, backgroundColor:'#22c55e', borderRadius:8}}, {{label:'LOSS', data:{json.dumps(loss_data)}, backgroundColor:'#ef4444', borderRadius:8}}]}}, options:{{responsive:true, scales:{{x:{{ticks:{{color:'#94a3b8'}}, grid:{{color:'#1f2937'}}}}, y:{{ticks:{{color:'#94a3b8'}}, grid:{{color:'#1f2937'}}}}}}}} }});
    new Chart(document.getElementById('pieChart'), {{type:'doughnut', data:{{labels:['Regular OT','RDOT','LOSS'], datasets:[{{data:[{reg_ot},{rdot_ot},{total_loss}], backgroundColor:['#22c55e','#f59e0b','#ef4444']}}]}}, options:{{responsive:true, plugins:{{legend:{{position:'bottom', labels:{{color:'#e2e8f0'}}}}}}}} }});
    new Chart(document.getElementById('topOtChart'), {{type:'bar', data:{{labels:{json.dumps([x[0].split(',')[0] for x in top_ot])}, datasets:[{{data:{json.dumps([x[1] for x in top_ot])}, backgroundColor:'#22c55e', borderRadius:8}}]}}, options:{{indexAxis:'y', responsive:true, plugins:{{legend:{{display:false}}}}}} }});
    new Chart(document.getElementById('topLossChart'), {{type:'bar', data:{{labels:{json.dumps([x[0].split(',')[0] for x in top_loss])}, datasets:[{{data:{json.dumps([x[1] for x in top_loss])}, backgroundColor:'#ef4444', borderRadius:8}}]}}, options:{{indexAxis:'y', responsive:true, plugins:{{legend:{{display:false}}}}}} }});
    </script>
    """
    cnt=db.execute('SELECT COUNT(*) FROM agents').fetchone()[0]
    return render_page(content, cnt)

@app.route("/export_excel")
def export_excel():
    init_db(); db=get_db()
    try:
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
        from openpyxl.chart import BarChart, PieChart, Reference
        from openpyxl.worksheet.table import Table, TableStyleInfo
        from openpyxl.utils import get_column_letter
    except:
        return "Add openpyxl to requirements.txt: openpyxl", 500
    
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Executive Summary"
    ws.sheet_view.showGridLines = False
    
    # Executive styling
    header_fill = PatternFill(start_color="0f172a", end_color="0f172a", fill_type="solid")
    gold_fill = PatternFill(start_color="fbbf24", end_color="fbbf24", fill_type="solid")
    green_fill = PatternFill(start_color="22c55e", end_color="22c55e", fill_type="solid")
    red_fill = PatternFill(start_color="ef4444", end_color="ef4444", fill_type="solid")
    dark_fill = PatternFill(start_color="111827", end_color="111827", fill_type="solid")
    white_font = Font(bold=True, color="FFFFFF", size=12)
    dark_font = Font(bold=True, color="0f172a", size=11)
    normal_font = Font(color="1f2937", size=11)
    bold_font = Font(bold=True, color="0f172a", size=11)
    
    # Title
    ws.merge_cells('A1:I1')
    ws['A1'] = "TEAM SHINE M9 - EXECUTIVE OT + LOSS REPORT"
    ws['A1'].font = Font(bold=True, color="FFFFFF", size=16)
    ws['A1'].fill = header_fill
    ws['A1'].alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 35
    
    ws['A2'] = f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')} | Executive Dashboard"
    ws['A2'].font = Font(italic=True, color="64748b", size=10)
    
    # Grand totals as table
    ws['A4'] = "GRAND TOTALS - EXECUTIVE OVERVIEW"
    ws['A4'].font = Font(bold=True, color="0f172a", size=12)
    ws['A4'].fill = gold_fill
    
    g_ot = db.execute('SELECT SUM(hours) as t, SUM(CASE WHEN ot_type="REGULAR" THEN hours ELSE 0 END) as reg, SUM(CASE WHEN ot_type="RDOT" THEN hours ELSE 0 END) as rdot FROM ot_logs').fetchone()
    g_loss = db.execute('SELECT SUM(hours) as t FROM loss_logs').fetchone()
    total_ot = g_ot['t'] or 0; reg_ot = g_ot['reg'] or 0; rdot_ot = g_ot['rdot'] or 0; total_loss = g_loss['t'] or 0
    
    totals = [
        ["Metric", "Hours", "Notes"],
        ["Total OT", total_ot, "All OT rendered"],
        ["Regular OT (Normal)", reg_ot, "Sept 1-4 Normal OT"],
        ["RDOT (Rest Day OT)", rdot_ot, "Sept 5-6 Rest Day OT"],
        ["Total LOSS", total_loss, "Late/Undertime/Absent"],
        ["NET (OT - LOSS)", total_ot - total_loss, "Final net hours"],
    ]
    for r, row in enumerate(totals, start=5):
        for c, val in enumerate(row, start=1):
            cell = ws.cell(row=r, column=c, value=val)
            if r==5:
                cell.font = white_font
                cell.fill = header_fill
            else:
                cell.font = bold_font if c==1 else normal_font
                cell.border = Border(left=Side(style='thin', color='e5e7eb'), right=Side(style='thin', color='e5e7eb'), top=Side(style='thin', color='e5e7eb'), bottom=Side(style='thin', color='e5e7eb'))
    
    # Agent ranking table - executive with no gridlines but table style
    start_row = 12
    ws.cell(row=start_row, column=1, value="AGENT RANKING - OT vs LOSS (EXECUTIVE TABLE - NO GRIDLINES)").font = Font(bold=True, size=12)
    ws.cell(row=start_row, column=1).fill = gold_fill
    
    headers = ["ID", "NAME", "NBS ID", "TENCENT ID", "Total OT", "Regular OT", "RDOT", "Total LOSS", "NET"]
    for c, h in enumerate(headers, start=1):
        cell = ws.cell(row=start_row+1, column=c, value=h)
        cell.font = white_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center")
    
    ot_map = {r['agent_id']: r['t'] for r in db.execute('SELECT agent_id, SUM(hours) as t FROM ot_logs GROUP BY agent_id').fetchall()}
    loss_map = {r['agent_id']: r['t'] for r in db.execute('SELECT agent_id, SUM(hours) as t FROM loss_logs GROUP BY agent_id').fetchall()}
    ot_reg = {r['agent_id']: r['t'] for r in db.execute('SELECT agent_id, SUM(hours) as t FROM ot_logs WHERE ot_type="REGULAR" GROUP BY agent_id').fetchall()}
    ot_rdot = {r['agent_id']: r['t'] for r in db.execute('SELECT agent_id, SUM(hours) as t FROM ot_logs WHERE ot_type="RDOT" GROUP BY agent_id').fetchall()}
    
    row_idx = start_row+2
    for a in db.execute('SELECT * FROM agents ORDER BY NAME').fetchall():
        ot = ot_map.get(a['id'],0) or 0
        loss = loss_map.get(a['id'],0) or 0
        if ot==0 and loss==0: continue
        ws.cell(row=row_idx, column=1, value=a['id']).font = normal_font
        ws.cell(row=row_idx, column=2, value=a['NAME']).font = Font(bold=True, color="0f172a")
        ws.cell(row=row_idx, column=3, value=a['NBS ID']).font = normal_font
        ws.cell(row=row_idx, column=4, value=a['TENCENT ID']).font = normal_font
        ws.cell(row=row_idx, column=5, value=ot).font = Font(bold=True, color="15803d")
        ws.cell(row=row_idx, column=6, value=ot_reg.get(a['id'],0) or 0).font = normal_font
        ws.cell(row=row_idx, column=7, value=ot_rdot.get(a['id'],0) or 0).font = normal_font
        ws.cell(row=row_idx, column=8, value=loss).font = Font(bold=True, color="dc2626")
        ws.cell(row=row_idx, column=9, value=ot-loss).font = Font(bold=True, color="b45309")
        # alternating row color
        if row_idx % 2 == 0:
            for c in range(1,10):
                ws.cell(row=row_idx, column=c).fill = PatternFill(start_color="f9fafb", end_color="f9fafb", fill_type="solid")
        row_idx+=1
    
    # Add Excel chart - OT vs LOSS bar chart
    chart1 = BarChart()
    chart1.type = "col"
    chart1.style = 10
    chart1.title = "OT vs LOSS per Agent"
    chart1.y_axis.title = 'Hours'
    chart1.x_axis.title = 'Agent'
    data = Reference(ws, min_col=5, min_row=start_row+1, max_row=row_idx-1, max_col=8)
    cats = Reference(ws, min_col=2, min_row=start_row+2, max_row=row_idx-1)
    chart1.add_data(data, titles_from_data=True)
    chart1.set_categories(cats)
    chart1.shape = 4
    ws.add_chart(chart1, "K5")
    
    # Pie chart for totals
    ws2 = wb.create_sheet("Charts Data")
    ws2.sheet_view.showGridLines = False
    ws2['A1'] = "OT Distribution for Pie Chart"
    ws2['A1'].font = white_font
    ws2['A1'].fill = header_fill
    ws2['A2'] = "Type"; ws2['B2'] = "Hours"
    ws2['A3'] = "Regular OT"; ws2['B3'] = reg_ot
    ws2['A4'] = "RDOT"; ws2['B4'] = rdot_ot
    ws2['A5'] = "LOSS"; ws2['B5'] = total_loss
    
    pie = PieChart()
    labels = Reference(ws2, min_col=1, min_row=3, max_row=5)
    data = Reference(ws2, min_col=2, min_row=2, max_row=5)
    pie.add_data(data, titles_from_data=True)
    pie.set_categories(labels)
    pie.title = "OT vs LOSS Distribution"
    ws2.add_chart(pie, "D2")
    
    # OT Logs
    ws3 = wb.create_sheet("OT Logs - Detailed")
    ws3.sheet_view.showGridLines = False
    ws3.append(["ID", "Agent ID", "Agent Name", "Date", "Type", "Hours", "Remarks"])
    for cell in ws3[1]:
        cell.font = white_font; cell.fill = header_fill
    for log in db.execute('SELECT o.*, a.NAME FROM ot_logs o JOIN agents a ON o.agent_id=a.id ORDER BY o.ot_date DESC').fetchall():
        ws3.append([log['id'], log['agent_id'], log['NAME'], log['ot_date'], log['ot_type'], log['hours'], log['remarks']])
    
    # Loss Logs
    ws4 = wb.create_sheet("Loss Logs - Detailed")
    ws4.sheet_view.showGridLines = False
    ws4.append(["ID", "Agent ID", "Agent Name", "Date", "Type", "Hours", "Remarks"])
    for cell in ws4[1]:
        cell.font = white_font; cell.fill = header_fill
    for log in db.execute('SELECT l.*, a.NAME FROM loss_logs l JOIN agents a ON l.agent_id=a.id ORDER BY l.loss_date DESC').fetchall():
        ws4.append([log['id'], log['agent_id'], log['NAME'], log['loss_date'], log['loss_type'], log['hours'], log['remarks']])
    
    # Agents master
    ws5 = wb.create_sheet("Agents Master - 16 Fields")
    ws5.sheet_view.showGridLines = False
    ws5.append(["ID"] + COLUMNS)
    for cell in ws5[1]:
        cell.font = white_font; cell.fill = header_fill
    for a in db.execute('SELECT * FROM agents ORDER BY id').fetchall():
        ws5.append([a['id']] + [a[c] for c in COLUMNS])
    
    # Auto width
    for sheet in [ws, ws2, ws3, ws4, ws5]:
        for col in sheet.columns:
            max_length = 0
            column = col[0].column_letter
            for cell in col:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 30)
            sheet.column_dimensions[column].width = adjusted_width
    
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return send_file(output, download_name=f"TeamShineM9_Executive_Report_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx", as_attachment=True, mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

@app.route("/add", methods=["GET","POST"])
@app.route("/edit/<int:aid>", methods=["GET","POST"])
def add_edit(aid=None):
    init_db(); db=get_db()
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
    f="".join([f"<div class='col-md-6 mb-3'><label class='field-label'>{c}</label><input name='{c}' value='{(ag[c] if ag else '') or ''}' class='form-control input-dark'></div>" for c in COLUMNS])
    title="Edit Agent" if aid else "Add Agent"
    content=f"<a href='/' class='btn btn-sm btn-outline-light mb-3' style='border-radius:10px'>Back</a><div class='card p-4'><h4 class='fw-bold'>{title}</h4><form method='post' class='row'>{f}<div class='col-12 mt-3'><button class='btn btn-warning fw-bold'>Save</button></div></form></div>"
    cnt=db.execute('SELECT COUNT(*) FROM agents').fetchone()[0]
    return render_page(content, cnt)

@app.route("/delete/<int:aid>", methods=["POST"])
def delete(aid):
    init_db(); db=get_db()
    db.execute('DELETE FROM agents WHERE id=?',(aid,))
    db.execute('DELETE FROM ot_logs WHERE agent_id=?',(aid,))
    db.execute('DELETE FROM loss_logs WHERE agent_id=?',(aid,))
    db.commit()
    return redirect("/")

if __name__=="__main__":
    import os
    port=int(os.environ.get("PORT",5000))
    app.run(host="0.0.0.0",port=port)
