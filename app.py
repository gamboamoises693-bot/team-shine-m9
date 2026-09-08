
import os, json, time
from collections import defaultdict
from flask import Flask, request, redirect, render_template_string, jsonify
import firebase_admin
from firebase_admin import credentials, db
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "shine-m9-secret")

# Firebase init
FIREBASE_URL = os.environ.get("FIREBASE_DATABASE_URL")  # e.g. https://team-shine-m9-default-rtdb.asia-southeast1.firebasedatabase.app
if not firebase_admin._apps:
    if os.path.exists("serviceAccountKey.json"):
        cred = credentials.Certificate("serviceAccountKey.json")
        # auto detect URL from json or env
        db_url = FIREBASE_URL or os.environ.get("FIREBASE_DB_URL")
        if not db_url:
            # try to guess asia-southeast1 for PH
            db_url = "https://team-shine-m9-default-rtdb.asia-southeast1.firebasedatabase.app/"
        firebase_admin.initialize_app(cred, {"databaseURL": db_url})
    elif os.environ.get("FIREBASE_CREDENTIALS"):
        cred_dict = json.loads(os.environ.get("FIREBASE_CREDENTIALS"))
        cred = credentials.Certificate(cred_dict)
        db_url = FIREBASE_URL or "https://team-shine-m9-default-rtdb.asia-southeast1.firebasedatabase.app/"
        firebase_admin.initialize_app(cred, {"databaseURL": db_url})
    else:
        raise Exception("Need serviceAccountKey.json or FIREBASE_CREDENTIALS + FIREBASE_DATABASE_URL")

def get_db_ref():
    return db.reference("team_shine_m9")

# cache
_cache = {"agents": None, "time": 0}
def get_all_agents_fast():
    global _cache
    if _cache["agents"] and time.time() - _cache["time"] < 20:
        return _cache["agents"]
    ref = get_db_ref().child("agents")
    data = ref.get() or {}
    agents = []
    for aid, aval in data.items():
        if not isinstance(aval, dict):
            continue
        aval["id"] = aid
        agents.append(aval)
    agents.sort(key=lambda x: x.get("NAME","").lower())
    _cache = {"agents": agents, "time": time.time()}
    return agents

def clear_cache():
    global _cache
    _cache = {"agents": None, "time": 0}

def esc(s):
    if s is None: return ""
    return str(s).replace("&","&amp;").replace("<","&lt;").replace(">","&gt;").replace('"',"&quot;")

BASE_HTML = """<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1">
__REFRESH__
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
<link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.0/font/bootstrap-icons.css" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<title>TEAM SHINE M9 - Realtime</title>
<style>
body{background:#080c14;color:#e2e8f0;font-family:system-ui}
.navbar{background:#0f172a!important;border-bottom:1px solid #1e293b}
.card{background:#111827!important;border:1px solid #1f2937!important;border-radius:20px!important}
.kpi-card{background:linear-gradient(135deg,#111827 0%,#0f172a 100%)!important;border:1px solid #1e293b!important;border-radius:16px!important;padding:18px;position:relative;overflow:hidden}
.kpi-card::before{content:'';position:absolute;top:0;left:0;width:4px;height:100%;background:var(--accent)}
.kpi-icon{width:44px;height:44px;border-radius:12px;display:flex;align-items:center;justify-content:center;font-size:20px}
.table{color:#e2e8f0!important;margin-bottom:0!important}
.table thead th{background:#0f172a!important;color:#fbbf24!important;border-bottom:2px solid #fbbf24!important;font-size:11px!important;text-transform:uppercase!important;padding:14px 12px!important;font-weight:800!important}
.table tbody td{background:#111827!important;border-color:#1f2937!important;padding:14px 12px!important;color:#e2e8f0!important}
.badge-id{background:#0f172a;border:1px solid #334155;color:#94a3b8;border-radius:8px;padding:6px 10px}
.btn-exec{background:linear-gradient(135deg,#fbbf24,#f59e0b);color:#0f172a;font-weight:800;border:none;border-radius:12px;padding:8px 18px}
.search-box{background:#0f172a;border:1px solid #1f2937;color:white;border-radius:12px;padding:12px}
.chart-container{position:relative;height:280px!important}
.nav-pill{padding:8px 16px;border-radius:10px;text-decoration:none;font-size:13px;font-weight:600;color:#94a3b8}
.nav-pill.active{background:#fbbf24;color:#0f172a}
@media (max-width: 992px){.desktop-grid{grid-template-columns:1fr!important}}
.detail-card{background:#0f172a;border:1px solid #1e293b;border-radius:14px;padding:14px;height:100%}
.field-label{color:#64748b;font-size:10px;text-transform:uppercase;font-weight:700;margin-bottom:4px}
.field-value{color:#f1f5f9;font-weight:600;font-size:13px;word-break:break-word}
.agent-avatar{width:80px;height:80px;background:linear-gradient(135deg,#fbbf24,#f59e0b);border-radius:20px;display:flex;align-items:center;justify-content:center;font-size:32px;font-weight:900;color:#0f172a}
.agent-name-dark{color:#f1f5f9!important;font-weight:700!important}
.agent-sub{color:#94a3b8!important;font-weight:400!important;font-size:11px!important}
</style></head><body>
<nav class="navbar navbar-dark p-3 sticky-top"><div class="container-fluid d-flex justify-content-between flex-wrap gap-2">
<a class="navbar-brand fw-bold" href="/"><i class="bi bi-lightning-charge-fill text-warning"></i> TEAM SHINE M9 <span style="font-size:10px" class="badge bg-success">REALTIME DB</span> <span class="badge bg-warning text-dark" style="font-size:9px">ULTRA FAST</span></a>
<div class="d-flex gap-2 align-items-center">
<a href="/" class="nav-pill __HOME_ACTIVE__"><i class="bi bi-people"></i> Agents</a>
<a href="/dashboard" class="nav-pill __DASH_ACTIVE__"><i class="bi bi-speedometer2"></i> Dashboard</a>
<a href="/export_csv" class="btn btn-sm btn-outline-warning" style="border-radius:10px"><i class="bi bi-download"></i></a>
<a href="/add" class="btn btn-sm btn-warning fw-bold" style="border-radius:10px;color:#0f172a">+ Add</a>
</div>
</div></nav><div class="container-fluid p-3 p-md-4">
__CONTENT__
</div></body></html>"""

