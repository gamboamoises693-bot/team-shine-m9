
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
    except:
        return []

def get_ot(aid):
    try:
        logs = db_root.child("ot_logs").get() if db_root else {}
        res=[]
        if isinstance(logs, dict):
            for lid,v in logs.items():
                if not isinstance(v,dict): continue
                if str(v.get("agent_id"))==str(aid):
                    v["log_id"]=lid
                    res.append(v)
        return res
    except:
        return []

def get_perf(aid):
    try:
        logs = db_root.child("perf_logs").get() if db_root else {}
        res=[]
        if isinstance(logs, dict):
            for lid,v in logs.items():
                if not isinstance(v,dict): continue
                if str(v.get("agent_id"))==str(aid):
                    v["log_id"]=lid
                    res.append(v)
        return res
    except:
        return []

def get_all_ot():
    try:
        logs = db_root.child("ot_logs").get() if db_root else {}
        return [v for v in logs.values() if isinstance(v, dict)] if isinstance(logs, dict) else []
    except:
        return []

def get_all_perf():
    try:
        logs = db_root.child("perf_logs").get() if db_root else {}
        return [v for v in logs.values() if isinstance(v, dict)] if isinstance(logs, dict) else []
    except:
        return []

def get_all_announcements():
    try:
        raw = db_root.child("announcements").get() if db_root else None
        if not raw:
            return []
        res=[]
        if isinstance(raw, dict):
            for aid, val in raw.items():
                if isinstance(val, dict):
                    val["id"]=aid
                    res.append(val)
        res.sort(key=lambda x: x.get("created_at",""), reverse=True)
        return res
    except:
        return []

def get_announcement_reads():
    try:
        raw = db_root.child("announcement_reads").get() if db_root else None
        if not raw:
            return []
        res=[]
        if isinstance(raw, dict):
            for rid, val in raw.items():
                if isinstance(val, dict):
                    val["id"]=rid
                    res.append(val)
        return res
    except:
        return []

def get_reads_for_announcement(ann_id):
    reads=get_announcement_reads()
    return [r for r in reads if str(r.get("announcement_id"))==str(ann_id)]

def has_read(ann_id, agent_id):
    reads=get_announcement_reads()
    for r in reads:
        if str(r.get("announcement_id"))==str(ann_id) and str(r.get("agent_id"))==str(agent_id):
            return True
    return False

def calc(logs):
    try:
        n=sum(float(l.get("hours",0)) for l in logs if l.get("type")=="NORMAL_OT")
        r=sum(float(l.get("hours",0)) for l in logs if l.get("type")=="RESTDAY_OT")
        loss=sum(float(l.get("hours",0)) for l in logs if l.get("type")=="LOSS")
        tot=n+r
        net=tot-loss
        return n,r,tot,loss,net
    except:
        return 0,0,0,0,0

def calc_perf(logs):
    try:
        aht_list=[float(l.get("value",0)) for l in logs if l.get("type")=="AHT"]
        qa_list=[float(l.get("value",0)) for l in logs if l.get("type")=="QA"]
        csat_list=[float(l.get("value",0)) for l in logs if l.get("type")=="CSAT"]
        fcr_list=[float(l.get("value",0)) for l in logs if l.get("type")=="FCR"]
        avg_aht=sum(aht_list)/len(aht_list) if aht_list else 0
        avg_qa=sum(qa_list)/len(qa_list) if qa_list else 0
        avg_csat=sum(csat_list)/len(csat_list) if csat_list else 0
        avg_fcr=sum(fcr_list)/len(fcr_list) if fcr_list else 0
        la=aht_list[-1] if aht_list else 0
        lq=qa_list[-1] if qa_list else 0
        lc=csat_list[-1] if csat_list else 0
        lf=fcr_list[-1] if fcr_list else 0
        return la,lq,lc,lf,avg_aht,avg_qa,avg_csat,avg_fcr
    except:
        return 0,0,0,0,0,0,0,0

def parse_date(dstr):
    try:
        return datetime.strptime(dstr, "%Y-%m-%d")
    except:
        return None

def get_filtered_stats(period, year, month, quarter, week):
    ot_logs=get_all_ot()
    perf_logs=get_all_perf()
    filtered_ot=[]
    filtered_perf=[]
    for l in ot_logs:
        dt=parse_date(l.get("date",""))
        if not dt: continue
        if year and dt.year!=int(year): continue
        if period=="monthly" and month and dt.month!=int(month): continue
        if period=="quarterly" and quarter:
            q=(dt.month-1)//3+1
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
            q=(dt.month-1)//3+1
            if q!=int(quarter): continue
        if period=="weekly" and week:
            if dt.isocalendar()[1]!=int(week): continue
        filtered_perf.append(l)
    labels=[]; nd=[]; rd=[]; td=[]; ld=[]; netd=[]; ahtd=[]; qad=[]
    if period=="daily":
        groups=defaultdict(list)
        for l in filtered_ot: groups[l.get("date")].append(l)
        sdates=sorted(groups.keys())[-14:]
        for d in sdates:
            n,r,tot,loss,net=calc(groups[d])
            labels.append(d[-5:]); nd.append(n); rd.append(r); td.append(tot); ld.append(loss); netd.append(net)
        pgroups=defaultdict(list)
        for l in filtered_perf: pgroups[l.get("date")].append(l)
        for d in sdates:
            la,lq,lc,lf,aa,qa,ac,af=calc_perf(pgroups.get(d,[]))
            ahtd.append(round(aa,1)); qad.append(round(qa,1))
    elif period=="monthly":
        if month:
            groups=defaultdict(list)
            for l in filtered_ot: groups[l.get("date")].append(l)
            sdates=sorted(groups.keys())
            for d in sdates:
                n,r,tot,loss,net=calc(groups[d])
                labels.append(d[-2:]); nd.append(n); rd.append(r); td.append(tot); ld.append(loss); netd.append(net)
            pgroups=defaultdict(list)
            for l in filtered_perf: pgroups[l.get("date")].append(l)
            for d in sdates:
                la,lq,lc,lf,aa,qa,ac,af=calc_perf(pgroups.get(d,[]))
                ahtd.append(round(aa,1)); qad.append(round(qa,1))
        else:
            mgroups=defaultdict(list); pmgroups=defaultdict(list)
            for l in filtered_ot:
                dt=parse_date(l.get("date"))
                if dt: mgroups[dt.month].append(l)
            for l in filtered_perf:
                dt=parse_date(l.get("date"))
                if dt: pmgroups[dt.month].append(l)
            for m in range(1,13):
                labels.append(calendar.month_abbr[m])
                n,r,tot,loss,net=calc(mgroups.get(m,[]))
                nd.append(n); rd.append(r); td.append(tot); ld.append(loss); netd.append(net)
                la,lq,lc,lf,aa,qa,ac,af=calc_perf(pmgroups.get(m,[]))
                ahtd.append(round(aa,1)); qad.append(round(qa,1))
    else:
        # Yearly default
        labels=[calendar.month_abbr[m] for m in range(1,13)]
        for m in range(1,13):
            logs=[l for l in filtered_ot if parse_date(l.get("date")) and parse_date(l.get("date")).month==m]
            n,r,tot,loss,net=calc(logs)
            nd.append(n); rd.append(r); td.append(tot); ld.append(loss); netd.append(net)
            pl=[l for l in filtered_perf if parse_date(l.get("date")) and parse_date(l.get("date")).month==m]
            la,lq,lc,lf,aa,qa,ac,af=calc_perf(pl)
            ahtd.append(round(aa,1)); qad.append(round(qa,1))
    return labels, nd, rd, td, ld, netd, ahtd, qad

BASE_CSS = """<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1">
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
:root{--bg:#0b1120;--card:#151e32;--card2:#0f172a;--border:#2d3748;--border2:#1e293b;--text:#f1f5f9;--text2:#94a3b8}
[data-theme="light"]{--bg:#f1f5f9;--card:#ffffff;--card2:#e2e8f0;--border:#cbd5e1;--border2:#e2e8f0;--text:#0f172a;--text2:#475569}
body{background:var(--bg);color:var(--text);font-family:Inter,system-ui}
.card-dark{background:var(--card);border:1px solid var(--border);border-radius:20px;padding:16px}
.kpi{padding:12px 8px;border-radius:16px;background:var(--card);border:1px solid var(--border);text-align:center;min-height:110px;height:110px;display:flex;flex-direction:column;justify-content:center;align-items:center}
.label{font-size:9px;color:var(--text2);text-transform:uppercase;font-weight:600;min-height:22px;display:flex;align-items:center;justify-content:center}
.val-big{font-size:22px;font-weight:800;margin-top:2px}
.chart-card{background:var(--card);border:1px solid var(--border);border-radius:20px;padding:16px}
.table thead th{background:var(--card2)!important;color:#fbbf24!important;font-size:10px;text-transform:uppercase;border:none!important}
.table tbody td{background:var(--card)!important;border-color:var(--border2)!important;color:var(--text)!important;padding:12px 8px}
input,select{background:var(--card2)!important;color:var(--text)!important;border:1px solid var(--border)!important}
.navbar{background:var(--card2)!important;border-bottom:1px solid var(--border2)!important}
</style></head><body>
"""
BASE_FOOT = "</div><footer style='text-align:center;padding:24px;color:#64748b;font-size:12px;border-top:1px solid #1e293b;margin-top:30px'><div>Developed By : <span style='color:#fbbf24;font-weight:700'>Moises Gamboa</span> | Computer Engineer</div></footer><script src='https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js'></script><script>function toggleTheme(){const html=document.documentElement;const current=html.getAttribute('data-theme')||'dark';const next=current==='dark'?'light':'dark';html.setAttribute('data-theme',next);localStorage.setItem('theme',next);const btn=document.getElementById('themeToggle');if(btn)btn.textContent=next==='dark'?'🌓':'☀️';}(function(){const saved=localStorage.getItem('theme')||'dark';document.documentElement.setAttribute('data-theme',saved);})();</script></body></html>"

def get_navbar():
    role=session.get("role","")
    is_agent=role=="agent"
    agent_id=session.get("agent_id","")
    if is_agent:
        return f"""
<nav class="navbar p-3"><div class="container-fluid">
<a class="navbar-brand fw-bold" href="/view/{agent_id}" style="color:var(--text)">TEAM SHINE M9 <small style="color:#fbbf24;font-size:11px">AGENT</small></a>
<div class="d-flex gap-2 align-items-center">
<button id="themeToggle" class="btn btn-sm btn-outline-warning" onclick="toggleTheme()">🌓</button>
<div class="dropdown">
  <button class="btn btn-sm btn-warning dropdown-toggle" type="button" data-bs-toggle="dropdown" style="font-weight:900">☰</button>
  <ul class="dropdown-menu dropdown-menu-end" style="background:var(--card);border:1px solid var(--border);min-width:200px">
    <li><h6 class="dropdown-header" style="color:#fbbf24">Agent Menu</h6></li>
    <li><a class="dropdown-item" href="/view/{agent_id}" style="color:var(--text)">🏠 My Dashboard</a></li>
    <li><a class="dropdown-item" href="/announcements" style="color:var(--text)">📢 Announcements</a></li>
    <li><hr class="dropdown-divider"></li>
    <li><a class="dropdown-item" href="/change_password" style="color:var(--text)">🔑 Change Password</a></li>
    <li><a class="dropdown-item" href="/health" style="color:var(--text)">✅ Health Check</a></li>
    <li><hr class="dropdown-divider"></li>
    <li><a class="dropdown-item" href="/logout" style="color:#ef4444">🚪 Logout</a></li>
  </ul>
</div>
</div>
</div></nav>
<div class="container-fluid p-3" style="max-width:1200px;margin:auto">
"""
    else:
        return """
<nav class="navbar p-3"><div class="container-fluid">
<a class="navbar-brand fw-bold" href="/" style="color:var(--text)">TEAM SHINE M9 <small style="color:#fbbf24;font-size:11px">TEAM LEADER</small></a>
<div class="d-flex gap-2 align-items-center">
<button id="themeToggle" class="btn btn-sm btn-outline-warning" onclick="toggleTheme()">🌓</button>
<div class="dropdown">
  <button class="btn btn-sm btn-warning dropdown-toggle" type="button" data-bs-toggle="dropdown" style="font-weight:900">☰</button>
  <ul class="dropdown-menu dropdown-menu-end" style="background:var(--card);border:1px solid var(--border);min-width:220px">
    <li><h6 class="dropdown-header" style="color:#fbbf24">Main Menu</h6></li>
    <li><a class="dropdown-item" href="/" style="color:var(--text)">🏠 Dashboard</a></li>
    <li><a class="dropdown-item" href="/agents" style="color:var(--text)">👥 Agents</a></li>
    <li><a class="dropdown-item" href="/logs" style="color:var(--text)">📋 Logs</a></li>
    <li><a class="dropdown-item" href="/working_hours" style="color:var(--text)">⏱️ Working Hours</a></li>
    <li><hr class="dropdown-divider"></li>
    <li><h6 class="dropdown-header" style="color:#22c55e">Export & Reports</h6></li>
    <li><a class="dropdown-item" href="/announcements" style="color:var(--text)">📢 Announcements</a></li>
    <li><a class="dropdown-item" href="/export" style="color:var(--text)">📊 Export</a></li>
    <li><a class="dropdown-item" href="/export/pdf" style="color:var(--text)">📄 PDF Report</a></li>
    <li><hr class="dropdown-divider"></li>
    <li><a class="dropdown-item" href="/change_password" style="color:var(--text)">🔑 Change Password</a></li>
    <li><a class="dropdown-item" href="/health" style="color:var(--text)">✅ Health Check</a></li>
    <li><hr class="dropdown-divider"></li>
    <li><a class="dropdown-item" href="/logout" style="color:#ef4444">🚪 Logout</a></li>
  </ul>
</div>
</div>
</div></nav>
<div class="container-fluid p-3" style="max-width:1200px;margin:auto">
"""

