
import os, json, io, csv, traceback
from flask import Flask, request, redirect, session, Response
from functools import wraps
from datetime import datetime, timezone, timedelta
from collections import defaultdict
import calendar

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "team-shine-m9-secret-2024-secure")
PH_TZ = timezone(timedelta(hours=8))

USERS = {
    os.environ.get("TEAM_USER","admin"): {"pass": os.environ.get("TEAM_PASS","shine2024"), "role": "admin", "name": "Admin"},
    "tl": {"pass": "tl2024", "role": "team_leader", "name": "Team Leader"},
    "qa": {"pass": "qa2024", "role": "qa", "name": "QA Specialist"},
    "admin": {"pass": "shine2024", "role": "admin", "name": "Moises Gamboa"},
}

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
    print(f"Firebase init error: {e}")
    db_root = None

def get_all():
    try:
        raw = db_root.child("agents").get() if db_root else None
        agents=[]
        if raw is None: return []
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
    except Exception as e:
        print(f"get_all error: {e}")
        return []

def get_ot(agent_id):
    try:
        logs = db_root.child("ot_logs").get() if db_root else {}
        result=[]
        if isinstance(logs, dict):
            for lid, v in logs.items():
                if not isinstance(v, dict): continue
                if str(v.get("agent_id"))==str(agent_id):
                    v["log_id"]=lid
                    result.append(v)
        return result
    except:
        return []

def get_all_ot_logs():
    try:
        logs = db_root.child("ot_logs").get() if db_root else {}
        return [v for v in logs.values() if isinstance(v, dict)] if isinstance(logs, dict) else []
    except:
        return []

def get_all_perf_logs():
    try:
        logs = db_root.child("perf_logs").get() if db_root else {}
        return [v for v in logs.values() if isinstance(v, dict)] if isinstance(logs, dict) else []
    except:
        return []

def get_perf(agent_id):
    try:
        logs = db_root.child("perf_logs").get() if db_root else {}
        result=[]
        if isinstance(logs, dict):
            for lid, v in logs.items():
                if not isinstance(v, dict): continue
                if str(v.get("agent_id"))==str(agent_id):
                    v["log_id"]=lid
                    result.append(v)
        return result
    except:
        return []

def calc(logs):
    try:
        normal=sum(float(l.get("hours",0)) for l in logs if l.get("type")=="NORMAL_OT")
        restday=sum(float(l.get("hours",0)) for l in logs if l.get("type")=="RESTDAY_OT")
        loss=sum(float(l.get("hours",0)) for l in logs if l.get("type")=="LOSS")
        return normal,restday,normal+restday,loss,(normal+restday-loss)
    except:
        return 0,0,0,0,0

def calc_perf(logs):
    try:
        aht_list=[float(l.get("value",0)) for l in logs if l.get("type")=="AHT"]
        qa_list=[float(l.get("value",0)) for l in logs if l.get("type")=="QA"]
        avg_aht = sum(aht_list)/len(aht_list) if aht_list else 0
        avg_qa = sum(qa_list)/len(qa_list) if qa_list else 0
        latest_aht = aht_list[-1] if aht_list else 0
        latest_qa = qa_list[-1] if qa_list else 0
        return latest_aht, latest_qa, avg_aht, avg_qa, aht_list, qa_list
    except:
        return 0,0,0,0,[],[]

BASE_HEAD = """<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1">
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
<link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.0/font/bootstrap-icons.css" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
body{background:#0b1120;color:#f1f5f9;font-family:Inter,system-ui}
.card-dark{background:#151e32;border:1px solid #2d3748;border-radius:20px;padding:16px}
.kpi{padding:12px 8px;border-radius:16px;background:#151e32;border:1px solid #2d3748;text-align:center;min-height:110px;height:110px;display:flex;flex-direction:column;justify-content:center;align-items:center}
.label{font-size:9px;color:#94a3b8;text-transform:uppercase;font-weight:600;min-height:22px;display:flex;align-items:center;justify-content:center}
.val-big{font-size:22px;font-weight:800;margin-top:2px}
.chart-card{background:#151e32;border:1px solid #2d3748;border-radius:20px;padding:16px}
.table thead th{background:#0f172a!important;color:#fbbf24!important;font-size:10px;text-transform:uppercase;border:none!important}
.table tbody td{background:#151e32!important;border-color:#1e293b!important;color:#e2e8f0!important;padding:12px 8px}
input,select{background:#0f172a!important;color:#f1f5f9!important;border:1px solid #334155!important}
</style></head><body>
<nav class="navbar p-3" style="background:#0f172a;border-bottom:1px solid #1e293b"><div class="container-fluid">
<a class="navbar-brand fw-bold text-light" href="/">TEAM SHINE M9 <small style="color:#fbbf24;font-size:11px">TEAM LEADER</small></a>
<div class="d-flex gap-1">
<button onclick="localStorage.setItem('theme', document.body.classList.contains('light-mode')?'dark':'light'); document.body.classList.toggle('light-mode')" class="btn btn-sm btn-outline-light">🌙</button>
<a href="/logs" class="btn btn-sm btn-outline-light">📋</a>
<a href="/agents" class="btn btn-sm btn-outline-light">Agents</a> 
<a href="/change_password" class="btn btn-sm btn-outline-light">🔑</a>
<a href="/logout" class="btn btn-sm btn-outline-danger">Logout</a>
</div>
</div></nav><div class="container-fluid p-3" style="max-width:1200px;margin:auto">
"""

