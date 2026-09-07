
import sqlite3
import os
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify

app = Flask(__name__)
app.secret_key = "team-shine-secret-2026"
DB_PATH = os.path.join(os.path.dirname(__file__), "Agent.db")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    # ensure table exists (use cleaned structure)
    conn = get_db()
    conn.execute("""
    CREATE TABLE IF NOT EXISTS agents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
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
    conn.commit()
    conn.close()

init_db()

@app.route("/")
def index():
    q = request.args.get("q","").strip()
    conn = get_db()
    if q:
        like = f"%{q}%"
        agents = conn.execute("""
            SELECT * FROM agents 
            WHERE NAME LIKE ? OR "TENCENT ID" LIKE ? OR "NBS ID" LIKE ? OR "PHONE NAME" LIKE ?
            ORDER BY id DESC
        """, (like,like,like,like)).fetchall()
    else:
        agents = conn.execute("SELECT * FROM agents ORDER BY id DESC").fetchall()
    conn.close()
    return render_template("index.html", agents=agents, q=q)

@app.route("/add", methods=["GET","POST"])
def add():
    if request.method == "POST":
        data = (
            request.form.get("NAME",""),
            request.form.get("TENCENT ID",""),
            request.form.get("DATE HIRED",""),
            request.form.get("PHONE NAME",""),
            request.form.get("NBS ID",""),
            request.form.get("HEADSET SN",""),
            request.form.get("IBAS",""),
            request.form.get("DJANGO",""),
            request.form.get("NT LOG IN",""),
            request.form.get("Sales Force",""),
            request.form.get("ZOHO",""),
            request.form.get("BSS WEB",""),
            request.form.get("EMAIL",""),
            request.form.get("BIRTHDAY",""),
            request.form.get("CONTACT NO.",""),
            request.form.get("ADDRESS",""),
        )
        conn = get_db()
        conn.execute("""
            INSERT INTO agents (NAME, "TENCENT ID","DATE HIRED","PHONE NAME","NBS ID","HEADSET SN",IBAS,DJANGO,"NT LOG IN","Sales Force",ZOHO,"BSS WEB",EMAIL,BIRTHDAY,"CONTACT NO.",ADDRESS)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, data)
        conn.commit()
        conn.close()
        flash("Agent added successfully!", "success")
        return redirect(url_for("index"))
    return render_template("form.html", agent=None, title="Add Agent")

@app.route("/edit/<int:agent_id>", methods=["GET","POST"])
def edit(agent_id):
    conn = get_db()
    agent = conn.execute("SELECT * FROM agents WHERE id=?", (agent_id,)).fetchone()
    if not agent:
        conn.close()
        flash("Agent not found", "danger")
        return redirect(url_for("index"))
    if request.method == "POST":
        data = (
            request.form.get("NAME",""),
            request.form.get("TENCENT ID",""),
            request.form.get("DATE HIRED",""),
            request.form.get("PHONE NAME",""),
            request.form.get("NBS ID",""),
            request.form.get("HEADSET SN",""),
            request.form.get("IBAS",""),
            request.form.get("DJANGO",""),
            request.form.get("NT LOG IN",""),
            request.form.get("Sales Force",""),
            request.form.get("ZOHO",""),
            request.form.get("BSS WEB",""),
            request.form.get("EMAIL",""),
            request.form.get("BIRTHDAY",""),
            request.form.get("CONTACT NO.",""),
            request.form.get("ADDRESS",""),
            agent_id
        )
        conn.execute("""
            UPDATE agents SET NAME=?, "TENCENT ID"=?, "DATE HIRED"=?, "PHONE NAME"=?, "NBS ID"=?, "HEADSET SN"=?, IBAS=?, DJANGO=?, "NT LOG IN"=?, "Sales Force"=?, ZOHO=?, "BSS WEB"=?, EMAIL=?, BIRTHDAY=?, "CONTACT NO."=?, ADDRESS=? WHERE id=?
        """, data)
        conn.commit()
        conn.close()
        flash("Agent updated!", "success")
        return redirect(url_for("index"))
    conn.close()
    return render_template("form.html", agent=agent, title="Edit Agent")

@app.route("/delete/<int:agent_id>", methods=["POST"])
def delete(agent_id):
    conn = get_db()
    conn.execute("DELETE FROM agents WHERE id=?", (agent_id,))
    conn.commit()
    conn.close()
    flash("Agent deleted", "warning")
    return redirect(url_for("index"))

@app.route("/api/agents")
def api_agents():
    conn = get_db()
    agents = conn.execute("SELECT * FROM agents").fetchall()
    conn.close()
    return jsonify([dict(a) for a in agents])

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