def render_page(content, total, refresh_secs=None, active='home'):
    refresh = f'<meta http-equiv="refresh" content="{refresh_secs}">' if refresh_secs else ''
    html_page = BASE_HTML.replace("__REFRESH__", refresh).replace("__CONTENT__", content)
    html_page = html_page.replace("__HOME_ACTIVE__", "active" if active=='home' else "")
    html_page = html_page.replace("__DASH_ACTIVE__", "active" if active=='dash' else "")
    return html_page

@app.route("/ping")
def ping():
    return "alive", 200

@app.route("/")
def index():
    agents = get_all_agents_fast()
    rows = ""
    for a in agents:
        ot = float(a.get("_ot_total",0) or 0)
        loss = float(a.get("_loss_total",0) or 0)
        net = ot-loss
        rows += f"<tr><td><span class='badge-id'>{esc(a['id'])}</span></td><td><a href='/view/{esc(a['id'])}' class='text-decoration-none' style='color:#f1f5f9'>{esc(a.get('NAME',''))}<br><small style='color:#94a3b8'>{esc(a.get('TENCENT ID',''))} | {esc(a.get('PHONE NAME',''))}</small></a></td><td><span class='badge bg-warning text-dark'>{ot:.1f}h</span></td><td><span class='badge bg-danger'>{loss:.1f}h</span></td><td><span class='badge bg-success'>{net:.1f}h</span></td></tr>"
    content = f"""
    <div class="d-flex justify-content-between align-items-center mb-3 flex-wrap gap-2">
      <h5 class="fw-bold mb-0">All Agents ({len(agents)}) - <span class="text-success">REALTIME ⚡</span> <span class="badge bg-success" style="font-size:10px">1 CALL ONLY</span></h5>
      <input id="searchBox" class="search-box" placeholder="Search..." onkeyup="filterTable()" style="min-width:250px">
    </div>
    <div class="card"><div class="table-responsive"><table class="table" id="agentTable"><thead><tr><th>ID</th><th>AGENT</th><th>OT</th><th>LOSS</th><th>NET</th></tr></thead><tbody>{rows}</tbody></table></div></div>
    <script>
    function filterTable(){{let q=document.getElementById('searchBox').value.toLowerCase();document.querySelectorAll('#agentTable tbody tr').forEach(r=>{{r.style.display=r.innerText.toLowerCase().includes(q)?'':'none'}})}}
    setInterval(()=>fetch('/ping'), 600000);
    </script>
    """
    return render_page(content, len(agents), active='home')

@app.route("/dashboard")
def dashboard():
    agents = get_all_agents_fast()
    total = len(agents)
    ot_total = sum(float(a.get("_ot_total",0) or 0) for a in agents)
    loss_total = sum(float(a.get("_loss_total",0) or 0) for a in agents)
    ot_by_agent = {a.get('NAME',''): float(a.get('_ot_total',0) or 0) for a in agents}
    loss_by_agent = {a.get('NAME',''): float(a.get('_loss_total',0) or 0) for a in agents}
    top_ot = sorted(ot_by_agent.items(), key=lambda x: x[1], reverse=True)[:5]
    top_loss = sorted(loss_by_agent.items(), key=lambda x: x[1], reverse=True)[:5]
    attendance = 100 - (loss_total / (total*176+1) *100) if total else 100
    now = datetime.now()
    content = f"""
    <div class="d-flex justify-content-between align-items-center mb-4">
      <div><h4 class="fw-bold mb-0">Command Center - Realtime DB</h4><small class="text-muted">1 JSON fetch only - fastest for call center</small></div>
      <span class="badge bg-success">LIVE {total} Agents</span>
    </div>
    <div class="row g-3 mb-4">
      <div class="col-6 col-lg-3"><div class="kpi-card" style="--accent:#fbbf24"><div class="text-muted" style="font-size:11px">TOTAL HC</div><div class="fs-3 fw-bold">{total}</div></div></div>
      <div class="col-6 col-lg-3"><div class="kpi-card" style="--accent:#22c55e"><div class="text-muted" style="font-size:11px">ATTENDANCE</div><div class="fs-3 fw-bold">{attendance:.1f}%</div></div></div>
      <div class="col-6 col-lg-3"><div class="kpi-card" style="--accent:#3b82f6"><div class="text-muted" style="font-size:11px">TOTAL OT</div><div class="fs-3 fw-bold">{ot_total:.1f}h</div></div></div>
      <div class="col-6 col-lg-3"><div class="kpi-card" style="--accent:#ef4444"><div class="text-muted" style="font-size:11px">TOTAL LOSS</div><div class="fs-3 fw-bold">{loss_total:.1f}h</div></div></div>
    </div>
    <div class="row g-3">
      <div class="col-lg-6"><div class="card p-3"><h6>🏆 Top 5 OT</h6><table class="table table-sm"><thead><tr><th>Agent</th><th>Hours</th></tr></thead><tbody>
        {''.join([f"<tr><td>{esc(n)}</td><td>{h:.1f}h</td></tr>" for n,h in top_ot])}
      </tbody></table></div></div>
      <div class="col-lg-6"><div class="card p-3"><h6>⚠️ Top 5 LOSS</h6><table class="table table-sm"><thead><tr><th>Agent</th><th>Hours</th></tr></thead><tbody>
        {''.join([f"<tr><td>{esc(n)}</td><td>{h:.1f}h</td></tr>" for n,h in top_loss]) if any(h>0 for _,h in top_loss) else "<tr><td colspan=2 class=text-center>No LOSS - Great!</td></tr>"}
      </tbody></table></div></div>
    </div>
    """
    return render_page(content, total, active='dash')

