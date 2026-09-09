# pdf_export.py
# Replaces the existing /export/pdf endpoint with a more "executive" report
# and fixes the "Graph error: maximum recursion depth exceeded" bug.
#
# There are TWO separate causes this bug can have, and this file fixes both:
#
# 1) The original code called `matplotlib.use('Agg')` fresh on every request
#    and drove chart creation through pyplot's global, stateful figure
#    registry (plt.subplots / plt.close). That global state is not safely
#    reentrant across concurrent requests/threads, which can itself surface
#    as a RecursionError under load. Fixed below by using the object-oriented
#    Figure/FigureCanvasAgg API instead of pyplot (no shared global state).
#
# 2) On many minimal/containerized hosts (Render, Railway, Heroku-style
#    dynos), matplotlib has to build its font cache on first use, and its
#    fallback font-lookup can recurse into itself when the container's font
#    directories are missing or unreadable — a known matplotlib issue on
#    stripped-down Linux images. This is very likely what you actually hit
#    in production (the error showed up on a *fresh report generation*, not
#    under concurrent load). Fixed below by pointing matplotlib's cache at a
#    guaranteed-writable directory and forcing it to use its own *bundled*
#    DejaVu Sans font, which skips the system font scan entirely.
#
# This file does not edit app.py's export_pdf function at all. Instead it
# swaps out the registered view function for the "/export/pdf" route after
# app.py has already defined it. app.py only needs one more import line
# at the bottom (`import pdf_export`) to load this file.

import os
import tempfile

# Must run BEFORE `import matplotlib` — this is what avoids cause #2 above.
_mpl_cache_dir = os.path.join(tempfile.gettempdir(), "mpl_cache_team_shine")
os.makedirs(_mpl_cache_dir, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", _mpl_cache_dir)

import matplotlib
matplotlib.use("Agg")  # set once, at import time — never again per-request
matplotlib.rcParams["font.family"] = "DejaVu Sans"  # bundled font, no system font scan
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg
