
import sqlite3, os, json
from flask import Flask, request, redirect, g

app = Flask(__name__)
DATABASE = "Agent.db"
COLUMNS = ['NAME', 'TENCENT ID', 'DATE HIRED', 'PHONE NAME', 'NBS ID', 'HEADSET SN', 'IBAS', 'DJANGO', 'NT LOG IN', 'Sales Force', 'ZOHO', 'BSS WEB', 'EMAIL', 'BIRTHDAY', 'CONTACT NO.', 'ADDRESS']
SEED_DATA = [
  {
    "id": 1,
    "NAME": "Bernaldo, Catherine",
    "TENCENT ID": "5116",
    "DATE HIRED": "2025-03-31",
    "PHONE NAME": "HOPE",
    "NBS ID": "10116",
    "HEADSET SN": "2309410DUO286",
    "IBAS": "CATBERNA",
    "DJANGO": "cabernaldo@uas2.com.ph",
    "NT LOG IN": "UAS-Bernaldo.Catheri",
    "Sales Force": "uas-bernaldo.cath@cict.com.ph",
    "ZOHO": "c.bernaldo@uas2.com.ph",
    "BSS WEB": "uas-bernaldo.cath@partner.convergeict.com",
    "EMAIL": "bernaldocatherine2@gmail.com",
    "BIRTHDAY": "1992-08-03",
    "CONTACT NO.": "09468168239",
    "ADDRESS": "15-C Feliza St. Brgy.Malabanias, Angeles City, Pampanga"
  },
  {
    "id": 2,
    "NAME": "Lopez, Eljay",
    "TENCENT ID": "5243",
    "DATE HIRED": "2025-04-14",
    "PHONE NAME": "SOJI",
    "NBS ID": "10752",
    "HEADSET SN": "2309410DU1324",
    "IBAS": "",
    "DJANGO": "eljhay.lopez@uas2.com.ph",
    "NT LOG IN": "UAS-Lopez.eljhay",
    "Sales Force": "uas-lopez.eljay@cict.com.ph",
    "ZOHO": "eljhay.lopez@uas2.com.ph",
    "BSS WEB": "uas-lopez.eljay@partner.convergeict.com",
    "EMAIL": "is.eljaylopez1@gmail.com",
    "BIRTHDAY": "1999-11-02",
    "CONTACT NO.": "09666096553",
    "ADDRESS": "Blk 5 Lot 14 Rockville Subdivision, Barangay Malpitic, City of San Fernando, Pamapanga"
  },
  {
    "id": 3,
    "NAME": "Maniago, Danzeil James",
    "TENCENT ID": "5242",
    "DATE HIRED": "2025-03-31",
    "PHONE NAME": "Danzeil",
    "NBS ID": "10148",
    "HEADSET SN": "2309410DU0522",
    "IBAS": "DAJMANIA",
    "DJANGO": "Damaniago@uas2.com.ph",
    "NT LOG IN": "UAS-Maniago.Danzeil",
    "Sales Force": "uas-danzeil.maniago@cict.com.ph",
    "ZOHO": "damaniago@uas2.com.ph",
    "BSS WEB": "uas-danzeil.maniago@partner.convergeict.com",
    "EMAIL": "denzeiljamesmaniago@gmail.com",
    "BIRTHDAY": "2003-01-16",
    "CONTACT NO.": "09630692546",
    "ADDRESS": "Blk.17 Lot.2, Brgy. Cristo Rey, Capas, Tarlac"
  },
  {
    "id": 4,
    "NAME": "Navarro, Jerome",
    "TENCENT ID": "5093",
    "DATE HIRED": "2025-03-03",
    "PHONE NAME": "KHALEE",
    "NBS ID": "9808",
    "HEADSET SN": "2309410DU0098",
    "IBAS": "NAVJEROM",
    "DJANGO": "je.navarro@uas2.com.ph",
    "NT LOG IN": "UAS-Navarro.Jerome",
    "Sales Force": "uas-jerome.navarro@cict.com.ph",
    "ZOHO": "je.navarro@uas2.com.ph",
    "BSS WEB": "uas-jerome.navarro@partner.convergeict.com",
    "EMAIL": "jeromen891@gmail.com",
    "BIRTHDAY": "1998-04-16",
    "CONTACT NO.": "09670696382",
    "ADDRESS": "1036, Baranggay Capaya 1, Angeles City, Pampanga"
  },
  {
    "id": 5,
    "NAME": "Paz, Ben Gerard",
    "TENCENT ID": "5038",
    "DATE HIRED": "2025-03-03",
    "PHONE NAME": "GIEH",
    "NBS ID": "9814",
    "HEADSET SN": "2309410DU0381",
    "IBAS": "PAZBENGE",
    "DJANGO": "bg.paz@uas2.com.ph",
    "NT LOG IN": "UAS-Paz.Ben",
    "Sales Force": "uas-ben.paz@cict.com.ph",
    "ZOHO": "bg.paz@uas2.com.ph",
    "BSS WEB": "uas-ben.paz@partner.convergeict.com",
    "EMAIL": "bengerardp@gmail.com",
    "BIRTHDAY": "1995-06-25",
    "CONTACT NO.": "09634269072",
    "ADDRESS": "Pulung Maragul, Angeles City"
  },
  {
    "id": 6,
    "NAME": "Waje, Avy",
    "TENCENT ID": "5115",
    "DATE HIRED": "2025-03-03",
    "PHONE NAME": "SCARLET",
    "NBS ID": "9828",
    "HEADSET SN": "2309410DU1246",
    "IBAS": "WAJAVYWA",
    "DJANGO": "a.waje@uas2.com.ph",
    "NT LOG IN": "UAS-Waje.Avy",
    "Sales Force": "uas-avy.waje@cict.com.ph",
    "ZOHO": "a.waje@uas2.com.ph",
    "BSS WEB": "uas-avy.waje@partner.convergeict.com",
    "EMAIL": "avywaje43@gmail.com",
    "BIRTHDAY": "2005-01-16",
    "CONTACT NO.": "09534367262",
    "ADDRESS": "0366 Purok 2, Brgy. Calzadang Bayu, Porac, Pampanga"
  },
  {
    "id": 7,
    "NAME": "Guevarra, James Rainielle",
    "TENCENT ID": "5291",
    "DATE HIRED": "2025-06-23",
    "PHONE NAME": "Rain",
    "NBS ID": "11412",
    "HEADSET SN": "",
    "IBAS": "JMSRNGVA",
    "DJANGO": "ja.guevarra@uas2.com.ph",
    "NT LOG IN": "UAS-Guevarra.JamesRa",
    "Sales Force": "uas-rain.guevarra@cict.com.ph",
    "ZOHO": "ja.guevarra@uas2.com.ph",
    "BSS WEB": "uas-rain.guevarra@partner.convergeict.com",
    "EMAIL": "jamesrainielle1423@gmail.com",
    "BIRTHDAY": "2006-08-31",
    "CONTACT NO.": "09480624706",
    "ADDRESS": "Blk cd Lot 2c phase 3, Sta. Lucia Rest., Brgy. San Isido, Magalang, Pampanga"
  },
  {
    "id": 8,
    "NAME": "Pare, Crisha Joy",
    "TENCENT ID": "5310",
    "DATE HIRED": "2025-06-23",
    "PHONE NAME": "Crisha",
    "NBS ID": "11368",
    "HEADSET SN": "",
    "IBAS": "CRISPARE",
    "DJANGO": "cr.pare@uas2.com.ph",
    "NT LOG IN": "UAS-Pare.Crishajoy",
    "Sales Force": "uas-crishajoy.pare@cict.com.ph",
    "ZOHO": "cr.pare@uas2.com.ph",
    "BSS WEB": "uas-crishajoy.pare@partner.convergeict.com",
    "EMAIL": "Crishapare@gmail.com",
    "BIRTHDAY": "2004-08-16",
    "CONTACT NO.": "09496274867",
    "ADDRESS": "3219 North Dang Bakal, Dau, Mabalacat City, Pampanga"
  },
  {
    "id": 9,
    "NAME": "Paraga, Elisa",
    "TENCENT ID": "5090",
    "DATE HIRED": "2025-04-28",
    "PHONE NAME": "Angel",
    "NBS ID": "10850",
    "HEADSET SN": "2309410DU0875",
    "IBAS": "RAGASELI",
    "DJANGO": "el.paragas@uas2.com.ph",
    "NT LOG IN": "UAS-paragas.elisallo",
    "Sales Force": "uas-elisa.paragas@cict.com.ph",
    "ZOHO": "el.paragas@uas2.com.ph",
    "BSS WEB": "uas-elisa.paragas@partner.convergeict.com",
    "EMAIL": "elp012581@gmail.com",
    "BIRTHDAY": "1981-01-25",
    "CONTACT NO.": "09760221814",
    "ADDRESS": "5016 Abacan, Malabanias, Angeles City, Pampanga"
  },
  {
    "id": 10,
    "NAME": "Cahuyong, Daveliet Jane",
    "TENCENT ID": "5726",
    "DATE HIRED": "2025-08-11",
    "PHONE NAME": "Devie",
    "NBS ID": "11518",
    "HEADSET SN": "",
    "IBAS": "DCAHUYO",
    "DJANGO": "d.cahuyong@uas2.com.ph",
    "NT LOG IN": "UAS-Cahuyong.Davelie",
    "Sales Force": "uas-dave.cahuyog@cict.com.ph",
    "ZOHO": "d.cahuyong@uas2.com.ph",
    "BSS WEB": "uas-dave.cahuyog@partner.convergeict.com",
    "EMAIL": "daveliethitosis@gmail.com",
    "BIRTHDAY": "2002-11-08",
    "CONTACT NO.": "09485518457",
    "ADDRESS": "Prk 6. Kadamay, Brgy. Cuayan, Angeles City, Pampanga"
  },
  {
    "id": 11,
    "NAME": "Quiambao, Allen",
    "TENCENT ID": "4995",
    "DATE HIRED": "2026-05-04",
    "PHONE NAME": "Noble",
    "NBS ID": "12468",
    "HEADSET SN": "",
    "IBAS": "ALQUIAMB",
    "DJANGO": "al.quiambao@uas2.com.ph",
    "NT LOG IN": "UAS-allen.quiambao",
    "Sales Force": "uas-allen.quiambao@cict.com.ph",
    "ZOHO": "al.quiambao@uas2.com.ph",
    "BSS WEB": "uas-allen.quiambao@partner.convergeict.com",
    "EMAIL": "allenquiambao298@gmail.com",
    "BIRTHDAY": "2008-02-09",
    "CONTACT NO.": "09978178943",
    "ADDRESS": "Blk37 Lot20, San Isidro Resettelment, Magalang, Pampanga"
  },
  {
    "id": 12,
    "NAME": "Reyes, Katherine",
    "TENCENT ID": "4996",
    "DATE HIRED": "2026-05-04",
    "PHONE NAME": "Kassel",
    "NBS ID": "12474",
    "HEADSET SN": "",
    "IBAS": "KAREYESE",
    "DJANGO": "ka.reyes@uas2.com.ph",
    "NT LOG IN": "UAS-katherine.reyes",
    "Sales Force": "uas-katherine.reyes@cict.com.ph",
    "ZOHO": "ka.reyes@uas2.com.ph",
    "BSS WEB": "uas-katherine.reyes@partner.convergeict.com",
    "EMAIL": "reyeskatherine093@gmail.com",
    "BIRTHDAY": "2026-09-19",
    "CONTACT NO.": "09614809467",
    "ADDRESS": "1624 Interior St. Brgy. Ninoy Aquino, Marisol, Angeles City, Pampanga"
  },
  {
    "id": 13,
    "NAME": "Salmero, Jeanel Ann",
    "TENCENT ID": "4997",
    "DATE HIRED": "2026-05-04",
    "PHONE NAME": "Rhett",
    "NBS ID": "12476",
    "HEADSET SN": "",
    "IBAS": "JESALMER",
    "DJANGO": "je.salmero@uas2.com.ph",
    "NT LOG IN": "UAS-jeanel.salmero",
    "Sales Force": "uas-jeanel.salmero@cict.com.ph",
    "ZOHO": "je.salmero@uas2.com.ph",
    "BSS WEB": "uas-jeanel.salmero@partner.convergeict.com",
    "EMAIL": "santosjeanel74@gmail.com",
    "BIRTHDAY": "2026-12-15",
    "CONTACT NO.": "09169205580",
    "ADDRESS": "5086 Juicy Fruit, Brgy Duquit, Mabalacat City, Pampanga"
  },
  {
    "id": 14,
    "NAME": "Sampaga, Marie Joy",
    "TENCENT ID": "4998",
    "DATE HIRED": "2026-05-04",
    "PHONE NAME": "Arhem",
    "NBS ID": "12478",
    "HEADSET SN": "",
    "IBAS": "MASAMPAG",
    "DJANGO": "ma.sampaga@uas2.com.ph",
    "NT LOG IN": "UAS-marie.sampaga",
    "Sales Force": "uas-marie.sampaga@cict.com.ph",
    "ZOHO": "ma.sampaga@uas2.com.ph",
    "BSS WEB": "uas-marie.sampaga@partner.convergeict.com",
    "EMAIL": "lacsonmariejoy@gmail.com",
    "BIRTHDAY": "1997-11-15",
    "CONTACT NO.": "09368001203",
    "ADDRESS": "782 Kadenang Kristal, Sapang Biabas, Dau, Mabalacat, Pampanga"
  },
  {
    "id": 15,
    "NAME": "Arcilla, Azarias",
    "TENCENT ID": "4909",
    "DATE HIRED": "2026-05-04",
    "PHONE NAME": "Chance",
    "NBS ID": "12352",
    "HEADSET SN": "J0XL4V",
    "IBAS": "AZARARCI",
    "DJANGO": "a.azarias@uas2.com.ph",
    "NT LOG IN": "UAS-Arcilla.Azarias",
    "Sales Force": "uas-azarias.arcilla@cict.com.ph",
    "ZOHO": "a.azarias@uas2.com.ph",
    "BSS WEB": "uas-azarias.arcilla@partner.convergeict.com",
    "EMAIL": "chancearcilla5100@gmail.com",
    "BIRTHDAY": "2006-05-01",
    "CONTACT NO.": "09122974939",
    "ADDRESS": "989 Chico St. San Francisco, Mabalacat City, Pampanga"
  },
  {
    "id": 16,
    "NAME": "Bigornia, Shenhel",
    "TENCENT ID": "4910",
    "DATE HIRED": "2026-05-04",
    "PHONE NAME": "Daiji",
    "NBS ID": "12360",
    "HEADSET SN": "J0XJP0",
    "IBAS": "SHENBIGO",
    "DJANGO": "s.bigornia@uas2.com.ph",
    "NT LOG IN": "UAS-Bigornia.Shenhel",
    "Sales Force": "uas-shenhel.bigornia@cict.com.ph",
    "ZOHO": "s.bigornia@uas2.com.ph",
    "BSS WEB": "uas-shenhel.bigornia@partner.convergeict.com",
    "EMAIL": "bshenhel@gmail.com",
    "BIRTHDAY": "2002-02-19",
    "CONTACT NO.": "09941644309",
    "ADDRESS": "26-18B Malaysia St. Don Bonifacio, Pulung Maragul, Balibago, Angeles City"
  },
  {
    "id": 17,
    "NAME": "Cano, Regina Carla",
    "TENCENT ID": "4911",
    "DATE HIRED": "2026-05-04",
    "PHONE NAME": "Rachel",
    "NBS ID": "12378",
    "HEADSET SN": "J0XJP3",
    "IBAS": "RCARCANO",
    "DJANGO": "r.cano@uas2.com.ph",
    "NT LOG IN": "UAS-Cano.Regina",
    "Sales Force": "uas-regina.cano@cict.com.ph",
    "ZOHO": "r.cano@uas2.com.ph",
    "BSS WEB": "uas-regina.cano@partner.convergeict.com",
    "EMAIL": "carlacano111517@gmail.com",
    "BIRTHDAY": "1998-11-11",
    "CONTACT NO.": "09069331284",
    "ADDRESS": "05 Mabini St. San Nicolas, Angeles City, Pampanga"
  },
  {
    "id": 18,
    "NAME": "Ocampo, Joana Marie",
    "TENCENT ID": "5269",
    "DATE HIRED": "2026-05-18",
    "PHONE NAME": "Tams",
    "NBS ID": "12578",
    "HEADSET SN": "JOXKVR",
    "IBAS": "JNMRIMCP",
    "DJANGO": "jo.ocampo@uas2.com.ph",
    "NT LOG IN": "UAS-Ocampo.joana",
    "Sales Force": "uas-joana.ocampo@cict.com.ph",
    "ZOHO": "jo.ocampo@uas2.com.p",
    "BSS WEB": "uas-joana.ocampo@partner.convergeict.com",
    "EMAIL": "omanarang30@gmail.com",
    "BIRTHDAY": "1992-08-30",
    "CONTACT NO.": "09491233865",
    "ADDRESS": "49 Purok 1, San Pedro 2, Magalang, Pampanga"
  },
  {
    "id": 19,
    "NAME": "Pangilinan, Princess",
    "TENCENT ID": "5271",
    "DATE HIRED": "2026-05-18",
    "PHONE NAME": "Peach",
    "NBS ID": "12580",
    "HEADSET SN": "JOXKVN",
    "IBAS": "PRNSPGNN",
    "DJANGO": "pr.pangilinan@uas2.com.ph",
    "NT LOG IN": "UAS-Pangilinan.Princ",
    "Sales Force": "uas-prin.pangilinan@cict.com.ph",
    "ZOHO": "pr.pangilinan@uas2.com.ph",
    "BSS WEB": "uas-prin.pangilinan@partner.convergeict.com",
    "EMAIL": "pangilinanp387@gmail.com",
    "BIRTHDAY": "2006-12-19",
    "CONTACT NO.": "09707673225",
    "ADDRESS": "31 D Yakal St. Aguas Subdivision, Manibaug Paralaya, Porac Pampanga"
  }
]

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

