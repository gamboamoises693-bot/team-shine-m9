
import sqlite3
import os
from flask import Flask, request, redirect, url_for, g

app = Flask(__name__)
DATABASE = "/tmp/Agent.db"

COLUMNS = [
    "NAME", "TENCENT ID", "PHONE NAME", "NBS ID",
    "HEADSET SN", "IBAS", "DJANGO", "NT LOG IN",
    "Sales Force", "ZOHO", "BSS WEB", "DATE HIRED",
    "EMAIL", "BIRTHDAY", "ADDRESS", "CONTACT NO."
]

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
    db.commit()
    # add missing cols if any
    cur = db.execute('PRAGMA table_info(agents)')
    existing = [r[1] for r in cur.fetchall()]
    for c in COLUMNS:
        if c not in existing:
            try:
                db.execute(f'ALTER TABLE agents ADD COLUMN "{c}" TEXT')
            except: pass
    db.commit()

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

BASE_HTML = """
<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1">
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
<title>TEAM SHINE M9</title>
<style>body{background:#f4f6f9}.navbar{background:#0d1b3e!important}</style>
</head><body>
<nav class="navbar navbar-dark p-3"><div class="container"><a class="navbar-brand fw-bold" href="/">✨ TEAM SHINE M9 - Agent System</a>
<a href="/add" class="btn btn-warning btn-sm fw-bold">+ Add Agent</a></div></nav>
<div class="container mt-4">{CONTENT}</div></body></html>
"""

def render_page(content):
    return BASE_HTML.replace("{CONTENT}", content)

@app.route("/", methods=["GET"])
def index():
    init_db()
    q = request.args.get("q", "").strip()
    db = get_db()
    if q:
        like = f"%{q}%"
        where = " OR ".join([f'"{c}" LIKE ?' for c in COLUMNS])
        params = [like]*len(COLUMNS)
        cur = db.execute(f'SELECT * FROM agents WHERE {where} ORDER BY id DESC', params)
    else:
        cur = db.execute('SELECT * FROM agents ORDER BY id DESC')
    agents = cur.fetchall()
    
    rows = ""
    for a in agents:
        rows += f"""
        <tr>
            <td><span class="badge bg-dark">{a['id']}</span></td>
            <td><b>{a['NAME'] or ''}</b><br><small class="text-muted">{a['NBS ID'] or ''}</small></td>
            <td>{a['TENCENT ID'] or ''}</td>
            <td>{a['PHONE NAME'] or ''}</td>
            <td>{a['HEADSET SN'] or ''}</td>
            <td>{a['DATE HIRED'] or ''}</td>
            <td>{a['CONTACT NO.'] or ''}</td>
            <td>
                <a href="/edit/{a['id']}" class="btn btn-sm btn-primary">Edit</a>
                <form method="post" action="/delete/{a['id']}" style="display:inline" onsubmit="return confirm('Delete?')">
                    <button class="btn btn-sm btn-danger">Del</button>
                </form>
            </td>
        </tr>"""
    
    if not rows:
        rows = '<tr><td colspan="8" class="text-center p-4 text-muted">No agents yet. Click + Add Agent</td></tr>'

    content = f"""
    <div class="card p-3 mb-3 shadow-sm">
        <form class="row g-2" method="get">
            <div class="col-9"><input name="q" value="{q}" class="form-control" placeholder="Search Name, Tencent ID, Phone..."></div>
            <div class="col-3 d-grid"><button class="btn btn-dark">Search</button></div>
        </form>
    </div>
    <div class="card p-0 overflow-hidden shadow-sm">
        <div class="table-responsive">
            <table class="table table-hover mb-0">
                <thead class="table-light"><tr><th>ID</th><th>Name</th><th>Tencent</th><th>Phone</th><th>Headset</th><th>Hired</th><th>Contact</th><th>Action</th></tr></thead>
                <tbody>{rows}</tbody>
            </table>
        </div>
    </div>
    """
    return render_page(content)

@app.route("/add", methods=["GET", "POST"])
@app.route("/edit/<int:agent_id>", methods=["GET", "POST"])
def add_edit(agent_id=None):
    init_db()
    db = get_db()
    agent = None
    if agent_id:
        cur = db.execute('SELECT * FROM agents WHERE id=?', (agent_id,))
        agent = cur.fetchone()

    if request.method == "POST":
        values = [request.form.get(c, "") for c in COLUMNS]
        if agent_id:
            set_clause = ", ".join([f'"{c}"=?' for c in COLUMNS])
            db.execute(f'UPDATE agents SET {set_clause} WHERE id=?', values + [agent_id])
        else:
            placeholders = ", ".join(["?"]*len(COLUMNS))
            cols = ", ".join([f'"{c}"' for c in COLUMNS])
            db.execute(f'INSERT INTO agents ({cols}) VALUES ({placeholders})', values)
        db.commit()
        return redirect(url_for("index"))

    # form html
    fields = ""
    for c in COLUMNS:
        val = agent[c] if agent else ""
        fields += f'<div class="col-md-6 mb-3"><label class="form-label fw-bold small">{c}</label><input name="{c}" value="{val}" class="form-control"></div>'

    title = "Edit Agent" if agent_id else "Add New Agent"
    content = f"""
    <div class="card p-4 shadow-sm"><h4 class="fw-bold mb-3">{title}</h4>
    <form method="post" class="row">{fields}
    <div class="col-12 mt-3 d-flex gap-2">
        <a href="/" class="btn btn-secondary">Cancel</a>
        <button class="btn btn-primary px-4">Save Agent</button>
    </div></form></div>
    """
    return render_page(content)

@app.route("/delete/<int:agent_id>", methods=["POST"])
def delete(agent_id):
    init_db()
    db = get_db()
    db.execute('DELETE FROM agents WHERE id=?', (agent_id,))
    db.commit()
    return redirect(url_for("index"))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