def page(c):
    return BASE_CSS + get_navbar() + c + BASE_FOOT


@app.route("/health")

@app.route("/health")
def health():
    return "OK", 200

@app.route("/ping")
def ping():
    return "pong", 200

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
                return redirect("/")
            found=None
            for a in get_all():
                tid=str(a.get("TENCENT_ID","")).strip()
                if u.lower()==tid.lower() or u.lower()==str(a.get("id")).lower():
                    found=a
                    break
            if found:
                stored=str(found.get("LOGIN_PASS") or found.get("TENCENT_ID") or "1234").strip()
                if p==stored or p==str(found.get("TENCENT_ID")):
                    session["logged_in"]=True
                    session["user"]=found.get("TENCENT_ID")
                    session["role"]="agent"
                    session["name"]=found.get("NAME")
                    session["agent_id"]=found.get("id")
                    try:
                        if db_root:
                            db_root.child("login_logs").push({"user": found.get("TENCENT_ID"),"name": found.get("NAME"),"role": "agent","type": "LOGIN","timestamp": datetime.now(PH_TZ).strftime("%Y-%m-%d %I:%M:%S %p"),"date": datetime.now(PH_TZ).strftime("%Y-%m-%d"),"agent_id": found.get("id")})
                    except: pass
                    return redirect(f"/view/{found.get('id')}")
                else:
                    error="Invalid agent password! Default Tencent ID"
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

@app.errorhandler(500)
def handle_500(e):
    return f"<div style='background:#0b1120;color:white;padding:20px'><h3>Error 500</h3><pre style='color:#fbbf24;font-size:10px'>{traceback.format_exc()}</pre><a href='/' class='btn btn-warning'>Back</a></div>", 500

def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated

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
    team_n=0; team_r=0; team_loss=0; team_tot=0
    agent_stats=[]
    for a in agents:
        logs=get_ot(a.get("id"))
        n,r,tot,loss,net=calc(logs)
        team_n+=n; team_r+=r; team_loss+=loss; team_tot+=tot
        plogs=get_perf(a.get("id"))
        la,lq,lc,lf,aa,qa,ac,af=calc_perf(plogs)
        target=float(a.get("TARGET_OT",20))
        pct=(tot/target*100) if target>0 else 0
        wh_target=float(a.get("WORKING_HOURS_TARGET",220))
        wh_comp=((wh_target-loss)/wh_target*100) if wh_target>0 else 0
        agent_stats.append({"id":a.get("id"),"name":a.get("NAME",""),"tid":a.get("TENCENT_ID",""),"n":n,"r":r,"tot":tot,"loss":loss,"net":net,"aht":la,"qa":lq,"csat":lc,"fcr":lf,"target":target,"pct":pct,"wh_target":wh_target,"wh_comp":wh_comp})
    avg_ot=team_tot/len(agents) if agents else 0
    team_qa_vals=[a["qa"] for a in agent_stats if a["qa"]>0]
    team_aht_vals=[a["aht"] for a in agent_stats if a["aht"]>0]
    team_csat_vals=[a["csat"] for a in agent_stats if a["csat"]>0]
    team_fcr_vals=[a["fcr"] for a in agent_stats if a["fcr"]>0]
    team_wh_comp_vals=[a["wh_comp"] for a in agent_stats]
    avg_qa_team=sum(team_qa_vals)/len(team_qa_vals) if team_qa_vals else 0
    avg_aht_team=sum(team_aht_vals)/len(team_aht_vals) if team_aht_vals else 0
    avg_csat_team=sum(team_csat_vals)/len(team_csat_vals) if team_csat_vals else 0
    avg_fcr_team=sum(team_fcr_vals)/len(team_fcr_vals) if team_fcr_vals else 0
    avg_wh_comp_team=sum(team_wh_comp_vals)/len(team_wh_comp_vals) if team_wh_comp_vals else 0
    total_wh_target=sum([a["wh_target"] for a in agent_stats])
    total_loss=sum([a["loss"] for a in agent_stats])
    total_actual=total_wh_target-total_loss
    overall_attendance=(total_actual/total_wh_target*100) if total_wh_target>0 else 0
    labels, nd, rd, td, ld, netd, ahtd, qad = get_filtered_stats(period, year, month, quarter, week)
    
    # Alerts
    alerts_html=""
    critical=[a for a in agent_stats if a["loss"]>=4]
    if critical:
        alerts_html+="<div class='card-dark mb-3' style='border:1px solid #ef4444;background:#450a0a'><h6 style='color:#fca5a5'>Alerts - Loss >=4h</h6>"
        for a in critical:
            alerts_html+=f"<div style='color:#fca5a5;font-size:12px'>{a['name']} - {a['loss']}h Loss</div>"
        alerts_html+="</div>"
    
    # Filter UI
    filter_html = f"""
    <div class="card-dark mb-3" style="border:1px solid #fbbf24">
      <h6 style="color:#fbbf24">Filters | {datetime.now(PH_TZ).strftime("%b %d, %Y %I:%M %p")} | Working Hours: 10h/day x 22 days = 220h/month</h6>
      <form method="GET" class="row g-2 mt-2">
        <div class="col-6 col-md-2"><label class="label">PERIOD</label><select name="period" class="form-select form-select-sm" onchange="this.form.submit()"><option value="monthly" {"selected" if period=="monthly" else ""}>Monthly</option><option value="daily" {"selected" if period=="daily" else ""}>Daily</option><option value="yearly" {"selected" if period=="yearly" else ""}>Yearly</option></select></div>
        <div class="col-6 col-md-2"><label class="label">YEAR</label><select name="year" class="form-select form-select-sm" onchange="this.form.submit()"><option value="2024" {"selected" if year=="2024" else ""}>2024</option><option value="2025" {"selected" if year=="2025" else ""}>2025</option><option value="2026" {"selected" if year=="2026" else ""}>2026</option></select></div>
        <div class="col-12 col-md-2 d-flex align-items-end"><a href="/" class="btn btn-sm btn-outline-light w-100">Reset</a></div>
      </form>
    </div>
    """
    
    html=alerts_html+filter_html
    html+=f"<div class='row g-2'><div class='col-6 col-md-2'><div class='kpi' style='border:1px solid #22c55e'><div class='label'>NORMAL OT</div><div class='val-big' style='color:#22c55e'>{round(team_n,1)}h</div></div></div><div class='col-6 col-md-2'><div class='kpi' style='border:1px solid #3b82f6'><div class='label'>RESTDAY OT</div><div class='val-big' style='color:#3b82f6'>{round(team_r,1)}h</div></div></div><div class='col-6 col-md-2'><div class='kpi' style='border:1px solid #fbbf24'><div class='label'>TOTAL OT</div><div class='val-big' style='color:#fbbf24'>{round(team_tot,1)}h</div></div></div><div class='col-6 col-md-2'><div class='kpi' style='border:1px solid #ef4444'><div class='label'>LOSS HRS</div><div class='val-big' style='color:#ef4444'>{round(team_loss,1)}h</div></div></div><div class='col-6 col-md-2'><div class='kpi' style='border:1px solid #a855f7'><div class='label'>TEAM NET</div><div class='val-big' style='color:#a855f7'>+{round(team_tot-team_loss,1)}h</div></div></div><div class='col-6 col-md-2'><div class='kpi' style='border:1px solid #06b6d4'><div class='label'>AVG OT</div><div class='val-big' style='color:#06b6d4'>{round(avg_ot,1)}h</div></div></div></div>"
    


    html+="<div class='row g-2 mt-3'>"
    html+=f"<div class='col-12'><h6 style='color:#fbbf24;margin:8px 0'>📊 TL Overall Team KPI - QA, AHT, ATTENDANCE (Main UI for TL)</h6></div>"
    html+=f"<div class='col-6 col-md-2'><div class='kpi' style='border:2px solid #8b5cf6'><div class='label'>TEAM AVG QA</div><div class='val-big' style='color:#8b5cf6'>{round(avg_qa_team,1)}%</div><small style='color:var(--text2);font-size:10px'>{len(team_qa_vals)} agents</small></div></div>"
    html+=f"<div class='col-6 col-md-2'><div class='kpi' style='border:2px solid #f97316'><div class='label'>TEAM AVG AHT</div><div class='val-big' style='color:#f97316'>{round(avg_aht_team,1)}m</div></div></div>"
    html+=f"<div class='col-6 col-md-2'><div class='kpi' style='border:2px solid #22c55e'><div class='label'>TEAM ATTENDANCE</div><div class='val-big' style='color:#22c55e'>{round(overall_attendance,1)}%</div></div></div>"
    html+=f"<div class='col-6 col-md-2'><div class='kpi' style='border:2px solid #06b6d4'><div class='label'>TEAM AVG CSAT</div><div class='val-big' style='color:#06b6d4'>{round(avg_csat_team,1)}%</div></div></div>"
    html+=f"<div class='col-6 col-md-2'><div class='kpi' style='border:2px solid #f59e0b'><div class='label'>TEAM AVG FCR</div><div class='val-big' style='color:#f59e0b'>{round(avg_fcr_team,1)}%</div></div></div>"
    html+=f"<div class='col-6 col-md-2'><div class='kpi' style='border:2px solid #22c55e'><div class='label'>WH COMP AVG</div><div class='val-big' style='color:#22c55e'>{round(avg_wh_comp_team,1)}%</div></div></div>"
    html+="</div>"

    # Top 3 Ranking UI - Enhanced ViewCard
    top3=sorted(agent_stats, key=lambda x: x["tot"], reverse=True)[:3]
    top_qa=sorted([a for a in agent_stats if a["qa"]>0], key=lambda x: x["qa"], reverse=True)[:3]
    top_csat=sorted([a for a in agent_stats if a["csat"]>0], key=lambda x: x["csat"], reverse=True)[:3]
    html+="<div class='row g-2 mt-3'>"
    html+="<div class='col-12 col-md-4'><div class='card-dark' style='border:1px solid #fbbf24;background:linear-gradient(135deg,#1e293b,#0f172a)'><h6 style='color:#fbbf24'>🏆 Top 3 OT Earners - Ranking UI</h6><div class='mt-3'>"
    for idx, a in enumerate(top3):
        medal="🥇" if idx==0 else "🥈" if idx==1 else "🥉"
        bg="#fbbf241a" if idx==0 else "#94a3b81a" if idx==1 else "#f973161a"
        border="#fbbf24" if idx==0 else "#94a3b8" if idx==1 else "#f97316"
        html+=f"<div style='background:{bg};border:1px solid {border};padding:10px;border-radius:12px;margin-bottom:8px;display:flex;justify-content:space-between;align-items:center'><div style='display:flex;align-items:center;gap:8px'><span style='font-size:20px'>{medal}</span><div><div style='color:white;font-weight:700;font-size:13px'>{a['name']}</div><small style='color:#94a3b8'>{a['tid']}</small></div></div><div style='text-align:right'><div style='color:#fbbf24;font-weight:800'>{a['tot']}h</div><small style='color:#94a3b8'>{round(a['pct'],0)}% target</small></div></div>"
    html+="</div></div></div>"
    html+="<div class='col-12 col-md-4'><div class='card-dark' style='border:1px solid #8b5cf6;background:linear-gradient(135deg,#1e1b4b,#0f172a)'><h6 style='color:#8b5cf6'>⭐ Top 3 QA - Ranking UI</h6><div class='mt-3'>"
    if top_qa:
        for idx, a in enumerate(top_qa):
            medal="🥇" if idx==0 else "🥈" if idx==1 else "🥉"
            html+=f"<div style='background:#8b5cf61a;border:1px solid #8b5cf6;padding:10px;border-radius:12px;margin-bottom:8px;display:flex;justify-content:space-between;align-items:center'><div style='display:flex;align-items:center;gap:8px'><span style='font-size:20px'>{medal}</span><div><div style='color:white;font-weight:700;font-size:13px'>{a['name']}</div><small style='color:#94a3b8'>{a['tid']}</small></div></div><div style='text-align:right'><div style='color:#8b5cf6;font-weight:800'>{a['qa']}%</div><small style='color:#94a3b8'>QA</small></div></div>"
    else:
        html+="<div style='color:#64748b;text-align:center;padding:20px'>No QA data<br><small>Add QA logs</small></div>"
    html+="</div></div></div>"
    html+="<div class='col-12 col-md-4'><div class='card-dark' style='border:1px solid #06b6d4;background:linear-gradient(135deg,#083344,#0f172a)'><h6 style='color:#06b6d4'>😊 Top 3 CSAT - Ranking UI</h6><div class='mt-3'>"
    if top_csat:
        for idx, a in enumerate(top_csat):
            medal="🥇" if idx==0 else "🥈" if idx==1 else "🥉"
            html+=f"<div style='background:#06b6d41a;border:1px solid #06b6d4;padding:10px;border-radius:12px;margin-bottom:8px;display:flex;justify-content:space-between;align-items:center'><div style='display:flex;align-items:center;gap:8px'><span style='font-size:20px'>{medal}</span><div><div style='color:white;font-weight:700;font-size:13px'>{a['name']}</div><small style='color:#94a3b8'>{a['tid']}</small></div></div><div style='text-align:right'><div style='color:#06b6d4;font-weight:800'>{a['csat']}%</div><small style='color:#94a3b8'>CSAT</small></div></div>"
    else:
        html+="<div style='color:#64748b;text-align:center;padding:20px'>No CSAT data<br><small>Add CSAT logs</small></div>"
    html+="</div></div></div></div>"
    # Charts
    # Charts - TL KPI QA, AHT, ATTENDANCE Graphs
    html+=f"""
    <div class="row g-3 mt-3">
      <div class="col-12 col-md-6"><div class="chart-card" style="border:1px solid #22c55e"><h6 style="color:#22c55e">Normal OT - {period}</h6><canvas id="chartNormal"></canvas></div></div>
      <div class="col-12 col-md-6"><div class="chart-card" style="border:1px solid #3b82f6"><h6 style="color:#3b82f6">Restday OT</h6><canvas id="chartRestday"></canvas></div></div>
      <div class="col-12 col-md-6"><div class="chart-card" style="border:1px solid #fbbf24"><h6 style="color:#fbbf24">Total OT</h6><canvas id="chartTotal"></canvas></div></div>
      <div class="col-12 col-md-6"><div class="chart-card" style="border:1px solid #ef4444"><h6 style="color:#ef4444">Loss Hrs</h6><canvas id="chartLoss"></canvas></div></div>
    </div>
    <div class="row g-3 mt-3">
      <div class="col-12"><h6 style="color:#fbbf24;margin:8px 0">📈 TL Team KPI Graphs - QA, AHT, ATTENDANCE (Main UI for TL)</h6></div>
      <div class="col-12 col-md-4"><div class="chart-card" style="border:1px solid #8b5cf6"><h6 style="color:#8b5cf6">Team QA Trend - {period}</h6><canvas id="chartQA"></canvas></div></div>
      <div class="col-12 col-md-4"><div class="chart-card" style="border:1px solid #f97316"><h6 style="color:#f97316">Team AHT Trend - {period}</h6><canvas id="chartAHT"></canvas></div></div>
      <div class="col-12 col-md-4"><div class="chart-card" style="border:1px solid #22c55e"><h6 style="color:#22c55e">Team Attendance Trend - {period}</h6><canvas id="chartAttendance"></canvas></div></div>
    </div>
    <script>
    const labels = {labels};
    const nd = {nd}; const rd = {rd}; const td = {td}; const ld = {ld};
    function makeChart(id, label, data, color){{
      new Chart(document.getElementById(id), {{type:'line', data:{{labels: labels, datasets:[{{label: label, data: data, borderColor: color, backgroundColor: color+'33', fill:true, tension:0.4}}]}}, options:{{responsive:true, plugins:{{legend:{{display:false}}}}, scales:{{y:{{beginAtZero:true}}}}}}}});
    }}
    makeChart('chartNormal','Normal',nd,'#22c55e'); makeChart('chartRestday','Restday',rd,'#3b82f6'); makeChart('chartTotal','Total',td,'#fbbf24'); makeChart('chartLoss','Loss',ld,'#ef4444'); makeChart('chartQA','QA',qad,'#8b5cf6'); makeChart('chartAHT','AHT',ahtd,'#f97316'); makeChart('chartAttendance','Attendance',netd,'#22c55e');
    </script>
    """
    
    # Full Team Table with PROGRESS BAR
    html+="<div class='card-dark mt-3'><div class='d-flex justify-content-between'><h6 style='color:white'>Full Team - With Progress Bar</h6><div class='d-flex gap-2'><input id='teamSearch' class='form-control form-control-sm' placeholder='Search agent...' style='width:160px'><a href='/agents' class='btn btn-sm btn-warning'>All Agents</a></div></div><div class='table-responsive mt-3'><table id='teamTable' class='table table-sm'><thead><tr><th>AGENT</th><th>TOTAL OT</th><th>TARGET</th><th>PROGRESS BAR</th><th>WH COMP</th><th>LOSS</th><th>QA/CSAT</th><th>STATUS</th></tr></thead><tbody>"
    for a in sorted(agent_stats, key=lambda x: x["tot"], reverse=True):
        pct = min(100, a['pct'])
        bar_color = "#22c55e" if pct>=100 else "#fbbf24" if pct>=70 else "#ef4444"
        wh_pct = min(100, a['wh_comp'])
        wh_color = "#22c55e" if wh_pct>=95 else "#fbbf24" if wh_pct>=90 else "#ef4444"
        st = "<span class='badge bg-danger'>Critical</span>" if a['loss']>=4 else "<span class='badge bg-success'>Good</span>"
        html+=f"<tr><td><a href='/view/{a['id']}' style='color:white;text-decoration:none'><b>{a['name']}</b><br><small style='color:#94a3b8'>{a['tid']}</small></a></td><td style='color:#fbbf24'>{a['tot']}h</td><td>{a['target']}h</td><td><div class='progress' style='height:10px;width:100px;background:#0f172a'><div class='progress-bar' style='width:{pct}%;background:{bar_color}'></div></div><small style='font-size:10px'>{round(a['pct'],0)}%</small></td><td><div class='progress' style='height:8px;width:80px;background:#0f172a'><div class='progress-bar' style='width:{wh_pct}%;background:{wh_color}'></div></div><small>{round(wh_pct,1)}%</small></td><td style='color:#ef4444'>{a['loss']}h</td><td>{a['qa']}% / {a['csat']}%</td><td>{st}</td></tr>"
    html+="</tbody></table></div></div><script>document.addEventListener('DOMContentLoaded',function(){var i=document.getElementById('teamSearch');if(!i)return;i.addEventListener('keyup',function(){var q=this.value.toLowerCase();document.querySelectorAll('#teamTable tbody tr').forEach(function(r){r.style.display=r.innerText.toLowerCase().includes(q)?'':'none';});});});</script>"
    return page(html)

