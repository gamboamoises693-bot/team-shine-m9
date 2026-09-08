
import os, json, re
from flask import Flask, request, redirect, jsonify
import time
app = Flask(__name__)

def sanitize(k):
    import re
    k = re.sub(r'[\.\$\#\[\]\/]', '_', k)
    k = k.strip().replace(" ", "_")
    k = re.sub(r'_+', '_', k)
    return k or "FIELD"

def desanitize_display(k):
    # show nice
    return k.replace("_"," ")

FIREBASE_MODE="none"
db_root=None
err=""
try:
    import firebase_admin
    from firebase_admin import credentials, db
    if not firebase_admin._apps:
        if os.path.exists("serviceAccountKey.json"):
            cred = credentials.Certificate("serviceAccountKey.json")
            firebase_admin.initialize_app(cred, {"databaseURL": os.environ.get("FIREBASE_DATABASE_URL")})
        elif os.environ.get("FIREBASE_CREDENTIALS"):
            cdict=json.loads(os.environ.get("FIREBASE_CREDENTIALS"))
            cred=credentials.Certificate(cdict)
            firebase_admin.initialize_app(cred, {"databaseURL": os.environ.get("FIREBASE_DATABASE_URL")})
    db_root=db.reference("team_shine_m9")
    FIREBASE_MODE="realtime"
except Exception as e:
    err=str(e)

_cache={"data":None,"t":0}
def get_agents():
    global _cache
    if _cache["data"] and time.time()-_cache["t"]<10:
        return _cache["data"]
    raw = db_root.child("agents").get() or {}
    agents=[]
    for aid, val in raw.items():
        if isinstance(val, dict):
            val["id"]=aid
            # make NAME accessible even if stored as NAME
            agents.append(val)
    agents.sort(key=lambda x: x.get("NAME","").lower())
    _cache={"data":agents,"t":time.time()}
    return agents

def clear_cache():
    global _cache
    _cache={"data":None,"t":0}

@app.route("/ping")
def ping(): return "alive"
@app.route("/")
def index():
    if FIREBASE_MODE=="none":
        return f"Setup needed {err}"
    agents=get_agents()
    rows=""
    for a in agents:
        name=a.get("NAME") or a.get("NAME_") or ""
        tid=a.get("TENCENT_ID") or a.get("TENCENT") or a.get("TENCENT_ID") or ""
        rows+=f"<tr><td>{a.get('id')}</td><td><a href='/view/{a.get('id')}' style='color:white'>{name}<br><small>{tid}</small></a></td><td>{float(a.get('_ot_total',0) or 0):.1f}</td></tr>"
    return f"""<html><head><meta name=viewport content="width=device-width,initial-scale=1"><link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet"></head><body style="background:#080c14;color:#e2e8f0"><nav class="navbar bg-dark p-2"><span class="navbar-brand text-white">TEAM SHINE M9 REALTIME - {len(agents)} agents ⚡</span><a href="/add" class="btn btn-warning btn-sm">+ Add</a></nav><div class="p-3"><table class="table table-dark"><thead><tr><th>ID</th><th>NAME</th><th>OT</th></tr></thead><tbody>{rows}</tbody></table><a href="/check">Check raw</a></div></body></html>"""

@app.route("/check")
def check():
    raw=db_root.child("agents").get() or {}
    return f"{len(raw)} agents<br>{str(list(raw.values())[:1])}"

@app.route("/view/<aid>")
def view(aid):
    data=db_root.child(f"agents/{aid}").get() or {}
    html="<h3>Agent "+aid+"</h3><ul>"
    for k,v in data.items():
        if not k.startswith("_"):
            html+=f"<li><b>{desanitize_display(k)}</b>: {v}</li>"
    html+=f"</ul><a href='/'>Back</a> | <a href='/delete/{aid}'>Delete</a>"
    return html

@app.route("/delete/<aid>")
def delete(aid):
    db_root.child(f"agents/{aid}").delete()
    clear_cache()
    return redirect("/")

@app.route("/add", methods=["GET","POST"])
def add():
    fields=["NAME","TENCENT_ID","DATE_HIRED","PHONE_NAME","NBS_ID","EMAIL","CONTACT_NO_","ADDRESS"]
    if request.method=="POST":
        clean={}
        for f in fields:
            clean[f]=request.form.get(f,"")
        clean["_ot_total"]=0
        ref=db_root.child("agents").push(clean)
        clear_cache()
        return redirect("/")
    form="".join([f'<label>{desanitize_display(f)}</label><input name="{f}" class="form-control mb-2">' for f in fields])
    return f"<form method='POST' class='p-3'>{form}<button class='btn btn-warning w-100'>Save</button></form>"

if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",5000)))