def init_db():
    db = get_db()
    cols_def = ", ".join([f'"{c}" TEXT' for c in COLUMNS])
    db.execute(f'CREATE TABLE IF NOT EXISTS agents (id INTEGER PRIMARY KEY AUTOINCREMENT, {cols_def})')
    db.commit()
    cur = db.execute('SELECT COUNT(*) FROM agents')
    if cur.fetchone()[0] == 0 and SEED_DATA:
        for row in SEED_DATA:
            vals = [row.get(c,"") for c in COLUMNS]
            ph = ", ".join(["?"]*len(COLUMNS))
            cq = ", ".join([f'"{c}"' for c in COLUMNS])
            db.execute(f'INSERT INTO agents ({cq}) VALUES ({ph})', vals)
        db.commit()

@app.teardown_appcontext
def close_connection(ex):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

BASE = """
<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1">
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
<link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.0/font/bootstrap-icons.css" rel="stylesheet">
<title>TEAM SHINE M9 - Executive</title>
<style>
body{background:#0f172a;color:#e2e8f0} .navbar{background:linear-gradient(90deg,#0f172a,#1e293b)!important;border-bottom:1px solid #334155}
.card{background:#1e293b;border:1px solid #334155;border-radius:16px} .table{color:#e2e8f0}
.table thead th{background:#0f172a;color:#94a3b8;border-bottom:2px solid #334155;font-size:11px;text-transform:uppercase;letter-spacing:.8px;white-space:nowrap}
.table tbody td{border-color:#1e293b;vertical-align:middle;font-size:13px;white-space:nowrap}
.table-hover tbody tr:hover{background:#0f172a!important} .badge-id{background:#0f172a;border:1px solid #334155;color:#94a3b8}
.btn-exec{background:#fbbf24;color:#0f172a;font-weight:700;border:none} .search-box{background:#0f172a;border:1px solid #334155;color:white}
.detail-card{background:#0f172a;border:1px solid #334155} .field-label{color:#64748b;font-size:11px;text-transform:uppercase;letter-spacing:.8px} .field-value{color:#f1f5f9;font-weight:500}
</style></head><body>
<nav class="navbar navbar-dark p-3 sticky-top"><div class="container-fluid d-flex justify-content-between">
<div class="d-flex align-items-center gap-3"><i class="bi bi-stars fs-4 text-warning"></i><div><div class="fw-bold fs-5">TEAM SHINE M9</div><div style="font-size:11px;color:#94a3b8;letter-spacing:2px">EXECUTIVE SYSTEM - AUTO DB</div></div><span class="badge bg-warning text-dark ms-3">{{count}} AGENTS</span></div>
<div class="d-flex gap-2"><a href="/" class="btn btn-sm btn-outline-light">Dashboard</a><a href="/add" class="btn btn-sm btn-exec">+ Add Agent</a></div>
</div></nav><div class="container-fluid p-4">{{CONTENT}}</div>
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body></html>
"""

def render(content, count=0):
    return BASE.replace("{CONTENT}", content).replace("{count}", str(count))

@app.route("/")
def index():
    init_db()
    q = request.args.get("q","").strip()
    db = get_db()
    if q:
        like = f"%{q}%"
        where = " OR ".join([f'"{c}" LIKE ?' for c in COLUMNS])
        cur = db.execute(f'SELECT * FROM agents WHERE {where} ORDER BY id DESC', [like]*len(COLUMNS))
    else:
        cur = db.execute('SELECT * FROM agents ORDER BY id DESC')
    agents = cur.fetchall()
    rows=""
    for a in agents:
        rows+=f"<tr><td><span class='badge badge-id'>{a['id']}</span></td><td><a href='/view/{a['id']}' class='text-decoration-none'><div class='fw-bold text-white'>{a['NAME'] or ''}</div><div style='font-size:11px;color:#94a3b8'>{a['NBS ID'] or ''} • {a['TENCENT ID'] or ''}</div></a></td><td>{a['TENCENT ID'] or ''}</td><td>{a['PHONE NAME'] or ''}</td><td><code style='color:#fbbf24'>{a['HEADSET SN'] or ''}</code></td><td>{a['IBAS'] or ''}</td><td>{a['DJANGO'] or ''}</td><td>{a['NT LOG IN'] or ''}</td><td>{a['Sales Force'] or ''}</td><td>{a['ZOHO'] or ''}</td><td>{a['BSS WEB'] or ''}</td><td>{a['DATE HIRED'] or ''}</td><td style='max-width:150px;overflow:hidden;text-overflow:ellipsis'>{a['EMAIL'] or ''}</td><td>{a['BIRTHDAY'] or ''}</td><td>{a['ADDRESS'] or ''}</td><td>{a['CONTACT NO.'] or ''}</td><td><a href='/view/{a['id']}' class='btn btn-sm btn-outline-light'><i class='bi bi-eye'></i></a> <a href='/edit/{a['id']}' class='btn btn-sm btn-outline-warning'><i class='bi bi-pencil'></i></a></td></tr>"
    content=f"<div class='card p-3 mb-3'><form class='d-flex gap-2' method='get'><div class='input-group'><span class='input-group-text' style='background:#0f172a;border:1px solid #334155;color:#94a3b8'><i class='bi bi-search'></i></span><input name='q' value='{q}' class='form-control search-box' placeholder='Search all 16 fields...'></div><button class='btn btn-light'>Search</button></form></div><div class='card p-0 overflow-hidden'><div class='table-responsive'><table class='table table-hover mb-0'><thead><tr><th>ID</th><th>Agent</th><th>Tencent</th><th>Phone</th><th>Headset</th><th>IBAS</th><th>Django</th><th>NT Login</th><th>SalesForce</th><th>ZOHO</th><th>BSS</th><th>Hired</th><th>Email</th><th>Bday</th><th>Address</th><th>Contact</th><th>Action</th></tr></thead><tbody>{rows if rows else '<tr><td colspan=17 class=text-center p-5>Empty</td></tr>'}</tbody></table></div></div><div class='mt-2' style='color:#475569;font-size:11px'>AUTO DB Active - data embedded • Scroll sideways for all fields • Click name for full profile</div>"
    return render(content, len(agents))

