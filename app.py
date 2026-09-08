
import os, json, io, csv
from flask import Flask, request, redirect, session, Response, send_file
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

def role_required(roles):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if not session.get("logged_in"):
                return redirect("/login")
            if session.get("role") not in roles and session.get("role")!="admin":
                return "<h3 style='color:white;text-align:center;margin-top:100px'>Access Denied</h3><a href='/'>Back</a>", 403
            return f(*args, **kwargs)
        return decorated
    return decorator

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

def get_all_ot_logs():
    logs = db_root.child("ot_logs").get() if db_root else {}
    return [v for v in logs.values() if isinstance(v, dict)] if isinstance(logs, dict) else []

def get_all_perf_logs():
    logs = db_root.child("perf_logs").get() if db_root else {}
    return [v for v in logs.values() if isinstance(v, dict)] if isinstance(logs, dict) else []

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

def calc(logs):
    normal=sum(float(l.get("hours",0)) for l in logs if l.get("type")=="NORMAL_OT")
    restday=sum(float(l.get("hours",0)) for l in logs if l.get("type")=="RESTDAY_OT")
    loss=sum(float(l.get("hours",0)) for l in logs if l.get("type")=="LOSS")
    return normal,restday,normal+restday,loss,(normal+restday-loss)

def calc_perf(logs):
    aht_list=[float(l.get("value",0)) for l in logs if l.get("type")=="AHT"]
    qa_list=[float(l.get("value",0)) for l in logs if l.get("type")=="QA"]
    avg_aht = sum(aht_list)/len(aht_list) if aht_list else 0
    avg_qa = sum(qa_list)/len(qa_list) if qa_list else 0
    latest_aht = aht_list[-1] if aht_list else 0
    latest_qa = qa_list[-1] if qa_list else 0
    return latest_aht, latest_qa, avg_aht, avg_qa, aht_list, qa_list

BASE_HEAD = """<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1">
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
<link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.0/font/bootstrap-icons.css" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
:root{--bg:#0b1120;--card:#151e32;--border:#2d3748;--text:#f1f5f9;--muted:#94a3b8}
.light-mode{--bg:#f1f5f9;--card:#ffffff;--border:#e2e8f0;--text:#0f172a;--muted:#64748b}
body{background:var(--bg);color:var(--text);font-family:Inter,system-ui;transition:all 0.3s}
.card-dark{background:var(--card);border:1px solid var(--border);border-radius:20px;padding:16px;box-shadow:0 4px 12px rgba(0,0,0,0.3)}
.kpi{padding:12px 8px;border-radius:16px;background:var(--card);border:1px solid var(--border);text-align:center;min-height:110px;height:110px;display:flex;flex-direction:column;justify-content:center;align-items:center}
.label{font-size:9px;color:var(--muted);text-transform:uppercase;letter-spacing:.6px;font-weight:600;line-height:11px;min-height:22px;display:flex;align-items:center;justify-content:center}
.val-big{font-size:22px;font-weight:800;margin-top:2px;line-height:24px}
.chart-card{background:var(--card);border:1px solid var(--border);border-radius:20px;padding:16px}
.table thead th{background:#0f172a!important;color:#fbbf24!important;font-size:10px;text-transform:uppercase;letter-spacing:.5px;border:none!important}
.table tbody td{background:var(--card)!important;border-color:var(--border)!important;color:var(--text)!important;padding:12px 8px}
input,select{background:#0f172a!important;color:#f1f5f9!important;border:1px solid #334155!important}
.light-mode input,.light-mode select{background:#ffffff!important;color:#0f172a!important;border:1px solid #e2e8f0!important}
.podium{height:100px;display:flex;align-items:flex-end;justify-content:center;gap:8px}
.podium-bar{width:60px;border-radius:8px 8px 0 0;display:flex;flex-direction:column;justify-content:flex-end;align-items:center;padding:8px;color:white;font-weight:700}
</style></head><body>
<nav class="navbar p-3" style="background:#0f172a;border-bottom:1px solid #1e293b"><div class="container-fluid">
<a class="navbar-brand fw-bold text-light" href="/">TEAM SHINE M9 <small style="color:#fbbf24;font-size:11px">TEAM LEADER</small> <small style="color:#94a3b8;font-size:9px" id="roleBadge"></small></a>
<div class="d-flex gap-1 align-items-center">
<button onclick="toggleTheme()" class="btn btn-sm btn-outline-light" id="themeBtn">🌙</button>
<a href="/leaderboard" class="btn btn-sm btn-outline-warning">🏆</a>
<a href="/export" class="btn btn-sm btn-outline-light">📥</a>
<a href="/bulk" class="btn btn-sm btn-outline-light">📤</a>
<a href="/logs" class="btn btn-sm btn-outline-light">📋 Logs</a> <a href="/agents" class="btn btn-sm btn-outline-light">Agents</a> 
<a href="/logout" class="btn btn-sm btn-outline-danger">Logout</a>
</div>
</div></nav><div class="container-fluid p-3" style="max-width:1200px;margin:auto">
<script>
function toggleTheme(){
  const body=document.body;
  body.classList.toggle('light-mode');
  localStorage.setItem('theme', body.classList.contains('light-mode') ? 'light' : 'dark');
  document.getElementById('themeBtn').innerText= body.classList.contains('light-mode') ? '🌙' : '☀️';
}
window.addEventListener('DOMContentLoaded',()=>{
  if(localStorage.getItem('theme')=='light'){document.body.classList.add('light-mode'); document.getElementById('themeBtn').innerText='🌙';}
  const role = localStorage.getItem('userRole');
  if(role){document.getElementById('roleBadge').innerText='| '+role;}
});
</script>
"""

BASE_FOOT = """
</div>
<footer style="text-align:center;padding:24px;color:#64748b;font-size:12px;border-top:1px solid #1e293b;margin-top:30px">
  <div>Developed By : <span style="color:#fbbf24;font-weight:700">Moises Gamboa</span> | Computer Engineer</div>
</footer></body></html>
"""

def page(c):
    return BASE_HEAD + c + BASE_FOOT