@app.route("/agents")
@login_required
def agents_list():
    if session.get("role")=="agent":
        return redirect(f"/view/{session.get('agent_id')}")
    q=request.args.get("q","").lower().strip()
    edit_id=request.args.get("edit","")
    agents=get_all()
    filtered=[a for a in agents if q in str(a.get("NAME","")).lower() or q in str(a.get("TENCENT ID","")).lower() or q in str(a.get("TENCENT_ID","")).lower() or q in str(a.get("EMAIL","")).lower()] if q else agents
    rows=""
    for a in filtered:
        logs=get_ot(a.get("id"))
        n,r,tot,loss,net=calc(logs)
        t_id=a.get("TENCENT ID") or a.get("TENCENT_ID","")
        rows+=f"<tr><td>{a.get('id')}</td><td><a href='/view/{a.get('id')}' style='color:var(--text);text-decoration:none'><b>{a.get('NAME','')}</b><br><small style='color:var(--text2)'>{t_id} | {a.get('EMAIL','')}</small></a></td><td>{tot}h</td><td style='color:#ef4444'>{loss}h</td><td><a href='/view/{a.get('id')}' class='btn btn-sm btn-warning'>View</a> <a href='/agents?edit={a.get('id')}&q={q}' class='btn btn-sm btn-primary'>Edit</a> <a href='/delete_agent/{a.get('id')}' class='btn btn-sm btn-outline-danger' onclick=\"return confirm('Delete agent {a.get('NAME','')}?')\">X</a></td></tr>"
    if not rows:
        rows="<tr><td colspan=5 style='text-align:center;color:var(--text2)'>No agents</td></tr>"
    # Edit form if edit_id
    edit_agent=None
    if edit_id:
        for a in agents:
            if str(a.get("id"))==str(edit_id):
                edit_agent=a
                break
    edit_form=""
    if edit_agent:
        edit_form=f"""
        <div class='card-dark mt-3' style='border:2px solid #3b82f6'>
          <h6 style='color:#3b82f6'>✏️ Edit Agent - {edit_agent.get('NAME','')} - All Fields</h6>
          <form method='POST' action='/update_agent/{edit_agent.get('id')}' class='row g-2 mt-2'>
            <div class='col-12 col-md-4'><label class='label'>NAME</label><input name='NAME' class='form-control form-control-sm' value='{edit_agent.get('NAME','')}' required></div>
            <div class='col-6 col-md-2'><label class='label'>TENCENT ID</label><input name='TENCENT ID' class='form-control form-control-sm' value='{edit_agent.get('TENCENT ID','') or edit_agent.get('TENCENT_ID','')}' required></div>
            <div class='col-6 col-md-2'><label class='label'>DATE HIRED</label><input name='DATE HIRED' type='date' class='form-control form-control-sm' value='{edit_agent.get('DATE HIRED','')}'></div>
            <div class='col-6 col-md-2'><label class='label'>PHONE NAME</label><input name='PHONE NAME' class='form-control form-control-sm' value='{edit_agent.get('PHONE NAME','')}'></div>
            <div class='col-6 col-md-2'><label class='label'>NBS ID</label><input name='NBS ID' class='form-control form-control-sm' value='{edit_agent.get('NBS ID','')}'></div>
            <div class='col-6 col-md-2'><label class='label'>HEADSET SN</label><input name='HEADSET SN' class='form-control form-control-sm' value='{edit_agent.get('HEADSET SN','')}'></div>
            <div class='col-6 col-md-2'><label class='label'>IBAS</label><input name='IBAS' class='form-control form-control-sm' value='{edit_agent.get('IBAS','')}'></div>
            <div class='col-6 col-md-3'><label class='label'>DJANGO</label><input name='DJANGO' class='form-control form-control-sm' value='{edit_agent.get('DJANGO','')}'></div>
            <div class='col-6 col-md-3'><label class='label'>NT LOG IN</label><input name='NT LOG IN' class='form-control form-control-sm' value='{edit_agent.get('NT LOG IN','')}'></div>
            <div class='col-12 col-md-4'><label class='label'>Sales Force</label><input name='Sales Force' class='form-control form-control-sm' value='{edit_agent.get('Sales Force','')}'></div>
            <div class='col-12 col-md-4'><label class='label'>ZOHO</label><input name='ZOHO' class='form-control form-control-sm' value='{edit_agent.get('ZOHO','')}'></div>
            <div class='col-12 col-md-4'><label class='label'>BSS WEB</label><input name='BSS WEB' class='form-control form-control-sm' value='{edit_agent.get('BSS WEB','')}'></div>
            <div class='col-12 col-md-4'><label class='label'>EMAIL</label><input name='EMAIL' type='email' class='form-control form-control-sm' value='{edit_agent.get('EMAIL','')}'></div>
            <div class='col-6 col-md-2'><label class='label'>BIRTHDAY</label><input name='BIRTHDAY' type='date' class='form-control form-control-sm' value='{edit_agent.get('BIRTHDAY','')}'></div>
            <div class='col-6 col-md-2'><label class='label'>CONTACT NO.</label><input name='CONTACT NO.' class='form-control form-control-sm' value='{edit_agent.get('CONTACT NO.','')}'></div>
            <div class='col-12 col-md-4'><label class='label'>ADDRESS</label><input name='ADDRESS' class='form-control form-control-sm' value='{edit_agent.get('ADDRESS','')}'></div>
            <div class='col-6 col-md-2'><label class='label'>TARGET_OT</label><input name='TARGET_OT' type='number' step='0.5' class='form-control form-control-sm' value='{edit_agent.get('TARGET_OT', edit_agent.get('TARGET OT','20'))}'></div>
            <div class='col-6 col-md-2'><label class='label'>WORKING_HOURS_TARGET</label><input name='WORKING_HOURS_TARGET' type='number' class='form-control form-control-sm' value='{edit_agent.get('WORKING_HOURS_TARGET', edit_agent.get('WORKING HOURS TARGET','220'))}'></div>
            <div class='col-6 col-md-2'><label class='label'>LOGIN_PASS</label><input name='LOGIN_PASS' class='form-control form-control-sm' value='{edit_agent.get('LOGIN_PASS','')}'></div>
            <div class='col-12 d-flex gap-2 mt-2'><button class='btn btn-primary w-100'>💾 Update Agent</button><a href='/agents' class='btn btn-outline-light w-100'>Cancel</a></div>
          </form>
        </div>
        """
    return page(f"""
    <div class='d-flex justify-content-between flex-wrap gap-2'><h5 style='color:var(--text)'>All Agents ({len(filtered)}/{len(agents)})</h5><div class='d-flex gap-2'><form method='GET' class='d-flex gap-2'><input name='q' value='{q}' class='form-control form-control-sm' placeholder='Search name, ID, email...' style='width:200px'><button class='btn btn-sm btn-warning'>Search</button></form><a href='/' class='btn btn-sm btn-outline-light'>Dashboard</a></div></div>
    <div class='card-dark mt-3' style='border:1px solid #22c55e'>
      <h6 style='color:#22c55e'>➕ Add New Agent - Full Fields</h6>
      <form method='POST' action='/add_agent' class='row g-2 mt-2'>
        <div class='col-12 col-md-4'><label class='label'>NAME *</label><input name='NAME' class='form-control form-control-sm' placeholder='Bernaldo, Catherine' required></div>
        <div class='col-6 col-md-2'><label class='label'>TENCENT ID *</label><input name='TENCENT ID' class='form-control form-control-sm' placeholder='5116' required></div>
        <div class='col-6 col-md-2'><label class='label'>DATE HIRED</label><input name='DATE HIRED' type='date' class='form-control form-control-sm'></div>
        <div class='col-6 col-md-2'><label class='label'>PHONE NAME</label><input name='PHONE NAME' class='form-control form-control-sm' placeholder='HOPE'></div>
        <div class='col-6 col-md-2'><label class='label'>NBS ID</label><input name='NBS ID' class='form-control form-control-sm' placeholder='10116'></div>
        <div class='col-6 col-md-2'><label class='label'>HEADSET SN</label><input name='HEADSET SN' class='form-control form-control-sm' placeholder='2309410DUO286'></div>
        <div class='col-6 col-md-2'><label class='label'>IBAS</label><input name='IBAS' class='form-control form-control-sm' placeholder='CATBERNA'></div>
        <div class='col-6 col-md-3'><label class='label'>DJANGO</label><input name='DJANGO' class='form-control form-control-sm' placeholder='cabernaldo@uas2.com.ph'></div>
        <div class='col-6 col-md-3'><label class='label'>NT LOG IN</label><input name='NT LOG IN' class='form-control form-control-sm' placeholder='UAS-Bernaldo.Catheri'></div>
        <div class='col-12 col-md-4'><label class='label'>Sales Force</label><input name='Sales Force' class='form-control form-control-sm' placeholder='uas-bernaldo.cath@cict.com.ph'></div>
        <div class='col-12 col-md-4'><label class='label'>ZOHO</label><input name='ZOHO' class='form-control form-control-sm' placeholder='c.bernaldo@uas2.com.ph'></div>
        <div class='col-12 col-md-4'><label class='label'>BSS WEB</label><input name='BSS WEB' class='form-control form-control-sm' placeholder='uas-bernaldo.cath@partner...'></div>
        <div class='col-12 col-md-4'><label class='label'>EMAIL</label><input name='EMAIL' type='email' class='form-control form-control-sm' placeholder='bernaldocatherine2@gmail.com'></div>
        <div class='col-6 col-md-2'><label class='label'>BIRTHDAY</label><input name='BIRTHDAY' type='date' class='form-control form-control-sm'></div>
        <div class='col-6 col-md-2'><label class='label'>CONTACT NO.</label><input name='CONTACT NO.' class='form-control form-control-sm' placeholder='09468168239'></div>
        <div class='col-12 col-md-4'><label class='label'>ADDRESS</label><input name='ADDRESS' class='form-control form-control-sm' placeholder='15-C Feliza St. Angeles City'></div>
        <div class='col-6 col-md-2'><label class='label'>TARGET_OT</label><input name='TARGET_OT' type='number' step='0.5' class='form-control form-control-sm' value='20'></div>
        <div class='col-6 col-md-2'><label class='label'>WORKING_HOURS_TARGET</label><input name='WORKING_HOURS_TARGET' type='number' class='form-control form-control-sm' value='220'></div>
        <div class='col-6 col-md-2'><label class='label'>LOGIN_PASS</label><input name='LOGIN_PASS' class='form-control form-control-sm' placeholder='Default TENCENT ID'></div>
        <div class='col-12 mt-2'><button class='btn btn-success w-100'>➕ Add Agent - Full Fields</button></div>
      </form>
    </div>
    {edit_form}
    <div class='card-dark mt-3'><div class='table-responsive'><table class='table'><thead><tr><th>ID</th><th>AGENT</th><th>TOTAL OT</th><th>LOSS</th><th>ACTION</th></tr></thead><tbody>{rows}</tbody></table></div></div>
    """)

