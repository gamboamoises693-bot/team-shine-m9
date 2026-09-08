
import os, json
from flask import Flask, request, redirect, session, jsonify
from functools import wraps
from datetime import datetime, timezone, timedelta
from collections import defaultdict
import calendar

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "team-shine-m9-secret-2024-secure")
TEAM_USER = os.environ.get("TEAM_USER", "admin")
TEAM_PASS = os.environ.get("TEAM_PASS", "shine2024")
PH_TZ = timezone(timedelta(hours=8))

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
    result=[]
    if isinstance(logs, dict):
        for lid, v in logs.items():
            if isinstance(v, dict):
                result.append(v)
    return result

def get_all_perf_logs():
    logs = db_root.child("perf_logs").get() if db_root else {}
    result=[]
    if isinstance(logs, dict):
        for lid, v in logs.items():
            if isinstance(v, dict):
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
body{background:#0b1120;color:#f1f5f9;font-family:Inter,system-ui}
.card-dark{background:#151e32;border:1px solid #2d3748;border-radius:20px;padding:16px;box-shadow:0 4px 12px rgba(0,0,0,0.3)}
.kpi{padding:12px 8px;border-radius:16px;background:#151e32;border:1px solid #2d3748;text-align:center;min-height:110px;height:110px;display:flex;flex-direction:column;justify-content:center;align-items:center}
.label{font-size:9px;color:#94a3b8;text-transform:uppercase;letter-spacing:.6px;font-weight:600;line-height:11px;min-height:22px;display:flex;align-items:center;justify-content:center}
.val-big{font-size:22px;font-weight:800;margin-top:2px;line-height:24px}
.chart-card{background:#151e32;border:1px solid #2d3748;border-radius:20px;padding:16px}
.table thead th{background:#0f172a!important;color:#fbbf24!important;font-size:10px;text-transform:uppercase;letter-spacing:.5px;border:none!important}
.table tbody td{background:#151e32!important;border-color:#1e293b!important;color:#e2e8f0!important;padding:12px 8px}
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
  <div style="font-size:10px;margin-top:4px">TEAM SHINE M9 - OT + LOSS + AHT + QA System</div>
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

def parse_date(dstr):
    try:
        return datetime.strptime(dstr, "%Y-%m-%d")
    except:
        return None

def get_filtered_stats(period, year, month, quarter, week):
    ot_logs=get_all_ot_logs()
    perf_logs=get_all_perf_logs()
    # Filter by year if provided
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
            # ISO week
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

    # Aggregate
    labels=[]
    normal_data=[]
    restday_data=[]
    total_data=[]
    loss_data=[]
    net_data=[]
    aht_data=[]
    qa_data=[]

    if period=="daily":
        # Last 14 days or selected month days
        groups=defaultdict(list)
        for l in filtered_ot:
            groups[l.get("date")].append(l)
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
        # AHT QA per day
        pgroups=defaultdict(list)
        for l in filtered_perf:
            pgroups[l.get("date")].append(l)
        for d in sorted_dates:
            pl=pgroups.get(d,[])
            _,_,aa,qa,_,_=calc_perf(pl)
            aht_data.append(round(aa,1))
            qa_data.append(round(qa,1))
    elif period=="weekly":
        # Group by week or by day within week
        if week:
            # Show daily within that week
            groups=defaultdict(list)
            for l in filtered_ot:
                groups[l.get("date")].append(l)
            sorted_dates=sorted(groups.keys())
            for d in sorted_dates:
                logs=groups[d]
                n,r,tot,loss,net=calc(logs)
                labels.append(d[-5:])
                normal_data.append(n); restday_data.append(r); total_data.append(tot); loss_data.append(loss); net_data.append(net)
            pgroups=defaultdict(list)
            for l in filtered_perf:
                pgroups[l.get("date")].append(l)
            for d in sorted_dates:
                pl=pgroups.get(d,[])
                _,_,aa,qa,_,_=calc_perf(pl)
                aht_data.append(round(aa,1)); qa_data.append(round(qa,1))
        else:
            # Weekly aggregation
            wgroups=defaultdict(list)
            pwgroups=defaultdict(list)
            for l in filtered_ot:
                dt=parse_date(l.get("date"))
                if not dt: continue
                key=f"{dt.year}-W{dt.isocalendar()[1]:02d}"
                wgroups[key].append(l)
            for l in filtered_perf:
                dt=parse_date(l.get("date"))
                if not dt: continue
                key=f"{dt.year}-W{dt.isocalendar()[1]:02d}"
                pwgroups[key].append(l)
            sorted_keys=sorted(wgroups.keys())[-12:]
            for k in sorted_keys:
                logs=wgroups[k]
                n,r,tot,loss,net=calc(logs)
                labels.append(k)
                normal_data.append(n); restday_data.append(r); total_data.append(tot); loss_data.append(loss); net_data.append(net)
                pl=pwgroups.get(k,[])
                _,_,aa,qa,_,_=calc_perf(pl)
                aht_data.append(round(aa,1)); qa_data.append(round(qa,1))
    elif period=="monthly":
        if month:
            # Daily within month
            groups=defaultdict(list)
            for l in filtered_ot:
                groups[l.get("date")].append(l)
            sorted_dates=sorted(groups.keys())
            for d in sorted_dates:
                logs=groups[d]
                n,r,tot,loss,net=calc(logs)
                labels.append(d[-2:])
                normal_data.append(n); restday_data.append(r); total_data.append(tot); loss_data.append(loss); net_data.append(net)
            pgroups=defaultdict(list)
            for l in filtered_perf:
                pgroups[l.get("date")].append(l)
            for d in sorted_dates:
                pl=pgroups.get(d,[])
                _,_,aa,qa,_,_=calc_perf(pl)
                aht_data.append(round(aa,1)); qa_data.append(round(qa,1))
        else:
            # Monthly for year
            mgroups=defaultdict(list)
            pmgroups=defaultdict(list)
            for l in filtered_ot:
                dt=parse_date(l.get("date"))
                if not dt: continue
                key=dt.month
                mgroups[key].append(l)
            for l in filtered_perf:
                dt=parse_date(l.get("date"))
                if not dt: continue
                key=dt.month
                pmgroups[key].append(l)
            for m in range(1,13):
                labels.append(calendar.month_abbr[m])
                logs=mgroups.get(m,[])
                n,r,tot,loss,net=calc(logs)
                normal_data.append(n); restday_data.append(r); total_data.append(tot); loss_data.append(loss); net_data.append(net)
                pl=pmgroups.get(m,[])
                _,_,aa,qa,_,_=calc_perf(pl)
                aht_data.append(round(aa,1)); qa_data.append(round(qa,1))
    elif period=="quarterly":
        if quarter:
            # Monthly within quarter
            months=range((int(quarter)-1)*3+1, int(quarter)*3+1)
            mgroups=defaultdict(list)
            pmgroups=defaultdict(list)
            for l in filtered_ot:
                dt=parse_date(l.get("date"))
                if not dt: continue
                if dt.month in months:
                    mgroups[dt.month].append(l)
            for l in filtered_perf:
                dt=parse_date(l.get("date"))
                if not dt: continue
                if dt.month in months:
                    pmgroups[dt.month].append(l)
            for m in months:
                labels.append(calendar.month_abbr[m])
                logs=mgroups.get(m,[])
                n,r,tot,loss,net=calc(logs)
                normal_data.append(n); restday_data.append(r); total_data.append(tot); loss_data.append(loss); net_data.append(net)
                pl=pmgroups.get(m,[])
                _,_,aa,qa,_,_=calc_perf(pl)
                aht_data.append(round(aa,1)); qa_data.append(round(qa,1))
        else:
            for q in range(1,5):
                labels.append(f"Q{q}")
                logs=[]
                for l in filtered_ot:
                    dt=parse_date(l.get("date"))
                    if not dt: continue
                    if (dt.month-1)//3+1==q:
                        logs.append(l)
                n,r,tot,loss,net=calc(logs)
                normal_data.append(n); restday_data.append(r); total_data.append(tot); loss_data.append(loss); net_data.append(net)
                pl=[]
                for l in filtered_perf:
                    dt=parse_date(l.get("date"))
                    if not dt: continue
                    if (dt.month-1)//3+1==q:
                        pl.append(l)
                _,_,aa,qa,_,_=calc_perf(pl)
                aht_data.append(round(aa,1)); qa_data.append(round(qa,1))
    else: # yearly
        ygroups=defaultdict(list)
        pygroups=defaultdict(list)
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
            labels.append(str(y))
            logs=ygroups.get(y,[])
            n,r,tot,loss,net=calc(logs)
            normal_data.append(n); restday_data.append(r); total_data.append(tot); loss_data.append(loss); net_data.append(net)
            pl=pygroups.get(y,[])
            _,_,aa,qa,_,_=calc_perf(pl)
            aht_data.append(round(aa,1)); qa_data.append(round(qa,1))
        if not labels:
            # If no data, show months of selected year
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
        agent_stats.append({"id":a.get("id"),"name":a.get("NAME",""),"tid":a.get("TENCENT_ID",""),"n":n,"r":r,"tot":tot,"loss":loss,"net":net,"aht":la,"qa":lq,"avg_aht":aa,"avg_qa":qa})
    agent_stats_sorted=sorted(agent_stats, key=lambda x: x["tot"], reverse=True)
    avg_ot=team_total/len(agents) if agents else 0
    avg_net=team_net/len(agents) if agents else 0
    
    labels, nd, rd, td, ld, netd, ahtd, qad = get_filtered_stats(period, year, month, quarter, week)

    # Team AHT QA avg
    team_aht_vals=[a["avg_aht"] for a in agent_stats if a["avg_aht"]>0]
    team_qa_vals=[a["avg_qa"] for a in agent_stats if a["avg_qa"]>0]
    team_avg_aht = sum(team_aht_vals)/len(team_aht_vals) if team_aht_vals else 0
    team_avg_qa = sum(team_qa_vals)/len(team_qa_vals) if team_qa_vals else 0

    # Filter UI
    filter_html = f"""
    <div class="card-dark mb-3" style="border:1px solid #fbbf24">
      <h6 style="color:#fbbf24"><i class="bi bi-funnel-fill"></i> Graph Filters - Per KPI</h6>
      <form method="GET" class="row g-2 mt-2">
        <div class="col-6 col-md-2">
          <label class="label">PERIOD</label>
          <select name="period" class="form-select form-select-sm" onchange="this.form.submit()">
            <option value="daily" {"selected" if period=="daily" else ""}>Daily</option>
            <option value="weekly" {"selected" if period=="weekly" else ""}>Weekly</option>
            <option value="monthly" {"selected" if period=="monthly" else ""}>Monthly</option>
            <option value="quarterly" {"selected" if period=="quarterly" else ""}>Quarterly</option>
            <option value="yearly" {"selected" if period=="yearly" else ""}>Yearly</option>
          </select>
        </div>
        <div class="col-6 col-md-2">
          <label class="label">YEAR</label>
          <select name="year" class="form-select form-select-sm" onchange="this.form.submit()">
            <option value="2024" {"selected" if year=="2024" else ""}>2024</option>
            <option value="2025" {"selected" if year=="2025" else ""}>2025</option>
            <option value="2026" {"selected" if year=="2026" else ""}>2026</option>
          </select>
        </div>
        <div class="col-6 col-md-2" style="display:{"block" if period=="monthly" else "none"}">
          <label class="label">MONTH</label>
          <select name="month" class="form-select form-select-sm" onchange="this.form.submit()">
            <option value="">All Months</option>
            {"".join([f'<option value="{m}" {"selected" if str(m)==month else ""}>{calendar.month_name[m]}</option>' for m in range(1,13)])}
          </select>
        </div>
        <div class="col-6 col-md-2" style="display:{"block" if period=="quarterly" else "none"}">
          <label class="label">QUARTER</label>
          <select name="quarter" class="form-select form-select-sm" onchange="this.form.submit()">
            <option value="">All Quarters</option>
            <option value="1" {"selected" if quarter=="1" else ""}>Q1 (Jan-Mar)</option>
            <option value="2" {"selected" if quarter=="2" else ""}>Q2 (Apr-Jun)</option>
            <option value="3" {"selected" if quarter=="3" else ""}>Q3 (Jul-Sep)</option>
            <option value="4" {"selected" if quarter=="4" else ""}>Q4 (Oct-Dec)</option>
          </select>
        </div>
        <div class="col-6 col-md-2" style="display:{"block" if period=="weekly" else "none"}">
          <label class="label">WEEK #</label>
          <select name="week" class="form-select form-select-sm" onchange="this.form.submit()">
            <option value="">All Weeks</option>
            {"".join([f'<option value="{w}" {"selected" if str(w)==week else ""}>Week {w}</option>' for w in range(1,53)])}
          </select>
        </div>
        <div class="col-6 col-md-2 d-flex align-items-end">
          <a href="/" class="btn btn-sm btn-outline-light w-100">Reset</a>
        </div>
      </form>
      <small style="color:#94a3b8" class="mt-2 d-block">Current: {period.upper()} | Year: {year} {f"| Month: {calendar.month_name[int(month)]}" if month else ""} {f"| {quarter} " if quarter else ""} | PH Time: {datetime.now(PH_TZ).strftime("%b %d, %Y %I:%M %p")}</small>
    </div>
    """

    html=filter_html
    html+=f"<div class='d-flex justify-content-between align-items-center mb-3'><h5 style='color:white'><i class='bi bi-speedometer2' style='color:#fbbf24'></i> Team Performance Overview</h5></div>"
    html+="<div class='row g-2'>"
    html+=f"<div class='col-6 col-md-2'><div class='kpi' style='border:1px solid #22c55e'><div class='label'>TEAM NORMAL OT</div><div class='val-big' style='color:#22c55e'>{round(team_normal,1)}h</div></div></div>"
    html+=f"<div class='col-6 col-md-2'><div class='kpi' style='border:1px solid #3b82f6'><div class='label'>TEAM RESTDAY OT</div><div class='val-big' style='color:#3b82f6'>{round(team_restday,1)}h</div></div></div>"
    html+=f"<div class='col-6 col-md-2'><div class='kpi' style='border:1px solid #fbbf24'><div class='label'>TEAM TOTAL OT</div><div class='val-big' style='color:#fbbf24'>{round(team_total,1)}h</div></div></div>"
    html+=f"<div class='col-6 col-md-2'><div class='kpi' style='border:1px solid #ef4444'><div class='label'>TEAM LOSS HRS</div><div class='val-big' style='color:#ef4444'>{round(team_loss,1)}h</div></div></div>"
    html+=f"<div class='col-6 col-md-2'><div class='kpi' style='border:1px solid #a855f7'><div class='label'>TEAM NET</div><div class='val-big' style='color:#a855f7'>+{round(team_net,1)}h</div></div></div>"
    html+=f"<div class='col-6 col-md-2'><div class='kpi' style='border:1px solid #06b6d4'><div class='label'>AVG OT / AGENT</div><div class='val-big' style='color:#06b6d4'>{round(avg_ot,1)}h</div></div></div>"
    html+="</div>"
    html+=f"<div class='row g-2 mt-2'><div class='col-6'><div class='kpi' style='border:1px solid #f97316;min-height:90px;height:90px'><div class='label'>TEAM AVG AHT</div><div class='val-big' style='color:#f97316'>{round(team_avg_aht,1)}m</div></div></div><div class='col-6'><div class='kpi' style='border:1px solid #8b5cf6;min-height:90px;height:90px'><div class='label'>TEAM AVG QA</div><div class='val-big' style='color:#8b5cf6'>{round(team_avg_qa,1)}%</div></div></div></div>"

    # Graphs
    html+=f"""
    <div class="row g-3 mt-3">
      <div class="col-12 col-md-6"><div class="chart-card" style="border:1px solid #22c55e"><h6 style="color:#22c55e">NORMAL OT Trend - {period}</h6><canvas id="chartNormal"></canvas></div></div>
      <div class="col-12 col-md-6"><div class="chart-card" style="border:1px solid #3b82f6"><h6 style="color:#3b82f6">RESTDAY OT Trend - {period}</h6><canvas id="chartRestday"></canvas></div></div>
      <div class="col-12 col-md-6"><div class="chart-card" style="border:1px solid #fbbf24"><h6 style="color:#fbbf24">TOTAL OT Trend - {period}</h6><canvas id="chartTotal"></canvas></div></div>
      <div class="col-12 col-md-6"><div class="chart-card" style="border:1px solid #ef4444"><h6 style="color:#ef4444">LOSS HRS Trend - {period}</h6><canvas id="chartLoss"></canvas></div></div>
      <div class="col-12 col-md-4"><div class="chart-card" style="border:1px solid #a855f7"><h6 style="color:#a855f7">NET OT Trend</h6><canvas id="chartNet"></canvas></div></div>
      <div class="col-12 col-md-4"><div class="chart-card" style="border:1px solid #f97316"><h6 style="color:#f97316">AHT Trend</h6><canvas id="chartAht"></canvas></div></div>
      <div class="col-12 col-md-4"><div class="chart-card" style="border:1px solid #8b5cf6"><h6 style="color:#8b5cf6">QA SCORE Trend</h6><canvas id="chartQa"></canvas></div></div>
    </div>
    <script>
    const labels = {labels};
    const normalData = {nd};
    const restdayData = {rd};
    const totalData = {td};
    const lossData = {ld};
    const netData = {netd};
    const ahtData = {ahtd};
    const qaData = {qad};
    function makeChart(id, label, data, color){{
      new Chart(document.getElementById(id), {{
        type: 'line',
        data: {{ labels: labels, datasets: [{{ label: label, data: data, borderColor: color, backgroundColor: color+'33', fill: true, tension: 0.4 }}] }},
        options: {{ responsive: true, plugins: {{ legend: {{ display: false }} }}, scales: {{ y: {{ beginAtZero: true, grid: {{ color: '#1e293b' }} }}, x: {{ grid: {{ color: '#1e293b' }} }} }} }}
      }});
    }}
    makeChart('chartNormal','Normal OT',normalData,'#22c55e');
    makeChart('chartRestday','Restday OT',restdayData,'#3b82f6');
    makeChart('chartTotal','Total OT',totalData,'#fbbf24');
    makeChart('chartLoss','Loss Hrs',lossData,'#ef4444');
    makeChart('chartNet','Net OT',netData,'#a855f7');
    makeChart('chartAht','AHT',ahtData,'#f97316');
    makeChart('chartQa','QA Score',qaData,'#8b5cf6');
    </script>
    """

    # Table
    html+="<div class='card-dark mt-3' style='border:1px solid #334155'><div class='d-flex justify-content-between align-items-center'><h6 style='color:white'><i class='bi bi-people-fill' style='color:#fbbf24'></i> Full Team - Critical KPIs</h6><div class='d-flex gap-2'><input id='teamSearch' class='form-control form-control-sm' placeholder='Quick search...' style='width:160px'><a href='/agents' class='btn btn-sm btn-warning'>View All</a></div></div><div class='table-responsive mt-3'><table id='teamTable' class='table table-sm'><thead><tr><th>AGENT</th><th>NORMAL</th><th>RESTDAY</th><th>TOTAL</th><th>LOSS</th><th>NET</th><th>AHT</th><th>QA</th><th>STATUS</th></tr></thead><tbody>"
    for a in agent_stats_sorted:
        st = "<span class='badge bg-danger'>Critical</span>" if a['loss']>=4 else "<span class='badge bg-warning text-dark'>Warning</span>" if a['loss']>0 else "<span class='badge bg-success'>Good</span>"
        html+=f"<tr><td><a href='/view/{a['id']}' style='color:white;text-decoration:none'><b>{a['name']}</b><br><small style='color:#94a3b8'>{a['tid']}</small></a></td><td style='color:#22c55e'>{a['n']}h</td><td style='color:#3b82f6'>{a['r']}h</td><td style='color:#fbbf24'>{a['tot']}h</td><td style='color:#ef4444'>{a['loss']}h</td><td style='color:#a855f7'>+{a['net']}h</td><td>{a['aht']}m</td><td>{a['qa']}%</td><td>{st}</td></tr>"
    html+="</tbody></table></div></div><script>document.addEventListener('DOMContentLoaded',function(){var i=document.getElementById('teamSearch');if(!i)return;i.addEventListener('keyup',function(){var q=this.value.toLowerCase();document.querySelectorAll('#teamTable tbody tr').forEach(function(r){r.style.display=r.innerText.toLowerCase().includes(q)?'':'none';});});});</script>"

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
        plogs=get_perf(a.get("id"))
        la,lq,_,_,_,_=calc_perf(plogs)
        rows+=f"<tr><td>{a.get('id')}</td><td><a href='/view/{a.get('id')}' style='color:white;text-decoration:none'><b>{a.get('NAME','')}</b><br><small style='color:#94a3b8'>{a.get('TENCENT_ID','')} NET:{net}h</small></a></td><td style='color:#22c55e'>{n}h</td><td style='color:#3b82f6'>{r}h</td><td style='color:#ef4444'>{loss}h</td><td><a href='/view/{a.get('id')}' class='btn btn-sm btn-warning'>View</a></td></tr>"
    if not rows:
        rows="<tr><td colspan=6 style='text-align:center;color:#64748b;padding:20px'>No agents found</td></tr>"
    top = f"<div class='d-flex justify-content-between align-items-center flex-wrap gap-2'><h5 style='color:white;margin:0'>All Agents ({len(filtered)}/{len(agents)})</h5><div class='d-flex gap-2'><form method='GET' class='d-flex gap-2'><input name='q' value='{q}' class='form-control form-control-sm' placeholder='Search name...' style='width:220px'><button class='btn btn-sm btn-warning'>Search</button></form><a href='/' class='btn btn-sm btn-outline-light'>Dashboard</a></div></div>"
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
    html=f"<a href='/' class='btn btn-sm btn-outline-light mb-3'>Back Dashboard</a><div class='card-dark' style='border:1px solid #334155'><div class='text-center'><div style='width:90px;height:90px;background:linear-gradient(135deg,#fbbf24,#f59e0b);border-radius:18px;display:flex;align-items:center;justify-content:center;font-size:40px;font-weight:900;color:#111827;margin:auto'>{initial}</div><h4 style='color:white;margin-top:12px'>{data.get('NAME','')}</h4><small style='color:#94a3b8'>{data.get('TENCENT_ID','')}</small></div>"
    html+=f"<div class='row g-2 mt-3'><div class='col-4'><div class='kpi' style='border:1px solid #22c55e'><div class='label'>NORMAL OT</div><div class='val-big' style='color:#22c55e'>{n}h</div></div></div><div class='col-4'><div class='kpi' style='border:1px solid #3b82f6'><div class='label'>RESTDAY OT</div><div class='val-big' style='color:#3b82f6'>{r}h</div></div></div><div class='col-4'><div class='kpi' style='border:1px solid #ef4444'><div class='label'>LOSS HRS</div><div class='val-big' style='color:#ef4444'>{loss}h</div></div></div><div class='col-6'><div class='kpi' style='border:1px solid #22c55e'><div class='label'>TOTAL OT</div><div class='val-big' style='color:#22c55e'>{tot}h</div></div></div><div class='col-6'><div class='kpi' style='border:1px solid #fbbf24'><div class='label'>NET</div><div class='val-big' style='color:#fbbf24'>+{net}h</div></div></div><div class='col-6'><div class='kpi' style='border:1px solid #f97316'><div class='label'>AHT</div><div class='val-big' style='color:#f97316'>{la}m</div><small style='color:#94a3b8;font-size:9px'>Avg:{round(aa,1)}m</small></div></div><div class='col-6'><div class='kpi' style='border:1px solid #8b5cf6'><div class='label'>QA SCORE</div><div class='val-big' style='color:#8b5cf6'>{lq}%</div><small style='color:#94a3b8;font-size:9px'>Avg:{round(qa,1)}%</small></div></div></div>"
    html+=f"<div class='row g-2 mt-4'><div class='col-6'><div class='card-dark' style='border:1px solid #22c55e'><h6 style='color:#22c55e'>Add NORMAL OT</h6><form method='POST' action='/add_ot/{aid}' class='row g-2'><input type='hidden' name='type' value='NORMAL_OT'><div class='col-6'><input name='hours' type='number' step='0.5' class='form-control form-control-sm' placeholder='Hours' required></div><div class='col-6'><input name='date' type='date' class='form-control form-control-sm' value='{datetime.now(PH_TZ).strftime('%Y-%m-%d')}'></div><div class='col-12'><input name='reason' class='form-control form-control-sm' placeholder='Reason'></div><div class='col-12'><button class='btn w-100 mt-1' style='background:#22c55e;color:white'>Add Normal OT</button></div></form></div></div><div class='col-6'><div class='card-dark' style='border:1px solid #3b82f6'><h6 style='color:#3b82f6'>Add RESTDAY OT</h6><form method='POST' action='/add_ot/{aid}' class='row g-2'><input type='hidden' name='type' value='RESTDAY_OT'><div class='col-6'><input name='hours' type='number' step='0.5' class='form-control form-control-sm' placeholder='Hours' required></div><div class='col-6'><input name='date' type='date' class='form-control form-control-sm' value='{datetime.now(PH_TZ).strftime('%Y-%m-%d')}'></div><div class='col-12'><input name='reason' class='form-control form-control-sm' placeholder='Reason'></div><div class='col-12'><button class='btn w-100 mt-1' style='background:#3b82f6;color:white'>Add Restday OT</button></div></form></div></div><div class='col-6'><div class='card-dark' style='border:1px solid #f97316'><h6 style='color:#f97316'>Add AHT</h6><form method='POST' action='/add_perf/{aid}' class='row g-2'><input type='hidden' name='type' value='AHT'><div class='col-6'><input name='value' type='number' step='0.1' class='form-control form-control-sm' placeholder='Minutes' required></div><div class='col-6'><input name='date' type='date' class='form-control form-control-sm' value='{datetime.now(PH_TZ).strftime('%Y-%m-%d')}'></div><div class='col-12'><input name='reason' class='form-control form-control-sm' placeholder='Notes'></div><div class='col-12'><button class='btn w-100 mt-1' style='background:#f97316;color:white'>Add AHT</button></div></form></div></div><div class='col-6'><div class='card-dark' style='border:1px solid #8b5cf6'><h6 style='color:#8b5cf6'>Add QA SCORE</h6><form method='POST' action='/add_perf/{aid}' class='row g-2'><input type='hidden' name='type' value='QA'><div class='col-6'><input name='value' type='number' step='0.1' class='form-control form-control-sm' placeholder='%' required></div><div class='col-6'><input name='date' type='date' class='form-control form-control-sm' value='{datetime.now(PH_TZ).strftime('%Y-%m-%d')}'></div><div class='col-12'><input name='reason' class='form-control form-control-sm' placeholder='QA notes'></div><div class='col-12'><button class='btn w-100 mt-1' style='background:#8b5cf6;color:white'>Add QA</button></div></form></div></div><div class='col-12'><div class='card-dark' style='border:1px solid #ef4444'><h6 style='color:#ef4444'>Add LOSS HOURS</h6><form method='POST' action='/add_ot/{aid}' class='row g-2'><input type='hidden' name='type' value='LOSS'><div class='col-4'><input name='hours' type='number' step='0.5' class='form-control form-control-sm' placeholder='Loss Hrs' required></div><div class='col-4'><input name='date' type='date' class='form-control form-control-sm' value='{datetime.now(PH_TZ).strftime('%Y-%m-%d')}'></div><div class='col-4'><select name='loss_type' class='form-select form-select-sm'><option>Late</option><option>Absent</option><option>Undertime</option></select></div><div class='col-12'><input name='reason' class='form-control form-control-sm' placeholder='Reason'></div><div class='col-12'><button class='btn w-100 mt-1' style='background:#ef4444;color:white'>Add Loss</button></div></form></div></div></div>"
    html+=f"<div class='mt-4'><h6 style='color:white'>OT & Loss History</h6><div class='table-responsive'><table class='table table-sm'><thead><tr><th>Date</th><th>Type</th><th>Hrs</th><th>Reason</th><th></th></tr></thead><tbody>{log_rows}</tbody></table></div></div><div class='mt-3'><h6 style='color:white'>AHT & QA History</h6><div class='table-responsive'><table class='table table-sm'><thead><tr><th>Date</th><th>Type</th><th>Value</th><th>Notes</th><th></th></tr></thead><tbody>{perf_rows}</tbody></table></div></div></div>"
    return page(html)

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