BASE_FOOT = """
</div><footer style="text-align:center;padding:24px;color:#64748b;font-size:12px;border-top:1px solid #1e293b;margin-top:30px"><div>Developed By : <span style="color:#fbbf24;font-weight:700">Moises Gamboa</span> | Computer Engineer</div></footer></body></html>
"""

def page(c):
    return BASE_HEAD + c + BASE_FOOT

@app.errorhandler(500)
def handle_500(e):
    tb = traceback.format_exc()
    return f"<h3 style='color:white'>Error occurred</h3><pre style='color:#fbbf24;font-size:11px'>{tb}</pre><a href='/'>Back</a>", 500

@app.route("/login", methods=["GET","POST"])
def login():
    error=""
    if request.method=="POST":
        try:
            u=request.form.get("username","").strip()
            p=request.form.get("password","").strip()
            user=USERS.get(u)
            if user and user["pass"]==p:
                session["logged_in"]=True
                session["user"]=u
                session["role"]=user["role"]
                session["name"]=user["name"]
                session["agent_id"]=None
                try:
                    if db_root:
                        db_root.child("login_logs").push({"user": u,"name": user["name"],"role": user["role"],"type": "LOGIN","timestamp": datetime.now(PH_TZ).strftime("%Y-%m-%d %I:%M:%S %p"),"date": datetime.now(PH_TZ).strftime("%Y-%m-%d"),"agent_id": "ADMIN"})
                except: pass
                return f"<script>window.location='/';</script>"
            found_agent=None
            agents = get_all()
            for a in agents:
                tid=str(a.get("TENCENT_ID","")).strip()
                if u==tid or u==str(a.get("id")):
                    found_agent=a
                    break
            if found_agent:
                stored=str(found_agent.get("LOGIN_PASS") or found_agent.get("TENCENT_ID") or "1234").strip()
                if p==stored or p==str(found_agent.get("TENCENT_ID")):
                    session["logged_in"]=True
                    session["user"]=found_agent.get("TENCENT_ID")
                    session["role"]="agent"
                    session["name"]=found_agent.get("NAME")
                    session["agent_id"]=found_agent.get("id")
                    try:
                        if db_root:
                            db_root.child("login_logs").push({"user": found_agent.get("TENCENT_ID"),"name": found_agent.get("NAME"),"role": "agent","type": "LOGIN","timestamp": datetime.now(PH_TZ).strftime("%Y-%m-%d %I:%M:%S %p"),"date": datetime.now(PH_TZ).strftime("%Y-%m-%d"),"agent_id": found_agent.get("id")})
                    except: pass
                    return redirect(f"/view/{found_agent.get('id')}")
                else:
                    error="Invalid agent password! Default is Tencent ID"
            else:
                error="Invalid username or password!"
        except Exception as e:
            error=f"Login error: {str(e)}"
    return f"""<html><head><meta name="viewport" content="width=device-width,initial-scale=1">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>body{{background:#0b1120;display:flex;align-items:center;justify-content:center;min-height:100vh;color:#f1f5f9}}.login-card{{background:#151e32;border:1px solid #2d3748;border-radius:20px;padding:32px;max-width:400px;width:90%}}.logo{{width:70px;height:70px;background:linear-gradient(135deg,#fbbf24,#f59e0b);border-radius:16px;display:flex;align-items:center;justify-content:center;font-size:32px;font-weight:900;color:#111827;margin:0 auto 16px}}input{{background:#0f172a!important;color:#f1f5f9!important;border:1px solid #334155!important;border-radius:10px!important;padding:12px!important}}</style></head><body>
    <div class="login-card text-center"><div class="logo">S9</div><h4 style="color:white">TEAM SHINE M9</h4><small style="color:#94a3b8">Team Access</small>
    <form method="POST" class="mt-4 text-start"><label style="font-size:11px;color:#94a3b8">USERNAME</label><input name="username" class="form-control mb-3" required><label style="font-size:11px;color:#94a3b8">PASSWORD</label><input name="password" type="password" class="form-control mb-3" required><div style="color:#ef4444;font-size:12px;margin-bottom:12px">{error}</div><button class="btn btn-warning w-100" style="font-weight:700;padding:12px">Login</button><div class="mt-3 text-center"><small style="color:#64748b;font-size:11px">Agent: Tencent ID as username & password</small></div></form>
    <div style="margin-top:20px;padding-top:16px;border-top:1px solid #1e293b;text-align:center"><small style="color:#94a3b8">Developed By : <span style="color:#fbbf24">Moises Gamboa</span></small></div></div></body></html>
    """