@app.route("/add_agent", methods=["POST"])
@login_required
def add_agent():
    if session.get("role")=="agent":
        return redirect("/")
    try:
        # All fields from DB
        fields = ["NAME","TENCENT ID","DATE HIRED","PHONE NAME","NBS ID","HEADSET SN","IBAS","DJANGO","NT LOG IN","Sales Force","ZOHO","BSS WEB","EMAIL","BIRTHDAY","CONTACT NO.","ADDRESS","TARGET_OT","WORKING_HOURS_TARGET","LOGIN_PASS"]
        data={}
        for f in fields:
            val=request.form.get(f,"").strip()
            if val:
                data[f]=val
        # Compatibility: also store TENCENT_ID underscore version
        if "TENCENT ID" in data:
            data["TENCENT_ID"]=data["TENCENT ID"]
        if "TARGET_OT" in data:
            data["TARGET_OT"]=data["TARGET_OT"]
            data["TARGET OT"]=data["TARGET_OT"]
        if "WORKING_HOURS_TARGET" in data:
            data["WORKING_HOURS_TARGET"]=data["WORKING_HOURS_TARGET"]
            data["WORKING HOURS TARGET"]=data["WORKING_HOURS_TARGET"]
        if not data.get("NAME") or not (data.get("TENCENT ID") or data.get("TENCENT_ID")):
            return redirect("/agents")
        if not data.get("LOGIN_PASS"):
            data["LOGIN_PASS"]=data.get("TENCENT ID") or data.get("TENCENT_ID") or "1234"
        if not data.get("TARGET_OT"):
            data["TARGET_OT"]="20"
        if not data.get("WORKING_HOURS_TARGET"):
            data["WORKING_HOURS_TARGET"]="220"
        agents=get_all()
        max_id=0
        for a in agents:
            try:
                max_id=max(max_id, int(a.get("id",0)))
            except:
                pass
        new_id=str(max_id+1)
        data["id"]=new_id
        if db_root:
            db_root.child(f"agents/{new_id}").set(data)
            try:
                db_root.child("login_logs").push({"user": session.get("user"),"name": session.get("name"),"role": "admin","type": f"ADD_AGENT {data.get('NAME')}","timestamp": datetime.now(PH_TZ).strftime("%Y-%m-%d %I:%M:%S %p"),"date": datetime.now(PH_TZ).strftime("%Y-%m-%d"),"agent_id": new_id})
            except:
                pass
    except Exception as e:
        print(f"add_agent error: {e}")
        traceback.print_exc()
    return redirect("/agents")

@app.route("/update_agent/<aid>", methods=["POST"])
@login_required
def update_agent(aid):
    if session.get("role")=="agent":
        return redirect("/")
    try:
        fields = ["NAME","TENCENT ID","DATE HIRED","PHONE NAME","NBS ID","HEADSET SN","IBAS","DJANGO","NT LOG IN","Sales Force","ZOHO","BSS WEB","EMAIL","BIRTHDAY","CONTACT NO.","ADDRESS","TARGET_OT","WORKING_HOURS_TARGET","LOGIN_PASS"]
        data={}
        for f in fields:
            val=request.form.get(f,"").strip()
            data[f]=val
        # Keep compatibility
        if "TENCENT ID" in data and data["TENCENT ID"]:
            data["TENCENT_ID"]=data["TENCENT ID"]
        if "TARGET_OT" in data:
            data["TARGET OT"]=data["TARGET_OT"]
        if "WORKING_HOURS_TARGET" in data:
            data["WORKING HOURS TARGET"]=data["WORKING_HOURS_TARGET"]
        data["id"]=aid
        # Remove empty fields? Keep all to update
        # Get existing to preserve id
        if db_root:
            # Update existing agent
            existing=db_root.child(f"agents/{aid}").get()
            if existing:
                # Merge
                if isinstance(existing, dict):
                    for k,v in data.items():
                        if v!="":
                            existing[k]=v
                    # Ensure compatibility fields
                    if existing.get("TENCENT ID"):
                        existing["TENCENT_ID"]=existing["TENCENT ID"]
                    db_root.child(f"agents/{aid}").set(existing)
                else:
                    db_root.child(f"agents/{aid}").set(data)
            else:
                db_root.child(f"agents/{aid}").set(data)
            try:
                db_root.child("login_logs").push({"user": session.get("user"),"name": session.get("name"),"role": "admin","type": f"UPDATE_AGENT {data.get('NAME')}","timestamp": datetime.now(PH_TZ).strftime("%Y-%m-%d %I:%M:%S %p"),"date": datetime.now(PH_TZ).strftime("%Y-%m-%d"),"agent_id": aid})
            except:
                pass
    except Exception as e:
        print(f"update_agent error: {e}")
        traceback.print_exc()
    return redirect("/agents")

@app.route("/delete_agent/<aid>")
@login_required
def delete_agent(aid):
    if session.get("role")!="admin":
        return redirect("/agents")
    try:
        if db_root:
            db_root.child(f"agents/{aid}").delete()
            try:
                db_root.child("login_logs").push({"user": session.get("user"),"name": session.get("name"),"role": "admin","type": f"DELETE_AGENT ID {aid}","timestamp": datetime.now(PH_TZ).strftime("%Y-%m-%d %I:%M:%S %p"),"date": datetime.now(PH_TZ).strftime("%Y-%m-%d"),"agent_id": aid})
            except:
                pass
    except:
        pass
    return redirect("/agents")


@app.route("/announcements")
@login_required
def announcements_page():
    anns=get_all_announcements()
    agents=get_all()
    reads=get_announcement_reads()
    role=session.get("role","")
    is_agent=role=="agent"
    if is_agent:
        agent_id=session.get("agent_id")
        html_cards=""
        for ann in anns:
            read=has_read(ann.get("id"), agent_id)
            reads_count=len(get_reads_for_announcement(ann.get("id")))
            important_badge="<span class='badge bg-danger'>IMPORTANT</span>" if str(ann.get("important"))=="true" else ""
            status_html="<span class='badge bg-success'>✅ Nabasa</span>" if read else f"<a href='/confirm_announcement/{ann.get('id')}' class='btn btn-sm btn-success'>✅ Confirm Nabasa</a>"
            html_cards+=f"<div class='card-dark mt-2' style='border:2px solid #fbbf24'><div class='d-flex justify-content-between'><b>{ann.get('title','')} {important_badge}</b><small>{ann.get('created_at','')}</small></div><p style='margin:8px 0'>{ann.get('message','')}</p><div class='d-flex justify-content-between'><small>By: {ann.get('created_by','')} | {reads_count} confirmed</small>{status_html}</div></div>"
        if not html_cards:
            html_cards="<div class='card-dark mt-3'><p style='text-align:center;color:var(--text2)'>No announcements</p></div>"
        return page(f"<h5>📢 Announcements</h5>{html_cards}<div class='mt-3'><a href='/view/{agent_id}' class='btn btn-sm btn-outline-light'>Back</a></div>")
    rows=""
    for ann in anns:
        ann_reads=get_reads_for_announcement(ann.get("id"))
        read_list=""
        for r in ann_reads:
            read_list+=f"<span class='badge bg-success' style='margin:2px'>{r.get('agent_name','')} ✅</span> "
        if not read_list:
            read_list="<small style='color:var(--text2)'>0 reads</small>"
        important_badge="<span class='badge bg-danger'>IMPORTANT</span>" if str(ann.get("important"))=="true" else ""
        rows+=f"<div class='card-dark mt-2'><div class='d-flex justify-content-between'><b>{ann.get('title','')} {important_badge}</b><div><small>{ann.get('created_at','')}</small> <a href='/delete_announcement/{ann.get('id')}' class='btn btn-sm btn-outline-danger'>X</a></div></div><p style='font-size:13px'>{ann.get('message','')}</p><small>{len(ann_reads)}/{len(agents)} confirmed</small><div class='mt-2'>{read_list}</div></div>"
    if not rows:
        rows="<div class='card-dark mt-3'><p style='text-align:center;color:var(--text2)'>No announcements</p></div>"
    return page(f"<h5>📢 Announcements Management</h5><div class='card-dark mt-3' style='border:2px solid #fbbf24'><h6>➕ Post Announcement</h6><form method='POST' action='/add_announcement' class='row g-2 mt-2'><div class='col-12 col-md-8'><input name='title' class='form-control form-control-sm' placeholder='Title' required></div><div class='col-12 col-md-4'><select name='important' class='form-select form-select-sm'><option value='false'>Normal</option><option value='true'>Important</option></select></div><div class='col-12'><textarea name='message' class='form-control form-control-sm' rows='3' placeholder='Message' required></textarea></div><div class='col-12'><button class='btn btn-warning w-100'>📢 Post Announcement</button></div></form></div><div class='mt-4'><h6>All Announcements ({len(anns)})</h6>{rows}</div><div class='mt-3'><a href='/' class='btn btn-sm btn-outline-light'>Back</a></div>")

