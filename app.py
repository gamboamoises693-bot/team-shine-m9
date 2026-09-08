
import os, json
from flask import Flask, request, redirect, session
from functools import wraps
from datetime import datetime, timezone, timedelta
PH_TZ = timezone(timedelta(hours=8))

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "team-shine-m9-secret-2024-secure")

TEAM_USER = os.environ.get("TEAM_USER", "admin")
TEAM_PASS = os.environ.get("TEAM_PASS", "shine2024")

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated

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
except Exception as e:
    db_root = None

def get_all():
    raw = db_root.child("agents").get() if db_root else None
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
    logs = db_root.child("ot_logs").get() if db_root else {}
    result=[]
    if isinstance(logs, dict):
        for lid, v in logs.items():
            if not isinstance(v, dict): continue
            if str(v.get("agent_id"))==str(agent_id):
                v["log_id"]=lid
                result.append(v)
    return result


def get_perf(agent_id):
    logs = db_root.child("perf_logs").get() if db_root else {}
    result=[]
    if isinstance(logs, dict):
        for lid, v in logs.items():
            if not isinstance(v, dict): continue
            if str(v.get("agent_id"))==str(agent_id):
                v["log_id"]=lid
                result.append(v)
    return result

def calc_perf(logs):
    aht_list=[float(l.get("value",0)) for l in logs if l.get("type")=="AHT"]
    qa_list=[float(l.get("value",0)) for l in logs if l.get("type")=="QA"]
    avg_aht = sum(aht_list)/len(aht_list) if aht_list else 0
    avg_qa = sum(qa_list)/len(qa_list) if qa_list else 0
    latest_aht = aht_list[-1] if aht_list else 0
    latest_qa = qa_list[-1] if qa_list else 0
    return latest_aht, latest_qa, avg_aht, avg_qa, aht_list, qa_list


def calc(logs):
    normal=sum(float(l.get("hours",0)) for l in logs if l.get("type")=="NORMAL_OT")
    restday=sum(float(l.get("hours",0)) for l in logs if l.get("type")=="RESTDAY_OT")
    loss=sum(float(l.get("hours",0)) for l in logs if l.get("type")=="LOSS")
    return normal,restday,normal+restday,loss,(normal+restday-loss)

BASE_HEAD = """<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1">
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
<link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.0/font/bootstrap-icons.css" rel="stylesheet">
<style>
body{background:#0b1120;color:#f1f5f9;font-family:Inter,system-ui}
.card-dark{background:#151e32;border:1px solid #2d3748;border-radius:20px;padding:16px;box-shadow:0 4px 12px rgba(0,0,0,0.3)}
.kpi{padding:12px 8px;border-radius:16px;background:#151e32;border:1px solid #2d3748;text-align:center;min-height:110px;height:110px;display:flex;flex-direction:column;justify-content:center;align-items:center}
.label{font-size:9px;color:#94a3b8;text-transform:uppercase;letter-spacing:.6px;font-weight:600;line-height:11px;min-height:22px;display:flex;align-items:center;justify-content:center}
.val-big{font-size:22px;font-weight:800;margin-top:2px;line-height:24px}
.avatar{width:44px;height:44px;background:linear-gradient(135deg,#fbbf24,#f59e0b);border-radius:12px;display:flex;align-items:center;justify-content:center;font-size:18px;font-weight:900;color:#111827}
.table thead th{background:#0f172a!important;color:#fbbf24!important;font-size:10px;text-transform:uppercase;letter-spacing:.5px;border:none!important}
.table tbody td{background:#151e32!important;border-color:#1e293b!important;color:#e2e8f0!important;padding:12px 8px}
.badge-critical{background:#ef4444;color:white;border-radius:6px;padding:2px 8px;font-size:10px}
.badge-warning{background:#f59e0b;color:#111827;border-radius:6px;padding:2px 8px;font-size:10px}
.badge-good{background:#22c55e;color:white;border-radius:6px;padding:2px 8px;font-size:10px}
input,select{background:#0f172a!important;color:#f1f5f9!important;border:1px solid #334155!important}
</style></head><body>
<nav class="navbar p-3" style="background:#0f172a;border-bottom:1px solid #1e293b"><div class="container-fluid">
<a class="navbar-brand fw-bold text-light" href="/">TEAM SHINE M9 <small style="color:#fbbf24;font-size:11px"><i class="bi bi-graph-up-arrow"></i> TEAM LEADER</small></a>
<div><span class="badge bg-warning text-dark">19 AGENTS LIVE</span> <a href="/agents" class="btn btn-sm btn-outline-light ms-2">Agents</a> <a href="/logout" class="btn btn-sm btn-outline-danger ms-1">Logout</a></div>
</div></nav><div class="container-fluid p-3" style="max-width:1200px;margin:auto">
"""