@app.route("/logout")
def logout():
    try:
        if db_root and session.get("logged_in"):
            db_root.child("login_logs").push({"user": session.get("user",""),"name": session.get("name",""),"role": session.get("role",""),"type": "LOGOUT","timestamp": datetime.now(PH_TZ).strftime("%Y-%m-%d %I:%M:%S %p"),"date": datetime.now(PH_TZ).strftime("%Y-%m-%d"),"agent_id": session.get("agent_id","")})
    except: pass
    session.clear()
    return redirect("/login")

@app.route("/")
@login_required
def dashboard():
    try:
        if session.get("role")=="agent" and session.get("agent_id"):
            return redirect(f"/view/{session.get('agent_id')}")
        agents=get_all()
        team_normal=0; team_restday=0; team_loss=0; team_total=0
        agent_stats=[]
        for a in agents:
            logs=get_ot(a.get("id"))
            n,r,tot,loss,net=calc(logs)
            team_normal+=n; team_restday+=r; team_loss+=loss; team_total+=tot
            plogs=get_perf(a.get("id"))
            la,lq,aa,qa,_,_=calc_perf(plogs)
            target=float(a.get("TARGET_OT",20))
            pct = (tot/target*100) if target>0 else 0
            agent_stats.append({"id":a.get("id"),"name":a.get("NAME",""),"tid":a.get("TENCENT_ID",""),"tot":tot,"loss":loss,"net":net,"aht":la,"qa":lq,"target":target,"pct":pct})
        agent_stats_sorted=sorted(agent_stats, key=lambda x: x["tot"], reverse=True)
        html=f"<h5 style='color:white'>Dashboard - {datetime.now(PH_TZ).strftime('%b %d, %Y %I:%M %p')}</h5>"
        html+=f"<div class='row g-2'><div class='col-6 col-md-3'><div class='kpi' style='border:1px solid #22c55e'><div class='label'>NORMAL OT</div><div class='val-big' style='color:#22c55e'>{round(team_normal,1)}h</div></div></div><div class='col-6 col-md-3'><div class='kpi' style='border:1px solid #3b82f6'><div class='label'>RESTDAY OT</div><div class='val-big' style='color:#3b82f6'>{round(team_restday,1)}h</div></div></div><div class='col-6 col-md-3'><div class='kpi' style='border:1px solid #fbbf24'><div class='label'>TOTAL OT</div><div class='val-big' style='color:#fbbf24'>{round(team_total,1)}h</div></div></div><div class='col-6 col-md-3'><div class='kpi' style='border:1px solid #ef4444'><div class='label'>LOSS</div><div class='val-big' style='color:#ef4444'>{round(team_loss,1)}h</div></div></div></div>"
        html+="<div class='card-dark mt-3'><div class='d-flex justify-content-between'><h6 style='color:white'>Full Team</h6><a href='/agents' class='btn btn-sm btn-warning'>View All</a></div><div class='table-responsive mt-3'><table class='table table-sm'><thead><tr><th>AGENT</th><th>TOTAL</th><th>TARGET</th><th>PROGRESS</th><th>LOSS</th><th>STATUS</th></tr></thead><tbody>"
        for a in agent_stats_sorted:
            pct = min(100, a['pct'])
            bar_color = "#22c55e" if pct>=100 else "#fbbf24" if pct>=70 else "#ef4444"
            st = "<span class='badge bg-danger'>Critical</span>" if a['loss']>=4 else "<span class='badge bg-success'>Good</span>"
            html+=f"<tr><td><a href='/view/{a['id']}' style='color:white'><b>{a['name']}</b><br><small style='color:#94a3b8'>{a['tid']}</small></a></td><td>{a['tot']}h</td><td>{a['target']}h</td><td><div class='progress' style='height:8px;width:80px;background:#0f172a'><div class='progress-bar' style='width:{pct}%;background:{bar_color}'></div></div><small>{round(a['pct'],0)}%</small></td><td style='color:#ef4444'>{a['loss']}h</td><td>{st}</td></tr>"
        html+="</tbody></table></div></div>"
        return page(html)
    except Exception as e:
        return page(f"<h5 style='color:#ef4444'>Dashboard error</h5><pre style='color:white'>{traceback.format_exc()}</pre>")

