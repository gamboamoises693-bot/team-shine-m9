
import sqlite3, os
from flask import Flask, request, redirect, g

app = Flask(__name__)
DATABASE = "Agent.db"  # DITO mismo sa repo, hindi /tmp, kaya auto persistent hanggat di ka nagre-redeploy
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
    # Create table if not exists - pero hindi buburahin laman
    db.execute(f'CREATE TABLE IF NOT EXISTS agents (id INTEGER PRIMARY KEY AUTOINCREMENT, {cols_def})')
    db.commit()
    # Check if old schema from previous version exists and migrate
    try:
        cur = db.execute('PRAGMA table_info(agents)')
        existing = [r[1] for r in cur.fetchall()]
        for c in COLUMNS:
            if c not in existing:
                db.execute(f'ALTER TABLE agents ADD COLUMN "{c}" TEXT')
        db.commit()
    except: pass

@app.teardown_appcontext
def close_connection(ex):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

BASE = """
<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1">
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
<link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.0/font/bootstrap-icons.css" rel="stylesheet">
<title>TEAM SHINE M9 - Executive</title>
<style>
body{background:#0f172a;color:#e2e8f0} .navbar{background:linear-gradient(90deg,#0f172a,#1e293b)!important;border-bottom:1px solid #334155}}
.card{background:#1e293b;border:1px solid #334155;border-radius:16px} .table{color:#e2e8f0}
.table thead th{background:#0f172a;color:#94a3b8;border-bottom:2px solid #334155;font-size:11px;text-transform:uppercase;letter-spacing:.8px;white-space:nowrap;position:sticky;top:0;z-index:10}
.table tbody td{border-color:#1e293b;vertical-align:middle;font-size:13px;white-space:nowrap}
.table-hover tbody tr:hover{background:#1e293b!important;transform:scale(1.01);transition:.2s} .badge-id{background:#0f172a;border:1px solid #334155;color:#94a3b8}
.btn-exec{background:#fbbf24;color:#0f172a;font-weight:700;border:none} .search-box{background:#0f172a;border:1px solid #334155;color:white}
.detail-card{background:#0f172a;border:1px solid #334155;transition:.2s} .detail-card:hover{border-color:#fbbf24} .field-label{color:#64748b;font-size:10px;text-transform:uppercase;letter-spacing:.8px} .field-value{color:#f1f5f9;font-weight:500;font-size:14px}
.scroll-hint{color:#475569;font-size:11px;text-align:center;padding:8px}
</style></head><body>
<nav class="navbar navbar-dark p-3 sticky-top"><div class="container-fluid d-flex justify-content-between">
<div class="d-flex align-items-center gap-3"><i class="bi bi-stars fs-4 text-warning"></i><div><div class="fw-bold fs-5">TEAM SHINE M9</div><div style="font-size:11px;color:#94a3b8;letter-spacing:2px">EXECUTIVE • DYNAMIC DB</div></div><span class="badge bg-warning text-dark ms-3">{{count}} AGENTS</span><span class="badge bg-success ms-1">AUTO SAVE</span></div>
<div class="d-flex gap-2"><a href="/" class="btn btn-sm btn-outline-light"><i class="bi bi-grid"></i> Dashboard</a><a href="/add" class="btn btn-sm btn-exec"><i class="bi bi-plus-lg"></i> Add Agent</a></div>
</div></nav><div class="container-fluid p-4">{{CONTENT}}</div>
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body></html>
"""

