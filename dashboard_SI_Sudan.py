import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import folium
from streamlit_folium import st_folium
import numpy as np
from datetime import datetime, date
import warnings
warnings.filterwarnings("ignore")

# ══════════════════════════════════════════════════════════════
# PAGE CONFIG
# ══════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="SI Sudan · IM Dashboard",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ══════════════════════════════════════════════════════════════
# GLOBAL CSS — dark humanitarian aesthetic
# ══════════════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Sans:ital,wght@0,300;0,400;0,500;1,300&display=swap');

/* ── Root tokens ── */
:root {
  --si-navy:   #0A1628;
  --si-blue:   #1A3A6B;
  --si-accent: #E8502A;
  --si-gold:   #F5A623;
  --si-teal:   #0D9488;
  --si-green:  #16A34A;
  --si-slate:  #1E293B;
  --si-muted:  #64748B;
  --si-border: rgba(255,255,255,0.07);
  --si-glass:  rgba(255,255,255,0.04);
  --si-text:   #E2E8F0;
  --si-dim:    #94A3B8;
  --radius:    12px;
}

/* ── Base ── */
html, body, [data-testid="stAppViewContainer"] {
  background: var(--si-navy) !important;
  color: var(--si-text) !important;
  font-family: 'DM Sans', sans-serif;
}
[data-testid="stSidebar"] {
  background: var(--si-slate) !important;
  border-right: 1px solid var(--si-border);
}
[data-testid="stHeader"] { background: transparent !important; }

/* ── Typography ── */
h1,h2,h3,h4 { font-family: 'Syne', sans-serif !important; }