BASE_FOOT = """
</div>
<footer style="text-align:center;padding:24px;color:#64748b;font-size:12px;border-top:1px solid #1e293b;margin-top:30px">
  <div>Developed By : <span style="color:#fbbf24;font-weight:700">Moises Gamboa</span> | Computer Engineer</div>
  <div style="font-size:10px;margin-top:4px">TEAM SHINE M9 - OT + LOSS Monitoring System</div>
</footer></body></html>
"""

def page(c):
    return BASE_HEAD + c + BASE_FOOT

@app.route("/login", methods=["GET","POST"])
def login():
    error=""
    if request.method=="POST":
        u=request.form.get("username","")
        p=request.form.get("password","")
        if u==TEAM_USER and p==TEAM_PASS:
            session["logged_in"]=True
            session["user"]=u
            return redirect("/")
        else:
            error="Invalid username or password!"
    return f"""<html><head><meta name="viewport" content="width=device-width,initial-scale=1">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
    body{{background:#0b1120;display:flex;align-items:center;justify-content:center;min-height:100vh;color:#f1f5f9}}
    .login-card{{background:#151e32;border:1px solid #2d3748;border-radius:20px;padding:32px;max-width:400px;width:90%;box-shadow:0 10px 30px rgba(0,0,0,0.5)}}
    .logo{{width:70px;height:70px;background:linear-gradient(135deg,#fbbf24,#f59e0b);border-radius:16px;display:flex;align-items:center;justify-content:center;font-size:32px;font-weight:900;color:#111827;margin:0 auto 16px}}
    input{{background:#0f172a!important;color:#f1f5f9!important;border:1px solid #334155!important;border-radius:10px!important;padding:12px!important}}
    </style></head><body>
    <div class="login-card text-center">
        <div class="logo">S9</div>
        <h4 style="color:white">TEAM SHINE M9</h4>
        <small style="color:#94a3b8">Team Leader Login</small>
        <form method="POST" class="mt-4 text-start">
            <label style="font-size:11px;color:#94a3b8">USERNAME</label>
            <input name="username" class="form-control mb-3" placeholder="Enter username" required>
            <label style="font-size:11px;color:#94a3b8">PASSWORD</label>
            <input name="password" type="password" class="form-control mb-3" placeholder="Enter password" required>
            <div style="color:#ef4444;font-size:12px;margin-bottom:12px">{error}</div>
            <button class="btn btn-warning w-100" style="font-weight:700;padding:12px">Login to Dashboard</button>
        </form>
        <div style="margin-top:20px;padding-top:16px;border-top:1px solid #1e293b;text-align:center">
            <small style="color:#94a3b8">Developed By : <span style="color:#fbbf24">Moises Gamboa</span> | Computer Engineer</small>
        </div>
    </div></body></html>
    """

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

