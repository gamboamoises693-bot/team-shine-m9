
import os, json, re, time
from flask import Flask, request, redirect, jsonify
from collections import defaultdict

app = Flask(__name__)

def sanitize(k):
    k = re.sub(r'[\.\$\#\[\]\/]', '_', k)
    k = k.strip().replace(" ", "_")
    k = re.sub(r'_+', '_', k)
    return k or "FIELD"

def pretty(k):
    return k.replace("_"," ").title()

# --- Firebase init ---
db_root = None
init_err = ""
try:
    import firebase_admin
    from firebase_admin import credentials, db
    if not firebase_admin._apps:
        url = os.environ.get("FIREBASE_DATABASE_URL")
        if not url:
            raise Exception("FIREBASE_DATABASE_URL missing")
        if os.path.exists("serviceAccountKey.json"):
            cred = credentials.Certificate("serviceAccountKey.json")
        else:
            cdict = json.loads(os.environ.get("FIREBASE_CREDENTIALS","{}"))
            cred = credentials.Certificate(cdict)
        firebase_admin.initialize_app(cred, {"databaseURL": url})
    from firebase_admin import db
    db_root = db.reference("team_shine_m9")
except Exception as e:
    init_err = str(e)

_cache = {"data": None, "t":0}
def get_agents():
    global _cache
    if _cache["data"] and time.time()-_cache["t"]<10:
        return _cache["data"]
    try:
        raw = db_root.child("agents").get() or {}
        agents=[]
        for aid, val in raw.items():
            if isinstance(val, dict):
                val["id"]=aid
                # ensure NAME field exists (handle both NAME and sanitized)
                agents.append(val)
        agents.sort(key=lambda x: (x.get("NAME") or x.get("TENCENT_ID") or "").lower())
        _cache={"data":agents,"t":time.time()}
        return agents
    except:
        return _cache["data"] or []

def clear_cache():
    global _cache
    _cache={"data":None,"t":0}

BASE_HTML = """<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1">
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
<link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.0/font/bootstrap-icons.css" rel="stylesheet">
<style>
body{background:#080c14;color:#e2e8f0;font-family:system-ui}
.card{background:#111827!important;border:1px solid #1f2937!important;border-radius:16px!important}
.kpi{padding:14px;border-radius:12px;background:#0f172a;border-left:4px solid #fbbf24}
.table thead th{background:#0f172a!important;color:#fbbf24!important;font-size:11px}
.table tbody td{background:#111827!important;border-color:#1f2937!important;color:#cbd5e1!important}
a{color:#fbbf24}
.badge-id{background:#0f172a;border:1px solid #334155;color:#94a3b8;border-radius:6px;padding:2px 6px;font-size:10px}
</style><title>TEAM SHINE M9</title></head><body>
<nav class="navbar navbar-dark bg-dark p-3 sticky-top"><div class="container-fluid">
<a class="navbar-brand fw-bold" href="/"><i class="bi bi-lightning-charge-fill text-warning"></i> TEAM SHINE M9 <span class="badge bg-success" style="font-size:9px">REALTIME ⚡ FAST</span></a>
<div><a href="/" class="btn btn-sm btn-outline-light">Agents</a> <a href="/dashboard" class="btn btn-sm btn-warning ms-1">Dashboard</a> <a href="/add" class="btn btn-sm btn-light ms-1">+ Add</a></div>
</div></nav><div class="container-fluid p-3">__CONTENT__</div></body></html>"""

def page(content):
    return BASE_HTML.replace("__CONTENT__", content)

@app.route("/ping")
def ping(): return "alive",200

@app.route("/status")
def status():
    return jsonify({"mode":"realtime","count":len(get_agents()),"error":init_err,"has_db": bool(db_root)})

@app.route("/")
def home():
    if not db_root:
        return page(f"<div class='card p-3'>Firebase error: {init_err}</div>")
    agents=get_agents()
    rows=""
    for a in agents:
        name = a.get("NAME") or "-"
        tid = a.get("TENCENT_ID") or a.get("TENCENT") or ""
        email = a.get("EMAIL") or ""
        rows+=f"<tr><td><span class='badge-id'>{a.get('id')}</span></td><td><a href='/view/{a.get('id')}' class='text-white text-decoration-none'><b>{name}</b><br><small style='color:#94a3b8'>{tid} | {email}</small></a></td><td><a href='/view/{a.get('id')}' class='btn btn-sm btn-outline-warning'>View</a></td></tr>"
    return page(f"""
    <div class="d-flex justify-content-between align-items-center mb-3">
    <h5 class="m-0">All Agents ({len(agents)}) - 1 Call Only ⚡ Super Fast</h5>
    <span class="badge bg-success">{len(agents)} Total</span>
    </div>
    <div class="card"><div class="table-responsive"><table class="table mb-0"><thead><tr><th>ID</th><th>AGENT INFO</th><th>ACTION</th></tr></thead><tbody>{rows}</tbody></table></div></div>
    <p class="mt-3 text-muted small">Realtime DB = mabilis tulad nung isa mong app. 1 Firebase call lang lahat agents na!</p>
    """)

