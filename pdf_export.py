# pdf_export.py
# Replaces the existing /export/pdf endpoint with a more "executive" report
# and fixes the "Graph error: maximum recursion depth exceeded" bug.
#
# Root cause of the original bug: the old code called `matplotlib.use('Agg')`
# fresh on every request and drove chart creation through pyplot's global,
# stateful figure registry (plt.subplots / plt.close). Under a threaded or
# gevent/eventlet worker, that shared global state is not safely reentrant,
# which is what surfaces as a RecursionError under load.
#
# Fix: matplotlib is configured ONCE at import time (below), and every chart
# is built with the object-oriented Figure/FigureCanvasAgg API instead of
# pyplot — no shared global figure state, so it's safe under concurrent
# requests.
#
# This file does not edit app.py's export_pdf function at all. Instead it
# swaps out the registered view function for the "/export/pdf" route after
# app.py has already defined it. app.py only needs one more import line
# at the bottom (`import pdf_export`) to load this file.

import matplotlib
matplotlib.use("Agg")  # set once, at import time — never again per-request
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg

from io import BytesIO
from datetime import datetime
from collections import defaultdict
import calendar
import traceback

from flask import Response

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image,
    PageBreak, HRFlowable,
)
from reportlab.pdfgen import canvas as pdfcanvas

from app import (
    app, login_required, page, PH_TZ,
    get_all, get_ot, get_perf, calc, calc_perf, parse_date,
    get_all_ot, get_all_perf, get_all_announcements, get_announcement_reads,
)

try:
    import coaching
    HAS_COACHING = True
except Exception:
    HAS_COACHING = False

GOLD = HexColor("#fbbf24")
DARK = HexColor("#0b1120")
CARD = HexColor("#151e32")
GREEN = HexColor("#22c55e")
RED = HexColor("#ef4444")
BLUE = HexColor("#3b82f6")
PURPLE = HexColor("#8b5cf6")
TEXT2 = HexColor("#64748b")


# ---------- Chart helpers (thread-safe: Figure + FigureCanvasAgg, no pyplot) ----------

def _fig_to_image(fig, width, height):
    fig.set_dpi(150)
    canvas_ = FigureCanvasAgg(fig)
    buf = BytesIO()
    canvas_.print_png(buf)
    buf.seek(0)
    return Image(buf, width=width, height=height)


def make_ot_trend_chart(months, normal_m, restday_m, total_m, loss_m):
    fig = Figure(figsize=(7.2, 3.2))
    ax = fig.add_subplot(111)
    ax.plot(months, normal_m, color="#22c55e", marker="o", label="Normal OT", linewidth=1.8)
    ax.plot(months, restday_m, color="#3b82f6", marker="o", label="Restday OT", linewidth=1.8)
    ax.plot(months, total_m, color="#fbbf24", marker="o", label="Total OT", linewidth=2.2)
    ax.plot(months, loss_m, color="#ef4444", marker="o", label="Loss", linewidth=1.8)
    ax.set_title("Monthly OT & Loss Trend", fontsize=11, fontweight="bold")
    ax.legend(fontsize=7, ncol=4, loc="upper center", bbox_to_anchor=(0.5, -0.15))
    ax.grid(alpha=0.25)
    ax.tick_params(labelsize=8)
    fig.tight_layout()
    return _fig_to_image(fig, 460, 200)