@app.route("/")
@login_required
def dashboard():
    agents=get_all()
    team_normal=0
    team_restday=0
    team_loss=0
    team_total=0
    team_net=0
    agent_stats=[]
    for a in agents:
        logs=get_ot(a.get("id"))
        n,r,tot,loss,net=calc(logs)
        team_normal+=n
        team_restday+=r
        team_loss+=loss
        team_total+=tot
        team_net+=net
        plogs=get_perf(a.get("id"))
        la, lq, aa, qa,_,_=calc_perf(plogs)
        agent_stats.append({"id":a.get("id"),"name":a.get("NAME","No Name"),"tid":a.get("TENCENT_ID",""),"n":n,"r":r,"tot":tot,"loss":loss,"net":net,"aht":la,"qa":lq,"avg_aht":aa,"avg_qa":qa})
    agent_stats_sorted=sorted(agent_stats, key=lambda x: x["tot"], reverse=True)
    top_performers=agent_stats_sorted[:5]
    critical_loss=sorted([x for x in agent_stats if x["loss"]>0], key=lambda x: x["loss"], reverse=True)[:5]
    avg_ot=team_total/len(agents) if agents else 0
    avg_net=team_net/len(agents) if agents else 0

    html="<div class='d-flex justify-content-between align-items-center mb-3'><h5 style='color:white'><i class='bi bi-speedometer2' style='color:#fbbf24'></i> Team Performance Overview</h5><small style='color:#94a3b8'>"+datetime.now(PH_TZ).strftime("%b %d, %Y %I:%M %p")+"</small></div>"
    html+="<div class='row g-2'>"
    html+="<div class='col-6 col-md-2'><div class='kpi' style='border:1px solid #22c55e'><div class='label'>TEAM NORMAL OT</div><div class='val-big' style='color:#22c55e'>"+str(round(team_normal,1))+"h</div><small style='color:#94a3b8;font-size:10px'>"+str(round(team_normal/len(agents),1))+" avg</small></div></div>"
    html+="<div class='col-6 col-md-2'><div class='kpi' style='border:1px solid #3b82f6'><div class='label'>TEAM RESTDAY OT</div><div class='val-big' style='color:#3b82f6'>"+str(round(team_restday,1))+"h</div><small style='color:#94a3b8;font-size:10px'>"+str(round(team_restday/len(agents),1))+" avg</small></div></div>"
    html+="<div class='col-6 col-md-2'><div class='kpi' style='border:1px solid #fbbf24'><div class='label'>TEAM TOTAL OT</div><div class='val-big' style='color:#fbbf24'>"+str(round(team_total,1))+"h</div><small style='color:#94a3b8;font-size:10px'>Total Team</small></div></div>"
    html+="<div class='col-6 col-md-2'><div class='kpi' style='border:1px solid #ef4444'><div class='label'>TEAM LOSS HRS</div><div class='val-big' style='color:#ef4444'>"+str(round(team_loss,1))+"h</div><small style='color:#ef4444;font-size:10px'>Critical KPI</small></div></div>"
    html+="<div class='col-6 col-md-2'><div class='kpi' style='border:1px solid #a855f7'><div class='label'>TEAM NET</div><div class='val-big' style='color:#a855f7'>+"+str(round(team_net,1))+"h</div><small style='color:#94a3b8;font-size:10px'>"+str(round(avg_net,1))+" avg</small></div></div>"
    html+="<div class='col-6 col-md-2'><div class='kpi' style='border:1px solid #06b6d4'><div class='label'>AVG OT / AGENT</div><div class='val-big' style='color:#06b6d4'>"+str(round(avg_ot,1))+"h</div><small style='color:#94a3b8;font-size:10px'>19 agents</small></div></div>"
    html+="</div>"
    
    # Calculate team AHT and QA
    team_aht_vals=[]
    team_qa_vals=[]
    for a in agent_stats:
        plogs=get_perf(a["id"])
        _,_,aa,qa,_,_=calc_perf(plogs)
        if aa>0: team_aht_vals.append(aa)
        if qa>0: team_qa_vals.append(qa)
    team_avg_aht = sum(team_aht_vals)/len(team_aht_vals) if team_aht_vals else 0
    team_avg_qa = sum(team_qa_vals)/len(team_qa_vals) if team_qa_vals else 0
    html+="<div class='row g-2 mt-2'>"
    html+="<div class='col-6 col-md-6'><div class='kpi' style='border:1px solid #f97316;min-height:90px;height:90px'><div class='label'>TEAM AVG AHT</div><div class='val-big' style='color:#f97316'>"+str(round(team_avg_aht,1))+"m</div><small style='color:#94a3b8;font-size:10px'>Avg Handling Time</small></div></div>"
    html+="<div class='col-6 col-md-6'><div class='kpi' style='border:1px solid #8b5cf6;min-height:90px;height:90px'><div class='label'>TEAM AVG QA SCORE</div><div class='val-big' style='color:#8b5cf6'>"+str(round(team_avg_qa,1))+"%</div><small style='color:#94a3b8;font-size:10px'>Quality Score</small></div></div>"
    html+="</div>"


    html+="<div class='row g-3 mt-3'>"
    html+="<div class='col-12 col-md-6'><div class='card-dark' style='border:1px solid #22c55e'><h6 style='color:#22c55e'><i class='bi bi-trophy-fill'></i> TOP PERFORMERS - Highest OT</h6>"
    for a in top_performers:
        html+="<div class='d-flex justify-content-between align-items-center mt-3'><div class='d-flex align-items-center'><div class='avatar' style='width:36px;height:36px;font-size:14px'>"+str(a['name'][:1])+"</div><div class='ms-2'><div style='color:white;font-size:13px;font-weight:600'>"+str(a['name'])+"</div><small style='color:#94a3b8'>"+str(a['tid'])+" N:"+str(a['n'])+" RD:"+str(a['r'])+"</small></div></div><div style='color:#22c55e;font-weight:800'>"+str(a['tot'])+"h</div></div>"
    html+="</div></div>"
    html+="<div class='col-12 col-md-6'><div class='card-dark' style='border:1px solid #ef4444'><h6 style='color:#ef4444'><i class='bi bi-exclamation-triangle-fill'></i> CRITICAL - Loss Monitoring</h6>"
    if not critical_loss:
        html+="<div class='text-center py-4'><div style='font-size:32px'>✅</div><div style='color:#94a3b8' class='mt-2'>No Loss Hours - Team is Good!</div></div>"
    else:
        for a in critical_loss:
            html+="<div class='d-flex justify-content-between align-items-center mt-3'><div><div style='color:white;font-size:13px'>"+str(a['name'])+"</div><small style='color:#94a3b8'>"+str(a['tid'])+"</small></div><div><span class='badge-critical'>"+str(a['loss'])+"h LOSS</span></div></div>"
    html+="</div></div>"
    html+="</div>"

    html+="<div class='card-dark mt-3' style='border:1px solid #334155'><div class='d-flex justify-content-between'><h6 style='color:white'><i class='bi bi-people-fill' style='color:#fbbf24'></i> Full Team - Critical KPIs</h6><a href='/agents' class='btn btn-sm btn-warning'>View All 19</a></div>"
    html+="<div class='table-responsive mt-3'><table class='table table-sm'><thead><tr><th>AGENT</th><th>NORMAL</th><th>RESTDAY</th><th>TOTAL</th><th>LOSS</th><th>NET</th><th>AHT</th><th>QA</th><th>STATUS</th></tr></thead><tbody>"
    for a in agent_stats_sorted:
        if a['loss']>=4:
            st="<span class='badge-critical'>Critical</span>"
        elif a['loss']>0:
            st="<span class='badge-warning'>Warning</span>"
        elif a['tot']>=10:
            st="<span class='badge-good'>Top</span>"
        else:
            st="<span style='color:#94a3b8;font-size:10px'>Normal</span>"
        aht_color="#f97316" if a['aht']>0 else "#64748b"
        qa_color="#8b5cf6" if a['qa']>=90 else "#f59e0b" if a['qa']>=80 else "#ef4444" if a['qa']>0 else "#64748b"
        html+="<tr><td><a href='/view/"+str(a['id'])+"' style='color:white;text-decoration:none'><b style='font-size:13px'>"+str(a['name'])+"</b><br><small style='color:#94a3b8'>"+str(a['tid'])+"</small></a></td><td style='color:#22c55e'>"+str(a['n'])+"h</td><td style='color:#3b82f6'>"+str(a['r'])+"h</td><td style='color:#fbbf24;font-weight:700'>"+str(a['tot'])+"h</td><td style='color:#ef4444'>"+str(a['loss'])+"h</td><td style='color:#a855f7;font-weight:700'>+"+str(a['net'])+"h</td><td style='color:"+aht_color+"'>"+(str(a['aht'])+"m" if a['aht']>0 else "-")+"</td><td style='color:"+qa_color+"'>"+(str(a['qa'])+"%" if a['qa']>0 else "-")+"</td><td>"+st+"</td></tr>"
    html+="</tbody></table></div></div>"

    return page(html)

