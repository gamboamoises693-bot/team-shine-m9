
import os, json, re
from flask import Flask
app = Flask(__name__)

def sanitize(k):
    if not k:
        return "FIELD"
    k = re.sub(r'[\.\$\#\[\]\/]', '_', k)
    k = k.strip().replace(" ", "_")
    k = re.sub(r'_+', '_', k)
    return k or "FIELD"

FIREBASE_MODE = "none"
db_root = None
err = ""
try:
    import firebase_admin
    from firebase_admin import credentials, db
    if not firebase_admin._apps:
        if os.path.exists("serviceAccountKey.json"):
            cred = credentials.Certificate("serviceAccountKey.json")
            firebase_admin.initialize_app(cred, {"databaseURL": os.environ.get("FIREBASE_DATABASE_URL")})
        elif os.environ.get("FIREBASE_CREDENTIALS"):
            cdict = json.loads(os.environ.get("FIREBASE_CREDENTIALS"))
            cred = credentials.Certificate(cdict)
            firebase_admin.initialize_app(cred, {"databaseURL": os.environ.get("FIREBASE_DATABASE_URL")})
    db_root = db.reference("team_shine_m9")
    FIREBASE_MODE = "realtime"
except Exception as e:
    err = str(e)

OLD_AGENTS = [{"id": 1, "NAME": "Bernaldo, Catherine", "TENCENT ID": "5116", "DATE HIRED": "2025-03-31", "PHONE NAME": "HOPE", "NBS ID": "10116", "HEADSET SN": "2309410DUO286", "IBAS": "CATBERNA", "DJANGO": "cabernaldo@uas2.com.ph", "NT LOG IN": "UAS-Bernaldo.Catheri", "Sales Force": "uas-bernaldo.cath@cict.com.ph", "ZOHO": "c.bernaldo@uas2.com.ph", "BSS WEB": "uas-bernaldo.cath@partner.convergeict.com", "EMAIL": "bernaldocatherine2@gmail.com", "BIRTHDAY": "1992-08-03", "CONTACT NO.": "09468168239", "ADDRESS": "15-C Feliza St. Brgy.Malabanias, Angeles City, Pampanga"}, {"id": 2, "NAME": "Lopez, Eljay", "TENCENT ID": "5243", "DATE HIRED": "2025-04-14", "PHONE NAME": "SOJI", "NBS ID": "10752", "HEADSET SN": "2309410DU1324", "IBAS": "", "DJANGO": "eljhay.lopez@uas2.com.ph", "NT LOG IN": "UAS-Lopez.eljhay", "Sales Force": "uas-lopez.eljay@cict.com.ph", "ZOHO": "eljhay.lopez@uas2.com.ph", "BSS WEB": "uas-lopez.eljay@partner.convergeict.com", "EMAIL": "is.eljaylopez1@gmail.com", "BIRTHDAY": "1999-11-02", "CONTACT NO.": "09666096553", "ADDRESS": "Blk 5 Lot 14 Rockville Subdivision, Barangay Malpitic, City of San Fernando, Pamapanga"}, {"id": 3, "NAME": "Maniago, Danzeil James", "TENCENT ID": "5242", "DATE HIRED": "2025-03-31", "PHONE NAME": "Danzeil", "NBS ID": "10148", "HEADSET SN": "2309410DU0522", "IBAS": "DAJMANIA", "DJANGO": "Damaniago@uas2.com.ph", "NT LOG IN": "UAS-Maniago.Danzeil", "Sales Force": "uas-danzeil.maniago@cict.com.ph", "ZOHO": "damaniago@uas2.com.ph", "BSS WEB": "uas-danzeil.maniago@partner.convergeict.com", "EMAIL": "denzeiljamesmaniago@gmail.com", "BIRTHDAY": "2003-01-16", "CONTACT NO.": "09630692546", "ADDRESS": "Blk.17 Lot.2, Brgy. Cristo Rey, Capas, Tarlac"}, {"id": 4, "NAME": "Navarro, Jerome", "TENCENT ID": "5093", "DATE HIRED": "2025-03-03", "PHONE NAME": "KHALEE", "NBS ID": "9808", "HEADSET SN": "2309410DU0098", "IBAS": "NAVJEROM", "DJANGO": "je.navarro@uas2.com.ph", "NT LOG IN": "UAS-Navarro.Jerome", "Sales Force": "uas-jerome.navarro@cict.com.ph", "ZOHO": "je.navarro@uas2.com.ph", "BSS WEB": "uas-jerome.navarro@partner.convergeict.com", "EMAIL": "jeromen891@gmail.com", "BIRTHDAY": "1998-04-16", "CONTACT NO.": "09670696382", "ADDRESS": "1036, Baranggay Capaya 1, Angeles City, Pampanga"}, {"id": 5, "NAME": "Paz, Ben Gerard", "TENCENT ID": "5038", "DATE HIRED": "2025-03-03", "PHONE NAME": "GIEH", "NBS ID": "9814", "HEADSET SN": "2309410DU0381", "IBAS": "PAZBENGE", "DJANGO": "bg.paz@uas2.com.ph", "NT LOG IN": "UAS-Paz.Ben", "Sales Force": "uas-ben.paz@cict.com.ph", "ZOHO": "bg.paz@uas2.com.ph", "BSS WEB": "uas-ben.paz@partner.convergeict.com", "EMAIL": "bengerardp@gmail.com", "BIRTHDAY": "1995-06-25", "CONTACT NO.": "09634269072", "ADDRESS": "Pulung Maragul, Angeles City"}, {"id": 6, "NAME": "Waje, Avy", "TENCENT ID": "5115", "DATE HIRED": "2025-03-03", "PHONE NAME": "SCARLET", "NBS ID": "9828", "HEADSET SN": "2309410DU1246", "IBAS": "WAJAVYWA", "DJANGO": "a.waje@uas2.com.ph", "NT LOG IN": "UAS-Waje.Avy", "Sales Force": "uas-avy.waje@cict.com.ph", "ZOHO": "a.waje@uas2.com.ph", "BSS WEB": "uas-avy.waje@partner.convergeict.com", "EMAIL": "avywaje43@gmail.com", "BIRTHDAY": "2005-01-16", "CONTACT NO.": "09534367262", "ADDRESS": "0366 Purok 2, Brgy. Calzadang Bayu, Porac, Pampanga"}, {"id": 7, "NAME": "Guevarra, James Rainielle", "TENCENT ID": "5291", "DATE HIRED": "2025-06-23", "PHONE NAME": "Rain", "NBS ID": "11412", "HEADSET SN": "", "IBAS": "JMSRNGVA", "DJANGO": "ja.guevarra@uas2.com.ph", "NT LOG IN": "UAS-Guevarra.JamesRa", "Sales Force": "uas-rain.guevarra@cict.com.ph", "ZOHO": "ja.guevarra@uas2.com.ph", "BSS WEB": "uas-rain.guevarra@partner.convergeict.com", "EMAIL": "jamesrainielle1423@gmail.com", "BIRTHDAY": "2006-08-31", "CONTACT NO.": "09480624706", "ADDRESS": "Blk cd Lot 2c phase 3, Sta. Lucia Rest., Brgy. San Isido, Magalang, Pampanga"}, {"id": 8, "NAME": "Pare, Crisha Joy", "TENCENT ID": "5310", "DATE HIRED": "2025-06-23", "PHONE NAME": "Crisha", "NBS ID": "11368", "HEADSET SN": "", "IBAS": "CRISPARE", "DJANGO": "cr.pare@uas2.com.ph", "NT LOG IN": "UAS-Pare.Crishajoy", "Sales Force": "uas-crishajoy.pare@cict.com.ph", "ZOHO": "cr.pare@uas2.com.ph", "BSS WEB": "uas-crishajoy.pare@partner.convergeict.com", "EMAIL": "Crishapare@gmail.com", "BIRTHDAY": "2004-08-16", "CONTACT NO.": "09496274867", "ADDRESS": "3219 North Dang Bakal, Dau, Mabalacat City, Pampanga"}, {"id": 9, "NAME": "Paraga, Elisa", "TENCENT ID": "5090", "DATE HIRED": "2025-04-28", "PHONE NAME": "Angel", "NBS ID": "10850", "HEADSET SN": "2309410DU0875", "IBAS": "RAGASELI", "DJANGO": "el.paragas@uas2.com.ph", "NT LOG IN": "UAS-paragas.elisallo", "Sales Force": "uas-elisa.paragas@cict.com.ph", "ZOHO": "el.paragas@uas2.com.ph", "BSS WEB": "uas-elisa.paragas@partner.convergeict.com", "EMAIL": "elp012581@gmail.com", "BIRTHDAY": "1981-01-25", "CONTACT NO.": "09760221814", "ADDRESS": "5016 Abacan, Malabanias, Angeles City, Pampanga"}, {"id": 10, "NAME": "Cahuyong, Daveliet Jane", "TENCENT ID": "5726", "DATE HIRED": "2025-08-11", "PHONE NAME": "Devie", "NBS ID": "11518", "HEADSET SN": "", "IBAS": "DCAHUYO", "DJANGO": "d.cahuyong@uas2.com.ph", "NT LOG IN": "UAS-Cahuyong.Davelie", "Sales Force": "uas-dave.cahuyog@cict.com.ph", "ZOHO": "d.cahuyong@uas2.com.ph", "BSS WEB": "uas-dave.cahuyog@partner.convergeict.com", "EMAIL": "daveliethitosis@gmail.com", "BIRTHDAY": "2002-11-08", "CONTACT NO.": "09485518457", "ADDRESS": "Prk 6. Kadamay, Brgy. Cuayan, Angeles City, Pampanga"}, {"id": 11, "NAME": "Quiambao, Allen", "TENCENT ID": "4995", "DATE HIRED": "2026-05-04", "PHONE NAME": "Noble", "NBS ID": "12468", "HEADSET SN": "", "IBAS": "ALQUIAMB", "DJANGO": "al.quiambao@uas2.com.ph", "NT LOG IN": "UAS-allen.quiambao", "Sales Force": "uas-allen.quiambao@cict.com.ph", "ZOHO": "al.quiambao@uas2.com.ph", "BSS WEB": "uas-allen.quiambao@partner.convergeict.com", "EMAIL": "allenquiambao298@gmail.com", "BIRTHDAY": "2008-02-09", "CONTACT NO.": "09978178943", "ADDRESS": "Blk37 Lot20, San Isidro Resettelment, Magalang, Pampanga"}, {"id": 12, "NAME": "Reyes, Katherine", "TENCENT ID": "4996", "DATE HIRED": "2026-05-04", "PHONE NAME": "Kassel", "NBS ID": "12474", "HEADSET SN": "", "IBAS": "KAREYESE", "DJANGO": "ka.reyes@uas2.com.ph", "NT LOG IN": "UAS-katherine.reyes", "Sales Force": "uas-katherine.reyes@cict.com.ph", "ZOHO": "ka.reyes@uas2.com.ph", "BSS WEB": "uas-katherine.reyes@partner.convergeict.com", "EMAIL": "reyeskatherine093@gmail.com", "BIRTHDAY": "2026-09-19", "CONTACT NO.": "09614809467", "ADDRESS": "1624 Interior St. Brgy. Ninoy Aquino, Marisol, Angeles City, Pampanga"}, {"id": 13, "NAME": "Salmero, Jeanel Ann", "TENCENT ID": "4997", "DATE HIRED": "2026-05-04", "PHONE NAME": "Rhett", "NBS ID": "12476", "HEADSET SN": "", "IBAS": "JESALMER", "DJANGO": "je.salmero@uas2.com.ph", "NT LOG IN": "UAS-jeanel.salmero", "Sales Force": "uas-jeanel.salmero@cict.com.ph", "ZOHO": "je.salmero@uas2.com.ph", "BSS WEB": "uas-jeanel.salmero@partner.convergeict.com", "EMAIL": "santosjeanel74@gmail.com", "BIRTHDAY": "2026-12-15", "CONTACT NO.": "09169205580", "ADDRESS": "5086 Juicy Fruit, Brgy Duquit, Mabalacat City, Pampanga"}, {"id": 14, "NAME": "Sampaga, Marie Joy", "TENCENT ID": "4998", "DATE HIRED": "2026-05-04", "PHONE NAME": "Arhem", "NBS ID": "12478", "HEADSET SN": "", "IBAS": "MASAMPAG", "DJANGO": "ma.sampaga@uas2.com.ph", "NT LOG IN": "UAS-marie.sampaga", "Sales Force": "uas-marie.sampaga@cict.com.ph", "ZOHO": "ma.sampaga@uas2.com.ph", "BSS WEB": "uas-marie.sampaga@partner.convergeict.com", "EMAIL": "lacsonmariejoy@gmail.com", "BIRTHDAY": "1997-11-15", "CONTACT NO.": "09368001203", "ADDRESS": "782 Kadenang Kristal, Sapang Biabas, Dau, Mabalacat, Pampanga"}, {"id": 15, "NAME": "Arcilla, Azarias", "TENCENT ID": "4909", "DATE HIRED": "2026-05-04", "PHONE NAME": "Chance", "NBS ID": "12352", "HEADSET SN": "J0XL4V", "IBAS": "AZARARCI", "DJANGO": "a.azarias@uas2.com.ph", "NT LOG IN": "UAS-Arcilla.Azarias", "Sales Force": "uas-azarias.arcilla@cict.com.ph", "ZOHO": "a.azarias@uas2.com.ph", "BSS WEB": "uas-azarias.arcilla@partner.convergeict.com", "EMAIL": "chancearcilla5100@gmail.com", "BIRTHDAY": "2006-05-01", "CONTACT NO.": "09122974939", "ADDRESS": "989 Chico St. San Francisco, Mabalacat City, Pampanga"}, {"id": 16, "NAME": "Bigornia, Shenhel", "TENCENT ID": "4910", "DATE HIRED": "2026-05-04", "PHONE NAME": "Daiji", "NBS ID": "12360", "HEADSET SN": "J0XJP0", "IBAS": "SHENBIGO", "DJANGO": "s.bigornia@uas2.com.ph", "NT LOG IN": "UAS-Bigornia.Shenhel", "Sales Force": "uas-shenhel.bigornia@cict.com.ph", "ZOHO": "s.bigornia@uas2.com.ph", "BSS WEB": "uas-shenhel.bigornia@partner.convergeict.com", "EMAIL": "bshenhel@gmail.com", "BIRTHDAY": "2002-02-19", "CONTACT NO.": "09941644309", "ADDRESS": "26-18B Malaysia St. Don Bonifacio, Pulung Maragul, Balibago, Angeles City"}, {"id": 17, "NAME": "Cano, Regina Carla", "TENCENT ID": "4911", "DATE HIRED": "2026-05-04", "PHONE NAME": "Rachel", "NBS ID": "12378", "HEADSET SN": "J0XJP3", "IBAS": "RCARCANO", "DJANGO": "r.cano@uas2.com.ph", "NT LOG IN": "UAS-Cano.Regina", "Sales Force": "uas-regina.cano@cict.com.ph", "ZOHO": "r.cano@uas2.com.ph", "BSS WEB": "uas-regina.cano@partner.convergeict.com", "EMAIL": "carlacano111517@gmail.com", "BIRTHDAY": "1998-11-11", "CONTACT NO.": "09069331284", "ADDRESS": "05 Mabini St. San Nicolas, Angeles City, Pampanga"}, {"id": 18, "NAME": "Ocampo, Joana Marie", "TENCENT ID": "5269", "DATE HIRED": "2026-05-18", "PHONE NAME": "Tams", "NBS ID": "12578", "HEADSET SN": "JOXKVR", "IBAS": "JNMRIMCP", "DJANGO": "jo.ocampo@uas2.com.ph", "NT LOG IN": "UAS-Ocampo.joana", "Sales Force": "uas-joana.ocampo@cict.com.ph", "ZOHO": "jo.ocampo@uas2.com.p", "BSS WEB": "uas-joana.ocampo@partner.convergeict.com", "EMAIL": "omanarang30@gmail.com", "BIRTHDAY": "1992-08-30", "CONTACT NO.": "09491233865", "ADDRESS": "49 Purok 1, San Pedro 2, Magalang, Pampanga"}, {"id": 19, "NAME": "Pangilinan, Princess", "TENCENT ID": "5271", "DATE HIRED": "2026-05-18", "PHONE NAME": "Peach", "NBS ID": "12580", "HEADSET SN": "JOXKVN", "IBAS": "PRNSPGNN", "DJANGO": "pr.pangilinan@uas2.com.ph", "NT LOG IN": "UAS-Pangilinan.Princ", "Sales Force": "uas-prin.pangilinan@cict.com.ph", "ZOHO": "pr.pangilinan@uas2.com.ph", "BSS WEB": "uas-prin.pangilinan@partner.convergeict.com", "EMAIL": "pangilinanp387@gmail.com", "BIRTHDAY": "2006-12-19", "CONTACT NO.": "09707673225", "ADDRESS": "31 D Yakal St. Aguas Subdivision, Manibaug Paralaya, Porac Pampanga"}]

