
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

BASE_HEAD = """<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1">
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
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
<a href="/health" class="btn btn-sm btn-outline-success">OK</a>
<a href="/logs" class="btn btn-sm btn-outline-light">📋 Logs</a>
<a href="/working_hours" class="btn btn-sm btn-outline-light">⏱️ 220h</a>
<a href="/agents" class="btn btn-sm btn-outline-light">Agents</a> 
<a href="/change_password" class="btn btn-sm btn-outline-light">🔑</a>
<a href="/logout" class="btn btn-sm btn-outline-danger">Logout</a>
</div>
</div></nav><div class="container-fluid p-3" style="max-width:1200px;margin:auto">
"""

BASE_FOOT = "</div><footer style='text-align:center;padding:24px;color:#64748b;font-size:12px;border-top:1px solid #1e293b;margin-top:30px'><div>Developed By : <span style='color:#fbbf24;font-weight:700'>Moises Gamboa</span> | Computer Engineer</div></footer></body></html>"

def page(c):
    return BASE_HEAD + c + BASE_FOOT

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
    
    # Top 3
    top3=sorted(agent_stats, key=lambda x: x["tot"], reverse=True)[:3]
    html+="<div class='card-dark mt-3' style='border:1px solid #fbbf24'><h6 style='color:#fbbf24'>Top 3 OT Earners</h6><div class='d-flex justify-content-center gap-2 mt-2'>"
    for idx, a in enumerate(top3):
        medal="🥇" if idx==0 else "🥈" if idx==1 else "🥉"
        html+=f"<div style='background:#1e293b;padding:8px 12px;border-radius:10px;text-align:center'><div>{medal}</div><div style='color:white;font-size:12px'>{a['name'][:10]}</div><div style='color:#fbbf24'>{a['tot']}h</div></div>"
    html+="</div></div>"
    
    # Charts
    html+=f"""
    <div class="row g-3 mt-3">
      <div class="col-12 col-md-6"><div class="chart-card" style="border:1px solid #22c55e"><h6 style="color:#22c55e">Normal OT - {period}</h6><canvas id="chartNormal"></canvas></div></div>
      <div class="col-12 col-md-6"><div class="chart-card" style="border:1px solid #3b82f6"><h6 style="color:#3b82f6">Restday OT</h6><canvas id="chartRestday"></canvas></div></div>
      <div class="col-12 col-md-6"><div class="chart-card" style="border:1px solid #fbbf24"><h6 style="color:#fbbf24">Total OT</h6><canvas id="chartTotal"></canvas></div></div>
      <div class="col-12 col-md-6"><div class="chart-card" style="border:1px solid #ef4444"><h6 style="color:#ef4444">Loss Hrs</h6><canvas id="chartLoss"></canvas></div></div>
    </div>
    <script>
    const labels = {labels};
    const nd = {nd}; const rd = {rd}; const td = {td}; const ld = {ld};
    function makeChart(id, label, data, color){{
      new Chart(document.getElementById(id), {{type:'line', data:{{labels: labels, datasets:[{{label: label, data: data, borderColor: color, backgroundColor: color+'33', fill:true, tension:0.4}}]}}, options:{{responsive:true, plugins:{{legend:{{display:false}}}}, scales:{{y:{{beginAtZero:true}}}}}}}});
    }}
    makeChart('chartNormal','Normal',nd,'#22c55e'); makeChart('chartRestday','Restday',rd,'#3b82f6'); makeChart('chartTotal','Total',td,'#fbbf24'); makeChart('chartLoss','Loss',ld,'#ef4444');
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
    agents=get_all()
    filtered=[a for a in agents if q in str(a.get("NAME","")).lower() or q in str(a.get("TENCENT_ID","")).lower()] if q else agents
    rows=""
    for a in filtered:
        logs=get_ot(a.get("id"))
        n,r,tot,loss,net=calc(logs)
        rows+=f"<tr><td>{a.get('id')}</td><td><a href='/view/{a.get('id')}' style='color:white'><b>{a.get('NAME','')}</b><br><small style='color:#94a3b8'>{a.get('TENCENT_ID')}</small></a></td><td>{tot}h</td><td style='color:#ef4444'>{loss}h</td><td><a href='/view/{a.get('id')}' class='btn btn-sm btn-warning'>View</a></td></tr>"
    if not rows:
        rows="<tr><td colspan=5 style='text-align:center;color:#64748b'>No agents</td></tr>"
    return page(f"<div class='d-flex justify-content-between'><h5 style='color:white'>All Agents ({len(filtered)}/{len(agents)})</h5><div class='d-flex gap-2'><form method='GET' class='d-flex gap-2'><input name='q' value='{q}' class='form-control form-control-sm' placeholder='Search...' style='width:180px'><button class='btn btn-sm btn-warning'>Search</button></form><a href='/' class='btn btn-sm btn-outline-light'>Dashboard</a></div></div><div class='card-dark mt-3'><div class='table-responsive'><table class='table'><thead><tr><th>ID</th><th>AGENT</th><th>TOTAL</th><th>LOSS</th><th></th></tr></thead><tbody>{rows}</tbody></table></div></div>")

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
    html+=f"""<div class="row g-3 mt-3"><div class="col-12 col-md-6"><div class="chart-card"><h6 style="color:#fbbf24">OT Trend</h6><canvas id="indOT"></canvas></div></div><div class="col-12 col-md-6"><div class="chart-card"><h6 style="color:#8b5cf6">QA/CSAT/FCR/AHT</h6><canvas id="indQA"></canvas></div></div></div><script>new Chart(document.getElementById('indOT'), {{type:'line', data:{{labels:{ind_labels}, datasets:[{{label:'OT', data:{ind_tot}, borderColor:'#fbbf24', backgroundColor:'#fbbf2433', fill:true, tension:0.4}},{{label:'Loss', data:{ind_loss}, borderColor:'#ef4444'}}]}}, options:{{responsive:true}}}}); new Chart(document.getElementById('indQA'), {{type:'line', data:{{labels:{ind_labels}, datasets:[{{label:'QA', data:{ind_qa}, borderColor:'#8b5cf6'}},{{label:'CSAT', data:{ind_csat}, borderColor:'#06b6d4'}},{{label:'FCR', data:{ind_fcr}, borderColor:'#f59e0b'}},{{label:'AHT', data:{ind_aht}, borderColor:'#f97316'}}]}}, options:{{responsive:true}}}});</script>"""
    html+=f"""<div class="card-dark mt-3" style="border:1px solid #334155"><div class="row g-2"><div class="col-6"><h6 style="color:#fbbf24">Target OT</h6><form method="POST" action="/set_target/{aid}" class="row g-2"><div class="col-6"><input name="target" type="number" step="0.5" class="form-control form-control-sm" value="{target}"></div><div class="col-6"><button class="btn btn-sm btn-warning w-100">Update OT</button></div></form></div><div class="col-6"><h6 style="color:#22c55e">WH Target 220h</h6><form method="POST" action="/set_working_hours/{aid}" class="row g-2"><div class="col-6"><input name="working_hours_target" type="number" step="1" class="form-control form-control-sm" value="{wh_target}"></div><div class="col-6"><button class="btn btn-sm btn-success w-100">Update WH</button></div></form></div></div></div>"""
    if session.get("role")=="admin":
        current_pw=data.get("LOGIN_PASS") or data.get("TENCENT_ID") or "1234"
        html+=f"""<div class="card-dark mt-3" style="border:1px solid #ef4444"><h6 style="color:#ef4444">Password - No current needed</h6><p style="color:#94a3b8;font-size:11px">Current: <span style="color:#fbbf24">{current_pw}</span> | User: {data.get("TENCENT_ID")}</p><form method="POST" action="/reset_password/{aid}" class="row g-2"><div class="col-6"><input name="new_pass" type="text" class="form-control form-control-sm" placeholder="Blank = reset to Tencent ID"></div><div class="col-6"><button class="btn btn-sm btn-danger w-100">Reset / Set Password</button></div></form></div>"""
    elif is_agent:
        html+=f"""<div class="card-dark mt-3" style="border:1px solid #fbbf24"><h6 style="color:#fbbf24">My Account</h6><a href="/change_password" class="btn btn-sm btn-warning w-100">Change Password</a></div>"""
    if not is_agent:
        html+=f"<div class='row g-2 mt-4'><div class='col-6'><div class='card-dark' style='border:1px solid #22c55e'><h6 style='color:#22c55e'>Add NORMAL OT</h6><form method='POST' action='/add_ot/{aid}' class='row g-2'><input type='hidden' name='type' value='NORMAL_OT'><div class='col-6'><input name='hours' type='number' step='0.5' class='form-control form-control-sm' placeholder='Hours' required></div><div class='col-6'><input name='date' type='date' class='form-control form-control-sm' value='{datetime.now(PH_TZ).strftime('%Y-%m-%d')}'></div><div class='col-12'><input name='reason' class='form-control form-control-sm' placeholder='Reason'></div><div class='col-12'><button class='btn w-100 mt-1' style='background:#22c55e;color:white'>Add Normal OT</button></div></form></div></div><div class='col-6'><div class='card-dark' style='border:1px solid #3b82f6'><h6 style='color:#3b82f6'>Add RESTDAY OT</h6><form method='POST' action='/add_ot/{aid}' class='row g-2'><input type='hidden' name='type' value='RESTDAY_OT'><div class='col-6'><input name='hours' type='number' step='0.5' class='form-control form-control-sm' placeholder='Hours' required></div><div class='col-6'><input name='date' type='date' class='form-control form-control-sm' value='{datetime.now(PH_TZ).strftime('%Y-%m-%d')}'></div><div class='col-12'><input name='reason' class='form-control form-control-sm' placeholder='Reason'></div><div class='col-12'><button class='btn w-100 mt-1' style='background:#3b82f6;color:white'>Add Restday</button></div></form></div></div><div class='col-6'><div class='card-dark' style='border:1px solid #f97316'><h6 style='color:#f97316'>Add AHT</h6><form method='POST' action='/add_perf/{aid}' class='row g-2'><input type='hidden' name='type' value='AHT'><div class='col-6'><input name='value' type='number' step='0.1' class='form-control form-control-sm' placeholder='Minutes' required></div><div class='col-6'><input name='date' type='date' class='form-control form-control-sm' value='{datetime.now(PH_TZ).strftime('%Y-%m-%d')}'></div><div class='col-12'><input name='reason' class='form-control form-control-sm' placeholder='Notes'></div><div class='col-12'><button class='btn w-100 mt-1' style='background:#f97316;color:white'>Add AHT</button></div></form></div></div><div class='col-6'><div class='card-dark' style='border:1px solid #8b5cf6'><h6 style='color:#8b5cf6'>Add QA</h6><form method='POST' action='/add_perf/{aid}' class='row g-2'><input type='hidden' name='type' value='QA'><div class='col-6'><input name='value' type='number' step='0.1' class='form-control form-control-sm' placeholder='%' required></div><div class='col-6'><input name='date' type='date' class='form-control form-control-sm' value='{datetime.now(PH_TZ).strftime('%Y-%m-%d')}'></div><div class='col-12'><input name='reason' class='form-control form-control-sm' placeholder='QA notes'></div><div class='col-12'><button class='btn w-100 mt-1' style='background:#8b5cf6;color:white'>Add QA</button></div></form></div></div><div class='col-6'><div class='card-dark' style='border:1px solid #06b6d4'><h6 style='color:#06b6d4'>Add CSAT</h6><form method='POST' action='/add_perf/{aid}' class='row g-2'><input type='hidden' name='type' value='CSAT'><div class='col-6'><input name='value' type='number' step='0.1' class='form-control form-control-sm' placeholder='CSAT %' required></div><div class='col-6'><input name='date' type='date' class='form-control form-control-sm' value='{datetime.now(PH_TZ).strftime('%Y-%m-%d')}'></div><div class='col-12'><input name='reason' class='form-control form-control-sm' placeholder='Feedback'></div><div class='col-12'><button class='btn w-100 mt-1' style='background:#06b6d4;color:white'>Add CSAT</button></div></form></div></div><div class='col-6'><div class='card-dark' style='border:1px solid #f59e0b'><h6 style='color:#f59e0b'>Add FCR</h6><form method='POST' action='/add_perf/{aid}' class='row g-2'><input type='hidden' name='type' value='FCR'><div class='col-6'><input name='value' type='number' step='0.1' class='form-control form-control-sm' placeholder='FCR %' required></div><div class='col-6'><input name='date' type='date' class='form-control form-control-sm' value='{datetime.now(PH_TZ).strftime('%Y-%m-%d')}'></div><div class='col-12'><input name='reason' class='form-control form-control-sm' placeholder='Notes'></div><div class='col-12'><button class='btn w-100 mt-1' style='background:#f59e0b;color:white'>Add FCR</button></div></form></div></div><div class='col-12'><div class='card-dark' style='border:1px solid #ef4444'><h6 style='color:#ef4444'>Add LOSS HOURS</h6><form method='POST' action='/add_ot/{aid}' class='row g-2'><input type='hidden' name='type' value='LOSS'><div class='col-4'><input name='hours' type='number' step='0.5' class='form-control form-control-sm' placeholder='Loss Hrs' required></div><div class='col-4'><input name='date' type='date' class='form-control form-control-sm' value='{datetime.now(PH_TZ).strftime('%Y-%m-%d')}'></div><div class='col-4'><select name='loss_type' class='form-select form-select-sm'><option>Late</option><option>Absent</option><option>Undertime</option><option>Emergency</option></select></div><div class='col-12'><input name='reason' class='form-control form-control-sm' placeholder='Reason'></div><div class='col-12'><button class='btn w-100 mt-1' style='background:#ef4444;color:white'>Add Loss</button></div></form></div></div></div>"
        html+=f"<div class='mt-4'><h6 style='color:white'>OT & Loss History</h6><div class='table-responsive'><table class='table table-sm'><thead><tr><th>Date</th><th>Type</th><th>Hrs</th><th>Reason</th><th></th></tr></thead><tbody>{log_rows}</tbody></table></div></div><div class='mt-3'><h6 style='color:white'>AHT/QA/CSAT/FCR History</h6><div class='table-responsive'><table class='table table-sm'><thead><tr><th>Date</th><th>Type</th><th>Value</th><th>Notes</th><th></th></tr></thead><tbody>{perf_rows}</tbody></table></div></div>"
    else:
        html+=f"<div class='card-dark mt-3'><h6 style='color:#94a3b8'>View Only - Agent Mode</h6><small style='color:#64748b'>CSAT {lc}% | FCR {lf}% | Risk {risk}</small></div>"
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
    return page("<h5 style='color:white'>Export</h5><div class='card-dark mt-3'><a href='/export/csv' class='btn btn-success w-100'>Download CSV</a></div>")

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

if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",5000)))