/* ── Metric cards ── */
.metric-card {
  background: var(--si-glass);
  border: 1px solid var(--si-border);
  border-radius: var(--radius);
  padding: 1.25rem 1.5rem;
  position: relative;
  overflow: hidden;
  transition: transform .2s, box-shadow .2s;
}
.metric-card:hover { transform: translateY(-2px); box-shadow: 0 8px 32px rgba(0,0,0,.4); }
.metric-card::before {
  content: '';
  position: absolute; top: 0; left: 0; right: 0; height: 3px;
}
.card-wash::before  { background: linear-gradient(90deg,#0EA5E9,#38BDF8); }
.card-fsl::before   { background: linear-gradient(90deg,#16A34A,#4ADE80); }
.card-shelter::before { background: linear-gradient(90deg,#D97706,#FBBF24); }
.card-cva::before   { background: linear-gradient(90deg,#E8502A,#FB923C); }
.card-meal::before  { background: linear-gradient(90deg,#7C3AED,#A78BFA); }
.card-total::before { background: linear-gradient(90deg,#0D9488,#2DD4BF); }

.metric-label {
  font-size: 0.72rem; font-weight: 500; letter-spacing: .08em;
  text-transform: uppercase; color: var(--si-dim); margin-bottom: .4rem;
}
.metric-value {
  font-family: 'Syne', sans-serif;
  font-size: 2rem; font-weight: 800; color: #fff; line-height: 1;
}
.metric-sub { font-size: 0.78rem; color: var(--si-dim); margin-top: .35rem; }
.metric-icon { font-size: 1.6rem; position: absolute; top: 1rem; right: 1.2rem; opacity: .35; }

/* ── Section headers ── */
.section-head {
  font-family: 'Syne', sans-serif;
  font-size: 1.05rem; font-weight: 700;
  color: var(--si-text);
  border-left: 3px solid var(--si-accent);
  padding-left: .75rem; margin: 1.5rem 0 1rem;
  letter-spacing: .02em;
}

/* ── Alert badges ── */
.badge {
  display: inline-block; padding: 2px 10px; border-radius: 20px;
  font-size: 0.72rem; font-weight: 600; letter-spacing:.04em;
}
.badge-green  { background:#166534; color:#86EFAC; }
.badge-yellow { background:#78350F; color:#FDE68A; }
.badge-red    { background:#7F1D1D; color:#FCA5A5; }

/* ── Progress bar ── */
.prog-wrap { background: rgba(255,255,255,.07); border-radius: 6px; height: 8px; overflow: hidden; }
.prog-bar  { height: 100%; border-radius: 6px; transition: width .6s ease; }

/* ── Login ── */
.login-wrap {
  max-width: 420px; margin: 8vh auto 0;
  background: var(--si-slate);
  border: 1px solid var(--si-border);
  border-radius: 20px; padding: 3rem 2.5rem;
  box-shadow: 0 30px 80px rgba(0,0,0,.5);
}
.login-logo { font-family:'Syne',sans-serif; font-size:1.8rem; font-weight:800; color:#fff; }
.login-sub  { color:var(--si-dim); font-size:.9rem; margin-top:.3rem; margin-bottom:2rem; }

/* ── Sidebar nav ── */
.sidebar-logo {
  font-family:'Syne',sans-serif; font-size:1.2rem; font-weight:800;
  color:#fff; padding:1rem 0 .5rem; line-height:1.2;
}
.sidebar-mission { font-size:.72rem; color:var(--si-dim); letter-spacing:.05em; text-transform:uppercase; }
.sidebar-divider { border:none; border-top:1px solid var(--si-border); margin:1rem 0; }

/* ── Plotly chart background ── */
.js-plotly-plot .plotly .main-svg { border-radius: 10px; }

/* ── Streamlit overrides ── */
[data-testid="stSelectbox"] > div > div,
[data-testid="stMultiSelect"] > div > div {
  background: var(--si-glass) !important;
  border-color: var(--si-border) !important;
  color: var(--si-text) !important;
}
.stButton > button {
  background: var(--si-accent) !important;
  color: #fff !important; border: none !important;
  border-radius: 8px !important; font-family: 'DM Sans', sans-serif !important;
  font-weight: 600 !important; letter-spacing:.03em !important;
}
.stButton > button:hover { opacity: .88 !important; }
[data-testid="stTextInput"] input {
  background: rgba(255,255,255,.06) !important;
  border: 1px solid var(--si-border) !important;
  color: var(--si-text) !important; border-radius: 8px !important;
}
label { color: var(--si-dim) !important; font-size:.82rem !important; }
[data-testid="stMetricValue"] { color:#fff !important; }

/* ── Tab styling ── */
[data-testid="stTabs"] [role="tab"] {
  font-family:'Syne',sans-serif; font-weight:600;
  color: var(--si-dim) !important;
}
[data-testid="stTabs"] [role="tab"][aria-selected="true"] {
  color:#fff !important;
  border-bottom: 2px solid var(--si-accent) !important;
}

/* ── Dataframe ── */
[data-testid="stDataFrame"] { border-radius: 10px; overflow: hidden; }

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 5px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--si-muted); border-radius: 3px; }
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
# PLOTLY THEME
# ══════════════════════════════════════════════════════════════
PLOT_BG   = "rgba(0,0,0,0)"
PAPER_BG  = "rgba(0,0,0,0)"
FONT_CLR  = "#94A3B8"
GRID_CLR  = "rgba(255,255,255,0.06)"
COLORS    = ["#0EA5E9","#16A34A","#F5A623","#E8502A","#7C3AED","#0D9488","#EC4899","#F59E0B"]

def apply_theme(fig, height=340):
    fig.update_layout(
        height=height,
        paper_bgcolor=PAPER_BG,
        plot_bgcolor=PLOT_BG,
        font=dict(family="DM Sans", color=FONT_CLR, size=12),
        margin=dict(l=16, r=16, t=28, b=16),
        legend=dict(
            bgcolor="rgba(0,0,0,0)", font=dict(color=FONT_CLR, size=11),
            bordercolor="rgba(255,255,255,.1)", borderwidth=1
        ),
        colorway=COLORS,
    )
    fig.update_xaxes(showgrid=False, zeroline=False, color=FONT_CLR,
                     tickfont=dict(color=FONT_CLR, size=11))
    fig.update_yaxes(gridcolor=GRID_CLR, zeroline=False, color=FONT_CLR,
                     tickfont=dict(color=FONT_CLR, size=11))
    return fig

# ══════════════════════════════════════════════════════════════
# LOGIN
# ══════════════════════════════════════════════════════════════
CREDENTIALS = {"im_manager": "15062026"}

def login_page():
    st.markdown("""
    <div class='login-wrap'>
      <div class='login-logo'>🌍 SI Sudan</div>
      <div class='login-sub'>Information Management Dashboard<br>Solidarites International · Sudan Mission</div>
    </div>
    """, unsafe_allow_html=True)

    col_l, col_m, col_r = st.columns([1, 1.4, 1])
    with col_m:
        st.markdown("<br>", unsafe_allow_html=True)
        username = st.text_input("Username", placeholder="im_manager")
        password = st.text_input("Password", type="password", placeholder="••••••••")
        login_btn = st.button("Sign In →", use_container_width=True)

        if login_btn:
            if username in CREDENTIALS and CREDENTIALS[username] == password:
                st.session_state["auth"] = True
                st.session_state["user"] = username
                st.rerun()
            else:
                st.error("Invalid credentials. Please try again.")

        st.markdown("""
        <div style='text-align:center;margin-top:1.5rem;font-size:.75rem;color:#475569;'>
        Restricted access · Solidarites International © 2026
        </div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
# DATA LOADING
# ══════════════════════════════════════════════════════════════
@st.cache_data(show_spinner=False)
def load_data(file):
    xls = pd.ExcelFile(file)
    dfs = {}
    for sheet in xls.sheet_names:
        try:
            df = pd.read_excel(xls, sheet_name=sheet, engine="openpyxl")
            dfs[sheet] = df
        except Exception:
            pass
    return dfs

# ══════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════
def fmt_num(n, decimals=0):
    if pd.isna(n): return "—"
    if n >= 1_000_000: return f"{n/1_000_000:.1f}M"
    if n >= 1_000: return f"{n/1_000:.1f}K"
    return f"{n:,.{decimals}f}"

def badge(status):
    s = str(status).lower()
    if "on track" in s or "paid" in s or "functional" in s and "non" not in s:
        return f"<span class='badge badge-green'>{status}</span>"
    elif "risk" in s or "pending" in s or "partial" in s or "low" in s:
        return f"<span class='badge badge-yellow'>{status}</span>"
    elif "off" in s or "fail" in s or "non" in s or "break" in s or "cancel" in s:
        return f"<span class='badge badge-red'>{status}</span>"
    return f"<span class='badge badge-green'>{status}</span>"

def metric_card(label, value, sub="", card_class="", icon=""):
    return f"""
    <div class='metric-card {card_class}'>
      <div class='metric-icon'>{icon}</div>
      <div class='metric-label'>{label}</div>
      <div class='metric-value'>{value}</div>
      <div class='metric-sub'>{sub}</div>
    </div>"""

def section(title):
    st.markdown(f"<div class='section-head'>{title}</div>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
# MAP BUILDER
# ══════════════════════════════════════════════════════════════
def build_map(df_ben):
    # Guard: GPS columns may be absent depending on the uploaded file
    gps_cols = [c for c in ["GPS_Latitude","GPS_Longitude"] if c in df_ben.columns]
    if len(gps_cols) < 2:
        m = folium.Map(location=[14.5, 29.5], zoom_start=5,
                       tiles="CartoDB dark_matter", attr="CartoDB")
        folium.Marker([14.5, 29.5],
                      popup="No GPS data available in this file.",
                      tooltip="No GPS data").add_to(m)
        return m

    df_map = df_ben.dropna(subset=["GPS_Latitude","GPS_Longitude"]).copy()
    df_map = df_map[
        (pd.to_numeric(df_map["GPS_Latitude"], errors="coerce").between(8, 24)) &
        (pd.to_numeric(df_map["GPS_Longitude"], errors="coerce").between(20, 40))
    ]
    m = folium.Map(
        location=[14.5, 29.5],
        zoom_start=5,
        tiles="CartoDB dark_matter",
        attr="CartoDB",
    )

    sector_colors_map = {
        "WASH": "#0EA5E9",
        "FSL": "#16A34A",
        "Shelter & NFI": "#F5A623",
        "Cash & Voucher Assistance": "#E8502A",
    }

    for _, row in df_map.iterrows():
        sector = str(row.get("Sector", ""))
        color  = sector_colors_map.get(sector, "#94A3B8")
        folium.CircleMarker(
            location=[row["GPS_Latitude"], row["GPS_Longitude"]],
            radius=5,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.7,
            weight=0.5,
            popup=folium.Popup(
                f"""<b>{row.get('Beneficiary_ID','')}</b><br>
                State: {row.get('State','')}<br>
                Sector: {sector}<br>
                Status: {row.get('Displacement_Status','')}""",
                max_width=200
            ),
            tooltip=f"{row.get('Locality','')} · {sector}"
        ).add_to(m)

    # Legend
    legend_html = """
    <div style="position:fixed;bottom:30px;left:30px;z-index:9999;
         background:rgba(15,23,42,.92);border:1px solid rgba(255,255,255,.15);
         border-radius:10px;padding:12px 16px;font-family:'DM Sans',sans-serif;">
      <div style="font-weight:700;font-size:12px;color:#e2e8f0;margin-bottom:8px;letter-spacing:.06em;text-transform:uppercase;">Sectors</div>
      <div style="display:flex;flex-direction:column;gap:5px;">
        <div><span style="background:#0EA5E9;width:10px;height:10px;border-radius:50%;display:inline-block;margin-right:6px;"></span><span style="color:#94a3b8;font-size:11px;">WASH</span></div>
        <div><span style="background:#16A34A;width:10px;height:10px;border-radius:50%;display:inline-block;margin-right:6px;"></span><span style="color:#94a3b8;font-size:11px;">FSL</span></div>
        <div><span style="background:#F5A623;width:10px;height:10px;border-radius:50%;display:inline-block;margin-right:6px;"></span><span style="color:#94a3b8;font-size:11px;">Shelter & NFI</span></div>
        <div><span style="background:#E8502A;width:10px;height:10px;border-radius:50%;display:inline-block;margin-right:6px;"></span><span style="color:#94a3b8;font-size:11px;">Cash & Voucher</span></div>
      </div>
    </div>"""
    m.get_root().html.add_child(folium.Element(legend_html))
    return m

# ══════════════════════════════════════════════════════════════
# PAGES
# ══════════════════════════════════════════════════════════════

def page_overview(dfs):
    df_ben  = dfs.get("Beneficiary_Registration", pd.DataFrame())
    df_wash = dfs.get("WASH_Monitoring", pd.DataFrame())
    df_fsl  = dfs.get("FSL_Distribution", pd.DataFrame())
    df_cva  = dfs.get("CVA_Cash_Transfers", pd.DataFrame())

    total_ben    = len(df_ben)
    active_ben   = len(df_ben[df_ben.get("Registration_Status","") == "Active"]) if "Registration_Status" in df_ben else total_ben
    wash_reached = int(df_wash["Reached_Beneficiaries"].sum()) if "Reached_Beneficiaries" in df_wash else 0
    fsl_hh       = int(df_fsl["HH_Reached"].sum()) if "HH_Reached" in df_fsl else 0
    cva_paid     = df_cva[df_cva.get("Transfer_Status","") == "Paid"]["Transfer_Value_USD"].sum() if "Transfer_Value_USD" in df_cva else 0
    states_nb    = df_ben["State"].nunique() if "State" in df_ben else 0

    # ── KPI row 1 ──
    section("Key Program Metrics")
    c1,c2,c3,c4,c5,c6 = st.columns(6)
    cards = [
        (c1, "Total Beneficiaries", fmt_num(total_ben), f"{active_ben:,} active", "card-total", "👤"),
        (c2, "WASH Individuals Reached", fmt_num(wash_reached), "cumulative", "card-wash", "💧"),
        (c3, "FSL Households Reached", fmt_num(fsl_hh), "all distributions", "card-fsl", "🌾"),
        (c4, "Cash Transferred", f"${fmt_num(cva_paid)}", "USD paid out", "card-cva", "💵"),
        (c5, "States Covered", str(states_nb), "operational areas", "card-shelter", "🗺️"),
        (c6, "Reporting Period", "2025–2026", "Jan 2025 – Apr 2026", "card-meal", "📅"),
    ]
    for col, label, value, sub, cls, icon in cards:
        with col:
            st.markdown(metric_card(label, value, sub, cls, icon), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Row 2: Sector split + Displacement ──
    section("Beneficiary Profile")
    col_a, col_b, col_c = st.columns([1.1,1,1])

    with col_a:
        if "Sector" in df_ben:
            sec_cnt = df_ben["Sector"].value_counts().reset_index()
            sec_cnt.columns = ["Sector","Count"]
            fig = px.pie(sec_cnt, values="Count", names="Sector",
                         color_discrete_sequence=COLORS, hole=0.55)
            fig.update_traces(textposition="outside", textfont_size=11,
                              marker=dict(line=dict(color="rgba(0,0,0,0)",width=0)))
            fig.update_layout(title=dict(text="Beneficiaries by Sector", font=dict(color="#fff",size=13,family="Syne")))
            apply_theme(fig, 300)
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar":False})

    with col_b:
        if "Displacement_Status" in df_ben:
            disp = df_ben["Displacement_Status"].value_counts().reset_index()
            disp.columns = ["Status","Count"]
            fig = px.bar(disp, x="Count", y="Status", orientation="h",
                         color="Status", color_discrete_sequence=COLORS)
            fig.update_layout(showlegend=False,
                title=dict(text="Displacement Status", font=dict(color="#fff",size=13,family="Syne")))
            apply_theme(fig, 300)
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar":False})

    with col_c:
        if "Vulnerability_Level" in df_ben:
            vuln = df_ben["Vulnerability_Level"].value_counts().reset_index()
            vuln.columns = ["Level","Count"]
            fig = px.bar(vuln, x="Level", y="Count", color="Level",
                         color_discrete_sequence=["#E8502A","#F5A623","#16A34A"])
            fig.update_layout(showlegend=False,
                title=dict(text="Vulnerability Level", font=dict(color="#fff",size=13,family="Syne")))
            apply_theme(fig, 300)
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar":False})

    # ── Registration trend ──
    section("Beneficiary Registration Trend")
    if "Registration_Date" in df_ben:
        df_ben2 = df_ben.copy()
        df_ben2["Registration_Date"] = pd.to_datetime(df_ben2["Registration_Date"], errors="coerce")
        df_trend = df_ben2.dropna(subset=["Registration_Date"])
        df_trend["Month"] = df_trend["Registration_Date"].dt.to_period("M").astype(str)
        trend = df_trend.groupby(["Month","Sector"]).size().reset_index(name="Count")
        fig = px.area(trend, x="Month", y="Count", color="Sector",
                      color_discrete_sequence=COLORS, line_group="Sector")
        fig.update_traces(line=dict(width=2))
        fig.update_layout(title=dict(text="Monthly Registrations by Sector",
                          font=dict(color="#fff",size=13,family="Syne")))
        apply_theme(fig, 320)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar":False})


def page_map(dfs):
    section("Geographic Coverage — Beneficiary Locations")
    df_ben = dfs.get("Beneficiary_Registration", pd.DataFrame())

    # Filters
    col1, col2, col3 = st.columns(3)
    with col1:
        states_all = ["All"] + sorted(df_ben["State"].dropna().unique().tolist()) if "State" in df_ben else ["All"]
        state_sel = st.selectbox("Filter by State", states_all)
    with col2:
        sectors_all = ["All"] + sorted(df_ben["Sector"].dropna().unique().tolist()) if "Sector" in df_ben else ["All"]
        sector_sel = st.selectbox("Filter by Sector", sectors_all)
    with col3:
        disp_all = ["All"] + sorted(df_ben["Displacement_Status"].dropna().unique().tolist()) if "Displacement_Status" in df_ben else ["All"]
        disp_sel = st.selectbox("Filter by Displacement", disp_all)

    df_f = df_ben.copy()
    if state_sel != "All":  df_f = df_f[df_f["State"] == state_sel]
    if sector_sel != "All": df_f = df_f[df_f["Sector"] == sector_sel]
    if disp_sel != "All":   df_f = df_f[df_f["Displacement_Status"] == disp_sel]

    # Stats strip
    c1,c2,c3,c4 = st.columns(4)
    with c1: st.markdown(metric_card("Beneficiaries shown", fmt_num(len(df_f)), "", "card-total", "📍"), unsafe_allow_html=True)
    with c2: st.markdown(metric_card("States", str(df_f["State"].nunique() if "State" in df_f else 0), "", "card-wash", "🗺️"), unsafe_allow_html=True)
    with c3: st.markdown(metric_card("Localities", str(df_f["Locality"].nunique() if "Locality" in df_f else 0), "", "card-fsl", "📌"), unsafe_allow_html=True)
    with c4:
        fem = len(df_f[df_f["Sex"]=="Female"]) if "Sex" in df_f else 0
        pct = f"{100*fem/len(df_f):.0f}% female" if len(df_f) > 0 else "—"
        st.markdown(metric_card("Gender split", pct, "", "card-cva", "♀"), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    col_map, col_bar = st.columns([2, 1])
    with col_map:
        m = build_map(df_f)
        st_folium(m, use_container_width=True, height=500, returned_objects=[])

    with col_bar:
        if "State" in df_f and len(df_f) > 0:
            by_state = df_f.groupby("State").size().reset_index(name="Count").sort_values("Count")
            fig = px.bar(by_state, x="Count", y="State", orientation="h",
                         color="Count", color_continuous_scale=["#1A3A6B","#0EA5E9"])
            fig.update_layout(showlegend=False, coloraxis_showscale=False,
                title=dict(text="Beneficiaries by State", font=dict(color="#fff",size=13,family="Syne")))
            apply_theme(fig, 240)
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar":False})

        if "Sector" in df_f and "State" in df_f and len(df_f) > 0:
            heat = df_f.groupby(["State","Sector"]).size().reset_index(name="Count")
            fig = px.density_heatmap(heat, x="Sector", y="State", z="Count",
                                     color_continuous_scale="Blues")
            fig.update_layout(
                title=dict(text="Coverage Heatmap", font=dict(color="#fff",size=13,family="Syne")),
                coloraxis_colorbar=dict(tickfont=dict(color=FONT_CLR)),
            )
            apply_theme(fig, 240)
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar":False})


def page_wash(dfs):
    df = dfs.get("WASH_Monitoring", pd.DataFrame())
    if df.empty:
        st.warning("WASH_Monitoring sheet not found."); return

    section("WASH Program Monitoring")

    # Filters
    col1, col2 = st.columns(2)
    with col1:
        states = ["All"] + sorted(df["State"].dropna().unique().tolist()) if "State" in df else ["All"]
        state_sel = st.selectbox("State", states, key="wash_state")
    with col2:
        acts = ["All"] + sorted(df["Activity_Type"].dropna().unique().tolist()) if "Activity_Type" in df else ["All"]
        act_sel = st.selectbox("Activity Type", acts, key="wash_act")

    df_f = df.copy()
    if state_sel != "All": df_f = df_f[df_f["State"] == state_sel]
    if act_sel != "All":   df_f = df_f[df_f["Activity_Type"] == act_sel]

    # KPIs
    reached   = int(df_f["Reached_Beneficiaries"].sum()) if "Reached_Beneficiaries" in df_f else 0
    target    = int(df_f["Target_Beneficiaries"].sum())  if "Target_Beneficiaries" in df_f else 1
    pct_reach = reached/target if target > 0 else 0
    water_vol = int(df_f["Water_Volume_Liters"].sum()) if "Water_Volume_Liters" in df_f else 0
    latrines  = int(df_f["Latrine_Units_Built"].sum())  if "Latrine_Units_Built" in df_f else 0
    hygiene   = int(df_f["Hygiene_Kits_Dist"].sum())    if "Hygiene_Kits_Dist" in df_f else 0

    c1,c2,c3,c4,c5 = st.columns(5)
    with c1: st.markdown(metric_card("Individuals Reached",fmt_num(reached),f"{pct_reach:.0%} of target","card-wash","💧"), unsafe_allow_html=True)
    with c2: st.markdown(metric_card("Target Beneficiaries",fmt_num(target),"planned","card-total","🎯"), unsafe_allow_html=True)
    with c3: st.markdown(metric_card("Water Distributed",fmt_num(water_vol)+" L","litres","card-wash","🚰"), unsafe_allow_html=True)
    with c4: st.markdown(metric_card("Latrines Built",fmt_num(latrines),"units","card-fsl","🏗️"), unsafe_allow_html=True)
    with c5: st.markdown(metric_card("Hygiene Kits",fmt_num(hygiene),"distributed","card-shelter","🧴"), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    col_a, col_b = st.columns(2)

    with col_a:
        if "Activity_Type" in df_f:
            grp = df_f.groupby("Activity_Type")[["Target_Beneficiaries","Reached_Beneficiaries"]].sum().reset_index()
            fig = go.Figure()
            fig.add_bar(name="Target", x=grp["Activity_Type"], y=grp["Target_Beneficiaries"],
                        marker_color="#1E3A6E", marker_line_width=0)
            fig.add_bar(name="Reached", x=grp["Activity_Type"], y=grp["Reached_Beneficiaries"],
                        marker_color="#0EA5E9", marker_line_width=0)
            fig.update_layout(barmode="group",
                title=dict(text="Target vs Reached by Activity", font=dict(color="#fff",size=13,family="Syne")))
            apply_theme(fig, 340)
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar":False})

    with col_b:
        if "Functionality_Status" in df_f:
            func = df_f["Functionality_Status"].value_counts().reset_index()
            func.columns = ["Status","Count"]
            colors_func = {"Fully Functional":"#16A34A","Partially Functional":"#F5A623",
                           "Non-Functional":"#E8502A","Under Construction":"#7C3AED"}
            fig = px.pie(func, values="Count", names="Status", hole=0.52,
                         color="Status", color_discrete_map=colors_func)
            fig.update_layout(title=dict(text="Infrastructure Functionality", font=dict(color="#fff",size=13,family="Syne")))
            apply_theme(fig, 340)
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar":False})

    # Gender split
    section("Gender Breakdown")
    if "Reached_Female" in df_f and "Reached_Male" in df_f:
        col_x, col_y = st.columns(2)
        with col_x:
            total_f = df_f["Reached_Female"].sum()
            total_m = df_f["Reached_Male"].sum()
            fig = go.Figure(go.Bar(
                x=["Female","Male"],
                y=[total_f, total_m],
                marker_color=["#EC4899","#0EA5E9"],
                text=[fmt_num(total_f), fmt_num(total_m)],
                textposition="outside",
                textfont=dict(color="#fff", size=13)
            ))
            fig.update_layout(title=dict(text="Sex Disaggregation — WASH",
                font=dict(color="#fff",size=13,family="Syne")))
            apply_theme(fig, 280)
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar":False})
        with col_y:
            if "State" in df_f:
                sg = df_f.groupby("State")[["Reached_Female","Reached_Male"]].sum().reset_index()
                fig = px.bar(sg, x="State", y=["Reached_Female","Reached_Male"],
                             color_discrete_map={"Reached_Female":"#EC4899","Reached_Male":"#0EA5E9"},
                             barmode="stack")
                fig.update_layout(title=dict(text="Sex by State",
                    font=dict(color="#fff",size=13,family="Syne")))
                apply_theme(fig, 280)
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar":False})


def page_fsl(dfs):
    df = dfs.get("FSL_Distribution", pd.DataFrame())
    if df.empty:
        st.warning("FSL_Distribution sheet not found."); return

    section("Food Security & Livelihoods — Distribution Tracking")

    col1, col2, col3 = st.columns(3)
    with col1:
        states = ["All"] + sorted(df["State"].dropna().unique().tolist()) if "State" in df else ["All"]
        state_sel = st.selectbox("State", states, key="fsl_state")
    with col2:
        commodities = ["All"] + sorted(df["Commodity_Type"].dropna().unique().tolist()) if "Commodity_Type" in df else ["All"]
        comm_sel = st.selectbox("Commodity", commodities, key="fsl_comm")
    with col3:
        donors = ["All"] + sorted(df["Donor"].dropna().unique().tolist()) if "Donor" in df else ["All"]
        donor_sel = st.selectbox("Donor", donors, key="fsl_donor")

    df_f = df.copy()
    if state_sel != "All":  df_f = df_f[df_f["State"] == state_sel]
    if comm_sel != "All":   df_f = df_f[df_f["Commodity_Type"] == comm_sel]
    if donor_sel != "All":  df_f = df_f[df_f["Donor"] == donor_sel]

    hh_target  = int(df_f["HH_Targeted"].sum())  if "HH_Targeted" in df_f else 0
    hh_reached = int(df_f["HH_Reached"].sum())   if "HH_Reached" in df_f else 0
    qty_plan   = df_f["Quantity_Planned"].sum()   if "Quantity_Planned" in df_f else 0
    qty_dist   = df_f["Quantity_Distributed"].sum() if "Quantity_Distributed" in df_f else 0
    fem_hh     = int(df_f["Female_HHH_Reached"].sum()) if "Female_HHH_Reached" in df_f else 0
    pct_fem    = fem_hh/hh_reached if hh_reached > 0 else 0

    c1,c2,c3,c4,c5 = st.columns(5)
    with c1: st.markdown(metric_card("HH Reached",fmt_num(hh_reached),f"of {fmt_num(hh_target)} targeted","card-fsl","🏠"), unsafe_allow_html=True)
    with c2: st.markdown(metric_card("Coverage Rate",f"{hh_reached/hh_target:.0%}" if hh_target else "—","achievement","card-total","📊"), unsafe_allow_html=True)
    with c3: st.markdown(metric_card("Qty Distributed",fmt_num(qty_dist),f"of {fmt_num(qty_plan)} planned","card-wash","📦"), unsafe_allow_html=True)
    with c4: st.markdown(metric_card("Female-headed HH",fmt_num(fem_hh),f"{pct_fem:.0%} of reached","card-cva","♀"), unsafe_allow_html=True)
    with c5:
        pipeline_breaks = len(df_f[df_f["Pipeline_Status"]=="Pipeline break"]) if "Pipeline_Status" in df_f else 0
        st.markdown(metric_card("Pipeline Breaks",str(pipeline_breaks),"supply chain alerts","card-shelter","⚠️"), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    col_a, col_b, col_c = st.columns(3)

    with col_a:
        if "Commodity_Type" in df_f:
            comm = df_f.groupby("Commodity_Type")["HH_Reached"].sum().reset_index().sort_values("HH_Reached",ascending=True).tail(8)
            fig = px.bar(comm, x="HH_Reached", y="Commodity_Type", orientation="h",
                         color="HH_Reached", color_continuous_scale=["#14532D","#4ADE80"])
            fig.update_layout(showlegend=False, coloraxis_showscale=False,
                title=dict(text="HH Reached by Commodity", font=dict(color="#fff",size=13,family="Syne")))
            apply_theme(fig, 340)
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar":False})

    with col_b:
        if "Pipeline_Status" in df_f:
            pipe = df_f["Pipeline_Status"].value_counts().reset_index()
            pipe.columns = ["Status","Count"]
            colors_pipe = {"In stock":"#16A34A","Low stock":"#F5A623",
                           "Pipeline break":"#E8502A","Awaiting delivery":"#7C3AED"}
            fig = px.pie(pipe, values="Count", names="Status", hole=0.5,
                         color="Status", color_discrete_map=colors_pipe)
            fig.update_layout(title=dict(text="Pipeline Status", font=dict(color="#fff",size=13,family="Syne")))
            apply_theme(fig, 340)
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar":False})

    with col_c:
        if "Donor" in df_f:
            don = df_f.groupby("Donor")["HH_Reached"].sum().reset_index()
            fig = px.bar(don, x="Donor", y="HH_Reached", color="Donor",
                         color_discrete_sequence=COLORS)
            fig.update_layout(showlegend=False,
                title=dict(text="HH Reached by Donor", font=dict(color="#fff",size=13,family="Syne")))
            apply_theme(fig, 340)
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar":False})

    # Satisfaction
    if "Beneficiary_Satisfaction" in df_f:
        section("Post-Distribution Monitoring — Beneficiary Satisfaction")
        sat = df_f["Beneficiary_Satisfaction"].value_counts().reset_index()
        sat.columns = ["Level","Count"]
        colors_sat = {"Above 80%":"#16A34A","60–80%":"#F5A623","Below 60%":"#E8502A","N/A":"#475569"}
        fig = px.bar(sat, x="Level", y="Count", color="Level", color_discrete_map=colors_sat,
                     text="Count")
        fig.update_traces(textposition="outside", textfont=dict(color="#fff"))
        fig.update_layout(showlegend=False,
            title=dict(text="Satisfaction Rate Distribution", font=dict(color="#fff",size=13,family="Syne")))
        apply_theme(fig, 280)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar":False})


def page_cva(dfs):
    df = dfs.get("CVA_Cash_Transfers", pd.DataFrame())
    if df.empty:
        st.warning("CVA_Cash_Transfers sheet not found."); return

    section("Cash & Voucher Assistance — Transfer Tracking")

    col1, col2 = st.columns(2)
    with col1:
        states = ["All"] + sorted(df["State"].dropna().unique().tolist()) if "State" in df else ["All"]
        state_sel = st.selectbox("State", states, key="cva_state")
    with col2:
        types = ["All"] + sorted(df["Transfer_Type"].dropna().unique().tolist()) if "Transfer_Type" in df else ["All"]
        type_sel = st.selectbox("Transfer Type", types, key="cva_type")

    df_f = df.copy()
    if state_sel != "All": df_f = df_f[df_f["State"] == state_sel]
    if type_sel != "All":  df_f = df_f[df_f["Transfer_Type"] == type_sel]

    paid    = df_f[df_f["Transfer_Status"]=="Paid"]  if "Transfer_Status" in df_f else df_f
    pending = df_f[df_f["Transfer_Status"]=="Pending"] if "Transfer_Status" in df_f else pd.DataFrame()
    failed  = df_f[df_f["Transfer_Status"]=="Failed"]  if "Transfer_Status" in df_f else pd.DataFrame()

    total_usd   = paid["Transfer_Value_USD"].sum() if ("Transfer_Value_USD" in paid.columns and len(paid) > 0) else 0
    avg_val     = paid["Transfer_Value_USD"].mean() if ("Transfer_Value_USD" in paid.columns and len(paid) > 0) else 0
    nb_paid     = len(paid)
    nb_pending  = len(pending)
    nb_failed   = len(failed)
    fem_pct     = len(df_f[df_f["Female_Headed_HH"]=="Yes"])/len(df_f) if (len(df_f)>0 and "Female_Headed_HH" in df_f.columns) else 0

    c1,c2,c3,c4,c5,c6 = st.columns(6)
    with c1: st.markdown(metric_card("Total Paid Out",f"${fmt_num(total_usd)}","USD","card-cva","💵"), unsafe_allow_html=True)
    with c2: st.markdown(metric_card("Transfers Paid",fmt_num(nb_paid),"completed","card-fsl","✅"), unsafe_allow_html=True)
    with c3: st.markdown(metric_card("Pending",fmt_num(nb_pending),"awaiting","card-shelter","⏳"), unsafe_allow_html=True)
    with c4: st.markdown(metric_card("Failed",fmt_num(nb_failed),"to investigate","card-total","❌"), unsafe_allow_html=True)
    with c5: st.markdown(metric_card("Avg Transfer",f"${avg_val:.0f}","per household","card-wash","📊"), unsafe_allow_html=True)
    with c6: st.markdown(metric_card("Female-headed HH",f"{fem_pct:.0%}","of beneficiaries","card-meal","♀"), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    col_a, col_b = st.columns(2)

    with col_a:
        if "Transfer_Status" in df_f:
            status_cnt = df_f["Transfer_Status"].value_counts().reset_index()
            status_cnt.columns = ["Status","Count"]
            colors_status = {"Paid":"#16A34A","Pending":"#F5A623","Failed":"#E8502A","Cancelled":"#7C3AED"}
            fig = px.pie(status_cnt, values="Count", names="Status", hole=0.55,
                         color="Status", color_discrete_map=colors_status)
            fig.update_layout(title=dict(text="Transfer Status Breakdown", font=dict(color="#fff",size=13,family="Syne")))
            apply_theme(fig, 320)
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar":False})

    with col_b:
        if "Payment_Method" in df_f:
            pm = df_f.groupby("Payment_Method")["Transfer_Value_USD"].sum().reset_index()
            fig = px.bar(pm, x="Payment_Method", y="Transfer_Value_USD", color="Payment_Method",
                         color_discrete_sequence=COLORS, text_auto=True)
            fig.update_traces(textposition="outside", texttemplate="%{y:,.0f}", textfont=dict(color="#fff",size=10))
            fig.update_layout(showlegend=False,
                title=dict(text="USD Transferred by Payment Method", font=dict(color="#fff",size=13,family="Syne")))
            apply_theme(fig, 320)
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar":False})

    # Timeline
    section("Transfer Timeline")
    if "Transfer_Date" in df_f:
        df_f2 = df_f.copy()
        df_f2["Transfer_Date"] = pd.to_datetime(df_f2["Transfer_Date"], errors="coerce")
        monthly = df_f2.dropna(subset=["Transfer_Date"])
        monthly["Month"] = monthly["Transfer_Date"].dt.to_period("M").astype(str)
        agg = monthly.groupby(["Month","Transfer_Status"])["Transfer_Value_USD"].sum().reset_index()
        fig = px.bar(agg, x="Month", y="Transfer_Value_USD", color="Transfer_Status",
                     color_discrete_map={"Paid":"#16A34A","Pending":"#F5A623","Failed":"#E8502A","Cancelled":"#7C3AED"})
        fig.update_layout(title=dict(text="Monthly Transfer Volume (USD) by Status",
            font=dict(color="#fff",size=13,family="Syne")))
        apply_theme(fig, 300)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar":False})


def page_indicators(dfs):
    df = dfs.get("Indicator_Tracker", pd.DataFrame())
    if df.empty:
        st.warning("Indicator_Tracker sheet not found."); return

    section("Program Indicator Tracker — Results-Based Management")

    # Summary counts
    if "Status" in df:
        on_track = len(df[df["Status"]=="On track"])
        at_risk  = len(df[df["Status"]=="At risk"])
        off_track= len(df[df["Status"]=="Off track"])
        total_ind= len(df)

        c1,c2,c3,c4 = st.columns(4)
        with c1: st.markdown(metric_card("Total Indicators",str(total_ind),"in tracking frame","card-total","📋"), unsafe_allow_html=True)
        with c2: st.markdown(metric_card("On Track",str(on_track),f"{on_track/total_ind:.0%} of indicators","card-fsl","✅"), unsafe_allow_html=True)
        with c3: st.markdown(metric_card("At Risk",str(at_risk),f"{at_risk/total_ind:.0%} of indicators","card-shelter","⚠️"), unsafe_allow_html=True)
        with c4: st.markdown(metric_card("Off Track",str(off_track),f"{off_track/total_ind:.0%} of indicators","card-cva","❌"), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Progress bars per indicator
    if "Sector" in df:
        sectors_u = df["Sector"].unique()
        for sec in sectors_u:
            df_sec = df[df["Sector"]==sec]
            section(f"Sector: {sec}")
            for _, row in df_sec.iterrows():
                indicator = row.get("Indicator","")
                unit = row.get("Unit","")
                target = row.get("Annual Target", None)
                cumul = row.get("Cumulative", None)
                status = str(row.get("Status",""))

                if pd.notna(target) and target not in [None,""] and float(str(target).replace(",","") if str(target) else 0) > 0:
                    try:
                        t = float(str(target).replace(",",""))
                        c_val = float(str(cumul).replace(",","")) if pd.notna(cumul) else 0
                        pct = min(c_val / t, 1.0)
                    except:
                        t, c_val, pct = 0, 0, 0

                    color = "#16A34A" if pct >= 0.80 else "#F5A623" if pct >= 0.60 else "#E8502A"
                    badge_html = badge(status)

                    st.markdown(f"""
                    <div style='margin-bottom:1rem;padding:1rem 1.25rem;background:var(--si-glass);
                         border:1px solid var(--si-border);border-radius:10px;'>
                      <div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:.6rem;'>
                        <span style='font-size:.88rem;font-weight:500;color:var(--si-text);'>{indicator}</span>
                        <span style='display:flex;gap:.5rem;align-items:center;'>
                          {badge_html}
                          <span style='font-size:.78rem;color:var(--si-dim);'>{fmt_num(c_val)} / {fmt_num(t)} {unit}</span>
                        </span>
                      </div>
                      <div class='prog-wrap'>
                        <div class='prog-bar' style='width:{pct*100:.1f}%;background:{color};'></div>
                      </div>
                      <div style='font-size:.72rem;color:var(--si-dim);margin-top:.3rem;'>{pct*100:.1f}% achieved</div>
                    </div>""", unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div style='margin-bottom:.6rem;padding:.8rem 1.25rem;background:var(--si-glass);
                         border:1px solid var(--si-border);border-radius:10px;
                         display:flex;justify-content:space-between;align-items:center;'>
                      <span style='font-size:.88rem;color:var(--si-text);'>{indicator}</span>
                      <span style='font-size:.82rem;color:var(--si-dim);'>{fmt_num(cumul) if pd.notna(cumul) else "—"} {unit}</span>
                    </div>""", unsafe_allow_html=True)

    # Sector comparison chart
    section("Indicator Performance by Sector")
    if "Sector" in df and "Status" in df:
        perf = df.groupby(["Sector","Status"]).size().reset_index(name="Count")
        fig = px.bar(perf, x="Sector", y="Count", color="Status", barmode="stack",
                     color_discrete_map={"On track":"#16A34A","At risk":"#F5A623","Off track":"#E8502A"})
        fig.update_layout(title=dict(text="Indicator Status by Sector",
            font=dict(color="#fff",size=13,family="Syne")))
        apply_theme(fig, 320)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar":False})


def page_data(dfs):
    section("Raw Data Explorer")
    sheet_sel = st.selectbox("Select sheet", list(dfs.keys()))
    df = dfs[sheet_sel]
    col1, col2 = st.columns([3,1])
    with col2:
        st.download_button(
            "⬇ Download CSV", df.to_csv(index=False).encode(),
            file_name=f"{sheet_sel}.csv", mime="text/csv"
        )
    with col1:
        st.markdown(f"**{len(df):,} rows · {len(df.columns)} columns**")
    st.dataframe(df, use_container_width=True, height=520)


# ══════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════
def sidebar_nav(dfs):
    with st.sidebar:
        st.markdown("""
        <div class='sidebar-logo'>
          🌍 SI Sudan<br>
          <span style='font-size:.95rem;font-weight:400;color:#94A3B8;'>IM Dashboard</span>
        </div>
        <div class='sidebar-mission'>Solidarites International · Sudan Mission</div>
        <hr class='sidebar-divider'>
        """, unsafe_allow_html=True)

        uploaded = st.file_uploader("📂 Load Excel Database", type=["xlsx"])

        if uploaded:
            dfs_new = load_data(uploaded)
            st.session_state["dfs"] = dfs_new
            st.success(f"✅ {len(dfs_new)} sheets loaded")

        st.markdown("<hr class='sidebar-divider'>", unsafe_allow_html=True)

        pages = {
            "🏠  Overview":         "overview",
            "🗺️  Geographic Map":   "map",
            "💧  WASH Monitoring":  "wash",
            "🌾  FSL Distribution": "fsl",
            "💵  CVA / Cash":       "cva",
            "📊  Indicator Tracker":"indicators",
            "🗂️  Raw Data":         "data",
        }
        page = st.radio("Navigation", list(pages.keys()), label_visibility="collapsed")

        st.markdown("<hr class='sidebar-divider'>", unsafe_allow_html=True)
        st.markdown(f"""
        <div style='font-size:.72rem;color:#475569;line-height:1.6;'>
          Logged in as <b style='color:#94A3B8;'>{st.session_state.get('user','—')}</b><br>
          Last refresh: {datetime.now().strftime('%d %b %Y %H:%M')}
        </div>""", unsafe_allow_html=True)
        if st.button("🚪 Logout"):
            st.session_state.clear(); st.rerun()

        return pages[page], st.session_state.get("dfs", dfs)


# ══════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════
def main():
    if "auth" not in st.session_state or not st.session_state["auth"]:
        login_page()
        return

    dfs = st.session_state.get("dfs", {})
    page_key, dfs = sidebar_nav(dfs)

    # Page header
    titles = {
        "overview":   ("Program Overview", "Key metrics across all sectors"),
        "map":        ("Geographic Coverage", "Beneficiary distribution across Sudan"),
        "wash":       ("WASH Monitoring", "Water, Sanitation & Hygiene program data"),
        "fsl":        ("Food Security & Livelihoods", "Distribution and pipeline tracking"),
        "cva":        ("Cash & Voucher Assistance", "Transfer tracking and analysis"),
        "indicators": ("Indicator Tracker", "Results-based management framework"),
        "data":       ("Raw Data Explorer", "Browse and export program datasets"),
    }
    title, subtitle = titles.get(page_key, ("Dashboard",""))
    st.markdown(f"""
    <div style='padding:.5rem 0 1.5rem;border-bottom:1px solid var(--si-border);margin-bottom:1.5rem;'>
      <div style='font-family:Syne,sans-serif;font-size:1.8rem;font-weight:800;color:#fff;line-height:1;'>{title}</div>
      <div style='font-size:.85rem;color:#64748B;margin-top:.35rem;'>{subtitle}</div>
    </div>""", unsafe_allow_html=True)

    if not dfs:
        st.markdown("""
        <div style='text-align:center;padding:4rem 2rem;background:var(--si-glass);
             border:1px dashed var(--si-border);border-radius:16px;margin-top:2rem;'>
          <div style='font-size:2.5rem;margin-bottom:1rem;'>📂</div>
          <div style='font-family:Syne,sans-serif;font-size:1.1rem;font-weight:700;color:#fff;margin-bottom:.5rem;'>
            No database loaded
          </div>
          <div style='font-size:.9rem;color:var(--si-dim);'>
            Upload your Excel file using the sidebar to start exploring the dashboard.
          </div>
        </div>""", unsafe_allow_html=True)
        return

    if page_key == "overview":   page_overview(dfs)
    elif page_key == "map":      page_map(dfs)
    elif page_key == "wash":     page_wash(dfs)
    elif page_key == "fsl":      page_fsl(dfs)
    elif page_key == "cva":      page_cva(dfs)
    elif page_key == "indicators": page_indicators(dfs)
    elif page_key == "data":     page_data(dfs)

if __name__ == "__main__":
    main()
