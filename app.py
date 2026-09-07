import sqlite3
import os
from flask import Flask, render_template, request, redirect, url_for, g

app = Flask(__name__)
DATABASE = "Agent.db"

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
    try:
        db.execute(f'CREATE TABLE IF NOT EXISTS agents (id INTEGER PRIMARY KEY AUTOINCREMENT, {cols_def})')
        db.commit()
        # check if old table has missing cols, add them
        cur = db.execute('PRAGMA table_info(agents)')
        existing = [r[1] for r in cur.fetchall()]
        for c in COLUMNS:
            if c not in existing:
                db.execute(f'ALTER TABLE agents ADD COLUMN "{c}" TEXT')
        db.commit()
    except Exception as e:
        # if totally broken, recreate
        db.execute('DROP TABLE IF EXISTS agents')
        db.execute(f'CREATE TABLE agents (id INTEGER PRIMARY KEY AUTOINCREMENT, {cols_def})')
        db.commit()

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

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
    return render_template("index.html", agents=agents, q=q)

@app.route("/add", methods=["GET", "POST"])
def add():
    init_db()
    if request.method == "POST":
        db = get_db()
        values = [request.form.get(c, "") for c in COLUMNS]
        placeholders = ", ".join(["?"]*len(COLUMNS))
        cols = ", ".join([f'"{c}"' for c in COLUMNS])
        db.execute(f'INSERT INTO agents ({cols}) VALUES ({placeholders})', values)
        db.commit()
        return redirect(url_for("index"))
    return render_template("form.html", title="Add Agent", agent=None)

@app.route("/edit/<int:agent_id>", methods=["GET", "POST"])
def edit(agent_id):
    init_db()
    db = get_db()
    if request.method == "POST":
        values = [request.form.get(c, "") for c in COLUMNS]
        set_clause = ", ".join([f'"{c}"=?' for c in COLUMNS])
        db.execute(f'UPDATE agents SET {set_clause} WHERE id=?', values + [agent_id])
        db.commit()
        return redirect(url_for("index"))
    cur = db.execute('SELECT * FROM agents WHERE id=?', (agent_id,))
    agent = cur.fetchone()
    return render_template("form.html", title="Edit Agent", agent=agent)

@app.route("/delete/<int:agent_id>", methods=["POST"])
def delete(agent_id):
    init_db()
    db = get_db()
    db.execute('DELETE FROM agents WHERE id=?', (agent_id,))
    db.commit()
    return redirect(url_for("index"))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