@app.route("/view/<aid>")
@login_required
def view(aid):
    try:
        if session.get("role")=="agent" and str(session.get("agent_id"))!=str(aid):
            return redirect(f"/view/{session.get('agent_id')}")
        data=None
        for a in get_all():
            if str(a.get("id"))==str(aid):
                data=a
                break
        if not data:
            return page(f"<div class='card-dark'>Agent {aid} not found</div><a href='/' class='btn btn-sm btn-outline-light'>Back</a>")
        logs=get_ot(aid)
        n,r,tot,loss,net=calc(logs)
        plogs=get_perf(aid)
        la,lq,aa,qa,_,_=calc_perf(plogs)
        date_groups=defaultdict(list)
        for l in logs:
            date_groups[l.get("date")].append(l)
        sorted_dates=sorted(date_groups.keys())[-14:]
        ind_labels=[]; ind_tot=[]; ind_loss=[]
        for d in sorted_dates:
            ll=date_groups[d]
            _,_,t,lo,ne=calc(ll)
            ind_labels.append(d[-5:] if d else "")
            ind_tot.append(t)
            ind_loss.append(lo)
        pgroups=defaultdict(list)
        for l in plogs:
            pgroups[l.get("date")].append(l)
        ind_aht=[]; ind_qa=[]
        for d in sorted_dates:
            pl=pgroups.get(d,[])
            _,_,aaa,qq,_,_=calc_perf(pl)
            ind_aht.append(aaa)
            ind_qa.append(qq)
        initial=str(data.get("NAME","?"))[:1]
        target=float(data.get("TARGET_OT",20))
        pct = (tot/target*100) if target>0 else 0
        bar_color = "#22c55e" if pct>=100 else "#fbbf24" if pct>=70 else "#ef4444"
        is_agent = session.get("role")=="agent"
        html=f"<a href='/' class='btn btn-sm btn-outline-light mb-3'>Back</a><div class='card-dark'><div class='text-center'><div style='width:90px;height:90px;background:linear-gradient(135deg,#fbbf24,#f59e0b);border-radius:18px;display:flex;align-items:center;justify-content:center;font-size:40px;font-weight:900;color:#111827;margin:auto'>{initial}</div><h4 style='color:white;margin-top:12px'>{data.get('NAME','')}</h4><small style='color:#94a3b8'>{data.get('TENCENT_ID','')}</small><div class='mt-2'><small style='color:#94a3b8'>Target: {target}h | {round(pct,1)}%</small><div class='progress' style='height:8px;width:200px;margin:auto;background:#0f172a'><div class='progress-bar' style='width:{min(100,pct)}%;background:{bar_color}'></div></div></div></div>"
        html+=f"<div class='row g-2 mt-3'><div class='col-4'><div class='kpi' style='border:1px solid #22c55e'><div class='label'>NORMAL</div><div class='val-big' style='color:#22c55e'>{n}h</div></div></div><div class='col-4'><div class='kpi' style='border:1px solid #3b82f6'><div class='label'>RESTDAY</div><div class='val-big' style='color:#3b82f6'>{r}h</div></div></div><div class='col-4'><div class='kpi' style='border:1px solid #ef4444'><div class='label'>LOSS</div><div class='val-big' style='color:#ef4444'>{loss}h</div></div></div><div class='col-6'><div class='kpi' style='border:1px solid #22c55e'><div class='label'>TOTAL</div><div class='val-big' style='color:#22c55e'>{tot}h</div></div></div><div class='col-6'><div class='kpi' style='border:1px solid #fbbf24'><div class='label'>NET</div><div class='val-big' style='color:#fbbf24'>+{net}h</div></div></div><div class='col-6'><div class='kpi' style='border:1px solid #f97316'><div class='label'>AHT</div><div class='val-big' style='color:#f97316'>{la}m</div></div></div><div class='col-6'><div class='kpi' style='border:1px solid #8b5cf6'><div class='label'>QA</div><div class='val-big' style='color:#8b5cf6'>{lq}%</div></div></div></div>"
        html+=f"""
        <div class="row g-3 mt-4">
          <div class="col-12 col-md-6"><div class="chart-card"><h6 style="color:#fbbf24">OT Trend</h6><canvas id="indOT"></canvas></div></div>
          <div class="col-12 col-md-6"><div class="chart-card"><h6 style="color:#8b5cf6">QA & AHT</h6><canvas id="indQA"></canvas></div></div>
        </div>
        <script>
        try{{
          new Chart(document.getElementById('indOT'), {{type:'line', data:{{labels:{ind_labels}, datasets:[{{label:'Total OT', data:{ind_tot}, borderColor:'#fbbf24', backgroundColor:'#fbbf2433', fill:true, tension:0.4}},{{label:'Loss', data:{ind_loss}, borderColor:'#ef4444'}}] }}, options:{{responsive:true}} }});
          new Chart(document.getElementById('indQA'), {{type:'line', data:{{labels:{ind_labels}, datasets:[{{label:'QA %', data:{ind_qa}, borderColor:'#8b5cf6'}},{{label:'AHT m', data:{ind_aht}, borderColor:'#f97316'}}] }}, options:{{responsive:true}} }});
        }}catch(e){{console.log(e)}}
        </script>
        """
        if is_agent:
            html+=f"""
            <div class="card-dark mt-3" style="border:1px solid #fbbf24">
              <h6 style="color:#fbbf24">My Account</h6>
              <p style="color:#94a3b8;font-size:11px">View only. Change password below.</p>
              <a href="/change_password" class="btn btn-warning w-100">Change Password</a>
            </div>
            </div>
            """
            return page(html)
        log_rows=""
        for l in logs:
            log_rows+=f"<tr><td>{l.get('date','')}</td><td>{l.get('type')}</td><td>{l.get('hours')}h</td><td>{l.get('reason','')}</td><td><a href='/delete_log/{aid}/{l.get('log_id','')}' class='btn btn-sm btn-outline-danger'>X</a></td></tr>"
        if not log_rows: log_rows="<tr><td colspan=5 style='text-align:center;color:#64748b'>No logs</td></tr>"
        perf_rows=""
        for l in plogs:
            unit="m" if l.get("type")=="AHT" else "%"
            perf_rows+=f"<tr><td>{l.get('date','')}</td><td>{l.get('type')}</td><td>{l.get('value')}{unit}</td><td>{l.get('reason','')}</td><td><a href='/delete_perf/{aid}/{l.get('log_id','')}' class='btn btn-sm btn-outline-danger'>X</a></td></tr>"
        if not perf_rows: perf_rows="<tr><td colspan=5 style='text-align:center;color:#64748b'>No logs</td></tr>"
        html+=f"""
        <div class="card-dark mt-3" style="border:1px solid #334155">
          <h6 style="color:#fbbf24">Target OT</h6>
          <form method="POST" action="/set_target/{aid}" class="row g-2">
            <div class="col-6"><input name="target" type="number" step="0.5" class="form-control form-control-sm" value="{target}"></div>
            <div class="col-6"><button class="btn btn-sm btn-warning w-100">Update Target</button></div>
          </form>
        </div>
        <div class="card-dark mt-3" style="border:1px solid #ef4444">
          <h6 style="color:#ef4444">Password Management - No current needed to reset</h6>
          <p style="color:#94a3b8;font-size:11px">Current: <span style="color:#fbbf24">{data.get("LOGIN_PASS") or data.get("TENCENT_ID") or "1234 (default = Tencent ID)"}</span> | User: {data.get("TENCENT_ID")}</p>
          <form method="POST" action="/reset_password/{aid}" class="row g-2">
            <div class="col-6"><input name="new_pass" type="text" class="form-control form-control-sm" placeholder="Leave blank = reset to Tencent ID"></div>
            <div class="col-6"><button class="btn btn-sm btn-danger w-100">Reset / Set New Password</button></div>
          </form>
          <small style="color:#64748b">Admin can reset without knowing current. Blank = reset to Tencent ID.</small>
        </div>
        """
        html+=f"<div class='row g-2 mt-4'><div class='col-6'><div class='card-dark' style='border:1px solid #22c55e'><h6 style='color:#22c55e'>Add Normal OT</h6><form method='POST' action='/add_ot/{aid}' class='row g-2'><input type='hidden' name='type' value='NORMAL_OT'><div class='col-6'><input name='hours' type='number' step='0.5' class='form-control form-control-sm' required></div><div class='col-6'><input name='date' type='date' class='form-control form-control-sm' value='{datetime.now(PH_TZ).strftime('%Y-%m-%d')}'></div><div class='col-12'><input name='reason' class='form-control form-control-sm' placeholder='Reason'></div><div class='col-12'><button class='btn w-100 mt-1' style='background:#22c55e;color:white'>Add Normal</button></div></form></div></div><div class='col-6'><div class='card-dark' style='border:1px solid #3b82f6'><h6 style='color:#3b82f6'>Add Restday OT</h6><form method='POST' action='/add_ot/{aid}' class='row g-2'><input type='hidden' name='type' value='RESTDAY_OT'><div class='col-6'><input name='hours' type='number' step='0.5' class='form-control form-control-sm' required></div><div class='col-6'><input name='date' type='date' class='form-control form-control-sm' value='{datetime.now(PH_TZ).strftime('%Y-%m-%d')}'></div><div class='col-12'><input name='reason' class='form-control form-control-sm' placeholder='Reason'></div><div class='col-12'><button class='btn w-100 mt-1' style='background:#3b82f6;color:white'>Add Restday</button></div></form></div></div><div class='col-6'><div class='card-dark' style='border:1px solid #f97316'><h6 style='color:#f97316'>Add AHT</h6><form method='POST' action='/add_perf/{aid}' class='row g-2'><input type='hidden' name='type' value='AHT'><div class='col-6'><input name='value' type='number' step='0.1' class='form-control form-control-sm' required></div><div class='col-6'><input name='date' type='date' class='form-control form-control-sm' value='{datetime.now(PH_TZ).strftime('%Y-%m-%d')}'></div><div class='col-12'><input name='reason' class='form-control form-control-sm' placeholder='Notes'></div><div class='col-12'><button class='btn w-100 mt-1' style='background:#f97316;color:white'>Add AHT</button></div></form></div></div><div class='col-6'><div class='card-dark' style='border:1px solid #8b5cf6'><h6 style='color:#8b5cf6'>Add QA</h6><form method='POST' action='/add_perf/{aid}' class='row g-2'><input type='hidden' name='type' value='QA'><div class='col-6'><input name='value' type='number' step='0.1' class='form-control form-control-sm' required></div><div class='col-6'><input name='date' type='date' class='form-control form-control-sm' value='{datetime.now(PH_TZ).strftime('%Y-%m-%d')}'></div><div class='col-12'><input name='reason' class='form-control form-control-sm' placeholder='Notes'></div><div class='col-12'><button class='btn w-100 mt-1' style='background:#8b5cf6;color:white'>Add QA</button></div></form></div></div><div class='col-12'><div class='card-dark' style='border:1px solid #ef4444'><h6 style='color:#ef4444'>Add Loss</h6><form method='POST' action='/add_ot/{aid}' class='row g-2'><input type='hidden' name='type' value='LOSS'><div class='col-4'><input name='hours' type='number' step='0.5' class='form-control form-control-sm' required></div><div class='col-4'><input name='date' type='date' class='form-control form-control-sm' value='{datetime.now(PH_TZ).strftime('%Y-%m-%d')}'></div><div class='col-4'><select name='loss_type' class='form-select form-select-sm'><option>Late</option><option>Absent</option></select></div><div class='col-12'><input name='reason' class='form-control form-control-sm' placeholder='Reason'></div><div class='col-12'><button class='btn w-100 mt-1' style='background:#ef4444;color:white'>Add Loss</button></div></form></div></div></div>"
        html+=f"<div class='mt-4'><h6 style='color:white'>OT History</h6><div class='table-responsive'><table class='table table-sm'><thead><tr><th>Date</th><th>Type</th><th>Hrs</th><th>Reason</th><th></th></tr></thead><tbody>{log_rows}</tbody></table></div></div><div class='mt-3'><h6 style='color:white'>AHT & QA History</h6><div class='table-responsive'><table class='table table-sm'><thead><tr><th>Date</th><th>Type</th><th>Value</th><th>Notes</th><th></th></tr></thead><tbody>{perf_rows}</tbody></table></div></div></div>"
        return page(html)
    except Exception as e:
        return page(f"<h5 style='color:#ef4444'>View error: {str(e)}</h5><pre style='color:white;font-size:10px'>{traceback.format_exc()}</pre><a href='/' class='btn btn-sm btn-outline-light'>Back</a>")

