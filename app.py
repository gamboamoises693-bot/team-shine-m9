
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
<title>TEAM SHINE M9 - Firebase</title>
<style>
body{background:#080c14;color:#e2e8f0;font-family:system-ui}
.navbar{background:#0f172a!important;border-bottom:1px solid #1e293b}
.card{background:#111827!important;border:1px solid #1f2937!important;border-radius:20px!important}
.table{color:#e2e8f0!important;margin-bottom:0!important}
.table thead th{background:#0f172a!important;color:#fbbf24!important;border-bottom:2px solid #fbbf24!important;font-size:11px!important;text-transform:uppercase!important;padding:14px 12px!important;font-weight:800!important}
.table tbody td{background:#111827!important;border-color:#1f2937!important;padding:14px 12px!important;color:#e2e8f0!important}
.table tbody tr{background:#111827!important}
.table tbody tr:nth-child(even){background:#0f172a!important}
.table tbody tr:nth-child(even) td{background:#0f172a!important}
.badge-id{background:#0f172a;border:1px solid #334155;color:#94a3b8;border-radius:8px;padding:6px 10px}
.btn-exec{background:linear-gradient(135deg,#fbbf24,#f59e0b);color:#0f172a;font-weight:800;border:none;border-radius:12px;padding:8px 18px}
.search-box{background:#0f172a;border:1px solid #1f2937;color:white;border-radius:12px;padding:12px}
.detail-card{background:#0f172a;border:1px solid #1e293b;border-radius:14px;padding:14px;height:100%}
.field-label{color:#64748b;font-size:10px;text-transform:uppercase;font-weight:700;margin-bottom:4px}
.field-value{color:#f1f5f9;font-weight:600;font-size:13px;word-break:break-word;white-space:normal}
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
.chart-container{position:relative;height:350px!important;width:100%!important}
.chart-container-small{position:relative;height:220px!important;width:100%!important;display:flex;align-items:center;justify-content:center}
.chart-container-top10{position:relative;height:300px!important;width:100%!important}
@media (max-width: 992px){.desktop-grid{grid-template-columns:1fr!important}.agent-sidebar{position:static!important}.ot-loss-grid{grid-template-columns:1fr!important}.chart-container{height:300px!important}}
</style></head><body>
<nav class="navbar navbar-dark p-3 sticky-top"><div class="container-fluid d-flex justify-content-between flex-wrap gap-2">
<a class="navbar-brand fw-bold" href="/"><i class="bi bi-lightning-charge-fill text-warning"></i> TEAM SHINE M9 <span style="font-size:10px" class="badge bg-warning text-dark">FIREBASE</span></a>
<div class="d-flex gap-2"><a href="/export_csv" class="btn btn-sm btn-outline-warning" style="border-radius:10px"><i class="bi bi-download"></i> CSV</a><a href="/add" class="btn btn-sm btn-warning fw-bold" style="border-radius:10px;color:#0f172a">+ Add Agent</a></div>
</div></nav><div class="container-fluid p-3 p-md-4">
__CONTENT__
</div></body></html>"""

def render_page(content, total, refresh_secs=None):
    refresh = f'<meta http-equiv="refresh" content="{refresh_secs}">' if refresh_secs else ''
    html_page = BASE_HTML.replace("__REFRESH__", refresh).replace("__CONTENT__", content)
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
    return render_page(content, 0)

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
    return render_page(content, 0)

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

if __name__=="__main__":
    port=int(os.environ.get("PORT",5000))
    app.run(host="0.0.0.0",port=port)
