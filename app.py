
import os, json, time
from flask import Flask, request, redirect, jsonify, Response
from collections import defaultdict
from datetime import datetime
import io, csv

app = Flask(__name__)
app.secret_key = "team-shine-m9-final"

# ---------- Firebase init with NO CRASH ----------
FIREBASE_MODE = "none"  # none | firestore | realtime
db_firestore = None
db_ref_root = None
init_error = ""

try:
    import firebase_admin
    from firebase_admin import credentials, firestore, db
    if not firebase_admin._apps:
        cred_obj = None
        if os.path.exists("serviceAccountKey.json"):
            cred_obj = credentials.Certificate("serviceAccountKey.json")
        elif os.environ.get("FIREBASE_CREDENTIALS"):
            try:
                cdict = json.loads(os.environ.get("FIREBASE_CREDENTIALS"))
                cred_obj = credentials.Certificate(cdict)
            except Exception as je:
                init_error = f"FIREBASE_CREDENTIALS invalid JSON: {je}"
        if cred_obj:
            db_url = os.environ.get("FIREBASE_DATABASE_URL") or os.environ.get("FIREBASE_DB_URL")
            if db_url:
                firebase_admin.initialize_app(cred_obj, {"databaseURL": db_url})
                FIREBASE_MODE = "realtime"
            else:
                firebase_admin.initialize_app(cred_obj)
                # try to detect mode later
                FIREBASE_MODE = "firestore"
            # test which is usable
            try:
                if db_url:
                    db_ref_root = db.reference("team_shine_m9")
                    FIREBASE_MODE = "realtime"
                else:
                    db_firestore = firestore.client()
                    FIREBASE_MODE = "firestore"
            except:
                db_firestore = firestore.client()
                FIREBASE_MODE = "firestore"
        else:
            init_error = "No serviceAccountKey.json and no FIREBASE_CREDENTIALS"
    else:
        # already init
        db_url = os.environ.get("FIREBASE_DATABASE_URL")
        if db_url:
            from firebase_admin import db
            db_ref_root = db.reference("team_shine_m9")
            FIREBASE_MODE = "realtime"
        else:
            db_firestore = firestore.client()
            FIREBASE_MODE = "firestore"
except Exception as e:
    init_error = str(e)
    FIREBASE_MODE = "none"

# ---------- helpers ----------
_cache = {"data": None, "t": 0}
def get_agents():
    global _cache
    if _cache["data"] and time.time() - _cache["t"] < 15:
        return _cache["data"]
    agents = []
    if FIREBASE_MODE == "realtime" and db_ref_root:
        raw = db_ref_root.child("agents").get() or {}
        for aid, aval in raw.items():
            if isinstance(aval, dict):
                aval["id"] = aid
                agents.append(aval)
    elif FIREBASE_MODE == "firestore" and db_firestore:
        try:
            docs = db_firestore.collection("agents").stream()
            for d in docs:
                a = d.to_dict()
                a["id"] = d.id
                # quick OT total
                try:
                    ot_q = db_firestore.collection("ot_logs").where("agent_id","==",a["id"]).stream()
                    a["_ot_total"] = sum(float(x.to_dict().get("hours",0) or 0) for x in ot_q)
                except:
                    a["_ot_total"] = a.get("_ot_total",0)
                agents.append(a)
        except Exception as e:
            print(e)
    agents.sort(key=lambda x: x.get("NAME","").lower())
    _cache = {"data": agents, "t": time.time()}
    return agents

def clear_cache():
    global _cache
    _cache = {"data": None, "t": 0}

def esc(s):
    if s is None: return ""
    return str(s).replace("&","&amp;").replace("<","&lt;").replace(">","&gt;").replace('"',"&quot;")

HTML_BASE = """<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1">
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
<link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.0/font/bootstrap-icons.css" rel="stylesheet">
<title>TEAM SHINE M9</title>
<style>
body{background:#080c14;color:#e2e8f0}
.card{background:#111827!important;border:1px solid #1f2937!important;border-radius:16px!important}
.kpi{padding:16px;border-radius:14px;background:#0f172a;border-left:4px solid #fbbf24}
.badge-id{background:#0f172a;border:1px solid #334155;color:#94a3b8;border-radius:8px;padding:4px 8px;font-size:11px}
.table thead th{background:#0f172a!important;color:#fbbf24!important;font-size:11px;text-transform:uppercase}
.table tbody td{background:#111827!important;border-color:#1f2937!important}
</style></head><body>
<nav class="navbar navbar-dark bg-dark p-3"><div class="container-fluid">
<a class="navbar-brand fw-bold" href="/"><i class="bi bi-lightning-charge-fill text-warning"></i> TEAM SHINE M9 <span class="badge bg-success" style="font-size:10px">__MODE__</span></a>
<div><a href="/" class="btn btn-sm btn-outline-light">Agents</a> <a href="/dashboard" class="btn btn-sm btn-warning">Dashboard</a> <a href="/add" class="btn btn-sm btn-warning">+ Add</a></div>
</div></nav><div class="container-fluid p-3">__CONTENT__</div></body></html>"""

