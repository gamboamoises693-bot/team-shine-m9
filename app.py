
import os, json
from flask import Flask, request, redirect
from datetime import datetime
app = Flask(__name__)
try:
    import firebase_admin
    from firebase_admin import credentials
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
except:
    db_root = None

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

def get_ot(agent_id):
    logs = db_root.child("ot_logs").get() or {}
    result=[]
    if isinstance(logs, dict):
        for lid, v in logs.items():
            if not isinstance(v, dict): continue
            if str(v.get("agent_id"))==str(agent_id):
                v["log_id"]=lid
                result.append(v)
    return result

def calc(logs):
    normal=sum(float(l.get("hours",0)) for l in logs if l.get("type")=="NORMAL_OT")
    restday=sum(float(l.get("hours",0)) for l in logs if l.get("type")=="RESTDAY_OT")
    loss=sum(float(l.get("hours",0)) for l in logs if l.get("type")=="LOSS")
    return normal,restday,normal+restday,loss,(normal+restday-loss)

BASE1 = """<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1">
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
<link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.0/font/bootstrap-icons.css" rel="stylesheet">
<style>
body{background:#0b1120;color:#f1f5f9}
.card-dark{background:#151e32;border:1px solid #1e293b;border-radius:20px;padding:16px}
.kpi{padding:14px;border-radius:14px;background:#151e32;border:1px solid #1e293b;text-align:center}
.label{font-size:11px;color:#94a3b8;text-transform:uppercase;letter-spacing:.5px}
.val{color:#ffffff;font-weight:700}
.val-big{font-size:26px;font-weight:800}
.avatar{width:90px;height:90px;background:linear-gradient(135deg,#fbbf24,#f59e0b);border-radius:18px;display:flex;align-items:center;justify-content:center;font-size:40px;font-weight:900;color:#111827;margin:auto}
.table thead th{background:#0f172a!important;color:#fbbf24!important;font-size:11px}
.table tbody td{background:#151e32!important;border-color:#1e293b!important;color:#e2e8f0!important}
input,select{background:#0f172a!important;color:#f1f5f9!important;border:1px solid #334155!important}
.card-ot{border:1px solid #22c55e!important;background:linear-gradient(135deg,#151e32,#0f172a)}
.card-rdot{border:1px solid #3b82f6!important;background:linear-gradient(135deg,#151e32,#0f172a)}
.card-loss{border:1px solid #ef4444!important;background:linear-gradient(135deg,#151e32,#1a1010)}
.btn-ot{background:#22c55e;color:white;font-weight:700;border:none}
.btn-rdot{background:#3b82f6;color:white;font-weight:700;border:none}
.btn-loss{background:#ef4444;color:white;font-weight:700;border:none}
</style></head><body>
<nav class="navbar p-3" style="background:#0f172a;border-bottom:1px solid #1e293b"><div class="container-fluid">
<a class="navbar-brand fw-bold text-light" href="/">TEAM SHINE M9 <small style="color:#94a3b8;font-size:10px">NORMAL + RD OT + LOSS</small></a>
<div><span class="badge bg-warning text-dark">19 AGENTS</span> <a href="/" class="btn btn-sm btn-outline-light ms-2">Agents</a></div>
</div></nav><div class="container-fluid p-3" style="max-width:1000px;margin:auto">"""

BASE2 = "</div></body></html>"

def page(c):
    return BASE1 + c + BASE2

@app.route("/")
def home():
    agents=get_all()
    rows=""
    for a in agents:
        logs=get_ot(a.get("id"))
        n,r,tot,loss,net=calc(logs)
        rows+="<tr><td>"+str(a.get("id"))+"</td><td><a href='/view/"+str(a.get("id"))+"' style='color:white;text-decoration:none'><b>"+str(a.get("NAME",""))+"</b><br><small style='color:#94a3b8'>"+str(a.get("TENCENT_ID",""))+" | N:"+str(n)+" R:"+str(r)+" L:"+str(loss)+" NET:"+str(net)+"</small></a></td><td><a href='/view/"+str(a.get("id"))+"' class='btn btn-sm btn-warning'>View</a></td></tr>"
    return page("<h5 style='color:white'>All Agents ("+str(len(agents))+") - OT Monitoring</h5><div class='card-dark mt-3'><div class='table-responsive'><table class='table'><thead><tr><th>ID</th><th>AGENT - N:Normal R:Restday L:Loss</th><th></th></tr></thead><tbody>"+rows+"</tbody></table></div></div>")

