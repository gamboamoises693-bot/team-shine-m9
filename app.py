
from flask import Flask
app = Flask(__name__)

@app.route("/")
def index():
    return """
    <h1>TEAM SHINE M9 - Emergency Mode LIVE ✅</h1>
    <p>502 Fixed! Ngayon ayusin natin Firebase.</p>
    <p><b>Next:</b> Punta ka Render -> Logs -> screenshot mo yung pula na error</p>
    <p>Tapos punta ka Environment Variables -> check kung may FIREBASE_CREDENTIALS</p>
    <a href="/ping">Ping Test</a>
    """

@app.route("/ping")
def ping():
    return "alive", 200

@app.route("/dashboard")
def dash():
    return "<h1>Dashboard - Emergency Mode</h1><a href='/'>Home</a>"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