def page(content):
    return HTML_BASE.replace("__CONTENT__", content).replace("__MODE__", FIREBASE_MODE.upper() + (" ⚡" if FIREBASE_MODE=="realtime" else ""))

@app.route("/ping")
def ping():
    return "alive", 200

@app.route("/status")
def status():
    return jsonify({"mode": FIREBASE_MODE, "has_db_url": bool(os.environ.get("FIREBASE_DATABASE_URL")), "has_cred": bool(os.path.exists("serviceAccountKey.json") or os.environ.get("FIREBASE_CREDENTIALS")), "error": init_error, "agent_count": len(get_agents()) if FIREBASE_MODE!="none" else 0})

@app.route("/")
def index():
    if FIREBASE_MODE=="none":
        return page(f"""
        <div class="card p-4"><h4>Setup Needed ⚙️</h4>
        <p>Mode: {FIREBASE_MODE} | Error: {esc(init_error)}</p>
        <p><b>1. Add Secret File:</b> Render -> Environment -> Secret Files -> Filename: serviceAccountKey.json -> Paste Firebase private key JSON</p>
        <p><b>2. For REALTIME (mas mabilis sa Pinas):</b> Add Environment Variable FIREBASE_DATABASE_URL = https://team-shine-m9-default-rtdb.asia-southeast1.firebasedatabase.app</p>
        <p>Current DB_URL: {esc(os.environ.get('FIREBASE_DATABASE_URL','EMPTY'))}</p>
        <p>Cred exists: {os.path.exists('serviceAccountKey.json')} | Env cred exists: {bool(os.environ.get('FIREBASE_CREDENTIALS'))}</p>
        <a href="/status" class="btn btn-warning">Check Status JSON</a>
        </div>
        """)
    agents = get_agents()
    rows = ""
    for a in agents:
        ot = float(a.get("_ot_total",0) or 0)
        loss = float(a.get("_loss_total",0) or 0)
        rows+=f"<tr><td><span class='badge-id'>{esc(a.get('id'))}</span></td><td><a href='/view/{esc(a.get('id'))}' style='color:white;text-decoration:none'>{esc(a.get('NAME',''))}<br><small style='color:#94a3b8'>{esc(a.get('TENCENT ID',''))}</small></a></td><td>{ot:.1f}h</td><td>{loss:.1f}h</td><td>{ot-loss:.1f}h</td></tr>"
    return page(f"""
    <h5>All Agents ({len(agents)}) - {FIREBASE_MODE.upper()} Mode - 1 call only ⚡</h5>
    <div class="card"><div class="table-responsive"><table class="table"><thead><tr><th>ID</th><th>AGENT</th><th>OT</th><th>LOSS</th><th>NET</th></tr></thead><tbody>{rows}</tbody></table></div></div>
    """)

@app.route("/dashboard")
def dashboard():
    if FIREBASE_MODE=="none":
        return redirect("/")
    agents = get_agents()
    total=len(agents)
    ot=sum(float(a.get("_ot_total",0) or 0) for a in agents)
    loss=sum(float(a.get("_loss_total",0) or 0) for a in agents)
    return page(f"""
    <div class="row g-3"><div class="col-6 col-md-3"><div class="kpi"><small>TOTAL</small><h3>{total}</h3></div></div>
    <div class="col-6 col-md-3"><div class="kpi" style="border-color:#22c55e"><small>OT</small><h3>{ot:.1f}h</h3></div></div>
    <div class="col-6 col-md-3"><div class="kpi" style="border-color:#ef4444"><small>LOSS</small><h3>{loss:.1f}h</h3></div></div>
    <div class="col-6 col-md-3"><div class="kpi" style="border-color:#3b82f6"><small>NET</small><h3>{ot-loss:.1f}h</h3></div></div></div>
    """)

