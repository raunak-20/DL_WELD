"""
utils/constants.py
──────────────────
App-wide palette, paths, storage helpers, and reusable widget factories.
Import from here instead of duplicating across pages.
"""

import os
import json
import re
import datetime

# ─── Paths ────────────────────────────────────────────────────────────────────
BASE_DIR   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_DIR = os.path.join(BASE_DIR, 'static')
SCANS_DIR  = os.path.join(BASE_DIR, 'scans')
SCANS_JSON = os.path.join(BASE_DIR, 'scans.json')

# ── Logo paths ────────────────────────────────────────────────────────────────
# PRIMARY LOGO  →  static/DSES-Logo.png   (used in topbar & home hero)
# SECONDARY LOGO → static/DSES-Logo-2.png (optional; replace with your file)
#
# To swap in a different logo just change the filename below.
LOGO_PRIMARY   = os.path.join(STATIC_DIR, 'sigmandt.png')
LOGO_SECONDARY = os.path.join(STATIC_DIR, 'sigmandt.png')  # place your file here

os.makedirs(SCANS_DIR, exist_ok=True)

# ─── Palette ──────────────────────────────────────────────────────────────────
C_NAVY      = '#1B2A4A'
C_NAVY_MID  = '#243660'
C_NAVY_DARK = '#0F1B33'
C_GOLD      = '#E8A838'
C_GOLD_DRK  = '#C98A1F'
C_BG        = '#F0F2F5'
C_WHITE     = '#FFFFFF'
C_BORDER    = '#D1D5DB'
C_TEXT_MID  = '#6B7280'
C_TEXT_LITE = '#9CA3AF'
C_GREEN     = '#22C55E'
C_RED       = '#EF4444'
C_AMBER     = '#F59E0B'

STATUS_COLORS = {
    'pending':  C_AMBER,
    'recorded': C_GREEN,
    'captured': '#3B82F6',
    'analysed': C_GREEN,
}

# ─── Storage ──────────────────────────────────────────────────────────────────
def load_scans() -> list:
    if not os.path.exists(SCANS_JSON):
        return []
    try:
        with open(SCANS_JSON, 'r') as f:
            return json.load(f)
    except Exception:
        return []

def save_scans(scans: list) -> None:
    with open(SCANS_JSON, 'w') as f:
        json.dump(scans, f, indent=2, default=str)

def gen_report_id() -> str:
    year    = datetime.datetime.now().year
    max_seq = 0
    for s in load_scans():
        parts = s.get('report_id', '').split('-')
        if len(parts) >= 3:
            try:
                max_seq = max(max_seq, int(parts[-1]))
            except ValueError:
                pass
    return f"RPT-{year}-{(max_seq + 1):05d}"

def gen_scan_number() -> int:
    max_seq = 0
    for s in load_scans():
        raw = s.get('scan_number', 0)
        if isinstance(raw, int):
            max_seq = max(max_seq, raw)
        elif isinstance(raw, str):
            m = re.search(r'(\d+)', raw)
            if m:
                max_seq = max(max_seq, int(m.group(1)))
    return max_seq + 1

def now_str() -> str:
    return datetime.datetime.now().strftime('%d %b %Y, %H:%M')
