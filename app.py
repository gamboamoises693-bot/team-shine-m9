
import os, json, html, io, csv
from flask import Flask, request, redirect, Response
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "shine-m9-secret-key-change-me")

# --- Firebase Init ---
# On Render: set FIREBASE_CREDENTIALS env var = entire JSON content of service account
# Locally: put serviceAccountKey.json in same folder as this file

if not firebase_admin._apps:
    cred_json = os.environ.get("FIREBASE_CREDENTIALS")
    if cred_json:
        # Handle both raw JSON and base64 (some people paste it weird)
        cred_dict = json.loads(cred_json)
        cred = credentials.Certificate(cred_dict)
    else:
        # Local file fallback
        if os.path.exists("serviceAccountKey.json"):
            cred = credentials.Certificate("serviceAccountKey.json")
        else:
            raise RuntimeError("FIREBASE_CREDENTIALS not set and serviceAccountKey.json not found. See setup guide.")
    firebase_admin.initialize_app(cred)

db = firestore.client()

COLS = ['NAME', 'TENCENT ID', 'DATE HIRED', 'PHONE NAME', 'NBS ID', 'HEADSET SN', 'IBAS', 'DJANGO', 'NT LOG IN', 'Sales Force', 'ZOHO', 'BSS WEB', 'EMAIL', 'BIRTHDAY', 'CONTACT NO.', 'ADDRESS']

def esc(v):
    return html.escape(str(v)) if v is not None else ""

def get_all_agents():
    docs = db.collection('agents').stream()
    agents = []
    for d in docs:
        data = d.to_dict()
        data['id'] = d.id
        agents.append(data)
    # sort by NAME
    agents.sort(key=lambda x: x.get('NAME','').lower())
    return agents

def get_agent(aid):
    doc = db.collection('agents').document(str(aid)).get()
    if not doc.exists:
        return None
    data = doc.to_dict()
    data['id'] = doc.id
    return data

# --- BASE HTML kept from your original ---
BASE_HTML = """<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1">
__REFRESH__
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
<link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.0/font/bootstrap-icons.css" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<title>TEAM SHINE M9 - Command Center</title>
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
.detail-card{background:#0f172a;border:1px solid #1e293b;border-radius:14px;padding:14px;height:100%}
.field-label{color:#64748b;font-size:10px;text-transform:uppercase;font-weight:700;margin-bottom:4px}
.field-value{color:#f1f5f9;font-weight:600;font-size:13px;word-break:break-word}
.agent-avatar{width:80px;height:80px;background:linear-gradient(135deg,#fbbf24,#f59e0b);border-radius:20px;display:flex;align-items:center;justify-content:center;font-size:32px;font-weight:900;color:#0f172a}
.stat-card{background:#0f172a;border:1px solid #1e293b;border-radius:16px;padding:16px;text-align:center}
.stat-value{font-size:28px;font-weight:800}
.desktop-grid{display:grid;grid-template-columns:340px 1fr;gap:20px}
.agent-sidebar{position:sticky;top:90px}
.details-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.ot-loss-grid{display:grid;grid-template-columns:1fr 1fr;gap:20px}
.input-dark{background:#0a0e1a!important;border:1px solid #1f2937!important;color:white!important;border-radius:10px!important}
.agent-name-dark{color:#f1f5f9!important;font-weight:700!important}
.agent-sub{color:#94a3b8!important;font-weight:400!important;font-size:11px!important}
.chart-container{position:relative;height:280px!important}
.nav-pill{padding:8px 16px;border-radius:10px;text-decoration:none;font-size:13px;font-weight:600;color:#94a3b8}
.nav-pill.active{background:#fbbf24;color:#0f172a}
.trend-up{color:#22c55e} .trend-down{color:#ef4444}
@media (max-width: 992px){.desktop-grid{grid-template-columns:1fr!important}.agent-sidebar{position:static!important}.ot-loss-grid{grid-template-columns:1fr!important}}
</style></head><body>
<nav class="navbar navbar-dark p-3 sticky-top"><div class="container-fluid d-flex justify-content-between flex-wrap gap-2">
<a class="navbar-brand fw-bold" href="/"><i class="bi bi-lightning-charge-fill text-warning"></i> TEAM SHINE M9 <span style="font-size:10px" class="badge bg-warning text-dark">LIVE</span></a>
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

@app.route("/")
def index():
    agents = get_all_agents()
    q = request.args.get("q","").lower()
    if q:
        agents = [a for a in agents if q in str(a.get('NAME','')).lower() or q in str(a.get('TENCENT ID','')).lower()]
    
    rows = ""
    for a in agents:
        # calculate OT/LOSS from subcollections
        ot_docs = db.collection('agents').document(a['id']).collection('ot_logs').stream()
        loss_docs = db.collection('agents').document(a['id']).collection('loss_logs').stream()
        ot_sum = sum(float(d.to_dict().get('hours',0) or 0) for d in ot_docs)
        loss_sum = sum(float(d.to_dict().get('hours',0) or 0) for d in loss_docs)
        rows += f"<tr><td><span class='badge-id'>{esc(a['id'][:6])}</span></td><td><a href='/view/{esc(a['id'])}' class='agent-name-dark text-decoration-none'>{esc(a.get('NAME',''))}</a><div class='agent-sub'>{esc(a.get('TENCENT ID',''))}</div></td><td class='text-success fw-bold'>{ot_sum}</td><td class='text-danger fw-bold'>{loss_sum}</td><td class='fw-bold'>{ot_sum-loss_sum}</td></tr>"

    content = f"""
    <div class="mb-3"><input id="search" placeholder="Search NAME or TENCENT ID..." class="search-box w-100" value="{esc(request.args.get('q',''))}" onkeyup="if(event.key==='Enter'){{window.location='/?q='+this.value}}"></div>
    <div class='card p-0 overflow-hidden'><div class='p-3 d-flex justify-content-between' style='background:#0f172a;border-bottom:1px solid #fbbf24'><h6 class='fw-bold mb-0 text-white'>All Agents ({len(agents)}) - Firebase Persistent</h6><span class='badge bg-success'>LIVE</span></div><div class='table-responsive'><table class='table table-hover mb-0'><thead><tr><th>ID</th><th>AGENT</th><th>OT</th><th>LOSS</th><th>NET</th></tr></thead><tbody>{rows if rows else '<tr><td colspan=5 class=text-center style=color:#94a3b8>No agents yet - click Add Agent</td></tr>'}</tbody></table></div></div>
    """
    return render_page(content, len(agents))

@app.route("/view/<aid>")
def view(aid):
    ag = get_agent(aid)
    if not ag:
        return redirect("/")
    ot_logs = [d.to_dict() | {'id': d.id} for d in db.collection('agents').document(aid).collection('ot_logs').order_by('created_at', direction=firestore.Query.DESCENDING).stream()]
    loss_logs = [d.to_dict() | {'id': d.id} for d in db.collection('agents').document(aid).collection('loss_logs').order_by('created_at', direction=firestore.Query.DESCENDING).stream()]
    
    details = "".join([f"<div class='detail-card'><div class='field-label'>{esc(c)}</div><div class='field-value'>{esc(ag.get(c,''))}</div></div>" for c in COLS])
    
    ot_rows = "".join([f"<tr><td>{esc(x.get('ot_date',''))}</td><td>{esc(x.get('ot_type',''))}</td><td>{esc(x.get('hours',''))}</td><td>{esc(x.get('remarks',''))}</td></tr>" for x in ot_logs]) or "<tr><td colspan=4 class='text-center text-muted'>No OT logs</td></tr>"
    loss_rows = "".join([f"<tr><td>{esc(x.get('loss_date',''))}</td><td>{esc(x.get('loss_type',''))}</td><td>{esc(x.get('hours',''))}</td><td>{esc(x.get('remarks',''))}</td></tr>" for x in loss_logs]) or "<tr><td colspan=4 class='text-center text-muted'>No LOSS logs</td></tr>"

    content = f"""
    <a href='/' class='btn btn-sm btn-outline-light mb-3' style='border-radius:10px'>Back</a>
    <div class="desktop-grid">
      <div class="agent-sidebar"><div class="card p-4 text-center"><div class="agent-avatar mx-auto mb-3">{esc(ag.get('NAME','')[0].upper() if ag.get('NAME') else 'A')}</div><h5 class="agent-name-dark">{esc(ag.get('NAME',''))}</h5><div class="agent-sub mb-3">{esc(ag.get('TENCENT ID',''))}</div><div class="d-flex gap-2 justify-content-center"><a href="/edit/{esc(ag['id'])}" class="btn btn-warning btn-sm fw-bold">Edit</a><form method="post" action="/delete/{esc(ag['id'])}" onsubmit="return confirm('Delete?')"><button class="btn btn-outline-danger btn-sm">Delete</button></form></div></div></div>
      <div><div class="card p-4 mb-3"><h6 class="fw-bold mb-3">Agent Details</h6><div class="details-grid">{details}</div></div>
      <div class="ot-loss-grid">
        <div class="card p-3"><h6 class="fw-bold">OT Logs</h6>
        <form method="post" action="/add_ot/{esc(ag['id'])}" class="row g-2 mb-3"><div class="col-6"><input name="ot_date" type="date" class="form-control input-dark" required></div><div class="col-6"><select name="ot_type" class="form-control input-dark"><option>Regular OT</option><option>RDOT</option></select></div><div class="col-6"><input name="hours" type="number" step="0.5" placeholder="Hours" class="form-control input-dark" required></div><div class="col-6"><input name="remarks" placeholder="Remarks" class="form-control input-dark"></div><div class="col-12"><button class="btn btn-success btn-sm w-100">Add OT</button></div></form>
        <div class="table-responsive"><table class="table table-sm"><thead><tr><th>Date</th><th>Type</th><th>Hrs</th><th>Remarks</th></tr></thead><tbody>{ot_rows}</tbody></table></div></div>
        <div class="card p-3"><h6 class="fw-bold">LOSS Logs</h6>
        <form method="post" action="/add_loss/{esc(ag['id'])}" class="row g-2 mb-3"><div class="col-6"><input name="loss_date" type="date" class="form-control input-dark" required></div><div class="col-6"><select name="loss_type" class="form-control input-dark"><option>Absent</option><option>Late</option><option>Undertime</option></select></div><div class="col-6"><input name="hours" type="number" step="0.5" placeholder="Hours" class="form-control input-dark" required></div><div class="col-6"><input name="remarks" placeholder="Remarks" class="form-control input-dark"></div><div class="col-12"><button class="btn btn-danger btn-sm w-100">Add LOSS</button></div></form>
        <div class="table-responsive"><table class="table table-sm"><thead><tr><th>Date</th><th>Type</th><th>Hrs</th><th>Remarks</th></tr></thead><tbody>{loss_rows}</tbody></table></div></div>
      </div></div>
    </div>
    """
    return render_page(content, 0, active='home')

@app.route("/add", methods=["GET","POST"])
@app.route("/edit/<aid>", methods=["GET","POST"])
def add_edit(aid=None):
    ag = get_agent(aid) if aid else None
    if request.method=="POST":
        vals = {c: request.form.get(c,"") for c in COLS}
        if aid:
            db.collection('agents').document(aid).update(vals)
        else:
            _, doc_ref = db.collection('agents').add(vals)
            aid = doc_ref.id
        return redirect(f"/view/{aid}")
    f = "".join([f"<div class='col-md-6 mb-3'><label class='field-label'>{esc(c)}</label><input name='{c}' value='{esc(ag.get(c,'')) if ag else ''}' class='form-control input-dark'></div>" for c in COLS])
    title="Edit Agent" if aid else "Add Agent"
    content=f"<a href='/' class='btn btn-sm btn-outline-light mb-3' style='border-radius:10px'>Back</a><div class='card p-4'><h4 class='fw-bold'>{title}</h4><form method='post' class='row'>{f}<div class='col-12 mt-3'><button class='btn btn-warning fw-bold'>Save</button></div></form></div>"
    return render_page(content, 0, active='home')

@app.route("/add_ot/<aid>", methods=["POST"])
def add_ot(aid):
    db.collection('agents').document(aid).collection('ot_logs').add({
        'ot_date': request.form.get('ot_date'),
        'ot_type': request.form.get('ot_type'),
        'hours': float(request.form.get('hours',0)),
        'remarks': request.form.get('remarks',''),
        'created_at': datetime.now().isoformat()
    })
    return redirect(f"/view/{aid}")

@app.route("/add_loss/<aid>", methods=["POST"])
def add_loss(aid):
    db.collection('agents').document(aid).collection('loss_logs').add({
        'loss_date': request.form.get('loss_date'),
        'loss_type': request.form.get('loss_type'),
        'hours': float(request.form.get('hours',0)),
        'remarks': request.form.get('remarks',''),
        'created_at': datetime.now().isoformat()
    })
    return redirect(f"/view/{aid}")

@app.route("/delete/<aid>", methods=["POST"])
def delete(aid):
    # delete subcollections first
    for coll in ['ot_logs', 'loss_logs']:
        docs = db.collection('agents').document(aid).collection(coll).stream()
        for d in docs:
            d.reference.delete()
    db.collection('agents').document(aid).delete()
    return redirect("/")

@app.route("/export_csv")
def export_csv():
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["TEAM SHINE M9 - FIREBASE REPORT", f"Generated {datetime.now()}"])
    agents = get_all_agents()
    writer.writerow(["ID", "NAME", "OT", "LOSS", "NET"])
    for a in agents:
        ot_sum = sum(float(d.to_dict().get('hours',0) or 0) for d in db.collection('agents').document(a['id']).collection('ot_logs').stream())
        loss_sum = sum(float(d.to_dict().get('hours',0) or 0) for d in db.collection('agents').document(a['id']).collection('loss_logs').stream())
        if ot_sum==0 and loss_sum==0:
            continue
        writer.writerow([a['id'], a.get('NAME',''), ot_sum, loss_sum, ot_sum-loss_sum])
    output.seek(0)
    return Response(output.getvalue(), mimetype="text/csv", headers={"Content-Disposition": f"attachment;filename=TeamShineM9_Firebase_{datetime.now().strftime('%Y%m%d')}.csv"})


# --- MIGRATION DATA (from your old SQLite) ---
MIGRATE_AGENTS = [
  {
    "id": 1,
    "NAME": "Bernaldo, Catherine",
    "TENCENT ID": "5116",
    "DATE HIRED": "2025-03-31",
    "PHONE NAME": "HOPE",
    "NBS ID": "10116",
    "HEADSET SN": "2309410DUO286",
    "IBAS": "CATBERNA",
    "DJANGO": "cabernaldo@uas2.com.ph",
    "NT LOG IN": "UAS-Bernaldo.Catheri",
    "Sales Force": "uas-bernaldo.cath@cict.com.ph",
    "ZOHO": "c.bernaldo@uas2.com.ph",
    "BSS WEB": "uas-bernaldo.cath@partner.convergeict.com",
    "EMAIL": "bernaldocatherine2@gmail.com",
    "BIRTHDAY": "1992-08-03",
    "CONTACT NO.": "09468168239",
    "ADDRESS": "15-C Feliza St. Brgy.Malabanias, Angeles City, Pampanga"
  },
  {
    "id": 2,
    "NAME": "Lopez, Eljay",
    "TENCENT ID": "5243",
    "DATE HIRED": "2025-04-14",
    "PHONE NAME": "SOJI",
    "NBS ID": "10752",
    "HEADSET SN": "2309410DU1324",
    "IBAS": "",
    "DJANGO": "eljhay.lopez@uas2.com.ph",
    "NT LOG IN": "UAS-Lopez.eljhay",
    "Sales Force": "uas-lopez.eljay@cict.com.ph",
    "ZOHO": "eljhay.lopez@uas2.com.ph",
    "BSS WEB": "uas-lopez.eljay@partner.convergeict.com",
    "EMAIL": "is.eljaylopez1@gmail.com",
    "BIRTHDAY": "1999-11-02",
    "CONTACT NO.": "09666096553",
    "ADDRESS": "Blk 5 Lot 14 Rockville Subdivision, Barangay Malpitic, City of San Fernando, Pamapanga"
  },
  {
    "id": 3,
    "NAME": "Maniago, Danzeil James",
    "TENCENT ID": "5242",
    "DATE HIRED": "2025-03-31",
    "PHONE NAME": "Danzeil",
    "NBS ID": "10148",
    "HEADSET SN": "2309410DU0522",
    "IBAS": "DAJMANIA",
    "DJANGO": "Damaniago@uas2.com.ph",
    "NT LOG IN": "UAS-Maniago.Danzeil",
    "Sales Force": "uas-danzeil.maniago@cict.com.ph",
    "ZOHO": "damaniago@uas2.com.ph",
    "BSS WEB": "uas-danzeil.maniago@partner.convergeict.com",
    "EMAIL": "denzeiljamesmaniago@gmail.com",
    "BIRTHDAY": "2003-01-16",
    "CONTACT NO.": "09630692546",
    "ADDRESS": "Blk.17 Lot.2, Brgy. Cristo Rey, Capas, Tarlac"
  },
  {
    "id": 4,
    "NAME": "Navarro, Jerome",
    "TENCENT ID": "5093",
    "DATE HIRED": "2025-03-03",
    "PHONE NAME": "KHALEE",
    "NBS ID": "9808",
    "HEADSET SN": "2309410DU0098",
    "IBAS": "NAVJEROM",
    "DJANGO": "je.navarro@uas2.com.ph",
    "NT LOG IN": "UAS-Navarro.Jerome",
    "Sales Force": "uas-jerome.navarro@cict.com.ph",
    "ZOHO": "je.navarro@uas2.com.ph",
    "BSS WEB": "uas-jerome.navarro@partner.convergeict.com",
    "EMAIL": "jeromen891@gmail.com",
    "BIRTHDAY": "1998-04-16",
    "CONTACT NO.": "09670696382",
    "ADDRESS": "1036, Baranggay Capaya 1, Angeles City, Pampanga"
  },
  {
    "id": 5,
    "NAME": "Paz, Ben Gerard",
    "TENCENT ID": "5038",
    "DATE HIRED": "2025-03-03",
    "PHONE NAME": "GIEH",
    "NBS ID": "9814",
    "HEADSET SN": "2309410DU0381",
    "IBAS": "PAZBENGE",
    "DJANGO": "bg.paz@uas2.com.ph",
    "NT LOG IN": "UAS-Paz.Ben",
    "Sales Force": "uas-ben.paz@cict.com.ph",
    "ZOHO": "bg.paz@uas2.com.ph",
    "BSS WEB": "uas-ben.paz@partner.convergeict.com",
    "EMAIL": "bengerardp@gmail.com",
    "BIRTHDAY": "1995-06-25",
    "CONTACT NO.": "09634269072",
    "ADDRESS": "Pulung Maragul, Angeles City"
  },
  {
    "id": 6,
    "NAME": "Waje, Avy",
    "TENCENT ID": "5115",
    "DATE HIRED": "2025-03-03",
    "PHONE NAME": "SCARLET",
    "NBS ID": "9828",
    "HEADSET SN": "2309410DU1246",
    "IBAS": "WAJAVYWA",
    "DJANGO": "a.waje@uas2.com.ph",
    "NT LOG IN": "UAS-Waje.Avy",
    "Sales Force": "uas-avy.waje@cict.com.ph",
    "ZOHO": "a.waje@uas2.com.ph",
    "BSS WEB": "uas-avy.waje@partner.convergeict.com",
    "EMAIL": "avywaje43@gmail.com",
    "BIRTHDAY": "2005-01-16",
    "CONTACT NO.": "09534367262",
    "ADDRESS": "0366 Purok 2, Brgy. Calzadang Bayu, Porac, Pampanga"
  },
  {
    "id": 7,
    "NAME": "Guevarra, James Rainielle",
    "TENCENT ID": "5291",
    "DATE HIRED": "2025-06-23",
    "PHONE NAME": "Rain",
    "NBS ID": "11412",
    "HEADSET SN": "",
    "IBAS": "JMSRNGVA",
    "DJANGO": "ja.guevarra@uas2.com.ph",
    "NT LOG IN": "UAS-Guevarra.JamesRa",
    "Sales Force": "uas-rain.guevarra@cict.com.ph",
    "ZOHO": "ja.guevarra@uas2.com.ph",
    "BSS WEB": "uas-rain.guevarra@partner.convergeict.com",
    "EMAIL": "jamesrainielle1423@gmail.com",
    "BIRTHDAY": "2006-08-31",
    "CONTACT NO.": "09480624706",
    "ADDRESS": "Blk cd Lot 2c phase 3, Sta. Lucia Rest., Brgy. San Isido, Magalang, Pampanga"
  },
  {
    "id": 8,
    "NAME": "Pare, Crisha Joy",
    "TENCENT ID": "5310",
    "DATE HIRED": "2025-06-23",
    "PHONE NAME": "Crisha",
    "NBS ID": "11368",
    "HEADSET SN": "",
    "IBAS": "CRISPARE",
    "DJANGO": "cr.pare@uas2.com.ph",
    "NT LOG IN": "UAS-Pare.Crishajoy",
    "Sales Force": "uas-crishajoy.pare@cict.com.ph",
    "ZOHO": "cr.pare@uas2.com.ph",
    "BSS WEB": "uas-crishajoy.pare@partner.convergeict.com",
    "EMAIL": "Crishapare@gmail.com",
    "BIRTHDAY": "2004-08-16",
    "CONTACT NO.": "09496274867",
    "ADDRESS": "3219 North Dang Bakal, Dau, Mabalacat City, Pampanga"
  },
  {
    "id": 9,
    "NAME": "Paraga, Elisa",
    "TENCENT ID": "5090",
    "DATE HIRED": "2025-04-28",
    "PHONE NAME": "Angel",
    "NBS ID": "10850",
    "HEADSET SN": "2309410DU0875",
    "IBAS": "RAGASELI",
    "DJANGO": "el.paragas@uas2.com.ph",
    "NT LOG IN": "UAS-paragas.elisallo",
    "Sales Force": "uas-elisa.paragas@cict.com.ph",
    "ZOHO": "el.paragas@uas2.com.ph",
    "BSS WEB": "uas-elisa.paragas@partner.convergeict.com",
    "EMAIL": "elp012581@gmail.com",
    "BIRTHDAY": "1981-01-25",
    "CONTACT NO.": "09760221814",
    "ADDRESS": "5016 Abacan, Malabanias, Angeles City, Pampanga"
  },
  {
    "id": 10,
    "NAME": "Cahuyong, Daveliet Jane",
    "TENCENT ID": "5726",
    "DATE HIRED": "2025-08-11",
    "PHONE NAME": "Devie",
    "NBS ID": "11518",
    "HEADSET SN": "",
    "IBAS": "DCAHUYO",
    "DJANGO": "d.cahuyong@uas2.com.ph",
    "NT LOG IN": "UAS-Cahuyong.Davelie",
    "Sales Force": "uas-dave.cahuyog@cict.com.ph",
    "ZOHO": "d.cahuyong@uas2.com.ph",
    "BSS WEB": "uas-dave.cahuyog@partner.convergeict.com",
    "EMAIL": "daveliethitosis@gmail.com",
    "BIRTHDAY": "2002-11-08",
    "CONTACT NO.": "09485518457",
    "ADDRESS": "Prk 6. Kadamay, Brgy. Cuayan, Angeles City, Pampanga"
  },
  {
    "id": 11,
    "NAME": "Quiambao, Allen",
    "TENCENT ID": "4995",
    "DATE HIRED": "2026-05-04",
    "PHONE NAME": "Noble",
    "NBS ID": "12468",
    "HEADSET SN": "",
    "IBAS": "ALQUIAMB",
    "DJANGO": "al.quiambao@uas2.com.ph",
    "NT LOG IN": "UAS-allen.quiambao",
    "Sales Force": "uas-allen.quiambao@cict.com.ph",
    "ZOHO": "al.quiambao@uas2.com.ph",
    "BSS WEB": "uas-allen.quiambao@partner.convergeict.com",
    "EMAIL": "allenquiambao298@gmail.com",
    "BIRTHDAY": "2008-02-09",
    "CONTACT NO.": "09978178943",
    "ADDRESS": "Blk37 Lot20, San Isidro Resettelment, Magalang, Pampanga"
  },
  {
    "id": 12,
    "NAME": "Reyes, Katherine",
    "TENCENT ID": "4996",
    "DATE HIRED": "2026-05-04",
    "PHONE NAME": "Kassel",
    "NBS ID": "12474",
    "HEADSET SN": "",
    "IBAS": "KAREYESE",
    "DJANGO": "ka.reyes@uas2.com.ph",
    "NT LOG IN": "UAS-katherine.reyes",
    "Sales Force": "uas-katherine.reyes@cict.com.ph",
    "ZOHO": "ka.reyes@uas2.com.ph",
    "BSS WEB": "uas-katherine.reyes@partner.convergeict.com",
    "EMAIL": "reyeskatherine093@gmail.com",
    "BIRTHDAY": "2026-09-19",
    "CONTACT NO.": "09614809467",
    "ADDRESS": "1624 Interior St. Brgy. Ninoy Aquino, Marisol, Angeles City, Pampanga"
  },
  {
    "id": 13,
    "NAME": "Salmero, Jeanel Ann",
    "TENCENT ID": "4997",
    "DATE HIRED": "2026-05-04",
    "PHONE NAME": "Rhett",
    "NBS ID": "12476",
    "HEADSET SN": "",
    "IBAS": "JESALMER",
    "DJANGO": "je.salmero@uas2.com.ph",
    "NT LOG IN": "UAS-jeanel.salmero",
    "Sales Force": "uas-jeanel.salmero@cict.com.ph",
    "ZOHO": "je.salmero@uas2.com.ph",
    "BSS WEB": "uas-jeanel.salmero@partner.convergeict.com",
    "EMAIL": "santosjeanel74@gmail.com",
    "BIRTHDAY": "2026-12-15",
    "CONTACT NO.": "09169205580",
    "ADDRESS": "5086 Juicy Fruit, Brgy Duquit, Mabalacat City, Pampanga"
  },
  {
    "id": 14,
    "NAME": "Sampaga, Marie Joy",
    "TENCENT ID": "4998",
    "DATE HIRED": "2026-05-04",
    "PHONE NAME": "Arhem",
    "NBS ID": "12478",
    "HEADSET SN": "",
    "IBAS": "MASAMPAG",
    "DJANGO": "ma.sampaga@uas2.com.ph",
    "NT LOG IN": "UAS-marie.sampaga",
    "Sales Force": "uas-marie.sampaga@cict.com.ph",
    "ZOHO": "ma.sampaga@uas2.com.ph",
    "BSS WEB": "uas-marie.sampaga@partner.convergeict.com",
    "EMAIL": "lacsonmariejoy@gmail.com",
    "BIRTHDAY": "1997-11-15",
    "CONTACT NO.": "09368001203",
    "ADDRESS": "782 Kadenang Kristal, Sapang Biabas, Dau, Mabalacat, Pampanga"
  },
  {
    "id": 15,
    "NAME": "Arcilla, Azarias",
    "TENCENT ID": "4909",
    "DATE HIRED": "2026-05-04",
    "PHONE NAME": "Chance",
    "NBS ID": "12352",
    "HEADSET SN": "J0XL4V",
    "IBAS": "AZARARCI",
    "DJANGO": "a.azarias@uas2.com.ph",
    "NT LOG IN": "UAS-Arcilla.Azarias",
    "Sales Force": "uas-azarias.arcilla@cict.com.ph",
    "ZOHO": "a.azarias@uas2.com.ph",
    "BSS WEB": "uas-azarias.arcilla@partner.convergeict.com",
    "EMAIL": "chancearcilla5100@gmail.com",
    "BIRTHDAY": "2006-05-01",
    "CONTACT NO.": "09122974939",
    "ADDRESS": "989 Chico St. San Francisco, Mabalacat City, Pampanga"
  },
  {
    "id": 16,
    "NAME": "Bigornia, Shenhel",
    "TENCENT ID": "4910",
    "DATE HIRED": "2026-05-04",
    "PHONE NAME": "Daiji",
    "NBS ID": "12360",
    "HEADSET SN": "J0XJP0",
    "IBAS": "SHENBIGO",
    "DJANGO": "s.bigornia@uas2.com.ph",
    "NT LOG IN": "UAS-Bigornia.Shenhel",
    "Sales Force": "uas-shenhel.bigornia@cict.com.ph",
    "ZOHO": "s.bigornia@uas2.com.ph",
    "BSS WEB": "uas-shenhel.bigornia@partner.convergeict.com",
    "EMAIL": "bshenhel@gmail.com",
    "BIRTHDAY": "2002-02-19",
    "CONTACT NO.": "09941644309",
    "ADDRESS": "26-18B Malaysia St. Don Bonifacio, Pulung Maragul, Balibago, Angeles City"
  },
  {
    "id": 17,
    "NAME": "Cano, Regina Carla",
    "TENCENT ID": "4911",
    "DATE HIRED": "2026-05-04",
    "PHONE NAME": "Rachel",
    "NBS ID": "12378",
    "HEADSET SN": "J0XJP3",
    "IBAS": "RCARCANO",
    "DJANGO": "r.cano@uas2.com.ph",
    "NT LOG IN": "UAS-Cano.Regina",
    "Sales Force": "uas-regina.cano@cict.com.ph",
    "ZOHO": "r.cano@uas2.com.ph",
    "BSS WEB": "uas-regina.cano@partner.convergeict.com",
    "EMAIL": "carlacano111517@gmail.com",
    "BIRTHDAY": "1998-11-11",
    "CONTACT NO.": "09069331284",
    "ADDRESS": "05 Mabini St. San Nicolas, Angeles City, Pampanga"
  },
  {
    "id": 18,
    "NAME": "Ocampo, Joana Marie",
    "TENCENT ID": "5269",
    "DATE HIRED": "2026-05-18",
    "PHONE NAME": "Tams",
    "NBS ID": "12578",
    "HEADSET SN": "JOXKVR",
    "IBAS": "JNMRIMCP",
    "DJANGO": "jo.ocampo@uas2.com.ph",
    "NT LOG IN": "UAS-Ocampo.joana",
    "Sales Force": "uas-joana.ocampo@cict.com.ph",
    "ZOHO": "jo.ocampo@uas2.com.p",
    "BSS WEB": "uas-joana.ocampo@partner.convergeict.com",
    "EMAIL": "omanarang30@gmail.com",
    "BIRTHDAY": "1992-08-30",
    "CONTACT NO.": "09491233865",
    "ADDRESS": "49 Purok 1, San Pedro 2, Magalang, Pampanga"
  },
  {
    "id": 19,
    "NAME": "Pangilinan, Princess",
    "TENCENT ID": "5271",
    "DATE HIRED": "2026-05-18",
    "PHONE NAME": "Peach",
    "NBS ID": "12580",
    "HEADSET SN": "JOXKVN",
    "IBAS": "PRNSPGNN",
    "DJANGO": "pr.pangilinan@uas2.com.ph",
    "NT LOG IN": "UAS-Pangilinan.Princ",
    "Sales Force": "uas-prin.pangilinan@cict.com.ph",
    "ZOHO": "pr.pangilinan@uas2.com.ph",
    "BSS WEB": "uas-prin.pangilinan@partner.convergeict.com",
    "EMAIL": "pangilinanp387@gmail.com",
    "BIRTHDAY": "2006-12-19",
    "CONTACT NO.": "09707673225",
    "ADDRESS": "31 D Yakal St. Aguas Subdivision, Manibaug Paralaya, Porac Pampanga"
  }
]
MIGRATE_OT_LOGS = [
  {
    "id": 1,
    "agent_id": 15,
    "ot_date": "2026-09-02",
    "ot_type": "REGULAR",
    "hours": 2.0,
    "remarks": "Imported from September sheet - Sept 2",
    "created_at": "2026-09-07 17:38:45"
  },
  {
    "id": 2,
    "agent_id": 15,
    "ot_date": "2026-09-04",
    "ot_type": "REGULAR",
    "hours": 1.0,
    "remarks": "Imported from September sheet - Sept 4",
    "created_at": "2026-09-07 17:38:45"
  },
  {
    "id": 3,
    "agent_id": 15,
    "ot_date": "2026-09-05",
    "ot_type": "RDOT",
    "hours": 10.0,
    "remarks": "Imported from September sheet - Sept 5",
    "created_at": "2026-09-07 17:38:45"
  },
  {
    "id": 4,
    "agent_id": 1,
    "ot_date": "2026-09-01",
    "ot_type": "REGULAR",
    "hours": 3.0,
    "remarks": "Imported from September sheet - Sept 1",
    "created_at": "2026-09-07 17:38:45"
  },
  {
    "id": 5,
    "agent_id": 1,
    "ot_date": "2026-09-02",
    "ot_type": "REGULAR",
    "hours": 1.0,
    "remarks": "Imported from September sheet - Sept 2",
    "created_at": "2026-09-07 17:38:45"
  },
  {
    "id": 6,
    "agent_id": 1,
    "ot_date": "2026-09-03",
    "ot_type": "REGULAR",
    "hours": 2.0,
    "remarks": "Imported from September sheet - Sept 3",
    "created_at": "2026-09-07 17:38:45"
  },
  {
    "id": 7,
    "agent_id": 1,
    "ot_date": "2026-09-04",
    "ot_type": "REGULAR",
    "hours": 1.0,
    "remarks": "Imported from September sheet - Sept 4",
    "created_at": "2026-09-07 17:38:45"
  },
  {
    "id": 8,
    "agent_id": 1,
    "ot_date": "2026-09-05",
    "ot_type": "RDOT",
    "hours": 10.0,
    "remarks": "Imported from September sheet - Sept 5",
    "created_at": "2026-09-07 17:38:45"
  },
  {
    "id": 9,
    "agent_id": 9,
    "ot_date": "2026-09-01",
    "ot_type": "REGULAR",
    "hours": 1.0,
    "remarks": "Imported from September sheet - Sept 1",
    "created_at": "2026-09-07 17:38:45"
  },
  {
    "id": 10,
    "agent_id": 9,
    "ot_date": "2026-09-03",
    "ot_type": "REGULAR",
    "hours": 1.0,
    "remarks": "Imported from September sheet - Sept 3",
    "created_at": "2026-09-07 17:38:45"
  },
  {
    "id": 11,
    "agent_id": 9,
    "ot_date": "2026-09-05",
    "ot_type": "RDOT",
    "hours": 10.0,
    "remarks": "Imported from September sheet - Sept 5",
    "created_at": "2026-09-07 17:38:45"
  },
  {
    "id": 12,
    "agent_id": 8,
    "ot_date": "2026-09-01",
    "ot_type": "REGULAR",
    "hours": 1.0,
    "remarks": "Imported from September sheet - Sept 1",
    "created_at": "2026-09-07 17:38:45"
  },
  {
    "id": 13,
    "agent_id": 8,
    "ot_date": "2026-09-02",
    "ot_type": "REGULAR",
    "hours": 1.0,
    "remarks": "Imported from September sheet - Sept 2",
    "created_at": "2026-09-07 17:38:45"
  },
  {
    "id": 14,
    "agent_id": 8,
    "ot_date": "2026-09-03",
    "ot_type": "REGULAR",
    "hours": 2.0,
    "remarks": "Imported from September sheet - Sept 3",
    "created_at": "2026-09-07 17:38:45"
  },
  {
    "id": 15,
    "agent_id": 8,
    "ot_date": "2026-09-05",
    "ot_type": "RDOT",
    "hours": 5.0,
    "remarks": "Imported from September sheet - Sept 5",
    "created_at": "2026-09-07 17:38:45"
  },
  {
    "id": 16,
    "agent_id": 5,
    "ot_date": "2026-09-01",
    "ot_type": "REGULAR",
    "hours": 2.0,
    "remarks": "Imported from September sheet - Sept 1",
    "created_at": "2026-09-07 17:38:45"
  },
  {
    "id": 17,
    "agent_id": 5,
    "ot_date": "2026-09-02",
    "ot_type": "REGULAR",
    "hours": 1.0,
    "remarks": "Imported from September sheet - Sept 2",
    "created_at": "2026-09-07 17:38:45"
  },
  {
    "id": 18,
    "agent_id": 5,
    "ot_date": "2026-09-03",
    "ot_type": "REGULAR",
    "hours": 1.0,
    "remarks": "Imported from September sheet - Sept 3",
    "created_at": "2026-09-07 17:38:45"
  },
  {
    "id": 19,
    "agent_id": 5,
    "ot_date": "2026-09-04",
    "ot_type": "REGULAR",
    "hours": 3.0,
    "remarks": "Imported from September sheet - Sept 4",
    "created_at": "2026-09-07 17:38:45"
  },
  {
    "id": 20,
    "agent_id": 5,
    "ot_date": "2026-09-05",
    "ot_type": "RDOT",
    "hours": 5.0,
    "remarks": "Imported from September sheet - Sept 5",
    "created_at": "2026-09-07 17:38:45"
  },
  {
    "id": 21,
    "agent_id": 11,
    "ot_date": "2026-09-01",
    "ot_type": "REGULAR",
    "hours": 1.0,
    "remarks": "Imported from September sheet - Sept 1",
    "created_at": "2026-09-07 17:38:45"
  },
  {
    "id": 22,
    "agent_id": 11,
    "ot_date": "2026-09-02",
    "ot_type": "REGULAR",
    "hours": 1.0,
    "remarks": "Imported from September sheet - Sept 2",
    "created_at": "2026-09-07 17:38:45"
  },
  {
    "id": 23,
    "agent_id": 12,
    "ot_date": "2026-09-01",
    "ot_type": "REGULAR",
    "hours": 1.0,
    "remarks": "Imported from September sheet - Sept 1",
    "created_at": "2026-09-07 17:38:45"
  },
  {
    "id": 24,
    "agent_id": 6,
    "ot_date": "2026-09-05",
    "ot_type": "RDOT",
    "hours": 7.0,
    "remarks": "Imported from September sheet - Sept 5",
    "created_at": "2026-09-07 17:38:45"
  },
  {
    "id": 25,
    "agent_id": 18,
    "ot_date": "2026-09-01",
    "ot_type": "REGULAR",
    "hours": 2.0,
    "remarks": "Imported from September sheet - Sept 1",
    "created_at": "2026-09-07 17:38:45"
  },
  {
    "id": 26,
    "agent_id": 18,
    "ot_date": "2026-09-02",
    "ot_type": "REGULAR",
    "hours": 1.0,
    "remarks": "Imported from September sheet - Sept 2",
    "created_at": "2026-09-07 17:38:45"
  },
  {
    "id": 27,
    "agent_id": 19,
    "ot_date": "2026-09-01",
    "ot_type": "REGULAR",
    "hours": 1.0,
    "remarks": "Imported from September sheet - Sept 1",
    "created_at": "2026-09-07 17:38:45"
  },
  {
    "id": 28,
    "agent_id": 2,
    "ot_date": "2026-09-04",
    "ot_type": "REGULAR",
    "hours": 1.0,
    "remarks": "Imported from September sheet - Sept 4",
    "created_at": "2026-09-07 17:38:45"
  },
  {
    "id": 29,
    "agent_id": 3,
    "ot_date": "2026-09-04",
    "ot_type": "REGULAR",
    "hours": 1.0,
    "remarks": "Imported from September sheet - Sept 4",
    "created_at": "2026-09-07 17:38:45"
  },
  {
    "id": 30,
    "agent_id": 4,
    "ot_date": "2026-09-01",
    "ot_type": "REGULAR",
    "hours": 1.0,
    "remarks": "Imported from September sheet - Sept 1",
    "created_at": "2026-09-07 17:38:45"
  }
]


@app.route("/dashboard")
def dashboard():
    agents = get_all_agents()
    total = len(agents)
    
    # calc metrics
    from collections import Counter, defaultdict
    from datetime import datetime, timedelta
    now = datetime.now()
    this_month = now.strftime("%Y-%m")
    
    ot_total = 0
    loss_total = 0
    ot_by_agent = {}
    loss_by_agent = {}
    ot_daily = defaultdict(float)
    new_hires = 0
    
    for a in agents:
        aid = a['id']
        # check date hired
        dh = a.get('DATE HIRED','')
        if this_month in str(dh) or now.strftime("%Y-%m") in str(dh) or str(now.year) in str(dh) and str(now.month) in str(dh):
            # simple: if hired 2026-05 etc
            pass
        # OT
        ot_sum = 0
        for d in db.collection('agents').document(aid).collection('ot_logs').stream():
            h = float(d.to_dict().get('hours',0) or 0)
            ot_sum+=h
            ot_total+=h
            dt = d.to_dict().get('ot_date','')
            if dt:
                ot_daily[dt]+=h
        ot_by_agent[a.get('NAME','')] = ot_sum
        
        # LOSS (if exists)
        loss_sum = 0
        try:
            for d in db.collection('agents').document(aid).collection('loss_logs').stream():
                h = float(d.to_dict().get('hours',0) or 0)
                loss_sum+=h
                loss_total+=h
        except:
            pass
        loss_by_agent[a.get('NAME','')] = loss_sum
        
        # new hire check (last 30 days)
        try:
            if a.get('DATE HIRED'):
                hired = datetime.strptime(str(a.get('DATE HIRED'))[:10], "%Y-%m-%d")
                if (now - hired).days <= 30:
                    new_hires+=1
        except:
            pass
    
    # attendance = 100 - (loss_total / (total*8*22) *100) simplified
    attendance_rate = 100
    if total>0:
        possible_hours = total * 8 * 22
        if possible_hours>0:
            attendance_rate = max(0, 100 - (loss_total / possible_hours * 100))
    
    top_ot = sorted(ot_by_agent.items(), key=lambda x: x[1], reverse=True)[:5]
    top_loss = sorted(loss_by_agent.items(), key=lambda x: x[1], reverse=True)[:5]
    
    # prepare chart data
    dates = sorted(ot_daily.keys())[-7:]  # last 7 dates with OT
    ot_values = [ot_daily[d] for d in dates]
    
    content = f"""
    <div class="d-flex justify-content-between align-items-center mb-4">
      <div><h4 class="fw-bold mb-0">Command Center</h4><small class="text-muted">Call Center KPI - Team Shine M9 | {now.strftime('%B %Y')}</small></div>
      <div class="d-flex gap-2"><span class="badge bg-success">LIVE FIREBASE</span><span class="badge bg-dark border">{total} Agents</span></div>
    </div>
    
    <div class="row g-3 mb-4">
      <div class="col-6 col-lg-3"><div class="kpi-card" style="--accent:#fbbf24"><div class="d-flex justify-content-between"><div><div class="text-muted" style="font-size:11px">TOTAL HEADCOUNT</div><div class="fs-3 fw-bold">{total}</div><small class="trend-up"><i class="bi bi-arrow-up"></i> {new_hires} new hires (30d)</small></div><div class="kpi-icon" style="background:#fbbf241a;color:#fbbf24"><i class="bi bi-people-fill"></i></div></div></div></div>
      <div class="col-6 col-lg-3"><div class="kpi-card" style="--accent:#22c55e"><div class="d-flex justify-content-between"><div><div class="text-muted" style="font-size:11px">ATTENDANCE RATE</div><div class="fs-3 fw-bold">{attendance_rate:.1f}%</div><small class="{'trend-down' if loss_total>10 else 'trend-up'}">{loss_total:.1f}h LOSS this month</small></div><div class="kpi-icon" style="background:#22c55e1a;color:#22c55e"><i class="bi bi-check-circle"></i></div></div></div></div>
      <div class="col-6 col-lg-3"><div class="kpi-card" style="--accent:#3b82f6"><div class="d-flex justify-content-between"><div><div class="text-muted" style="font-size:11px">TOTAL OT HOURS</div><div class="fs-3 fw-bold">{ot_total:.1f}h</div><small class="text-muted">{len(dates)} days with OT</small></div><div class="kpi-icon" style="background:#3b82f61a;color:#3b82f6"><i class="bi bi-clock-history"></i></div></div></div></div>
      <div class="col-6 col-lg-3"><div class="kpi-card" style="--accent:#ef4444"><div class="d-flex justify-content-between"><div><div class="text-muted" style="font-size:11px">SHRINKAGE / LOSS</div><div class="fs-3 fw-bold">{loss_total:.1f}h</div><small class="trend-down">{(loss_total/(ot_total+1)*100):.0f}% vs OT</small></div><div class="kpi-icon" style="background:#ef44441a;color:#ef4444"><i class="bi bi-exclamation-triangle"></i></div></div></div></div>
    </div>
    
    <div class="row g-3 mb-4">
      <div class="col-lg-8"><div class="card p-3"><h6 class="fw-bold mb-3"><i class="bi bi-graph-up text-warning"></i> OT Trend (Last 7 Days)</h6><div class="chart-container"><canvas id="otChart"></canvas></div></div></div>
      <div class="col-lg-4"><div class="card p-3 h-100"><h6 class="fw-bold mb-3"><i class="bi bi-pie-chart text-warning"></i> Workload Distribution</h6><div class="chart-container"><canvas id="distChart"></canvas></div>
      <div class="mt-3 small text-muted">Call Center Standard: OT should be <10% of total hours. Current OT ratio helps track burnout risk.</div>
      </div></div>
    </div>
    
    <div class="row g-3 mb-4">
      <div class="col-lg-6"><div class="card p-3"><h6 class="fw-bold">🏆 Top 5 OT - Overtime Heroes</h6><p class="text-muted small">Monitor for burnout - best for incentives</p><div class="table-responsive"><table class="table table-sm"><thead><tr><th>Agent</th><th>Hours</th><th>Risk</th></tr></thead><tbody>
        {''.join([f"<tr><td>{esc(name)}</td><td><span class='badge bg-warning text-dark'>{h:.1f}h</span></td><td>{'<span class=text-danger>High</span>' if h>20 else '<span class=text-warning>Medium</span>' if h>10 else '<span class=text-success>OK</span>'}</td></tr>" for name,h in top_ot])}
      </tbody></table></div></div></div>
      <div class="col-lg-6"><div class="card p-3"><h6 class="fw-bold">⚠️ Top 5 LOSS - Attendance Coaching Needed</h6><p class="text-muted small">For 1-on-1 coaching & NTE tracking</p><div class="table-responsive"><table class="table table-sm"><thead><tr><th>Agent</th><th>Loss Hours</th><th>Action</th></tr></thead><tbody>
        {''.join([f"<tr><td>{esc(name)}</td><td><span class='badge bg-danger'>{h:.1f}h</span></td><td>{'Coaching' if h>0 else 'Good'}</td></tr>" for name,h in top_loss]) if any(h>0 for _,h in top_loss) else "<tr><td colspan=3 class='text-center text-success'>No LOSS - Excellent attendance!</td></tr>"}
      </tbody></table></div></div></div>
    </div>
    
    <div class="card p-3"><h6 class="fw-bold"><i class="bi bi-lightbulb text-warning"></i> Call Center Manager Recommendations</h6>
    <div class="row g-2 mt-2">
      <div class="col-md-4"><div class="detail-card"><strong>For BPO KPI:</strong><br><small>• AHT Target: Track via ZOHO/BSS<br>• CSAT: Integrate survey<br>• Attendance Goal: >95% (You: {attendance_rate:.1f}%)<br>• OT Limit: Max 20h/month/agent</small></div></div>
      <div class="col-md-4"><div class="detail-card"><strong>Suggested Next Features:</strong><br><small>• Daily Scorecard per agent<br>• Auto NTE generator for LOSS >3<br>• Birthday & Tenure alerts<br>• Shift schedule vs OT validation</small></div></div>
      <div class="col-md-4"><div class="detail-card"><strong>Current Health:</strong><br><small>• Total HC: {total}<br>• Net OT: {ot_total-loss_total:.1f}h<br>• Burnout Risk: {len([h for _,h in top_ot if h>20])} agents >20h OT<br>• Coaching Needed: {len([h for _,h in top_loss if h>0])} agents</small></div></div>
    </div></div>
    
    <script>
    const otCtx = document.getElementById('otChart');
    new Chart(otCtx, {{
      type: 'bar',
      data: {{
        labels: {json.dumps(dates)},
        datasets: [{{label: 'OT Hours', data: {json.dumps(ot_values)}, backgroundColor: '#fbbf24', borderRadius: 8}}]
      }},
      options: {{responsive:true, maintainAspectRatio:false, plugins:{{legend:{{display:false}}}}, scales:{{y:{{beginAtZero:true, grid:{{color:'#1e293b'}}}}, x:{{grid:{{display:false}}}}}} }}
    }});
    const distCtx = document.getElementById('distChart');
    new Chart(distCtx, {{
      type: 'doughnut',
      data: {{
        labels: ['OT Hours', 'Loss Hours', 'Regular'],
        datasets: [{{data: [{ot_total}, {loss_total}, {max(0, total*176 - ot_total - loss_total)}], backgroundColor: ['#fbbf24','#ef4444','#1e293b']}}]
      }},
      options: {{responsive:true, maintainAspectRatio:false, plugins:{{legend:{{position:'bottom', labels:{{color:'#94a3b8'}}}}}}}}
    }});
    </script>
    """
    return render_page(content, total, active='dash')

@app.route("/migrate")
def migrate():
    # safety: only run if DB empty
    existing = list(db.collection('agents').limit(1).stream())
    if existing:
        return f"<h2>Already migrated - {len(list(db.collection('agents').stream()))} agents in Firebase. Delete them first if you want to re-migrate.</h2><a href='/'>Back to Home</a>"
    
    count_a = 0
    count_ot = 0
    for ag in MIGRATE_AGENTS:
        old_id = str(ag.pop('id'))
        clean = {k: ('' if v is None else str(v)) for k,v in ag.items()}
        db.collection('agents').document(old_id).set(clean)
        count_a+=1
    
    for ot in MIGRATE_OT_LOGS:
        agent_id = str(ot['agent_id'])
        doc = {
            'ot_date': str(ot['ot_date']),
            'ot_type': str(ot['ot_type']),
            'hours': float(ot['hours'] or 0),
            'remarks': str(ot.get('remarks','')),
            'created_at': str(ot.get('created_at',''))
        }
        db.collection('agents').document(agent_id).collection('ot_logs').add(doc)
        count_ot+=1
    
    return f"<h1>Migration DONE!</h1><p>Imported {count_a} agents and {count_ot} OT logs to Firebase.</p><a href='/' style='background:#fbbf24;padding:10px 20px;border-radius:10px;text-decoration:none;color:#000;font-weight:bold'>Go to TEAM SHINE M9</a>"

@app.route("/migrate_status")
def migrate_status():
    total = len(list(db.collection('agents').stream()))
    return f"{total} agents in Firebase"

if __name__=="__main__":
    port=int(os.environ.get("PORT",5000))
    app.run(host="0.0.0.0",port=port)