@app.route("/view/<aid>")
def view_aid(aid):
    if FIREBASE_MODE=="realtime":
        data = db_ref_root.child(f"agents/{aid}").get() or {}
    else:
        doc = db_firestore.collection("agents").document(aid).get()
        data = doc.to_dict() if doc.exists else {}
    if not data:
        return "Not found",404
    fields = ["NAME","TENCENT ID","DATE HIRED","PHONE NAME","NBS ID","EMAIL"]
    det = "".join([f"<div class='col-6'><small>{f}</small><br><b>{esc(data.get(f,''))}</b></div>" for f in fields])
    return page(f"<a href='/' class='btn btn-sm btn-light mb-2'>Back</a><div class='card p-3'><h5>{esc(data.get('NAME',''))}</h5><div class='row g-2'>{det}</div><hr><p>OT: {float(data.get('_ot_total',0) or 0):.1f}h</p><a href='/edit/{aid}' class='btn btn-warning btn-sm'>Edit</a> <a href='/delete/{aid}' class='btn btn-outline-danger btn-sm'>Delete</a></div>")

@app.route("/add", methods=["GET","POST"])
def add():
    if request.method=="POST":
        vals = {k: request.form.get(k,"") for k in ["NAME","TENCENT ID","DATE HIRED","PHONE NAME","NBS ID","EMAIL"]}
        vals["_ot_total"]=0; vals["_loss_total"]=0
        if FIREBASE_MODE=="realtime":
            new = db_ref_root.child("agents").push(vals)
            aid=new.key
        else:
            new = db_firestore.collection("agents").add(vals)
            aid=new[1].id
        clear_cache()
        return redirect(f"/view/{aid}")
    form="".join([f'<div class="col-6"><label>{f}</label><input name="{f}" class="form-control mb-2"></div>' for f in ["NAME","TENCENT ID","DATE HIRED","PHONE NAME","NBS ID","EMAIL"]])
    return page(f"<div class='card p-3'><form method='POST' class='row'>{form}<div class='col-12'><button class='btn btn-warning w-100 mt-2'>Save</button></div></form></div>")

@app.route("/edit/<aid>", methods=["GET","POST"])
def edit(aid):
    if FIREBASE_MODE=="realtime":
        ref = db_ref_root.child(f"agents/{aid}")
        data = ref.get() or {}
    else:
        ref = db_firestore.collection("agents").document(aid)
        data = ref.get().to_dict() if ref.get().exists else {}
    if request.method=="POST":
        vals = {k: request.form.get(k,"") for k in ["NAME","TENCENT ID","DATE HIRED","PHONE NAME","NBS ID","EMAIL"]}
        if FIREBASE_MODE=="realtime":
            ref.update(vals)
        else:
            ref.update(vals)
        clear_cache()
        return redirect(f"/view/{aid}")
    form="".join([f'<div class="col-6"><label>{f}</label><input name="{f}" value="{esc(data.get(f,""))}" class="form-control mb-2"></div>' for f in ["NAME","TENCENT ID","DATE HIRED","PHONE NAME","NBS ID","EMAIL"]])
    return page(f"<div class='card p-3'><form method='POST' class='row'>{form}<div class='col-12'><button class='btn btn-warning w-100 mt-2'>Update</button></div></form></div>")

@app.route("/delete/<aid>")
def delete(aid):
    if FIREBASE_MODE=="realtime":
        db_ref_root.child(f"agents/{aid}").delete()
    else:
        db_firestore.collection("agents").document(aid).delete()
    clear_cache()
    return redirect("/")