# ---- keep all other routes (view, add, edit, etc) using realtime ----
@app.route("/view/<aid>")
def view_agent(aid):
    data = get_db_ref().child(f"agents/{aid}").get()
    if not data:
        return "Not found", 404
    data["id"]=aid
    ot_logs = data.get("ot_logs", {})
    loss_logs = data.get("loss_logs", {})
    ot_list = []
    if isinstance(ot_logs, dict):
        for k,v in ot_logs.items():
            if isinstance(v, dict):
                v["_key"]=k
                ot_list.append(v)
    # sort by date desc
    ot_list.sort(key=lambda x: x.get("ot_date",""), reverse=True)
    ot_total = float(data.get("_ot_total",0) or 0)
    
    # build details html (simplified from old)
    fields = ["NAME","TENCENT ID","DATE HIRED","PHONE NAME","NBS ID","HEADSET SN","IBAS","DJANGO","NT LOG IN","Sales Force","ZOHO","BSS WEB","EMAIL","BIRTHDAY","CONTACT NO.","ADDRESS"]
    details_html = ""
    for f in fields:
        details_html += f"<div class='col-6'><div class='detail-card'><div class='field-label'>{f}</div><div class='field-value'>{esc(data.get(f,''))}</div></div></div>"
    
    ot_rows = ""
    for ot in ot_list:
        ot_rows+=f"<tr><td>{esc(ot.get('ot_date',''))}</td><td>{esc(ot.get('ot_type',''))}</td><td>{esc(ot.get('hours',''))}</td><td>{esc(ot.get('remarks',''))}</td></tr>"
    if not ot_rows:
        ot_rows="<tr><td colspan=4 class='text-center'>No OT</td></tr>"
    
    content = f"""
    <a href='/' class='btn btn-sm btn-outline-light mb-3'>← Back</a>
    <div class="card p-3 mb-3 text-center"><div class="agent-avatar mx-auto">{esc(data.get('NAME','')[0] if data.get('NAME') else 'A')}</div><h5 class="mt-2">{esc(data.get('NAME',''))}</h5><small>{esc(data.get('TENCENT ID',''))}</small><div class="mt-2"><a href='/edit/{aid}' class='btn btn-sm btn-warning'>Edit</a> <a href='/delete/{aid}' class='btn btn-sm btn-outline-danger' onclick="return confirm('Delete?')">Delete</a></div></div>
    <div class="card p-3 mb-3"><h6>Agent Details</h6><div class="row g-2">{details_html}</div></div>
    <div class="card p-3 mb-3"><h6>OT Logs - Total {ot_total:.1f}h</h6>
    <form method="POST" action="/add_ot/{aid}" class="row g-2 mb-3">
      <div class="col-6"><input type="date" name="ot_date" class="form-control" required></div>
      <div class="col-6"><select name="ot_type" class="form-control"><option>REGULAR</option><option>RDOT</option><option>HOLIDAY</option></select></div>
      <div class="col-6"><input type="number" step="0.5" name="hours" placeholder="Hours" class="form-control" required></div>
      <div class="col-6"><input type="text" name="remarks" placeholder="Remarks" class="form-control"></div>
      <div class="col-12"><button class="btn btn-success w-100">Add OT</button></div>
    </form>
    <div class="table-responsive"><table class="table table-sm"><thead><tr><th>DATE</th><th>TYPE</th><th>HRS</th><th>REMARKS</th></tr></thead><tbody>{ot_rows}</tbody></table></div></div>
    """
    return render_page(content, 0, active='home')

@app.route("/add_ot/<aid>", methods=["POST"])
def add_ot(aid):
    ref = get_db_ref().child(f"agents/{aid}")
    data = ref.get() or {}
    cur_ot = float(data.get("_ot_total",0) or 0)
    new_ot = float(request.form.get("hours",0) or 0)
    # push log
    log = {"ot_date": request.form.get("ot_date"), "ot_type": request.form.get("ot_type"), "hours": new_ot, "remarks": request.form.get("remarks",""), "created_at": datetime.now().isoformat()}
    ref.child("ot_logs").push(log)
    ref.update({"_ot_total": cur_ot + new_ot})
    clear_cache()
    return redirect(f"/view/{aid}")