@app.route("/add_announcement", methods=["POST"])
@login_required
def add_announcement():
    if session.get("role")=="agent":
        return redirect("/announcements")
    try:
        title=request.form.get("title","").strip()
        message=request.form.get("message","").strip()
        important=request.form.get("important","false")
        if not title or not message:
            return redirect("/announcements")
        if db_root:
            import uuid
            ann_id=str(uuid.uuid4())[:8]
            db_root.child(f"announcements/{ann_id}").set({"id": ann_id, "title": title, "message": message, "important": important, "created_by": session.get("name","TL"), "created_at": datetime.now(PH_TZ).strftime("%Y-%m-%d %I:%M %p"), "date": datetime.now(PH_TZ).strftime("%Y-%m-%d")})
    except:
        pass
    return redirect("/announcements")

@app.route("/delete_announcement/<ann_id>")
@login_required
def delete_announcement(ann_id):
    if session.get("role")=="agent":
        return redirect("/announcements")
    try:
        if db_root:
            db_root.child(f"announcements/{ann_id}").delete()
            reads=get_announcement_reads()
            for r in reads:
                if str(r.get("announcement_id"))==str(ann_id):
                    db_root.child(f"announcement_reads/{r.get('id')}").delete()
    except:
        pass
    return redirect("/announcements")

@app.route("/confirm_announcement/<ann_id>")
@login_required
def confirm_announcement(ann_id):
    try:
        agent_id=session.get("agent_id") or session.get("user")
        agent_name=session.get("name") or session.get("user")
        if not agent_id or has_read(ann_id, agent_id):
            return redirect("/announcements")
        if db_root:
            import uuid
            read_id=str(uuid.uuid4())[:8]
            db_root.child(f"announcement_reads/{read_id}").set({"id": read_id, "announcement_id": ann_id, "agent_id": agent_id, "agent_name": agent_name, "read_at": datetime.now(PH_TZ).strftime("%Y-%m-%d %I:%M %p"), "date": datetime.now(PH_TZ).strftime("%Y-%m-%d")})
    except:
        pass
    return redirect("/announcements")

@app.route("/upload_avatar/<aid>", methods=["POST"])
@login_required
def upload_avatar(aid):
    try:
        if 'avatar' not in request.files:
            return redirect(f"/view/{aid}")
        file=request.files['avatar']
        if file.filename=='':
            return redirect(f"/view/{aid}")
        if not file.content_type.startswith('image/'):
            return redirect(f"/view/{aid}")
        import base64
        data=file.read()
        if len(data)>200*1024:
            return page(f"<div class='card-dark'><h6 style='color:#ef4444'>Image too large max 200KB</h6><a href='/view/{aid}' class='btn btn-sm btn-outline-light'>Back</a></div>")
        b64=base64.b64encode(data).decode('utf-8')
        data_url=f"data:{file.content_type};base64,{b64}"
        if db_root:
            db_root.child(f"agents/{aid}/AVATAR").set(data_url)
    except:
        pass
    return redirect(f"/view/{aid}")

@app.route("/delete_avatar/<aid>")
@login_required
def delete_avatar(aid):
    try:
        if db_root:
            db_root.child(f"agents/{aid}/AVATAR").delete()
    except:
        pass
    return redirect(f"/view/{aid}")



