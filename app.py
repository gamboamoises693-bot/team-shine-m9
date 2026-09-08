

import os, json
from flask import Flask, request, redirect

app = Flask(__name__)

try:
    import firebase_admin
    from firebase_admin import credentials, db
    if not firebase_admin._apps:
        url = os.environ.get("FIREBASE_DATABASE_URL")
        if os.path.exists("serviceAccountKey.json"):
            cred = credentials.Certificate("serviceAccountKey.json")
        else:
            cdict = json.loads(os.environ.get("FIREBASE_CREDENTIALS","{}"))
            cred = credentials.Certificate(cdict)
        firebase_admin.initialize_app(cred, {"databaseURL": url})
    from firebase_admin import db as db_mod
    db_root = db_mod.reference("team_shine_m9")
except Exception as e:
    db_root = None

def get_all_agents():
    raw = db_root.child("agents").get()
    agents = []
    if raw is None:
        return []
    if isinstance(raw, list):
        # Realtime sometimes returns list
        for idx, val in enumerate(raw):
            if isinstance(val, dict) and val:
                val["id"] = val.get("id") or str(idx)
                agents.append(val)
    elif isinstance(raw, dict):
        for aid, val in raw.items():
            if isinstance(val, dict):
                val["id"] = aid
                agents.append(val)
    return agents

@app.route("/")
def home():
    try:
        agents = get_all_agents()
        rows = ""
        for a in agents:
            name = a.get("NAME","No Name")
            tid = a.get("TENCENT_ID","")
            rows += f"<tr><td>{a.get('id')}</td><td><b>{name}</b><br><small>{tid}</small></td><td><a href='/view/{a.get('id')}' class='btn btn-sm btn-warning'>View</a></td></tr>"
        return f"""
        <html><head><meta name="viewport" content="width=device-width,initial-scale=1">
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <style>body{{background:#080c14;color:#e2e8f0}} .card{{background:#111827!important;border:1px solid #1f2937!important}}</style>
        </head><body>
        <nav class="navbar navbar-dark bg-dark p-3"><a class="navbar-brand" href="/">TEAM SHINE M9 - {len(agents)} Agents REALTIME</a></nav>
        <div class="container p-3">
        <h5>All Agents ({len(agents)}) - Fixed List Bug</h5>
        <div class="card"><div class="table-responsive"><table class="table table-dark"><thead><tr><th>ID</th><th>NAME</th><th></th></tr></thead><tbody>{rows}</tbody></table></div></div>
        <a href="/debug" class="btn btn-outline-light btn-sm mt-2">Debug</a>
        </div></body></html>
        """
    except Exception as e:
        import traceback
        return f"<pre>Error: {e}\n{traceback.format_exc()}</pre>"

@app.route("/debug")
def debug():
    raw = db_root.child("agents").get()
    t = type(raw).__name__
    count = len(raw) if raw else 0
    sample = str(raw)[:1000]
    return f"Type: {t}<br>Count: {count}<br>Sample: {sample}<br><br><a href='/'>Home</a>"

@app.route("/view/<aid>")
def view(aid):
    # Try to find by id - need to handle list storage
    agents = get_all_agents()
    data = None
    for a in agents:
        if str(a.get("id")) == str(aid):
            data = a
            break
    if not data:
        # try direct
        data = db_root.child(f"agents/{aid}").get() or {}
    return f"<h2>{data.get('NAME','')}</h2><pre>{data}</pre><a href='/'>Home</a> | <a href='/delete/{aid}'>Delete</a>"

@app.route("/delete/<aid>")
def delete(aid):
    try:
        db_root.child(f"agents/{aid}").delete()
    except:
        # if list, set to None
        raw = db_root.child("agents").get()
        if isinstance(raw, list):
            try:
                idx = int(aid)
                db_root.child(f"agents/{idx}").delete()
            except:
                pass
    return redirect("/")

@app.route("/add", methods=["GET","POST"])
def add():
    if request.method=="POST":
        data = {"NAME": request.form.get("NAME",""), "TENCENT_ID": request.form.get("TENCENT_ID",""), "EMAIL": request.form.get("EMAIL","")}
        # Always use push with generated key to avoid list bug - use child with custom id
        new_id = str(len(get_all_agents())+1)
        db_root.child(f"agents/{new_id}").set(data)
        return redirect("/")
    return '<form method="POST"><input name="NAME" placeholder="Name"><input name="TENCENT_ID" placeholder="Tencent"><button>Save</button></form>'

@app.route("/ping")
def ping():
    return "alive"

if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",5000)))
