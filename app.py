
import os, json, re
from flask import Flask, request, redirect

app = Flask(__name__)

def pretty(k):
    return k.replace("_"," ").title()

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
    from firebase_admin import db
    db_root = db.reference("team_shine_m9")
except Exception as e:
    db_root = None
    init_err = str(e)

BASE = """<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1">
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
<link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.0/font/bootstrap-icons.css" rel="stylesheet">
<style>
body{background:#080c14;color:#e2e8f0}
.card{background:#111827!important;border:1px solid #1f2937!important;border-radius:16px!important}
.table thead th{background:#0f172a!important;color:#fbbf24!important;font-size:11px}
.table tbody td{background:#111827!important;border-color:#1f2937!important;color:#cbd5e1!important}
.kpi{padding:14px;border-radius:12px;background:#0f172a;border-left:4px solid #fbbf24}
</style></head><body>
<nav class="navbar navbar-dark bg-dark p-3"><div class="container-fluid">
<a class="navbar-brand fw-bold" href="/"><i class="bi bi-lightning-charge-fill text-warning"></i> TEAM SHINE M9 <span class="badge bg-success" style="font-size:9px">REALTIME ⚡</span></a>
<div><a href="/" class="btn btn-sm btn-outline-light">Agents</a> <a href="/dashboard" class="btn btn-sm btn-warning ms-1">Dashboard</a> <a href="/add" class="btn btn-sm btn-light ms-1">+ Add</a></div>
</div></nav><div class="container-fluid p-3">__CONTENT__</div></body></html>"""

def page(c): return BASE.replace("__CONTENT__", c)

@app.route("/ping")
def ping(): return "alive"

@app.route("/debug")
def debug():
    try:
        raw = db_root.child("agents").get() or {}
        return f"Raw count: {len(raw)}<br>Keys: {list(raw.keys())[:5]}<br>First: {str(list(raw.values())[0])[:500]}"
    except Exception as e:
        import traceback
        return f"<pre>{e}\n{traceback.format_exc()}</pre>"

@app.route("/")
def home():
    try:
        raw = db_root.child("agents").get() or {}
        agents=[]
        for aid, val in raw.items():
            if isinstance(val, dict):
                val["id"]=aid
                agents.append(val)
        # no sort to avoid bug
        rows=""
        for a in agents:
            name = a.get("NAME") or a.get("Name") or "No Name"
            tid = a.get("TENCENT_ID") or a.get("TENCENT") or ""
            email = a.get("EMAIL") or ""
            rows+=f"<tr><td>{a.get('id')}</td><td><a href='/view/{a.get('id')}' style='color:white'><b>{name}</b><br><small style='color:#94a3b8'>{tid}</small></a></td><td>{email}</td><td><a href='/view/{a.get('id')}' class='btn btn-sm btn-warning'>View</a></td></tr>"
        return page(f"<h5>All Agents ({len(agents)}) - REALTIME 1 Call ⚡</h5><div class='card'><div class='table-responsive'><table class='table'><thead><tr><th>ID</th><th>NAME</th><th>EMAIL</th><th></th></tr></thead><tbody>{rows}</tbody></table></div></div><p class='mt-2'><a href='/debug' class='btn btn-sm btn-outline-light'>Debug raw data</a></p>")
    except Exception as e:
        import traceback
        return page(f"<pre>{e}\n{traceback.format_exc()}</pre>")

@app.route("/dashboard")
def dash():
    raw = db_root.child("agents").get() or {}
    total = len(raw)
    return page(f"""
    <div class="row g-3">
    <div class="col-6 col-md-3"><div class="kpi"><small>TOTAL AGENTS</small><h3>{total}</h3><small>Realtime Mode</small></div></div>
    <div class="col-6 col-md-3"><div class="kpi" style="border-color:#22c55e"><small>DB LOCATION</small><h3>SG</h3><small>Asia-Southeast1</small></div></div>
    <div class="col-6 col-md-3"><div class="kpi" style="border-color:#3b82f6"><small>SPEED</small><h3>FAST</h3><small>1 Call</small></div></div>
    <div class="col-6 col-md-3"><div class="kpi" style="border-color:#a855f7"><small>STATUS</small><h3>LIVE</h3><small>{total} agents</small></div></div>
    </div>
    """)

@app.route("/view/<aid>")
def view(aid):
    data = db_root.child(f"agents/{aid}").get() or {}
    fields=""
    for k,v in data.items():
        if k in ("id",): continue
        if k.startswith("_"): continue
        fields+=f"<div class='col-6 mb-2'><small style='color:#94a3b8'>{pretty(k)}</small><br><b>{v}</b></div>"
    return page(f"<a href='/' class='btn btn-sm btn-light mb-2'>Back</a><div class='card p-3'><h5>{data.get('NAME','No Name')} <small>{aid}</small></h5><div class='row mt-2'>{fields}</div><hr><a href='/edit/{aid}' class='btn btn-warning btn-sm'>Edit</a> <a href='/delete/{aid}' class='btn btn-outline-danger btn-sm ms-2' onclick='return confirm("Delete?")'>Delete</a></div>")

@app.route("/add", methods=["GET","POST"])
def add():
    fields = ["NAME","TENCENT_ID","DATE_HIRED","PHONE_NAME","NBS_ID","HEADSET_SN","IBAS","DJANGO","NT_LOG_IN","Sales_Force","ZOHO","BSS_WEB","EMAIL","BIRTHDAY","CONTACT_NO_","ADDRESS"]
    if request.method=="POST":
        clean={f: request.form.get(f,"") for f in fields}
        ref=db_root.child("agents").push(clean)
        return redirect(f"/view/{ref.key}")
    form="".join([f'<div class="col-6"><label class="small">{pretty(f)}</label><input name="{f}" class="form-control form-control-sm mb-2 bg-dark text-light"></div>' for f in fields])
    return page(f"<div class='card p-3'><h5>Add Agent</h5><form method='POST' class='row'>{form}<div class='col-12 mt-2'><button class='btn btn-warning w-100'>Save to Realtime</button></div></form></div>")

@app.route("/edit/<aid>", methods=["GET","POST"])
def edit(aid):
    data=db_root.child(f"agents/{aid}").get() or {}
    fields = ["NAME","TENCENT_ID","DATE_HIRED","PHONE_NAME","NBS_ID","HEADSET_SN","IBAS","DJANGO","NT_LOG_IN","Sales_Force","ZOHO","BSS_WEB","EMAIL","BIRTHDAY","CONTACT_NO_","ADDRESS"]
    if request.method=="POST":
        clean={f: request.form.get(f,"") for f in fields}
        db_root.child(f"agents/{aid}").update(clean)
        return redirect(f"/view/{aid}")
    form="".join([f'<div class="col-6"><label class="small">{pretty(f)}</label><input name="{f}" value="{data.get(f,"")}" class="form-control form-control-sm mb-2 bg-dark text-light"></div>' for f in fields])
    return page(f"<div class='card p-3'><h5>Edit {data.get('NAME','')}</h5><form method='POST' class='row'>{form}<div class='col-12 mt-2'><button class='btn btn-warning w-100'>Update</button></div></form></div>")

@app.route("/delete/<aid>")
def delete(aid):
    db_root.child(f"agents/{aid}").delete()
    return redirect("/")

if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",5000)))