@app.route("/change_password", methods=["GET","POST"])
@login_required
def change_password():
    msg=""; color="#22c55e"
    if request.method=="POST":
        try:
            current=request.form.get("current","")
            new=request.form.get("new","")
            confirm=request.form.get("confirm","")
            if new!=confirm:
                msg="New and confirm do not match!"; color="#ef4444"
            else:
                if session.get("role") in ["admin","team_leader","qa"]:
                    u=session.get("user")
                    if USERS.get(u) and (USERS[u]["pass"]==current or session.get("role")=="admin"):
                        USERS[u]["pass"]=new
                        msg="Password updated!"
                    else:
                        msg="Current incorrect!"; color="#ef4444"
                else:
                    aid=session.get("agent_id")
                    agent=None
                    for a in get_all():
                        if str(a.get("id"))==str(aid):
                            agent=a; break
                    if agent:
                        stored=str(agent.get("LOGIN_PASS") or agent.get("TENCENT_ID") or "1234")
                        if current!=stored:
                            msg="Current incorrect! Default is Tencent ID"; color="#ef4444"
                        else:
                            if db_root:
                                db_root.child(f"agents/{aid}/LOGIN_PASS").set(new)
                                msg="Password updated!"
                    else:
                        msg="Agent not found"; color="#ef4444"
        except Exception as e:
            msg=f"Error: {str(e)}"; color="#ef4444"
    html=f"<a href='/' class='btn btn-sm btn-outline-light mb-3'>Back</a><div class='card-dark' style='max-width:500px;margin:auto'><h5 style='color:white'>Change Password</h5><p style='color:#94a3b8;font-size:12px'>{session.get('name')} - {session.get('role')}</p>"
    if msg:
        html+=f"<div style='background:{color}22;border:1px solid {color};color:{color};padding:8px;border-radius:8px;font-size:12px'>{msg}</div>"
    html+="""
      <form method="POST" class="mt-3">
        <label class="label">CURRENT</label><input name="current" type="password" class="form-control mb-2" required>
        <label class="label">NEW</label><input name="new" type="password" class="form-control mb-2" required>
        <label class="label">CONFIRM</label><input name="confirm" type="password" class="form-control mb-3" required>
        <button class="btn btn-warning w-100">Update Password</button>
      </form>
    </div>
    """
    return page(html)

