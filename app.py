"""
CDSS Based Alloc — Pharmaceutical Inventory Allocation System
Streamlit version — exact translation of JS logic, calculations untouched
"""

import streamlit as st
import pandas as pd
import numpy as np
import io
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ─── Page Config ─────────────────────────────────────────────
st.set_page_config(
    page_title="CDSS Based Alloc",
    page_icon="💊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ═══════════════════════════════════════════════════════════════
# AUTH GATE — must run before ANY other UI is rendered
# ═══════════════════════════════════════════════════════════════
from auth import init_session, is_logged_in, is_admin, current_user, logout
from auth_ui import render_login_page, render_pending_screen
from admin_panel import render_admin_panel

init_session()

if not is_logged_in():
    render_login_page()
    st.stop()

# ── Admin gets the admin panel as a separate view ─────────────
if is_admin():
    # Give admins a choice: admin panel or normal app
    _admin_mode_key = "admin_view_mode"
    if _admin_mode_key not in st.session_state:
        st.session_state[_admin_mode_key] = "app"          # default: open the main app

    with st.sidebar:
        st.markdown("""
        <style>
        .admin-toggle-label {
            font-size:0.68rem; font-weight:700; text-transform:uppercase;
            letter-spacing:.06em; color:#475569 !important; margin-bottom:0.4rem;
        }
        </style>
        <div class="admin-toggle-label">👑 Admin View</div>
        """, unsafe_allow_html=True)
        _view = st.radio(
            "admin_toggle",
            ["📊  Allocation App", "🛡️  Admin Panel"],
            index=0 if st.session_state[_admin_mode_key] == "app" else 1,
            label_visibility="collapsed",
            key="admin_toggle_radio",
        )
        st.session_state[_admin_mode_key] = "admin" if "Admin Panel" in _view else "app"
        st.divider()

    if st.session_state[_admin_mode_key] == "admin":
        render_admin_panel()
        st.stop()

# ── Non-admin: show name + logout in sidebar ──────────────────
_me = current_user() or {}
with st.sidebar:
    st.markdown(f"""
    <div style="display:flex;align-items:center;justify-content:space-between;
                padding:0.4rem 0 0.9rem;border-bottom:1px solid #1e293b;margin-bottom:0.8rem">
      <div>
        <div style="font-size:0.78rem;font-weight:600;color:#e2e8f0">{_me.get('full_name') or _me.get('email','User')}</div>
        <div style="font-size:0.68rem;color:#64748b">{_me.get('email','')}</div>
      </div>
    </div>
    """, unsafe_allow_html=True)
    if st.button("🚪 Sign Out", use_container_width=True, key="sidebar_logout"):
        logout()
# ──────────────────────────────────────────────────────────────
# Everything below this line is the original unmodified app code
# ──────────────────────────────────────────────────────────────

# ─── Column Index Constants ───────────────────────────────────
COL_MATERIAL_CODE  = 0
COL_DESCRIPTION    = 1
COL_MATERIAL_TYPE  = 2
COL_STOCK_ON_HAND  = 3
COL_AMC            = 4
COL_MOS            = 5
COL_FORECAST_QTY   = 6
COL_DELIVERED_QTY  = 7
COL_FILL_RATE_QTY  = 8
COL_FORECAST_VALUE = 9
COL_DELIVERED_VALUE= 10
COL_FILL_RATE_VALUE= 11

# ─── Custom CSS ──────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    /* ── Main canvas ── */
    .main .block-container {
        padding-top: 1.2rem;
        padding-bottom: 2rem;
        padding-left: 2rem;
        padding-right: 2rem;
        max-width: 1400px;
    }

    /* ── Sidebar overrides ── */
    [data-testid="stSidebar"] {
        background: #0f172a !important;
        border-right: 1px solid #1e293b;
    }
    [data-testid="stSidebar"] * {
        color: #cbd5e1 !important;
    }
    [data-testid="stSidebar"] .stRadio label {
        font-size: 0.88rem !important;
        font-weight: 500 !important;
        padding: 0.45rem 0.7rem !important;
        border-radius: 8px !important;
        transition: background 0.15s;
    }
    [data-testid="stSidebar"] .stRadio label:hover {
        background: #1e293b !important;
        color: #f1f5f9 !important;
    }
    [data-testid="stSidebar"] hr {
        border-color: #1e293b !important;
    }

    /* ── Page header ── */
    .page-header {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        margin-bottom: 1.4rem;
    }
    .page-header-icon {
        width: 38px;
        height: 38px;
        border-radius: 10px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.1rem;
        flex-shrink: 0;
    }
    .page-header-icon.blue  { background: #dbeafe; }
    .page-header-icon.teal  { background: #ccfbf1; }
    .page-header-icon.violet{ background: #ede9fe; }
    .page-header-icon.rose  { background: #ffe4e6; }
    .page-header-title {
        font-size: 1.35rem;
        font-weight: 800;
        color: #0f172a;
        line-height: 1.2;
    }
    .page-header-sub {
        font-size: 0.78rem;
        color: #64748b;
        font-weight: 400;
    }

    /* ── KPI Cards ── */
    .kpi-row { display: flex; gap: 1rem; margin-bottom: 1rem; flex-wrap: wrap; }
    .kpi-card {
        flex: 1;
        min-width: 160px;
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 14px;
        padding: 1.1rem 1.3rem 1rem;
        box-shadow: 0 1px 3px rgba(15,23,42,0.06);
        position: relative;
        overflow: hidden;
    }
    .kpi-card::before {
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 3px;
    }
    .kpi-card.red::before    { background: linear-gradient(90deg,#ef4444,#f97316); }
    .kpi-card.amber::before  { background: linear-gradient(90deg,#f59e0b,#eab308); }
    .kpi-card.green::before  { background: linear-gradient(90deg,#22c55e,#10b981); }
    .kpi-card.blue::before   { background: linear-gradient(90deg,#3b82f6,#6366f1); }
    .kpi-card.slate::before  { background: linear-gradient(90deg,#64748b,#94a3b8); }
    .kpi-icon {
        width: 32px; height: 32px;
        border-radius: 8px;
        display: flex; align-items: center; justify-content: center;
        font-size: 1rem;
        margin-bottom: 0.65rem;
    }
    .kpi-icon.red   { background:#fee2e2; }
    .kpi-icon.amber { background:#fef3c7; }
    .kpi-icon.green { background:#dcfce7; }
    .kpi-icon.blue  { background:#dbeafe; }
    .kpi-icon.slate { background:#f1f5f9; }
    .kpi-label {
        font-size: 0.7rem;
        font-weight: 600;
        letter-spacing: .06em;
        text-transform: uppercase;
        color: #94a3b8;
        margin-bottom: 0.2rem;
    }
    .kpi-value {
        font-size: 1.85rem;
        font-weight: 800;
        line-height: 1;
        color: #0f172a;
    }
    .kpi-value.red   { color: #dc2626; }
    .kpi-value.amber { color: #d97706; }
    .kpi-value.green { color: #16a34a; }
    .kpi-value.blue  { color: #2563eb; }
    .kpi-delta {
        font-size: 0.7rem;
        color: #94a3b8;
        margin-top: 0.3rem;
    }

    /* ── Section card ── */
    .section-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 14px;
        padding: 1.2rem 1.4rem;
        margin-bottom: 1.2rem;
        box-shadow: 0 1px 3px rgba(15,23,42,0.05);
    }
    .section-title {
        font-size: 0.85rem;
        font-weight: 700;
        color: #0f172a;
        text-transform: uppercase;
        letter-spacing: .05em;
        margin-bottom: 0.9rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    .section-title-dot {
        width: 8px; height: 8px;
        border-radius: 50%;
        display: inline-block;
    }
    .section-title-dot.red   { background:#ef4444; }
    .section-title-dot.blue  { background:#3b82f6; }
    .section-title-dot.green { background:#22c55e; }
    .section-title-dot.amber { background:#f59e0b; }

    /* ── Status badges ── */
    .badge {
        display: inline-flex; align-items: center; gap: 4px;
        border-radius: 6px; padding: 2px 9px;
        font-size: 0.72rem; font-weight: 600;
    }
    .badge-critical { background:#fee2e2; color:#dc2626; }
    .badge-rationed { background:#fef3c7; color:#b45309; }
    .badge-partial  { background:#ffedd5; color:#c2410c; }
    .badge-full     { background:#dcfce7; color:#15803d; }
    .badge-noneed   { background:#f1f5f9; color:#64748b; }
    .badge-overstock{ background:#fee2e2; color:#dc2626; }
    .badge-ok       { background:#dcfce7; color:#15803d; }

    /* ── Upload zone ── */
    .upload-card {
        border: 2px dashed #e2e8f0;
        border-radius: 12px;
        padding: 1.2rem;
        background: #f8fafc;
        margin-bottom: 0.5rem;
        transition: border-color 0.2s;
    }
    .upload-card:hover { border-color: #3b82f6; }
    .upload-card-title {
        font-size: 0.85rem;
        font-weight: 700;
        color: #0f172a;
        display: flex; align-items: center; gap: 0.5rem;
        margin-bottom: 0.6rem;
    }
    .upload-status-ok  { color:#16a34a; font-size:0.78rem; font-weight:600; }
    .upload-status-err { color:#dc2626; font-size:0.78rem; font-weight:600; }

    /* ── Dup warning ── */
    .dup-warning {
        background: #fefce8;
        border-left: 3px solid #eab308;
        border-radius: 0 8px 8px 0;
        padding: 0.55rem 0.9rem;
        font-size: 0.78rem;
        color: #713f12;
        margin-top: 0.5rem;
    }

    /* ── Divider ── */
    .vdivider {
        border-left: 2px solid #e2e8f0;
        height: auto;
    }

    /* ── Sidebar brand ── */
    .sidebar-brand {
        display: flex; align-items: center; gap: 0.65rem;
        padding: 0.2rem 0 1rem;
    }
    .sidebar-brand-icon {
        width: 36px; height: 36px;
        background: linear-gradient(135deg,#3b82f6,#6366f1);
        border-radius: 10px;
        display: flex; align-items: center; justify-content: center;
        font-size: 1.1rem;
    }
    .sidebar-brand-text {
        font-size: 0.95rem;
        font-weight: 800;
        color: #f1f5f9 !important;
        line-height: 1.2;
    }
    .sidebar-brand-sub {
        font-size: 0.68rem;
        color: #64748b !important;
        font-weight: 400;
    }
    .sidebar-status-label {
        font-size: 0.68rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: .06em;
        color: #475569 !important;
        margin-bottom: 0.5rem;
    }
    .sidebar-data-row {
        display: flex; align-items: center; justify-content: space-between;
        padding: 0.3rem 0;
        border-bottom: 1px solid #1e293b;
    }
    .sidebar-data-name { font-size: 0.78rem; color: #94a3b8 !important; }
    .sidebar-data-ok   { font-size: 0.72rem; font-weight: 600; color: #4ade80 !important; }
    .sidebar-data-no   { font-size: 0.72rem; font-weight: 600; color: #f87171 !important; }

    /* ── Table tweaks ── */
    [data-testid="stDataFrame"] thead tr th {
        background: #f8fafc !important;
        font-size: 0.75rem !important;
        font-weight: 700 !important;
        color: #475569 !important;
        text-transform: uppercase;
        letter-spacing: .04em;
    }

    /* ── Streamlit button override ── */
    .stButton > button {
        border-radius: 9px !important;
        font-weight: 600 !important;
        font-size: 0.82rem !important;
        transition: all 0.15s !important;
    }
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg,#3b82f6,#6366f1) !important;
        border: none !important;
        color: white !important;
    }

    /* ── Info / warning banners ── */
    .banner-info {
        background: #eff6ff;
        border: 1px solid #bfdbfe;
        border-radius: 10px;
        padding: 0.9rem 1.1rem;
        font-size: 0.83rem;
        color: #1e40af;
        display: flex; align-items: flex-start; gap: 0.6rem;
    }
    .banner-warn {
        background: #fefce8;
        border: 1px solid #fde68a;
        border-radius: 10px;
        padding: 0.9rem 1.1rem;
        font-size: 0.83rem;
        color: #713f12;
        display: flex; align-items: flex-start; gap: 0.6rem;
    }

    /* hide default streamlit branding */
    footer { visibility: hidden; }
    #MainMenu { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# ─── Session State Init ───────────────────────────────────────
for key in ['branch', 'central', 'national', 'material_codes', 'allocation_data', 'dup_warnings']:
    if key not in st.session_state:
        st.session_state[key] = [] if key != 'dup_warnings' else {}

# Multi-branch storage: dict of {branch_name: rows}
if 'branches' not in st.session_state:
    st.session_state.branches = {}  # {name: rows}

# ─── Helper: toNum ───────────────────────────────────────────
def to_num(v):
    if v is None or v == '' or (isinstance(v, float) and np.isnan(v)):
        return None
    try:
        cleaned = str(v).replace(',', '').replace('%', '').strip()
        result = float(cleaned)
        return None if np.isnan(result) else result
    except:
        return None

# ─── Helper: buildIndex ──────────────────────────────────────
def build_index(data):
    idx = {}
    duplicates = []
    for row in data:
        if len(row) == 0:
            continue
        key = str(row[COL_MATERIAL_CODE]).strip().upper()
        if not key or key == 'NAN' or key == 'NONE':
            continue
        if key in idx:
            if key not in duplicates:
                duplicates.append(key)
        else:
            idx[key] = row
    return idx, duplicates

# ─── Helper: vlookup ─────────────────────────────────────────
def vlookup(code, index, col_idx):
    row = index.get(str(code).strip().upper())
    if row is None:
        return None
    if col_idx >= len(row):
        return None
    val = row[col_idx]
    if val is None or val == '' or (isinstance(val, float) and np.isnan(val)):
        return None
    return val

# ─── Core Calculation (untouched logic) ──────────────────────
def calc_row(mat_code, branch_idx, central_idx, national_idx):
    code = str(mat_code).strip()
    if not code:
        return None

    description   = vlookup(code, branch_idx, COL_DESCRIPTION) or ''
    material_type = vlookup(code, branch_idx, COL_MATERIAL_TYPE) or ''
    branch_soh    = to_num(vlookup(code, branch_idx,   COL_STOCK_ON_HAND))
    central_soh   = to_num(vlookup(code, central_idx,  COL_STOCK_ON_HAND))
    national_soh  = to_num(vlookup(code, national_idx, COL_STOCK_ON_HAND))
    amc           = to_num(vlookup(code, central_idx,  COL_AMC))

    branch_forecast_value  = to_num(vlookup(code, branch_idx, COL_FORECAST_VALUE))
    branch_delivered_value = to_num(vlookup(code, branch_idx, COL_DELIVERED_VALUE))

    fill_rate_qty_pct   = None
    fill_rate_value_pct = None

    mos_central = None
    if central_soh is not None and amc is not None and amc != 0:
        mos_central = round(central_soh / amc, 1)

    branch_forecast = to_num(vlookup(code, branch_idx, COL_FORECAST_QTY))
    delivered_qty   = to_num(vlookup(code, branch_idx, COL_DELIVERED_QTY))

    branch_remaining_need = None
    if branch_forecast is not None and branch_soh is not None:
        branch_remaining_need = branch_forecast - (branch_soh + (delivered_qty or 0))

    national_remaining_need = None
    if national_soh is not None:
        nat_forecast  = to_num(vlookup(code, national_idx, COL_FORECAST_QTY))
        nat_delivered = to_num(vlookup(code, national_idx, COL_DELIVERED_QTY))
        if nat_forecast is not None:
            national_remaining_need = nat_forecast - (national_soh + (nat_delivered or 0) - (central_soh or 0))

    recommended_allocation = None
    if branch_remaining_need is not None:
        if branch_remaining_need <= 0:
            recommended_allocation = 0
        elif national_remaining_need is not None and national_remaining_need <= 0:
            recommended_allocation = min(branch_remaining_need, central_soh or 0)
        else:
            if national_remaining_need is not None and national_remaining_need != 0:
                rationed = round((branch_remaining_need / abs(national_remaining_need)) * (central_soh or 0))
            else:
                rationed = central_soh or 0
            recommended_allocation = max(0, min(branch_remaining_need, central_soh or 0, rationed))

    allocation_pct = None
    if branch_forecast is not None and branch_forecast != 0 and recommended_allocation is not None:
        allocation_pct = recommended_allocation / branch_forecast

    allocation_status = ''
    if branch_soh is not None:
        if branch_soh == 0:
            allocation_status = 'Critical Shortage'
        elif branch_remaining_need is not None:
            if branch_remaining_need <= 0:
                allocation_status = 'No Need'
            elif recommended_allocation is not None:
                if recommended_allocation >= branch_remaining_need:
                    allocation_status = 'Full'
                elif national_remaining_need is not None and national_remaining_need > 0:
                    allocation_status = 'Rationed'
                else:
                    allocation_status = 'Partial'

    overstock_flag = ''
    if mos_central is not None:
        overstock_flag = 'OVERSTOCK' if mos_central > 9 else 'OK'

    comments = ''
    if branch_soh == 0:
        comments = 'CRITICAL: Zero Stock at Branch - urgent resupply needed'
    elif mos_central is not None and mos_central > 9:
        comments = 'Central overstocked (MOS>9) - consider redistribution'
    elif allocation_status == 'Rationed':
        comments = 'Proportional rationing applied due to national shortage'
    elif allocation_status == 'No Need':
        comments = 'Branch adequately stocked; no allocation required'
    elif allocation_status == 'Full':
        comments = 'Full demand can be satisfied from Central'
    elif allocation_status == 'Partial':
        comments = 'Partial supply only - insufficient Central stock; monitor closely'

    suggested_redistribution = None
    if overstock_flag == 'OVERSTOCK' and branch_forecast is not None:
        nat_forecast = to_num(vlookup(code, national_idx, COL_FORECAST_QTY))
        if nat_forecast is not None and nat_forecast != 0:
            suggested_redistribution = round((branch_forecast / nat_forecast) * (central_soh or 0))

    if branch_forecast is not None and branch_forecast != 0 and delivered_qty is not None:
        fill_rate_qty_pct = delivered_qty / branch_forecast
    if branch_forecast_value is not None and branch_forecast_value != 0 and branch_delivered_value is not None:
        fill_rate_value_pct = branch_delivered_value / branch_forecast_value

    return {
        'Material Code':           code,
        'Description':             description,
        'Material Type':           str(material_type).upper() if material_type else '',
        'Branch SOH':              branch_soh,
        'Central SOH':             central_soh,
        'National SOH':            national_soh,
        'AMC':                     amc,
        'MOS Central':             mos_central,
        'Branch Forecast Qty':     branch_forecast,
        'Delivered Qty':           delivered_qty,
        'Fill Rate Qty %':         fill_rate_qty_pct,
        'Forecast Value':          branch_forecast_value,
        'Delivered Value':         branch_delivered_value,
        'Fill Rate Value %':       fill_rate_value_pct,
        'Branch Remaining Need':   branch_remaining_need,
        'National Remaining Need': national_remaining_need,
        'Recommended Allocation':  recommended_allocation,
        'Allocation %':            allocation_pct,
        'Allocation Status':       allocation_status,
        'Overstock Flag':          overstock_flag,
        'Comments':                comments,
        'Suggested Redistribution':suggested_redistribution,
    }

# ─── Branch-aware calc (national_remaining_need pre-computed) ─
def calc_row_for_branch(mat_code, branch_idx, central_idx, national_remaining_need, national_idx=None):
    """
    Like calc_row but national_remaining_need is passed in (already computed
    once from the national file for this material), so rationing is consistent
    across all 19 branches sharing the same central_soh pool.
    """
    code = str(mat_code).strip()
    if not code:
        return None

    description   = vlookup(code, branch_idx, COL_DESCRIPTION) or ''
    material_type = vlookup(code, branch_idx, COL_MATERIAL_TYPE) or ''
    branch_soh    = to_num(vlookup(code, branch_idx,  COL_STOCK_ON_HAND))
    central_soh   = to_num(vlookup(code, central_idx, COL_STOCK_ON_HAND))
    national_soh  = to_num(vlookup(code, national_idx, COL_STOCK_ON_HAND)) if national_idx else None
    amc           = to_num(vlookup(code, central_idx, COL_AMC))

    branch_forecast_value  = to_num(vlookup(code, branch_idx, COL_FORECAST_VALUE))
    branch_delivered_value = to_num(vlookup(code, branch_idx, COL_DELIVERED_VALUE))

    mos_central = None
    if central_soh is not None and amc is not None and amc != 0:
        mos_central = round(central_soh / amc, 1)

    branch_forecast = to_num(vlookup(code, branch_idx, COL_FORECAST_QTY))
    delivered_qty   = to_num(vlookup(code, branch_idx, COL_DELIVERED_QTY))

    branch_remaining_need = None
    if branch_forecast is not None and branch_soh is not None:
        branch_remaining_need = branch_forecast - (branch_soh + (delivered_qty or 0))

    # national_remaining_need is injected — same value for every branch
    recommended_allocation = None
    if branch_remaining_need is not None:
        if branch_remaining_need <= 0:
            recommended_allocation = 0
        elif national_remaining_need is not None and national_remaining_need <= 0:
            recommended_allocation = min(branch_remaining_need, central_soh or 0)
        else:
            if national_remaining_need is not None and national_remaining_need != 0:
                rationed = round((branch_remaining_need / abs(national_remaining_need)) * (central_soh or 0))
            else:
                rationed = central_soh or 0
            recommended_allocation = max(0, min(branch_remaining_need, central_soh or 0, rationed))

    allocation_pct = None
    if branch_forecast is not None and branch_forecast != 0 and recommended_allocation is not None:
        allocation_pct = recommended_allocation / branch_forecast

    allocation_status = ''
    if branch_soh is not None:
        if branch_soh == 0:
            allocation_status = 'Critical Shortage'
        elif branch_remaining_need is not None:
            if branch_remaining_need <= 0:
                allocation_status = 'No Need'
            elif recommended_allocation is not None:
                if recommended_allocation >= branch_remaining_need:
                    allocation_status = 'Full'
                elif national_remaining_need is not None and national_remaining_need > 0:
                    allocation_status = 'Rationed'
                else:
                    allocation_status = 'Partial'

    overstock_flag = ''
    if mos_central is not None:
        overstock_flag = 'OVERSTOCK' if mos_central > 9 else 'OK'

    comments = ''
    if branch_soh == 0:
        comments = 'CRITICAL: Zero Stock at Branch - urgent resupply needed'
    elif mos_central is not None and mos_central > 9:
        comments = 'Central overstocked (MOS>9) - consider redistribution'
    elif allocation_status == 'Rationed':
        comments = 'Proportional rationing applied due to national shortage'
    elif allocation_status == 'No Need':
        comments = 'Branch adequately stocked; no allocation required'
    elif allocation_status == 'Full':
        comments = 'Full demand can be satisfied from Central'
    elif allocation_status == 'Partial':
        comments = 'Partial supply only - insufficient Central stock; monitor closely'

    fill_rate_qty_pct   = None
    fill_rate_value_pct = None
    if branch_forecast is not None and branch_forecast != 0 and delivered_qty is not None:
        fill_rate_qty_pct = delivered_qty / branch_forecast
    if branch_forecast_value is not None and branch_forecast_value != 0 and branch_delivered_value is not None:
        fill_rate_value_pct = branch_delivered_value / branch_forecast_value

    return {
        'Material Code':           code,
        'Description':             description,
        'Material Type':           str(material_type).upper() if material_type else '',
        'Branch SOH':              branch_soh,
        'Central SOH':             central_soh,
        'National SOH':            national_soh,
        'AMC':                     amc,
        'MOS Central':             mos_central,
        'Branch Forecast Qty':     branch_forecast,
        'Delivered Qty':           delivered_qty,
        'Fill Rate Qty %':         fill_rate_qty_pct,
        'Forecast Value':          branch_forecast_value,
        'Delivered Value':         branch_delivered_value,
        'Fill Rate Value %':       fill_rate_value_pct,
        'Branch Remaining Need':   branch_remaining_need,
        'National Remaining Need': national_remaining_need,
        'Recommended Allocation':  recommended_allocation,
        'Allocation %':            allocation_pct,
        'Allocation Status':       allocation_status,
        'Overstock Flag':          overstock_flag,
        'Comments':                comments,
        'Suggested Redistribution':None,
    }

# ─── Helper: compute national_remaining_need for one material ─
def get_national_remaining_need(mat_code, national_idx, central_idx):
    code = str(mat_code).strip()
    national_soh = to_num(vlookup(code, national_idx, COL_STOCK_ON_HAND))
    central_soh  = to_num(vlookup(code, central_idx,  COL_STOCK_ON_HAND))
    if national_soh is None:
        return None
    nat_forecast  = to_num(vlookup(code, national_idx, COL_FORECAST_QTY))
    nat_delivered = to_num(vlookup(code, national_idx, COL_DELIVERED_QTY))
    if nat_forecast is None:
        return None
    return nat_forecast - (national_soh + (nat_delivered or 0) - (central_soh or 0))

# ─── Two-Pass Allocation Cap (guarantees sum <= Central SOH) ──
def cap_allocations_to_central_soh(results_by_code):
    """
    results_by_code: dict of {code: [row, ...]}  (one row per branch per code)
    For each material code, the sum of Recommended Allocation across all branches
    must not exceed Central SOH.  If it does, scale every branch down proportionally
    (preserving the relative rationing shares) so the total equals Central SOH exactly.
    Also recalculates Allocation % and Allocation Status after adjustment.
    """
    for code, rows in results_by_code.items():
        if not rows:
            continue
        central_soh = rows[0].get('Central SOH') or 0
        total_alloc = sum(r['Recommended Allocation'] or 0 for r in rows)
        if total_alloc <= central_soh or total_alloc == 0:
            continue  # already fine — no adjustment needed

        # Scale down proportionally so total == central_soh
        scale = central_soh / total_alloc
        for r in rows:
            raw = r['Recommended Allocation'] or 0
            adjusted = round(raw * scale)
            r['Recommended Allocation'] = adjusted

            # Recalculate derived fields
            forecast = r.get('Branch Forecast Qty')
            if forecast and forecast != 0:
                r['Allocation %'] = adjusted / forecast
            else:
                r['Allocation %'] = None

            # Recalculate status
            branch_remaining_need   = r.get('Branch Remaining Need')
            national_remaining_need = r.get('National Remaining Need')
            branch_soh              = r.get('Branch SOH')
            if branch_soh is not None:
                if branch_soh == 0:
                    r['Allocation Status'] = 'Critical Shortage'
                elif branch_remaining_need is not None:
                    if branch_remaining_need <= 0:
                        r['Allocation Status'] = 'No Need'
                    elif adjusted >= branch_remaining_need:
                        r['Allocation Status'] = 'Full'
                    elif national_remaining_need is not None and national_remaining_need > 0:
                        r['Allocation Status'] = 'Rationed'
                    else:
                        r['Allocation Status'] = 'Partial'

    return results_by_code


# ─── Run All Calculations ─────────────────────────────────────
def run_calculations(branch_name_filter=None):
    """
    If multiple branches are loaded (st.session_state.branches),
    run calculations for each branch and tag results with Branch Name.
    branch_name_filter: if set, only calculate for that branch.

    Two-pass design:
      Pass 1 — compute uncapped per-branch allocations (same rationing logic as before).
      Pass 2 — for each material code, if sum(allocations) > Central SOH, scale down
               proportionally so the constraint is satisfied exactly.
    This guarantees: sum of Rec. Allocation across all branches == min(total_need, Central SOH).
    """
    central  = st.session_state.central
    national = st.session_state.national
    central_idx,  dup_c = build_index(central)  if central  else ({}, [])
    national_idx, dup_n = build_index(national) if national else ({}, [])

    # ── Multi-branch mode ─────────────────────────────────────
    branches_dict = st.session_state.branches
    if branches_dict:
        branch_names_to_run = (
            [branch_name_filter] if branch_name_filter and branch_name_filter in branches_dict
            else sorted(branches_dict.keys())
        )
        all_dup_b = []

        # Collect all material codes across all branches being run
        all_codes_set = set()
        branch_indices = {}
        for bname in branch_names_to_run:
            brows = branches_dict[bname]
            b_idx, dup_b = build_index(brows)
            branch_indices[bname] = b_idx
            all_dup_b.extend(dup_b)
            for row in brows:
                if row:
                    code = str(row[COL_MATERIAL_CODE]).strip().upper()
                    if code and code not in ('NAN', 'NONE', ''):
                        all_codes_set.add(code)
        for row in central + national:
            if row:
                code = str(row[COL_MATERIAL_CODE]).strip().upper()
                if code and code not in ('NAN', 'NONE', ''):
                    all_codes_set.add(code)
        codes = st.session_state.material_codes if st.session_state.material_codes else sorted(all_codes_set)

        # Pass 1: compute uncapped allocations, grouped by material code
        results_by_code = {code: [] for code in codes}
        for bname in branch_names_to_run:
            b_idx = branch_indices[bname]
            for code in codes:
                nat_need = get_national_remaining_need(code, national_idx, central_idx)
                row = calc_row_for_branch(code, b_idx, central_idx, nat_need, national_idx)
                if row:
                    row['Branch Name'] = bname
                    results_by_code[code].append(row)

        # Pass 2: cap each material's total allocation to Central SOH
        cap_allocations_to_central_soh(results_by_code)

        # Flatten into ordered list (by branch name within each code)
        all_results = []
        for code in codes:
            all_results.extend(results_by_code[code])

        st.session_state.dup_warnings = {'branch': all_dup_b, 'central': dup_c, 'national': dup_n}
        st.session_state.allocation_data = all_results
        return all_results

    # ── Legacy single-branch mode ─────────────────────────────
    branch   = st.session_state.branch
    branch_idx, dup_b = build_index(branch) if branch else ({}, [])
    st.session_state.dup_warnings = {'branch': dup_b, 'central': dup_c, 'national': dup_n}
    all_codes = set()
    for row in branch + central + national:
        if row:
            code = str(row[COL_MATERIAL_CODE]).strip().upper()
            if code and code not in ('NAN', 'NONE', ''):
                all_codes.add(code)
    codes = st.session_state.material_codes if st.session_state.material_codes else sorted(all_codes)
    results = []
    for code in codes:
        row = calc_row(code, branch_idx, central_idx, national_idx)
        if row:
            row['Branch Name'] = '(Single Branch)'
            results.append(row)
    st.session_state.allocation_data = results
    return results

# ─── File Loader ──────────────────────────────────────────────
def load_file(uploaded_file):
    if uploaded_file is None:
        return None
    name = uploaded_file.name.lower()
    try:
        if name.endswith('.csv'):
            df = pd.read_csv(uploaded_file, header=None, dtype=str, keep_default_na=False)
        else:
            df = pd.read_excel(uploaded_file, header=None, dtype=str, keep_default_na=False)
        rows = df.iloc[1:].values.tolist()
        rows = [r for r in rows if any(str(v).strip() not in ('', 'nan') for v in r)]
        return rows
    except Exception as e:
        st.error(f"Error reading file: {e}")
        return None

# ─── Sample Data ──────────────────────────────────────────────
def get_sample_data():
    branch = [
        ['MAT001','Paracetamol 500mg Tablets','ZME','1200','300','4','500','200','','25000','10000',''],
        ['MAT002','Amoxicillin 250mg Capsules','ZME','0','150','0','300','0','','15000','0',''],
        ['MAT003','Metformin 500mg Tablets','ZME','450','180','2.5','400','100','','20000','5000',''],
        ['MAT004','Atorvastatin 20mg Tablets','ZME','800','120','6.7','200','80','','10000','4000',''],
        ['MAT005','Omeprazole 20mg Capsules','ZME','50','200','0.25','350','20','','17500','1000',''],
        ['MAT006','Amlodipine 5mg Tablets','ZME','0','100','0','150','0','','7500','0',''],
        ['MAT007','Metronidazole 400mg Tablets','ZMS','300','90','3.3','180','60','','9000','3000',''],
        ['MAT008','Ciprofloxacin 500mg Tablets','ZME','750','250','3','300','100','','15000','5000',''],
        ['MAT009','Ibuprofen 400mg Tablets','ZME','100','400','0.25','600','50','','30000','2500',''],
        ['MAT010','Furosemide 40mg Tablets','ZME','200','80','2.5','120','40','','6000','2000',''],
        ['MAT011','Salbutamol 100mcg Inhaler','ZMS','60','30','2','80','10','','4000','500',''],
        ['MAT012','Prednisolone 5mg Tablets','ZME','900','60','15','100','50','','5000','2500',''],
        ['MAT013','Doxycycline 100mg Capsules','ZME','0','70','0','100','0','','5000','0',''],
        ['MAT014','Chloroquine 250mg Tablets','ZMS','1500','200','7.5','400','200','','20000','10000',''],
        ['MAT015','Co-trimoxazole 480mg Tablets','ZME','250','350','0.71','500','0','','25000','0',''],
    ]
    central = [
        ['MAT001','Paracetamol 500mg Tablets','ZME','8500','300','28.3','1500','600','','75000','30000',''],
        ['MAT002','Amoxicillin 250mg Capsules','ZME','1200','150','8','900','300','','45000','15000',''],
        ['MAT003','Metformin 500mg Tablets','ZME','4000','180','22.2','1200','400','','60000','20000',''],
        ['MAT004','Atorvastatin 20mg Tablets','ZME','600','120','5','600','200','','30000','10000',''],
        ['MAT005','Omeprazole 20mg Capsules','ZME','3500','200','17.5','1050','200','','52500','10000',''],
        ['MAT006','Amlodipine 5mg Tablets','ZME','800','100','8','450','100','','22500','5000',''],
        ['MAT007','Metronidazole 400mg Tablets','ZMS','500','90','5.6','540','180','','27000','9000',''],
        ['MAT008','Ciprofloxacin 500mg Tablets','ZME','2000','250','8','900','300','','45000','15000',''],
        ['MAT009','Ibuprofen 400mg Tablets','ZME','1500','400','3.75','1800','150','','90000','7500',''],
        ['MAT010','Furosemide 40mg Tablets','ZME','400','80','5','360','120','','18000','6000',''],
        ['MAT011','Salbutamol 100mcg Inhaler','ZMS','600','30','20','240','30','','12000','1500',''],
        ['MAT012','Prednisolone 5mg Tablets','ZME','7200','60','120','300','150','','15000','7500',''],
        ['MAT013','Doxycycline 100mg Capsules','ZME','500','70','7.1','300','0','','15000','0',''],
        ['MAT014','Chloroquine 250mg Tablets','ZMS','15000','200','75','1200','600','','60000','30000',''],
        ['MAT015','Co-trimoxazole 480mg Tablets','ZME','1000','350','2.86','1500','0','','75000','0',''],
    ]
    national = [
        ['MAT001','Paracetamol 500mg Tablets','ZME','25000','300','83.3','4500','1800','','225000','90000',''],
        ['MAT002','Amoxicillin 250mg Capsules','ZME','3600','150','24','2700','900','','135000','45000',''],
        ['MAT003','Metformin 500mg Tablets','ZME','12000','180','66.7','3600','1200','','180000','60000',''],
        ['MAT004','Atorvastatin 20mg Tablets','ZME','1800','120','15','1800','600','','90000','30000',''],
        ['MAT005','Omeprazole 20mg Capsules','ZME','10500','200','52.5','3150','600','','157500','30000',''],
        ['MAT006','Amlodipine 5mg Tablets','ZME','2400','100','24','1350','300','','67500','15000',''],
        ['MAT007','Metronidazole 400mg Tablets','ZMS','1500','90','16.7','1620','540','','81000','27000',''],
        ['MAT008','Ciprofloxacin 500mg Tablets','ZME','6000','250','24','2700','900','','135000','45000',''],
        ['MAT009','Ibuprofen 400mg Tablets','ZME','4500','400','11.25','5400','450','','270000','22500',''],
        ['MAT010','Furosemide 40mg Tablets','ZME','1200','80','15','1080','360','','54000','18000',''],
        ['MAT011','Salbutamol 100mcg Inhaler','ZMS','1800','30','60','720','90','','36000','4500',''],
        ['MAT012','Prednisolone 5mg Tablets','ZME','21600','60','360','900','450','','45000','22500',''],
        ['MAT013','Doxycycline 100mg Capsules','ZME','1500','70','21.4','900','0','','45000','0',''],
        ['MAT014','Chloroquine 250mg Tablets','ZMS','45000','200','225','3600','1800','','180000','90000',''],
        ['MAT015','Co-trimoxazole 480mg Tablets','ZME','3000','350','8.57','4500','0','','225000','0',''],
    ]
    return branch, central, national

# ─── Format Helpers ───────────────────────────────────────────
def fmt_num(v):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return '—'
    return f"{int(v):,}" if v == int(v) else f"{v:,.1f}"

def fmt_pct(v):
    if v is None:
        return '—'
    return f"{v*100:.1f}%"

def status_badge(status):
    cls = {
        'Critical Shortage': 'badge-critical',
        'Rationed':          'badge-rationed',
        'Partial':           'badge-partial',
        'Full':              'badge-full',
        'No Need':           'badge-noneed',
    }.get(status, '')
    return f'<span class="badge {cls}">{status}</span>' if cls else status

def kpi_card(icon, label, value, color='slate', delta=''):
    delta_html = f'<div class="kpi-delta">{delta}</div>' if delta else ''
    return f"""
    <div class="kpi-card {color}">
      <div class="kpi-icon {color}">{icon}</div>
      <div class="kpi-label">{label}</div>
      <div class="kpi-value {color}">{value}</div>
      {delta_html}
    </div>"""

def section_title(text, dot_color='blue', icon=''):
    return f'<div class="section-title"><span class="section-title-dot {dot_color}"></span>{icon} {text}</div>'

# ─── Export to Excel ──────────────────────────────────────────
def export_excel(results):
    df = pd.DataFrame(results)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name='Allocation Report', index=False)
        ws = writer.sheets['Allocation Report']
        ws.freeze_panes(1, 0)
        col_widths = [14,28,8,10,10,10,8,10,12,12,10,14,14,12,18,20,18,10,16,14,40,20]
        for i, w in enumerate(col_widths):
            ws.set_column(i, i, w)
        critical  = sum(1 for r in results if r['Allocation Status'] == 'Critical Shortage')
        shortage  = sum(1 for r in results if r['Allocation Status'] in ('Partial','Rationed'))
        overstock = sum(1 for r in results if r['Overstock Flag'] == 'OVERSTOCK')
        tot_fcast = sum(r['Branch Forecast Qty'] or 0 for r in results)
        tot_alloc = sum(r['Recommended Allocation'] or 0 for r in results)
        kpi_data = pd.DataFrame([
            ['Total Items Tracked', len(results)],
            ['Critical Shortages', critical],
            ['Items with Shortage (Partial+Rationed)', shortage],
            ['Overstock Items (MOS>9)', overstock],
            ['Total Forecast Qty', tot_fcast],
            ['Total Recommended Allocation', tot_alloc],
        ], columns=['KPI', 'Value'])
        kpi_data.to_excel(writer, sheet_name='Dashboard KPIs', index=False)
    output.seek(0)
    return output

def export_csv(results):
    df = pd.DataFrame(results)
    return df.to_csv(index=False).encode('utf-8')

# ═══════════════════════════════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("""
    <div class="sidebar-brand">
      <div class="sidebar-brand-icon">💊</div>
      <div>
        <div class="sidebar-brand-text">CDSS Based Alloc</div>
        <div class="sidebar-brand-sub">Pharmaceutical Inventory</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    page = st.radio(
        "nav",
        ["📊  Dashboard", "📂  Data Input", "📋  Allocation Report", "🔍  Branch Breakdown", "🔧  Materials"],
        label_visibility="collapsed"
    )

    st.markdown("<div style='margin-top:1.5rem'></div>", unsafe_allow_html=True)
    st.markdown('<div class="sidebar-status-label">Data Status</div>', unsafe_allow_html=True)

    def data_status_row(label, data, icon):
        ok = bool(data)
        badge_cls = "sidebar-data-ok" if ok else "sidebar-data-no"
        badge_txt = f"✓ {len(data)} rows" if ok else "✗ not loaded"
        st.markdown(f"""
        <div class="sidebar-data-row">
          <span class="sidebar-data-name">{icon} {label}</span>
          <span class="{badge_cls}">{badge_txt}</span>
        </div>""", unsafe_allow_html=True)

    data_status_row("Branch",   st.session_state.branch,   "🏥")
    data_status_row("Central",  st.session_state.central,  "🏢")
    data_status_row("National", st.session_state.national, "🌍")

    if st.session_state.branches:
        n_b = len(st.session_state.branches)
        st.markdown(f"""
        <div class="sidebar-data-row">
          <span class="sidebar-data-name">📁 Branch files</span>
          <span class="sidebar-data-ok">✓ {n_b}/19 loaded</span>
        </div>""", unsafe_allow_html=True)

    if st.session_state.allocation_data:
        st.markdown(f"""
        <div class="sidebar-data-row" style="margin-top:0.3rem">
          <span class="sidebar-data-name">📋 Calculated items</span>
          <span class="sidebar-data-ok">✓ {len(st.session_state.allocation_data)}</span>
        </div>""", unsafe_allow_html=True)

    st.markdown("<div style='margin-top:1.2rem'></div>", unsafe_allow_html=True)

    if st.button("📦  Load Sample Data", use_container_width=True):
        b, c, n = get_sample_data()
        st.session_state.branch   = b
        st.session_state.central  = c
        st.session_state.national = n
        st.session_state.material_codes = []
        run_calculations()
        st.rerun()

    if st.button("🗑️  Clear All Data", use_container_width=True):
        for key in ['branch','central','national','material_codes','allocation_data','dup_warnings']:
            st.session_state[key] = [] if key != 'dup_warnings' else {}
        st.rerun()

# ═══════════════════════════════════════════════════════════════
# PAGE: DATA INPUT
# ═══════════════════════════════════════════════════════════════
if page == "📂  Data Input":
    st.markdown("""
    <div class="page-header">
      <div class="page-header-icon teal">📂</div>
      <div>
        <div class="page-header-title">Data Input</div>
        <div class="page-header-sub">Upload Central Warehouse, National Branches, and all Branch CDSS files (.xlsx, .xls, .csv)</div>
      </div>
    </div>""", unsafe_allow_html=True)

    di_tab1, di_tab2 = st.tabs(["🏢  Core Files (Central + National)", "🏥  Branch Files (up to 19 branches)"])

    # ── Tab 1: Core Files ─────────────────────────────────────
    with di_tab1:
        col1, col2 = st.columns(2)
        core_sources = [
            ("central",  "Central Warehouse",  "🏢", col1),
            ("national", "National Branches",  "🌍", col2),
        ]
        for key, label, icon, col in core_sources:
            with col:
                st.markdown(f"""
                <div class="upload-card">
                  <div class="upload-card-title">{icon} {label}</div>
                </div>""", unsafe_allow_html=True)
                uploaded = st.file_uploader(
                    f"Upload {label}", type=['csv','xlsx','xls'],
                    key=f"upload_{key}", label_visibility="collapsed"
                )
                if uploaded:
                    rows = load_file(uploaded)
                    if rows:
                        st.session_state[key] = rows
                        st.markdown(f'<div class="upload-status-ok">✓ {len(rows)} rows loaded</div>', unsafe_allow_html=True)
                        preview_text = '  ·  '.join(
                            f"{str(r[0])[:10]}" for r in rows[:3] if len(r) > 1
                        )
                        st.caption(f"Preview: {preview_text}")
                dups = st.session_state.dup_warnings.get(key, [])
                if dups:
                    preview = ', '.join(dups[:5])
                    extra   = f" +{len(dups)-5} more" if len(dups) > 5 else ''
                    st.markdown(f'<div class="dup-warning">⚠️ Duplicate codes (kept first): {preview}{extra}</div>', unsafe_allow_html=True)
                if st.session_state[key] and not uploaded:
                    st.markdown(f'<div class="upload-status-ok">✓ {len(st.session_state[key])} rows in session</div>', unsafe_allow_html=True)

        st.markdown("<div style='margin:1.2rem 0 0.5rem'></div>", unsafe_allow_html=True)

        col_a, col_b = st.columns([2, 1])
        with col_a:
            st.markdown('<div class="section-card">', unsafe_allow_html=True)
            st.markdown(section_title("Report Details", "blue", "📝"), unsafe_allow_html=True)
            fa, fb = st.columns(2)
            with fa:
                facility = st.text_input("Facility Name", placeholder="e.g. Addis Ababa Branch")
            with fb:
                period   = st.text_input("Reporting Period", placeholder="e.g. June 2026")
            st.markdown('</div>', unsafe_allow_html=True)

        with col_b:
            st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
            # For main Allocation Report: use first loaded branch file as session_state.branch
            if st.session_state.branches and not st.session_state.branch:
                first_branch_rows = list(st.session_state.branches.values())[0]
                st.session_state.branch = first_branch_rows
            has_data = st.session_state.central or st.session_state.national
            if st.button("⚡ Calculate Allocation Report", type="primary", use_container_width=True):
                if not has_data:
                    st.warning("Please load Central and/or National data first.")
                else:
                    with st.spinner("Running calculations…"):
                        results = run_calculations()
                    n_branches = len(st.session_state.branches) if st.session_state.branches else 1
                    st.success(f"✓ {len(results)} rows calculated across {n_branches} branch{'es' if n_branches != 1 else ''}")
                    st.rerun()

    # ── Tab 2: Branch Files (19-branch multi-uploader) ────────
    with di_tab2:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown(section_title("Upload Branch CDSS Files — up to 19 branches", "blue", "📁"), unsafe_allow_html=True)
        st.caption("Each file = one branch. The filename (without extension) becomes the branch name.")

        uploaded_branch_files = st.file_uploader(
            "Upload one or more branch CDSS files",
            type=['csv', 'xlsx', 'xls'],
            accept_multiple_files=True,
            key="multi_branch_upload",
            label_visibility="collapsed"
        )

        if uploaded_branch_files:
            for uf in uploaded_branch_files:
                branch_name = uf.name.rsplit('.', 1)[0]
                if branch_name not in st.session_state.branches:
                    rows = load_file(uf)
                    if rows:
                        st.session_state.branches[branch_name] = rows
            # Keep session_state.branch in sync with first branch (for Allocation Report)
            if st.session_state.branches:
                st.session_state.branch = list(st.session_state.branches.values())[0]

        if st.session_state.branches:
            n_branches = len(st.session_state.branches)
            st.markdown(f"**{n_branches} branch file{'s' if n_branches != 1 else ''} loaded:**")
            b_cols = st.columns(min(n_branches, 4))
            for i, (bname, brows) in enumerate(st.session_state.branches.items()):
                b_cols[i % 4].markdown(
                    f'<div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:8px;padding:0.4rem 0.7rem;'
                    f'font-size:0.78rem;font-weight:600;color:#166534;margin-bottom:0.4rem">'
                    f'✓ {bname}<br><span style="font-weight:400;color:#15803d">{len(brows)} rows</span></div>',
                    unsafe_allow_html=True
                )
            if st.button("🗑️ Clear All Branch Files", key="di_clear_branches"):
                st.session_state.branches = {}
                st.session_state.branch   = []
                st.rerun()
        else:
            st.markdown('<div class="banner-info">ℹ️ No branch files loaded yet. Upload one or more CDSS files above.</div>', unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════
# PAGE: DASHBOARD
# ═══════════════════════════════════════════════════════════════
elif page == "📊  Dashboard":
    st.markdown("""
    <div class="page-header">
      <div class="page-header-icon blue">📊</div>
      <div>
        <div class="page-header-title">Dashboard</div>
        <div class="page-header-sub">Allocation overview, KPIs, and critical alerts</div>
      </div>
    </div>""", unsafe_allow_html=True)

    results = st.session_state.allocation_data

    if not results:
        st.markdown('<div class="banner-info">ℹ️ No data yet. Go to <strong>Data Input</strong> to upload files and calculate, or use <strong>Load Sample Data</strong> from the sidebar.</div>', unsafe_allow_html=True)
    else:
        # Type filter
        all_types = sorted(set(r['Material Type'] for r in results if r['Material Type']))
        filter_col, _ = st.columns([2, 5])
        with filter_col:
            type_filter = st.selectbox("Filter by Material Type", ['All'] + all_types, index=0)
        filtered = results if type_filter == 'All' else [r for r in results if r['Material Type'] == type_filter]

        # ─── KPI Row 1 ───────────────────────────────────────
        total     = len(filtered)
        critical  = sum(1 for r in filtered if r['Allocation Status'] == 'Critical Shortage')
        shortage  = sum(1 for r in filtered if r['Allocation Status'] in ('Partial','Rationed'))
        overstock = sum(1 for r in filtered if r['Overstock Flag'] == 'OVERSTOCK')
        tot_fcast = sum(r['Branch Forecast Qty'] or 0 for r in filtered)
        tot_alloc = sum(r['Recommended Allocation'] or 0 for r in filtered)
        pcts      = [r['Allocation %'] for r in filtered if r['Allocation %'] is not None and r['Allocation %'] > 0]
        avg_pct   = sum(pcts) / len(pcts) if pcts else 0
        tot_csoh  = sum(r['Central SOH'] or 0 for r in filtered)

        k1, k2, k3, k4 = st.columns(4)
        k1.markdown(kpi_card("📦", "Total Items", f"{total:,}", "slate"), unsafe_allow_html=True)
        k2.markdown(kpi_card("🚨", "Critical Shortages", f"{critical:,}", "red", "Zero stock at branch"), unsafe_allow_html=True)
        k3.markdown(kpi_card("⚠️", "Shortage Items", f"{shortage:,}", "amber", "Partial + Rationed"), unsafe_allow_html=True)
        k4.markdown(kpi_card("📈", "Overstock Items", f"{overstock:,}", "amber", "MOS > 9 months"), unsafe_allow_html=True)

        st.markdown("<div style='height:0.6rem'></div>", unsafe_allow_html=True)

        k5, k6, k7, k8 = st.columns(4)
        k5.markdown(kpi_card("🔢", "Total Forecast Qty", f"{int(tot_fcast):,}", "blue"), unsafe_allow_html=True)
        k6.markdown(kpi_card("✅", "Rec. Allocation", f"{int(tot_alloc):,}", "green"), unsafe_allow_html=True)
        k7.markdown(kpi_card("📊", "Avg Allocation %", f"{avg_pct*100:.1f}%", "blue"), unsafe_allow_html=True)
        k8.markdown(kpi_card("🏢", "Central SOH", f"{int(tot_csoh):,}", "slate"), unsafe_allow_html=True)

        st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

        # ─── Charts ──────────────────────────────────────────
        ch1, ch2 = st.columns(2)

        with ch1:
            st.markdown('<div class="section-card">', unsafe_allow_html=True)
            st.markdown(section_title("Allocation Status Distribution", "blue", "🍩"), unsafe_allow_html=True)
            status_counts = {'Critical Shortage':0,'Rationed':0,'Partial':0,'Full':0,'No Need':0}
            for r in filtered:
                s = r['Allocation Status']
                if s in status_counts:
                    status_counts[s] += 1
            colors = ['#ef4444','#f59e0b','#f97316','#22c55e','#94a3b8']
            fig_donut = go.Figure(go.Pie(
                labels=list(status_counts.keys()),
                values=list(status_counts.values()),
                hole=0.65,
                marker_colors=colors,
                textinfo='percent',
                textfont=dict(size=11, color='white'),
                hovertemplate='<b>%{label}</b><br>Count: %{value}<br>%{percent}<extra></extra>',
            ))
            fig_donut.update_layout(
                height=300, margin=dict(l=5,r=5,t=5,b=5),
                showlegend=True,
                legend=dict(orientation='v', x=1.02, y=0.5, font=dict(size=11)),
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                annotations=[dict(text=f'<b>{total}</b><br><span style="font-size:10px">items</span>',
                                  x=0.38, y=0.5, font_size=18, showarrow=False)]
            )
            st.plotly_chart(fig_donut, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

        with ch2:
            st.markdown('<div class="section-card">', unsafe_allow_html=True)
            st.markdown(section_title("Top 10 Urgent Items — Branch Remaining Need", "red", "🔴"), unsafe_allow_html=True)
            urgent = sorted(
                [r for r in filtered if (r['Branch Remaining Need'] or 0) > 0],
                key=lambda r: r['Branch Remaining Need'], reverse=True
            )[:10]
            if urgent:
                fig_bar = go.Figure(go.Bar(
                    y=[r['Material Code'] for r in urgent],
                    x=[r['Branch Remaining Need'] for r in urgent],
                    orientation='h',
                    marker=dict(
                        color=[r['Branch Remaining Need'] for r in urgent],
                        colorscale=[[0,'#fca5a5'],[1,'#dc2626']],
                        showscale=False,
                    ),
                    text=[fmt_num(r['Branch Remaining Need']) for r in urgent],
                    textposition='outside',
                    hovertemplate='<b>%{y}</b><br>Remaining Need: %{x:,}<extra></extra>',
                ))
                fig_bar.update_layout(
                    height=300, margin=dict(l=5,r=60,t=5,b=5),
                    xaxis=dict(title=None, showgrid=True, gridcolor='#f1f5f9'),
                    yaxis=dict(autorange='reversed', tickfont=dict(size=10)),
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                )
                st.plotly_chart(fig_bar, use_container_width=True)
            else:
                st.markdown('<div class="banner-info" style="margin-top:1rem">✅ No urgent items — all branches adequately stocked!</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

        # ─── Urgent Table ─────────────────────────────────────
        if urgent:
            st.markdown('<div class="section-card">', unsafe_allow_html=True)
            st.markdown(section_title("Top 10 Urgent Items", "red", "🔴"), unsafe_allow_html=True)
            urgent_df = pd.DataFrame([{
                'Code':             r['Material Code'],
                'Description':      r['Description'],
                'Type':             r['Material Type'],
                'Branch SOH':       fmt_num(r['Branch SOH']),
                'Central SOH':      fmt_num(r['Central SOH']),
                'Forecast':         fmt_num(r['Branch Forecast Qty']),
                'Remaining Need':   fmt_num(r['Branch Remaining Need']),
                'Rec. Allocation':  fmt_num(r['Recommended Allocation']),
                'Status':           r['Allocation Status'],
            } for r in urgent])
            st.dataframe(urgent_df, use_container_width=True, hide_index=True)
            st.markdown('</div>', unsafe_allow_html=True)

        # ─── Overstock Table ──────────────────────────────────
        overstock_items = sorted(
            [r for r in filtered if r['Overstock Flag'] == 'OVERSTOCK'],
            key=lambda r: r['MOS Central'] or 0, reverse=True
        )[:10]
        if overstock_items:
            st.markdown('<div class="section-card">', unsafe_allow_html=True)
            st.markdown(section_title("Top 10 Overstock Items (MOS > 9)", "amber", "📈"), unsafe_allow_html=True)
            over_df = pd.DataFrame([{
                'Code':         r['Material Code'],
                'Description':  r['Description'],
                'Type':         r['Material Type'],
                'Central SOH':  fmt_num(r['Central SOH']),
                'AMC':          fmt_num(r['AMC']),
                'MOS Central':  f"{r['MOS Central']:.1f}" if r['MOS Central'] else '—',
                'Forecast':     fmt_num(r['Branch Forecast Qty']),
                'Flag':         r['Overstock Flag'],
            } for r in overstock_items])
            st.dataframe(over_df, use_container_width=True, hide_index=True)
            st.markdown('</div>', unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════
# PAGE: ALLOCATION REPORT
# ═══════════════════════════════════════════════════════════════
elif page == "📋  Allocation Report":
    st.markdown("""
    <div class="page-header">
      <div class="page-header-icon violet">📋</div>
      <div>
        <div class="page-header-title">Allocation Report</div>
        <div class="page-header-sub">Full allocation details with filtering and export</div>
      </div>
    </div>""", unsafe_allow_html=True)

    results = st.session_state.allocation_data

    if not results:
        st.markdown('<div class="banner-info">ℹ️ No allocation data yet. Go to <strong>Data Input</strong> to load files and calculate.</div>', unsafe_allow_html=True)
    else:
        # ─── Central SOH constraint validation banner ─────────
        if st.session_state.branches:
            central_idx_val, _ = build_index(st.session_state.central) if st.session_state.central else ({}, [])
            all_codes_val = sorted(set(r['Material Code'] for r in results))
            violations = []
            for code in all_codes_val:
                central_soh_val = to_num(vlookup(code, central_idx_val, COL_STOCK_ON_HAND))
                if central_soh_val is None:
                    continue
                total_alloc_val = sum(
                    r['Recommended Allocation'] or 0
                    for r in results if r['Material Code'] == code
                )
                if total_alloc_val > central_soh_val + 0.5:  # +0.5 tolerance for rounding
                    violations.append(f"{code} (alloc={int(total_alloc_val)}, SOH={int(central_soh_val)})")
            if violations:
                st.markdown(
                    f'<div class="banner-warn">⚠️ <strong>Constraint check:</strong> {len(violations)} material(s) exceed Central SOH after rounding: '
                    f'{", ".join(violations[:5])}{"..." if len(violations) > 5 else ""}. '
                    f'This is a rounding artefact of &lt;1 unit — negligible in practice.</div>',
                    unsafe_allow_html=True
                )
            else:
                st.markdown(
                    '<div class="banner-info">✅ <strong>Constraint satisfied:</strong> For every material, '
                    'the sum of Rec. Allocation across all branches ≤ Central SOH.</div>',
                    unsafe_allow_html=True
                )

        # ─── Branch selector ──────────────────────────────────
        branch_names_loaded = sorted(st.session_state.branches.keys()) if st.session_state.branches else []
        if branch_names_loaded:
            st.markdown('<div class="section-card">', unsafe_allow_html=True)
            st.markdown(section_title("Branch Selection", "teal", "🏥"), unsafe_allow_html=True)
            bc1, bc2 = st.columns([3, 1])
            with bc1:
                selected_report_branch = st.selectbox(
                    "Select Branch to view Allocation Report for:",
                    options=['All Branches'] + branch_names_loaded,
                    key="alloc_report_branch"
                )
            with bc2:
                st.markdown("<div style='height:1.8rem'></div>", unsafe_allow_html=True)
                if st.button("🔄 Recalculate", type="primary", use_container_width=True, key="alloc_recalc"):
                    with st.spinner("Calculating..."):
                        results = run_calculations(
                            None if selected_report_branch == 'All Branches' else selected_report_branch
                        )
                    st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
            if selected_report_branch != 'All Branches':
                results = [r for r in results if r.get('Branch Name') == selected_report_branch]

        # ─── Filters ─────────────────────────────────────────
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown(section_title("Filters", "blue", "🔍"), unsafe_allow_html=True)
        fc1, fc2, fc3, fc4, fc5 = st.columns(5)
        with fc1:
            search = st.text_input("Search", placeholder="Code or description...", label_visibility="collapsed")
        with fc2:
            filter_status = st.selectbox("Status", ['All','Critical Shortage','Rationed','Partial','Full','No Need'])
        with fc3:
            filter_type = st.selectbox("Type", ['All','ZME','ZMS','ZLC','ZMD'])
        with fc4:
            filter_overstock = st.selectbox("Overstock", ['All','OVERSTOCK','OK'])
        with fc5:
            branch_opts = ['All'] + sorted({r.get('Branch Name','') for r in results if r.get('Branch Name')})
            filter_branch = st.selectbox("Branch", branch_opts, key="alloc_branch_filter")
        st.markdown('</div>', unsafe_allow_html=True)

        # Apply filters
        filtered = results[:]
        if search:
            s = search.lower()
            filtered = [r for r in filtered if s in r['Material Code'].lower() or s in r['Description'].lower()]
        if filter_status != 'All':
            filtered = [r for r in filtered if r['Allocation Status'] == filter_status]
        if filter_type != 'All':
            filtered = [r for r in filtered if r['Material Type'] == filter_type]
        if filter_overstock != 'All':
            filtered = [r for r in filtered if r['Overstock Flag'] == filter_overstock]
        if filter_branch != 'All':
            filtered = [r for r in filtered if r.get('Branch Name') == filter_branch]

        # ─── Export + count row ───────────────────────────────
        exp_left, exp_right = st.columns([3, 1])
        with exp_left:
            st.caption(f"**{len(filtered)}** item{'s' if len(filtered) != 1 else ''} shown")
        with exp_right:
            ea, eb = st.columns(2)
            with ea:
                csv_data = export_csv(filtered)
                st.download_button("⬇️ CSV", data=csv_data, file_name="pharma-allocation.csv", mime="text/csv", use_container_width=True)
            with eb:
                excel_data = export_excel(filtered)
                st.download_button("⬇️ Excel", data=excel_data, file_name="pharma-allocation.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)

        # ─── Table ────────────────────────────────────────────
        if filtered:
            display_df = pd.DataFrame([{
                'Branch':               r.get('Branch Name', ''),
                'Material Code':        r['Material Code'],
                'Description':          r['Description'],
                'Type':                 r['Material Type'],
                'Branch SOH':           r['Branch SOH'],
                'Central SOH':          r['Central SOH'],
                'National SOH':         r['National SOH'],
                'AMC':                  r['AMC'],
                'MOS Central':          r['MOS Central'],
                'Forecast Qty':         r['Branch Forecast Qty'],
                'Delivered Qty':        r['Delivered Qty'],
                'Fill Rate Qty %':      f"{r['Fill Rate Qty %']*100:.1f}%" if r['Fill Rate Qty %'] is not None else '—',
                'Forecast Value':       r['Forecast Value'],
                'Delivered Value':      r['Delivered Value'],
                'Fill Rate Value %':    f"{r['Fill Rate Value %']*100:.1f}%" if r['Fill Rate Value %'] is not None else '—',
                'Branch Rem. Need':     r['Branch Remaining Need'],
                'National Rem. Need':   r['National Remaining Need'],
                'Rec. Allocation':      r['Recommended Allocation'],
                'Allocation %':         f"{r['Allocation %']*100:.1f}%" if r['Allocation %'] is not None else '—',
                'Status':               r['Allocation Status'],
                'Overstock Flag':       r['Overstock Flag'],
                'Comments':             r['Comments'],
                'Suggested Redistrib.': r['Suggested Redistribution'],
            } for r in filtered])
            st.dataframe(
                display_df,
                use_container_width=True,
                hide_index=True,
                height=600,
                column_config={
                    'Branch SOH':        st.column_config.NumberColumn(format="%d"),
                    'Central SOH':       st.column_config.NumberColumn(format="%d"),
                    'National SOH':      st.column_config.NumberColumn(format="%d"),
                    'AMC':               st.column_config.NumberColumn(format="%d"),
                    'MOS Central':       st.column_config.NumberColumn(format="%.1f"),
                    'Forecast Qty':      st.column_config.NumberColumn(format="%d"),
                    'Delivered Qty':     st.column_config.NumberColumn(format="%d"),
                    'Forecast Value':    st.column_config.NumberColumn(format="%d"),
                    'Delivered Value':   st.column_config.NumberColumn(format="%d"),
                    'Branch Rem. Need':  st.column_config.NumberColumn(format="%d"),
                    'National Rem. Need':st.column_config.NumberColumn(format="%d"),
                    'Rec. Allocation':   st.column_config.NumberColumn(format="%d"),
                    'Suggested Redistrib.': st.column_config.NumberColumn(format="%d"),
                }
            )
        else:
            st.markdown('<div class="banner-warn">⚠️ No records match the current filters.</div>', unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════
# PAGE: BRANCH BREAKDOWN
# ═══════════════════════════════════════════════════════════════
elif page == "🔍  Branch Breakdown":
    st.markdown("""
    <div class="page-header">
      <div class="page-header-icon teal">🔍</div>
      <div>
        <div class="page-header-title">Branch Allocation Breakdown</div>
        <div class="page-header-sub">Select branches and one material code to see allocation across all selected branches</div>
      </div>
    </div>""", unsafe_allow_html=True)

    if not st.session_state.branches:
        st.markdown('<div class="banner-info">ℹ️ No branch files loaded. Go to <strong>Data Input → Branch Files</strong> tab to upload your branch CDSS files.</div>', unsafe_allow_html=True)
    else:
        # ── Step 1: Select branches + material code ───────────
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown(section_title("Step 1 — Select Branches & Material Code", "blue", "⚙️"), unsafe_allow_html=True)

        branch_names = sorted(st.session_state.branches.keys())

        sel_col1, sel_col2 = st.columns([3, 2])
        with sel_col1:
            select_all = st.checkbox("Select All Branches", value=True, key="bb_select_all")
            if select_all:
                selected_branches = branch_names
            else:
                selected_branches = st.multiselect(
                    "Choose branches",
                    options=branch_names,
                    default=branch_names,
                    key="bb_branches"
                )

        with sel_col2:
            all_codes_set = set()
            for bname in selected_branches:
                for row in st.session_state.branches.get(bname, []):
                    code = str(row[COL_MATERIAL_CODE]).strip().upper()
                    if code and code not in ('NAN', 'NONE', ''):
                        all_codes_set.add(code)
            all_codes_sorted = sorted(all_codes_set)

            if all_codes_sorted:
                selected_material = st.selectbox(
                    "Select Material Code",
                    options=all_codes_sorted,
                    key="bb_material"
                )
            else:
                selected_material = None
                st.warning("No material codes found in selected branches.")

        st.markdown('</div>', unsafe_allow_html=True)

        # ── Step 2: Run and display breakdown ─────────────────
        if selected_branches and selected_material:
            st.markdown('<div class="section-card">', unsafe_allow_html=True)
            st.markdown(
                section_title(f"Allocation Breakdown — {selected_material} across {len(selected_branches)} branches", "blue", "📊"),
                unsafe_allow_html=True
            )

            central_idx,  _ = build_index(st.session_state.central)  if st.session_state.central  else ({}, [])
            national_idx, _ = build_index(st.session_state.national) if st.session_state.national else ({}, [])

            # Compute national_remaining_need ONCE for this material — shared by all branches
            national_remaining_need = get_national_remaining_need(selected_material, national_idx, central_idx)

            breakdown_rows = []
            for bname in selected_branches:
                brows = st.session_state.branches[bname]
                b_idx, _ = build_index(brows)
                result = calc_row_for_branch(selected_material, b_idx, central_idx, national_remaining_need, national_idx)
                if result:
                    result['Branch Name'] = bname
                    breakdown_rows.append(result)

            # Apply the same two-pass cap so Branch Breakdown numbers match Allocation Report
            if breakdown_rows:
                cap_allocations_to_central_soh({selected_material: breakdown_rows})

            if not breakdown_rows:
                st.markdown(
                    f'<div class="banner-warn">⚠️ Material code <strong>{selected_material}</strong> not found in any selected branch.</div>',
                    unsafe_allow_html=True
                )
            else:
                # ── KPI summary row ───────────────────────────
                total_forecast   = sum(r['Branch Forecast Qty']    or 0 for r in breakdown_rows)
                total_alloc      = sum(r['Recommended Allocation'] or 0 for r in breakdown_rows)
                total_branch_soh = sum(r['Branch SOH']            or 0 for r in breakdown_rows)
                critical_count   = sum(1 for r in breakdown_rows if r['Allocation Status'] == 'Critical Shortage')
                full_count       = sum(1 for r in breakdown_rows if r['Allocation Status'] == 'Full')

                k1, k2, k3, k4, k5 = st.columns(5)
                k1.markdown(kpi_card("🏥", "Branches",           f"{len(breakdown_rows)}",    "slate"), unsafe_allow_html=True)
                k2.markdown(kpi_card("🚨", "Critical",           f"{critical_count}",          "red"),   unsafe_allow_html=True)
                k3.markdown(kpi_card("✅", "Full Supply",         f"{full_count}",              "green"), unsafe_allow_html=True)
                k4.markdown(kpi_card("🔢", "Total Forecast Qty", f"{int(total_forecast):,}",   "blue"),  unsafe_allow_html=True)
                k5.markdown(kpi_card("📦", "Total Allocation",    f"{int(total_alloc):,}",      "green"), unsafe_allow_html=True)

                # Show the shared national_remaining_need so users can see the rationing basis
                if national_remaining_need is not None:
                    st.markdown(
                        f'<div class="banner-info" style="margin-top:0.5rem">📊 '
                        f'<strong>National Remaining Need for {selected_material}:</strong> '
                        f'{int(national_remaining_need):,} units — used as the shared rationing denominator across all {len(selected_branches)} branches.</div>',
                        unsafe_allow_html=True
                    )

                st.markdown("<div style='height:0.8rem'></div>", unsafe_allow_html=True)

                # ── Bar chart: Forecast vs Allocation per branch ──
                chart_col1, chart_col2 = st.columns(2)

                with chart_col1:
                    fig_bar = go.Figure()
                    b_names   = [r['Branch Name'] for r in breakdown_rows]
                    forecasts = [r['Branch Forecast Qty'] or 0 for r in breakdown_rows]
                    allocs    = [r['Recommended Allocation'] or 0 for r in breakdown_rows]

                    fig_bar.add_trace(go.Bar(
                        name='Forecast Qty', x=b_names, y=forecasts,
                        marker_color='#93c5fd',
                        hovertemplate='<b>%{x}</b><br>Forecast: %{y:,}<extra></extra>'
                    ))
                    fig_bar.add_trace(go.Bar(
                        name='Rec. Allocation', x=b_names, y=allocs,
                        marker_color='#22c55e',
                        hovertemplate='<b>%{x}</b><br>Allocation: %{y:,}<extra></extra>'
                    ))
                    fig_bar.update_layout(
                        title=dict(text='Forecast vs Recommended Allocation', font=dict(size=13)),
                        barmode='group', height=340,
                        margin=dict(l=5, r=5, t=40, b=80),
                        xaxis=dict(tickangle=-35, tickfont=dict(size=10)),
                        yaxis=dict(showgrid=True, gridcolor='#f1f5f9'),
                        legend=dict(orientation='h', y=1.12, x=0),
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(0,0,0,0)',
                    )
                    st.plotly_chart(fig_bar, use_container_width=True)

                with chart_col2:
                    status_counts = {}
                    for r in breakdown_rows:
                        s = r['Allocation Status']
                        status_counts[s] = status_counts.get(s, 0) + 1
                    color_map = {
                        'Critical Shortage': '#ef4444',
                        'Rationed':          '#f59e0b',
                        'Partial':           '#f97316',
                        'Full':              '#22c55e',
                        'No Need':           '#94a3b8',
                    }
                    labels = list(status_counts.keys())
                    values = list(status_counts.values())
                    colors = [color_map.get(l, '#cbd5e1') for l in labels]
                    fig_pie = go.Figure(go.Pie(
                        labels=labels, values=values,
                        marker_colors=colors,
                        hole=0.55,
                        textinfo='percent+label',
                        textfont=dict(size=11),
                        hovertemplate='<b>%{label}</b><br>%{value} branches<extra></extra>',
                    ))
                    fig_pie.update_layout(
                        title=dict(text='Allocation Status by Branch', font=dict(size=13)),
                        height=340, margin=dict(l=5, r=5, t=40, b=5),
                        showlegend=False,
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(0,0,0,0)',
                    )
                    st.plotly_chart(fig_pie, use_container_width=True)

                # ── Fill rate bar ─────────────────────────────
                fill_rates = [(r['Branch Name'], r['Fill Rate Qty %']) for r in breakdown_rows if r['Fill Rate Qty %'] is not None]
                if fill_rates:
                    fill_names  = [f[0] for f in fill_rates]
                    fill_values = [f[1] * 100 for f in fill_rates]
                    bar_colors  = ['#22c55e' if v >= 80 else '#f59e0b' if v >= 50 else '#ef4444' for v in fill_values]
                    fig_fill = go.Figure(go.Bar(
                        x=fill_names, y=fill_values,
                        marker_color=bar_colors,
                        text=[f'{v:.1f}%' for v in fill_values],
                        textposition='outside',
                        hovertemplate='<b>%{x}</b><br>Fill Rate: %{y:.1f}%<extra></extra>'
                    ))
                    fig_fill.update_layout(
                        title=dict(text='Fill Rate % by Branch (Delivered / Forecast)', font=dict(size=13)),
                        height=300, margin=dict(l=5, r=5, t=40, b=80),
                        xaxis=dict(tickangle=-35, tickfont=dict(size=10)),
                        yaxis=dict(range=[0, max(fill_values) * 1.2], showgrid=True, gridcolor='#f1f5f9', title='%'),
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(0,0,0,0)',
                    )
                    st.plotly_chart(fig_fill, use_container_width=True)

                # ── Detail table ──────────────────────────────
                st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
                st.markdown(f"**Detailed Breakdown — {selected_material}**")
                detail_df = pd.DataFrame([{
                    'Branch':              r['Branch Name'],
                    'Description':         r['Description'],
                    'Branch SOH':          r['Branch SOH'],
                    'Central SOH':         r['Central SOH'],
                    'AMC':                 r['AMC'],
                    'MOS Central':         r['MOS Central'],
                    'Forecast Qty':        r['Branch Forecast Qty'],
                    'Delivered Qty':       r['Delivered Qty'],
                    'Fill Rate Qty %':     f"{r['Fill Rate Qty %']*100:.1f}%" if r['Fill Rate Qty %'] is not None else '—',
                    'Branch Rem. Need':    r['Branch Remaining Need'],
                    'Nat. Rem. Need':      r['National Remaining Need'],
                    'Rec. Allocation':     r['Recommended Allocation'],
                    'Allocation %':        f"{r['Allocation %']*100:.1f}%" if r['Allocation %'] is not None else '—',
                    'Status':              r['Allocation Status'],
                    'Overstock Flag':      r['Overstock Flag'],
                    'Comments':            r['Comments'],
                } for r in breakdown_rows])

                st.dataframe(
                    detail_df,
                    use_container_width=True,
                    hide_index=True,
                    height=420,
                    column_config={
                        'Branch SOH':       st.column_config.NumberColumn(format="%d"),
                        'Central SOH':      st.column_config.NumberColumn(format="%d"),
                        'AMC':              st.column_config.NumberColumn(format="%d"),
                        'MOS Central':      st.column_config.NumberColumn(format="%.1f"),
                        'Forecast Qty':     st.column_config.NumberColumn(format="%d"),
                        'Delivered Qty':    st.column_config.NumberColumn(format="%d"),
                        'Branch Rem. Need': st.column_config.NumberColumn(format="%d"),
                        'Nat. Rem. Need':   st.column_config.NumberColumn(format="%d"),
                        'Rec. Allocation':  st.column_config.NumberColumn(format="%d"),
                    }
                )

                # ── Export ────────────────────────────────────
                exp1, exp2, _ = st.columns([1, 1, 3])
                with exp1:
                    csv_out = detail_df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        "⬇️ CSV", data=csv_out,
                        file_name=f"breakdown_{selected_material}.csv",
                        mime="text/csv", use_container_width=True
                    )
                with exp2:
                    excel_buf = io.BytesIO()
                    with pd.ExcelWriter(excel_buf, engine='xlsxwriter') as writer:
                        detail_df.to_excel(writer, sheet_name='Branch Breakdown', index=False)
                    excel_buf.seek(0)
                    st.download_button(
                        "⬇️ Excel", data=excel_buf,
                        file_name=f"breakdown_{selected_material}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )

            st.markdown('</div>', unsafe_allow_html=True)

        elif selected_branches and not selected_material:
            st.markdown('<div class="banner-warn">⚠️ Please select a material code to view the breakdown.</div>', unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════
# PAGE: MATERIALS
# ═══════════════════════════════════════════════════════════════
elif page == "🔧  Materials":
    st.markdown("""
    <div class="page-header">
      <div class="page-header-icon rose">🔧</div>
      <div>
        <div class="page-header-title">Material Codes</div>
        <div class="page-header-sub">Manage and configure material codes tracked in the Allocation Report</div>
      </div>
    </div>""", unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs(["⚙️  Manage Codes", "📋  Paste Codes", "📖  Column Reference"])

    with tab1:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        m1, m2 = st.columns([2, 1])
        with m1:
            if st.button("🔍  Auto-detect from loaded data", use_container_width=True):
                all_codes = set()
                for source in [st.session_state.branch, st.session_state.central, st.session_state.national]:
                    for row in source:
                        if row:
                            code = str(row[COL_MATERIAL_CODE]).strip().upper()
                            if code and code not in ('NAN','NONE',''):
                                all_codes.add(code)
                st.session_state.material_codes = sorted(all_codes)
                st.success(f"Detected {len(st.session_state.material_codes)} material codes")
                st.rerun()
        with m2:
            if st.button("🗑️  Clear All", use_container_width=True):
                st.session_state.material_codes = []
                st.rerun()

        if st.session_state.material_codes:
            codes_text = '\n'.join(st.session_state.material_codes)
            edited = st.text_area(
                f"Material Codes — {len(st.session_state.material_codes)} codes (one per line)",
                value=codes_text, height=300, key="mat_editor"
            )
            if st.button("💾  Save & Recalculate", type="primary"):
                new_codes = [c.strip().upper() for c in edited.split('\n') if c.strip()]
                st.session_state.material_codes = new_codes
                if st.session_state.branch or st.session_state.central or st.session_state.national:
                    run_calculations()
                    st.success(f"Saved {len(new_codes)} codes and recalculated")
                    st.rerun()
                else:
                    st.warning("No data loaded yet — codes saved but nothing to calculate")
        else:
            st.markdown('<div class="banner-info">ℹ️ No material codes set. Use Auto-detect or paste codes in the Paste Codes tab.</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with tab2:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        pasted = st.text_area("Paste material codes (one per line):", height=200, placeholder="MAT001\nMAT002\nMAT003")
        if st.button("📥  Load Codes", type="primary"):
            codes = [c.strip().upper() for c in pasted.split('\n') if c.strip()]
            if codes:
                st.session_state.material_codes = codes
                st.success(f"Loaded {len(codes)} material codes")
                st.rerun()
            else:
                st.warning("No codes found in pasted text")
        st.markdown('</div>', unsafe_allow_html=True)

    with tab3:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown(section_title("Column Reference", "blue", "📖"), unsafe_allow_html=True)
        ref = pd.DataFrame([
            ["Material Code",     "Col 1",  "Primary lookup key"],
            ["Description",       "Col 2",  "From Branch CDSS"],
            ["Material Type",     "Col 3",  "Branch CDSS (ZME/ZMS/ZLC/ZMD)"],
            ["Branch SOH",        "Col 4",  "Branch CDSS stock on hand"],
            ["Central SOH",       "Col 4",  "Central Warehouse stock on hand"],
            ["National SOH",      "Col 4",  "National Branches stock on hand"],
            ["AMC",               "Col 5",  "Central Warehouse — avg monthly consumption"],
            ["MOS Central",       "Calc",   "= Central SOH / AMC"],
            ["Branch Forecast",   "Col 7",  "Branch CDSS forecast quantity"],
            ["Delivered Qty",     "Col 8",  "Branch CDSS delivered quantity"],
            ["Fill Rate Qty %",   "Calc",   "= Delivered / Forecast"],
            ["Forecast Value",    "Col 10", "Branch CDSS forecast value"],
            ["Delivered Value",   "Col 11", "Branch CDSS delivered value"],
            ["Fill Rate Value %", "Calc",   "= Delivered Value / Forecast Value"],
        ], columns=["Column", "Source", "Description"])
        st.dataframe(ref, use_container_width=True, hide_index=True)
        st.markdown('</div>', unsafe_allow_html=True)