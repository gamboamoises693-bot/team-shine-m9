
import os, json, time
from flask import Flask, request, redirect
app = Flask(__name__)

# Try firebase, but don't crash if fail
FIREBASE_OK = False
DB_URL = os.environ.get("FIREBASE_DATABASE_URL","")
try:
    import firebase_admin
    from firebase_admin import credentials, db, firestore
    if not firebase_admin._apps:
        if os.path.exists("serviceAccountKey.json"):
            cred = credentials.Certificate("serviceAccountKey.json")
            firebase_admin.initialize_app(cred, {"databaseURL": DB_URL} if DB_URL else {})
            FIREBASE_OK = True
        elif os.environ.get("FIREBASE_CREDENTIALS"):
            cdict = json.loads(os.environ.get("FIREBASE_CREDENTIALS"))
            cred = credentials.Certificate(cdict)
            firebase_admin.initialize_app(cred, {"databaseURL": DB_URL} if DB_URL else {})
            FIREBASE_OK = True
except Exception as e:
    print("Firebase init failed:", e)
    FIREBASE_OK = False

@app.route("/")
def index():
    if not FIREBASE_OK:
        return f"""
        <h1>Firebase Not Connected</h1>
        <p>DB_URL set: {bool(DB_URL)}</p>
        <p>DB_URL value: {DB_URL[:50] if DB_URL else 'EMPTY'}</p>
        <p>CRED exists: {bool(os.environ.get('FIREBASE_CREDENTIALS') or os.path.exists('serviceAccountKey.json'))}</p>
        <p>Go to Render -> Environment -> Add FIREBASE_DATABASE_URL</p>
        <p>Value: https://team-shine-m9-default-rtdb.asia-southeast1.firebasedatabase.app</p>
        """
    # if ok, load data
    try:
        ref = db.reference("team_shine_m9/agents")
        agents = ref.get() or {}
        return f"<h1>REALTIME LIVE! {len(agents)} agents</h1><p>Super fast na boss!</p><a href='/ping'>Ping</a>"
    except Exception as e:
        return f"<h1>Error loading: {e}</h1>"

@app.route("/ping")
def ping():
    return "alive", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",5000)))
