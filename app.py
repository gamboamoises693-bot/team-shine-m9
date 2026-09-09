
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