@app.route("/view/<int:aid>")
def view(aid):
    init_db()
    db=get_db()
    a=db.execute('SELECT * FROM agents WHERE id=?',(aid,)).fetchone()
    if not a: return redirect("/")
    fields=""
    for c in COLUMNS:
        fields+=f"<div class='col-md-6 mb-3'><div class='detail-card p-3 rounded-3 h-100'><div class='field-label mb-1'>{c}</div><div class='field-value'>{a[c] or '<span style=color:#334155>— empty —</span>'}</div></div></div>"
    content=f"<a href='/' class='btn btn-sm btn-outline-light mb-3'>Back</a><div class='row'><div class='col-md-4'><div class='card p-4 text-center'><div style='width:80px;height:80px;background:linear-gradient(135deg,#fbbf24,#f59e0b);border-radius:20px;display:flex;align-items:center;justify-content:center;margin:0 auto 16px;font-size:32px;font-weight:800;color:#0f172a'>{(a['NAME'] or 'A')[0]}</div><div class='fw-bold fs-4 text-white'>{a['NAME'] or ''}</div><div class='field-label'>{a['NBS ID'] or ''}</div><hr style='border-color:#334155'><div class='d-flex justify-content-between text-start'><div><div class='field-label'>Tencent</div><div class='field-value'>{a['TENCENT ID'] or ''}</div></div><div><div class='field-label'>Hired</div><div class='field-value'>{a['DATE HIRED'] or ''}</div></div></div><div class='d-grid gap-2 mt-4'><a href='/edit/{a['id']}' class='btn btn-warning fw-bold'>Edit</a><form method='post' action='/delete/{a['id']}' onsubmit="return confirm('Delete?')"><button class='btn btn-outline-danger w-100'>Delete</button></form></div></div></div><div class='col-md-8'><div class='card p-4'><h5 class='fw-bold text-white mb-3'>Full Details - 16 Fields</h5><div class='row'>{fields}</div></div></div></div>"
    cnt=db.execute('SELECT COUNT(*) FROM agents').fetchone()[0]
    return render(content, cnt)