@app.route("/view/<aid>")
@login_required
def view(aid):
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
    la,lq,lc,lf,aa,qa,ac,af=calc_perf(plogs)
    from collections import defaultdict
    date_groups=defaultdict(list)
    for l in logs:
        date_groups[l.get("date")].append(l)
    sdates=sorted(date_groups.keys())[-14:]
    ind_labels=[]; ind_tot=[]; ind_loss=[]
    for d in sdates:
        ll=date_groups[d]
        _,_,t,lo,ne=calc(ll)
        ind_labels.append(d[-5:] if d else "")
        ind_tot.append(t)
        ind_loss.append(lo)
    pgroups=defaultdict(list)
    for l in plogs:
        pgroups[l.get("date")].append(l)
    ind_aht=[]; ind_qa=[]; ind_csat=[]; ind_fcr=[]
    for d in sdates:
        pl=pgroups.get(d,[])
        la2,lq2,lc2,lf2,aa2,qa2,ac2,af2=calc_perf(pl)
        ind_aht.append(aa2); ind_qa.append(qa2); ind_csat.append(ac2); ind_fcr.append(af2)
    log_rows=""
    for l in logs:
        col="#22c55e" if l.get("type")=="NORMAL_OT" else "#3b82f6" if l.get("type")=="RESTDAY_OT" else "#ef4444"
        log_rows+=f"<tr><td>{l.get('date','')}</td><td><span style='color:{col}'>{l.get('type')}</span></td><td>{l.get('hours')}h</td><td>{l.get('reason','')}</td><td><a href='/delete_log/{aid}/{l.get('log_id','')}' class='btn btn-sm btn-outline-danger'>X</a></td></tr>"
    if not log_rows:
        log_rows="<tr><td colspan=5 style='text-align:center;color:#64748b'>No logs</td></tr>"
    perf_rows=""
    for l in plogs:
        col="#f97316" if l.get("type")=="AHT" else "#8b5cf6" if l.get("type")=="QA" else "#06b6d4" if l.get("type")=="CSAT" else "#f59e0b" if l.get("type")=="FCR" else "#94a3b8"
        unit="m" if l.get("type")=="AHT" else "%"
        perf_rows+=f"<tr><td>{l.get('date','')}</td><td><span style='color:{col}'>{l.get('type')}</span></td><td>{l.get('value')}{unit}</td><td>{l.get('reason','')}</td><td><a href='/delete_perf/{aid}/{l.get('log_id','')}' class='btn btn-sm btn-outline-danger'>X</a></td></tr>"
    if not perf_rows:
        perf_rows="<tr><td colspan=5 style='text-align:center;color:#64748b'>No logs</td></tr>"
    initial=str(data.get("NAME","?"))[:1]
    target=float(data.get("TARGET_OT",20))
    wh_target=float(data.get("WORKING_HOURS_TARGET",220))
    pct=(tot/target*100) if target>0 else 0
    wh_comp=((wh_target-loss)/wh_target*100) if wh_target>0 else 0
    bar_color="#22c55e" if pct>=100 else "#fbbf24" if pct>=70 else "#ef4444"
    wh_bar_color="#22c55e" if wh_comp>=95 else "#fbbf24" if wh_comp>=90 else "#ef4444"
    is_agent=session.get("role")=="agent"
    risk_score=0
    if tot>40: risk_score+=30
    if loss>8: risk_score+=30
    if lq>0 and lq<80: risk_score+=20
    if la>10: risk_score+=20
    risk="Critical" if risk_score>=60 else "High" if risk_score>=40 else "Moderate" if risk_score>=20 else "Low"
    risk_color="#22c55e" if risk=="Low" else "#fbbf24" if risk=="Moderate" else "#f97316" if risk=="High" else "#ef4444"
    html=f"<a href='/' class='btn btn-sm btn-outline-light mb-3'>Back</a><div class='card-dark'><div class='text-center'><div style='width:90px;height:90px;background:linear-gradient(135deg,#fbbf24,#f59e0b);border-radius:18px;display:flex;align-items:center;justify-content:center;font-size:40px;font-weight:900;color:#111827;margin:auto'>{initial}</div><h4 style='color:white;margin-top:12px'>{data.get('NAME','')}</h4><small style='color:#94a3b8'>{data.get('TENCENT_ID','')} | WH: {wh_target}h | OT: {target}h</small><div class='mt-2'><small style='color:#94a3b8'>OT {round(pct,1)}% | WH {round(wh_comp,1)}% | Risk <span style='color:{risk_color}'>{risk}</span></small><div class='d-flex justify-content-center gap-2 mt-1'><div class='progress' style='height:8px;width:100px;background:#0f172a'><div class='progress-bar' style='width:{min(100,pct)}%;background:{bar_color}'></div></div><div class='progress' style='height:8px;width:100px;background:#0f172a'><div class='progress-bar' style='width:{min(100,wh_comp)}%;background:{wh_bar_color}'></div></div></div></div></div>"
    html+=f"<div class='row g-2 mt-3'><div class='col-4'><div class='kpi' style='border:1px solid #22c55e'><div class='label'>NORMAL</div><div class='val-big' style='color:#22c55e'>{n}h</div></div></div><div class='col-4'><div class='kpi' style='border:1px solid #3b82f6'><div class='label'>RESTDAY</div><div class='val-big' style='color:#3b82f6'>{r}h</div></div></div><div class='col-4'><div class='kpi' style='border:1px solid #ef4444'><div class='label'>LOSS</div><div class='val-big' style='color:#ef4444'>{loss}h</div></div></div><div class='col-6'><div class='kpi' style='border:1px solid #22c55e'><div class='label'>TOTAL OT</div><div class='val-big' style='color:#22c55e'>{tot}h</div></div></div><div class='col-6'><div class='kpi' style='border:1px solid #fbbf24'><div class='label'>NET</div><div class='val-big' style='color:#fbbf24'>+{net}h</div></div></div><div class='col-3'><div class='kpi' style='border:1px solid #f97316;min-height:80px;height:80px'><div class='label'>AHT</div><div class='val-big' style='font-size:16px;color:#f97316'>{la}m</div></div></div><div class='col-3'><div class='kpi' style='border:1px solid #8b5cf6;min-height:80px;height:80px'><div class='label'>QA</div><div class='val-big' style='font-size:16px;color:#8b5cf6'>{lq}%</div></div></div><div class='col-3'><div class='kpi' style='border:1px solid #06b6d4;min-height:80px;height:80px'><div class='label'>CSAT</div><div class='val-big' style='font-size:16px;color:#06b6d4'>{lc}%</div></div></div><div class='col-3'><div class='kpi' style='border:1px solid #f59e0b;min-height:80px;height:80px'><div class='label'>FCR</div><div class='val-big' style='font-size:16px;color:#f59e0b'>{lf}%</div></div></div></div>"

    # ViewCard AHT QA - Enhanced
    aht_status = "Good" if la<=7 and la>0 else "Warning" if la<=10 and la>0 else "Critical" if la>10 else "No data"
    aht_color = "#22c55e" if aht_status=="Good" else "#fbbf24" if aht_status=="Warning" else "#ef4444" if aht_status=="Critical" else "#64748b"
    qa_status = "Excellent" if lq>=90 else "Good" if lq>=75 else "Needs Improvement" if lq>0 else "No data"
    qa_color = "#22c55e" if qa_status=="Excellent" else "#fbbf24" if qa_status=="Good" else "#ef4444" if qa_status=="Needs Improvement" else "#64748b"
    csat_status = "Excellent" if lc>=90 else "Good" if lc>=85 else "Needs Improvement" if lc>0 else "No data"
    csat_color = "#22c55e" if csat_status=="Excellent" else "#fbbf24" if csat_status=="Good" else "#ef4444" if csat_status=="Needs Improvement" else "#64748b"
    fcr_status = "Excellent" if lf>=75 else "Good" if lf>=70 else "Needs Improvement" if lf>0 else "No data"
    fcr_color = "#22c55e" if fcr_status=="Excellent" else "#fbbf24" if fcr_status=="Good" else "#ef4444" if fcr_status=="Needs Improvement" else "#64748b"

    html+=f"""
    <div class="row g-3 mt-3">
      <div class="col-12 col-md-6">
        <div class="card-dark" style="border:2px solid #f97316;background:linear-gradient(135deg,#431407,#0f172a);min-height:160px">
          <div class="d-flex justify-content-between align-items-center">
            <h6 style="color:#f97316;margin:0">⏱️ AHT ViewCard</h6>
            <span class="badge" style="background:{aht_color};font-size:10px">{aht_status}</span>
          </div>
          <div class="row mt-3">
            <div class="col-6 text-center" style="border-right:1px solid #334155">
              <div style="color:#94a3b8;font-size:10px">Latest AHT</div>
              <div style="color:#f97316;font-size:36px;font-weight:900">{la}<small style="font-size:14px">m</small></div>
              <small style="color:#94a3b8">Target ≤7m Good</small>
            </div>
            <div class="col-6 text-center">
              <div style="color:#94a3b8;font-size:10px">Average AHT</div>
              <div style="color:white;font-size:28px;font-weight:800">{round(aa,1)}<small style="font-size:12px">m</small></div>
              <small style="color:#94a3b8">All logs avg</small>
              <div class="mt-2"><small style="color:{aht_color};font-size:11px">Industry 6m 3s avg</small></div>
            </div>
          </div>
        </div>
      </div>
      <div class="col-12 col-md-6">
        <div class="card-dark" style="border:2px solid #8b5cf6;background:linear-gradient(135deg,#2e1065,#0f172a);min-height:160px">
          <div class="d-flex justify-content-between align-items-center">
            <h6 style="color:#8b5cf6;margin:0">⭐ QA ViewCard</h6>
            <span class="badge" style="background:{qa_color};font-size:10px">{qa_status}</span>
          </div>
          <div class="row mt-3">
            <div class="col-6 text-center" style="border-right:1px solid #334155">
              <div style="color:#94a3b8;font-size:10px">Latest QA</div>
              <div style="color:#8b5cf6;font-size:36px;font-weight:900">{lq}<small style="font-size:14px">%</small></div>
              <small style="color:#94a3b8">Target 90%+ Excellent</small>
            </div>
            <div class="col-6 text-center">
              <div style="color:#94a3b8;font-size:10px">Average QA</div>
              <div style="color:white;font-size:28px;font-weight:800">{round(qa,1)}<small style="font-size:12px">%</small></div>
              <small style="color:#94a3b8">All logs avg</small>
              <div class="mt-2"><small style="color:{qa_color};font-size:11px">Industry 75-90% standard</small></div>
            </div>
          </div>
        </div>
      </div>
      <div class="col-12 col-md-6">
        <div class="card-dark" style="border:2px solid #06b6d4;background:linear-gradient(135deg,#0c4a6e,#0f172a);min-height:160px">
          <div class="d-flex justify-content-between align-items-center">
            <h6 style="color:#06b6d4;margin:0">⏱️ AHT vs Target & Industry</h6>
            <span class="badge" style="background:{aht_color};font-size:10px">AHT {aht_status}</span>
          </div>
          <div class="row mt-3">
            <div class="col-6 text-center" style="border-right:1px solid #334155">
              <div style="color:#94a3b8;font-size:10px">AHT TARGET</div>
              <div style="color:#06b6d4;font-size:18px;font-weight:800">≤7m Good<br><small style="font-size:11px">≤10m Warning</small></div>
              <div class="mt-2"><div class="progress" style="height:8px;width:100%;background:#0f172a"><div class="progress-bar" style="width:{min(100,(la/7*100) if la>0 else 0)}%;background:{aht_color}"></div></div></div>
            </div>
            <div class="col-6 text-center">
              <div style="color:#94a3b8;font-size:10px">Industry 6m 3s avg</div>
              <div style="color:white;font-size:13px;font-weight:700">6m 3s avg<br>Telco 8m 48s</div>
              <small style="color:#94a3b8">Your AHT: {la}m</small>
            </div>
          </div>
        </div>
      </div>
      <div class="col-12 col-md-6">
        <div class="card-dark" style="border:2px solid #f59e0b;background:linear-gradient(135deg,#451a03,#0f172a);min-height:160px">
          <div class="d-flex justify-content-between align-items-center">
            <h6 style="color:#f59e0b;margin:0">✅ FCR ViewCard</h6>
            <span class="badge" style="background:{fcr_color};font-size:10px">{fcr_status}</span>
          </div>
          <div class="row mt-3">
            <div class="col-6 text-center" style="border-right:1px solid #334155">
              <div style="color:#94a3b8;font-size:10px">Latest FCR</div>
              <div style="color:#f59e0b;font-size:36px;font-weight:900">{lf}<small style="font-size:14px">%</small></div>
              <small style="color:#94a3b8">Target 70-75%</small>
            </div>
            <div class="col-6 text-center">
              <div style="color:#94a3b8;font-size:10px">Average FCR</div>
              <div style="color:white;font-size:28px;font-weight:800">{round(af,1)}<small style="font-size:12px">%</small></div>
              <small style="color:#94a3b8">All logs avg</small>
            </div>
          </div>
        </div>
      </div>
    </div>
    """

    html+=f"""<div class="row g-3 mt-3"><div class="col-12 col-md-6"><div class="chart-card"><h6 style="color:#fbbf24">OT Trend</h6><canvas id="indOT"></canvas></div></div><div class="col-12 col-md-6"><div class="chart-card"><h6 style="color:#8b5cf6">QA/CSAT/FCR/AHT</h6><canvas id="indQA"></canvas></div></div></div><script>new Chart(document.getElementById('indOT'), {{type:'line', data:{{labels:{ind_labels}, datasets:[{{label:'OT', data:{ind_tot}, borderColor:'#fbbf24', backgroundColor:'#fbbf2433', fill:true, tension:0.4}},{{label:'Loss', data:{ind_loss}, borderColor:'#ef4444'}}]}}, options:{{responsive:true}}}}); new Chart(document.getElementById('indQA'), {{type:'line', data:{{labels:{ind_labels}, datasets:[{{label:'QA', data:{ind_qa}, borderColor:'#8b5cf6'}},{{label:'CSAT', data:{ind_csat}, borderColor:'#06b6d4'}},{{label:'FCR', data:{ind_fcr}, borderColor:'#f59e0b'}},{{label:'AHT', data:{ind_aht}, borderColor:'#f97316'}}]}}, options:{{responsive:true}}}});</script>"""
    html+=f"""<div class="card-dark mt-3" style="border:1px solid #334155"><div class="row g-2"><div class="col-6"><h6 style="color:#fbbf24">Target OT</h6><form method="POST" action="/set_target/{aid}" class="row g-2"><div class="col-6"><input name="target" type="number" step="0.5" class="form-control form-control-sm" value="{target}"></div><div class="col-6"><button class="btn btn-sm btn-warning w-100">Update OT</button></div></form></div><div class="col-6"><h6 style="color:#22c55e">WH Target 220h</h6><form method="POST" action="/set_working_hours/{aid}" class="row g-2"><div class="col-6"><input name="working_hours_target" type="number" step="1" class="form-control form-control-sm" value="{wh_target}"></div><div class="col-6"><button class="btn btn-sm btn-success w-100">Update WH</button></div></form></div></div></div>"""
    if session.get("role")=="admin":
        current_pw=data.get("LOGIN_PASS") or data.get("TENCENT_ID") or "1234"
        html+=f"""<div class="card-dark mt-3" style="border:1px solid #ef4444"><h6 style="color:#ef4444">Password - No current needed</h6><p style="color:#94a3b8;font-size:11px">Current: <span style="color:#fbbf24">{current_pw}</span> | User: {data.get("TENCENT_ID")}</p><form method="POST" action="/reset_password/{aid}" class="row g-2"><div class="col-6"><input name="new_pass" type="text" class="form-control form-control-sm" placeholder="Blank = reset to Tencent ID"></div><div class="col-6"><button class="btn btn-sm btn-danger w-100">Reset / Set Password</button></div></form></div>"""
    elif is_agent:
        html+=f"""<div class="card-dark mt-3" style="border:1px solid #fbbf24"><h6 style="color:#fbbf24">My Account</h6><a href="/change_password" class="btn btn-sm btn-warning w-100">Change Password</a></div>"""
    if not is_agent:
        html+=f"<div class='row g-2 mt-4'><div class='col-6'><div class='card-dark' style='border:1px solid #22c55e'><h6 style='color:#22c55e'>Add NORMAL OT</h6><form method='POST' action='/add_ot/{aid}' class='row g-2'><input type='hidden' name='type' value='NORMAL_OT'><div class='col-6'><input name='hours' type='number' step='0.5' class='form-control form-control-sm' placeholder='Hours' required></div><div class='col-6'><input name='date' type='date' class='form-control form-control-sm' value='{datetime.now(PH_TZ).strftime('%Y-%m-%d')}'></div><div class='col-12'><input name='reason' class='form-control form-control-sm' placeholder='Reason'></div><div class='col-12'><button class='btn w-100 mt-1' style='background:#22c55e;color:white'>Add Normal OT</button></div></form></div></div><div class='col-6'><div class='card-dark' style='border:1px solid #3b82f6'><h6 style='color:#3b82f6'>Add RESTDAY OT</h6><form method='POST' action='/add_ot/{aid}' class='row g-2'><input type='hidden' name='type' value='RESTDAY_OT'><div class='col-6'><input name='hours' type='number' step='0.5' class='form-control form-control-sm' placeholder='Hours' required></div><div class='col-6'><input name='date' type='date' class='form-control form-control-sm' value='{datetime.now(PH_TZ).strftime('%Y-%m-%d')}'></div><div class='col-12'><input name='reason' class='form-control form-control-sm' placeholder='Reason'></div><div class='col-12'><button class='btn w-100 mt-1' style='background:#3b82f6;color:white'>Add Restday</button></div></form></div></div><div class='col-6'><div class='card-dark' style='border:1px solid #f97316'><h6 style='color:#f97316'>Add AHT</h6><form method='POST' action='/add_perf/{aid}' class='row g-2'><input type='hidden' name='type' value='AHT'><div class='col-6'><input name='value' type='number' step='0.1' class='form-control form-control-sm' placeholder='Minutes' required></div><div class='col-6'><input name='date' type='date' class='form-control form-control-sm' value='{datetime.now(PH_TZ).strftime('%Y-%m-%d')}'></div><div class='col-12'><input name='reason' class='form-control form-control-sm' placeholder='Notes'></div><div class='col-12'><button class='btn w-100 mt-1' style='background:#f97316;color:white'>Add AHT</button></div></form></div></div><div class='col-6'><div class='card-dark' style='border:1px solid #8b5cf6'><h6 style='color:#8b5cf6'>Add QA</h6><form method='POST' action='/add_perf/{aid}' class='row g-2'><input type='hidden' name='type' value='QA'><div class='col-6'><input name='value' type='number' step='0.1' class='form-control form-control-sm' placeholder='%' required></div><div class='col-6'><input name='date' type='date' class='form-control form-control-sm' value='{datetime.now(PH_TZ).strftime('%Y-%m-%d')}'></div><div class='col-12'><input name='reason' class='form-control form-control-sm' placeholder='QA notes'></div><div class='col-12'><button class='btn w-100 mt-1' style='background:#8b5cf6;color:white'>Add QA</button></div></form></div></div><div class='col-6'><div class='card-dark' style='border:1px solid #06b6d4'><h6 style='color:#06b6d4'>Add CSAT</h6><form method='POST' action='/add_perf/{aid}' class='row g-2'><input type='hidden' name='type' value='CSAT'><div class='col-6'><input name='value' type='number' step='0.1' class='form-control form-control-sm' placeholder='CSAT %' required></div><div class='col-6'><input name='date' type='date' class='form-control form-control-sm' value='{datetime.now(PH_TZ).strftime('%Y-%m-%d')}'></div><div class='col-12'><input name='reason' class='form-control form-control-sm' placeholder='Feedback'></div><div class='col-12'><button class='btn w-100 mt-1' style='background:#06b6d4;color:white'>Add CSAT</button></div></form></div></div><div class='col-6'><div class='card-dark' style='border:1px solid #f59e0b'><h6 style='color:#f59e0b'>Add FCR</h6><form method='POST' action='/add_perf/{aid}' class='row g-2'><input type='hidden' name='type' value='FCR'><div class='col-6'><input name='value' type='number' step='0.1' class='form-control form-control-sm' placeholder='FCR %' required></div><div class='col-6'><input name='date' type='date' class='form-control form-control-sm' value='{datetime.now(PH_TZ).strftime('%Y-%m-%d')}'></div><div class='col-12'><input name='reason' class='form-control form-control-sm' placeholder='Notes'></div><div class='col-12'><button class='btn w-100 mt-1' style='background:#f59e0b;color:white'>Add FCR</button></div></form></div></div><div class='col-12'><div class='card-dark' style='border:1px solid #ef4444'><h6 style='color:#ef4444'>Add LOSS HOURS</h6><form method='POST' action='/add_ot/{aid}' class='row g-2'><input type='hidden' name='type' value='LOSS'><div class='col-4'><input name='hours' type='number' step='0.5' class='form-control form-control-sm' placeholder='Loss Hrs' required></div><div class='col-4'><input name='date' type='date' class='form-control form-control-sm' value='{datetime.now(PH_TZ).strftime('%Y-%m-%d')}'></div><div class='col-4'><select name='loss_type' class='form-select form-select-sm'><option>Late</option><option>Absent</option><option>Undertime</option><option>Emergency</option></select></div><div class='col-12'><input name='reason' class='form-control form-control-sm' placeholder='Reason'></div><div class='col-12'><button class='btn w-100 mt-1' style='background:#ef4444;color:white'>Add Loss</button></div></form></div></div></div>"
        html+=f"""
      <div class='mt-4'>
        <div class='d-flex justify-content-between align-items-center flex-wrap gap-2'>
          <h6 style='color:white;margin:0'>OT & Loss History - Previous Performance</h6>
          <input id='otSearch' class='form-control form-control-sm' placeholder='Search previous...' style='width:220px'>
        </div>
        <small style='color:#94a3b8'>Search tulad ng main dashboard</small>
        <div class='table-responsive mt-2'><table id='otTable' class='table table-sm'><thead><tr><th>Date</th><th>Type</th><th>Hrs</th><th>Reason</th><th></th></tr></thead><tbody>{log_rows}</tbody></table></div>
      </div>
      <div class='mt-3'>
        <div class='d-flex justify-content-between align-items-center flex-wrap gap-2'>
          <h6 style='color:white;margin:0'>QA/AHT/Attendance History - Previous</h6>
          <input id='perfSearch' class='form-control form-control-sm' placeholder='Search previous...' style='width:220px'>
        </div>
        <small style='color:#94a3b8'>Search previous performance</small>
        <div class='table-responsive mt-2'><table id='perfTable' class='table table-sm'><thead><tr><th>Date</th><th>Type</th><th>Value</th><th>Notes</th><th></th></tr></thead><tbody>{perf_rows}</tbody></table></div>
      </div>
      <script>
      document.addEventListener('DOMContentLoaded', function(){{
        var ot=document.getElementById('otSearch'); if(ot){{ot.addEventListener('keyup',function(){{var q=this.value.toLowerCase(); document.querySelectorAll('#otTable tbody tr').forEach(function(r){{r.style.display=r.innerText.toLowerCase().includes(q)?'':'none';}});}});}}
        var pf=document.getElementById('perfSearch'); if(pf){{pf.addEventListener('keyup',function(){{var q=this.value.toLowerCase(); document.querySelectorAll('#perfTable tbody tr').forEach(function(r){{r.style.display=r.innerText.toLowerCase().includes(q)?'':'none';}});}});}}
      }});
      </script>
      """
    else:
        html+=f"<div class='card-dark mt-3'><h6 style='color:#94a3b8'>View Only - Agent Mode</h6><small style='color:#64748b'>CSAT {lc}% | FCR {lf}% | Risk {risk}</small></div>"

    # --- Coaching Minutes integration (added) ---
    import coaching
    html += coaching.render_coaching_section(aid, is_agent)
    # --- end Coaching Minutes integration ---

    html+="</div>"
    return page(html)