# migrate route
MIGRATE = {"agents": [{"id": 1, "NAME": "Bernaldo, Catherine", "TENCENT ID": "5116", "DATE HIRED": "2025-03-31", "PHONE NAME": "HOPE", "NBS ID": "10116", "HEADSET SN": "2309410DUO286", "IBAS": "CATBERNA", "DJANGO": "cabernaldo@uas2.com.ph", "NT LOG IN": "UAS-Bernaldo.Catheri", "Sales Force": "uas-bernaldo.cath@cict.com.ph", "ZOHO": "c.bernaldo@uas2.com.ph", "BSS WEB": "uas-bernaldo.cath@partner.convergeict.com", "EMAIL": "bernaldocatherine2@gmail.com", "BIRTHDAY": "1992-08-03", "CONTACT NO.": "09468168239", "ADDRESS": "15-C Feliza St. Brgy.Malabanias, Angeles City, Pampanga"}, {"id": 2, "NAME": "Lopez, Eljay", "TENCENT ID": "5243", "DATE HIRED": "2025-04-14", "PHONE NAME": "SOJI", "NBS ID": "10752", "HEADSET SN": "2309410DU1324", "IBAS": "", "DJANGO": "eljhay.lopez@uas2.com.ph", "NT LOG IN": "UAS-Lopez.eljhay", "Sales Force": "uas-lopez.eljay@cict.com.ph", "ZOHO": "eljhay.lopez@uas2.com.ph", "BSS WEB": "uas-lopez.eljay@partner.convergeict.com", "EMAIL": "is.eljaylopez1@gmail.com", "BIRTHDAY": "1999-11-02", "CONTACT NO.": "09666096553", "ADDRESS": "Blk 5 Lot 14 Rockville Subdivision, Barangay Malpitic, City of San Fernando, Pamapanga"}, {"id": 3, "NAME": "Maniago, Danzeil James", "TENCENT ID": "5242", "DATE HIRED": "2025-03-31", "PHONE NAME": "Danzeil", "NBS ID": "10148", "HEADSET SN": "2309410DU0522", "IBAS": "DAJMANIA", "DJANGO": "Damaniago@uas2.com.ph", "NT LOG IN": "UAS-Maniago.Danzeil", "Sales Force": "uas-danzeil.maniago@cict.com.ph", "ZOHO": "damaniago@uas2.com.ph", "BSS WEB": "uas-danzeil.maniago@partner.convergeict.com", "EMAIL": "denzeiljamesmaniago@gmail.com", "BIRTHDAY": "2003-01-16", "CONTACT NO.": "09630692546", "ADDRESS": "Blk.17 Lot.2, Brgy. Cristo Rey, Capas, Tarlac"}, {"id": 4, "NAME": "Navarro, Jerome", "TENCENT ID": "5093", "DATE HIRED": "2025-03-03", "PHONE NAME": "KHALEE", "NBS ID": "9808", "HEADSET SN": "2309410DU0098", "IBAS": "NAVJEROM", "DJANGO": "je.navarro@uas2.com.ph", "NT LOG IN": "UAS-Navarro.Jerome", "Sales Force": "uas-jerome.navarro@cict.com.ph", "ZOHO": "je.navarro@uas2.com.ph", "BSS WEB": "uas-jerome.navarro@partner.convergeict.com", "EMAIL": "jeromen891@gmail.com", "BIRTHDAY": "1998-04-16", "CONTACT NO.": "09670696382", "ADDRESS": "1036, Baranggay Capaya 1, Angeles City, Pampanga"}, {"id": 5, "NAME": "Paz, Ben Gerard", "TENCENT ID": "5038", "DATE HIRED": "2025-03-03", "PHONE NAME": "GIEH", "NBS ID": "9814", "HEADSET SN": "2309410DU0381", "IBAS": "PAZBENGE", "DJANGO": "bg.paz@uas2.com.ph", "NT LOG IN": "UAS-Paz.Ben", "Sales Force": "uas-ben.paz@cict.com.ph", "ZOHO": "bg.paz@uas2.com.ph", "BSS WEB": "uas-ben.paz@partner.convergeict.com", "EMAIL": "bengerardp@gmail.com", "BIRTHDAY": "1995-06-25", "CONTACT NO.": "09634269072", "ADDRESS": "Pulung Maragul, Angeles City"}, {"id": 6, "NAME": "Waje, Avy", "TENCENT ID": "5115", "DATE HIRED": "2025-03-03", "PHONE NAME": "SCARLET", "NBS ID": "9828", "HEADSET SN": "2309410DU1246", "IBAS": "WAJAVYWA", "DJANGO": "a.waje@uas2.com.ph", "NT LOG IN": "UAS-Waje.Avy", "Sales Force": "uas-avy.waje@cict.com.ph", "ZOHO": "a.waje@uas2.com.ph", "BSS WEB": "uas-avy.waje@partner.convergeict.com", "EMAIL": "avywaje43@gmail.com", "BIRTHDAY": "2005-01-16", "CONTACT NO.": "09534367262", "ADDRESS": "0366 Purok 2, Brgy. Calzadang Bayu, Porac, Pampanga"}, {"id": 7, "NAME": "Guevarra, James Rainielle", "TENCENT ID": "5291", "DATE HIRED": "2025-06-23", "PHONE NAME": "Rain", "NBS ID": "11412", "HEADSET SN": "", "IBAS": "JMSRNGVA", "DJANGO": "ja.guevarra@uas2.com.ph", "NT LOG IN": "UAS-Guevarra.JamesRa", "Sales Force": "uas-rain.guevarra@cict.com.ph", "ZOHO": "ja.guevarra@uas2.com.ph", "BSS WEB": "uas-rain.guevarra@partner.convergeict.com", "EMAIL": "jamesrainielle1423@gmail.com", "BIRTHDAY": "2006-08-31", "CONTACT NO.": "09480624706", "ADDRESS": "Blk cd Lot 2c phase 3, Sta. Lucia Rest., Brgy. San Isido, Magalang, Pampanga"}, {"id": 8, "NAME": "Pare, Crisha Joy", "TENCENT ID": "5310", "DATE HIRED": "2025-06-23", "PHONE NAME": "Crisha", "NBS ID": "11368", "HEADSET SN": "", "IBAS": "CRISPARE", "DJANGO": "cr.pare@uas2.com.ph", "NT LOG IN": "UAS-Pare.Crishajoy", "Sales Force": "uas-crishajoy.pare@cict.com.ph", "ZOHO": "cr.pare@uas2.com.ph", "BSS WEB": "uas-crishajoy.pare@partner.convergeict.com", "EMAIL": "Crishapare@gmail.com", "BIRTHDAY": "2004-08-16", "CONTACT NO.": "09496274867", "ADDRESS": "3219 North Dang Bakal, Dau, Mabalacat City, Pampanga"}, {"id": 9, "NAME": "Paraga, Elisa", "TENCENT ID": "5090", "DATE HIRED": "2025-04-28", "PHONE NAME": "Angel", "NBS ID": "10850", "HEADSET SN": "2309410DU0875", "IBAS": "RAGASELI", "DJANGO": "el.paragas@uas2.com.ph", "NT LOG IN": "UAS-paragas.elisallo", "Sales Force": "uas-elisa.paragas@cict.com.ph", "ZOHO": "el.paragas@uas2.com.ph", "BSS WEB": "uas-elisa.paragas@partner.convergeict.com", "EMAIL": "elp012581@gmail.com", "BIRTHDAY": "1981-01-25", "CONTACT NO.": "09760221814", "ADDRESS": "5016 Abacan, Malabanias, Angeles City, Pampanga"}, {"id": 10, "NAME": "Cahuyong, Daveliet Jane", "TENCENT ID": "5726", "DATE HIRED": "2025-08-11", "PHONE NAME": "Devie", "NBS ID": "11518", "HEADSET SN": "", "IBAS": "DCAHUYO", "DJANGO": "d.cahuyong@uas2.com.ph", "NT LOG IN": "UAS-Cahuyong.Davelie", "Sales Force": "uas-dave.cahuyog@cict.com.ph", "ZOHO": "d.cahuyong@uas2.com.ph", "BSS WEB": "uas-dave.cahuyog@partner.convergeict.com", "EMAIL": "daveliethitosis@gmail.com", "BIRTHDAY": "2002-11-08", "CONTACT NO.": "09485518457", "ADDRESS": "Prk 6. Kadamay, Brgy. Cuayan, Angeles City, Pampanga"}, {"id": 11, "NAME": "Quiambao, Allen", "TENCENT ID": "4995", "DATE HIRED": "2026-05-04", "PHONE NAME": "Noble", "NBS ID": "12468", "HEADSET SN": "", "IBAS": "ALQUIAMB", "DJANGO": "al.quiambao@uas2.com.ph", "NT LOG IN": "UAS-allen.quiambao", "Sales Force": "uas-allen.quiambao@cict.com.ph", "ZOHO": "al.quiambao@uas2.com.ph", "BSS WEB": "uas-allen.quiambao@partner.convergeict.com", "EMAIL": "allenquiambao298@gmail.com", "BIRTHDAY": "2008-02-09", "CONTACT NO.": "09978178943", "ADDRESS": "Blk37 Lot20, San Isidro Resettelment, Magalang, Pampanga"}, {"id": 12, "NAME": "Reyes, Katherine", "TENCENT ID": "4996", "DATE HIRED": "2026-05-04", "PHONE NAME": "Kassel", "NBS ID": "12474", "HEADSET SN": "", "IBAS": "KAREYESE", "DJANGO": "ka.reyes@uas2.com.ph", "NT LOG IN": "UAS-katherine.reyes", "Sales Force": "uas-katherine.reyes@cict.com.ph", "ZOHO": "ka.reyes@uas2.com.ph", "BSS WEB": "uas-katherine.reyes@partner.convergeict.com", "EMAIL": "reyeskatherine093@gmail.com", "BIRTHDAY": "2026-09-19", "CONTACT NO.": "09614809467", "ADDRESS": "1624 Interior St. Brgy. Ninoy Aquino, Marisol, Angeles City, Pampanga"}, {"id": 13, "NAME": "Salmero, Jeanel Ann", "TENCENT ID": "4997", "DATE HIRED": "2026-05-04", "PHONE NAME": "Rhett", "NBS ID": "12476", "HEADSET SN": "", "IBAS": "JESALMER", "DJANGO": "je.salmero@uas2.com.ph", "NT LOG IN": "UAS-jeanel.salmero", "Sales Force": "uas-jeanel.salmero@cict.com.ph", "ZOHO": "je.salmero@uas2.com.ph", "BSS WEB": "uas-jeanel.salmero@partner.convergeict.com", "EMAIL": "santosjeanel74@gmail.com", "BIRTHDAY": "2026-12-15", "CONTACT NO.": "09169205580", "ADDRESS": "5086 Juicy Fruit, Brgy Duquit, Mabalacat City, Pampanga"}, {"id": 14, "NAME": "Sampaga, Marie Joy", "TENCENT ID": "4998", "DATE HIRED": "2026-05-04", "PHONE NAME": "Arhem", "NBS ID": "12478", "HEADSET SN": "", "IBAS": "MASAMPAG", "DJANGO": "ma.sampaga@uas2.com.ph", "NT LOG IN": "UAS-marie.sampaga", "Sales Force": "uas-marie.sampaga@cict.com.ph", "ZOHO": "ma.sampaga@uas2.com.ph", "BSS WEB": "uas-marie.sampaga@partner.convergeict.com", "EMAIL": "lacsonmariejoy@gmail.com", "BIRTHDAY": "1997-11-15", "CONTACT NO.": "09368001203", "ADDRESS": "782 Kadenang Kristal, Sapang Biabas, Dau, Mabalacat, Pampanga"}, {"id": 15, "NAME": "Arcilla, Azarias", "TENCENT ID": "4909", "DATE HIRED": "2026-05-04", "PHONE NAME": "Chance", "NBS ID": "12352", "HEADSET SN": "J0XL4V", "IBAS": "AZARARCI", "DJANGO": "a.azarias@uas2.com.ph", "NT LOG IN": "UAS-Arcilla.Azarias", "Sales Force": "uas-azarias.arcilla@cict.com.ph", "ZOHO": "a.azarias@uas2.com.ph", "BSS WEB": "uas-azarias.arcilla@partner.convergeict.com", "EMAIL": "chancearcilla5100@gmail.com", "BIRTHDAY": "2006-05-01", "CONTACT NO.": "09122974939", "ADDRESS": "989 Chico St. San Francisco, Mabalacat City, Pampanga"}, {"id": 16, "NAME": "Bigornia, Shenhel", "TENCENT ID": "4910", "DATE HIRED": "2026-05-04", "PHONE NAME": "Daiji", "NBS ID": "12360", "HEADSET SN": "J0XJP0", "IBAS": "SHENBIGO", "DJANGO": "s.bigornia@uas2.com.ph", "NT LOG IN": "UAS-Bigornia.Shenhel", "Sales Force": "uas-shenhel.bigornia@cict.com.ph", "ZOHO": "s.bigornia@uas2.com.ph", "BSS WEB": "uas-shenhel.bigornia@partner.convergeict.com", "EMAIL": "bshenhel@gmail.com", "BIRTHDAY": "2002-02-19", "CONTACT NO.": "09941644309", "ADDRESS": "26-18B Malaysia St. Don Bonifacio, Pulung Maragul, Balibago, Angeles City"}, {"id": 17, "NAME": "Cano, Regina Carla", "TENCENT ID": "4911", "DATE HIRED": "2026-05-04", "PHONE NAME": "Rachel", "NBS ID": "12378", "HEADSET SN": "J0XJP3", "IBAS": "RCARCANO", "DJANGO": "r.cano@uas2.com.ph", "NT LOG IN": "UAS-Cano.Regina", "Sales Force": "uas-regina.cano@cict.com.ph", "ZOHO": "r.cano@uas2.com.ph", "BSS WEB": "uas-regina.cano@partner.convergeict.com", "EMAIL": "carlacano111517@gmail.com", "BIRTHDAY": "1998-11-11", "CONTACT NO.": "09069331284", "ADDRESS": "05 Mabini St. San Nicolas, Angeles City, Pampanga"}, {"id": 18, "NAME": "Ocampo, Joana Marie", "TENCENT ID": "5269", "DATE HIRED": "2026-05-18", "PHONE NAME": "Tams", "NBS ID": "12578", "HEADSET SN": "JOXKVR", "IBAS": "JNMRIMCP", "DJANGO": "jo.ocampo@uas2.com.ph", "NT LOG IN": "UAS-Ocampo.joana", "Sales Force": "uas-joana.ocampo@cict.com.ph", "ZOHO": "jo.ocampo@uas2.com.p", "BSS WEB": "uas-joana.ocampo@partner.convergeict.com", "EMAIL": "omanarang30@gmail.com", "BIRTHDAY": "1992-08-30", "CONTACT NO.": "09491233865", "ADDRESS": "49 Purok 1, San Pedro 2, Magalang, Pampanga"}, {"id": 19, "NAME": "Pangilinan, Princess", "TENCENT ID": "5271", "DATE HIRED": "2026-05-18", "PHONE NAME": "Peach", "NBS ID": "12580", "HEADSET SN": "JOXKVN", "IBAS": "PRNSPGNN", "DJANGO": "pr.pangilinan@uas2.com.ph", "NT LOG IN": "UAS-Pangilinan.Princ", "Sales Force": "uas-prin.pangilinan@cict.com.ph", "ZOHO": "pr.pangilinan@uas2.com.ph", "BSS WEB": "uas-prin.pangilinan@partner.convergeict.com", "EMAIL": "pangilinanp387@gmail.com", "BIRTHDAY": "2006-12-19", "CONTACT NO.": "09707673225", "ADDRESS": "31 D Yakal St. Aguas Subdivision, Manibaug Paralaya, Porac Pampanga"}], "ot_logs": [{"id": 1, "agent_id": 15, "ot_date": "2026-09-02", "ot_type": "REGULAR", "hours": 2.0, "remarks": "Imported from September sheet - Sept 2", "created_at": "2026-09-07 17:38:45"}, {"id": 2, "agent_id": 15, "ot_date": "2026-09-04", "ot_type": "REGULAR", "hours": 1.0, "remarks": "Imported from September sheet - Sept 4", "created_at": "2026-09-07 17:38:45"}, {"id": 3, "agent_id": 15, "ot_date": "2026-09-05", "ot_type": "RDOT", "hours": 10.0, "remarks": "Imported from September sheet - Sept 5", "created_at": "2026-09-07 17:38:45"}, {"id": 4, "agent_id": 1, "ot_date": "2026-09-01", "ot_type": "REGULAR", "hours": 3.0, "remarks": "Imported from September sheet - Sept 1", "created_at": "2026-09-07 17:38:45"}, {"id": 5, "agent_id": 1, "ot_date": "2026-09-02", "ot_type": "REGULAR", "hours": 1.0, "remarks": "Imported from September sheet - Sept 2", "created_at": "2026-09-07 17:38:45"}, {"id": 6, "agent_id": 1, "ot_date": "2026-09-03", "ot_type": "REGULAR", "hours": 2.0, "remarks": "Imported from September sheet - Sept 3", "created_at": "2026-09-07 17:38:45"}, {"id": 7, "agent_id": 1, "ot_date": "2026-09-04", "ot_type": "REGULAR", "hours": 1.0, "remarks": "Imported from September sheet - Sept 4", "created_at": "2026-09-07 17:38:45"}, {"id": 8, "agent_id": 1, "ot_date": "2026-09-05", "ot_type": "RDOT", "hours": 10.0, "remarks": "Imported from September sheet - Sept 5", "created_at": "2026-09-07 17:38:45"}, {"id": 9, "agent_id": 9, "ot_date": "2026-09-01", "ot_type": "REGULAR", "hours": 1.0, "remarks": "Imported from September sheet - Sept 1", "created_at": "2026-09-07 17:38:45"}, {"id": 10, "agent_id": 9, "ot_date": "2026-09-03", "ot_type": "REGULAR", "hours": 1.0, "remarks": "Imported from September sheet - Sept 3", "created_at": "2026-09-07 17:38:45"}, {"id": 11, "agent_id": 9, "ot_date": "2026-09-05", "ot_type": "RDOT", "hours": 10.0, "remarks": "Imported from September sheet - Sept 5", "created_at": "2026-09-07 17:38:45"}, {"id": 12, "agent_id": 8, "ot_date": "2026-09-01", "ot_type": "REGULAR", "hours": 1.0, "remarks": "Imported from September sheet - Sept 1", "created_at": "2026-09-07 17:38:45"}, {"id": 13, "agent_id": 8, "ot_date": "2026-09-02", "ot_type": "REGULAR", "hours": 1.0, "remarks": "Imported from September sheet - Sept 2", "created_at": "2026-09-07 17:38:45"}, {"id": 14, "agent_id": 8, "ot_date": "2026-09-03", "ot_type": "REGULAR", "hours": 2.0, "remarks": "Imported from September sheet - Sept 3", "created_at": "2026-09-07 17:38:45"}, {"id": 15, "agent_id": 8, "ot_date": "2026-09-05", "ot_type": "RDOT", "hours": 5.0, "remarks": "Imported from September sheet - Sept 5", "created_at": "2026-09-07 17:38:45"}, {"id": 16, "agent_id": 5, "ot_date": "2026-09-01", "ot_type": "REGULAR", "hours": 2.0, "remarks": "Imported from September sheet - Sept 1", "created_at": "2026-09-07 17:38:45"}, {"id": 17, "agent_id": 5, "ot_date": "2026-09-02", "ot_type": "REGULAR", "hours": 1.0, "remarks": "Imported from September sheet - Sept 2", "created_at": "2026-09-07 17:38:45"}, {"id": 18, "agent_id": 5, "ot_date": "2026-09-03", "ot_type": "REGULAR", "hours": 1.0, "remarks": "Imported from September sheet - Sept 3", "created_at": "2026-09-07 17:38:45"}, {"id": 19, "agent_id": 5, "ot_date": "2026-09-04", "ot_type": "REGULAR", "hours": 3.0, "remarks": "Imported from September sheet - Sept 4", "created_at": "2026-09-07 17:38:45"}, {"id": 20, "agent_id": 5, "ot_date": "2026-09-05", "ot_type": "RDOT", "hours": 5.0, "remarks": "Imported from September sheet - Sept 5", "created_at": "2026-09-07 17:38:45"}, {"id": 21, "agent_id": 11, "ot_date": "2026-09-01", "ot_type": "REGULAR", "hours": 1.0, "remarks": "Imported from September sheet - Sept 1", "created_at": "2026-09-07 17:38:45"}, {"id": 22, "agent_id": 11, "ot_date": "2026-09-02", "ot_type": "REGULAR", "hours": 1.0, "remarks": "Imported from September sheet - Sept 2", "created_at": "2026-09-07 17:38:45"}, {"id": 23, "agent_id": 12, "ot_date": "2026-09-01", "ot_type": "REGULAR", "hours": 1.0, "remarks": "Imported from September sheet - Sept 1", "created_at": "2026-09-07 17:38:45"}, {"id": 24, "agent_id": 6, "ot_date": "2026-09-05", "ot_type": "RDOT", "hours": 7.0, "remarks": "Imported from September sheet - Sept 5", "created_at": "2026-09-07 17:38:45"}, {"id": 25, "agent_id": 18, "ot_date": "2026-09-01", "ot_type": "REGULAR", "hours": 2.0, "remarks": "Imported from September sheet - Sept 1", "created_at": "2026-09-07 17:38:45"}, {"id": 26, "agent_id": 18, "ot_date": "2026-09-02", "ot_type": "REGULAR", "hours": 1.0, "remarks": "Imported from September sheet - Sept 2", "created_at": "2026-09-07 17:38:45"}, {"id": 27, "agent_id": 19, "ot_date": "2026-09-01", "ot_type": "REGULAR", "hours": 1.0, "remarks": "Imported from September sheet - Sept 1", "created_at": "2026-09-07 17:38:45"}, {"id": 28, "agent_id": 2, "ot_date": "2026-09-04", "ot_type": "REGULAR", "hours": 1.0, "remarks": "Imported from September sheet - Sept 4", "created_at": "2026-09-07 17:38:45"}, {"id": 29, "agent_id": 3, "ot_date": "2026-09-04", "ot_type": "REGULAR", "hours": 1.0, "remarks": "Imported from September sheet - Sept 4", "created_at": "2026-09-07 17:38:45"}, {"id": 30, "agent_id": 4, "ot_date": "2026-09-01", "ot_type": "REGULAR", "hours": 1.0, "remarks": "Imported from September sheet - Sept 1", "created_at": "2026-09-07 17:38:45"}]}

