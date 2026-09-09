# coaching.py
# Coaching Minutes feature — logs coaching sessions per agent, displayed on
# each agent's individual page (/view/<aid>), with an announcement-style
# read-receipt so the agent can confirm they received the coaching.
#
# This file is self-contained. It imports the shared app/db/helpers from
# app.py and registers its own routes on the same Flask app instance.
# app.py only needs one line at the bottom (`import coaching`) to load it.

import uuid
from datetime import datetime
from flask import request, redirect, session

from app import app, db_root, login_required, PH_TZ

CATEGORY_COLORS = {
    "Performance": "#8b5cf6",
    "Behavior": "#f97316",
    "Attendance": "#ef4444",
    "Quality": "#06b6d4",
    "Product Knowledge": "#22c55e",
    "Other": "#94a3b8",
}


# ---------- Data helpers ----------

def get_coaching(aid):
    """All coaching sessions for one agent, newest first."""
    try:
        raw = db_root.child("coaching_logs").get() if db_root else None
        res = []
        if isinstance(raw, dict):
            for cid, v in raw.items():
                if isinstance(v, dict) and str(v.get("agent_id")) == str(aid):
                    v["id"] = cid
                    res.append(v)
        res.sort(key=lambda x: (x.get("date", ""), x.get("created_at", "")), reverse=True)
        return res
    except Exception:
        return []


def get_coaching_reads():
    try:
        raw = db_root.child("coaching_reads").get() if db_root else None
        res = []
        if isinstance(raw, dict):
            for rid, v in raw.items():
                if isinstance(v, dict):
                    v["id"] = rid
                    res.append(v)
        return res
    except Exception:
        return []


def get_read_for(coaching_id):
    """Returns the read-receipt record for a coaching entry, or None."""
    for r in get_coaching_reads():
        if str(r.get("coaching_id")) == str(coaching_id):
            return r
    return None


# ---------- Routes ----------

@app.route("/add_coaching/<aid>", methods=["POST"])
@login_required
def add_coaching(aid):
    if session.get("role") == "agent":
        return redirect(f"/view/{aid}")
    try:
        category = request.form.get("category", "Other")
        notes = request.form.get("notes", "").strip()
        action_items = request.form.get("action_items", "").strip()
        date = request.form.get("date") or datetime.now(PH_TZ).strftime("%Y-%m-%d")
        if not notes:
            return redirect(f"/view/{aid}")
        if db_root:
            cid = str(uuid.uuid4())[:8]
            db_root.child(f"coaching_logs/{cid}").set({
                "id": cid,
                "agent_id": aid,
                "category": category,
                "notes": notes,
                "action_items": action_items,
                "coach": session.get("name", "TL"),
                "date": date,
                "created_at": datetime.now(PH_TZ).strftime("%Y-%m-%d %I:%M %p"),
            })
    except Exception:
        pass
    return redirect(f"/view/{aid}")


@app.route("/delete_coaching/<aid>/<cid>")
@login_required
def delete_coaching(aid, cid):
    if session.get("role") == "agent":
        return redirect(f"/view/{aid}")
    try:
        if db_root:
            db_root.child(f"coaching_logs/{cid}").delete()
            r = get_read_for(cid)
            if r:
                db_root.child(f"coaching_reads/{r.get('id')}").delete()
    except Exception:
        pass
    return redirect(f"/view/{aid}")


@app.route("/confirm_coaching/<aid>/<cid>")
@login_required
def confirm_coaching(aid, cid):
    try:
        agent_id = session.get("agent_id")
        if session.get("role") != "agent" or str(agent_id) != str(aid):
            return redirect(f"/view/{aid}")
        if get_read_for(cid):
            return redirect(f"/view/{aid}")
        if db_root:
            rid = str(uuid.uuid4())[:8]
            db_root.child(f"coaching_reads/{rid}").set({
                "id": rid,
                "coaching_id": cid,
                "agent_id": agent_id,
                "confirmed_at": datetime.now(PH_TZ).strftime("%Y-%m-%d %I:%M %p"),
            })
    except Exception:
        pass
    return redirect(f"/view/{aid}")


# ---------- Renderer (called from app.py's view() function) ----------

def render_coaching_section(aid, is_agent):
    logs = get_coaching(aid)
    today = datetime.now(PH_TZ).strftime("%Y-%m-%d")

    cards = ""
    for l in logs:
        cat = l.get("category", "Other")
        color = CATEGORY_COLORS.get(cat, "#94a3b8")
        read = get_read_for(l.get("id"))
        if is_agent:
            status_html = (
                "<span class='badge bg-success'>✅ Confirmed</span>" if read
                else f"<a href='/confirm_coaching/{aid}/{l.get('id')}' class='btn btn-sm btn-success'>✅ Confirm Received</a>"
            )
        else:
            status_html = (
                f"<span class='badge bg-success'>✅ Confirmed {read.get('confirmed_at','')}</span>" if read
                else "<span class='badge bg-secondary'>⏳ Pending</span>"
            )
        action_html = (
            f"<div style='margin-top:6px;font-size:12px;color:#fbbf24'><b>Action items:</b> {l.get('action_items')}</div>"
            if l.get("action_items") else ""
        )
        delete_btn = (
            f"<a href='/delete_coaching/{aid}/{l.get('id')}' class='btn btn-sm btn-outline-danger'>X</a>"
            if not is_agent else ""
        )
        cards += f"""<div class='card-dark mt-2' style='border-left:4px solid {color}'>
          <div class='d-flex justify-content-between align-items-start flex-wrap gap-2'>
            <div><span class='badge' style='background:{color}'>{cat}</span> <small style='color:var(--text2)'>{l.get('date','')} &middot; Coached by {l.get('coach','')}</small></div>
            <div class='d-flex align-items-center gap-2'>{status_html}{delete_btn}</div>
          </div>
          <p style='margin:8px 0 0;font-size:13px'>{l.get('notes','')}</p>
          {action_html}
        </div>"""

    if not cards:
        cards = "<div class='card-dark mt-2'><p style='text-align:center;color:var(--text2);margin:0'>No coaching sessions logged yet</p></div>"

    form_html = ""
    if not is_agent:
        options = "".join([f"<option value='{c}'>{c}</option>" for c in CATEGORY_COLORS.keys()])
        form_html = f"""<form method='POST' action='/add_coaching/{aid}' class='row g-2 mt-2'>
          <div class='col-6 col-md-3'><select name='category' class='form-select form-select-sm'>{options}</select></div>
          <div class='col-6 col-md-3'><input name='date' type='date' class='form-control form-control-sm' value='{today}'></div>
          <div class='col-12'><textarea name='notes' class='form-control form-control-sm' rows='2' placeholder='Coaching notes' required></textarea></div>
          <div class='col-12'><input name='action_items' class='form-control form-control-sm' placeholder='Action items / follow-up (optional)'></div>
          <div class='col-12'><button class='btn btn-sm w-100' style='background:#ec4899;color:white'>🎯 Log Coaching Session</button></div>
        </form>"""

    return f"""<div class='card-dark mt-3' style='border:1px solid #ec4899'>
      <h6 style='color:#ec4899;margin:0'>🎯 Coaching Minutes</h6>
      {form_html}
      <div class='mt-3'>{cards}</div>
    </div>"""