@app.route("/view/<aid>")
def view(aid):
    data=None
    for a in get_all():
        if str(a.get("id"))==str(aid):
            data=a
            break
    if not data:
        data={}
    logs=get_ot(aid)
    n,r,tot,loss,net=calc(logs)
    log_rows=""
    for l in sorted(logs, key=lambda x: x.get("date",""), reverse=True):
        col="#22c55e" if l.get("type")=="NORMAL_OT" else "#3b82f6" if l.get("type")=="RESTDAY_OT" else "#ef4444"
        icon="bi-sun" if l.get("type")=="NORMAL_OT" else "bi-moon-stars" if l.get("type")=="RESTDAY_OT" else "bi-exclamation-triangle"
        log_rows+="<tr><td style='color:#cbd5e1'>"+str(l.get("date",""))+"</td><td><i class='bi "+icon+"' style='color:"+col+"'></i> <span style='color:"+col+";font-weight:700'>"+str(l.get("type")).replace("_"," ")+"</span></td><td style='color:white;font-weight:700'>"+str(l.get("hours"))+"h</td><td style='color:#94a3b8'>"+str(l.get("reason",""))+"</td><td><a href='/delete_log/"+str(aid)+"/"+str(l.get("log_id"))+"' class='btn btn-sm btn-outline-danger' style='font-size:10px'>X</a></td></tr>"
    if not log_rows:
        log_rows="<tr><td colspan=5 style='color:#64748b;text-align:center'>No logs yet - add OT or Loss below</td></tr>"
    initial=str(data.get("NAME","?"))[:1]
    html="<a href='/' class='btn btn-sm btn-outline-light mb-3'><i class='bi bi-arrow-left'></i> Back Dashboard</a>"
    html+="<div class='card-dark'>"
    html+="<div class='text-center'><div class='avatar'>"+initial+"</div><h4 style='color:white;margin-top:12px'>"+str(data.get("NAME",""))+"</h4><small style='color:#94a3b8'>"+str(data.get("TENCENT_ID",""))+" • ID:"+str(aid)+"</small></div>"
    html+="<div class='row g-2 mt-3'>"
    html+="<div class='col-4'><div class='kpi'><div class='label'>NORMAL OT</div><div class='val-big' style='color:#22c55e'>"+str(n)+"h</div></div></div>"
    html+="<div class='col-4'><div class='kpi'><div class='label'>RESTDAY OT</div><div class='val-big' style='color:#3b82f6'>"+str(r)+"h</div></div></div>"
    html+="<div class='col-4'><div class='kpi'><div class='label'>LOSS HRS</div><div class='val-big' style='color:#ef4444'>"+str(loss)+"h</div></div></div>"
    html+="<div class='col-6'><div class='kpi'><div class='label'>TOTAL OT (N+RD)</div><div class='val-big' style='color:#22c55e'>"+str(tot)+"h</div><small style='color:#94a3b8'>N:"+str(n)+" + RD:"+str(r)+"</small></div></div>"
    html+="<div class='col-6'><div class='kpi' style='border:1px solid #fbbf24'><div class='label'>NET (OT-LOSS)</div><div class='val-big' style='color:#fbbf24'>+"+str(net)+"h</div></div></div>"
    html+="</div>"
    # OT Input UI - 2 columns: Normal+Restday vs Loss
    html+="<div class='row g-3 mt-4'>"
    # Normal OT Card
    html+="<div class='col-12 col-md-6'><div class='card-dark card-ot'>"
    html+="<h6 style='color:#22c55e'><i class='bi bi-sun-fill'></i> Add NORMAL OT</h6>"
    html+="<form method='POST' action='/add_ot/"+str(aid)+"' class='row g-2 mt-1'>"
    html+="<input type='hidden' name='type' value='NORMAL_OT'>"
    html+="<div class='col-5'><label class='label'>Hours</label><input name='hours' type='number' step='0.5' class='form-control form-control-sm' placeholder='2.5' required></div>"
    html+="<div class='col-7'><label class='label'>Date</label><input name='date' type='date' class='form-control form-control-sm' value='"+datetime.now().strftime('%Y-%m-%d')+"'></div>"
    html+="<div class='col-12'><label class='label'>Reason</label><input name='reason' class='form-control form-control-sm' placeholder='Extended shift, etc'></div>"
    html+="<div class='col-12'><button class='btn btn-ot w-100 mt-1'><i class='bi bi-plus'></i> Add Normal OT</button></div>"
    html+="</form></div></div>"
    # Restday OT Card
    html+="<div class='col-12 col-md-6'><div class='card-dark card-rdot'>"
    html+="<h6 style='color:#3b82f6'><i class='bi bi-moon-stars-fill'></i> Add RESTDAY OT</h6>"
    html+="<form method='POST' action='/add_ot/"+str(aid)+"' class='row g-2 mt-1'>"
    html+="<input type='hidden' name='type' value='RESTDAY_OT'>"
    html+="<div class='col-5'><label class='label'>Hours</label><input name='hours' type='number' step='0.5' class='form-control form-control-sm' placeholder='8' required></div>"
    html+="<div class='col-7'><label class='label'>Date</label><input name='date' type='date' class='form-control form-control-sm' value='"+datetime.now().strftime('%Y-%m-%d')+"'></div>"
    html+="<div class='col-12'><label class='label'>Reason</label><input name='reason' class='form-control form-control-sm' placeholder='Sunday duty, holiday'></div>"
    html+="<div class='col-12'><button class='btn btn-rdot w-100 mt-1'><i class='bi bi-plus'></i> Add Restday OT</button></div>"
    html+="</form></div></div>"
    # Loss Hours Card - Full width red
    html+="<div class='col-12'><div class='card-dark card-loss'>"
    html+="<h6 style='color:#ef4444'><i class='bi bi-exclamation-triangle-fill'></i> Add LOSS HOURS</h6>"
    html+="<form method='POST' action='/add_ot/"+str(aid)+"' class='row g-2 mt-1'>"
    html+="<input type='hidden' name='type' value='LOSS'>"
    html+="<div class='col-4'><label class='label'>Loss Hours</label><input name='hours' type='number' step='0.5' class='form-control form-control-sm' placeholder='1.5' required></div>"
    html+="<div class='col-4'><label class='label'>Date</label><input name='date' type='date' class='form-control form-control-sm' value='"+datetime.now().strftime('%Y-%m-%d')+"'></div>"
    html+="<div class='col-4'><label class='label'>Type</label><select name='loss_type' class='form-select form-select-sm'><option>Late</option><option>Absent</option><option>Undertime</option><option>NCNS</option><option>Others</option></select></div>"
    html+="<div class='col-12'><label class='label'>Reason / Details</label><input name='reason' class='form-control form-control-sm' placeholder='Late 1.5h - traffic, etc'></div>"
    html+="<div class='col-12'><button class='btn btn-loss w-100 mt-1'><i class='bi bi-dash-circle'></i> Add Loss Hours</button></div>"
    html+="</form></div></div>"
    html+="</div>"
    html+="<div class='mt-4'><h6 style='color:white'><i class='bi bi-clock-history'></i> Monitoring History - Normal | Restday | Loss</h6><div class='table-responsive'><table class='table table-sm'><thead><tr><th>Date</th><th>Type</th><th>Hrs</th><th>Reason</th><th></th></tr></thead><tbody>"+log_rows+"</tbody></table></div></div>"
    html+="<hr style='border-color:#1e293b'>"
    html+="<div class='row g-2'>"
    html+="<div class='col-6'><div class='card-dark'><div class='label'>NAME</div><div class='val'>"+str(data.get("NAME",""))+"</div></div></div>"
    html+="<div class='col-6'><div class='card-dark'><div class='label'>TENCENT ID</div><div class='val'>"+str(data.get("TENCENT_ID",""))+"</div></div></div>"
    html+="</div>"
    html+="</div>"
    return page(html)

