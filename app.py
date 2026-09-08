
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

def pretty(k):
    return k.replace("_"," ").title()

def get_all():
    raw = db_root.child("agents").get()
    agents=[]
    if raw is None:
        return []
    if isinstance(raw, list):
        for idx, val in enumerate(raw):
            if isinstance(val, dict) and val:
                val["id"]=str(val.get("id") or idx)
                agents.append(val)
    elif isinstance(raw, dict):
        for aid, val in raw.items():
            if isinstance(val, dict):
                val["id"]=str(aid)
                agents.append(val)
    return agents

BASE = '''<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1">
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
<link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.0/font/bootstrap-icons.css" rel="stylesheet">
<title>TEAM SHINE M9</title>
<style>
body{background:#080c14;color:#e2e8f0}
.card{background:#111827!important;border:1px solid #1f2937!important;border-radius:16px!important}
.kpi{padding:16px;border-radius:14px;background:#0f172a;border-left:4px solid #fbbf24}
.badge-id{background:#0f172a;border:1px solid #334155;color:#94a3b8;border-radius:8px;padding:4px 8px;font-size:11px}
.table thead th{background:#0f172a!important;color:#fbbf24!important;font-size:11px;text-transform:uppercase}
.table tbody td{background:#111827!important;border-color:#1f2937!important;color:#cbd5e1!important}
</style></head><body>
<nav class="navbar navbar-dark bg-dark p-3"><div class="container-fluid">
<a class="navbar-brand fw-bold" href="/"><i class="bi bi-lightning-charge-fill text-warning"></i> TEAM SHINE M9 <span class="badge bg-success ms-2" style="font-size:10px">REALTIME 19 FAST</span></a>
<div><a href="/" class="btn btn-sm btn-outline-light">Agents</a> <a href="/dashboard" class="btn btn-sm btn-warning ms-1">Dashboard</a> <a href="/add" class="btn btn-sm btn-light ms-1">+ Add</a></div>
</div></nav><div class="container-fluid p-3">__CONTENT__</div></body></html>'''

def page(c):
    return BASE.replace("__CONTENT__", c)

@app.route("/ping")
def ping(): return "alive"

@app.route("/")
def home():
    agents = get_all()
    q = request.args.get("q","").lower()
    if q:
        agents = [a for a in agents if q in str(a.get("NAME","")).lower()]
    rows=""
    for a in agents:
        name = a.get("NAME","No Name")
        tid = a.get("TENCENT_ID","")
        rows += "<tr><td><span class='badge-id'>"+str(a.get("id"))+"</span></td><td><a href='/view/"+str(a.get("id"))+"' style='color:white;text-decoration:none'><b>"+str(name)+"</b><br><small style='color:#94a3b8'>"+str(tid)+"</small></a></td><td><a href='/view/"+str(a.get("id"))+"' class='btn btn-sm btn-warning'>View</a></td></tr>"
    html = "<h5>All Agents ("+str(len(agents))+") - REALTIME FAST ⚡</h5><div class='card'><div class='table-responsive'><table class='table'><thead><tr><th>ID</th><th>AGENT</th><th></th></tr></thead><tbody>"+rows+"</tbody></table></div></div>"
    return page(html)

@app.route("/dashboard")
def dash():
    agents = get_all()
    total = len(agents)
    html = "<div class='row g-3'><div class='col-6'><div class='kpi'><small>TOTAL AGENTS</small><h2>"+str(total)+"</h2><small style='color:#22c55e'>Realtime DB Live</small></div></div><div class='col-6'><div class='kpi' style='border-color:#22c55e'><small>SPEED</small><h2>FAST</h2><small>SG Region</small></div></div></div>"
    return page(html)

@app.route("/view/<aid>")
def view(aid):
    agents = get_all()
    data = None
    for a in agents:
        if str(a.get("id"))==str(aid):
            data=a
            break
    if not data:
        data={}
    fields=""
    for k,v in data.items():
        if k=="id" or k.startswith("_"): continue
        fields += "<div class='col-6 mb-2'><small style='color:#94a3b8'>"+pretty(k)+"</small><br><b>"+str(v)+"</b></div>"
    html = "<a href='/' class='btn btn-sm btn-light mb-2'>Back</a><div class='card p-3'><h5>"+str(data.get("NAME",""))+"</h5><div class='row'>"+fields+"</div><hr><a href='/edit/"+str(aid)+"' class='btn btn-warning btn-sm'>Edit</a> <a href='/delete/"+str(aid)+"' class='btn btn-outline-danger btn-sm ms-2'>Delete</a></div>"
    return page(html)

@app.route("/add", methods=["GET","POST"])
def add():
    fields = ["NAME","TENCENT_ID","DATE_HIRED","PHONE_NAME","NBS_ID","EMAIL"]
    if request.method=="POST":
        clean={}
        for f in fields:
            clean[f]=request.form.get(f,"")
        agents=get_all()
        max_id=0
        for a in agents:
            try:
                max_id=max(max_id, int(a.get("id")))
            except:
                pass
        new_id=str(max_id+1)
        db_root.child("agents/"+new_id).set(clean)
        return redirect("/view/"+new_id)
    form=""
    for f in fields:
        form += "<div class='col-6'><label class='small'>"+pretty(f)+"</label><input name='"+f+"' class='form-control form-control-sm mb-2 bg-dark text-light'></div>"
    html = "<div class='card p-3'><h5>Add Agent</h5><form method='POST' class='row'>"+form+"<div class='col-12 mt-2'><button class='btn btn-warning w-100'>Save</button></div></form></div>"
    return page(html)

@app.route("/edit/<aid>", methods=["GET","POST"])
def edit(aid):
    data=None
    for a in get_all():
        if str(a.get("id"))==str(aid):
            data=a
            break
    if not data:
        data={}
    fields = ["NAME","TENCENT_ID","DATE_HIRED","PHONE_NAME","NBS_ID","EMAIL"]
    if request.method=="POST":
        clean={}
        for f in fields:
            clean[f]=request.form.get(f,"")
        db_root.child("agents/"+aid).update(clean)
        return redirect("/view/"+aid)
    form=""
    for f in fields:
        v=str(data.get(f,"")).replace("'","")
        form += "<div class='col-6'><label class='small'>"+pretty(f)+"</label><input name='"+f+"' value='"+v+"' class='form-control form-control-sm mb-2 bg-dark text-light'></div>"
    html = "<div class='card p-3'><h5>Edit</h5><form method='POST' class='row'>"+form+"<div class='col-12 mt-2'><button class='btn btn-warning w-100'>Update</button></div></form></div>"
    return page(html)

@app.route("/delete/<aid>")
def delete(aid):
    db_root.child("agents/"+aid).delete()
    return redirect("/")

if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",5000)))