@app.route("/agents")
@login_required
def agents_list():
    agents=get_all()
    rows=""
    for a in agents:
        logs=get_ot(a.get("id"))
        n,r,tot,loss,net=calc(logs)
        rows+="<tr><td>"+str(a.get("id"))+"</td><td><a href='/view/"+str(a.get("id"))+"' style='color:white;text-decoration:none'><b>"+str(a.get("NAME",""))+"</b><br><small style='color:#94a3b8'>"+str(a.get("TENCENT_ID",""))+" NET:"+str(net)+"h</small></a></td><td style='color:#22c55e'>"+str(n)+"h</td><td style='color:#3b82f6'>"+str(r)+"h</td><td style='color:#ef4444'>"+str(loss)+"h</td><td><a href='/view/"+str(a.get("id"))+"' class='btn btn-sm btn-warning'>View</a></td></tr>"
    return page("<div class='d-flex justify-content-between'><h5 style='color:white'>All Agents ("+str(len(agents))+")</h5><a href='/' class='btn btn-sm btn-outline-light'>Dashboard</a></div><div class='card-dark mt-3'><div class='table-responsive'><table class='table'><thead><tr><th>ID</th><th>AGENT</th><th>N</th><th>RD</th><th>LOSS</th><th></th></tr></thead><tbody>"+rows+"</tbody></table></div></div>")