@app.route("/add", methods=["GET","POST"])
@app.route("/edit/<int:aid>", methods=["GET","POST"])
def add_edit(aid=None):
    init_db()
    db=get_db()
    ag=None
    if aid:
        ag=db.execute('SELECT * FROM agents WHERE id=?',(aid,)).fetchone()
    if request.method=="POST":
        vals=[request.form.get(c,"") for c in COLUMNS]
        if aid:
            sc=", ".join([f'"{c}"=?' for c in COLUMNS])
            db.execute(f'UPDATE agents SET {sc} WHERE id=?', vals+[aid])
        else:
            ph=", ".join(["?"]*len(COLUMNS))
            cq=", ".join([f'"{c}"' for c in COLUMNS])
            db.execute(f'INSERT INTO agents ({cq}) VALUES ({ph})', vals)
        db.commit()
        return redirect(f"/view/{aid}" if aid else "/")
    f=""
    for c in COLUMNS:
        v=ag[c] if ag else ""
        f+=f"<div class='col-md-6 mb-3'><label class='field-label mb-1'>{c}</label><input name='{c}' value='{v}' class='form-control' style='background:#0f172a;border:1px solid #334155;color:white'></div>"
    title="Edit Agent" if aid else "Add New Agent"
    content=f"<a href='/' class='btn btn-sm btn-outline-light mb-3'>Back</a><div class='card p-4'><h4 class='fw-bold text-white mb-4'>{title}</h4><form method='post' class='row'>{f}<div class='col-12 mt-3'><button class='btn btn-warning fw-bold px-5'>Save</button></div></form></div>"
    cnt=db.execute('SELECT COUNT(*) FROM agents').fetchone()[0]
    return render(content, cnt)

@app.route("/delete/<int:aid>", methods=["POST"])
def delete(aid):
    init_db()
    db=get_db()
    db.execute('DELETE FROM agents WHERE id=?',(aid,))
    db.commit()
    return redirect("/")

if __name__=="__main__":
    port=int(os.environ.get("PORT",5000))
    app.run(host="0.0.0.0",port=port)