@app.route("/add", methods=["GET","POST"])
def add_agent():
    if request.method=="POST":
        vals = {k: request.form.get(k,"") for k in ["NAME","TENCENT ID","DATE HIRED","PHONE NAME","NBS ID","HEADSET SN","IBAS","DJANGO","NT LOG IN","Sales Force","ZOHO","BSS WEB","EMAIL","BIRTHDAY","CONTACT NO.","ADDRESS"]}
        vals["_ot_total"]=0
        vals["_loss_total"]=0
        new_ref = get_db_ref().child("agents").push(vals)
        clear_cache()
        return redirect(f"/view/{new_ref.key}")
    content = """
    <div class="card p-4"><h5>Add Agent</h5><form method="POST" class="row g-2">
    """ + "".join([f'<div class="col-md-6"><label class="field-label">{f}</label><input name="{f}" class="form-control"></div>' for f in ["NAME","TENCENT ID","DATE HIRED","PHONE NAME","NBS ID","HEADSET SN","IBAS","DJANGO","NT LOG IN","Sales Force","ZOHO","BSS WEB","EMAIL","BIRTHDAY","CONTACT NO.","ADDRESS"]]) + """
    <div class="col-12"><button class="btn btn-warning w-100 fw-bold">Save Agent</button></div></form></div>
    """
    return render_page(content,0)

@app.route("/edit/<aid>", methods=["GET","POST"])
def edit_agent(aid):
    ref = get_db_ref().child(f"agents/{aid}")
    if request.method=="POST":
        vals = {k: request.form.get(k,"") for k in ["NAME","TENCENT ID","DATE HIRED","PHONE NAME","NBS ID","HEADSET SN","IBAS","DJANGO","NT LOG IN","Sales Force","ZOHO","BSS WEB","EMAIL","BIRTHDAY","CONTACT NO.","ADDRESS"]}
        ref.update(vals)
        clear_cache()
        return redirect(f"/view/{aid}")
    data = ref.get() or {}
    content = '<div class="card p-4"><h5>Edit Agent</h5><form method="POST" class="row g-2">'
    for f in ["NAME","TENCENT ID","DATE HIRED","PHONE NAME","NBS ID","HEADSET SN","IBAS","DJANGO","NT LOG IN","Sales Force","ZOHO","BSS WEB","EMAIL","BIRTHDAY","CONTACT NO.","ADDRESS"]:
        content+=f'<div class="col-md-6"><label class="field-label">{f}</label><input name="{f}" value="{esc(data.get(f,""))}" class="form-control"></div>'
    content+='<div class="col-12"><button class="btn btn-warning w-100">Update</button></div></form></div>'
    return render_page(content,0)

@app.route("/delete/<aid>")
def delete_agent(aid):
    get_db_ref().child(f"agents/{aid}").delete()
    clear_cache()
    return redirect("/")

@app.route("/export_csv")
def export_csv():
    import csv, io
    agents = get_all_agents_fast()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID","NAME","TENCENT ID","OT TOTAL","LOSS TOTAL","NET"])
    for a in agents:
        writer.writerow([a.get("id"), a.get("NAME"), a.get("TENCENT ID"), a.get("_ot_total",0), a.get("_loss_total",0), float(a.get("_ot_total",0) or 0)-float(a.get("_loss_total",0) or 0)])
    from flask import Response
    return Response(output.getvalue(), mimetype="text/csv", headers={"Content-Disposition":"attachment;filename=team_shine_m9.csv"})