def make_quality_trend_chart(months, qa_m, aht_m, csat_m, fcr_m):
    fig = Figure(figsize=(7.2, 3.2))
    ax = fig.add_subplot(111)
    ax.plot(months, qa_m, color="#8b5cf6", marker="o", label="QA %", linewidth=1.8)
    ax.plot(months, csat_m, color="#06b6d4", marker="o", label="CSAT %", linewidth=1.8)
    ax.plot(months, fcr_m, color="#f59e0b", marker="o", label="FCR %", linewidth=1.8)
    ax2 = ax.twinx()
    ax2.plot(months, aht_m, color="#f97316", marker="s", linestyle="--", label="AHT (min)", linewidth=1.5)
    ax.set_title("Monthly Quality Trend (QA / CSAT / FCR vs AHT)", fontsize=11, fontweight="bold")
    lines1, labels1 = ax.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax.legend(lines1 + lines2, labels1 + labels2, fontsize=7, ncol=4, loc="upper center", bbox_to_anchor=(0.5, -0.15))
    ax.grid(alpha=0.25)
    ax.tick_params(labelsize=8)
    ax2.tick_params(labelsize=8)
    fig.tight_layout()
    return _fig_to_image(fig, 460, 200)


def make_leaderboard_chart(names, values, title, color, unit=""):
    fig = Figure(figsize=(7.2, 3.0))
    ax = fig.add_subplot(111)
    y_pos = range(len(names))
    ax.barh(list(y_pos), values, color=color)
    ax.set_yticks(list(y_pos))
    ax.set_yticklabels(names, fontsize=8)
    ax.invert_yaxis()
    ax.set_title(title, fontsize=11, fontweight="bold")
    for i, v in enumerate(values):
        ax.text(v, i, f" {v}{unit}", va="center", fontsize=7)
    ax.grid(alpha=0.2, axis="x")
    fig.tight_layout()
    return _fig_to_image(fig, 460, 190)


# ---------- Page chrome (branded header/footer, page numbers) ----------

class BrandedCanvas(pdfcanvas.Canvas):
    def __init__(self, *args, **kwargs):
        pdfcanvas.Canvas.__init__(self, *args, **kwargs)
        self._saved_pages = []

    def showPage(self):
        self._saved_pages.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        total = len(self._saved_pages)
        for i, state in enumerate(self._saved_pages):
            self.__dict__.update(state)
            self._draw_footer(i + 1, total)
            pdfcanvas.Canvas.showPage(self)
        pdfcanvas.Canvas.save(self)

    def _draw_footer(self, page_num, total_pages):
        self.setStrokeColor(GOLD)
        self.setLineWidth(0.6)
        self.line(30, 34, A4[0] - 30, 34)
        self.setFont("Helvetica", 7)
        self.setFillColor(TEXT2)
        self.drawString(30, 22, "TEAM SHINE M9 — Executive Performance Report")
        self.drawCentredString(A4[0] / 2, 22, "Confidential — Internal Use Only")
        self.drawRightString(A4[0] - 30, 22, f"Page {page_num} of {total_pages}")


# ---------- Report builder ----------