@app.route("/add_ot/<aid>", methods=["POST"])
def add_ot(aid):
    typ=request.form.get("type","NORMAL_OT")
    hours=request.form.get("hours","0")
    date=request.form.get("date",datetime.now().strftime("%Y-%m-%d"))
    reason=request.form.get("reason","")
    loss_type=request.form.get("loss_type","")
    if loss_type:
        reason = "["+loss_type+"] " + reason
    db_root.child("ot_logs").push({"agent_id":str(aid),"type":typ,"hours":str(hours),"date":date,"reason":reason})
    return redirect("/view/"+str(aid))

@app.route("/delete_log/<aid>/<log_id>")
def delete_log(aid, log_id):
    db_root.child("ot_logs/"+log_id).delete()
    return redirect("/view/"+str(aid))

@app.route("/add", methods=["GET","POST"])
def add():
    if request.method=="POST":
        clean={"NAME":request.form.get("NAME",""),"TENCENT_ID":request.form.get("TENCENT_ID","")}
        agents=get_all()
        max_id=0
        for a in agents:
            try: max_id=max(max_id,int(a.get("id")))
            except: pass
        new_id=str(max_id+1)
        db_root.child("agents/"+new_id).set(clean)
        return redirect("/view/"+new_id)
    return page("<div class='card-dark'><h5 style='color:white'>Add Agent</h5><form method='POST' class='row g-2'><div class='col-6'><label class='label'>NAME</label><input name='NAME' class='form-control form-control-sm'></div><div class='col-6'><label class='label'>TENCENT ID</label><input name='TENCENT_ID' class='form-control form-control-sm'></div><div class='col-12'><button class='btn btn-warning w-100 mt-2'>Save</button></div></form></div>")

if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",5000)))
