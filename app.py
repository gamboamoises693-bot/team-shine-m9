
import os, json
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
    from firebase_admin import db as db_mod
    db_root = db_mod.reference("team_shine_m9")
except Exception as e:
    db_root = None
    init_err = str(e)

BASE_START = """<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1">
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
<style>
body{background:#080c14;color:#e2e8f0}
.card{background:#111827!important;border:1px solid #1f2937!important;border-radius:16px!important}
.table thead th{background:#0f172a!important;color:#fbbf24!important}
.table tbody td{background:#111827!important;border-color:#1f2937!important;color:#cbd5e1!important}
.kpi{padding:14px;border-radius:12px;background:#0f172a;border-left:4px solid #fbbf24}
</style></head><body>
<nav class="navbar navbar-dark bg-dark p-3"><div class="container-fluid">
<a class="navbar-brand fw-bold" href="/">TEAM SHINE M9 REALTIME</a>
<div><a href="/" class="btn btn-sm btn-outline-light">Agents</a> <a href="/dashboard" class="btn btn-sm btn-warning ms-1">Dashboard</a> <a href="/add" class="btn btn-sm btn-light ms-1">+ Add</a></div>
</div></nav><div class="container-fluid p-3">"""

BASE_END = "</div></body></html>"

def page(c):
    return BASE_START + c + BASE_END

@app.route("/ping")
def ping():
    return "alive"

@app.route("/debug")
def debug():
    try:
        raw = db_root.child("agents").get() or {}
        first = list(raw.values())[0] if raw else {}
        return f"Count {len(raw)}<br>First {first}"
    except Exception as e:
        return str(e)

@app.route("/")
def home():
    raw = db_root.child("agents").get() or {}
    rows = ""
    for aid, val in raw.items():
        if not isinstance(val, dict):
            continue
        name = val.get("NAME","No Name")
        tid = val.get("TENCENT_ID","")
        email = val.get("EMAIL","")
        rows += "<tr><td>" + str(aid) + "</td><td><a href='/view/" + str(aid) + "' style='color:white'><b>" + str(name) + "</b><br><small>" + str(tid) + "</small></a></td><td>" + str(email) + "</td><td><a href='/view/" + str(aid) + "' class='btn btn-sm btn-warning'>View</a></td></tr>"
    content = "<h5>All Agents (" + str(len(raw)) + ") - REALTIME 1 Call</h5><div class='card'><div class='table-responsive'><table class='table'><thead><tr><th>ID</th><th>NAME</th><th>EMAIL</th><th></th></tr></thead><tbody>" + rows + "</tbody></table></div></div>"
    return page(content)

@app.route("/dashboard")
def dash():
    raw = db_root.child("agents").get() or {}
    total = len(raw)
    content = "<div class='row g-3'><div class='col-6'><div class='kpi'><small>TOTAL</small><h3>" + str(total) + "</h3></div></div><div class='col-6'><div class='kpi' style='border-color:#22c55e'><small>DB</small><h3>SG FAST</h3></div></div></div>"
    return page(content)

@app.route("/view/<aid>")
def view(aid):
    data = db_root.child("agents/" + aid).get() or {}
    fields = ""
    for k,v in data.items():
        if k.startswith("_"):
            continue
        fields += "<div class='col-6 mb-2'><small>" + pretty(k) + "</small><br><b>" + str(v) + "</b></div>"
    content = "<a href='/' class='btn btn-sm btn-light mb-2'>Back</a><div class='card p-3'><h5>" + str(data.get("NAME","")) + "</h5><div class='row'>" + fields + "</div><hr><a href='/edit/" + aid + "' class='btn btn-warning btn-sm'>Edit</a> <a href='/delete/" + aid + "' class='btn btn-outline-danger btn-sm ms-2'>Delete</a></div>"
    return page(content)

@app.route("/add", methods=["GET","POST"])
def add():
    fields = ["NAME","TENCENT_ID","DATE_HIRED","PHONE_NAME","NBS_ID","HEADSET_SN","IBAS","DJANGO","NT_LOG_IN","Sales_Force","ZOHO","BSS_WEB","EMAIL","BIRTHDAY","CONTACT_NO_","ADDRESS"]
    if request.method=="POST":
        clean = {}
        for f in fields:
            clean[f] = request.form.get(f,"")
        ref = db_root.child("agents").push(clean)
        return redirect("/view/" + ref.key)
    form = ""
    for f in fields:
        form += "<div class='col-6'><label class='small'>" + pretty(f) + "</label><input name='" + f + "' class='form-control form-control-sm mb-2 bg-dark text-light'></div>"
    content = "<div class='card p-3'><h5>Add Agent</h5><form method='POST' class='row'>" + form + "<div class='col-12 mt-2'><button class='btn btn-warning w-100'>Save</button></div></form></div>"
    return page(content)

@app.route("/edit/<aid>", methods=["GET","POST"])
def edit(aid):
    data = db_root.child("agents/" + aid).get() or {}
    fields = ["NAME","TENCENT_ID","DATE_HIRED","PHONE_NAME","NBS_ID","HEADSET_SN","IBAS","DJANGO","NT_LOG_IN","Sales_Force","ZOHO","BSS_WEB","EMAIL","BIRTHDAY","CONTACT_NO_","ADDRESS"]
    if request.method=="POST":
        clean = {}
        for f in fields:
            clean[f] = request.form.get(f,"")
        db_root.child("agents/" + aid).update(clean)
        return redirect("/view/" + aid)
    form = ""
    for f in fields:
        val = data.get(f,"")
        form += "<div class='col-6'><label class='small'>" + pretty(f) + "</label><input name='" + f + "' value='" + str(val).replace("'","") + "' class='form-control form-control-sm mb-2 bg-dark text-light'></div>"
    content = "<div class='card p-3'><h5>Edit " + str(data.get("NAME","")) + "</h5><form method='POST' class='row'>" + form + "<div class='col-12 mt-2'><button class='btn btn-warning w-100'>Update</button></div></form></div>"
    return page(content)

@app.route("/delete/<aid>")
def delete(aid):
    db_root.child("agents/" + aid).delete()
    return redirect("/")

if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",5000)))