@app.route("/view/<aid>")
@login_required
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
    for l in logs:
        col="#22c55e" if l.get("type")=="NORMAL_OT" else "#3b82f6" if l.get("type")=="RESTDAY_OT" else "#ef4444"
        log_rows+="<tr><td style='color:#cbd5e1'>"+str(l.get("date",""))+"</td><td><span style='color:"+col+"'>"+str(l.get("type"))+"</span></td><td style='color:white'>"+str(l.get("hours"))+"h</td><td style='color:#94a3b8'>"+str(l.get("reason",""))+"</td><td><a href='/delete_log/"+str(aid)+"/"+str(l.get("log_id",''))+"' class='btn btn-sm btn-outline-danger' style='font-size:10px'>X</a></td></tr>"
    if not log_rows:
        log_rows="<tr><td colspan=5 style='color:#64748b;text-align:center'>No logs yet</td></tr>"
    initial=str(data.get("NAME","?"))[:1]
    html="<a href='/' class='btn btn-sm btn-outline-light mb-3'>Back Dashboard</a>"
    html+="<div class='card-dark' style='border:1px solid #334155'><div class='text-center'><div style='width:90px;height:90px;background:linear-gradient(135deg,#fbbf24,#f59e0b);border-radius:18px;display:flex;align-items:center;justify-content:center;font-size:40px;font-weight:900;color:#111827;margin:auto'>"+initial+"</div><h4 style='color:white;margin-top:12px'>"+str(data.get("NAME",""))+"</h4><small style='color:#94a3b8'>"+str(data.get("TENCENT_ID",""))+"</small></div>"
    plogs=get_perf(aid)
    la,lq,aa,qa,_,_=calc_perf(plogs)
    html+="<div class='row g-2 mt-3'>"
    html+="<div class='col-4'><div class='kpi' style='border:1px solid #22c55e'><div class='label'>NORMAL OT</div><div class='val-big' style='color:#22c55e'>"+str(n)+"h</div></div></div>"
    html+="<div class='col-4'><div class='kpi' style='border:1px solid #3b82f6'><div class='label'>RESTDAY OT</div><div class='val-big' style='color:#3b82f6'>"+str(r)+"h</div></div></div>"
    html+="<div class='col-4'><div class='kpi' style='border:1px solid #ef4444'><div class='label'>LOSS HRS</div><div class='val-big' style='color:#ef4444'>"+str(loss)+"h</div></div></div>"
    html+="<div class='col-6'><div class='kpi' style='border:1px solid #22c55e'><div class='label'>TOTAL OT</div><div class='val-big' style='color:#22c55e'>"+str(tot)+"h</div></div></div>"
    html+="<div class='col-6'><div class='kpi' style='border:1px solid #fbbf24'><div class='label'>NET</div><div class='val-big' style='color:#fbbf24'>+"+str(net)+"h</div></div></div>"
    html+="<div class='col-6'><div class='kpi' style='border:1px solid #f97316'><div class='label'>AHT</div><div class='val-big' style='color:#f97316'>"+str(la)+"m</div><small style='color:#94a3b8;font-size:9px'>Avg:"+str(round(aa,1))+"m</small></div></div>"
    html+="<div class='col-6'><div class='kpi' style='border:1px solid #8b5cf6'><div class='label'>QA SCORE</div><div class='val-big' style='color:#8b5cf6'>"+str(lq)+"%</div><small style='color:#94a3b8;font-size:9px'>Avg:"+str(round(qa,1))+"%</small></div></div>"
    html+="</div>"
    html+="<div class='row g-2 mt-4'>"
    html+="<div class='col-6'><div class='card-dark' style='border:1px solid #22c55e'><h6 style='color:#22c55e'>Add NORMAL OT</h6><form method='POST' action='/add_ot/"+str(aid)+"' class='row g-2'><input type='hidden' name='type' value='NORMAL_OT'><div class='col-6'><input name='hours' type='number' step='0.5' class='form-control form-control-sm' placeholder='Hours' required></div><div class='col-6'><input name='date' type='date' class='form-control form-control-sm' value='"+datetime.now(PH_TZ).strftime("%Y-%m-%d")+"'></div><div class='col-12'><input name='reason' class='form-control form-control-sm' placeholder='Reason'></div><div class='col-12'><button class='btn w-100 mt-1' style='background:#22c55e;color:white'>Add Normal OT</button></div></form></div></div>"
    html+="<div class='col-6'><div class='card-dark' style='border:1px solid #3b82f6'><h6 style='color:#3b82f6'>Add RESTDAY OT</h6><form method='POST' action='/add_ot/"+str(aid)+"' class='row g-2'><input type='hidden' name='type' value='RESTDAY_OT'><div class='col-6'><input name='hours' type='number' step='0.5' class='form-control form-control-sm' placeholder='Hours' required></div><div class='col-6'><input name='date' type='date' class='form-control form-control-sm' value='"+datetime.now(PH_TZ).strftime("%Y-%m-%d")+"'></div><div class='col-12'><input name='reason' class='form-control form-control-sm' placeholder='Reason'></div><div class='col-12'><button class='btn w-100 mt-1' style='background:#3b82f6;color:white'>Add Restday OT</button></div></form></div></div>"
    html+="<div class='col-6'><div class='card-dark' style='border:1px solid #f97316'><h6 style='color:#f97316'><i class='bi bi-stopwatch'></i> Add AHT</h6><form method='POST' action='/add_perf/"+str(aid)+"' class='row g-2'><input type='hidden' name='type' value='AHT'><div class='col-6'><input name='value' type='number' step='0.1' class='form-control form-control-sm' placeholder='Minutes' required></div><div class='col-6'><input name='date' type='date' class='form-control form-control-sm' value='"+datetime.now(PH_TZ).strftime("%Y-%m-%d")+"'></div><div class='col-12'><input name='reason' class='form-control form-control-sm' placeholder='Notes'></div><div class='col-12'><button class='btn w-100 mt-1' style='background:#f97316;color:white'><i class='bi bi-plus'></i> Add AHT</button></div></form></div></div>"
    html+="<div class='col-6'><div class='card-dark' style='border:1px solid #8b5cf6'><h6 style='color:#8b5cf6'><i class='bi bi-star-fill'></i> Add QA SCORE</h6><form method='POST' action='/add_perf/"+str(aid)+"' class='row g-2'><input type='hidden' name='type' value='QA'><div class='col-6'><input name='value' type='number' step='0.1' min='0' max='100' class='form-control form-control-sm' placeholder='%' required></div><div class='col-6'><input name='date' type='date' class='form-control form-control-sm' value='"+datetime.now(PH_TZ).strftime("%Y-%m-%d")+"'></div><div class='col-12'><input name='reason' class='form-control form-control-sm' placeholder='QA notes'></div><div class='col-12'><button class='btn w-100 mt-1' style='background:#8b5cf6;color:white'><i class='bi bi-plus'></i> Add QA Score</button></div></form></div></div>"
    html+="<div class='col-12'><div class='card-dark' style='border:1px solid #ef4444'><h6 style='color:#ef4444'>Add LOSS HOURS</h6><form method='POST' action='/add_ot/"+str(aid)+"' class='row g-2'><input type='hidden' name='type' value='LOSS'><div class='col-4'><input name='hours' type='number' step='0.5' class='form-control form-control-sm' placeholder='Loss Hrs' required></div><div class='col-4'><input name='date' type='date' class='form-control form-control-sm' value='"+datetime.now(PH_TZ).strftime("%Y-%m-%d")+"'></div><div class='col-4'><select name='loss_type' class='form-select form-select-sm'><option>Late</option><option>Absent</option><option>Undertime</option></select></div><div class='col-12'><input name='reason' class='form-control form-control-sm' placeholder='Reason'></div><div class='col-12'><button class='btn w-100 mt-1' style='background:#ef4444;color:white'>Add Loss</button></div></form></div></div>"
    html+="</div>"
    perf_rows=""
    for l in plogs:
        col="#f97316" if l.get("type")=="AHT" else "#8b5cf6"
        unit="m" if l.get("type")=="AHT" else "%"
        perf_rows+="<tr><td style='color:#cbd5e1'>"+str(l.get("date",""))+"</td><td><span style='color:"+col+"'>"+str(l.get("type"))+"</span></td><td style='color:white'>"+str(l.get("value"))+unit+"</td><td style='color:#94a3b8'>"+str(l.get("reason",""))+"</td><td><a href='/delete_perf/"+str(aid)+"/"+str(l.get("log_id",''))+"' class='btn btn-sm btn-outline-danger' style='font-size:10px'>X</a></td></tr>"
    if not perf_rows:
        perf_rows="<tr><td colspan=5 style='color:#64748b;text-align:center'>No AHT/QA logs</td></tr>"
    html+="<div class='mt-4'><h6 style='color:white'>OT & Loss History</h6><div class='table-responsive'><table class='table table-sm'><thead><tr><th>Date</th><th>Type</th><th>Hrs</th><th>Reason</th><th></th></tr></thead><tbody>"+log_rows+"</tbody></table></div></div>"
    html+="<div class='mt-3'><h6 style='color:white'><i class='bi bi-graph-up'></i> AHT & QA Score History</h6><div class='table-responsive'><table class='table table-sm'><thead><tr><th>Date</th><th>Type</th><th>Value</th><th>Notes</th><th></th></tr></thead><tbody>"+perf_rows+"</tbody></table></div></div>"

    html+="</div>"
    return page(html)