@app.route("/migrate_realtime")
def mig():
    if FIREBASE_MODE!="realtime":
        return f"Need realtime mode. Current: {FIREBASE_MODE}. Add FIREBASE_DATABASE_URL"
    existing = db_ref_root.child("agents").get() or {}
    if existing:
        return f"Already {len(existing)} in realtime. <a href='/'>Home</a>"
    count=0
    for ag in MIGRATE["agents"]:
        aid = str(ag.get("id") or ag.get("ID") or count+1)
        ag.pop("id",None)
        clean = {k: ("" if v is None else str(v)) for k,v in ag.items()}
        clean["_ot_total"]=0
        for ot in MIGRATE["ot_logs"]:
            if str(ot.get("agent_id"))==aid:
                clean["_ot_total"]+=float(ot.get("hours",0) or 0)
        db_ref_root.child(f"agents/{aid}").set(clean)
        for ot in MIGRATE["ot_logs"]:
            if str(ot.get("agent_id"))==aid:
                db_ref_root.child(f"agents/{aid}/ot_logs").push({"ot_date": str(ot.get("ot_date")), "hours": float(ot.get("hours",0) or 0), "ot_type": str(ot.get("ot_type")), "remarks": str(ot.get("remarks",""))})
        count+=1
    clear_cache()
    return f"Migrated {count} agents to REALTIME! <a href='/'>Go Home - SUPER FAST NA!</a>"

if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",5000)))