@app.route("/login", methods=["GET","POST"])
def login():
    error=""
    if request.method=="POST":
        u=request.form.get("username","").strip()
        p=request.form.get("password","").strip()
        user=USERS.get(u)
        if user and user["pass"]==p:
            session["logged_in"]=True
            session["user"]=u
            session["role"]=user["role"]
            session["name"]=user["name"]
            session["agent_id"]=None
            if db_root:
                try:
                    db_root.child("login_logs").push({
                        "user": u,
                        "name": user["name"],
                        "role": user["role"],
                        "type": "LOGIN",
                        "timestamp": datetime.now(PH_TZ).strftime("%Y-%m-%d %I:%M:%S %p"),
                        "date": datetime.now(PH_TZ).strftime("%Y-%m-%d"),
                        "agent_id": "ADMIN"
                    })
                except: pass
            return f"<script>localStorage.setItem('userRole','{user['role']} - {user['name']}');window.location='/';</script>"
        # Check agent login - username = TENCENT_ID or NAME
        found_agent=None
        for a in get_all():
            tid=str(a.get("TENCENT_ID","")).strip()
            name=str(a.get("NAME","")).lower()
            aid=str(a.get("id"))
            # Username can be TENCENT_ID, ID, or NAME (no space lower)
            if u.lower()==tid.lower() or u.lower()==aid.lower() or u.lower()==name or u.lower()==name.replace(",","").replace(" ","").lower() or u.lower()==tid:
                found_agent=a
                break
            # Also check if agent has custom username
            if a.get("USERNAME","") and u.lower()==str(a.get("USERNAME")).lower():
                found_agent=a
                break
        if found_agent:
            # Password check: custom LOGIN_PASS or TENCENT_ID or default 1234
            stored_pass=str(found_agent.get("LOGIN_PASS") or found_agent.get("TENCENT_ID") or "1234").strip()
            if p==stored_pass or p==str(found_agent.get("TENCENT_ID")) or (stored_pass=="1234" and p=="1234"):
                session["logged_in"]=True
                session["user"]=found_agent.get("TENCENT_ID")
                session["role"]="agent"
                session["name"]=found_agent.get("NAME")
                session["agent_id"]=found_agent.get("id")
                if db_root:
                    try:
                        db_root.child("login_logs").push({
                            "user": found_agent.get("TENCENT_ID"),
                            "name": found_agent.get("NAME"),
                            "role": "agent",
                            "type": "LOGIN",
                            "timestamp": datetime.now(PH_TZ).strftime("%Y-%m-%d %I:%M:%S %p"),
                            "date": datetime.now(PH_TZ).strftime("%Y-%m-%d"),
                            "agent_id": found_agent.get("id")
                        })
                    except: pass
                return f"<script>localStorage.setItem('userRole','agent - {found_agent.get('NAME')}');window.location='/view/{found_agent.get('id')}';</script>"
            else:
                error="Invalid agent password! Default is Tencent ID"
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
        <small style="color:#94a3b8">Team Access</small>
        <form method="POST" class="mt-4 text-start">
            <label style="font-size:11px;color:#94a3b8">USERNAME</label>
            <input name="username" class="form-control mb-3" placeholder="Enter username" required>
            <label style="font-size:11px;color:#94a3b8">PASSWORD</label>
            <input name="password" type="password" class="form-control mb-3" placeholder="Enter password" required>
            <div style="color:#ef4444;font-size:12px;margin-bottom:12px">{error}</div>
            <button class="btn btn-warning w-100" style="font-weight:700;padding:12px">Login</button>
            <div class="mt-3 text-center"><small style="color:#64748b;font-size:11px">Agent: Use Tencent ID as username & password<br>Admin: Use your admin account</small></div>
        </form>
        <div style="margin-top:20px;padding-top:16px;border-top:1px solid #1e293b;text-align:center">
            <small style="color:#94a3b8">Developed By : <span style="color:#fbbf24">Moises Gamboa</span> | Computer Engineer</small>
        </div>
    </div></body></html>
    """


@app.route("/logout")
def logout():
    if db_root and session.get("logged_in"):
        try:
            db_root.child("login_logs").push({
                "user": session.get("user",""),
                "name": session.get("name",""),
                "role": session.get("role",""),
                "type": "LOGOUT",
                "timestamp": datetime.now(PH_TZ).strftime("%Y-%m-%d %I:%M:%S %p"),
                "date": datetime.now(PH_TZ).strftime("%Y-%m-%d"),
                "agent_id": session.get("agent_id","")
            })
        except: pass
    session.clear()
    return redirect("/login")

def parse_date(dstr):
    try:
        return datetime.strptime(dstr, "%Y-%m-%d")
    except:
        return None

def get_filtered_stats(period, year, month, quarter, week):
    ot_logs=get_all_ot_logs()
    perf_logs=get_all_perf_logs()
    filtered_ot=[]
    filtered_perf=[]
    for l in ot_logs:
        dt=parse_date(l.get("date",""))
        if not dt: continue
        if year and dt.year!=int(year): continue
        if period=="monthly" and month and dt.month!=int(month): continue
        if period=="quarterly" and quarter:
            q = (dt.month-1)//3 + 1
            if q!=int(quarter): continue
        if period=="weekly" and week:
            if dt.isocalendar()[1]!=int(week): continue
        filtered_ot.append(l)
    for l in perf_logs:
        dt=parse_date(l.get("date",""))
        if not dt: continue
        if year and dt.year!=int(year): continue
        if period=="monthly" and month and dt.month!=int(month): continue
        if period=="quarterly" and quarter:
            q = (dt.month-1)//3 + 1
            if q!=int(quarter): continue
        if period=="weekly" and week:
            if dt.isocalendar()[1]!=int(week): continue
        filtered_perf.append(l)
    labels=[]
    normal_data=[]
    restday_data=[]
    total_data=[]
    loss_data=[]
    net_data=[]
    aht_data=[]
    qa_data=[]
    if period=="daily":
        groups=defaultdict(list)
        for l in filtered_ot: groups[l.get("date")].append(l)
        sorted_dates=sorted(groups.keys())[-14:]
        for d in sorted_dates:
            logs=groups[d]
            n,r,tot,loss,net=calc(logs)
            labels.append(d[-5:])
            normal_data.append(n)
            restday_data.append(r)
            total_data.append(tot)
            loss_data.append(loss)
            net_data.append(net)
        pgroups=defaultdict(list)
        for l in filtered_perf: pgroups[l.get("date")].append(l)
        for d in sorted_dates:
            pl=pgroups.get(d,[])
            _,_,aa,qa,_,_=calc_perf(pl)
            aht_data.append(round(aa,1))
            qa_data.append(round(qa,1))
    elif period=="weekly":
        if week:
            groups=defaultdict(list)
            for l in filtered_ot: groups[l.get("date")].append(l)
            sorted_dates=sorted(groups.keys())
            for d in sorted_dates:
                logs=groups[d]
                n,r,tot,loss,net=calc(logs)
                labels.append(d[-5:])
                normal_data.append(n); restday_data.append(r); total_data.append(tot); loss_data.append(loss); net_data.append(net)
            pgroups=defaultdict(list)
            for l in filtered_perf: pgroups[l.get("date")].append(l)
            for d in sorted_dates:
                pl=pgroups.get(d,[])
                _,_,aa,qa,_,_=calc_perf(pl)
                aht_data.append(round(aa,1)); qa_data.append(round(qa,1))
        else:
            wgroups=defaultdict(list); pwgroups=defaultdict(list)
            for l in filtered_ot:
                dt=parse_date(l.get("date"))
                if not dt: continue
                key=f"{dt.year}-W{dt.isocalendar()[1]:02d}"; wgroups[key].append(l)
            for l in filtered_perf:
                dt=parse_date(l.get("date"))
                if not dt: continue
                key=f"{dt.year}-W{dt.isocalendar()[1]:02d}"; pwgroups[key].append(l)
            sorted_keys=sorted(wgroups.keys())[-12:]
            for k in sorted_keys:
                logs=wgroups[k]; n,r,tot,loss,net=calc(logs)
                labels.append(k)
                normal_data.append(n); restday_data.append(r); total_data.append(tot); loss_data.append(loss); net_data.append(net)
                pl=pwgroups.get(k,[]); _,_,aa,qa,_,_=calc_perf(pl); aht_data.append(round(aa,1)); qa_data.append(round(qa,1))
    elif period=="monthly":
        if month:
            groups=defaultdict(list)
            for l in filtered_ot: groups[l.get("date")].append(l)
            sorted_dates=sorted(groups.keys())
            for d in sorted_dates:
                logs=groups[d]; n,r,tot,loss,net=calc(logs)
                labels.append(d[-2:])
                normal_data.append(n); restday_data.append(r); total_data.append(tot); loss_data.append(loss); net_data.append(net)
            pgroups=defaultdict(list)
            for l in filtered_perf: pgroups[l.get("date")].append(l)
            for d in sorted_dates:
                pl=pgroups.get(d,[])
                _,_,aa,qa,_,_=calc_perf(pl)
                aht_data.append(round(aa,1)); qa_data.append(round(qa,1))
        else:
            mgroups=defaultdict(list); pmgroups=defaultdict(list)
            for l in filtered_ot:
                dt=parse_date(l.get("date"))
                if not dt: continue
                mgroups[dt.month].append(l)
            for l in filtered_perf:
                dt=parse_date(l.get("date"))
                if not dt: continue
                pmgroups[dt.month].append(l)
            for m in range(1,13):
                labels.append(calendar.month_abbr[m]); logs=mgroups.get(m,[])
                n,r,tot,loss,net=calc(logs)
                normal_data.append(n); restday_data.append(r); total_data.append(tot); loss_data.append(loss); net_data.append(net)
                pl=pmgroups.get(m,[]); _,_,aa,qa,_,_=calc_perf(pl); aht_data.append(round(aa,1)); qa_data.append(round(qa,1))
    elif period=="quarterly":
        if quarter:
            months=range((int(quarter)-1)*3+1, int(quarter)*3+1)
            mgroups=defaultdict(list); pmgroups=defaultdict(list)
            for l in filtered_ot:
                dt=parse_date(l.get("date"))
                if not dt: continue
                if dt.month in months: mgroups[dt.month].append(l)
            for l in filtered_perf:
                dt=parse_date(l.get("date"))
                if not dt: continue
                if dt.month in months: pmgroups[dt.month].append(l)
            for m in months:
                labels.append(calendar.month_abbr[m]); logs=mgroups.get(m,[])
                n,r,tot,loss,net=calc(logs)
                normal_data.append(n); restday_data.append(r); total_data.append(tot); loss_data.append(loss); net_data.append(net)
                pl=pmgroups.get(m,[]); _,_,aa,qa,_,_=calc_perf(pl); aht_data.append(round(aa,1)); qa_data.append(round(qa,1))
        else:
            for q in range(1,5):
                labels.append(f"Q{q}"); logs=[]
                for l in filtered_ot:
                    dt=parse_date(l.get("date"))
                    if not dt: continue
                    if (dt.month-1)//3+1==q: logs.append(l)
                n,r,tot,loss,net=calc(logs)
                normal_data.append(n); restday_data.append(r); total_data.append(tot); loss_data.append(loss); net_data.append(net)
                pl=[]
                for l in filtered_perf:
                    dt=parse_date(l.get("date"))
                    if not dt: continue
                    if (dt.month-1)//3+1==q: pl.append(l)
                _,_,aa,qa,_,_=calc_perf(pl); aht_data.append(round(aa,1)); qa_data.append(round(qa,1))
    else:
        ygroups=defaultdict(list); pygroups=defaultdict(list)
        for l in filtered_ot:
            dt=parse_date(l.get("date"))
            if not dt: continue
            ygroups[dt.year].append(l)
        for l in filtered_perf:
            dt=parse_date(l.get("date"))
            if not dt: continue
            pygroups[dt.year].append(l)
        sorted_years=sorted(ygroups.keys())[-5:]
        for y in sorted_years:
            labels.append(str(y)); logs=ygroups.get(y,[])
            n,r,tot,loss,net=calc(logs)
            normal_data.append(n); restday_data.append(r); total_data.append(tot); loss_data.append(loss); net_data.append(net)
            pl=pygroups.get(y,[]); _,_,aa,qa,_,_=calc_perf(pl); aht_data.append(round(aa,1)); qa_data.append(round(qa,1))
        if not labels:
            labels=[calendar.month_abbr[m] for m in range(1,13)]
            for m in range(1,13):
                logs=[l for l in filtered_ot if parse_date(l.get("date")) and parse_date(l.get("date")).month==m]
                n,r,tot,loss,net=calc(logs)
                normal_data.append(n); restday_data.append(r); total_data.append(tot); loss_data.append(loss); net_data.append(net)
                pl=[l for l in filtered_perf if parse_date(l.get("date")) and parse_date(l.get("date")).month==m]
                _,_,aa,qa,_,_=calc_perf(pl)
                aht_data.append(round(aa,1)); qa_data.append(round(qa,1))
    return labels, normal_data, restday_data, total_data, loss_data, net_data, aht_data, qa_data

@app.route("/")
@login_required
def dashboard():
    if session.get("role")=="agent" and session.get("agent_id"):
        return redirect(f"/view/{session.get('agent_id')}")

    period=request.args.get("period","monthly")
    year=request.args.get("year",str(datetime.now(PH_TZ).year))
    month=request.args.get("month","")
    quarter=request.args.get("quarter","")
    week=request.args.get("week","")
    agents=get_all()
    team_normal=0; team_restday=0; team_loss=0; team_total=0; team_net=0
    agent_stats=[]
    for a in agents:
        logs=get_ot(a.get("id"))
        n,r,tot,loss,net=calc(logs)
        team_normal+=n; team_restday+=r; team_loss+=loss; team_total+=tot; team_net+=net
        plogs=get_perf(a.get("id"))
        la,lq,aa,qa,_,_=calc_perf(plogs)
        target=float(a.get("TARGET_OT",20))
        pct = (tot/target*100) if target>0 else 0
        agent_stats.append({"id":a.get("id"),"name":a.get("NAME",""),"tid":a.get("TENCENT_ID",""),"n":n,"r":r,"tot":tot,"loss":loss,"net":net,"aht":la,"qa":lq,"avg_aht":aa,"avg_qa":qa,"target":target,"pct":pct})
    agent_stats_sorted=sorted(agent_stats, key=lambda x: x["tot"], reverse=True)
    avg_ot=team_total/len(agents) if agents else 0
    labels, nd, rd, td, ld, netd, ahtd, qad = get_filtered_stats(period, year, month, quarter, week)
    team_aht_vals=[a["avg_aht"] for a in agent_stats if a["avg_aht"]>0]
    team_qa_vals=[a["avg_qa"] for a in agent_stats if a["avg_qa"]>0]
    team_avg_aht = sum(team_aht_vals)/len(team_aht_vals) if team_aht_vals else 0
    team_avg_qa = sum(team_qa_vals)/len(team_qa_vals) if team_qa_vals else 0
    alerts_html=""
    critical_agents=[a for a in agent_stats if a["loss"]>=4]
    low_qa=[a for a in agent_stats if a["qa"]>0 and a["qa"]<80]
    high_aht=[a for a in agent_stats if a["aht"]>10]
    if critical_agents or low_qa or high_aht:
        alerts_html+="<div class='card-dark mb-3' style='border:1px solid #ef4444;background:#450a0a'>"
        alerts_html+="<h6 style='color:#fca5a5'><i class='bi bi-bell-fill'></i> Alerts</h6>"
        for a in critical_agents:
            alerts_html+=f"<div style='color:#fca5a5;font-size:12px'>{a['name']} - {a['loss']}h Loss</div>"
        for a in low_qa:
            alerts_html+=f"<div style='color:#fbbf24;font-size:12px'>{a['name']} - QA {a['qa']}%</div>"
        for a in high_aht:
            alerts_html+=f"<div style='color:#fdba74;font-size:12px'>{a['name']} - AHT {a['aht']}m</div>"
        alerts_html+="</div>"
    filter_html = f"""
    <div class="card-dark mb-3" style="border:1px solid #fbbf24">
      <h6 style="color:#fbbf24"><i class="bi bi-funnel-fill"></i> Filters | {datetime.now(PH_TZ).strftime("%b %d, %Y %I:%M %p")}</h6>
      <form method="GET" class="row g-2 mt-2">
        <div class="col-6 col-md-2"><label class="label">PERIOD</label><select name="period" class="form-select form-select-sm" onchange="this.form.submit()"><option value="daily" {"selected" if period=="daily" else ""}>Daily</option><option value="weekly" {"selected" if period=="weekly" else ""}>Weekly</option><option value="monthly" {"selected" if period=="monthly" else ""}>Monthly</option><option value="quarterly" {"selected" if period=="quarterly" else ""}>Quarterly</option><option value="yearly" {"selected" if period=="yearly" else ""}>Yearly</option></select></div>
        <div class="col-6 col-md-2"><label class="label">YEAR</label><select name="year" class="form-select form-select-sm" onchange="this.form.submit()"><option value="2024" {"selected" if year=="2024" else ""}>2024</option><option value="2025" {"selected" if year=="2025" else ""}>2025</option><option value="2026" {"selected" if year=="2026" else ""}>2026</option></select></div>
        <div class="col-6 col-md-2" style="display:{"block" if period=="monthly" else "none"}"><label class="label">MONTH</label><select name="month" class="form-select form-select-sm" onchange="this.form.submit()"><option value="">All Months</option>{"".join([f'<option value="{m}" {"selected" if str(m)==month else ""}>{calendar.month_name[m]}</option>' for m in range(1,13)])}</select></div>
        <div class="col-6 col-md-2" style="display:{"block" if period=="quarterly" else "none"}"><label class="label">QUARTER</label><select name="quarter" class="form-select form-select-sm" onchange="this.form.submit()"><option value="">All Quarters</option><option value="1" {"selected" if quarter=="1" else ""}>Q1</option><option value="2" {"selected" if quarter=="2" else ""}>Q2</option><option value="3" {"selected" if quarter=="3" else ""}>Q3</option><option value="4" {"selected" if quarter=="4" else ""}>Q4</option></select></div>
        <div class="col-6 col-md-2" style="display:{"block" if period=="weekly" else "none"}"><label class="label">WEEK</label><select name="week" class="form-select form-select-sm" onchange="this.form.submit()"><option value="">All Weeks</option>{"".join([f'<option value="{w}" {"selected" if str(w)==week else ""}>Week {w}</option>' for w in range(1,53)])}</select></div>
        <div class="col-6 col-md-2 d-flex align-items-end"><a href="/" class="btn btn-sm btn-outline-light w-100">Reset</a></div>
      </form>
    </div>
    """
    html=alerts_html+filter_html
    html+=f"<div class='row g-2'><div class='col-6 col-md-2'><div class='kpi' style='border:1px solid #22c55e'><div class='label'>NORMAL OT</div><div class='val-big' style='color:#22c55e'>{round(team_normal,1)}h</div></div></div><div class='col-6 col-md-2'><div class='kpi' style='border:1px solid #3b82f6'><div class='label'>RESTDAY OT</div><div class='val-big' style='color:#3b82f6'>{round(team_restday,1)}h</div></div></div><div class='col-6 col-md-2'><div class='kpi' style='border:1px solid #fbbf24'><div class='label'>TOTAL OT</div><div class='val-big' style='color:#fbbf24'>{round(team_total,1)}h</div></div></div><div class='col-6 col-md-2'><div class='kpi' style='border:1px solid #ef4444'><div class='label'>LOSS HRS</div><div class='val-big' style='color:#ef4444'>{round(team_loss,1)}h</div></div></div><div class='col-6 col-md-2'><div class='kpi' style='border:1px solid #a855f7'><div class='label'>TEAM NET</div><div class='val-big' style='color:#a855f7'>+{round(team_net,1)}h</div></div></div><div class='col-6 col-md-2'><div class='kpi' style='border:1px solid #06b6d4'><div class='label'>AVG OT</div><div class='val-big' style='color:#06b6d4'>{round(avg_ot,1)}h</div></div></div></div>"
    html+=f"<div class='row g-2 mt-2'><div class='col-6'><div class='kpi' style='border:1px solid #f97316;min-height:90px;height:90px'><div class='label'>AVG AHT</div><div class='val-big' style='color:#f97316'>{round(team_avg_aht,1)}m</div></div></div><div class='col-6'><div class='kpi' style='border:1px solid #8b5cf6;min-height:90px;height:90px'><div class='label'>AVG QA</div><div class='val-big' style='color:#8b5cf6'>{round(team_avg_qa,1)}%</div></div></div></div>"
    top3=agent_stats_sorted[:3]
    html+="<div class='card-dark mt-3' style='border:1px solid #fbbf24'><h6 style='color:#fbbf24'>Top 3 OT Earners</h6><div class='podium mt-3'>"
    order=[1,0,2]
    colors=["#fbbf24","#22c55e","#3b82f6"]
    heights=["70px","100px","50px"]
    for idx in order:
        if idx < len(top3):
            a=top3[idx]
            html+=f"<div class='podium-bar' style='background:{colors[idx]};height:{heights[idx]}'><div>{a['tot']}h</div><small style='font-size:9px'>{a['name'][:8]}</small></div>"
    html+="</div><div class='text-center mt-2'><a href='/leaderboard' class='btn btn-sm btn-warning'>View Leaderboard</a></div></div>"
    html+=f"""
    <div class="row g-3 mt-3">
      <div class="col-12 col-md-6"><div class="chart-card" style="border:1px solid #22c55e"><h6 style="color:#22c55e">Normal OT</h6><canvas id="chartNormal"></canvas></div></div>
      <div class="col-12 col-md-6"><div class="chart-card" style="border:1px solid #3b82f6"><h6 style="color:#3b82f6">Restday OT</h6><canvas id="chartRestday"></canvas></div></div>
      <div class="col-12 col-md-6"><div class="chart-card" style="border:1px solid #fbbf24"><h6 style="color:#fbbf24">Total OT</h6><canvas id="chartTotal"></canvas></div></div>
      <div class="col-12 col-md-6"><div class="chart-card" style="border:1px solid #ef4444"><h6 style="color:#ef4444">Loss Hrs</h6><canvas id="chartLoss"></canvas></div></div>
      <div class="col-12 col-md-4"><div class="chart-card" style="border:1px solid #a855f7"><h6 style="color:#a855f7">Net OT</h6><canvas id="chartNet"></canvas></div></div>
      <div class="col-12 col-md-4"><div class="chart-card" style="border:1px solid #f97316"><h6 style="color:#f97316">AHT</h6><canvas id="chartAht"></canvas></div></div>
      <div class="col-12 col-md-4"><div class="chart-card" style="border:1px solid #8b5cf6"><h6 style="color:#8b5cf6">QA Score</h6><canvas id="chartQa"></canvas></div></div>
    </div>
    <script>
    const labels = {labels};
    const normalData = {nd}; const restdayData = {rd}; const totalData = {td}; const lossData = {ld}; const netData = {netd}; const ahtData = {ahtd}; const qaData = {qad};
    function makeChart(id, label, data, color){{
      new Chart(document.getElementById(id), {{ type: 'line', data: {{ labels: labels, datasets: [{{ label: label, data: data, borderColor: color, backgroundColor: color+'33', fill: true, tension: 0.4 }}] }}, options: {{ responsive: true, plugins: {{ legend: {{ display: false }} }}, scales: {{ y: {{ beginAtZero: true, grid: {{ color: '#1e293b' }} }}, x: {{ grid: {{ color: '#1e293b' }} }} }} }} }});
    }}
    makeChart('chartNormal','Normal OT',normalData,'#22c55e'); makeChart('chartRestday','Restday OT',restdayData,'#3b82f6'); makeChart('chartTotal','Total OT',totalData,'#fbbf24'); makeChart('chartLoss','Loss',lossData,'#ef4444'); makeChart('chartNet','Net',netData,'#a855f7'); makeChart('chartAht','AHT',ahtData,'#f97316'); makeChart('chartQa','QA',qaData,'#8b5cf6');
    </script>
    """
    html+="<div class='card-dark mt-3' style='border:1px solid #334155'><div class='d-flex justify-content-between align-items-center'><h6 style='color:white'>Full Team</h6><div class='d-flex gap-2'><input id='teamSearch' class='form-control form-control-sm' placeholder='Search...' style='width:160px'><a href='/agents' class='btn btn-sm btn-warning'>All</a></div></div><div class='table-responsive mt-3'><table id='teamTable' class='table table-sm'><thead><tr><th>AGENT</th><th>TOTAL</th><th>TARGET</th><th>PROGRESS</th><th>LOSS</th><th>AHT</th><th>QA</th><th>STATUS</th></tr></thead><tbody>"
    for a in agent_stats_sorted:
        pct = min(100, a['pct'])
        bar_color = "#22c55e" if pct>=100 else "#fbbf24" if pct>=70 else "#ef4444"
        st = "<span class='badge bg-danger'>Critical</span>" if a['loss']>=4 else "<span class='badge bg-warning text-dark'>Warning</span>" if a['loss']>0 else "<span class='badge bg-success'>Good</span>"
        html+=f"<tr><td><a href='/view/{a['id']}' style='color:white;text-decoration:none'><b>{a['name']}</b><br><small style='color:#94a3b8'>{a['tid']}</small></a></td><td style='color:#fbbf24'>{a['tot']}h</td><td>{a['target']}h</td><td><div class='progress' style='height:8px;width:80px;background:#0f172a'><div class='progress-bar' style='width:{pct}%;background:{bar_color}'></div></div><small style='font-size:9px'>{round(a['pct'],0)}%</small></td><td style='color:#ef4444'>{a['loss']}h</td><td>{a['aht']}m</td><td>{a['qa']}%</td><td>{st}</td></tr>"
    html+="</tbody></table></div></div><script>document.addEventListener('DOMContentLoaded',function(){var i=document.getElementById('teamSearch');if(!i)return;i.addEventListener('keyup',function(){var q=this.value.toLowerCase();document.querySelectorAll('#teamTable tbody tr').forEach(function(r){r.style.display=r.innerText.toLowerCase().includes(q)?'':'none';});});});</script>"
    return page(html)

@app.route("/leaderboard")
@login_required
def leaderboard():
    agents=get_all()
    stats=[]
    for a in agents:
        logs=get_ot(a.get("id"))
        n,r,tot,loss,net=calc(logs)
        plogs=get_perf(a.get("id"))
        la,lq,aa,qa,_,_=calc_perf(plogs)
        stats.append({"name":a.get("NAME",""),"tid":a.get("TENCENT_ID",""),"id":a.get("id"),"tot":tot,"loss":loss,"net":net,"qa":lq,"aht":la})
    top_ot=sorted(stats, key=lambda x: x["tot"], reverse=True)[:10]
    low_loss=sorted(stats, key=lambda x: x["loss"])[:5]
    top_qa=sorted([s for s in stats if s["qa"]>0], key=lambda x: x["qa"], reverse=True)[:5]
    low_aht=sorted([s for s in stats if s["aht"]>0], key=lambda x: x["aht"])[:5]
    html="<h5 style='color:white'>Leaderboard</h5><div class='row g-3 mt-2'>"
    html+="<div class='col-12 col-md-6'><div class='card-dark' style='border:1px solid #fbbf24'><h6 style='color:#fbbf24'>Top OT Earners</h6><table class='table table-sm mt-2'><thead><tr><th>#</th><th>Agent</th><th>Total OT</th></tr></thead><tbody>"
    for idx, a in enumerate(top_ot):
        medal="🥇" if idx==0 else "🥈" if idx==1 else "🥉" if idx==2 else f"{idx+1}"
        html+=f"<tr><td>{medal}</td><td>{a['name']}<br><small style='color:#94a3b8'>{a['tid']}</small></td><td style='color:#fbbf24;font-weight:700'>{a['tot']}h</td></tr>"
    html+="</tbody></table></div></div>"
    html+="<div class='col-12 col-md-6'><div class='card-dark' style='border:1px solid #22c55e'><h6 style='color:#22c55e'>Best QA Scores</h6><table class='table table-sm mt-2'><thead><tr><th>#</th><th>Agent</th><th>QA</th></tr></thead><tbody>"
    for idx, a in enumerate(top_qa):
        html+=f"<tr><td>{idx+1}</td><td>{a['name']}</td><td style='color:#8b5cf6'>{a['qa']}%</td></tr>"
    html+="</tbody></table></div></div>"
    html+="<div class='col-12 col-md-6'><div class='card-dark' style='border:1px solid #22c55e'><h6 style='color:#22c55e'>Lowest Loss</h6><table class='table table-sm'><thead><tr><th>Agent</th><th>Loss</th></tr></thead><tbody>"
    for a in low_loss:
        html+=f"<tr><td>{a['name']}</td><td style='color:#22c55e'>{a['loss']}h</td></tr>"
    html+="</tbody></table></div></div>"
    html+="<div class='col-12 col-md-6'><div class='card-dark' style='border:1px solid #f97316'><h6 style='color:#f97316'>Best AHT</h6><table class='table table-sm'><thead><tr><th>Agent</th><th>AHT</th></tr></thead><tbody>"
    for a in low_aht:
        html+=f"<tr><td>{a['name']}</td><td style='color:#f97316'>{a['aht']}m</td></tr>"
    html+="</tbody></table></div></div></div>"
    return page(html)

@app.route("/export")
@login_required
def export_page():
    html="<h5 style='color:white'>Export Reports</h5><div class='row g-3 mt-2'>"
    html+="<div class='col-12 col-md-6'><div class='card-dark' style='border:1px solid #22c55e'><h6 style='color:#22c55e'>Excel / CSV</h6><p style='color:#94a3b8;font-size:12px'>Download team data</p><a href='/export/csv' class='btn btn-sm btn-success w-100'>Download CSV</a><a href='/export/excel' class='btn btn-sm btn-outline-success w-100 mt-2'>Download Excel</a></div></div>"
    html+="<div class='col-12 col-md-6'><div class='card-dark' style='border:1px solid #fbbf24'><h6 style='color:#fbbf24'>PDF Report</h6><p style='color:#94a3b8;font-size:12px'>Printable report</p><a href='/export/pdf' target='_blank' class='btn btn-sm btn-warning w-100'>View PDF</a></div></div></div>"
    return page(html)

@app.route("/export/csv")
@login_required
def export_csv():
    agents=get_all()
    output=io.StringIO()
    writer=csv.writer(output)
    writer.writerow(["ID","NAME","TENCENT_ID","NORMAL_OT","RESTDAY_OT","TOTAL_OT","LOSS","NET","AHT","QA","TARGET","STATUS"])
    for a in agents:
        logs=get_ot(a.get("id"))
        n,r,tot,loss,net=calc(logs)
        plogs=get_perf(a.get("id"))
        la,lq,_,_,_,_=calc_perf(plogs)
        target=a.get("TARGET_OT",20)
        status="Critical" if loss>=4 else "Warning" if loss>0 else "Good"
        writer.writerow([a.get("id"),a.get("NAME"),a.get("TENCENT_ID"),n,r,tot,loss,net,la,lq,target,status])
    return Response(output.getvalue(), mimetype="text/csv", headers={"Content-Disposition":"attachment;filename=team_shine_m9_export.csv"})

@app.route("/export/excel")
@login_required
def export_excel():
    try:
        import openpyxl
        wb=openpyxl.Workbook()
        ws=wb.active
        ws.title="Team Shine M9"
        ws.append(["ID","NAME","TENCENT_ID","NORMAL_OT","RESTDAY_OT","TOTAL_OT","LOSS","NET","AHT","QA","TARGET","STATUS"])
        for a in get_all():
            logs=get_ot(a.get("id")); n,r,tot,loss,net=calc(logs)
            plogs=get_perf(a.get("id")); la,lq,_,_,_,_=calc_perf(plogs)
            target=a.get("TARGET_OT",20)
            status="Critical" if loss>=4 else "Warning" if loss>0 else "Good"
            ws.append([a.get("id"),a.get("NAME"),a.get("TENCENT_ID"),n,r,tot,loss,net,la,lq,target,status])
        bio=io.BytesIO(); wb.save(bio); bio.seek(0)
        return send_file(bio, as_attachment=True, download_name="team_shine_m9.xlsx", mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    except:
        return redirect("/export/csv")

@app.route("/export/pdf")
@login_required
def export_pdf():
    agents=get_all()
    html="<html><head><style>body{font-family:Arial} table{width:100%;border-collapse:collapse} th,td{border:1px solid #ccc;padding:6px;font-size:11px} th{background:#fbbf24}</style></head><body>"
    html+=f"<h2>TEAM SHINE M9 - Performance Report</h2><p>Generated: {datetime.now(PH_TZ).strftime('%Y-%m-%d %I:%M %p')}</p>"
    html+="<table><tr><th>ID</th><th>NAME</th><th>TENCENT</th><th>N OT</th><th>RD OT</th><th>TOTAL</th><th>LOSS</th><th>NET</th><th>AHT</th><th>QA</th></tr>"
    for a in agents:
        logs=get_ot(a.get("id")); n,r,tot,loss,net=calc(logs)
        plogs=get_perf(a.get("id")); la,lq,_,_,_,_=calc_perf(plogs)
        html+=f"<tr><td>{a.get('id')}</td><td>{a.get('NAME')}</td><td>{a.get('TENCENT_ID')}</td><td>{n}</td><td>{r}</td><td>{tot}</td><td>{loss}</td><td>{net}</td><td>{la}m</td><td>{lq}%</td></tr>"
    html+="</table><p>Developed By: Moises Gamboa | Computer Engineer</p></body></html>"
    return html

@app.route("/bulk", methods=["GET","POST"])
@login_required
@role_required(["admin","team_leader"])
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
                        db_root.child("perf_logs").push({"agent_id":str(agent_id),"type":typ,"value":str(hours),"date":date,"reason":"Bulk import"})
                    else:
                        db_root.child("ot_logs").push({"agent_id":str(agent_id),"type":typ,"hours":str(hours),"date":date,"reason":"Bulk import"})
                    count+=1
                msg=f"Imported {count} records!"
            except Exception as e:
                msg=f"Error: {str(e)}"
    html="<h5 style='color:white'>Bulk Import</h5>"
    html+=f"<div style='color:#22c55e'>{msg}</div>" if msg else ""
    html+="""
    <div class="card-dark mt-3" style="border:1px solid #fbbf24">
      <h6 style="color:#fbbf24">Paste CSV</h6>
      <p style="color:#94a3b8;font-size:12px">Format: agent_id,type,value,date<br>Types: NORMAL_OT, RESTDAY_OT, LOSS, AHT, QA</p>
      <form method="POST">
        <textarea name="csv_text" class="form-control" rows="10" placeholder="agent_id,type,value,date"></textarea>
        <button class="btn btn-warning w-100 mt-2">Import</button>
      </form>
    </div>
    """
    return page(html)


@app.route("/logs")
@login_required
def login_logs():
    if session.get("role") not in ["admin"]:
        return redirect("/")
    logs_raw = db_root.child("login_logs").get() if db_root else {}
    logs=[]
    if isinstance(logs_raw, dict):
        for lid, v in logs_raw.items():
            if isinstance(v, dict):
                logs.append(v)
    logs_sorted=sorted(logs, key=lambda x: x.get("timestamp",""), reverse=True)[:100]
    rows=""
    for l in logs_sorted:
        color="#22c55e" if l.get("type")=="LOGIN" else "#ef4444"
        rows+=f"<tr><td style='color:#cbd5e1'>{l.get('timestamp','')}</td><td><b style='color:white'>{l.get('name','')}</b><br><small style='color:#94a3b8'>{l.get('user','')}</small></td><td><span class='badge' style='background:{color}'>{l.get('type')}</span></td><td>{l.get('role')}</td><td>{l.get('agent_id','')}</td></tr>"
    if not rows:
        rows="<tr><td colspan=5 style='text-align:center;color:#64748b'>No logs yet</td></tr>"
    html="<div class='d-flex justify-content-between'><h5 style='color:white'>Login / Logout Logs</h5><a href='/' class='btn btn-sm btn-outline-light'>Dashboard</a></div>"
    html+=f"<div class='card-dark mt-3'><div class='table-responsive'><table class='table table-sm'><thead><tr><th>Time</th><th>User</th><th>Type</th><th>Role</th><th>ID</th></tr></thead><tbody>{rows}</tbody></table></div></div>"
    html+="<div class='card-dark mt-3'><h6 style='color:#94a3b8'>Info</h6><small style='color:#64748b'>Agent login: Username = Tencent ID (ex: 4909), Password = Tencent ID default<br>Agent sees only view card + graphs, no data entry<br>All login/logout tracked here</small></div>"
    return page(html)


@app.route("/agents")
@login_required
def agents_list():
    q = request.args.get("q","").lower().strip()
    agents=get_all()
    filtered=agents
    if q:
        filtered=[a for a in agents if q in str(a.get("NAME","")).lower() or q in str(a.get("TENCENT_ID","")).lower()]
    rows=""
    for a in filtered:
        logs=get_ot(a.get("id"))
        n,r,tot,loss,net=calc(logs)
        rows+=f"<tr><td>{a.get('id')}</td><td><a href='/view/{a.get('id')}' style='color:white;text-decoration:none'><b>{a.get('NAME','')}</b><br><small style='color:#94a3b8'>{a.get('TENCENT_ID','')} NET:{net}h</small></a></td><td style='color:#22c55e'>{n}h</td><td style='color:#3b82f6'>{r}h</td><td style='color:#ef4444'>{loss}h</td><td><a href='/view/{a.get('id')}' class='btn btn-sm btn-warning'>View</a></td></tr>"
    if not rows:
        rows="<tr><td colspan=6 style='text-align:center;color:#64748b;padding:20px'>No agents found</td></tr>"
    top = f"<div class='d-flex justify-content-between align-items-center flex-wrap gap-2'><h5 style='color:white;margin:0'>All Agents ({len(filtered)}/{len(agents)})</h5><div class='d-flex gap-2'><form method='GET' class='d-flex gap-2'><input name='q' value='{q}' class='form-control form-control-sm' placeholder='Search...' style='width:220px'><button class='btn btn-sm btn-warning'>Search</button></form><a href='/' class='btn btn-sm btn-outline-light'>Dashboard</a></div></div>"
    return page(top + f"<div class='card-dark mt-3'><div class='table-responsive'><table class='table'><thead><tr><th>ID</th><th>AGENT</th><th>N</th><th>RD</th><th>LOSS</th><th></th></tr></thead><tbody>{rows}</tbody></table></div></div>")

@app.route("/view/<aid>")
@login_required
def view(aid):
    data=None
    for a in get_all():
        if str(a.get("id"))==str(aid):
            data=a
            break
    if not data: data={}
    logs=get_ot(aid)
    n,r,tot,loss,net=calc(logs)
    plogs=get_perf(aid)
    la,lq,aa,qa,_,_=calc_perf(plogs)
    date_groups=defaultdict(list)
    for l in logs:
        date_groups[l.get("date")].append(l)
    sorted_dates=sorted(date_groups.keys())[-14:]
    ind_labels=[]
    ind_tot=[]
    ind_loss=[]
    ind_net=[]
    for d in sorted_dates:
        ll=date_groups[d]
        _,_,t,lo,ne=calc(ll)
        ind_labels.append(d[-5:])
        ind_tot.append(t)
        ind_loss.append(lo)
        ind_net.append(ne)
    pgroups=defaultdict(list)
    for l in plogs:
        pgroups[l.get("date")].append(l)
    ind_aht=[]
    ind_qa=[]
    for d in sorted_dates:
        pl=pgroups.get(d,[])
        _,_,aaa,qq,_,_=calc_perf(pl)
        ind_aht.append(aaa)
        ind_qa.append(qq)
    log_rows=""
    for l in logs:
        col="#22c55e" if l.get("type")=="NORMAL_OT" else "#3b82f6" if l.get("type")=="RESTDAY_OT" else "#ef4444"
        log_rows+=f"<tr><td style='color:#cbd5e1'>{l.get('date','')}</td><td><span style='color:{col}'>{l.get('type')}</span></td><td style='color:white'>{l.get('hours')}h</td><td style='color:#94a3b8'>{l.get('reason','')}</td><td><a href='/delete_log/{aid}/{l.get('log_id','')}' class='btn btn-sm btn-outline-danger' style='font-size:10px'>X</a></td></tr>"
    if not log_rows: log_rows="<tr><td colspan=5 style='color:#64748b;text-align:center'>No logs yet</td></tr>"
    perf_rows=""
    for l in plogs:
        col="#f97316" if l.get("type")=="AHT" else "#8b5cf6"
        unit="m" if l.get("type")=="AHT" else "%"
        perf_rows+=f"<tr><td style='color:#cbd5e1'>{l.get('date','')}</td><td><span style='color:{col}'>{l.get('type')}</span></td><td style='color:white'>{l.get('value')}{unit}</td><td style='color:#94a3b8'>{l.get('reason','')}</td><td><a href='/delete_perf/{aid}/{l.get('log_id','')}' class='btn btn-sm btn-outline-danger' style='font-size:10px'>X</a></td></tr>"
    if not perf_rows: perf_rows="<tr><td colspan=5 style='color:#64748b;text-align:center'>No AHT/QA logs</td></tr>"
    initial=str(data.get("NAME","?"))[:1]
    target=float(data.get("TARGET_OT",20))
    pct = (tot/target*100) if target>0 else 0
    bar_color = "#22c55e" if pct>=100 else "#fbbf24" if pct>=70 else "#ef4444"
    html=f"<a href='/' class='btn btn-sm btn-outline-light mb-3'>Back</a><div class='card-dark' style='border:1px solid #334155'><div class='text-center'><div style='width:90px;height:90px;background:linear-gradient(135deg,#fbbf24,#f59e0b);border-radius:18px;display:flex;align-items:center;justify-content:center;font-size:40px;font-weight:900;color:#111827;margin:auto'>{initial}</div><h4 style='color:white;margin-top:12px'>{data.get('NAME','')}</h4><small style='color:#94a3b8'>{data.get('TENCENT_ID','')}</small><div class='mt-2'><small style='color:#94a3b8'>Target: {target}h | Progress: {round(pct,1)}%</small><div class='progress' style='height:8px;width:200px;margin:auto;background:#0f172a'><div class='progress-bar' style='width:{min(100,pct)}%;background:{bar_color}'></div></div></div></div>"
    html+=f"<div class='row g-2 mt-3'><div class='col-4'><div class='kpi' style='border:1px solid #22c55e'><div class='label'>NORMAL OT</div><div class='val-big' style='color:#22c55e'>{n}h</div></div></div><div class='col-4'><div class='kpi' style='border:1px solid #3b82f6'><div class='label'>RESTDAY OT</div><div class='val-big' style='color:#3b82f6'>{r}h</div></div></div><div class='col-4'><div class='kpi' style='border:1px solid #ef4444'><div class='label'>LOSS HRS</div><div class='val-big' style='color:#ef4444'>{loss}h</div></div></div><div class='col-6'><div class='kpi' style='border:1px solid #22c55e'><div class='label'>TOTAL OT</div><div class='val-big' style='color:#22c55e'>{tot}h</div></div></div><div class='col-6'><div class='kpi' style='border:1px solid #fbbf24'><div class='label'>NET</div><div class='val-big' style='color:#fbbf24'>+{net}h</div></div></div><div class='col-6'><div class='kpi' style='border:1px solid #f97316'><div class='label'>AHT</div><div class='val-big' style='color:#f97316'>{la}m</div><small style='color:#94a3b8;font-size:9px'>Avg:{round(aa,1)}m</small></div></div><div class='col-6'><div class='kpi' style='border:1px solid #8b5cf6'><div class='label'>QA SCORE</div><div class='val-big' style='color:#8b5cf6'>{lq}%</div><small style='color:#94a3b8;font-size:9px'>Avg:{round(qa,1)}%</small></div></div></div>"
    html+=f"""
    <div class="row g-3 mt-4">
      <div class="col-12 col-md-6"><div class="chart-card"><h6 style="color:#fbbf24">Personal OT Trend</h6><canvas id="indOT"></canvas></div></div>
      <div class="col-12 col-md-6"><div class="chart-card"><h6 style="color:#8b5cf6">QA & AHT Trend</h6><canvas id="indQA"></canvas></div></div>
    </div>
    <script>
    new Chart(document.getElementById('indOT'), {{type:'line', data:{{labels:{ind_labels}, datasets:[{{label:'Total OT', data:{ind_tot}, borderColor:'#fbbf24', backgroundColor:'#fbbf2433', fill:true, tension:0.4}},{{label:'Loss', data:{ind_loss}, borderColor:'#ef4444', fill:false}}] }}, options:{{responsive:true}} }});
    new Chart(document.getElementById('indQA'), {{type:'line', data:{{labels:{ind_labels}, datasets:[{{label:'QA %', data:{ind_qa}, borderColor:'#8b5cf6', yAxisID:'y'}},{{label:'AHT m', data:{ind_aht}, borderColor:'#f97316', yAxisID:'y1'}}] }}, options:{{responsive:true, scales:{{y:{{type:'linear', position:'left'}}, y1:{{type:'linear', position:'right', grid:{{drawOnChartArea:false}}}}}} }} }});
    </script>
    """
    html+=f"""
    <div class="card-dark mt-3" style="border:1px solid #334155">
      <h6 style="color:#fbbf24">Target OT Setting</h6>
      <form method="POST" action="/set_target/{aid}" class="row g-2">
        <div class="col-6"><input name="target" type="number" step="0.5" class="form-control form-control-sm" value="{target}" placeholder="Target OT hours"></div>
        <div class="col-6"><button class="btn btn-sm btn-warning w-100">Update Target</button></div>
      </form>
    </div>
    """
    html+=f"<div class='row g-2 mt-4'><div class='col-6'><div class='card-dark' style='border:1px solid #22c55e'><h6 style='color:#22c55e'>Add Normal OT</h6><form method='POST' action='/add_ot/{aid}' class='row g-2'><input type='hidden' name='type' value='NORMAL_OT'><div class='col-6'><input name='hours' type='number' step='0.5' class='form-control form-control-sm' placeholder='Hours' required></div><div class='col-6'><input name='date' type='date' class='form-control form-control-sm' value='{datetime.now(PH_TZ).strftime('%Y-%m-%d')}'></div><div class='col-12'><input name='reason' class='form-control form-control-sm' placeholder='Reason'></div><div class='col-12'><button class='btn w-100 mt-1' style='background:#22c55e;color:white'>Add Normal OT</button></div></form></div></div><div class='col-6'><div class='card-dark' style='border:1px solid #3b82f6'><h6 style='color:#3b82f6'>Add Restday OT</h6><form method='POST' action='/add_ot/{aid}' class='row g-2'><input type='hidden' name='type' value='RESTDAY_OT'><div class='col-6'><input name='hours' type='number' step='0.5' class='form-control form-control-sm' placeholder='Hours' required></div><div class='col-6'><input name='date' type='date' class='form-control form-control-sm' value='{datetime.now(PH_TZ).strftime('%Y-%m-%d')}'></div><div class='col-12'><input name='reason' class='form-control form-control-sm' placeholder='Reason'></div><div class='col-12'><button class='btn w-100 mt-1' style='background:#3b82f6;color:white'>Add Restday OT</button></div></form></div></div><div class='col-6'><div class='card-dark' style='border:1px solid #f97316'><h6 style='color:#f97316'>Add AHT</h6><form method='POST' action='/add_perf/{aid}' class='row g-2'><input type='hidden' name='type' value='AHT'><div class='col-6'><input name='value' type='number' step='0.1' class='form-control form-control-sm' placeholder='Minutes' required></div><div class='col-6'><input name='date' type='date' class='form-control form-control-sm' value='{datetime.now(PH_TZ).strftime('%Y-%m-%d')}'></div><div class='col-12'><input name='reason' class='form-control form-control-sm' placeholder='Notes'></div><div class='col-12'><button class='btn w-100 mt-1' style='background:#f97316;color:white'>Add AHT</button></div></form></div></div><div class='col-6'><div class='card-dark' style='border:1px solid #8b5cf6'><h6 style='color:#8b5cf6'>Add QA Score</h6><form method='POST' action='/add_perf/{aid}' class='row g-2'><input type='hidden' name='type' value='QA'><div class='col-6'><input name='value' type='number' step='0.1' class='form-control form-control-sm' placeholder='%' required></div><div class='col-6'><input name='date' type='date' class='form-control form-control-sm' value='{datetime.now(PH_TZ).strftime('%Y-%m-%d')}'></div><div class='col-12'><input name='reason' class='form-control form-control-sm' placeholder='QA notes'></div><div class='col-12'><button class='btn w-100 mt-1' style='background:#8b5cf6;color:white'>Add QA</button></div></form></div></div><div class='col-12'><div class='card-dark' style='border:1px solid #ef4444'><h6 style='color:#ef4444'>Add Loss Hours</h6><form method='POST' action='/add_ot/{aid}' class='row g-2'><input type='hidden' name='type' value='LOSS'><div class='col-4'><input name='hours' type='number' step='0.5' class='form-control form-control-sm' placeholder='Loss Hrs' required></div><div class='col-4'><input name='date' type='date' class='form-control form-control-sm' value='{datetime.now(PH_TZ).strftime('%Y-%m-%d')}'></div><div class='col-4'><select name='loss_type' class='form-select form-select-sm'><option>Late</option><option>Absent</option><option>Undertime</option></select></div><div class='col-12'><input name='reason' class='form-control form-control-sm' placeholder='Reason'></div><div class='col-12'><button class='btn w-100 mt-1' style='background:#ef4444;color:white'>Add Loss</button></div></form></div></div></div>"
    # History for admin only
    if not is_agent:
            html+=f"<div class='mt-4'><h6 style='color:white'>OT & Loss History</h6><div class='table-responsive'><table class='table table-sm'><thead><tr><th>Date</th><th>Type</th><th>Hrs</th><th>Reason</th><th></th></tr></thead><tbody>{log_rows}</tbody></table></div></div><div class='mt-3'><h6 style='color:white'>AHT & QA History</h6><div class='table-responsive'><table class='table table-sm'><thead><tr><th>Date</th><th>Type</th><th>Value</th><th>Notes</th><th></th></tr></thead><tbody>{perf_rows}</tbody></table></div></div>"
    else:
        html+=f"<div class='card-dark mt-3' style='border:1px solid #334155'><h6 style='color:#94a3b8'>View Only - Agent Mode</h6><small style='color:#64748b'>You can view your performance cards and graphs only. Data entry is restricted to Team Leader.</small></div>"
    html+="</div>"
    return page(html)

@app.route("/set_target/<aid>", methods=["POST"])
@login_required
def set_target(aid):
    target=request.form.get("target","20")
    if db_root:
        db_root.child(f"agents/{aid}/TARGET_OT").set(target)
    return redirect(f"/view/{aid}")

@app.route("/add_ot/<aid>", methods=["POST"])
@login_required
def add_ot(aid):
    typ=request.form.get("type","NORMAL_OT")
    hours=request.form.get("hours","0")
    date=request.form.get("date",datetime.now(PH_TZ).strftime("%Y-%m-%d"))
    reason=request.form.get("reason","")
    if db_root:
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

@app.route("/delete_log/<aid>/<log_id>")
@login_required
def delete_log(aid, log_id):
    if db_root: db_root.child("ot_logs/"+log_id).delete()
    return redirect("/view/"+str(aid))

@app.route("/delete_perf/<aid>/<log_id>")
@login_required
def delete_perf(aid, log_id):
    if db_root: db_root.child("perf_logs/"+log_id).delete()
    return redirect("/view/"+str(aid))

if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",5000)))
