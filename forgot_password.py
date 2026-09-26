# forgot_password.py
# Self-service "Forgot Password" for the Admin / Team Leader / QA accounts
# (the ones in app.py's hardcoded USERS dict). This app has no email/SMS
# setup, so there is no "send me a reset link" flow possible. Instead this
# uses a MASTER RECOVERY KEY — a secret only the owner knows, set as a
# Render environment variable — to prove identity before allowing a new
# password to be set.
#
# How it works:
#   1. You set RESET_MASTER_KEY as an environment variable on Render
#      (Settings -> Environment). Pick your own long random value — this
#      key is what lets you regain access, so treat it like a password.
#   2. On /forgot_password, you pick which account to reset (admin/tl/qa),
#      enter the Master Recovery Key, and set a new password.
#   3. The new password is stored in Firebase under "admin_credentials" —
#      NOT in the code — so it survives restarts/redeploys and overrides
#      the hardcoded default in app.py's USERS dict from then on.
#
# This file only ADDS a new route. It does not remove or rewrite anything
# in app.py. app.py needs two small, separate changes to actually use the
# stored overrides (see the patch notes at the bottom of this file).

import os
from datetime import datetime
from flask import request, redirect, session

from app import app, db_root, PH_TZ, page

RESET_MASTER_KEY = os.environ.get("RESET_MASTER_KEY", "")


def get_password_override(username):
    """Returns the Firebase-stored password for this account, or None if
    it has never been reset (meaning app.py's hardcoded default applies)."""
    try:
        if not db_root:
            return None
        val = db_root.child(f"admin_credentials/{username}").get()
        if isinstance(val, dict):
            return val.get("password")
        return None
    except Exception:
        return None


def set_password_override(username, new_password):
    try:
        if not db_root:
            return False
        db_root.child(f"admin_credentials/{username}").set({
            "password": new_password,
            "updated_at": datetime.now(PH_TZ).strftime("%Y-%m-%d %I:%M %p"),
        })
        return True
    except Exception:
        return False


FORGOT_PAGE_TEMPLATE = """<html><head><meta name="viewport" content="width=device-width,initial-scale=1">
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
<style>body{{background:#0b1120;display:flex;align-items:center;justify-content:center;min-height:100vh;color:#f1f5f9}}.login-card{{background:#151e32;border:1px solid #2d3748;border-radius:20px;padding:32px;max-width:420px;width:90%}}.logo{{width:70px;height:70px;background:linear-gradient(135deg,#fbbf24,#f59e0b);border-radius:16px;display:flex;align-items:center;justify-content:center;font-size:32px;font-weight:900;color:#111827;margin:0 auto 16px}}input,select{{background:#0f172a!important;color:#f1f5f9!important;border:1px solid #334155!important;border-radius:10px!important;padding:12px!important}}</style></head><body>
<div class="login-card text-center">
  <div class="logo">S9</div>
  <h4 style="color:white">Forgot Password</h4>
  <small style="color:#94a3b8">Reset an Admin / Team Leader / QA account</small>
  {no_key_warning}
  <form method="POST" class="mt-4 text-start">
    <label style="font-size:11px;color:#94a3b8">ACCOUNT TO RESET</label>
    <select name="username" class="form-select mb-3" required>
      <option value="">Select account...</option>
      <option value="admin">admin (Admin)</option>
      <option value="tl">tl (Team Leader)</option>
      <option value="qa">qa (QA Specialist)</option>
    </select>
    <label style="font-size:11px;color:#94a3b8">MASTER RECOVERY KEY</label>
    <input name="master_key" type="password" class="form-control mb-3" required>
    <label style="font-size:11px;color:#94a3b8">NEW PASSWORD</label>
    <input name="new_password" type="password" class="form-control mb-3" minlength="6" required>
    <label style="font-size:11px;color:#94a3b8">CONFIRM NEW PASSWORD</label>
    <input name="confirm_password" type="password" class="form-control mb-3" minlength="6" required>
    <div style="color:{msg_color};font-size:12px;margin-bottom:12px">{message}</div>
    <button class="btn btn-warning w-100" style="font-weight:700;padding:12px">Reset Password</button>
    <div class="mt-3 text-center"><a href="/login" style="color:#94a3b8;font-size:12px">Back to Login</a></div>
  </form>
</div>
</body></html>"""


@app.route("/forgot_password", methods=["GET", "POST"])
def forgot_password():
    message = ""
    msg_color = "#ef4444"

    no_key_warning = ""
    if not RESET_MASTER_KEY:
        no_key_warning = (
            "<div style='background:#451a03;border:1px solid #f59e0b;border-radius:10px;"
            "padding:10px;margin-top:14px;font-size:11px;color:#fbbf24;text-align:left'>"
            "⚠️ No RESET_MASTER_KEY is set on this deployment yet. Set it under Render → "
            "Settings → Environment before this page can be used.</div>"
        )

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        master_key = request.form.get("master_key", "")
        new_password = request.form.get("new_password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not RESET_MASTER_KEY:
            message = "Password reset is not configured yet (missing RESET_MASTER_KEY). Contact whoever deployed this app."
        elif username not in ("admin", "tl", "qa"):
            message = "Please select a valid account."
        elif master_key != RESET_MASTER_KEY:
            message = "Incorrect Master Recovery Key."
        elif len(new_password) < 6:
            message = "New password must be at least 6 characters."
        elif new_password != confirm_password:
            message = "Passwords do not match."
        else:
            ok = set_password_override(username, new_password)
            if ok:
                # Log the reset for an audit trail, same pattern as login/logout logs.
                try:
                    if db_root:
                        db_root.child("login_logs").push({
                            "user": username, "name": username, "role": "admin",
                            "type": "PASSWORD_RESET",
                            "timestamp": datetime.now(PH_TZ).strftime("%Y-%m-%d %I:%M:%S %p"),
                            "date": datetime.now(PH_TZ).strftime("%Y-%m-%d"),
                            "agent_id": "ADMIN",
                        })
                except Exception:
                    pass
                return page(
                    f"<div class='card-dark' style='max-width:420px;margin:60px auto;text-align:center'>"
                    f"<h5 style='color:#22c55e'>✅ Password Reset</h5>"
                    f"<p style='color:var(--text2)'>The password for <b>{username}</b> has been updated. "
                    f"You can log in with it now.</p>"
                    f"<a href='/login' class='btn btn-warning w-100 mt-2'>Go to Login</a></div>"
                )
            else:
                message = "Could not save the new password (database unavailable). Try again in a moment."

    return FORGOT_PAGE_TEMPLATE.format(
        message=message, msg_color=msg_color, no_key_warning=no_key_warning,
    )