# Migration from old Firestore / SQLite to Realtime
MIGRATE_DATA = {"agents": [{"id": 1, "NAME": "Bernaldo, Catherine", "TENCENT ID": "5116", "DATE HIRED": "2025-03-31", "PHONE NAME": "HOPE", "NBS ID": "10116", "HEADSET SN": "2309410DUO286", "IBAS": "CATBERNA", "DJANGO": "cabernaldo@uas2.com.ph", "NT LOG IN": "UAS-Bernaldo.Catheri", "Sales Force": "uas-bernaldo.cath@cict.com.ph", "ZOHO": "c.bernaldo@uas2.com.ph", "BSS WEB": "uas-bernaldo.cath@partner.convergeict.com", "EMAIL": "bernaldocatherine2@gmail.com", "BIRTHDAY": "1992-08-03", "CONTACT NO.": "09468168239", "ADDRESS": "15-C Feliza St. Brgy.Malabanias, Angeles City, Pampanga"}, {"id": 2, "NAME": "Lopez, Eljay", "TENCENT ID": "5243", "DATE HIRED": "2025-04-14", "PHONE NAME": "SOJI", "NBS ID": "10752", "HEADSET SN": "2309410DU1324", "IBAS": "", "DJANGO": "eljhay.lopez@uas2.com.ph", "NT LOG IN": "UAS-Lopez.eljhay", "Sales Force": "uas-lopez.eljay@cict.com.ph", "ZOHO": "eljhay.lopez@uas2.com.ph", "BSS WEB": "uas-lopez.eljay@partner.convergeict.com", "EMAIL": "is.eljaylopez1@gmail.com", "BIRTHDAY": "1999-11-02", "CONTACT NO.": "09666096553", "ADDRESS": "Blk 5 Lot 14 Rockville Subdivision, Barangay Malpitic, City of San Fernando, Pamapanga"}, {"id": 3, "NAME": "Maniago, Danzeil James", "TENCENT ID": "5242", "DATE HIRED": "2025-03-31", "PHONE NAME": "Danzeil", "NBS ID": "10148", "HEADSET SN": "2309410DU0522", "IBAS": "DAJMANIA", "DJANGO": "Damaniago@uas2.com.ph", "NT LOG IN": "UAS-Maniago.Danzeil", "Sales Force": "uas-danzeil.maniago@cict.com.ph", "ZOHO": "damaniago@uas2.com.ph", "BSS WEB": "uas-danzeil.maniago@partner.convergeict.com", "EMAIL": "denzeiljamesmaniago@gmail.com", "BIRTHDAY": "2003-01-16", "CONTACT NO.": "09630692546", "ADDRESS": "Blk.17 Lot.2, Brgy. Cristo Rey, Capas, Tarlac"}, {"id": 4, "NAME": "Navarro, Jerome", "TENCENT ID": "5093", "DATE HIRED": "2025-03-03", "PHONE NAME": "KHALEE", "NBS ID": "9808", "HEADSET SN": "2309410DU0098", "IBAS": "NAVJEROM", "DJANGO": "je.navarro@uas2.com.ph", "NT LOG IN": "UAS-Navarro.Jerome", "Sales Force": "uas-jerome.navarro@cict.com.ph", "ZOHO": "je.navarro@uas2.com.ph", "BSS WEB": "uas-jerome.navarro@partner.convergeict.com", "EMAIL": "jeromen891@gmail.com", "BIRTHDAY": "1998-04-16", "CONTACT NO.": "09670696382", "ADDRESS": "1036, Baranggay Capaya 1, Angeles City, Pampanga"}, {"id": 5, "NAME": "Paz, Ben Gerard", "TENCENT ID": "5038", "DATE HIRED": "2025-03-03", "PHONE NAME": "GIEH", "NBS ID": "9814", "HEADSET SN": "2309410DU0381", "IBAS": "PAZBENGE", "DJANGO": "bg.paz@uas2.com.ph", "NT LOG IN": "UAS-Paz.Ben", "Sales Force": "uas-ben.paz@cict.com.ph", "ZOHO": "bg.paz@uas2.com.ph", "BSS WEB": "uas-ben.paz@partner.convergeict.com", "EMAIL": "bengerardp@gmail.com", "BIRTHDAY": "1995-06-25", "CONTACT NO.": "09634269072", "ADDRESS": "Pulung Maragul, Angeles City"}, {"id": 6, "NAME": "Waje, Avy", "TENCENT ID": "5115", "DATE HIRED": "2025-03-03", "PHONE NAME": "SCARLET", "NBS ID": "9828", "HEADSET SN": "2309410DU1246", "IBAS": "WAJAVYWA", "DJANGO": "a.waje@uas2.com.ph", "NT LOG IN": "UAS-Waje.Avy", "Sales Force": "uas-avy.waje@cict.com.ph", "ZOHO": "a.waje@uas2.com.ph", "BSS WEB": "uas-avy.waje@partner.convergeict.com", "EMAIL": "avywaje43@gmail.com", "BIRTHDAY": "2005-01-16", "CONTACT NO.": "09534367262", "ADDRESS": "0366 Purok 2, Brgy. Calzadang Bayu, Porac, Pampanga"}, {"id": 7, "NAME": "Guevarra, James Rainielle", "TENCENT ID": "5291", "DATE HIRED": "2025-06-23", "PHONE NAME": "Rain", "NBS ID": "11412", "HEADSET SN": "", "IBAS": "JMSRNGVA", "DJANGO": "ja.guevarra@uas2.com.ph", "NT LOG IN": "UAS-Guevarra.JamesRa", "Sales Force": "uas-rain.guevarra@cict.com.ph", "ZOHO": "ja.guevarra@uas2.com.ph", "BSS WEB": "uas-rain.guevarra@partner.convergeict.com", "EMAIL": "jamesrainielle1423@gmail.com", "BIRTHDAY": "2006-08-31", "CONTACT NO.": "09480624706", "ADDRESS": "Blk cd Lot 2c phase 3, Sta. Lucia Rest., Brgy. San Isido, Magalang, Pampanga"}, {"id": 8, "NAME": "Pare, Crisha Joy", "TENCENT ID": "5310", "DATE HIRED": "2025-06-23", "PHONE NAME": "Crisha", "NBS ID": "11368", "HEADSET SN": "", "IBAS": "CRISPARE", "DJANGO": "cr.pare@uas2.com.ph", "NT LOG IN": "UAS-Pare.Crishajoy", "Sales Force": "uas-crishajoy.pare@cict.com.ph", "ZOHO": "cr.pare@uas2.com.ph", "BSS WEB": "uas-crishajoy.pare@partner.convergeict.com", "EMAIL": "Crishapare@gmail.com", "BIRTHDAY": "2004-08-16", "CONTACT NO.": "09496274867", "ADDRESS": "3219 North Dang Bakal, Dau, Mabalacat City, Pampanga"}, {"id": 9, "NAME": "Paraga, Elisa", "TENCENT ID": "5090", "DATE HIRED": "2025-04-28", "PHONE NAME": "Angel", "NBS ID": "10850", "HEADSET SN": "2309410DU0875", "IBAS": "RAGASELI", "DJANGO": "el.paragas@uas2.com.ph", "NT LOG IN": "UAS-paragas.elisallo", "Sales Force": "uas-elisa.paragas@cict.com.ph", "ZOHO": "el.paragas@uas2.com.ph", "BSS WEB": "uas-elisa.paragas@partner.convergeict.com", "EMAIL": "elp012581@gmail.com", "BIRTHDAY": "1981-01-25", "CONTACT NO.": "09760221814", "ADDRESS": "5016 Abacan, Malabanias, Angeles City, Pampanga"}, {"id": 10, "NAME": "Cahuyong, Daveliet Jane", "TENCENT ID": "5726", "DATE HIRED": "2025-08-11", "PHONE NAME": "Devie", "NBS ID": "11518", "HEADSET SN": "", "IBAS": "DCAHUYO", "DJANGO": "d.cahuyong@uas2.com.ph", "NT LOG IN": "UAS-Cahuyong.Davelie", "Sales Force": "uas-dave.cahuyog@cict.com.ph", "ZOHO": "d.cahuyong@uas2.com.ph", "BSS WEB": "uas-dave.cahuyog@partner.convergeict.com", "EMAIL": "daveliethitosis@gmail.com", "BIRTHDAY": "2002-11-08", "CONTACT NO.": "09485518457", "ADDRESS": "Prk 6. Kadamay, Brgy. Cuayan, Angeles City, Pampanga"}, {"id": 11, "NAME": "Quiambao, Allen", "TENCENT ID": "4995", "DATE HIRED": "2026-05-04", "PHONE NAME": "Noble", "NBS ID": "12468", "HEADSET SN": "", "IBAS": "ALQUIAMB", "DJANGO": "al.quiambao@uas2.com.ph", "NT LOG IN": "UAS-allen.quiambao", "Sales Force": "uas-allen.quiambao@cict.com.ph", "ZOHO": "al.quiambao@uas2.com.ph", "BSS WEB": "uas-allen.quiambao@partner.convergeict.com", "EMAIL": "allenquiambao298@gmail.com", "BIRTHDAY": "2008-02-09", "CONTACT NO.": "09978178943", "ADDRESS": "Blk37 Lot20, San Isidro Resettelment, Magalang, Pampanga"}, {"id": 12, "NAME": "Reyes, Katherine", "TENCENT ID": "4996", "DATE HIRED": "2026-05-04", "PHONE NAME": "Kassel", "NBS ID": "12474", "HEADSET SN": "", "IBAS": "KAREYESE", "DJANGO": "ka.reyes@uas2.com.ph", "NT LOG IN": "UAS-katherine.reyes", "Sales Force": "uas-katherine.reyes@cict.com.ph", "ZOHO": "ka.reyes@uas2.com.ph", "BSS WEB": "uas-katherine.reyes@partner.convergeict.com", "EMAIL": "reyeskatherine093@gmail.com", "BIRTHDAY": "2026-09-19", "CONTACT NO.": "09614809467", "ADDRESS": "1624 Interior St. Brgy. Ninoy Aquino, Marisol, Angeles City, Pampanga"}, {"id": 13, "NAME": "Salmero, Jeanel Ann", "TENCENT ID": "4997", "DATE HIRED": "2026-05-04", "PHONE NAME": "Rhett", "NBS ID": "12476", "HEADSET SN": "", "IBAS": "JESALMER", "DJANGO": "je.salmero@uas2.com.ph", "NT LOG IN": "UAS-jeanel.salmero", "Sales Force": "uas-jeanel.salmero@cict.com.ph", "ZOHO": "je.salmero@uas2.com.ph", "BSS WEB": "uas-jeanel.salmero@partner.convergeict.com", "EMAIL": "santosjeanel74@gmail.com", "BIRTHDAY": "2026-12-15", "CONTACT NO.": "09169205580", "ADDRESS": "5086 Juicy Fruit, Brgy Duquit, Mabalacat City, Pampanga"}, {"id": 14, "NAME": "Sampaga, Marie Joy", "TENCENT ID": "4998", "DATE HIRED": "2026-05-04", "PHONE NAME": "Arhem", "NBS ID": "12478", "HEADSET SN": "", "IBAS": "MASAMPAG", "DJANGO": "ma.sampaga@uas2.com.ph", "NT LOG IN": "UAS-marie.sampaga", "Sales Force": "uas-marie.sampaga@cict.com.ph", "ZOHO": "ma.sampaga@uas2.com.ph", "BSS WEB": "uas-marie.sampaga@partner.convergeict.com", "EMAIL": "lacsonmariejoy@gmail.com", "BIRTHDAY": "1997-11-15", "CONTACT NO.": "09368001203", "ADDRESS": "782 Kadenang Kristal, Sapang Biabas, Dau, Mabalacat, Pampanga"}, {"id": 15, "NAME": "Arcilla, Azarias", "TENCENT ID": "4909", "DATE HIRED": "2026-05-04", "PHONE NAME": "Chance", "NBS ID": "12352", "HEADSET SN": "J0XL4V", "IBAS": "AZARARCI", "DJANGO": "a.azarias@uas2.com.ph", "NT LOG IN": "UAS-Arcilla.Azarias", "Sales Force": "uas-azarias.arcilla@cict.com.ph", "ZOHO": "a.azarias@uas2.com.ph", "BSS WEB": "uas-azarias.arcilla@partner.convergeict.com", "EMAIL": "chancearcilla5100@gmail.com", "BIRTHDAY": "2006-05-01", "CONTACT NO.": "09122974939", "ADDRESS": "989 Chico St. San Francisco, Mabalacat City, Pampanga"}, {"id": 16, "NAME": "Bigornia, Shenhel", "TENCENT ID": "4910", "DATE HIRED": "2026-05-04", "PHONE NAME": "Daiji", "NBS ID": "12360", "HEADSET SN": "J0XJP0", "IBAS": "SHENBIGO", "DJANGO": "s.bigornia@uas2.com.ph", "NT LOG IN": "UAS-Bigornia.Shenhel", "Sales Force": "uas-shenhel.bigornia@cict.com.ph", "ZOHO": "s.bigornia@uas2.com.ph", "BSS WEB": "uas-shenhel.bigornia@partner.convergeict.com", "EMAIL": "bshenhel@gmail.com", "BIRTHDAY": "2002-02-19", "CONTACT NO.": "09941644309", "ADDRESS": "26-18B Malaysia St. Don Bonifacio, Pulung Maragul, Balibago, Angeles City"}, {"id": 17, "NAME": "Cano, Regina Carla", "TENCENT ID": "4911", "DATE HIRED": "2026-05-04", "PHONE NAME": "Rachel", "NBS ID": "12378", "HEADSET SN": "J0XJP3", "IBAS": "RCARCANO", "DJANGO": "r.cano@uas2.com.ph", "NT LOG IN": "UAS-Cano.Regina", "Sales Force": "uas-regina.cano@cict.com.ph", "ZOHO": "r.cano@uas2.com.ph", "BSS WEB": "uas-regina.cano@partner.convergeict.com", "EMAIL": "carlacano111517@gmail.com", "BIRTHDAY": "1998-11-11", "CONTACT NO.": "09069331284", "ADDRESS": "05 Mabini St. San Nicolas, Angeles City, Pampanga"}, {"id": 18, "NAME": "Ocampo, Joana Marie", "TENCENT ID": "5269", "DATE HIRED": "2026-05-18", "PHONE NAME": "Tams", "NBS ID": "12578", "HEADSET SN": "JOXKVR", "IBAS": "JNMRIMCP", "DJANGO": "jo.ocampo@uas2.com.ph", "NT LOG IN": "UAS-Ocampo.joana", "Sales Force": "uas-joana.ocampo@cict.com.ph", "ZOHO": "jo.ocampo@uas2.com.p", "BSS WEB": "uas-joana.ocampo@partner.convergeict.com", "EMAIL": "omanarang30@gmail.com", "BIRTHDAY": "1992-08-30", "CONTACT NO.": "09491233865", "ADDRESS": "49 Purok 1, San Pedro 2, Magalang, Pampanga"}, {"id": 19, "NAME": "Pangilinan, Princess", "TENCENT ID": "5271", "DATE HIRED": "2026-05-18", "PHONE NAME": "Peach", "NBS ID": "12580", "HEADSET SN": "JOXKVN", "IBAS": "PRNSPGNN", "DJANGO": "pr.pangilinan@uas2.com.ph", "NT LOG IN": "UAS-Pangilinan.Princ", "Sales Force": "uas-prin.pangilinan@cict.com.ph", "ZOHO": "pr.pangilinan@uas2.com.ph", "BSS WEB": "uas-prin.pangilinan@partner.convergeict.com", "EMAIL": "pangilinanp387@gmail.com", "BIRTHDAY": "2006-12-19", "CONTACT NO.": "09707673225", "ADDRESS": "31 D Yakal St. Aguas Subdivision, Manibaug Paralaya, Porac Pampanga"}], "ot_logs": [{"id": 1, "agent_id": 15, "ot_date": "2026-09-02", "ot_type": "REGULAR", "hours": 2.0, "remarks": "Imported from September sheet - Sept 2", "created_at": "2026-09-07 17:38:45"}, {"id": 2, "agent_id": 15, "ot_date": "2026-09-04", "ot_type": "REGULAR", "hours": 1.0, "remarks": "Imported from September sheet - Sept 4", "created_at": "2026-09-07 17:38:45"}, {"id": 3, "agent_id": 15, "ot_date": "2026-09-05", "ot_type": "RDOT", "hours": 10.0, "remarks": "Imported from September sheet - Sept 5", "created_at": "2026-09-07 17:38:45"}, {"id": 4, "agent_id": 1, "ot_date": "2026-09-01", "ot_type": "REGULAR", "hours": 3.0, "remarks": "Imported from September sheet - Sept 1", "created_at": "2026-09-07 17:38:45"}, {"id": 5, "agent_id": 1, "ot_date": "2026-09-02", "ot_type": "REGULAR", "hours": 1.0, "remarks": "Imported from September sheet - Sept 2", "created_at": "2026-09-07 17:38:45"}, {"id": 6, "agent_id": 1, "ot_date": "2026-09-03", "ot_type": "REGULAR", "hours": 2.0, "remarks": "Imported from September sheet - Sept 3", "created_at": "2026-09-07 17:38:45"}, {"id": 7, "agent_id": 1, "ot_date": "2026-09-04", "ot_type": "REGULAR", "hours": 1.0, "remarks": "Imported from September sheet - Sept 4", "created_at": "2026-09-07 17:38:45"}, {"id": 8, "agent_id": 1, "ot_date": "2026-09-05", "ot_type": "RDOT", "hours": 10.0, "remarks": "Imported from September sheet - Sept 5", "created_at": "2026-09-07 17:38:45"}, {"id": 9, "agent_id": 9, "ot_date": "2026-09-01", "ot_type": "REGULAR", "hours": 1.0, "remarks": "Imported from September sheet - Sept 1", "created_at": "2026-09-07 17:38:45"}, {"id": 10, "agent_id": 9, "ot_date": "2026-09-03", "ot_type": "REGULAR", "hours": 1.0, "remarks": "Imported from September sheet - Sept 3", "created_at": "2026-09-07 17:38:45"}, {"id": 11, "agent_id": 9, "ot_date": "2026-09-05", "ot_type": "RDOT", "hours": 10.0, "remarks": "Imported from September sheet - Sept 5", "created_at": "2026-09-07 17:38:45"}, {"id": 12, "agent_id": 8, "ot_date": "2026-09-01", "ot_type": "REGULAR", "hours": 1.0, "remarks": "Imported from September sheet - Sept 1", "created_at": "2026-09-07 17:38:45"}, {"id": 13, "agent_id": 8, "ot_date": "2026-09-02", "ot_type": "REGULAR", "hours": 1.0, "remarks": "Imported from September sheet - Sept 2", "created_at": "2026-09-07 17:38:45"}, {"id": 14, "agent_id": 8, "ot_date": "2026-09-03", "ot_type": "REGULAR", "hours": 2.0, "remarks": "Imported from September sheet - Sept 3", "created_at": "2026-09-07 17:38:45"}, {"id": 15, "agent_id": 8, "ot_date": "2026-09-05", "ot_type": "RDOT", "hours": 5.0, "remarks": "Imported from September sheet - Sept 5", "created_at": "2026-09-07 17:38:45"}, {"id": 16, "agent_id": 5, "ot_date": "2026-09-01", "ot_type": "REGULAR", "hours": 2.0, "remarks": "Imported from September sheet - Sept 1", "created_at": "2026-09-07 17:38:45"}, {"id": 17, "agent_id": 5, "ot_date": "2026-09-02", "ot_type": "REGULAR", "hours": 1.0, "remarks": "Imported from September sheet - Sept 2", "created_at": "2026-09-07 17:38:45"}, {"id": 18, "agent_id": 5, "ot_date": "2026-09-03", "ot_type": "REGULAR", "hours": 1.0, "remarks": "Imported from September sheet - Sept 3", "created_at": "2026-09-07 17:38:45"}, {"id": 19, "agent_id": 5, "ot_date": "2026-09-04", "ot_type": "REGULAR", "hours": 3.0, "remarks": "Imported from September sheet - Sept 4", "created_at": "2026-09-07 17:38:45"}, {"id": 20, "agent_id": 5, "ot_date": "2026-09-05", "ot_type": "RDOT", "hours": 5.0, "remarks": "Imported from September sheet - Sept 5", "created_at": "2026-09-07 17:38:45"}, {"id": 21, "agent_id": 11, "ot_date": "2026-09-01", "ot_type": "REGULAR", "hours": 1.0, "remarks": "Imported from September sheet - Sept 1", "created_at": "2026-09-07 17:38:45"}, {"id": 22, "agent_id": 11, "ot_date": "2026-09-02", "ot_type": "REGULAR", "hours": 1.0, "remarks": "Imported from September sheet - Sept 2", "created_at": "2026-09-07 17:38:45"}, {"id": 23, "agent_id": 12, "ot_date": "2026-09-01", "ot_type": "REGULAR", "hours": 1.0, "remarks": "Imported from September sheet - Sept 1", "created_at": "2026-09-07 17:38:45"}, {"id": 24, "agent_id": 6, "ot_date": "2026-09-05", "ot_type": "RDOT", "hours": 7.0, "remarks": "Imported from September sheet - Sept 5", "created_at": "2026-09-07 17:38:45"}, {"id": 25, "agent_id": 18, "ot_date": "2026-09-01", "ot_type": "REGULAR", "hours": 2.0, "remarks": "Imported from September sheet - Sept 1", "created_at": "2026-09-07 17:38:45"}, {"id": 26, "agent_id": 18, "ot_date": "2026-09-02", "ot_type": "REGULAR", "hours": 1.0, "remarks": "Imported from September sheet - Sept 2", "created_at": "2026-09-07 17:38:45"}, {"id": 27, "agent_id": 19, "ot_date": "2026-09-01", "ot_type": "REGULAR", "hours": 1.0, "remarks": "Imported from September sheet - Sept 1", "created_at": "2026-09-07 17:38:45"}, {"id": 28, "agent_id": 2, "ot_date": "2026-09-04", "ot_type": "REGULAR", "hours": 1.0, "remarks": "Imported from September sheet - Sept 4", "created_at": "2026-09-07 17:38:45"}, {"id": 29, "agent_id": 3, "ot_date": "2026-09-04", "ot_type": "REGULAR", "hours": 1.0, "remarks": "Imported from September sheet - Sept 4", "created_at": "2026-09-07 17:38:45"}, {"id": 30, "agent_id": 4, "ot_date": "2026-09-01", "ot_type": "REGULAR", "hours": 1.0, "remarks": "Imported from September sheet - Sept 1", "created_at": "2026-09-07 17:38:45"}]}