@app.route("/")
def index():
    return f"Mode: {FIREBASE_MODE} Err: {err}<br><a href='/migrate_now'>Migrate 19 (fixed keys)</a> | <a href='/check'>Check</a> | <a href='/clear'>Clear</a>"

@app.route("/check")
def check():
    try:
        data = db_root.child("agents").get() or {}
        html = f"Has {len(data)} agents<br>"
        for aid, val in list(data.items())[:3]:
            html+= f"{aid}: {str(val.get('NAME',''))}<br>"
        html+= "<br><a href='/'>Home</a>"
        return html
    except Exception as e:
        return f"Error: {e}"

@app.route("/clear")
def clear():
    db_root.child("agents").delete()
    return "Cleared <a href='/migrate_now'>Migrate now</a>"

@app.route("/migrate_now")
def migrate_now():
    try:
        count=0
        for ag in OLD_AGENTS:
            aid = str(ag.get("id"))
            clean = {}
            for k,v in ag.items():
                if k=="id": continue
                sk = sanitize(k)
                clean[sk] = "" if v is None else str(v)
            # add standard fields for app
            clean["_ot_total"]=0
            clean["_loss_total"]=0
            # keep original NAME mapping for compatibility
            # map sanitized back to expected fields in final app
            # final app will read both sanitized and original
            db_root.child(f"agents/{aid}").set(clean)
            count+=1
        return f"<h1>DONE Fixed! {count} agents migrated with safe keys!</h1><br>Fields now: NAME, TENCENT_ID, CONTACT_NO_, etc (no dots)<br><a href='/check'>Check</a><br>Next upload FINAL app v2 that reads sanitized keys"
    except Exception as e:
        import traceback
        return f"<pre>{e}\n{traceback.format_exc()}</pre>"

@app.route("/ping")
def ping():
    return "alive"

if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",5000)))