@app.route("/add_ot/<aid>", methods=["POST"])
@login_required
def add_ot(aid):
    typ=request.form.get("type","NORMAL_OT")
    hours=request.form.get("hours","0")
    date=request.form.get("date",datetime.now(PH_TZ).strftime("%Y-%m-%d"))
    reason=request.form.get("reason","")
    db_root.child("ot_logs").push({"agent_id":str(aid),"type":typ,"hours":str(hours),"date":date,"reason":reason})
    return redirect("/view/"+str(aid))


@app.route("/add_perf/<aid>", methods=["POST"])
@login_required
def add_perf(aid):
    typ=request.form.get("type","AHT")
    value=request.form.get("value","0")
    date=request.form.get("date",datetime.now(PH_TZ).strftime("%Y-%m-%d"))
    reason=request.form.get("reason","")
    if db_root:
        db_root.child("perf_logs").push({"agent_id":str(aid),"type":typ,"value":str(value),"date":date,"reason":reason})
    return redirect("/view/"+str(aid))

@app.route("/delete_perf/<aid>/<log_id>")
@login_required
def delete_perf(aid, log_id):
    if db_root:
        db_root.child("perf_logs/"+log_id).delete()
    return redirect("/view/"+str(aid))


@app.route("/delete_log/<aid>/<log_id>")
@login_required
def delete_log(aid, log_id):
    if db_root:
        db_root.child("ot_logs/"+log_id).delete()
    return redirect("/view/"+str(aid))

if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",5000)))