@app.route("/migrate_realtime")
def migrate_realtime():
    existing = get_db_ref().child("agents").get()
    if existing and len(existing)>0:
        return f"Already {len(existing)} agents in Realtime - delete first if re-migrate. <a href='/'>Home</a>"
    count=0
    for ag in MIGRATE_DATA["agents"]:
        aid = str(ag.get("id") or ag.get("ID") or count+1)
        ag.pop("id", None)
        clean = {k: ("" if v is None else str(v)) for k,v in ag.items()}
        clean["_ot_total"]=0
        clean["_loss_total"]=0
        # sum ot for this agent
        ot_sum = sum(float(o.get("hours",0) or 0) for o in MIGRATE_DATA["ot_logs"] if str(o.get("agent_id"))==aid)
        clean["_ot_total"]=ot_sum
        get_db_ref().child(f"agents/{aid}").set(clean)
        # add ot logs
        for ot in MIGRATE_DATA["ot_logs"]:
            if str(ot.get("agent_id"))==aid:
                get_db_ref().child(f"agents/{aid}/ot_logs").push({"ot_date": str(ot.get("ot_date")), "ot_type": str(ot.get("ot_type")), "hours": float(ot.get("hours",0) or 0), "remarks": str(ot.get("remarks","")), "created_at": str(ot.get("created_at",""))})
        count+=1
    clear_cache()
    return f"<h1>DONE! Migrated {count} agents to Realtime DB</h1><a href='/'>Go Home</a>"

@app.route("/migrate_status")
def migrate_status():
    agents = get_all_agents_fast()
    return f"{len(agents)} agents in Realtime DB"

if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",5000)))