@app.route("/set_target/<aid>", methods=["POST"])
@login_required
def set_target(aid):
    try:
        target=request.form.get("target","20")
        if db_root:
            db_root.child(f"agents/{aid}/TARGET_OT").set(str(float(target)))
    except Exception as e:
        print(f"set_target error: {e}")
    return redirect(f"/view/{aid}")

@app.route("/set_working_hours/<aid>", methods=["POST"])
@login_required
def set_working_hours(aid):
    try:
        wh=request.form.get("working_hours_target","220")
        if db_root:
            db_root.child(f"agents/{aid}/WORKING_HOURS_TARGET").set(str(float(wh)))
    except:
        pass
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
        loss_type=request.form.get("loss_type","")
        if loss_type:
            reason=f"{loss_type} - {reason}" if reason else loss_type
        if db_root:
            db_root.child("ot_logs").push({"agent_id":str(aid),"type":typ,"hours":str(hours),"date":date,"reason":reason})
    except Exception as e:
        print(f"add_ot error: {e}")
    return redirect(f"/view/{aid}")

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
    except Exception as e:
        print(f"add_perf error: {e}")
    return redirect(f"/view/{aid}")

@app.route("/delete_log/<aid>/<log_id>")
@login_required
def delete_log(aid, log_id):
    if session.get("role")=="agent":
        return redirect(f"/view/{aid}")
    try:
        if db_root:
            db_root.child(f"ot_logs/{log_id}").delete()
    except:
        pass
    return redirect(f"/view/{aid}")

@app.route("/delete_perf/<aid>/<log_id>")
@login_required
def delete_perf(aid, log_id):
    if session.get("role")=="agent":
        return redirect(f"/view/{aid}")
    try:
        if db_root:
            db_root.child(f"perf_logs/{log_id}").delete()
    except:
        pass
    return redirect(f"/view/{aid}")

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
                            msg="Current incorrect! Default Tencent ID"; color="#ef4444"
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
            try:
                db_root.child("login_logs").push({"user": session.get("user"),"name": session.get("name"),"role": "admin","type": f"RESET_PASSWORD to {new_pass}","timestamp": datetime.now(PH_TZ).strftime("%Y-%m-%d %I:%M:%S %p"),"date": datetime.now(PH_TZ).strftime("%Y-%m-%d"),"agent_id": aid})
            except: pass
    except:
        pass
    return redirect(f"/view/{aid}")

@app.route("/logs")
@login_required
def login_logs():
    if session.get("role")!="admin":
        return redirect("/")
    try:
        logs_raw = db_root.child("login_logs").get() if db_root else {}
        logs=[]
        if isinstance(logs_raw, dict):
            for lid, v in logs_raw.items():
                if isinstance(v, dict):
                    logs.append(v)
        logs_sorted=sorted(logs, key=lambda x: x.get("timestamp",""), reverse=True)
        search_q=request.args.get("q","").lower().strip()
        if search_q:
            logs_sorted=[l for l in logs_sorted if search_q in str(l.get("name","")).lower() or search_q in str(l.get("user","")).lower() or search_q in str(l.get("agent_id","")).lower()]
            display=logs_sorted[:50]
        else:
            display=logs_sorted[:20]
        rows=""
        for l in display:
            color="#22c55e" if l.get("type")=="LOGIN" else "#ef4444" if l.get("type")=="LOGOUT" else "#fbbf24"
            rows+=f"<tr><td style='color:#cbd5e1'>{l.get('timestamp','')}</td><td><b style='color:white'>{l.get('name','')}</b><br><small style='color:#94a3b8'>{l.get('user','')} | ID:{l.get('agent_id','')}</small></td><td><span class='badge' style='background:{color}'>{l.get('type')}</span></td><td>{l.get('role')}</td><td>{l.get('agent_id','')}</td></tr>"
        if not rows:
            rows="<tr><td colspan=5 style='text-align:center;color:#64748b'>No logs</td></tr>"
        html=f"""
        <div class='d-flex justify-content-between flex-wrap gap-2'><h5 style='color:white'>Login Logs - Last 20</h5><div class='d-flex gap-2'><form method='GET' class='d-flex gap-2'><input name='q' value='{request.args.get('q','')}' class='form-control form-control-sm' placeholder='Search agent...' style='width:200px'><button class='btn btn-sm btn-warning'>Search</button></form><a href='/logs' class='btn btn-sm btn-outline-light'>Reset</a><a href='/' class='btn btn-sm btn-outline-light'>Dashboard</a></div></div>
        <small style='color:#94a3b8'>Showing {len(display)} of {len(logs_sorted)} logs (20 default, 50 when searching)</small>
        <div class='card-dark mt-3'><div class='table-responsive'><table class='table table-sm'><thead><tr><th>Time</th><th>User</th><th>Type</th><th>Role</th><th>ID</th></tr></thead><tbody>{rows}</tbody></table></div></div>
        """
        return page(html)
    except:
        return page(f"<pre>{traceback.format_exc()}</pre>")

@app.route("/working_hours")
@login_required
def working_hours():
    if session.get("role")=="agent":
        return redirect(f"/view/{session.get('agent_id')}")
    agents=get_all()
    stats=[]
    for a in agents:
        logs=get_ot(a.get("id"))
        n,r,tot,loss,net=calc(logs)
        wh_target=float(a.get("WORKING_HOURS_TARGET",220))
        actual=wh_target-loss
        comp=(actual/wh_target*100) if wh_target>0 else 0
        stats.append({"id":a.get("id"),"name":a.get("NAME",""),"tid":a.get("TENCENT_ID",""),"wh_target":wh_target,"loss":loss,"actual":actual,"comp":comp,"tot":tot})
    rows=""
    for s in sorted(stats, key=lambda x: x["comp"]):
        bar_color="#22c55e" if s["comp"]>=95 else "#fbbf24" if s["comp"]>=90 else "#ef4444"
        badge="<span class='badge bg-success'>Good</span>" if s["comp"]>=95 else "<span class='badge bg-warning text-dark'>Warning</span>" if s["comp"]>=90 else "<span class='badge bg-danger'>Critical</span>"
        rows+=f"<tr><td><a href='/view/{s['id']}' style='color:white'><b>{s['name']}</b><br><small style='color:#94a3b8'>{s['tid']}</small></a></td><td>{s['wh_target']}h</td><td style='color:#ef4444'>{s['loss']}h</td><td>{round(s['actual'],1)}h</td><td><div class='progress' style='height:10px;width:100px;background:#0f172a'><div class='progress-bar' style='width:{min(100,s['comp'])}%;background:{bar_color}'></div></div><small>{round(s['comp'],1)}%</small></td><td>{s['tot']}h</td><td>{badge}</td></tr>"
    html=f"<div class='d-flex justify-content-between'><h5 style='color:white'>Working Hours - 220h Target (10h x 22 days)</h5><a href='/' class='btn btn-sm btn-outline-light'>Dashboard</a></div><div class='card-dark mt-3'><div class='table-responsive'><table class='table table-sm'><thead><tr><th>AGENT</th><th>TARGET</th><th>LOSS</th><th>ACTUAL</th><th>COMPLIANCE</th><th>OT</th><th>STATUS</th></tr></thead><tbody>{rows}</tbody></table></div></div>"
    return page(html)

@app.route("/export")
@login_required
def export_page():
    return page("""
    <h5 style='color:var(--text)'>📊 Export - TL Team KPI - QA, AHT, ATTENDANCE + Excel + Light/Dark</h5>
    <div class='row g-3 mt-3'>
      <div class='col-12 col-md-6'><div class='card-dark' style='border:1px solid #22c55e'><h6 style='color:#22c55e'>Export CSV - Overall Team KPI</h6><a href='/export/csv' class='btn btn-success w-100'>📥 Download CSV</a></div></div>
      <div class='col-12 col-md-6'><div class='card-dark' style='border:1px solid #3b82f6'><h6 style='color:#3b82f6'>Export Excel - TL KPI QA AHT ATTENDANCE</h6><a href='/export/excel' class='btn btn-primary w-100'>📊 Download Excel</a></div></div>
      <div class='col-12'><div class='card-dark' style='border:1px solid #fbbf24'><h6 style='color:#fbbf24'>TL Overall Team KPI Summary - QA, AHT, ATTENDANCE Graphs</h6></div></div>
    </div>
    """)

@app.route("/export/csv")
@login_required
def export_csv():
    agents=get_all()
    output=io.StringIO()
    writer=csv.writer(output)
    writer.writerow(["ID","NAME","TENCENT_ID","TOTAL_OT","LOSS","NET","AHT","QA","CSAT","FCR","WH_TARGET","WH_COMP"])
    for a in agents:
        logs=get_ot(a.get("id"))
        n,r,tot,loss,net=calc(logs)
        plogs=get_perf(a.get("id"))
        la,lq,lc,lf,aa,qa,ac,af=calc_perf(plogs)
        wh_target=float(a.get("WORKING_HOURS_TARGET",220))
        wh_comp=((wh_target-loss)/wh_target*100) if wh_target>0 else 0
        writer.writerow([a.get("id"),a.get("NAME"),a.get("TENCENT_ID"),tot,loss,net,la,lq,lc,lf,wh_target,round(wh_comp,1)])
    return Response(output.getvalue(), mimetype="text/csv", headers={"Content-Disposition":"attachment;filename=team_shine_m9.csv"})