@app.route("/dashboard")
def dashboard():
    agents=get_agents()
    total=len(agents)
    return page(f"""
    <div class="row g-3 mb-3">
    <div class="col-6 col-md-3"><div class="kpi"><small style="color:#94a3b8">TOTAL AGENTS</small><h3>{total}</h3><small class="text-success">Realtime Mode</small></div></div>
    <div class="col-6 col-md-3"><div class="kpi" style="border-color:#22c55e"><small>DB LOCATION</small><h3>SG</h3><small>Asia-Southeast1</small></div></div>
    <div class="col-6 col-md-3"><div class="kpi" style="border-color:#3b82f6"><small>SPEED</small><h3>FAST</h3><small>1 Call ⚡</small></div></div>
    <div class="col-6 col-md-3"><div class="kpi" style="border-color:#a855f7"><small>STATUS</small><h3>LIVE</h3><small>20 agents</small></div></div>
    </div>
    <div class="card p-3"><h6>Top Agents</h6>{"".join([f"<div>{a.get('NAME')} - {a.get('TENCENT_ID')}</div>" for a in agents[:5]])}
    </div>
    """)

@app.route("/view/<aid>")
def view(aid):
    data = db_root.child(f"agents/{aid}").get() or {}
    if not data:
        return "Not found",404
    fields_html=""
    for k,v in data.items():
        if k.startswith("_") or k=="id": continue
        fields_html+=f"<div class='col-6 col-md-4 mb-2'><small style='color:#94a3b8'>{pretty(k)}</small><br><b>{v}</b></div>"
    return page(f"""
    <a href="/" class="btn btn-sm btn-outline-light mb-3">← Back</a>
    <div class="card p-3">
    <h4>{data.get('NAME','Unknown')} <span class="badge-id">{aid}</span></h4>
    <div class="row g-2 mt-2">{fields_html}</div>
    <hr>
    <a href="/edit/{aid}" class="btn btn-warning btn-sm">Edit</a>
    <a href="/delete/{aid}" class="btn btn-outline-danger btn-sm ms-2" onclick="return confirm('Delete?')">Delete</a>
    </div>
    """)

@app.route("/add", methods=["GET","POST"])
def add():
    all_fields = ["NAME","TENCENT_ID","DATE_HIRED","PHONE_NAME","NBS_ID","HEADSET_SN","IBAS","DJANGO","NT_LOG_IN","Sales_Force","ZOHO","BSS_WEB","EMAIL","BIRTHDAY","CONTACT_NO_","ADDRESS"]
    if request.method=="POST":
        clean={}
        for f in all_fields:
            clean[f]=request.form.get(f,"")
        clean["_ot_total"]=0
        clean["_loss_total"]=0
        ref = db_root.child("agents").push(clean)
        clear_cache()
        return redirect(f"/view/{ref.key}")
    form=""
    for f in all_fields:
        form+=f'<div class="col-6"><label class="small">{pretty(f)}</label><input name="{f}" class="form-control form-control-sm mb-2 bg-dark text-light border-secondary"></div>'
    return page(f"<div class='card p-3'><h5>Add Agent</h5><form method='POST' class='row g-1 mt-2'>{form}<div class='col-12 mt-2'><button class='btn btn-warning w-100'>Save to Realtime ⚡</button></div></form></div>")

@app.route("/edit/<aid>", methods=["GET","POST"])
def edit(aid):
    data = db_root.child(f"agents/{aid}").get() or {}
    all_fields = ["NAME","TENCENT_ID","DATE_HIRED","PHONE_NAME","NBS_ID","HEADSET_SN","IBAS","DJANGO","NT_LOG_IN","Sales_Force","ZOHO","BSS_WEB","EMAIL","BIRTHDAY","CONTACT_NO_","ADDRESS"]
    if request.method=="POST":
        clean={}
        for f in all_fields:
            clean[f]=request.form.get(f,"")
        db_root.child(f"agents/{aid}").update(clean)
        clear_cache()
        return redirect(f"/view/{aid}")
    form=""
    for f in all_fields:
        val = data.get(f,"")
        form+=f'<div class="col-6"><label class="small">{pretty(f)}</label><input name="{f}" value="{val}" class="form-control form-control-sm mb-2 bg-dark text-light border-secondary"></div>'
    return page(f"<div class='card p-3'><h5>Edit {data.get('NAME','')}</h5><form method='POST' class='row g-1 mt-2'>{form}<div class='col-12 mt-2'><button class='btn btn-warning w-100'>Update</button></div></form></div>")

@app.route("/delete/<aid>")
def delete(aid):
    db_root.child(f"agents/{aid}").delete()
    clear_cache()
    return redirect("/")

if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",5000)))