def render_page(content, count=0):
    return BASE.replace("{{CONTENT}}", content).replace("{{count}}", str(count))

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
    rows=""
    for a in agents:
        rows+=f"<tr><td><span class='badge badge-id'>{a['id']}</span></td><td><a href='/view/{a['id']}' class='text-decoration-none'><div class='fw-bold text-white'>{a['NAME'] or ''}</div><div style='font-size:11px;color:#94a3b8'>{a['NBS ID'] or ''} • {a['TENCENT ID'] or ''}</div></a></td><td><span class='badge bg-dark border'>{a['TENCENT ID'] or ''}</span></td><td>{a['PHONE NAME'] or ''}</td><td><code style='color:#fbbf24'>{a['HEADSET SN'] or ''}</code></td><td>{a['IBAS'] or ''}</td><td>{a['DJANGO'] or ''}</td><td>{a['NT LOG IN'] or ''}</td><td>{a['Sales Force'] or ''}</td><td>{a['ZOHO'] or ''}</td><td>{a['BSS WEB'] or ''}</td><td>{a['DATE HIRED'] or ''}</td><td style='max-width:180px;overflow:hidden;text-overflow:ellipsis'>{a['EMAIL'] or ''}</td><td>{a['BIRTHDAY'] or ''}</td><td style='max-width:200px;overflow:hidden;text-overflow:ellipsis'>{a['ADDRESS'] or ''}</td><td><b>{a['CONTACT NO.'] or ''}</b></td><td><a href='/view/{a['id']}' class='btn btn-sm btn-outline-light'><i class='bi bi-eye'></i></a> <a href='/edit/{a['id']}' class='btn btn-sm btn-outline-warning'><i class='bi bi-pencil'></i></a></td></tr>"
    content=f"""
    <div class="card p-3 mb-3"><form class="d-flex gap-2" method="get"><div class="input-group"><span class="input-group-text" style="background:#0f172a;border:1px solid #334155;color:#94a3b8"><i class="bi bi-search"></i></span><input name="q" value="{q}" class="form-control search-box" placeholder="Search lahat ng fields..."></div><button class="btn btn-light">Search</button></form></div>
    <div class="card p-0 overflow-hidden"><div class="table-responsive"><table class="table table-hover mb-0"><thead><tr><th>ID</th><th>Agent (click for full details)</th><th>Tencent</th><th>Phone</th><th>Headset</th><th>IBAS</th><th>Django</th><th>NT Login</th><th>SalesForce</th><th>ZOHO</th><th>BSS</th><th>Hired</th><th>Email</th><th>Bday</th><th>Address</th><th>Contact</th><th>Action</th></tr></thead><tbody>{rows if rows else '<tr><td colspan=17 class=text-center p-5>Walang laman pa - Add Agent ka boss</td></tr>'}</tbody></table></div></div>
    <div class="scroll-hint">← Scroll sideways para makita lahat ng 16 fields • Click name para full executive view • Auto-save pag nag-add ka →</div>
    <div class="card mt-3 p-3" style="background:#0f172a;border:1px dashed #fbbf24"><small style="color:#fbbf24"><i class="bi bi-info-circle"></i> <b>DYNAMIC DB TIP:</b> Pag nag-add ka ng bagong agent, auto save sa Agent.db. Para hindi mawala pag nag-redeploy, i-download mo yung Agent.db sa Render Shell at i-upload mo ulit sa GitHub. Pero sa ngayon, habang hindi ka nagde-deploy, safe lahat!</small></div>
    """
    return render_page(content, len(agents))

@app.route("/view/<int:aid>")
def view(aid):
    init_db()
    db=get_db()
    a=db.execute('SELECT * FROM agents WHERE id=?',(aid,)).fetchone()
    if not a: return redirect("/")
    fields=""
    for c in COLUMNS:
        fields+=f"<div class='col-md-6 mb-3'><div class='detail-card p-3 rounded-3 h-100'><div class='field-label mb-1'>{c}</div><div class='field-value'>{a[c] or '<span style=color:#334155>— empty —</span>'}</div></div></div>"
    content=f"<a href='/' class='btn btn-sm btn-outline-light mb-3'><i class='bi bi-arrow-left'></i> Back</a><div class='row'><div class='col-md-4'><div class='card p-4 text-center'><div style='width:80px;height:80px;background:linear-gradient(135deg,#fbbf24,#f59e0b);border-radius:20px;display:flex;align-items:center;justify-content:center;margin:0 auto 16px;font-size:32px;font-weight:800;color:#0f172a'>{(a['NAME'] or 'A')[0]}</div><div class='fw-bold fs-4 text-white'>{a['NAME'] or ''}</div><div class='field-label'>{a['NBS ID'] or ''} • {a['TENCENT ID'] or ''}</div><hr style='border-color:#334155'><div class='d-grid gap-2 mt-4'><a href='/edit/{a['id']}' class='btn btn-warning fw-bold'>Edit Agent</a><form method='post' action='/delete/{a['id']}' onsubmit=\"return confirm('Delete?')\"><button class='btn btn-outline-danger w-100'>Delete</button></form></div></div></div><div class='col-md-8'><div class='card p-4'><h5 class='fw-bold text-white mb-3'><i class='bi bi-person-badge me-2 text-warning'></i>Full Details - Lahat ng 16 Fields</h5><div class='row'>{fields}</div></div></div></div>"
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
        f+=f"<div class='col-md-6 mb-3'><label class='field-label mb-1'>{c}</label><input name='{c}' value='{v}' class='form-control' style='background:#0f172a;border:1px solid #334155;color:white'></div>"
    title="Edit Agent" if aid else "Add New Agent"
    content=f"<a href='/' class='btn btn-sm btn-outline-light mb-3'>Back</a><div class='card p-4'><h4 class='fw-bold text-white mb-4'>{title}</h4><form method='post' class='row'>{f}<div class='col-12 mt-3'><button class='btn btn-warning fw-bold px-5'><i class='bi bi-save'></i> Save Agent</button></div></form></div>"
    cnt=db.execute('SELECT COUNT(*) FROM agents').fetchone()[0]
    return render_page(content, cnt)

@app.route("/delete/<int:aid>", methods=["POST"])
def delete(aid):
    init_db()
    db=get_db()
    db.execute('DELETE FROM agents WHERE id=?',(aid,))
    db.commit()
    return redirect("/")

if __name__=="__main__":
    port=int(os.environ.get("PORT",5000))
    app.run(host="0.0.0.0",port=port)