@app.route("/export/excel")
@login_required
def export_excel():
    try:
        import io
        agents=get_all()
        output=io.StringIO()
        try:
            from openpyxl import Workbook
            wb=Workbook()
            ws=wb.active
            ws.title="TL Team KPI - QA AHT ATTENDANCE"
            ws.append(["TEAM SHINE M9 - TL OVERALL KPI - QA, AHT, ATTENDANCE"])
            ws.append(["Generated", datetime.now(PH_TZ).strftime("%Y-%m-%d %I:%M %p")])
            ws.append([])
            ws.append(["METRIC", "VALUE", "UNIT", "DETAILS"])
            agent_stats=[]
            team_n=0; team_r=0; team_loss=0; team_tot=0
            for a in agents:
                logs=get_ot(a.get("id"))
                n,r,tot,loss,net=calc(logs)
                team_n+=n; team_r+=r; team_loss+=loss; team_tot+=tot
                plogs=get_perf(a.get("id"))
                la,lq,lc,lf,aa,qa,ac,af=calc_perf(plogs)
                agent_stats.append({"name":a.get("NAME",""),"tid":a.get("TENCENT_ID",""),"tot":tot,"loss":loss,"qa":lq,"aht":la,"csat":lc,"fcr":lf,"wh_target":float(a.get("WORKING_HOURS_TARGET",220))})
            team_qa=[a["qa"] for a in agent_stats if a["qa"]>0]
            team_aht=[a["aht"] for a in agent_stats if a["aht"]>0]
            team_csat=[a["csat"] for a in agent_stats if a["csat"]>0]
            team_fcr=[a["fcr"] for a in agent_stats if a["fcr"]>0]
            total_wh=sum([a["wh_target"] for a in agent_stats])
            total_actual=total_wh-team_loss
            overall_att=(total_actual/total_wh*100) if total_wh>0 else 0
            ws.append(["Team Avg QA", round(sum(team_qa)/len(team_qa),1) if team_qa else 0, "%", f"{len(team_qa)} agents"])
            ws.append(["Team Avg AHT", round(sum(team_aht)/len(team_aht),1) if team_aht else 0, "minutes", f"{len(team_aht)} agents"])
            ws.append(["Team Avg CSAT", round(sum(team_csat)/len(team_csat),1) if team_csat else 0, "%", f"{len(team_csat)} agents"])
            ws.append(["Team Avg FCR", round(sum(team_fcr)/len(team_fcr),1) if team_fcr else 0, "%", f"{len(team_fcr)} agents"])
            ws.append(["Team Attendance", round(overall_att,1), "%", f"{round(total_actual,1)}/{total_wh}h"])
            ws.append(["Total Normal OT", round(team_n,1), "h", ""])
            ws.append(["Total Restday OT", round(team_r,1), "h", ""])
            ws.append(["Total OT", round(team_tot,1), "h", ""])
            ws.append(["Total Loss", round(team_loss,1), "h", ""])
            ws.append(["Team Net", round(team_tot-team_loss,1), "h", ""])
            ws.append([])
            ws.append(["AGENT DETAIL - QA, AHT, ATTENDANCE KPI"])
            ws.append(["ID","NAME","TENCENT_ID","TOTAL_OT","LOSS","NET","AHT","QA","CSAT","FCR","WH_TARGET","WH_ACTUAL","WH_COMP%"])
            for a in agents:
                logs=get_ot(a.get("id"))
                n,r,tot,loss,net=calc(logs)
                plogs=get_perf(a.get("id"))
                la,lq,lc,lf,aa,qa,ac,af=calc_perf(plogs)
                wh_target=float(a.get("WORKING_HOURS_TARGET",220))
                wh_actual=wh_target-loss
                wh_comp=(wh_actual/wh_target*100) if wh_target>0 else 0
                ws.append([a.get("id"),a.get("NAME"),a.get("TENCENT_ID"),tot,loss,net,la,lq,lc,lf,wh_target,round(wh_actual,1),round(wh_comp,1)])
            ws2=wb.create_sheet("OT Logs")
            ws2.append(["Agent ID","Name","Tencent ID","Date","Type","Hours","Reason"])
            all_ot=get_all_ot()
            for l in all_ot:
                aname=""; tid=""
                for a in agents:
                    if str(a.get("id"))==str(l.get("agent_id")):
                        aname=a.get("NAME",""); tid=a.get("TENCENT_ID",""); break
                ws2.append([l.get("agent_id"),aname,tid,l.get("date"),l.get("type"),l.get("hours"),l.get("reason")])
            ws3=wb.create_sheet("QA AHT ATTENDANCE Logs")
            ws3.append(["Agent ID","Name","Tencent ID","Date","Type","Value","Reason"])
            all_perf=get_all_perf()
            for l in all_perf:
                aname=""; tid=""
                for a in agents:
                    if str(a.get("id"))==str(l.get("agent_id")):
                        aname=a.get("NAME",""); tid=a.get("TENCENT_ID",""); break
                ws3.append([l.get("agent_id"),aname,tid,l.get("date"),l.get("type"),l.get("value"),l.get("reason")])
            from io import BytesIO
            bio=BytesIO()
            wb.save(bio)
            bio.seek(0)
            return Response(bio.getvalue(), mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition":"attachment;filename=Team_Shine_M9_TL_KPI_QA_AHT_ATTENDANCE.xlsx"})
        except ImportError:
            output=io.StringIO()
            import csv
            writer=csv.writer(output)
            writer.writerow(["TEAM SHINE M9 - TL KPI - QA, AHT, ATTENDANCE"])
            writer.writerow(["Generated", datetime.now(PH_TZ).strftime("%Y-%m-%d %I:%M %p")])
            writer.writerow([])
            writer.writerow(["METRIC","VALUE"])
            agent_stats=[]
            team_n=0; team_r=0; team_loss=0; team_tot=0
            for a in agents:
                logs=get_ot(a.get("id"))
                n,r,tot,loss,net=calc(logs)
                team_n+=n; team_r+=r; team_loss+=loss; team_tot+=tot
                plogs=get_perf(a.get("id"))
                la,lq,lc,lf,aa,qa,ac,af=calc_perf(plogs)
                agent_stats.append({"qa":lq,"aht":la,"csat":lc,"fcr":lf,"wh_target":float(a.get("WORKING_HOURS_TARGET",220))})
            team_qa=[a["qa"] for a in agent_stats if a["qa"]>0]
            team_aht=[a["aht"] for a in agent_stats if a["aht"]>0]
            writer.writerow(["Team Avg QA", round(sum(team_qa)/len(team_qa),1) if team_qa else 0])
            writer.writerow(["Team Avg AHT", round(sum(team_aht)/len(team_aht),1) if team_aht else 0])
            writer.writerow(["Total OT", team_tot])
            writer.writerow(["Total Loss", team_loss])
            writer.writerow([])
            writer.writerow(["ID","NAME","TENCENT_ID","TOTAL_OT","LOSS","AHT","QA","WH_TARGET","WH_COMP"])
            for a in agents:
                logs=get_ot(a.get("id"))
                n,r,tot,loss,net=calc(logs)
                plogs=get_perf(a.get("id"))
                la,lq,lc,lf,aa,qa,ac,af=calc_perf(plogs)
                wh_target=float(a.get("WORKING_HOURS_TARGET",220))
                wh_comp=((wh_target-loss)/wh_target*100) if wh_target>0 else 0
                writer.writerow([a.get("id"),a.get("NAME"),a.get("TENCENT_ID"),tot,loss,la,lq,wh_target,round(wh_comp,1)])
            return Response(output.getvalue(), mimetype="text/csv", headers={"Content-Disposition":"attachment;filename=Team_Shine_M9_TL_KPI.csv"})
    except Exception as e:
        print(f"export_excel error: {e}")
        traceback.print_exc()
        return page(f"<div class='card-dark'><h6 style='color:#ef4444'>Export Error</h6><pre style='color:#fbbf24;font-size:10px'>{traceback.format_exc()}</pre><a href='/export' class='btn btn-sm btn-outline-light'>Back</a></div>")


if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",5000)))

@app.route("/export/pdf")
@login_required
def export_pdf():
    try:
        agents=get_all()
        ot_logs=get_all_ot()
        perf_logs=get_all_perf()
        anns=get_all_announcements()
        reads=get_announcement_reads()
        agent_stats=[]
        team_n=0; team_r=0; team_loss=0; team_tot=0
        for a in agents:
            logs=get_ot(a.get("id"))
            n,r,tot,loss,net=calc(logs)
            team_n+=n; team_r+=r; team_loss+=loss; team_tot+=tot
            plogs=get_perf(a.get("id"))
            la,lq,lc,lf,aa,qa,ac,af=calc_perf(plogs)
            wh_target=float(a.get("WORKING_HOURS_TARGET", 220))
            wh_actual=wh_target-loss
            wh_comp=(wh_actual/wh_target*100) if wh_target>0 else 0
            agent_stats.append({"name":a.get("NAME",""),"tid":a.get("TENCENT ID") or a.get("TENCENT_ID",""),"tot":tot,"loss":loss,"net":net,"aht":la,"qa":lq,"csat":lc,"fcr":lf,"wh_target":wh_target,"wh_actual":wh_actual,"wh_comp":wh_comp})
        team_qa=[a["qa"] for a in agent_stats if a["qa"]>0]
        team_aht=[a["aht"] for a in agent_stats if a["aht"]>0]
        total_wh=sum([a["wh_target"] for a in agent_stats])
        total_actual=total_wh-team_loss
        overall_att=(total_actual/total_wh*100) if total_wh>0 else 0
        avg_qa=round(sum(team_qa)/len(team_qa),1) if team_qa else 0
        avg_aht=round(sum(team_aht)/len(team_aht),1) if team_aht else 0
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.units import inch
            from reportlab.lib.colors import HexColor
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
            from reportlab.lib import colors
            from io import BytesIO
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt
            buffer=BytesIO()
            doc=SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=18)
            styles=getSampleStyleSheet()
            title_style=ParagraphStyle('CustomTitle', parent=styles['Heading1'], fontSize=16, spaceAfter=12, textColor=HexColor('#fbbf24'), alignment=1)
            heading_style=ParagraphStyle('CustomHeading', parent=styles['Heading2'], fontSize=12, spaceAfter=6)
            normal_style=styles['Normal']
            normal_style.fontSize=9
            story=[]
            story.append(Paragraph("TEAM SHINE M9 - Executive Report", title_style))
            story.append(Paragraph(f"Generated: {datetime.now(PH_TZ).strftime('%Y-%m-%d %I:%M %p')} | Agents: {len(agents)}", normal_style))
            story.append(Spacer(1, 12))
            story.append(Paragraph("Executive Summary", heading_style))
            summary_text=f"Total {len(agents)} agents. Total OT: {round(team_tot,1)}h. Loss: {round(team_loss,1)}h. Avg QA: {avg_qa}%. Avg AHT: {avg_aht}m. Attendance: {round(overall_att,1)}%. Announcements: {len(anns)} posted, {len(reads)} confirmations."
            story.append(Paragraph(summary_text, normal_style))
            story.append(Spacer(1, 12))
            story.append(Paragraph("TL Team KPI", heading_style))
            kpi_data=[["Metric","Value","Details"],["Team Avg QA",str(avg_qa)+"%",f"{len(team_qa)} agents"],["Team Avg AHT",str(avg_aht)+"m",f"{len(team_aht)} agents"],["Attendance",str(round(overall_att,1))+"%",f"{round(total_actual,1)}/{round(total_wh,1)}h"],["Total OT",str(round(team_tot,1))+"h",""],["Total Loss",str(round(team_loss,1))+"h",""]]
            t=Table(kpi_data, colWidths=[120, 80, 150])
            t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),HexColor('#fbbf24')),('GRID',(0,0),(-1,-1),1,colors.black),('FONTSIZE',(0,0),(-1,-1),8)]))
            story.append(t)
            story.append(Spacer(1, 12))
            try:
                from collections import defaultdict
                m_groups=defaultdict(list)
                for l in ot_logs:
                    dt=parse_date(l.get("date",""))
                    if dt:
                        m_groups[dt.month].append(l)
                months=list(range(1,13))
                normal_m=[]; restday_m=[]; total_m=[]; loss_m=[]
                for m in months:
                    n,r,tot,loss,net=calc(m_groups.get(m,[]))
                    normal_m.append(n); restday_m.append(r); total_m.append(tot); loss_m.append(loss)
                fig, axes=plt.subplots(2,2, figsize=(8,6))
                axes[0,0].plot(months, normal_m, color='#22c55e', marker='o')
                axes[0,0].set_title('Normal OT')
                axes[0,1].plot(months, restday_m, color='#3b82f6', marker='o')
                axes[0,1].set_title('Restday OT')
                axes[1,0].plot(months, total_m, color='#fbbf24', marker='o')
                axes[1,0].set_title('Total OT')
                axes[1,1].plot(months, loss_m, color='#ef4444', marker='o')
                axes[1,1].set_title('Loss')
                plt.tight_layout()
                img_buffer=BytesIO()
                plt.savefig(img_buffer, format='png', dpi=150)
                plt.close()
                img_buffer.seek(0)
                story.append(Image(img_buffer, width=450, height=300))
                story.append(Spacer(1, 12))
            except Exception as e:
                story.append(Paragraph(f"Graph error: {str(e)}", normal_style))
            story.append(PageBreak())
            story.append(Paragraph("Agent Detail", heading_style))
            agent_data=[["NAME","TENCENT_ID","OT","LOSS","QA","AHT","WH_COMP"]]
            for a in agent_stats[:20]:
                agent_data.append([a["name"][:12], a["tid"], str(a["tot"]), str(a["loss"]), str(a["qa"]), str(a["aht"]), str(round(a["wh_comp"],1))+"%"])
            t2=Table(agent_data, colWidths=[70, 50, 40, 40, 40, 40, 50])
            t2.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),HexColor('#151e32')),('TEXTCOLOR',(0,0),(-1,0),HexColor('#fbbf24')),('GRID',(0,0),(-1,-1),1,colors.black),('FONTSIZE',(0,0),(-1,-1),7)]))
            story.append(t2)
            doc.build(story)
            pdf=buffer.getvalue()
            buffer.close()
            return Response(pdf, mimetype="application/pdf", headers={"Content-Disposition":"attachment;filename=Team_Shine_M9_Executive_Report.pdf"})
        except ImportError as e:
            return page(f"<div class='card-dark'><h6 style='color:#ef4444'>Need reportlab matplotlib</h6><p>Error: {str(e)}</p><a href='/export' class='btn btn-sm btn-outline-light'>Back</a></div>")
    except Exception as e:
        traceback.print_exc()
        return page(f"<div class='card-dark'><h6>PDF Error</h6><pre>{traceback.format_exc()}</pre><a href='/export' class='btn btn-sm btn-outline-light'>Back</a></div>")

# --- Coaching Minutes integration (added) ---
# Loads coaching.py so its @app.route(...) decorators register on this app.
import coaching
# --- end Coaching Minutes integration ---