@app.route("/reset_password/<aid>", methods=["POST"])
@login_required
def reset_password(aid):
    if session.get("role")!="admin":
        return redirect("/")
    try:
        new_pass=request.form.get("new_pass","").strip()
        if not new_pass:
            for a in get_all():
                if str(a.get("id"))==str(aid):
                    new_pass=str(a.get("TENCENT_ID"))
                    break
        if db_root and new_pass:
            db_root.child(f"agents/{aid}/LOGIN_PASS").set(new_pass)
            db_root.child("login_logs").push({"user": session.get("user"),"name": session.get("name"),"role": "admin","type": f"RESET_PASSWORD to {new_pass}","timestamp": datetime.now(PH_TZ).strftime("%Y-%m-%d %I:%M:%S %p"),"date": datetime.now(PH_TZ).strftime("%Y-%m-%d"),"agent_id": aid})
    except Exception as e:
        print(f"reset error {e}")
    return redirect(f"/view/{aid}")

@app.route("/set_target/<aid>", methods=["POST"])
@login_required
def set_target(aid):
    try:
        target=request.form.get("target","20")
        if db_root:
            db_root.child(f"agents/{aid}/TARGET_OT").set(target)
    except: pass
    return redirect(f"/view/{aid}")

@app.route("/add_ot/<aid>", methods=["POST"])
@login_required
def add_ot(aid):
    if session.get("role")=="agent":
        return redirect(f"/view/{aid}")
    try:
        typ=request.form.get("type","NORMAL_OT")
        hours=request.form.get("hours","0")
        date=request.form.get("date",datetime.now(PH_TZ).strftime("%Y-%m-%d"))
        reason=request.form.get("reason","")
        if db_root:
            db_root.child("ot_logs").push({"agent_id":str(aid),"type":typ,"hours":str(hours),"date":date,"reason":reason})
    except: pass
    return redirect("/view/"+str(aid))