def build_pdf_report():
    agents = get_all()
    ot_logs = get_all_ot()
    perf_logs = get_all_perf()
    anns = get_all_announcements()
    reads = get_announcement_reads()

    agent_stats = []
    team_n = team_r = team_loss = team_tot = 0.0
    for a in agents:
        logs = get_ot(a.get("id"))
        n, r, tot, loss, net = calc(logs)
        team_n += n; team_r += r; team_loss += loss; team_tot += tot
        plogs = get_perf(a.get("id"))
        la, lq, lc, lf, aa, qa, ac, af = calc_perf(plogs)
        wh_target = float(a.get("WORKING_HOURS_TARGET", 220))
        wh_actual = wh_target - loss
        wh_comp = (wh_actual / wh_target * 100) if wh_target > 0 else 0
        agent_stats.append({
            "name": a.get("NAME", ""), "tid": a.get("TENCENT_ID", ""),
            "tot": tot, "loss": loss, "net": net,
            "aht": la, "qa": lq, "csat": lc, "fcr": lf,
            "wh_target": wh_target, "wh_actual": wh_actual, "wh_comp": wh_comp,
        })

    team_qa = [a["qa"] for a in agent_stats if a["qa"] > 0]
    team_aht = [a["aht"] for a in agent_stats if a["aht"] > 0]
    team_csat = [a["csat"] for a in agent_stats if a["csat"] > 0]
    team_fcr = [a["fcr"] for a in agent_stats if a["fcr"] > 0]
    total_wh = sum(a["wh_target"] for a in agent_stats)
    total_actual = total_wh - team_loss
    overall_att = (total_actual / total_wh * 100) if total_wh > 0 else 0
    avg_qa = round(sum(team_qa) / len(team_qa), 1) if team_qa else 0
    avg_aht = round(sum(team_aht) / len(team_aht), 1) if team_aht else 0
    avg_csat = round(sum(team_csat) / len(team_csat), 1) if team_csat else 0
    avg_fcr = round(sum(team_fcr) / len(team_fcr), 1) if team_fcr else 0

    at_risk = sorted([a for a in agent_stats if a["loss"] >= 4], key=lambda x: -x["loss"])

    coaching_line = ""
    if HAS_COACHING:
        try:
            all_coaching = coaching.get_all_coaching()
            c_reads = coaching.get_coaching_reads()
            confirmed_ids = {r.get("coaching_id") for r in c_reads}
            pending = [c for c in all_coaching if c.get("id") not in confirmed_ids]
            coaching_line = f" {len(all_coaching)} coaching sessions logged this period, {len(pending)} pending agent confirmation."
        except Exception:
            coaching_line = ""

    # ---- Monthly aggregates for charts ----
    m_ot = defaultdict(list)
    for l in ot_logs:
        dt = parse_date(l.get("date", ""))
        if dt:
            m_ot[dt.month].append(l)
    m_perf = defaultdict(list)
    for l in perf_logs:
        dt = parse_date(l.get("date", ""))
        if dt:
            m_perf[dt.month].append(l)

    months_lbl = [calendar.month_abbr[m] for m in range(1, 13)]
    normal_m, restday_m, total_m, loss_m = [], [], [], []
    qa_m, aht_m, csat_m, fcr_m = [], [], [], []
    for m in range(1, 13):
        n, r, tot, loss, net = calc(m_ot.get(m, []))
        normal_m.append(round(n, 1)); restday_m.append(round(r, 1))
        total_m.append(round(tot, 1)); loss_m.append(round(loss, 1))
        la, lq, lc, lf, aa, qav, acv, afv = calc_perf(m_perf.get(m, []))
        qa_m.append(round(qav, 1)); aht_m.append(round(aa, 1))
        csat_m.append(round(acv, 1)); fcr_m.append(round(afv, 1))

    # ---- Build the PDF ----
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=48,
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("ExecTitle", parent=styles["Heading1"], fontSize=20,
                                  leading=24, textColor=colors.white, alignment=TA_LEFT, spaceAfter=2)
    subtitle_style = ParagraphStyle("ExecSubtitle", parent=styles["Normal"], fontSize=10,
                                     textColor=HexColor("#cbd5e1"), alignment=TA_LEFT)
    section_style = ParagraphStyle("Section", parent=styles["Heading2"], fontSize=13,
                                    textColor=HexColor("#111827"), spaceBefore=14, spaceAfter=6)
    body_style = ParagraphStyle("Body", parent=styles["Normal"], fontSize=9.5, leading=14)
    small_style = ParagraphStyle("Small", parent=styles["Normal"], fontSize=8, textColor=TEXT2)

    story = []

    # --- Header band (dark card look, like the app's theme) ---
    header_table = Table(
        [[Paragraph("TEAM SHINE M9", title_style)],
         [Paragraph("Executive Performance Report", subtitle_style)],
         [Paragraph(
             f"Generated {datetime.now(PH_TZ).strftime('%B %d, %Y — %I:%M %p')} &nbsp;|&nbsp; Team size: {len(agents)} agents",
             small_style)]],
        colWidths=[535],
    )
    header_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), DARK),
        ("LEFTPADDING", (0, 0), (-1, -1), 16),
        ("RIGHTPADDING", (0, 0), (-1, -1), 16),
        ("TOPPADDING", (0, 0), (0, 0), 14),
        ("BOTTOMPADDING", (0, -1), (0, -1), 12),
        ("TOPPADDING", (0, 2), (0, 2), 2),
    ]))
    story.append(header_table)
    story.append(HRFlowable(width="100%", thickness=2, color=GOLD, spaceAfter=14, spaceBefore=0))

    # --- Executive summary (narrative) ---
    story.append(Paragraph("Executive Summary", section_style))
    att_word = "strong" if overall_att >= 95 else "adequate" if overall_att >= 90 else "a concern"
    qa_word = "on target" if avg_qa >= 80 or avg_qa == 0 else "below target"
    summary_text = (
        f"The team of <b>{len(agents)} agents</b> logged <b>{round(team_tot,1)}h</b> of overtime this period "
        f"against <b>{round(team_loss,1)}h</b> of loss, for a net contribution of <b>{round(team_tot-team_loss,1)}h</b>. "
        f"Overall attendance stands at <b>{round(overall_att,1)}%</b>, which is {att_word}. "
        f"Average QA is <b>{avg_qa}%</b> ({qa_word}), average AHT is <b>{avg_aht} min</b>, "
        f"CSAT averages <b>{avg_csat}%</b> and FCR averages <b>{avg_fcr}%</b>. "
        f"{len(at_risk)} agent(s) are flagged for loss hours of 4+ and may need follow-up.{coaching_line} "
        f"{len(anns)} announcement(s) were posted with {len(reads)} total confirmations."
    )
    story.append(Paragraph(summary_text, body_style))
    story.append(Spacer(1, 10))

    # --- KPI summary table ---
    story.append(Paragraph("Team KPI Summary", section_style))
    kpi_rows = [
        ["Metric", "Value", "Status"],
        ["Attendance", f"{round(overall_att,1)}%", "Good" if overall_att >= 95 else "Watch" if overall_att >= 90 else "Attention"],
        ["Team Avg QA", f"{avg_qa}%", "Good" if avg_qa >= 85 else "Watch" if avg_qa >= 75 else "Attention"],
        ["Team Avg AHT", f"{avg_aht} min", "—"],
        ["Team Avg CSAT", f"{avg_csat}%", "Good" if avg_csat >= 90 else "Watch" if avg_csat >= 80 else "Attention"],
        ["Team Avg FCR", f"{avg_fcr}%", "Good" if avg_fcr >= 70 else "Watch" if avg_fcr >= 60 else "Attention"],
        ["Total OT", f"{round(team_tot,1)}h", "—"],
        ["Total Loss", f"{round(team_loss,1)}h", "—"],
        ["Agents at Risk (Loss ≥4h)", str(len(at_risk)), "Attention" if at_risk else "Good"],
    ]
    kpi_table = Table(kpi_rows, colWidths=[260, 120, 120])
    status_color_rows = []
    for i, row in enumerate(kpi_rows[1:], start=1):
        status = row[2]
        c = GREEN if status == "Good" else RED if status == "Attention" else HexColor("#f59e0b") if status == "Watch" else colors.grey
        status_color_rows.append((i, c))
    style_cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), DARK),
        ("TEXTCOLOR", (0, 0), (-1, 0), GOLD),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#cbd5e1")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, HexColor("#f8fafc")]),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]
    for i, c in status_color_rows:
        style_cmds.append(("TEXTCOLOR", (2, i), (2, i), c))
        style_cmds.append(("FONTNAME", (2, i), (2, i), "Helvetica-Bold"))
    kpi_table.setStyle(TableStyle(style_cmds))
    story.append(kpi_table)
    story.append(Spacer(1, 12))

    # --- Charts ---
    try:
        story.append(Paragraph("Trends", section_style))
        story.append(make_ot_trend_chart(months_lbl, normal_m, restday_m, total_m, loss_m))
        story.append(Spacer(1, 8))
        story.append(make_quality_trend_chart(months_lbl, qa_m, aht_m, csat_m, fcr_m))
        story.append(Spacer(1, 10))
    except Exception as e:
        story.append(Paragraph(f"Chart rendering note: {str(e)}", small_style))

    # --- Leaderboard (top QA performers, if any data) ---
    try:
        qa_ranked = sorted([a for a in agent_stats if a["qa"] > 0], key=lambda x: -x["qa"])[:8]
        if qa_ranked:
            story.append(Paragraph("Top QA Performers", section_style))
            story.append(make_leaderboard_chart(
                [a["name"][:16] for a in qa_ranked], [round(a["qa"], 1) for a in qa_ranked],
                "Top QA Performers", "#8b5cf6", "%",
            ))
            story.append(Spacer(1, 10))
    except Exception:
        pass

    # --- At-risk callout ---
    if at_risk:
        story.append(Paragraph("Agents Flagged for Follow-up (Loss ≥ 4h)", section_style))
        risk_rows = [["Name", "Tencent ID", "Loss (h)", "Net OT (h)", "QA %"]]
        for a in at_risk[:15]:
            risk_rows.append([a["name"], a["tid"], round(a["loss"], 1), round(a["net"], 1), round(a["qa"], 1) if a["qa"] else "-"])
        risk_table = Table(risk_rows, colWidths=[150, 90, 90, 90, 90], repeatRows=1)
        risk_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), RED),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTSIZE", (0, 0), (-1, -1), 8.5),
            ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#cbd5e1")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, HexColor("#fef2f2")]),
        ]))
        story.append(risk_table)
        story.append(Spacer(1, 10))

    story.append(PageBreak())

    # --- Full agent detail table ---
    story.append(Paragraph("Agent Detail", section_style))
    agent_data = [["Name", "Tencent ID", "OT (h)", "Loss (h)", "QA %", "AHT (m)", "WH Comp."]]
    for a in sorted(agent_stats, key=lambda x: -x["wh_comp"]):
        agent_data.append([
            a["name"][:18], a["tid"], round(a["tot"], 1), round(a["loss"], 1),
            round(a["qa"], 1) if a["qa"] else "-", round(a["aht"], 1) if a["aht"] else "-", f"{round(a['wh_comp'],1)}%",
        ])
    agent_table = Table(agent_data, colWidths=[130, 70, 60, 60, 60, 65, 75], repeatRows=1)
    agent_style_cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), DARK),
        ("TEXTCOLOR", (0, 0), (-1, 0), GOLD),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#cbd5e1")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, HexColor("#f8fafc")]),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]
    for i, a in enumerate(sorted(agent_stats, key=lambda x: -x["wh_comp"]), start=1):
        if a["loss"] >= 4:
            agent_style_cmds.append(("TEXTCOLOR", (3, i), (3, i), RED))
            agent_style_cmds.append(("FONTNAME", (3, i), (3, i), "Helvetica-Bold"))
    agent_table.setStyle(TableStyle(agent_style_cmds))
    story.append(agent_table)

    doc.build(story, canvasmaker=BrandedCanvas)
    pdf = buffer.getvalue()
    buffer.close()
    return pdf


# ---------- Flask view (overrides the existing /export/pdf endpoint) ----------

@login_required
def export_pdf_v2():
    try:
        pdf = build_pdf_report()
        return Response(
            pdf, mimetype="application/pdf",
            headers={"Content-Disposition": "attachment;filename=Team_Shine_M9_Executive_Report.pdf"},
        )
    except Exception:
        return page(
            f"<div class='card-dark'><h6 style='color:#ef4444'>PDF Error</h6>"
            f"<pre style='color:#fbbf24;font-size:10px'>{traceback.format_exc()}</pre>"
            f"<a href='/export' class='btn btn-sm btn-outline-light'>Back</a></div>"
        )


# Preserve the endpoint name/route Flask already registered for "/export/pdf",
# just point it at the new, fixed implementation.
export_pdf_v2.__name__ = "export_pdf"
app.view_functions["export_pdf"] = export_pdf_v2