@app.route("/add_perf/<aid>", methods=["POST"])
@login_required
def add_perf(aid):
    if session.get("role")=="agent":
        return redirect(f"/view/{aid}")
    try:
        typ=request.form.get("type","AHT")
        value=request.form.get("value","0")
        date=request.form.get("date",datetime.now(PH_TZ).strftime("%Y-%m-%d"))
        reason=request.form.get("reason","")
        if db_root:
            db_root.child("perf_logs").push({"agent_id":str(aid),"type":typ,"value":str(value),"date":date,"reason":reason})
    except: pass
    return redirect("/view/"+str(aid))

@app.route("/delete_log/<aid>/<log_id>")
@login_required
def delete_log(aid, log_id):
    if session.get("role")=="agent":
        return redirect(f"/view/{aid}")
    try:
        if db_root: db_root.child("ot_logs/"+log_id).delete()
    except: pass
    return redirect("/view/"+str(aid))

@app.route("/delete_perf/<aid>/<log_id>")
@login_required
def delete_perf(aid, log_id):
    if session.get("role")=="agent":
        return redirect(f"/view/{aid}")
    try:
        if db_root: db_root.child("perf_logs/"+log_id).delete()
    except: pass
    return redirect("/view/"+str(aid))

@app.route("/agents")
@login_required
def agents_list():
    if session.get("role")=="agent":
        return redirect(f"/view/{session.get('agent_id')}")
    q = request.args.get("q","").lower().strip()
    agents=get_all()
    filtered=agents
    if q:
        filtered=[a for a in agents if q in str(a.get("NAME","")).lower() or q in str(a.get("TENCENT_ID","")).lower()]
    rows=""
    for a in filtered:
        logs=get_ot(a.get("id"))
        n,r,tot,loss,net=calc(logs)
        rows+=f"<tr><td>{a.get('id')}</td><td><a href='/view/{a.get('id')}' style='color:white'><b>{a.get('NAME','')}</b><br><small style='color:#94a3b8'>{a.get('TENCENT_ID')}</small></a></td><td>{n}h</td><td>{r}h</td><td>{loss}h</td><td><a href='/view/{a.get('id')}' class='btn btn-sm btn-warning'>View</a></td></tr>"
    if not rows:
        rows="<tr><td colspan=6 style='text-align:center;color:#64748b'>No agents</td></tr>"
    top = f"<div class='d-flex justify-content-between'><h5 style='color:white'>All Agents ({len(filtered)}/{len(agents)})</h5><div class='d-flex gap-2'><form method='GET' class='d-flex gap-2'><input name='q' value='{q}' class='form-control form-control-sm' placeholder='Search...' style='width:180px'><button class='btn btn-sm btn-warning'>Search</button></form><a href='/' class='btn btn-sm btn-outline-light'>Dashboard</a></div></div>"
    return page(top + f"<div class='card-dark mt-3'><div class='table-responsive'><table class='table'><thead><tr><th>ID</th><th>AGENT</th><th>N</th><th>RD</th><th>LOSS</th><th></th></tr></thead><tbody>{rows}</tbody></table></div></div>")

@app.route("/logs")
@login_required
def login_logs():
    if session.get("role") not in ["admin"]:
        return redirect("/")
    try:
        logs_raw = db_root.child("login_logs").get() if db_root else {}
        logs=[]
        if isinstance(logs_raw, dict):
            for lid, v in logs_raw.items():
                if isinstance(v, dict):
                    logs.append(v)
        logs_sorted=sorted(logs, key=lambda x: x.get("timestamp",""), reverse=True)[:100]
        rows=""
        for l in logs_sorted:
            color="#22c55e" if l.get("type")=="LOGIN" else "#ef4444" if l.get("type")=="LOGOUT" else "#fbbf24"
            rows+=f"<tr><td style='color:#cbd5e1'>{l.get('timestamp','')}</td><td><b style='color:white'>{l.get('name','')}</b><br><small style='color:#94a3b8'>{l.get('user','')}</small></td><td><span class='badge' style='background:{color}'>{l.get('type')}</span></td><td>{l.get('role')}</td><td>{l.get('agent_id','')}</td></tr>"
        if not rows:
            rows="<tr><td colspan=5 style='text-align:center;color:#64748b'>No logs yet</td></tr>"
        html="<div class='d-flex justify-content-between'><h5 style='color:white'>Login / Logout Logs</h5><a href='/' class='btn btn-sm btn-outline-light'>Dashboard</a></div>"
        html+=f"<div class='card-dark mt-3'><div class='table-responsive'><table class='table table-sm'><thead><tr><th>Time</th><th>User</th><th>Type</th><th>Role</th><th>ID</th></tr></thead><tbody>{rows}</tbody></table></div></div>"
        return page(html)
    except Exception as e:
        return page(f"<pre>{traceback.format_exc()}</pre>")

@app.route("/leaderboard")
@login_required
def leaderboard():
    try:
        agents=get_all()
        stats=[]
        for a in agents:
            logs=get_ot(a.get("id"))
            n,r,tot,loss,net=calc(logs)
            stats.append({"name":a.get("NAME",""),"tot":tot})
        top_ot=sorted(stats, key=lambda x: x["tot"], reverse=True)[:10]
        html="<h5 style='color:white'>Leaderboard</h5><div class='card-dark mt-3'><table class='table table-sm'><thead><tr><th>#</th><th>Agent</th><th>Total OT</th></tr></thead><tbody>"
        for idx, a in enumerate(top_ot):
            medal="🥇" if idx==0 else "🥈" if idx==1 else "🥉" if idx==2 else f"{idx+1}"
            html+=f"<tr><td>{medal}</td><td>{a['name']}</td><td style='color:#fbbf24'>{a['tot']}h</td></tr>"
        html+="</tbody></table></div>"
        return page(html)
    except Exception as e:
        return page(f"<pre>{traceback.format_exc()}</pre>")

@app.route("/export")
@login_required
def export_page():
    html="<h5 style='color:white'>Export</h5><div class='row g-3 mt-2'><div class='col-6'><div class='card-dark'><a href='/export/csv' class='btn btn-success w-100'>CSV</a></div></div><div class='col-6'><div class='card-dark'><a href='/export/pdf' class='btn btn-warning w-100'>PDF</a></div></div></div>"
    return page(html)

@app.route("/export/csv")
@login_required
def export_csv():
    agents=get_all()
    output=io.StringIO()
    writer=csv.writer(output)
    writer.writerow(["ID","NAME","TENCENT_ID","TOTAL_OT","LOSS"])
    for a in agents:
        logs=get_ot(a.get("id")); n,r,tot,loss,net=calc(logs)
        writer.writerow([a.get("id"),a.get("NAME"),a.get("TENCENT_ID"),tot,loss])
    return Response(output.getvalue(), mimetype="text/csv", headers={"Content-Disposition":"attachment;filename=export.csv"})

@app.route("/export/pdf")
@login_required
def export_pdf():
    agents=get_all()
    html="<html><body><h2>Report</h2><table border=1><tr><th>ID</th><th>NAME</th><th>TOTAL</th></tr>"
    for a in agents:
        logs=get_ot(a.get("id")); n,r,tot,loss,net=calc(logs)
        html+=f"<tr><td>{a.get('id')}</td><td>{a.get('NAME')}</td><td>{tot}</td></tr>"
    html+="</table></body></html>"
    return html

@app.route("/bulk", methods=["GET","POST"])
@login_required
def bulk_import():
    msg=""
    if request.method=="POST":
        csv_text=request.form.get("csv_text","")
        if csv_text:
            try:
                reader=csv.DictReader(io.StringIO(csv_text))
                count=0
                for row in reader:
                    agent_id=row.get("agent_id") or row.get("ID")
                    typ=row.get("type","NORMAL_OT")
                    hours=row.get("hours") or row.get("value")
                    date=row.get("date",datetime.now(PH_TZ).strftime("%Y-%m-%d"))
                    if not agent_id or not hours: continue
                    if typ in ["AHT","QA"]:
                        db_root.child("perf_logs").push({"agent_id":str(agent_id),"type":typ,"value":str(hours),"date":date,"reason":"Bulk"})
                    else:
                        db_root.child("ot_logs").push({"agent_id":str(agent_id),"type":typ,"hours":str(hours),"date":date,"reason":"Bulk"})
                    count+=1
                msg=f"Imported {count}"
            except Exception as e:
                msg=f"Error: {e}"
    html=f"<h5 style='color:white'>Bulk Import</h5><div style='color:#22c55e'>{msg}</div><div class='card-dark mt-3'><form method='POST'><textarea name='csv_text' class='form-control' rows='10'></textarea><button class='btn btn-warning w-100 mt-2'>Import</button></form></div>"
    return page(html)

if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",5000)))
