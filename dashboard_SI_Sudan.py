import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import folium
from folium.plugins import MarkerCluster, HeatMap, MiniMap
from streamlit_folium import st_folium
from datetime import datetime
import io, warnings, requests
warnings.filterwarnings("ignore")

# ── KoBoToolbox API ───────────────────────────────────────────────────────────
KOBO_BASE = "https://kf.kobotoolbox.org"  # or https://kobo.humanitarianresponse.info

def kobo_get_token(username, password):
    try:
        r = requests.post(f"{KOBO_BASE}/token/?format=json",
                          data={"username": username, "password": password}, timeout=15)
        if r.status_code == 200:
            return r.json().get("token"), None
        return None, f"HTTP {r.status_code} — Check your credentials or server URL."
    except Exception as e:
        return None, f"Connection error: {e}"

def kobo_header(token):
    return {"Authorization": f"Token {token}"}

def kobo_list_forms(token):
    try:
        r = requests.get(f"{KOBO_BASE}/api/v2/assets/?format=json&asset_type=survey&limit=200",
                         headers=kobo_header(token), timeout=20)
        if r.status_code == 200:
            return r.json().get("results", []), None
        return [], f"HTTP {r.status_code}: {r.text[:300]}"
    except Exception as e:
        return [], str(e)

def kobo_fetch_data(token, uid, label="form"):
    try:
        all_rows = []
        url = f"{KOBO_BASE}/api/v2/assets/{uid}/data/?format=json&limit=500"
        while url:
            r = requests.get(url, headers=kobo_header(token), timeout=30)
            if r.status_code != 200:
                return pd.DataFrame(), f"HTTP {r.status_code}"
            j = r.json()
            all_rows.extend(j.get("results", []))
            url = j.get("next")
        if not all_rows:
            return pd.DataFrame(), None
        df = pd.json_normalize(all_rows)
        df.columns = [c.split("/")[-1] if "/" in c else c for c in df.columns]
        return df, None
    except Exception as e:
        return pd.DataFrame(), str(e)


# ── ReportLab (PDF) ──────────────────────────────────────────────────────────
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors as rl_colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                    Table, TableStyle, HRFlowable, PageBreak)
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    HAS_PDF = True
except ImportError:
    HAS_PDF = False

st.set_page_config(
    page_title="SI Sudan · IM Dashboard",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ══════════════════════════════════════════════════════════════════════════════
# THEME TOKENS
# ══════════════════════════════════════════════════════════════════════════════
DARK = dict(
    bg="#060D1F", surface="#0F1B2D", panel="#131F35",
    border="rgba(99,140,210,0.13)", border2="rgba(99,140,210,0.24)",
    text="#E2E8F0", muted="#64748B", dim="#1E293B",
    navbg="#0F1B2D", navborder="rgba(99,140,210,0.18)",
    card="#131F35", input="#0F1B2D",
    plotbg="rgba(0,0,0,0)", gridc="rgba(255,255,255,0.05)",
    fontc="#64748B", title="#CBD5E1",
    accent="#3B82F6", accent2="#60A5FA",
    sbg="#060D1F",
)
LIGHT = dict(
    bg="#F0F4FA", surface="#FFFFFF", panel="#FFFFFF",
    border="rgba(59,130,246,0.15)", border2="rgba(59,130,246,0.28)",
    text="#1E293B", muted="#64748B", dim="#E2E8F0",
    navbg="#FFFFFF", navborder="rgba(59,130,246,0.15)",
    card="#FFFFFF", input="#F8FAFC",
    plotbg="rgba(0,0,0,0)", gridc="rgba(0,0,0,0.04)",
    fontc="#94A3B8", title="#334155",
    accent="#2563EB", accent2="#3B82F6",
    sbg="#F8FAFC",
)
COLORS  = ["#3B82F6","#10B981","#F59E0B","#EF4444","#8B5CF6","#14B8A6","#EC4899","#F97316"]
SC = {"WASH":"#3B82F6","FSL":"#10B981","Shelter & NFI":"#F59E0B","Cash & Voucher Assistance":"#EF4444"}
CREDENTIALS = {"im_manager": "15062026"}

NAV_ITEMS = [
    ("🏠", "Overview"),("🗺️", "Map"),("💧", "WASH"),
    ("🌾", "FSL"),("💵", "CVA"),("📊", "Indicators"),
    ("🗂️", "Raw Data"),("📄", "Report"),
]

# ══════════════════════════════════════════════════════════════════════════════
# CSS INJECTOR
# ══════════════════════════════════════════════════════════════════════════════
def inject_css(T):
    st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');

:root {{
  --bg:      {T['bg']};
  --surface: {T['surface']};
  --panel:   {T['panel']};
  --border:  {T['border']};
  --border2: {T['border2']};
  --text:    {T['text']};
  --muted:   {T['muted']};
  --dim:     {T['dim']};
  --navbg:   {T['navbg']};
  --navbdr:  {T['navborder']};
  --card:    {T['card']};
  --input:   {T['input']};
  --accent:  {T['accent']};
  --accent2: {T['accent2']};
  --sbg:     {T['sbg']};
  --font:    'Outfit',sans-serif;
  --mono:    'JetBrains Mono',monospace;
  --r:       10px;
}}

*,*::before,*::after {{ box-sizing:border-box; }}
html,body {{ font-family:var(--font); background:var(--bg); color:var(--text); margin:0; }}

/* APP BACKGROUND */
[data-testid="stAppViewContainer"],
[data-testid="stMain"],
.main .block-container {{ background:var(--bg) !important; }}
[data-testid="stHeader"] {{ background:var(--navbg) !important;
  border-bottom:1px solid var(--navbdr) !important; }}
[data-testid="stSidebar"] {{ display:none !important; }}

/* BLOCK CONTAINER */
[data-testid="block-container"] {{
  padding:0 !important; max-width:100% !important;
}}

/* TOP NAV */
.topnav {{
  position:sticky; top:0; z-index:1000;
  background:var(--navbg);
  border-bottom:1px solid var(--navbdr);
  display:flex; align-items:center; gap:0;
  padding:0 2rem;
  backdrop-filter:blur(12px);
  -webkit-backdrop-filter:blur(12px);
}}
.topnav-brand {{
  font-size:1rem; font-weight:800; color:var(--text);
  white-space:nowrap; margin-right:2rem;
  display:flex; align-items:center; gap:8px;
}}
.topnav-brand span {{ color:var(--accent); }}
.nav-tab {{
  padding:0.85rem 1.1rem; cursor:pointer; border:none;
  background:transparent; color:var(--muted);
  font-family:var(--font); font-size:0.84rem; font-weight:500;
  border-bottom:2px solid transparent;
  transition:all 0.15s; white-space:nowrap;
  display:flex; align-items:center; gap:5px;
}}
.nav-tab:hover {{ color:var(--text); }}
.nav-tab.active {{ color:var(--accent); border-bottom-color:var(--accent); font-weight:600; }}
.nav-right {{ margin-left:auto; display:flex; align-items:center; gap:12px; }}
.theme-toggle {{
  background:var(--dim); border:1px solid var(--border);
  border-radius:20px; padding:4px 10px; cursor:pointer;
  font-size:0.78rem; color:var(--muted); font-family:var(--font);
  display:flex; align-items:center; gap:5px; transition:all .15s;
}}
.theme-toggle:hover {{ border-color:var(--border2); color:var(--text); }}
.user-chip {{
  background:var(--dim); border:1px solid var(--border);
  border-radius:20px; padding:4px 12px;
  font-size:0.78rem; color:var(--muted); font-family:var(--font);
}}

/* PAGE CONTENT */
.page-content {{ padding:1.8rem 2.2rem; }}

/* KPI CARDS */
.kpi-card {{
  background:var(--card); border:1px solid var(--border);
  border-radius:var(--r); padding:1.1rem 1.2rem 1rem;
  position:relative; overflow:hidden;
}}
.kpi-card::after {{ content:''; position:absolute; bottom:0; left:0; right:0; height:2px; }}
.kpi-blue::after   {{ background:linear-gradient(90deg,#3B82F6,#60A5FA); }}
.kpi-green::after  {{ background:linear-gradient(90deg,#10B981,#34D399); }}
.kpi-amber::after  {{ background:linear-gradient(90deg,#F59E0B,#FCD34D); }}
.kpi-red::after    {{ background:linear-gradient(90deg,#EF4444,#F87171); }}
.kpi-purple::after {{ background:linear-gradient(90deg,#8B5CF6,#A78BFA); }}
.kpi-teal::after   {{ background:linear-gradient(90deg,#14B8A6,#5EEAD4); }}
.kpi-pink::after   {{ background:linear-gradient(90deg,#EC4899,#F9A8D4); }}

.kpi-label {{ font-size:0.65rem; font-weight:700; letter-spacing:.1em;
  text-transform:uppercase; color:var(--muted); margin-bottom:0.4rem; }}
.kpi-value {{ font-size:1.75rem; font-weight:800; color:var(--text);
  line-height:1; font-family:var(--font); }}
.kpi-sub  {{ font-size:0.7rem; color:var(--muted); margin-top:0.3rem; }}
.kpi-icon {{ position:absolute; top:0.9rem; right:1rem; font-size:1.3rem; opacity:0.15; }}
.kpi-delta {{ font-size:0.7rem; font-weight:700; margin-top:0.35rem;
  display:inline-flex; align-items:center; gap:3px;
  padding:1px 7px; border-radius:20px; }}
.d-up   {{ background:rgba(16,185,129,0.15); color:#34D399; }}
.d-down {{ background:rgba(239,68,68,0.15);  color:#F87171; }}
.d-mid  {{ background:rgba(245,158,11,0.15); color:#FCD34D; }}

/* SECTION HEADER */
.sh {{
  font-size:0.67rem; font-weight:700; letter-spacing:.12em; text-transform:uppercase;
  color:var(--accent2); margin:1.6rem 0 0.9rem;
  display:flex; align-items:center; gap:8px;
}}
.sh::after {{ content:''; flex:1; height:1px; background:var(--border); }}

/* PAGE HEADER */
.ph {{ border-bottom:1px solid var(--border); margin-bottom:1.5rem; padding-bottom:0.9rem; }}
.ph h1 {{ font-size:1.55rem; font-weight:800; color:var(--text); margin:0 0 3px; font-family:var(--font); }}
.ph p  {{ font-size:0.81rem; color:var(--muted) !important; margin:0; }}

/* BADGES */
.badge {{ display:inline-block; padding:2px 9px; border-radius:20px;
  font-size:0.67rem; font-weight:700; letter-spacing:.04em; }}
.bg  {{ background:rgba(16,185,129,0.18);  color:#34D399; }}
.ba  {{ background:rgba(245,158,11,0.18);  color:#FCD34D; }}
.br  {{ background:rgba(239,68,68,0.18);   color:#F87171; }}
.bn  {{ background:rgba(100,116,139,0.18); color:#94A3B8; }}

/* PROGRESS BAR */
.pbar-wrap {{ background:rgba(128,128,128,0.12); border-radius:4px; height:5px; overflow:hidden; margin:5px 0 3px; }}
.pbar {{ height:100%; border-radius:4px; }}

/* INDICATOR CARD */
.ind-card {{
  background:var(--card); border:1px solid var(--border);
  border-radius:var(--r); padding:0.9rem 1.1rem; margin-bottom:0.5rem;
}}
.ind-name {{ font-size:0.86rem; font-weight:500; color:var(--text); }}
.ind-vals {{ font-size:0.71rem; color:var(--muted); font-family:var(--mono); }}

/* ALERT BANNER */
.alert-banner {{
  background:rgba(239,68,68,0.07); border:1px solid rgba(239,68,68,0.2);
  border-left:3px solid #EF4444; border-radius:var(--r);
  padding:0.72rem 1rem; margin-bottom:0.55rem;
}}
.alert-banner span {{ font-size:0.82rem; color:#FCA5A5; }}

/* INPUTS OVERRIDES */
[data-testid="stSelectbox"] > div > div {{
  background:var(--input) !important; border:1px solid var(--border2) !important;
  border-radius:var(--r) !important; color:var(--text) !important;
}}
[data-testid="stTextInput"] > div > div > input {{
  background:var(--input) !important; border:1px solid var(--border2) !important;
  color:var(--text) !important; border-radius:var(--r) !important;
}}
[data-baseweb="select"] * {{ color:var(--text) !important; }}
[data-baseweb="menu"]    {{ background:var(--input) !important; }}
label {{ color:var(--muted) !important; font-size:0.81rem !important; }}
p     {{ color:var(--muted) !important; }}

/* BUTTONS */
.stButton > button {{
  background:var(--accent) !important; color:#fff !important;
  border:none !important; border-radius:var(--r) !important;
  font-family:var(--font) !important; font-weight:600 !important;
  font-size:0.88rem !important; padding:0.55rem 1.3rem !important;
  transition:all .2s !important;
}}
.stButton > button:hover {{ opacity:.88 !important; transform:translateY(-1px) !important; }}
[data-testid="stDownloadButton"] > button {{
  background:var(--card) !important; border:1px solid var(--border2) !important;
  color:var(--text) !important; border-radius:var(--r) !important;
}}
[data-testid="stFileUploader"] {{
  background:var(--card) !important; border:1px dashed var(--border2) !important;
  border-radius:var(--r) !important;
}}

/* DATAFRAME */
[data-testid="stDataFrame"] {{ border-radius:var(--r); overflow:hidden; }}

/* LOGIN */
.login-card {{
  background:var(--surface); border:1px solid var(--border2);
  border-radius:18px; padding:2.8rem 2.5rem;
  box-shadow:0 30px 80px rgba(0,0,0,0.3);
}}
.login-badge {{
  display:inline-block; background:rgba(59,130,246,0.12); color:var(--accent2);
  font-size:0.69rem; font-weight:700; letter-spacing:.1em; text-transform:uppercase;
  padding:3px 10px; border-radius:20px; margin-bottom:1rem;
}}
.login-title {{ font-size:1.55rem; font-weight:800; color:var(--text); margin-bottom:0.3rem; }}
.login-sub   {{ font-size:0.82rem; color:var(--muted); margin-bottom:2rem; }}

/* SCROLLBAR */
::-webkit-scrollbar {{ width:4px; height:4px; }}
::-webkit-scrollbar-thumb {{ background:rgba(100,116,139,0.4); border-radius:2px; }}

/* STREAMLIT MISC */
[data-testid="stVerticalBlock"] {{ gap:0 !important; }}
div[data-testid="stHorizontalBlock"] {{ gap:12px !important; }}
.stTabs [data-baseweb="tab-panel"] {{ padding:0 !important; }}
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════
def N(n, d=0):
    try:
        n = float(n)
        if pd.isna(n): return "—"
        if n >= 1_000_000: return f"{n/1_000_000:.1f}M"
        if n >= 1_000:     return f"{n/1_000:.1f}K"
        return f"{n:,.{d}f}"
    except: return "—"

def has(df, col): return col in df.columns
def ssum(df, col): return df[col].sum() if has(df, col) else 0
def slen(df, col, val): return len(df[df[col]==val]) if has(df, col) else 0
def suniq(df, col): return df[col].nunique() if has(df, col) else 0
def sopts(df, col): return ["All"] + sorted(df[col].dropna().unique().tolist()) if has(df, col) else ["All"]
def sfilt(df, col, val):
    if val == "All" or not has(df, col): return df
    return df[df[col]==val]

def TH(): return DARK if st.session_state.get("dark", True) else LIGHT

def bdg(status):
    s = str(status).lower()
    if any(x in s for x in ["on track","paid","completed","above 80","in stock","fully"]):
        return f"<span class='badge bg'>{status}</span>"
    if any(x in s for x in ["risk","pending","partial","low stock","60–80","awaiting"]):
        return f"<span class='badge ba'>{status}</span>"
    if any(x in s for x in ["off","fail","non-func","pipeline break","cancel","below 60","not"]):
        return f"<span class='badge br'>{status}</span>"
    return f"<span class='badge bn'>{status}</span>"

def kpi(label, value, sub="", color="blue", icon="", delta=None, ddir="up"):
    dc = {"up":"d-up","down":"d-down","mid":"d-mid"}.get(ddir,"d-mid")
    da = f"<div class='kpi-delta {dc}'>{delta}</div>" if delta else ""
    return f"""<div class='kpi-card kpi-{color}'>
      <div class='kpi-icon'>{icon}</div>
      <div class='kpi-label'>{label}</div>
      <div class='kpi-value'>{value}</div>
      <div class='kpi-sub'>{sub}</div>{da}
    </div>"""

def sh(t): st.markdown(f"<div class='sh'>{t}</div>", unsafe_allow_html=True)
def ph(title, sub=""): st.markdown(f"<div class='ph'><h1>{title}</h1><p>{sub}</p></div>", unsafe_allow_html=True)

def pc(fig):
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

def T(fig, h=340, leg=True):
    th = TH()
    fig.update_layout(
        height=h, paper_bgcolor=th["plotbg"], plot_bgcolor=th["plotbg"],
        font=dict(family="Outfit", color=th["fontc"], size=11),
        margin=dict(l=12,r=12,t=36,b=12), showlegend=leg,
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color=th["muted"],size=10),
                    borderwidth=0, orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        colorway=COLORS,
        title_font=dict(size=12, color=th["title"], family="Outfit"),
    )
    fig.update_xaxes(showgrid=False, zeroline=False, color=th["fontc"],
                     tickfont=dict(size=10,color=th["fontc"]),
                     linecolor=th["gridc"])
    fig.update_yaxes(gridcolor=th["gridc"], zeroline=False, color=th["fontc"],
                     tickfont=dict(size=10,color=th["fontc"]), linewidth=0)
    return fig

# ══════════════════════════════════════════════════════════════════════════════
# DATA
# ══════════════════════════════════════════════════════════════════════════════
@st.cache_data(show_spinner="Loading…")
def load_data(file):
    xls = pd.ExcelFile(file, engine="openpyxl")
    out = {}
    for name in xls.sheet_names:
        try: out[name] = pd.read_excel(xls, sheet_name=name)
        except: pass
    return out

# ══════════════════════════════════════════════════════════════════════════════
# TOP NAVIGATION
# ══════════════════════════════════════════════════════════════════════════════
def top_nav():
    page = st.session_state.get("page", "Overview")
    user = st.session_state.get("user", "")
    dark = st.session_state.get("dark", True)
    theme_icon = "☀️ Light" if dark else "🌙 Dark"

    tabs_html = ""
    for icon, label in NAV_ITEMS:
        active = "active" if page == label else ""
        tabs_html += f"<button class='nav-tab {active}' onclick=\"document.getElementById('nav_{label}').click()\">{icon} {label}</button>"

    st.markdown(f"""
    <div class='topnav'>
      <div class='topnav-brand'>🌍 <span>SI</span> Sudan IM</div>
      {tabs_html}
      <div class='nav-right'>
        <div class='user-chip'>👤 {user}</div>
      </div>
    </div>""", unsafe_allow_html=True)

    # Hidden Streamlit radio that JS clicks
    cols = st.columns(len(NAV_ITEMS) + 3)
    nav_labels = [f"{icon} {label}" for icon, label in NAV_ITEMS]
    current_label = f"{dict(NAV_ITEMS).get(page, '🏠')} {page}" if False else next(
        (f"{i} {l}" for i, l in NAV_ITEMS if l == page), nav_labels[0])

    with cols[0]:
        sel = st.radio("nav", nav_labels, index=nav_labels.index(current_label)
                       if current_label in nav_labels else 0,
                       label_visibility="collapsed", horizontal=True, key="nav_radio")
        if sel:
            label = sel.split(" ", 1)[1]
            if st.session_state.get("page") != label:
                st.session_state["page"] = label
                st.rerun()

    # Theme toggle and logout as buttons in remaining cols
    with cols[-2]:
        if st.button(theme_icon, key="theme_btn"):
            st.session_state["dark"] = not dark
            st.rerun()
    with cols[-1]:
        if st.button("🚪 Logout", key="logout_btn"):
            st.session_state.clear(); st.rerun()

    # File uploader (compact, always visible)
    with st.expander("📂 Load / change database", expanded=not bool(st.session_state.get("dfs"))):
        up = st.file_uploader("Excel file", type=["xlsx"], label_visibility="collapsed")
        if up:
            data = load_data(up)
            st.session_state["dfs"] = data
            st.success(f"✅ {len(data)} sheets loaded")
            st.rerun()

    st.markdown("<div class='page-content'>", unsafe_allow_html=True)

# LOGIN
# ══════════════════════════════════════════════════════════════════════════════
def login_page():
    inject_css(DARK)
    c1,c2,c3 = st.columns([1,1.2,1])
    with c2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("""<div class='login-card'>
          <div class='login-badge'>🌍 Restricted Access</div>
          <div class='login-title'>SI Sudan IM Dashboard</div>
          <div class='login-sub'>Solidarites International · Sudan Mission 2025–2026<br>Enter your credentials to continue.</div>
        </div>""", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        user = st.text_input("Username", placeholder="im_manager", label_visibility="collapsed")
        pw   = st.text_input("Password", type="password", placeholder="Password", label_visibility="collapsed")
        if st.button("Sign in →", use_container_width=True):
            if CREDENTIALS.get(user) == pw:
                st.session_state.update(auth=True, user=user, dark=True, page="Overview")
                st.rerun()
            else: st.error("Invalid credentials.")
        st.markdown("<div style='text-align:center;font-size:.7rem;color:#334155;margin-top:1.2rem;'>Confidential · SI © 2026</div>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# MAP PAGE  (enriched)
# ══════════════════════════════════════════════════════════════════════════════
def make_folium(df, th):
    tiles = "CartoDB dark_matter" if st.session_state.get("dark",True) else "CartoDB positron"
    m = folium.Map(location=[14.5,29.5], zoom_start=5, tiles=tiles, attr="CartoDB")
    MiniMap(toggle_display=True, position="bottomleft").add_to(m)

    if has(df,"GPS_Latitude") and has(df,"GPS_Longitude"):
        dfm = df.copy()
        dfm["GPS_Latitude"]  = pd.to_numeric(dfm["GPS_Latitude"],  errors="coerce")
        dfm["GPS_Longitude"] = pd.to_numeric(dfm["GPS_Longitude"], errors="coerce")
        dfm = dfm.dropna(subset=["GPS_Latitude","GPS_Longitude"])
        dfm = dfm[dfm["GPS_Latitude"].between(8,24) & dfm["GPS_Longitude"].between(20,40)]

        if not dfm.empty:
            HeatMap(dfm[["GPS_Latitude","GPS_Longitude"]].values.tolist(),
                    radius=14, blur=18, min_opacity=0.25).add_to(m)
            cl = MarkerCluster(options={"maxClusterRadius":45,"showCoverageOnHover":False}).add_to(m)
            for _, row in dfm.iterrows():
                sec   = str(row.get("Sector","")) if has(df,"Sector") else ""
                color = SC.get(sec,"#64748B")
                pop   = f"""<div style='font-family:Outfit,sans-serif;font-size:12px;min-width:170px;'>
                  <b>{row.get('Beneficiary_ID','—')}</b><br>
                  <span style='color:#64748b;'>State:</span> {row.get('State','—')}<br>
                  <span style='color:#64748b;'>Locality:</span> {row.get('Locality','—')}<br>
                  <span style='color:#64748b;'>Sector:</span> <b style='color:{color};'>{sec}</b><br>
                  <span style='color:#64748b;'>Displacement:</span> {row.get('Displacement_Status','—')}<br>
                  <span style='color:#64748b;'>Vulnerability:</span> {row.get('Vulnerability_Level','—')}
                </div>"""
                folium.CircleMarker(
                    location=[row["GPS_Latitude"],row["GPS_Longitude"]],
                    radius=6, color=color, fill=True, fill_color=color,
                    fill_opacity=0.8, weight=1,
                    popup=folium.Popup(pop,max_width=230),
                    tooltip=f"{row.get('Locality','—')} · {sec}"
                ).add_to(cl)

    # Sudan state boundaries approximation markers
    states_coords = {
        "West Darfur":  (13.45,22.44), "North Darfur": (13.63,25.35),
        "Gedaref":      (14.04,35.38), "Khartoum":     (15.55,32.52),
    }
    for state, (lat,lon) in states_coords.items():
        folium.Marker(
            location=[lat,lon],
            icon=folium.DivIcon(html=f"""
            <div style='background:rgba(59,130,246,0.85);color:#fff;padding:3px 8px;
            border-radius:12px;font-family:Outfit,sans-serif;font-size:11px;
            font-weight:700;white-space:nowrap;border:1px solid rgba(255,255,255,0.3);'>{state}</div>""",
            icon_size=(120,28), icon_anchor=(60,14)),
        ).add_to(m)

    leg_bg = "rgba(13,23,48,0.95)" if st.session_state.get("dark",True) else "rgba(255,255,255,0.95)"
    leg_text = "#e2e8f0" if st.session_state.get("dark",True) else "#1e293b"
    leg_sub  = "#94a3b8"  if st.session_state.get("dark",True) else "#64748b"
    leg = f"""<div style='position:fixed;bottom:28px;right:16px;z-index:9999;
      background:{leg_bg};border:1px solid rgba(99,140,210,0.2);border-radius:10px;
      padding:12px 16px;font-family:Outfit,sans-serif;'>
      <div style='font-weight:700;font-size:11px;color:{leg_text};margin-bottom:8px;
      letter-spacing:.07em;text-transform:uppercase;'>Sectors</div>"""
    for s,c in SC.items():
        leg += f"<div style='display:flex;align-items:center;gap:7px;margin-bottom:4px;'><span style='width:9px;height:9px;border-radius:50%;background:{c};display:inline-block;'></span><span style='font-size:11px;color:{leg_sub};'>{s}</span></div>"
    leg += "</div>"
    m.get_root().html.add_child(folium.Element(leg))
    return m

def page_map(dfs):
    ph("Geographic Coverage", "Interactive map — beneficiary locations, clustering, heatmap, and spatial analysis")
    df = dfs.get("Beneficiary_Registration", pd.DataFrame())
    if df.empty: st.info("Load the Excel database to view geographic data."); return
    th = TH()

    c1,c2,c3,c4 = st.columns(4)
    with c1: s1 = st.selectbox("State",        sopts(df,"State"),               key="m_s")
    with c2: s2 = st.selectbox("Sector",       sopts(df,"Sector"),              key="m_sec")
    with c3: s3 = st.selectbox("Displacement", sopts(df,"Displacement_Status"), key="m_d")
    with c4: s4 = st.selectbox("Vulnerability",sopts(df,"Vulnerability_Level"), key="m_v")

    df_f = sfilt(sfilt(sfilt(sfilt(df.copy(),"State",s1),"Sector",s2),"Displacement_Status",s3),"Vulnerability_Level",s4)
    nb   = len(df_f)
    fem  = slen(df_f,"Sex","Female")

    c1,c2,c3,c4,c5,c6 = st.columns(6)
    c1.markdown(kpi("Shown",       N(nb),                      "beneficiaries",   "blue",  "📍"), unsafe_allow_html=True)
    c2.markdown(kpi("States",      N(suniq(df_f,"State")),     "covered",         "teal",  "🗺️"), unsafe_allow_html=True)
    c3.markdown(kpi("Localities",  N(suniq(df_f,"Locality")),  "zones",           "amber", "📌"), unsafe_allow_html=True)
    c4.markdown(kpi("Female",      f"{100*fem/nb:.0f}%" if nb else "—","of shown","purple","♀"), unsafe_allow_html=True)
    c5.markdown(kpi("IDP",         N(slen(df_f,"Displacement_Status","IDP")),    "","green","🏕️"), unsafe_allow_html=True)
    c6.markdown(kpi("Active",      N(slen(df_f,"Registration_Status","Active")), "","teal","✅"), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── MAP + side charts ─────────────────────────────────────────────────
    col_map, col_right = st.columns([2.4, 1])
    with col_map:
        sh("Interactive Beneficiary Map")
        st_folium(make_folium(df_f, th), use_container_width=True, height=480, returned_objects=[])

    with col_right:
        sh("State Distribution")
        if has(df_f,"State") and nb > 0:
            by_s = df_f.groupby("State").size().reset_index(name="n").sort_values("n")
            fig = px.bar(by_s, x="n", y="State", orientation="h",
                         color="n", color_continuous_scale=["#1E3A6E","#60A5FA"],
                         title="Beneficiaries by State")
            fig.update_layout(coloraxis_showscale=False)
            pc(T(fig, h=220, leg=False))

        if has(df_f,"Sector") and nb > 0:
            by_sec = df_f.groupby("Sector").size().reset_index(name="n")
            fig = px.pie(by_sec, values="n", names="Sector", hole=0.55,
                         color="Sector", color_discrete_map=SC, title="By Sector")
            fig.update_traces(textinfo="none", marker=dict(line=dict(color=th["bg"],width=2)))
            pc(T(fig, h=220))

    st.markdown("<br>", unsafe_allow_html=True)

    # ── SPATIAL ANALYSIS CHARTS ───────────────────────────────────────────
    sh("Spatial Analysis — Multi-Dimensional Breakdown")
    c1, c2, c3 = st.columns(3)

    with c1:
        if has(df_f,"State") and has(df_f,"Sector") and nb > 0:
            ct = df_f.groupby(["State","Sector"]).size().reset_index(name="Count")
            fig = px.bar(ct, x="State", y="Count", color="Sector",
                         barmode="stack", color_discrete_map=SC,
                         title="Beneficiaries by State & Sector")
            pc(T(fig, h=310))

    with c2:
        if has(df_f,"Displacement_Status") and has(df_f,"Sector") and nb > 0:
            ct = df_f.groupby(["Displacement_Status","Sector"]).size().reset_index(name="Count")
            fig = px.bar(ct, x="Displacement_Status", y="Count", color="Sector",
                         barmode="stack", color_discrete_map=SC,
                         title="Displacement Status by Sector")
            fig.update_xaxes(tickangle=-20)
            pc(T(fig, h=310))

    with c3:
        if has(df_f,"Vulnerability_Level") and has(df_f,"Sex") and nb > 0:
            ct = df_f.groupby(["Vulnerability_Level","Sex"]).size().reset_index(name="Count")
            fig = px.bar(ct, x="Vulnerability_Level", y="Count", color="Sex",
                         barmode="group",
                         color_discrete_map={"Female":"#EC4899","Male":"#3B82F6"},
                         title="Vulnerability × Sex")
            pc(T(fig, h=310))

    c1, c2, c3 = st.columns(3)

    with c1:
        if has(df_f,"State") and has(df_f,"Sex") and nb > 0:
            sg = df_f.groupby("State")[["Sex"]].value_counts().reset_index(name="Count") if False else \
                 df_f.groupby(["State","Sex"]).size().reset_index(name="Count")
            fig = px.bar(sg, x="State", y="Count", color="Sex",
                         color_discrete_map={"Female":"#EC4899","Male":"#3B82F6"},
                         barmode="stack", title="Sex Disaggregation by State")
            pc(T(fig, h=290))

    with c2:
        if has(df_f,"Age") and nb > 0:
            df_age = df_f.copy()
            df_age["Age"] = pd.to_numeric(df_age["Age"], errors="coerce")
            df_age = df_age.dropna(subset=["Age"])
            bins = [0,5,18,35,50,120]
            labels = ["0–4","5–17","18–34","35–49","50+"]
            df_age["Age_Group"] = pd.cut(df_age["Age"], bins=bins, labels=labels, right=False)
            age_grp = df_age.groupby("Age_Group").size().reset_index(name="Count")
            fig = px.bar(age_grp, x="Age_Group", y="Count",
                         color="Age_Group", color_discrete_sequence=COLORS,
                         title="Age Group Distribution")
            fig.update_layout(showlegend=False)
            pc(T(fig, h=290))

    with c3:
        if has(df_f,"Registration_Date") and nb > 0:
            df_t = df_f.copy()
            df_t["Registration_Date"] = pd.to_datetime(df_t["Registration_Date"], errors="coerce")
            df_t = df_t.dropna(subset=["Registration_Date"])
            df_t["Month"] = df_t["Registration_Date"].dt.to_period("M").astype(str)
            trend = df_t.groupby("Month").size().reset_index(name="Count")
            fig = px.line(trend, x="Month", y="Count",
                          title="Registration Timeline", markers=True)
            fig.update_traces(line_color="#3B82F6", marker_color="#60A5FA", line_width=2)
            pc(T(fig, h=290))

    # ── HEATMAP TABLE ──────────────────────────────────────────────────────
    sh("Coverage Heatmap — State × Sector")
    if has(df_f,"State") and has(df_f,"Sector") and nb > 0:
        heat = df_f.groupby(["State","Sector"]).size().reset_index(name="Count")
        fig = px.density_heatmap(heat, x="Sector", y="State", z="Count",
                                 color_continuous_scale="Blues",
                                 title="Beneficiary Density by State & Sector")
        fig.update_layout(coloraxis_colorbar=dict(tickfont=dict(color=TH()["fontc"])))
        pc(T(fig, h=300, leg=False))

# ══════════════════════════════════════════════════════════════════════════════
# OVERVIEW
# ══════════════════════════════════════════════════════════════════════════════
def page_overview(dfs):
    ph("Program Overview", "Consolidated metrics — all sectors · Sudan Mission 2025–2026")
    th = TH()
    df_b = dfs.get("Beneficiary_Registration", pd.DataFrame())
    df_w = dfs.get("WASH_Monitoring",           pd.DataFrame())
    df_f = dfs.get("FSL_Distribution",          pd.DataFrame())
    df_c = dfs.get("CVA_Cash_Transfers",        pd.DataFrame())
    df_i = dfs.get("Indicator_Tracker",         pd.DataFrame())

    tot  = len(df_b); act = slen(df_b,"Registration_Status","Active")
    wr   = int(ssum(df_w,"Reached_Beneficiaries"))
    fhh  = int(ssum(df_f,"HH_Reached"))
    paid = sfilt(df_c,"Transfer_Status","Paid")
    usd  = paid["Transfer_Value_USD"].sum() if has(paid,"Transfer_Value_USD") and len(paid)>0 else 0
    on_t = slen(df_i,"Status","On track"); ti = len(df_i)

    sh("Programme Scale")
    c1,c2,c3,c4,c5,c6 = st.columns(6)
    c1.markdown(kpi("Beneficiaries", N(tot), f"{act:,} active",    "blue",  "👤", f"↑ {act/tot:.0%}" if tot else None,"up"), unsafe_allow_html=True)
    c2.markdown(kpi("WASH Reached",  N(wr),  "cumulative",         "teal",  "💧"), unsafe_allow_html=True)
    c3.markdown(kpi("FSL HH",        N(fhh), "households reached", "green", "🌾"), unsafe_allow_html=True)
    c4.markdown(kpi("Cash Paid",     f"${N(usd)}","USD disbursed", "amber", "💵"), unsafe_allow_html=True)
    c5.markdown(kpi("States",        str(suniq(df_b,"State")),"covered","purple","🗺️"), unsafe_allow_html=True)
    c6.markdown(kpi("On Track",      f"{on_t}/{ti}","indicators",  "green", "📊", f"↑ {on_t/ti:.0%}" if ti else None,"up"), unsafe_allow_html=True)

    alerts = []
    pb = slen(df_f,"Pipeline_Status","Pipeline break")
    fa = slen(df_c,"Transfer_Status","Failed")
    ot = slen(df_i,"Status","Off track")
    if pb: alerts.append(f"⚠️  <b>{pb}</b> pipeline breaks detected in FSL supply chain")
    if fa: alerts.append(f"❌  <b>{fa}</b> failed cash transfers require investigation")
    if ot: alerts.append(f"🔴  <b>{ot}</b> program indicators are off track")
    if alerts:
        sh("Active Alerts")
        for a in alerts: st.markdown(f"<div class='alert-banner'><span>{a}</span></div>",unsafe_allow_html=True)

    sh("Beneficiary Profile")
    c1,c2,c3 = st.columns([1.1,1,1])
    with c1:
        if not df_b.empty and has(df_b,"Sector"):
            d = df_b.groupby("Sector").size().reset_index(name="n")
            fig = px.pie(d, values="n", names="Sector", hole=0.58,
                         color="Sector", color_discrete_map=SC, title="Beneficiaries by Sector")
            fig.update_traces(textinfo="percent", textfont_size=10,
                              marker=dict(line=dict(color=th["bg"],width=2)))
            pc(T(fig,h=300))
    with c2:
        if not df_b.empty and has(df_b,"Displacement_Status"):
            d = df_b["Displacement_Status"].value_counts().reset_index(); d.columns=["Status","Count"]
            fig = px.bar(d, x="Count", y="Status", orientation="h",
                         color="Count", color_continuous_scale=["#1E3A6E","#3B82F6"],
                         title="Displacement Status")
            fig.update_layout(coloraxis_showscale=False)
            pc(T(fig,h=300,leg=False))
    with c3:
        if not df_b.empty and has(df_b,"Sex") and has(df_b,"Vulnerability_Level"):
            ct = df_b.groupby(["Vulnerability_Level","Sex"]).size().reset_index(name="n")
            fig = px.bar(ct, x="Vulnerability_Level", y="n", color="Sex", barmode="stack",
                         color_discrete_map={"Female":"#EC4899","Male":"#3B82F6"},
                         title="Vulnerability × Sex")
            pc(T(fig,h=300))

    sh("Registration Trend")
    if not df_b.empty and has(df_b,"Registration_Date"):
        df_t = df_b.copy()
        df_t["Registration_Date"] = pd.to_datetime(df_t["Registration_Date"],errors="coerce")
        df_t = df_t.dropna(subset=["Registration_Date"])
        df_t["Month"] = df_t["Registration_Date"].dt.to_period("M").astype(str)
        if has(df_t,"Sector"):
            trend = df_t.groupby(["Month","Sector"]).size().reset_index(name="Count")
            fig = px.area(trend, x="Month", y="Count", color="Sector",
                          color_discrete_map=SC, title="Monthly Registrations by Sector")
            fig.update_traces(line_width=2)
            pc(T(fig,h=290))

    if not df_b.empty and has(df_b,"State") and has(df_b,"Sector"):
        sh("Coverage Heatmap — State × Sector")
        heat = df_b.groupby(["State","Sector"]).size().reset_index(name="Count")
        fig = px.density_heatmap(heat, x="Sector", y="State", z="Count",
                                 color_continuous_scale="Blues",
                                 title="Beneficiaries by State × Sector")
        fig.update_layout(coloraxis_colorbar=dict(tickfont=dict(color=th["fontc"])))
        pc(T(fig,h=280,leg=False))

# ══════════════════════════════════════════════════════════════════════════════
# WASH
# ══════════════════════════════════════════════════════════════════════════════
def page_wash(dfs):
    ph("WASH Monitoring","Water, Sanitation & Hygiene — activity performance and gender disaggregation")
    df = dfs.get("WASH_Monitoring",pd.DataFrame())
    if df.empty: st.info("No WASH_Monitoring sheet found."); return
    th = TH()
    c1,c2 = st.columns(2)
    with c1: s1 = st.selectbox("State",         sopts(df,"State"),        key="w_s")
    with c2: s2 = st.selectbox("Activity Type", sopts(df,"Activity_Type"),key="w_a")
    df_f = sfilt(sfilt(df.copy(),"State",s1),"Activity_Type",s2)
    reached = int(ssum(df_f,"Reached_Beneficiaries"))
    target  = int(ssum(df_f,"Target_Beneficiaries")) or 1
    pct = reached/target
    sh("Key Indicators")
    c1,c2,c3,c4,c5 = st.columns(5)
    dd="up" if pct>=0.8 else "mid" if pct>=0.6 else "down"
    c1.markdown(kpi("Reached",    N(reached),                     f"of {N(target)} target","blue",  "💧",f"{pct:.0%} coverage",dd),unsafe_allow_html=True)
    c2.markdown(kpi("Water",      N(int(ssum(df_f,"Water_Volume_Liters")))+" L","litres",  "teal",  "🚰"),unsafe_allow_html=True)
    c3.markdown(kpi("Latrines",   N(int(ssum(df_f,"Latrine_Units_Built"))),    "built",    "green", "🏗️"),unsafe_allow_html=True)
    c4.markdown(kpi("Hyg Kits",   N(int(ssum(df_f,"Hygiene_Kits_Dist"))),      "distrib.", "amber", "🧴"),unsafe_allow_html=True)
    c5.markdown(kpi("NFI Kits",   N(int(ssum(df_f,"NFI_Kits_Dist"))),          "distrib.", "purple","📦"),unsafe_allow_html=True)

    sh("Activity Performance")
    c1,c2 = st.columns(2)
    with c1:
        if has(df_f,"Activity_Type"):
            grp = df_f.groupby("Activity_Type")[["Target_Beneficiaries","Reached_Beneficiaries"]].sum().reset_index()
            fig = go.Figure()
            fig.add_bar(name="Target", x=grp["Activity_Type"],y=grp["Target_Beneficiaries"],
                        marker_color="rgba(59,130,246,0.2)",marker_line_color="#3B82F6",marker_line_width=1)
            fig.add_bar(name="Reached",x=grp["Activity_Type"],y=grp["Reached_Beneficiaries"],marker_color="#3B82F6")
            fig.update_layout(barmode="group",title="Target vs Reached")
            pc(T(fig,h=320))
    with c2:
        if has(df_f,"Functionality_Status"):
            func=df_f["Functionality_Status"].value_counts().reset_index(); func.columns=["Status","Count"]
            cmap={"Fully Functional":"#10B981","Partially Functional":"#F59E0B","Non-Functional":"#EF4444","Under Construction":"#8B5CF6"}
            fig=px.pie(func,values="Count",names="Status",hole=0.55,color="Status",color_discrete_map=cmap,title="Infrastructure Functionality")
            fig.update_traces(textinfo="percent+label",textfont_size=9,marker=dict(line=dict(color=th["bg"],width=2)))
            pc(T(fig,h=320))

    sh("Gender Disaggregation")
    if has(df_f,"Reached_Female") and has(df_f,"Reached_Male"):
        c1,c2,c3 = st.columns(3)
        tf=df_f["Reached_Female"].sum(); tm=df_f["Reached_Male"].sum()
        with c1:
            fig=go.Figure(go.Bar(x=["Female","Male"],y=[tf,tm],marker_color=["#EC4899","#3B82F6"],
                text=[N(tf),N(tm)],textposition="outside",textfont=dict(color=th["text"],size=11)))
            fig.update_layout(title="Sex Disaggregation — Total")
            pc(T(fig,h=280,leg=False))
        with c2:
            if has(df_f,"State"):
                sg=df_f.groupby("State")[["Reached_Female","Reached_Male"]].sum().reset_index()
                fig=px.bar(sg,x="State",y=["Reached_Female","Reached_Male"],barmode="stack",
                    color_discrete_map={"Reached_Female":"#EC4899","Reached_Male":"#3B82F6"},title="Sex by State")
                pc(T(fig,h=280))
        with c3:
            if has(df_f,"Reached_Children_U5"):
                tc5=df_f["Reached_Children_U5"].sum()
                fig=go.Figure(go.Pie(labels=["Children U5","Adults"],values=[tc5,max(0,(tf+tm)-tc5)],hole=0.55,
                    marker=dict(colors=["#F59E0B","#3B82F6"],line=dict(color=th["bg"],width=2))))
                fig.update_layout(title="Children U5 vs Adults")
                pc(T(fig,h=280))

    sh("Reporting Compliance")
    if has(df_f,"Cluster_Reporting"):
        c1,c2 = st.columns(2)
        with c1:
            cr=df_f["Cluster_Reporting"].value_counts().reset_index(); cr.columns=["Status","Count"]
            fig=px.pie(cr,values="Count",names="Status",hole=0.55,color="Status",
                color_discrete_map={"Reported":"#10B981","Not reported":"#EF4444"},title="Cluster Reporting")
            fig.update_traces(marker=dict(line=dict(color=th["bg"],width=2)),textinfo="percent")
            pc(T(fig,h=270))
        with c2:
            if has(df_f,"State"):
                g2=df_f.groupby(["State","Cluster_Reporting"]).size().reset_index(name="n")
                fig=px.bar(g2,x="State",y="n",color="Cluster_Reporting",
                    color_discrete_map={"Reported":"#10B981","Not reported":"#EF4444"},title="Reporting by State")
                pc(T(fig,h=270))

# ══════════════════════════════════════════════════════════════════════════════
# FSL
# ══════════════════════════════════════════════════════════════════════════════
def page_fsl(dfs):
    ph("Food Security & Livelihoods","Distribution tracking — commodities, pipeline, donor coverage")
    df=dfs.get("FSL_Distribution",pd.DataFrame())
    if df.empty: st.info("No FSL_Distribution sheet found."); return
    th=TH()
    c1,c2,c3=st.columns(3)
    with c1: s1=st.selectbox("State",     sopts(df,"State"),         key="f_s")
    with c2: s2=st.selectbox("Commodity", sopts(df,"Commodity_Type"),key="f_c")
    with c3: s3=st.selectbox("Donor",     sopts(df,"Donor"),         key="f_d")
    df_f=sfilt(sfilt(sfilt(df.copy(),"State",s1),"Commodity_Type",s2),"Donor",s3)
    hht=int(ssum(df_f,"HH_Targeted")); hhr=int(ssum(df_f,"HH_Reached"))
    qp=ssum(df_f,"Quantity_Planned"); qd=ssum(df_f,"Quantity_Distributed")
    fem=int(ssum(df_f,"Female_HHH_Reached")); pb=slen(df_f,"Pipeline_Status","Pipeline break")
    cov=hhr/hht if hht else 0
    sh("Key Indicators")
    c1,c2,c3,c4,c5=st.columns(5)
    dd="up" if cov>=0.8 else "mid" if cov>=0.6 else "down"
    c1.markdown(kpi("HH Reached",  N(hhr), f"of {N(hht)} targeted","green", "🏠",f"{cov:.0%} coverage",dd),unsafe_allow_html=True)
    c2.markdown(kpi("Qty Dist.",   N(qd),  f"of {N(qp)} planned",  "blue",  "📦"),unsafe_allow_html=True)
    c3.markdown(kpi("Female HHH",  N(fem), f"{fem/hhr:.0%}" if hhr else "—","purple","♀"),unsafe_allow_html=True)
    c4.markdown(kpi("Pipeline ⚠️", str(pb),"supply breaks",        "red" if pb else "green","⚠️"),unsafe_allow_html=True)
    c5.markdown(kpi("Records",     N(len(df_f)),"in selection",    "teal", "📋"),unsafe_allow_html=True)

    sh("Distribution Analysis")
    c1,c2,c3=st.columns(3)
    with c1:
        if has(df_f,"Commodity_Type"):
            comm=df_f.groupby("Commodity_Type")["HH_Reached"].sum().reset_index()
            comm=comm.sort_values("HH_Reached",ascending=True).tail(10); comm.columns=["Commodity","HH_Reached"]
            fig=px.bar(comm,x="HH_Reached",y="Commodity",orientation="h",color="HH_Reached",
                color_continuous_scale=["#14532D","#34D399"],title="HH Reached by Commodity")
            fig.update_layout(coloraxis_showscale=False)
            pc(T(fig,h=350,leg=False))
    with c2:
        if has(df_f,"Pipeline_Status"):
            pipe=df_f["Pipeline_Status"].value_counts().reset_index(); pipe.columns=["Status","Count"]
            cmap={"In stock":"#10B981","Low stock":"#F59E0B","Pipeline break":"#EF4444","Awaiting delivery":"#8B5CF6"}
            fig=px.pie(pipe,values="Count",names="Status",hole=0.55,color="Status",color_discrete_map=cmap,title="Pipeline Status")
            fig.update_traces(marker=dict(line=dict(color=th["bg"],width=2)),textinfo="percent")
            pc(T(fig,h=350))
    with c3:
        if has(df_f,"Donor"):
            don=df_f.groupby("Donor")["HH_Reached"].sum().reset_index()
            fig=px.bar(don,x="Donor",y="HH_Reached",color="Donor",color_discrete_sequence=COLORS,
                title="HH Reached by Donor",text="HH_Reached")
            fig.update_traces(texttemplate="%{text:,.0f}",textposition="outside",textfont=dict(color=th["text"],size=9))
            fig.update_layout(showlegend=False)
            pc(T(fig,h=350,leg=False))

    sh("Distribution Timeline")
    if has(df_f,"Distribution_Date"):
        df_t=df_f.copy(); df_t["Distribution_Date"]=pd.to_datetime(df_t["Distribution_Date"],errors="coerce")
        df_t=df_t.dropna(subset=["Distribution_Date"]); df_t["Month"]=df_t["Distribution_Date"].dt.to_period("M").astype(str)
        if has(df_t,"Donor"):
            monthly=df_t.groupby(["Month","Donor"])["HH_Reached"].sum().reset_index()
            fig=px.area(monthly,x="Month",y="HH_Reached",color="Donor",title="Monthly HH Reached by Donor",color_discrete_sequence=COLORS)
            fig.update_traces(line_width=1.5); pc(T(fig,h=270))

    sh("Post-Distribution Monitoring")
    c1,c2=st.columns(2)
    with c1:
        if has(df_f,"Beneficiary_Satisfaction"):
            sat=df_f["Beneficiary_Satisfaction"].value_counts().reset_index(); sat.columns=["Level","Count"]
            cmap={"Above 80%":"#10B981","60–80%":"#F59E0B","Below 60%":"#EF4444","N/A":"#475569"}
            fig=px.bar(sat,x="Level",y="Count",color="Level",color_discrete_map=cmap,title="Beneficiary Satisfaction",text="Count")
            fig.update_traces(textposition="outside",textfont=dict(color=th["text"])); fig.update_layout(showlegend=False)
            pc(T(fig,h=270))
    with c2:
        if has(df_f,"Post_Dist_Monitor"):
            pdm=df_f["Post_Dist_Monitor"].value_counts().reset_index(); pdm.columns=["Status","Count"]
            fig=px.pie(pdm,values="Count",names="Status",hole=0.5,title="PDM Completion",color_discrete_sequence=COLORS)
            fig.update_traces(marker=dict(line=dict(color=th["bg"],width=2)),textinfo="percent")
            pc(T(fig,h=270))

# ══════════════════════════════════════════════════════════════════════════════
# CVA
# ══════════════════════════════════════════════════════════════════════════════
def page_cva(dfs):
    ph("Cash & Voucher Assistance","Transfer tracking — payment status, modalities, beneficiary profile")
    df=dfs.get("CVA_Cash_Transfers",pd.DataFrame())
    if df.empty: st.info("No CVA_Cash_Transfers sheet found."); return
    th=TH()
    c1,c2,c3=st.columns(3)
    with c1: s1=st.selectbox("State",         sopts(df,"State"),        key="c_s")
    with c2: s2=st.selectbox("Transfer Type", sopts(df,"Transfer_Type"),key="c_t")
    with c3: s3=st.selectbox("Round",         sopts(df,"Round"),        key="c_r")
    df_f=sfilt(sfilt(sfilt(df.copy(),"State",s1),"Transfer_Type",s2),"Round",s3)
    paid_df=sfilt(df_f,"Transfer_Status","Paid"); pend_df=sfilt(df_f,"Transfer_Status","Pending"); fail_df=sfilt(df_f,"Transfer_Status","Failed")
    usd=paid_df["Transfer_Value_USD"].sum() if has(paid_df,"Transfer_Value_USD") and len(paid_df)>0 else 0
    avg_v=paid_df["Transfer_Value_USD"].mean() if has(paid_df,"Transfer_Value_USD") and len(paid_df)>0 else 0
    fem_pct=slen(df_f,"Female_Headed_HH","Yes")/len(df_f) if len(df_f)>0 and has(df_f,"Female_Headed_HH") else 0
    sh("Key Indicators")
    c1,c2,c3,c4,c5,c6=st.columns(6)
    c1.markdown(kpi("Total Paid", f"${N(usd)}","USD",            "blue",  "💵"),unsafe_allow_html=True)
    c2.markdown(kpi("Paid",       N(len(paid_df)),"completed",   "green", "✅"),unsafe_allow_html=True)
    c3.markdown(kpi("Pending",    N(len(pend_df)),"awaiting",    "amber", "⏳"),unsafe_allow_html=True)
    c4.markdown(kpi("Failed",     N(len(fail_df)),"to check",    "red" if len(fail_df) else "green","❌"),unsafe_allow_html=True)
    c5.markdown(kpi("Avg Value",  f"${avg_v:.0f}","per HH",      "teal",  "📊"),unsafe_allow_html=True)
    c6.markdown(kpi("Female HHH", f"{fem_pct:.0%}","",           "purple","♀"),unsafe_allow_html=True)
    if len(fail_df)>0:
        st.markdown(f"<div class='alert-banner'><span>❌ <b>{len(fail_df)}</b> failed transfers — verification required before next round.</span></div>",unsafe_allow_html=True)
    sh("Transfer Analysis")
    c1,c2=st.columns(2)
    with c1:
        if has(df_f,"Transfer_Status"):
            sc=df_f["Transfer_Status"].value_counts().reset_index(); sc.columns=["Status","Count"]
            cmap={"Paid":"#10B981","Pending":"#F59E0B","Failed":"#EF4444","Cancelled":"#8B5CF6"}
            fig=px.pie(sc,values="Count",names="Status",hole=0.58,color="Status",color_discrete_map=cmap,title="Transfer Status")
            fig.update_traces(marker=dict(line=dict(color=th["bg"],width=2)),textinfo="percent")
            pc(T(fig,h=310))
    with c2:
        if has(df_f,"Payment_Method") and has(df_f,"Transfer_Value_USD"):
            pm=df_f.groupby("Payment_Method")["Transfer_Value_USD"].sum().reset_index().sort_values("Transfer_Value_USD",ascending=True)
            fig=px.bar(pm,x="Transfer_Value_USD",y="Payment_Method",orientation="h",color="Transfer_Value_USD",
                color_continuous_scale=["#1E3A6E","#60A5FA"],title="USD by Payment Method",text="Transfer_Value_USD")
            fig.update_traces(texttemplate="$%{text:,.0f}",textposition="outside",textfont=dict(color=th["text"],size=9))
            fig.update_layout(coloraxis_showscale=False); pc(T(fig,h=310,leg=False))
    sh("Transfer Timeline")
    if has(df_f,"Transfer_Date") and has(df_f,"Transfer_Value_USD"):
        df_t=df_f.copy(); df_t["Transfer_Date"]=pd.to_datetime(df_t["Transfer_Date"],errors="coerce")
        df_t=df_t.dropna(subset=["Transfer_Date"]); df_t["Month"]=df_t["Transfer_Date"].dt.to_period("M").astype(str)
        if has(df_t,"Transfer_Status"):
            agg=df_t.groupby(["Month","Transfer_Status"])["Transfer_Value_USD"].sum().reset_index()
            cmap={"Paid":"#10B981","Pending":"#F59E0B","Failed":"#EF4444","Cancelled":"#8B5CF6"}
            fig=px.bar(agg,x="Month",y="Transfer_Value_USD",color="Transfer_Status",color_discrete_map=cmap,title="Monthly Volume (USD)")
            pc(T(fig,h=270))
    sh("Beneficiary Profile")
    c1,c2=st.columns(2)
    with c1:
        if has(df_f,"Transfer_Type") and has(df_f,"Transfer_Value_USD"):
            tt=df_f.groupby("Transfer_Type")["Transfer_Value_USD"].sum().reset_index(); tt.columns=["Type","Total"]
            fig=px.bar(tt,x="Type",y="Total",color="Type",color_discrete_sequence=COLORS,title="USD by Transfer Type",text="Total")
            fig.update_traces(texttemplate="%{text:,.0f}",textposition="outside",textfont=dict(color=th["text"],size=9)); fig.update_layout(showlegend=False)
            pc(T(fig,h=270))
    with c2:
        if has(df_f,"State") and has(df_f,"Transfer_Value_USD"):
            st_g=df_f.groupby("State")["Transfer_Value_USD"].sum().reset_index()
            fig=px.pie(st_g,values="Transfer_Value_USD",names="State",hole=0.5,title="Value by State",color_discrete_sequence=COLORS)
            fig.update_traces(marker=dict(line=dict(color=th["bg"],width=2)),textinfo="percent")
            pc(T(fig,h=270))

# ══════════════════════════════════════════════════════════════════════════════
# INDICATORS
# ══════════════════════════════════════════════════════════════════════════════
def page_ind(dfs):
    ph("Indicator Tracker","Results-based management — progress vs annual targets by sector")
    df=dfs.get("Indicator_Tracker",pd.DataFrame())
    if df.empty: st.info("No Indicator_Tracker sheet found."); return
    th=TH()
    on_t=slen(df,"Status","On track"); at_r=slen(df,"Status","At risk"); off=slen(df,"Status","Off track"); tot=len(df)
    c1,c2,c3,c4=st.columns(4)
    c1.markdown(kpi("Total",    str(tot),f"indicators",       "blue",  "📋"),unsafe_allow_html=True)
    c2.markdown(kpi("On Track", str(on_t),f"{on_t/tot:.0%}", "green", "✅",f"↑ {on_t/tot:.0%}","up"),unsafe_allow_html=True)
    c3.markdown(kpi("At Risk",  str(at_r),f"{at_r/tot:.0%}", "amber", "⚠️"),unsafe_allow_html=True)
    c4.markdown(kpi("Off Track",str(off), f"{off/tot:.0%}",  "red",   "❌"),unsafe_allow_html=True)
    sh("Performance Overview")
    c1,c2=st.columns([1,2])
    with c1:
        fig=go.Figure(go.Pie(labels=["On Track","At Risk","Off Track"],values=[on_t,at_r,off],hole=0.62,
            marker=dict(colors=["#10B981","#F59E0B","#EF4444"],line=dict(color=th["bg"],width=3)),textinfo="none"))
        fig.add_annotation(text=f"<b>{tot}</b>",x=0.5,y=0.5,font_size=20,showarrow=False,font_color=th["text"])
        fig.update_layout(title="Overall Status")
        pc(T(fig,h=280))
    with c2:
        if has(df,"Sector") and has(df,"Status"):
            perf=df.groupby(["Sector","Status"]).size().reset_index(name="Count")
            cmap={"On track":"#10B981","At risk":"#F59E0B","Off track":"#EF4444"}
            fig=px.bar(perf,x="Sector",y="Count",color="Status",color_discrete_map=cmap,barmode="stack",title="Status by Sector")
            pc(T(fig,h=280))
    if has(df,"Sector"):
        for sec in sorted(df["Sector"].dropna().unique()):
            df_sec=df[df["Sector"]==sec]; sh(f"Sector — {sec}")
            for _,row in df_sec.iterrows():
                ind=str(row.get("Indicator","")); unit=str(row.get("Unit",""))
                target=row.get("Annual Target",None); cumul=row.get("Cumulative",None)
                q1=float(row.get("Q1 Achieved",0) or 0); q2=float(row.get("Q2 Achieved",0) or 0)
                q3=float(row.get("Q3 Achieved",0) or 0); q4=float(row.get("Q4 (Partial)",0) or 0)
                status=str(row.get("Status",""))
                has_t=pd.notna(target) and str(target) not in ["","nan","None"]
                if has_t:
                    try:
                        t=float(str(target).replace(",","").replace("%","")); cv=float(str(cumul).replace(",","").replace("%","")) if pd.notna(cumul) else 0
                        pct=min(cv/t,1.0) if t>0 else 0
                    except: t,cv,pct=0,0,0
                    bc="#10B981" if pct>=0.8 else "#F59E0B" if pct>=0.6 else "#EF4444"
                    st.markdown(f"""<div class='ind-card'>
                      <div style='display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:7px;'>
                        <div><div class='ind-name'>{ind}</div><div class='ind-vals'>Target: {N(t)} {unit} · Achieved: {N(cv)} · {pct*100:.1f}%</div></div>
                        <div>{bdg(status)}</div>
                      </div>
                      <div class='pbar-wrap'><div class='pbar' style='width:{pct*100:.1f}%;background:{bc};'></div></div>
                      <div style='display:flex;gap:16px;margin-top:5px;'>
                        <span class='ind-vals'>Q1: {N(q1)}</span><span class='ind-vals'>Q2: {N(q2)}</span>
                        <span class='ind-vals'>Q3: {N(q3)}</span><span class='ind-vals'>Q4: {N(q4)}</span>
                        <span class='ind-vals' style='margin-left:auto;color:#60A5FA;'>Cumul: {N(q1+q2+q3+q4)}</span>
                      </div>
                    </div>""",unsafe_allow_html=True)
                else:
                    st.markdown(f"""<div class='ind-card' style='display:flex;justify-content:space-between;align-items:center;'>
                      <div><div class='ind-name'>{ind}</div><div class='ind-vals'>Count — no annual target</div></div>
                      <div style='display:flex;align-items:center;gap:10px;'>
                        <span style='font-size:1.1rem;font-weight:700;color:{th["text"]};'>{N(cumul) if pd.notna(cumul) else "—"} <span style='font-size:.7rem;color:#64748B;'>{unit}</span></span>
                        {bdg(status)}
                      </div>
                    </div>""",unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# RAW DATA
# ══════════════════════════════════════════════════════════════════════════════
def page_raw(dfs):
    ph("Raw Data Explorer","Browse, filter and export program datasets")
    sheet=st.selectbox("Select dataset",list(dfs.keys()))
    df=dfs[sheet]
    c1,c2=st.columns([3,1])
    with c1: st.markdown(f"<div style='padding:.5rem 0;font-size:.8rem;color:#64748B;'>{len(df):,} rows · {len(df.columns)} columns</div>",unsafe_allow_html=True)
    with c2: st.download_button("⬇ Download CSV",df.to_csv(index=False).encode(),file_name=f"{sheet}.csv",mime="text/csv",use_container_width=True)
    num_cols=df.select_dtypes(include="number").columns.tolist()
    if num_cols:
        sh("Quick Statistics")
        st.dataframe(df[num_cols].describe().round(2),use_container_width=True)
    sh("Data Table")
    st.dataframe(df,use_container_width=True,height=500)

# ══════════════════════════════════════════════════════════════════════════════
# AUTOMATIC REPORT GENERATOR
# ══════════════════════════════════════════════════════════════════════════════
def build_pdf_report(dfs):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=2*cm, bottomMargin=2*cm,
                            leftMargin=2.2*cm, rightMargin=2.2*cm)
    styles = getSampleStyleSheet()
    SI_BLUE = rl_colors.HexColor("#1A3A6B")
    SI_ACCENT = rl_colors.HexColor("#3B82F6")
    SI_LIGHT = rl_colors.HexColor("#EFF6FF")
    SI_GREEN = rl_colors.HexColor("#10B981")
    SI_AMBER = rl_colors.HexColor("#F59E0B")
    SI_RED   = rl_colors.HexColor("#EF4444")
    GRAY     = rl_colors.HexColor("#64748B")
    LIGHTGRAY= rl_colors.HexColor("#F8FAFC")

    H1 = ParagraphStyle("h1", parent=styles["Heading1"], fontSize=18, textColor=SI_BLUE,
                          spaceAfter=6, fontName="Helvetica-Bold")
    H2 = ParagraphStyle("h2", parent=styles["Heading2"], fontSize=13, textColor=SI_BLUE,
                          spaceBefore=14, spaceAfter=4, fontName="Helvetica-Bold")
    H3 = ParagraphStyle("h3", parent=styles["Heading3"], fontSize=11, textColor=SI_ACCENT,
                          spaceBefore=10, spaceAfter=4, fontName="Helvetica-Bold")
    BODY = ParagraphStyle("body", parent=styles["Normal"], fontSize=10, textColor=rl_colors.HexColor("#1E293B"),
                           spaceAfter=6, leading=15, fontName="Helvetica")
    SMALL= ParagraphStyle("small",parent=styles["Normal"], fontSize=8.5, textColor=GRAY,
                           spaceAfter=4, leading=12, fontName="Helvetica")
    CENTER = ParagraphStyle("center",parent=BODY, alignment=TA_CENTER)
    RIGHT  = ParagraphStyle("right", parent=SMALL,alignment=TA_RIGHT)

    story = []
    now = datetime.now().strftime("%B %d, %Y")
    page_w = A4[0] - 4.2*cm

    def hr(): return HRFlowable(width="100%",thickness=1,color=rl_colors.HexColor("#E2E8F0"),spaceAfter=8,spaceBefore=4)
    def sp(n=8): return Spacer(1, n)

    def kpi_table(rows):
        col_w = page_w / len(rows)
        cells = []
        for label, value, sub in rows:
            cells.append([
                Paragraph(label.upper(), ParagraphStyle("kl",parent=SMALL,textColor=GRAY,fontSize=7.5,fontName="Helvetica-Bold",letterSpacing=0.5)),
                Paragraph(value, ParagraphStyle("kv",parent=styles["Normal"],fontSize=18,fontName="Helvetica-Bold",textColor=SI_BLUE)),
                Paragraph(sub, SMALL),
            ])
        tdata = [cells[i] for i in range(len(cells))]
        # Transpose: one row per column
        tdata_t = [[cells[i][j] for i in range(len(cells))] for j in range(3)]
        widths = [col_w]*len(rows)
        t = Table(tdata_t, colWidths=widths)
        t.setStyle(TableStyle([
            ("BACKGROUND",(0,0),(-1,-1),SI_LIGHT),
            ("ROWBACKGROUNDS",(0,0),(-1,-1),[SI_LIGHT,SI_LIGHT]),
            ("BOX",(0,0),(-1,-1),0.5,rl_colors.HexColor("#BFDBFE")),
            ("INNERGRID",(0,0),(-1,-1),0.3,rl_colors.HexColor("#DBEAFE")),
            ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
            ("TOPPADDING",(0,0),(-1,-1),8),
            ("BOTTOMPADDING",(0,0),(-1,-1),8),
            ("LEFTPADDING",(0,0),(-1,-1),10),
            ("RIGHTPADDING",(0,0),(-1,-1),6),
        ]))
        return t

    def data_table(headers, rows, col_widths=None):
        data = [headers] + rows
        cw = col_widths or [page_w/len(headers)]*len(headers)
        t = Table(data, colWidths=cw, repeatRows=1)
        ts = TableStyle([
            ("BACKGROUND",(0,0),(-1,0),SI_BLUE),
            ("TEXTCOLOR",(0,0),(-1,0),rl_colors.white),
            ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),
            ("FONTSIZE",(0,0),(-1,0),9),
            ("ALIGN",(0,0),(-1,0),"CENTER"),
            ("ROWBACKGROUNDS",(0,1),(-1,-1),[LIGHTGRAY,rl_colors.white]),
            ("FONTSIZE",(0,1),(-1,-1),8.5),
            ("FONTNAME",(0,1),(-1,-1),"Helvetica"),
            ("ALIGN",(1,1),(-1,-1),"CENTER"),
            ("ALIGN",(0,1),(0,-1),"LEFT"),
            ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
            ("TOPPADDING",(0,0),(-1,-1),5),
            ("BOTTOMPADDING",(0,0),(-1,-1),5),
            ("LEFTPADDING",(0,0),(-1,-1),8),
            ("RIGHTPADDING",(0,0),(-1,-1),8),
            ("BOX",(0,0),(-1,-1),0.5,rl_colors.HexColor("#CBD5E1")),
            ("LINEBELOW",(0,0),(-1,0),1,rl_colors.HexColor("#1E40AF")),
        ])
        t.setStyle(ts)
        return t

    # ── COVER PAGE ──────────────────────────────────────────────────────────
    story.append(sp(60))
    story.append(Paragraph("SOLIDARITES INTERNATIONAL", ParagraphStyle("cover_org",parent=styles["Normal"],
        fontSize=11,textColor=SI_ACCENT,fontName="Helvetica-Bold",alignment=TA_CENTER,letterSpacing=1.5)))
    story.append(sp(8))
    story.append(Paragraph("Sudan Mission", ParagraphStyle("cover_mission",parent=styles["Normal"],
        fontSize=28,textColor=SI_BLUE,fontName="Helvetica-Bold",alignment=TA_CENTER)))
    story.append(Paragraph("Information Management Program Report", ParagraphStyle("cover_sub",parent=styles["Normal"],
        fontSize=15,textColor=GRAY,fontName="Helvetica",alignment=TA_CENTER,spaceAfter=4)))
    story.append(sp(6))
    story.append(HRFlowable(width="60%",thickness=2,color=SI_ACCENT,hAlign="CENTER",spaceAfter=14,spaceBefore=4))
    story.append(Paragraph(f"Generated: {now}", ParagraphStyle("cover_date",parent=styles["Normal"],
        fontSize=10,textColor=GRAY,fontName="Helvetica",alignment=TA_CENTER)))
    story.append(Paragraph("Reporting Period: January 2025 – April 2026", ParagraphStyle("cover_period",parent=styles["Normal"],
        fontSize=10,textColor=GRAY,fontName="Helvetica",alignment=TA_CENTER)))
    story.append(sp(30))
    story.append(Paragraph("⚠ CONFIDENTIAL — For internal use only", ParagraphStyle("cover_conf",parent=styles["Normal"],
        fontSize=9,textColor=rl_colors.HexColor("#DC2626"),fontName="Helvetica-Bold",alignment=TA_CENTER)))
    story.append(PageBreak())

    # ── EXECUTIVE SUMMARY ───────────────────────────────────────────────────
    story.append(Paragraph("1. Executive Summary", H1))
    story.append(hr())
    df_b = dfs.get("Beneficiary_Registration",pd.DataFrame())
    df_w = dfs.get("WASH_Monitoring",pd.DataFrame())
    df_f = dfs.get("FSL_Distribution",pd.DataFrame())
    df_c = dfs.get("CVA_Cash_Transfers",pd.DataFrame())
    df_i = dfs.get("Indicator_Tracker",pd.DataFrame())

    tot  = len(df_b)
    act  = slen(df_b,"Registration_Status","Active")
    wr   = int(ssum(df_w,"Reached_Beneficiaries"))
    fhh  = int(ssum(df_f,"HH_Reached"))
    paid = sfilt(df_c,"Transfer_Status","Paid")
    usd  = paid["Transfer_Value_USD"].sum() if has(paid,"Transfer_Value_USD") and len(paid)>0 else 0
    on_t = slen(df_i,"Status","On track"); at_r=slen(df_i,"Status","At risk"); off_t=slen(df_i,"Status","Off track"); ti=len(df_i)
    states_n = suniq(df_b,"State")

    story.append(Paragraph(
        f"This report presents the consolidated program performance of the Solidarites International (SI) Sudan Mission "
        f"for the period January 2025 to April 2026. The mission is operational across <b>{states_n} states</b> of Sudan, "
        f"providing multi-sector humanitarian assistance in WASH, Food Security & Livelihoods (FSL), Shelter & NFI, "
        f"and Cash & Voucher Assistance (CVA).", BODY))
    story.append(Paragraph(
        f"As of the reporting date, the mission has registered a total of <b>{tot:,} beneficiaries</b>, "
        f"of whom <b>{act:,} ({act/tot:.0%})</b> are currently active in the program. "
        f"WASH activities have cumulatively reached <b>{wr:,} individuals</b>, while FSL distributions "
        f"have covered <b>{fhh:,} households</b>. Cash transfers totalling <b>${usd:,.0f}</b> have been disbursed "
        f"to eligible households.", BODY))
    story.append(sp(6))
    story.append(kpi_table([
        ("Total Beneficiaries", f"{tot:,}", f"{act:,} active ({act/tot:.0%})" if tot else ""),
        ("WASH Individuals", f"{wr:,}", "cumulative reached"),
        ("FSL Households", f"{fhh:,}", "all distributions"),
        ("Cash Disbursed", f"${usd:,.0f}", "USD paid out"),
        ("States Covered", str(states_n), "operational areas"),
    ]))
    story.append(sp(12))

    # Indicator status narrative
    story.append(Paragraph(
        f"Of the <b>{ti}</b> program indicators tracked in the results framework, <b>{on_t}</b> are currently "
        f"<b style='color:green;'>On Track</b> ({on_t/ti:.0%}), <b>{at_r}</b> are <b>At Risk</b> ({at_r/ti:.0%}), "
        f"and <b>{off_t}</b> are <b>Off Track</b> ({off_t/ti:.0%}). "
        f"Immediate attention is required for off-track indicators, particularly in sectors experiencing supply chain disruptions "
        f"or low field coverage.", BODY) if ti else Paragraph("No indicator data available.", BODY))

    story.append(PageBreak())

    # ── SECTOR: BENEFICIARIES ───────────────────────────────────────────────
    story.append(Paragraph("2. Beneficiary Registration", H1))
    story.append(hr())
    if not df_b.empty:
        story.append(Paragraph("2.1 Overview", H2))
        story.append(Paragraph(
            f"The beneficiary registry contains <b>{tot:,} records</b> across {suniq(df_b,'State')} states and "
            f"{suniq(df_b,'Locality')} localities. The dominant displacement categories are IDPs and host community members.",BODY))
        # Breakdown table
        if has(df_b,"Sector"):
            sec_cnt = df_b["Sector"].value_counts().reset_index(); sec_cnt.columns=["Sector","Count"]
            sec_cnt["% of Total"] = (sec_cnt["Count"]/tot*100).map(lambda x:f"{x:.1f}%")
            headers=["Sector","Beneficiaries","% of Total"]
            rows=[[s,f"{c:,}",p] for s,c,p in sec_cnt.values.tolist()]
            story.append(Paragraph("Table 1 — Beneficiaries by Sector",H3))
            story.append(data_table(headers,rows,[8*cm,4*cm,4*cm]))
            story.append(sp(8))
        if has(df_b,"Displacement_Status"):
            disp=df_b["Displacement_Status"].value_counts().reset_index(); disp.columns=["Status","Count"]
            disp["% of Total"]=(disp["Count"]/tot*100).map(lambda x:f"{x:.1f}%")
            story.append(Paragraph("Table 2 — Displacement Status Breakdown",H3))
            story.append(data_table(["Displacement Status","Count","% of Total"],
                [[s,f"{c:,}",p] for s,c,p in disp.values.tolist()],[7*cm,4*cm,4*cm]))
            story.append(sp(8))
        if has(df_b,"Sex"):
            fem=slen(df_b,"Sex","Female"); male=tot-fem
            story.append(Paragraph("2.2 Gender & Vulnerability", H2))
            story.append(Paragraph(f"Of all registered beneficiaries, <b>{fem:,} ({fem/tot:.0%})</b> are female and "
                                    f"<b>{male:,} ({male/tot:.0%})</b> are male. The program is aligned with SI's "
                                    f"gender mainstreaming policy, targeting female-headed households as a priority group.", BODY))

    story.append(PageBreak())

    # ── SECTOR: WASH ────────────────────────────────────────────────────────
    story.append(Paragraph("3. WASH Program Performance", H1))
    story.append(hr())
    if not df_w.empty:
        reached=int(ssum(df_w,"Reached_Beneficiaries")); target=int(ssum(df_w,"Target_Beneficiaries")) or 1
        pct=reached/target; wv=int(ssum(df_w,"Water_Volume_Liters")); lat=int(ssum(df_w,"Latrine_Units_Built")); hyg=int(ssum(df_w,"Hygiene_Kits_Dist"))
        story.append(Paragraph(
            f"The WASH program has reached <b>{reached:,} individuals</b> against a target of <b>{target:,}</b>, "
            f"representing an overall coverage rate of <b>{pct:.0%}</b>. "
            f"Water distribution totalled <b>{wv:,} litres</b>, <b>{lat:,} latrine units</b> were constructed or rehabilitated, "
            f"and <b>{hyg:,} hygiene kits</b> were distributed to households in need.", BODY))
        story.append(kpi_table([
            ("Individuals Reached",f"{reached:,}",f"{pct:.0%} of target"),
            ("Water Distributed",f"{wv:,} L","litres"),
            ("Latrines Built",f"{lat:,}","units"),
            ("Hygiene Kits",f"{hyg:,}","distributed"),
        ]))
        story.append(sp(10))
        if has(df_w,"Activity_Type"):
            grp=df_w.groupby("Activity_Type")[["Target_Beneficiaries","Reached_Beneficiaries"]].sum().reset_index()
            grp["Coverage"]=grp.apply(lambda r: f"{r['Reached_Beneficiaries']/r['Target_Beneficiaries']:.0%}" if r["Target_Beneficiaries"]>0 else "N/A",axis=1)
            story.append(Paragraph("Table 3 — WASH Performance by Activity Type",H3))
            rows=[[r["Activity_Type"],f"{int(r['Target_Beneficiaries']):,}",f"{int(r['Reached_Beneficiaries']):,}",r["Coverage"]] for _,r in grp.iterrows()]
            story.append(data_table(["Activity Type","Target","Reached","Coverage Rate"],rows,[6*cm,3*cm,3*cm,3*cm]))
    else:
        story.append(Paragraph("No WASH data available in the uploaded database.",BODY))

    story.append(PageBreak())

    # ── SECTOR: FSL ─────────────────────────────────────────────────────────
    story.append(Paragraph("4. Food Security & Livelihoods (FSL)", H1))
    story.append(hr())
    if not df_f.empty:
        hht=int(ssum(df_f,"HH_Targeted")); hhr=int(ssum(df_f,"HH_Reached"))
        qp=ssum(df_f,"Quantity_Planned"); qd=ssum(df_f,"Quantity_Distributed")
        fem_fsl=int(ssum(df_f,"Female_HHH_Reached")); pb=slen(df_f,"Pipeline_Status","Pipeline break")
        cov=hhr/hht if hht else 0
        story.append(Paragraph(
            f"FSL distributions have reached <b>{hhr:,} households</b> out of a planned target of <b>{hht:,}</b> "
            f"(coverage rate: <b>{cov:.0%}</b>). Female-headed households accounted for <b>{fem_fsl:,}</b> of beneficiary households "
            f"({fem_fsl/hhr:.0%} of reached). Total commodity volume distributed stands at <b>{qd:,.1f}</b> units "
            f"against a plan of <b>{qp:,.1f}</b> units.", BODY))
        if pb:
            story.append(Paragraph(f"⚠ Supply Chain Alert: <b>{pb} pipeline breaks</b> were recorded during the reporting period. "
                                    f"Program teams should coordinate with the logistics cluster to address supply disruptions.",BODY))
        story.append(kpi_table([
            ("HH Reached",f"{hhr:,}",f"{cov:.0%} of target"),
            ("Qty Distributed",f"{qd:,.0f}","units"),
            ("Female HHH",f"{fem_fsl:,}",f"{fem_fsl/hhr:.0%} of reached" if hhr else ""),
            ("Pipeline Breaks",str(pb),"supply alerts"),
        ]))
        story.append(sp(10))
        if has(df_f,"Commodity_Type"):
            comm=df_f.groupby("Commodity_Type")["HH_Reached"].sum().reset_index().sort_values("HH_Reached",ascending=False)
            story.append(Paragraph("Table 4 — HH Reached by Commodity Type",H3))
            rows=[[r["Commodity_Type"],f"{int(r['HH_Reached']):,}"] for _,r in comm.iterrows()]
            story.append(data_table(["Commodity","HH Reached"],rows,[9*cm,5*cm]))
    else:
        story.append(Paragraph("No FSL data available in the uploaded database.",BODY))

    story.append(PageBreak())

    # ── SECTOR: CVA ─────────────────────────────────────────────────────────
    story.append(Paragraph("5. Cash & Voucher Assistance (CVA)", H1))
    story.append(hr())
    if not df_c.empty:
        paid=sfilt(df_c,"Transfer_Status","Paid"); pend=sfilt(df_c,"Transfer_Status","Pending"); fail=sfilt(df_c,"Transfer_Status","Failed")
        usd=paid["Transfer_Value_USD"].sum() if has(paid,"Transfer_Value_USD") and len(paid)>0 else 0
        avg_v=paid["Transfer_Value_USD"].mean() if has(paid,"Transfer_Value_USD") and len(paid)>0 else 0
        fem_cva=slen(df_c,"Female_Headed_HH","Yes")
        story.append(Paragraph(
            f"A total of <b>{len(paid):,} cash transfers</b> have been successfully paid, disbursing <b>${usd:,.0f} USD</b> "
            f"to eligible households, with an average transfer value of <b>${avg_v:,.0f}</b> per household. "
            f"Female-headed households represent <b>{fem_cva:,}</b> beneficiaries "
            f"({fem_cva/len(df_c):.0%} of all transfers).", BODY))
        if len(fail)>0:
            story.append(Paragraph(f"⚠ Transfer Alert: <b>{len(fail)} transfers</b> failed and require investigation before the next payment cycle.",BODY))
        story.append(kpi_table([
            ("Total Paid",f"${usd:,.0f}","USD disbursed"),
            ("Paid Transfers",f"{len(paid):,}","completed"),
            ("Pending",f"{len(pend):,}","awaiting"),
            ("Failed",f"{len(fail):,}","to investigate"),
        ]))
        story.append(sp(10))
        if has(df_c,"Payment_Method") and has(df_c,"Transfer_Value_USD"):
            pm=df_c.groupby("Payment_Method")["Transfer_Value_USD"].sum().reset_index().sort_values("Transfer_Value_USD",ascending=False)
            story.append(Paragraph("Table 5 — USD Disbursed by Payment Method",H3))
            rows=[[r["Payment_Method"],f"${r['Transfer_Value_USD']:,.0f}"] for _,r in pm.iterrows()]
            story.append(data_table(["Payment Method","Total USD"],rows,[9*cm,5*cm]))
    else:
        story.append(Paragraph("No CVA data available.",BODY))

    story.append(PageBreak())

    # ── INDICATOR TRACKER ───────────────────────────────────────────────────
    story.append(Paragraph("6. Program Indicators — Results Framework", H1))
    story.append(hr())
    if not df_i.empty:
        story.append(Paragraph(
            f"The program results framework tracks <b>{ti}</b> indicators across four sectors. "
            f"As of the reporting date, <b>{on_t} indicators ({on_t/ti:.0%})</b> are on track, "
            f"<b>{at_r} ({at_r/ti:.0%})</b> are at risk, and <b>{off_t} ({off_t/ti:.0%})</b> are off track.", BODY))
        story.append(sp(6))
        # Full indicator table
        headers=["Indicator","Unit","Annual Target","Cumulative","% vs Target","Status"]
        rows=[]
        for _,row in df_i.iterrows():
            ind=str(row.get("Indicator",""))[:55]; unit=str(row.get("Unit",""))
            targ=row.get("Annual Target",None); cumul=row.get("Cumulative",None); status=str(row.get("Status",""))
            try:
                t=float(str(targ).replace(",","").replace("%","")) if pd.notna(targ) and str(targ) not in ["","nan"] else None
                cv=float(str(cumul).replace(",","").replace("%","")) if pd.notna(cumul) and str(cumul) not in ["","nan"] else 0
                pct_s=f"{cv/t:.0%}" if t and t>0 else "N/A"
                targ_s=f"{t:,.0f}" if t else "N/A"
                cumul_s=f"{cv:,.0f}"
            except: targ_s=str(targ); cumul_s=str(cumul); pct_s="N/A"
            rows.append([ind,unit,targ_s,cumul_s,pct_s,status])
        t_table=data_table(headers,rows,[5.2*cm,1.8*cm,2.2*cm,2.2*cm,2.2*cm,2*cm])
        story.append(t_table)
    else:
        story.append(Paragraph("No indicator data available.",BODY))

    story.append(PageBreak())

    # ── RECOMMENDATIONS ──────────────────────────────────────────────────────
    story.append(Paragraph("7. Recommendations", H1))
    story.append(hr())
    recs = [
        ("Data Quality & Completeness",
         "Ensure all field teams submit data within 48 hours of each activity. Implement automated daily quality checks through the dashboard to flag missing or inconsistent records before they reach program reports."),
        ("WASH Coverage",
         f"Coverage stands at {int(ssum(df_w,'Reached_Beneficiaries'))/max(int(ssum(df_w,'Target_Beneficiaries')),1):.0%} of target. Field teams in underperforming states should be prioritized for supervisory support and resource reallocation."),
        ("CVA Failed Transfers",
         f"{slen(df_c,'Transfer_Status','Failed')} transfers have failed and must be investigated. Coordinate with payment agents to identify root causes (account errors, connectivity issues) and reprocess eligible cases before the next payment round."),
        ("FSL Pipeline Monitoring",
         f"{slen(df_f,'Pipeline_Status','Pipeline break')} pipeline breaks were recorded. The logistics team should increase monitoring frequency and establish a minimum buffer stock threshold to prevent distribution gaps."),
        ("Off-Track Indicators",
         f"{slen(df_i,'Status','Off track')} indicators are off track. Program managers should review implementation plans and propose corrective measures in the next Monthly Program Review (MPR)."),
        ("MEAL Capacity",
         "Consider a refresher training for field data collectors on KoboToolbox protocols and GPS accuracy. High-quality georeferenced data is essential for accurate coverage mapping and cluster reporting compliance."),
    ]
    for i,(title,text) in enumerate(recs,1):
        story.append(Paragraph(f"7.{i} {title}",H3))
        story.append(Paragraph(text,BODY))

    story.append(PageBreak())

    # ── ANNEXES ──────────────────────────────────────────────────────────────
    story.append(Paragraph("Annex — Data Sources & Methodology", H1))
    story.append(hr())
    annex_data = [
        ["Dataset","Sheet Name","Records","Key Variables"],
        ["Beneficiary Registry","Beneficiary_Registration",f"{len(df_b):,}","ID, State, Sector, Sex, Age, GPS"],
        ["WASH Activities","WASH_Monitoring",f"{len(df_w):,}","Activity Type, Target, Reached, Functionality"],
        ["FSL Distributions","FSL_Distribution",f"{len(df_f):,}","Commodity, HH Reached, Pipeline, Donor"],
        ["CVA Transfers","CVA_Cash_Transfers",f"{len(df_c):,}","Transfer Type, Value USD, Status, Method"],
        ["Indicator Tracker","Indicator_Tracker",f"{len(df_i):,}","Indicator, Target, Q1–Q4, Status"],
    ]
    t_annex=Table(annex_data,colWidths=[4.5*cm,4.5*cm,2.5*cm,5.1*cm])
    t_annex.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),SI_BLUE),("TEXTCOLOR",(0,0),(-1,0),rl_colors.white),
        ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),("FONTSIZE",(0,0),(-1,0),9),
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[LIGHTGRAY,rl_colors.white]),
        ("FONTSIZE",(0,1),(-1,-1),8.5),("FONTNAME",(0,1),(-1,-1),"Helvetica"),
        ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
        ("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5),
        ("LEFTPADDING",(0,0),(-1,-1),8),("RIGHTPADDING",(0,0),(-1,-1),8),
        ("BOX",(0,0),(-1,-1),0.5,rl_colors.HexColor("#CBD5E1")),
    ]))
    story.append(t_annex)
    story.append(sp(16))
    story.append(Paragraph(
        "All data was collected through KoboToolbox electronic data collection forms and processed using Python/pandas. "
        "Geographic data was captured via GPS-enabled devices. "
        "Indicator progress is calculated against annual targets agreed with donors at project inception.",SMALL))
    story.append(sp(20))
    story.append(HRFlowable(width="100%",thickness=1,color=rl_colors.HexColor("#E2E8F0"),spaceAfter=8))
    story.append(Paragraph(f"Solidarites International — Sudan Mission IM Unit | Report generated {now} | CONFIDENTIAL",
        ParagraphStyle("footer",parent=styles["Normal"],fontSize=8,textColor=GRAY,alignment=TA_CENTER,fontName="Helvetica")))

    doc.build(story)
    return buf.getvalue()

def build_text_report(dfs):
    now = datetime.now().strftime("%B %d, %Y")
    df_b=dfs.get("Beneficiary_Registration",pd.DataFrame())
    df_w=dfs.get("WASH_Monitoring",pd.DataFrame())
    df_f=dfs.get("FSL_Distribution",pd.DataFrame())
    df_c=dfs.get("CVA_Cash_Transfers",pd.DataFrame())
    df_i=dfs.get("Indicator_Tracker",pd.DataFrame())
    tot=len(df_b); act=slen(df_b,"Registration_Status","Active")
    wr=int(ssum(df_w,"Reached_Beneficiaries")); fhh=int(ssum(df_f,"HH_Reached"))
    paid=sfilt(df_c,"Transfer_Status","Paid")
    usd=paid["Transfer_Value_USD"].sum() if has(paid,"Transfer_Value_USD") and len(paid)>0 else 0
    on_t=slen(df_i,"Status","On track"); ti=len(df_i)
    lines = [
        "="*70,
        "SOLIDARITES INTERNATIONAL — SUDAN MISSION",
        "INFORMATION MANAGEMENT PROGRAM REPORT",
        f"Generated: {now}",
        "CONFIDENTIAL — FOR INTERNAL USE ONLY",
        "="*70, "",
        "1. EXECUTIVE SUMMARY",
        "-"*40,
        f"Total Beneficiaries:    {tot:,} ({act:,} active — {act/tot:.0%})" if tot else "No beneficiary data.",
        f"WASH Individuals:       {wr:,} reached",
        f"FSL Households:         {fhh:,} reached",
        f"Cash Disbursed:         ${usd:,.0f} USD",
        f"States Covered:         {suniq(df_b,'State')}",
        f"Indicators On Track:    {on_t}/{ti} ({on_t/ti:.0%})" if ti else "No indicator data.",
        "",
        "2. WASH", "-"*40,
        f"Reached: {wr:,} | Target: {int(ssum(df_w,'Target_Beneficiaries')):,} | Coverage: {wr/max(int(ssum(df_w,'Target_Beneficiaries')),1):.0%}",
        f"Water: {int(ssum(df_w,'Water_Volume_Liters')):,} L | Latrines: {int(ssum(df_w,'Latrine_Units_Built')):,} | Hygiene Kits: {int(ssum(df_w,'Hygiene_Kits_Dist')):,}",
        "",
        "3. FSL", "-"*40,
        f"HH Reached: {fhh:,} / {int(ssum(df_f,'HH_Targeted')):,} | Pipeline Breaks: {slen(df_f,'Pipeline_Status','Pipeline break')}",
        f"Female-headed HH: {int(ssum(df_f,'Female_HHH_Reached')):,}",
        "",
        "4. CVA", "-"*40,
        f"Paid: {len(paid):,} transfers | ${usd:,.0f} USD | Failed: {slen(df_c,'Transfer_Status','Failed')}",
        "",
        "5. INDICATORS", "-"*40,
        f"On Track: {on_t} | At Risk: {slen(df_i,'Status','At risk')} | Off Track: {slen(df_i,'Status','Off track')}",
        "",
        "="*70,
        "END OF REPORT",
        "="*70,
    ]
    return "\n".join(lines)

def page_report(dfs):
    ph("Automatic Report Generator","Generate a comprehensive program report in PDF or text format")
    if not dfs:
        st.info("Load the Excel database first to generate a report.")
        return

    sh("Report Configuration")
    c1,c2,c3 = st.columns(3)
    with c1:
        report_type = st.selectbox("Report Format", ["PDF (full report)","Plain Text (summary)"])
    with c2:
        st.markdown("<div style='padding:.5rem 0;font-size:.82rem;color:#64748B;'>Report language</div>",unsafe_allow_html=True)
        st.markdown("<div style='font-weight:600;color:#E2E8F0;'>English</div>",unsafe_allow_html=True)
    with c3:
        st.markdown("<div style='padding:.5rem 0;font-size:.82rem;color:#64748B;'>Generation date</div>",unsafe_allow_html=True)
        st.markdown(f"<div style='font-weight:600;color:#E2E8F0;'>{datetime.now().strftime('%B %d, %Y')}</div>",unsafe_allow_html=True)

    # Preview statistics
    sh("Report Preview — Key Figures")
    df_b=dfs.get("Beneficiary_Registration",pd.DataFrame())
    df_w=dfs.get("WASH_Monitoring",pd.DataFrame())
    df_f=dfs.get("FSL_Distribution",pd.DataFrame())
    df_c=dfs.get("CVA_Cash_Transfers",pd.DataFrame())
    df_i=dfs.get("Indicator_Tracker",pd.DataFrame())
    tot=len(df_b); wr=int(ssum(df_w,"Reached_Beneficiaries"))
    fhh=int(ssum(df_f,"HH_Reached"))
    paid=sfilt(df_c,"Transfer_Status","Paid")
    usd=paid["Transfer_Value_USD"].sum() if has(paid,"Transfer_Value_USD") and len(paid)>0 else 0
    on_t=slen(df_i,"Status","On track"); ti=len(df_i)

    c1,c2,c3,c4,c5 = st.columns(5)
    c1.markdown(kpi("Beneficiaries",N(tot),"registered","blue","👤"),unsafe_allow_html=True)
    c2.markdown(kpi("WASH Reached",N(wr),"individuals","teal","💧"),unsafe_allow_html=True)
    c3.markdown(kpi("FSL HH",N(fhh),"households","green","🌾"),unsafe_allow_html=True)
    c4.markdown(kpi("Cash Paid",f"${N(usd)}","USD","amber","💵"),unsafe_allow_html=True)
    c5.markdown(kpi("Indicators",f"{on_t}/{ti}","on track","green","📊"),unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    sh("Report Contents")
    st.markdown("""<div style='background:var(--panel);border:1px solid var(--border);border-radius:10px;padding:1.2rem 1.5rem;'>
      <div style='font-size:.85rem;color:var(--text);line-height:2;'>
        ✅ &nbsp;Cover page with mission details and generation date<br>
        ✅ &nbsp;Executive summary with consolidated KPIs<br>
        ✅ &nbsp;Section 2 — Beneficiary registration (tables by sector, displacement, sex)<br>
        ✅ &nbsp;Section 3 — WASH program performance (coverage, activities, infrastructure)<br>
        ✅ &nbsp;Section 4 — FSL distribution (commodities, pipeline, gender)<br>
        ✅ &nbsp;Section 5 — CVA cash transfers (status, payment methods)<br>
        ✅ &nbsp;Section 6 — Program indicators (results framework, all sectors)<br>
        ✅ &nbsp;Section 7 — Recommendations based on actual data<br>
        ✅ &nbsp;Annex — Data sources and methodology
      </div>
    </div>""",unsafe_allow_html=True)

    st.markdown("<br>",unsafe_allow_html=True)
    if st.button("🖨️ Generate Report", use_container_width=False):
        if "PDF" in report_type:
            if HAS_PDF:
                with st.spinner("Building PDF report…"):
                    try:
                        pdf_bytes = build_pdf_report(dfs)
                        fname = f"SI_Sudan_IM_Report_{datetime.now().strftime('%Y%m%d')}.pdf"
                        st.download_button("⬇ Download PDF Report", pdf_bytes, file_name=fname,
                                           mime="application/pdf", use_container_width=False)
                        st.success("✅ PDF report generated successfully!")
                    except Exception as e:
                        st.error(f"PDF generation error: {e}")
            else:
                st.warning("ReportLab not installed. Run: pip install reportlab")
        else:
            txt = build_text_report(dfs)
            fname = f"SI_Sudan_IM_Report_{datetime.now().strftime('%Y%m%d')}.txt"
            st.download_button("⬇ Download Text Report", txt.encode(), file_name=fname,
                               mime="text/plain", use_container_width=False)
            st.success("✅ Text report ready!")
            st.code(txt, language=None)

# ══════════════════════════════════════════════════════════════════════════════

# ══════════════════════════════════════════════════════════════════════════════
# DATA SOURCE SELECTION PAGE
# ══════════════════════════════════════════════════════════════════════════════

DS_CSS = """
<style>
.ds-card {
  background: var(--panel); border: 2px solid var(--border);
  border-radius: 14px; padding: 1.8rem 2rem; cursor: pointer;
  transition: all .2s; position: relative; overflow: hidden;
  text-align: center;
}
.ds-card:hover { border-color: var(--accent); transform: translateY(-3px);
  box-shadow: 0 12px 40px rgba(59,130,246,0.15); }
.ds-card.selected { border-color: var(--accent);
  background: rgba(59,130,246,0.07); }
.ds-card::before { content:''; position:absolute; top:0; left:0; right:0; height:3px; }
.ds-card-excel::before { background: linear-gradient(90deg,#10B981,#34D399); }
.ds-card-kobo::before  { background: linear-gradient(90deg,#3B82F6,#60A5FA); }
.ds-icon { font-size: 2.8rem; margin-bottom: .8rem; }
.ds-title { font-size: 1.1rem; font-weight: 700; color: var(--text);
  font-family: var(--font); margin-bottom: .4rem; }
.ds-desc { font-size: .82rem; color: var(--muted); line-height: 1.6; }
.ds-badge { display:inline-block; background:rgba(16,185,129,0.15); color:#34D399;
  font-size:.68rem; font-weight:700; padding:2px 8px; border-radius:12px;
  margin-top:.6rem; letter-spacing:.05em; }
.ds-badge-blue { background:rgba(59,130,246,0.15); color:#60A5FA; }

.kobo-step {
  background: var(--panel); border: 1px solid var(--border);
  border-radius: 12px; padding: 1.4rem 1.8rem; margin-bottom: 1rem;
}
.kobo-step-num {
  display:inline-flex; align-items:center; justify-content:center;
  width:26px; height:26px; border-radius:50%;
  background:var(--accent); color:#fff;
  font-size:.75rem; font-weight:700; margin-right:8px; flex-shrink:0;
}
.kobo-step-title { font-size:.95rem; font-weight:600; color:var(--text);
  display:flex; align-items:center; margin-bottom:.7rem; }

.form-item {
  background: var(--card); border: 1px solid var(--border);
  border-radius: 10px; padding: .9rem 1.1rem; margin-bottom: .5rem;
  display: flex; align-items: center; gap: 12px; transition: all .15s;
}
.form-item:hover { border-color: var(--border2); }
.form-item.selected { border-color: var(--accent); background: rgba(59,130,246,0.05); }
.form-tag { font-size:.7rem; font-weight:600; padding:2px 8px; border-radius:12px;
  background:rgba(59,130,246,0.12); color:var(--accent2); }
.form-meta { font-size:.72rem; color:var(--muted); font-family:var(--mono); }
.form-name { font-size:.88rem; font-weight:500; color:var(--text); }

.server-option {
  background:var(--card); border:1px solid var(--border); border-radius:10px;
  padding:.8rem 1.1rem; cursor:pointer; transition:all .15s; margin-bottom:.4rem;
  display:flex; align-items:center; gap:10px;
}
.server-option:hover { border-color:var(--border2); }
.server-option.selected { border-color:var(--accent); }
.server-dot { width:10px; height:10px; border-radius:50%;
  background:var(--border2); flex-shrink:0; }
.server-dot.active { background:var(--accent); }
</style>
"""

def page_datasource():
    """
    Step-by-step data source selection shown after login, before dashboard.
    Handles both Excel upload and KoBoToolbox API flow.
    """
    inject_css(DARK)
    th = DARK

    # Header
    st.markdown(f"""
    <div style='text-align:center; padding: 2.5rem 0 1.5rem;'>
      <div style='font-size:.8rem;font-weight:700;letter-spacing:.12em;text-transform:uppercase;
        color:{th["accent2"]};margin-bottom:.8rem;'>Step 1 of 2 — Data Source</div>
      <div style='font-size:1.7rem;font-weight:800;color:{th["text"]};font-family:Outfit,sans-serif;margin-bottom:.4rem;'>
        Choose your data source
      </div>
      <div style='font-size:.9rem;color:{th["muted"]};'>
        Select how you want to load program data into the dashboard
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(DS_CSS, unsafe_allow_html=True)

    source = st.session_state.get("ds_choice", None)

    col_l, col_excel, col_kobo, col_r = st.columns([0.5, 1, 1, 0.5])

    with col_excel:
        excel_sel = "selected" if source == "excel" else ""
        st.markdown(f"""<div class='ds-card ds-card-excel {excel_sel}'>
          <div class='ds-icon'>📊</div>
          <div class='ds-title'>Excel / CSV File</div>
          <div class='ds-desc'>Upload a local .xlsx file containing your program data across multiple sheets (beneficiaries, WASH, FSL, CVA, indicators).</div>
          <div class='ds-badge'>✓ Offline · No internet needed</div>
        </div>""", unsafe_allow_html=True)
        if st.button("Use Excel file", use_container_width=True, key="btn_excel"):
            st.session_state["ds_choice"] = "excel"
            st.rerun()

    with col_kobo:
        kobo_sel = "selected" if source == "kobo" else ""
        st.markdown(f"""<div class='ds-card ds-card-kobo {kobo_sel}'>
          <div class='ds-icon'>🔗</div>
          <div class='ds-title'>KoBoToolbox Live Data</div>
          <div class='ds-desc'>Connect directly to your KoBoToolbox account to pull real-time form submissions and build your dashboard from live field data.</div>
          <div class='ds-badge ds-badge-blue'>⚡ Real-time · Always up-to-date</div>
        </div>""", unsafe_allow_html=True)
        if st.button("Connect KoBoToolbox", use_container_width=True, key="btn_kobo"):
            st.session_state["ds_choice"] = "kobo"
            st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    # ── EXCEL FLOW ─────────────────────────────────────────────────────────
    if source == "excel":
        st.markdown(f"""
        <div style='max-width:600px;margin:0 auto;'>
          <div class='kobo-step'>
            <div class='kobo-step-title'><span class='kobo-step-num'>1</span>Upload your Excel database</div>
        """, unsafe_allow_html=True)
        c1, c2, c3 = st.columns([0.5, 2, 0.5])
        with c2:
            up = st.file_uploader("Excel file (.xlsx)", type=["xlsx"], label_visibility="collapsed")
            if up:
                with st.spinner("Loading sheets…"):
                    data = load_data(up)
                st.session_state["dfs"] = data
                st.session_state["data_source"] = "excel"
                st.session_state["ds_step"] = "done"
                st.success(f"✅ {len(data)} sheets loaded: {', '.join(data.keys())}")
                if st.button("→ Open Dashboard", use_container_width=True, key="btn_open_excel"):
                    st.session_state["ds_done"] = True
                    st.rerun()
        st.markdown("</div></div>", unsafe_allow_html=True)

    # ── KOBO FLOW ───────────────────────────────────────────────────────────
    elif source == "kobo":
        kobo_step = st.session_state.get("kobo_step", "server")  # server → auth → forms → done

        st.markdown("<div style='max-width:680px;margin:0 auto;'>", unsafe_allow_html=True)

        # ── Step A: Server selection ──────────────────────────────────────
        server = st.session_state.get("kobo_server", KOBO_BASE)
        server_options = {
            "KoBoToolbox (Global)":           "https://kf.kobotoolbox.org",
            "Humanitarian (OCHA / UN)":       "https://kobo.humanitarianresponse.info",
            "Custom server":                  "__custom__",
        }
        rev_map = {v: k for k, v in server_options.items()}
        current_srv_label = rev_map.get(server, "Custom server")

        with st.container():
            st.markdown(f"""<div class='kobo-step'>
              <div class='kobo-step-title'><span class='kobo-step-num'>1</span>Select KoBoToolbox server</div>
            """, unsafe_allow_html=True)
            srv_choice = st.radio("Server", list(server_options.keys()),
                                  index=list(server_options.keys()).index(current_srv_label)
                                  if current_srv_label in server_options else 0,
                                  label_visibility="collapsed", key="srv_radio")
            chosen_url = server_options[srv_choice]
            if chosen_url == "__custom__":
                chosen_url = st.text_input("Custom server URL",
                                           value=server if server not in server_options.values() else "https://",
                                           placeholder="https://your-kobo-server.org",
                                           label_visibility="collapsed", key="custom_srv")
            if chosen_url != server:
                st.session_state["kobo_server"] = chosen_url
            st.markdown("</div>", unsafe_allow_html=True)

        # ── Step B: Authentication ────────────────────────────────────────
        with st.container():
            st.markdown(f"""<div class='kobo-step'>
              <div class='kobo-step-title'><span class='kobo-step-num'>2</span>Sign in to KoBoToolbox</div>
            """, unsafe_allow_html=True)

            kobo_token = st.session_state.get("kobo_token")

            if kobo_token:
                st.success(f"✅ Connected — token active")
                st.markdown(f"<div class='form-meta'>Server: {st.session_state.get('kobo_server', KOBO_BASE)}</div>", unsafe_allow_html=True)
                if st.button("🔓 Disconnect / change account", key="btn_disco"):
                    for k in ["kobo_token","kobo_forms","kobo_selected_uids","kobo_step"]:
                        st.session_state.pop(k, None)
                    st.rerun()
            else:
                c1, c2 = st.columns(2)
                with c1:
                    ku = st.text_input("KoBoToolbox username", placeholder="your_username", label_visibility="collapsed", key="kobo_user")
                with c2:
                    kp = st.text_input("KoBoToolbox password", type="password", placeholder="Password", label_visibility="collapsed", key="kobo_pass")
                if st.button("🔐 Connect to KoBoToolbox", use_container_width=True, key="btn_kobo_auth"):
                    srv = st.session_state.get("kobo_server", KOBO_BASE)
                    if not ku or not kp:
                        st.error("Please enter both username and password.")
                    else:
                        with st.spinner("Authenticating…"):
                            token, err = kobo_get_token_from_server(srv, ku, kp)
                        if token:
                            st.session_state["kobo_token"] = token
                            st.session_state["kobo_username"] = ku
                            st.session_state["kobo_step"] = "forms"
                            st.success("✅ Connected successfully!")
                            st.rerun()
                        else:
                            st.error(f"Authentication failed: {err}")
            st.markdown("</div>", unsafe_allow_html=True)

        # ── Step C: Form selection ────────────────────────────────────────
        kobo_token = st.session_state.get("kobo_token")
        if kobo_token:
            with st.container():
                st.markdown(f"""<div class='kobo-step'>
                  <div class='kobo-step-title'><span class='kobo-step-num'>3</span>Select KoBoToolbox forms to use in the dashboard</div>
                """, unsafe_allow_html=True)

                # Load form list (cached in session)
                if "kobo_forms" not in st.session_state:
                    srv = st.session_state.get("kobo_server", KOBO_BASE)
                    with st.spinner("Fetching your forms…"):
                        forms, err = kobo_list_forms_from_server(srv, kobo_token)
                    if err:
                        st.error(f"Could not load forms: {err}")
                        forms = []
                    st.session_state["kobo_forms"] = forms

                forms = st.session_state.get("kobo_forms", [])

                if not forms:
                    st.info("No forms found on this account. Make sure you have at least one deployed survey.")
                else:
                    st.markdown(f"<div class='form-meta' style='margin-bottom:.8rem;'>Found <b>{len(forms)}</b> form(s) on your account. Select those to pull into the dashboard.</div>", unsafe_allow_html=True)

                    # Quick filters
                    search = st.text_input("🔍 Search forms", placeholder="Type form name…", label_visibility="collapsed", key="form_search")
                    filtered_forms = [f for f in forms if search.lower() in f.get("name","").lower()] if search else forms

                    selected_uids = st.session_state.get("kobo_selected_uids", set())
                    if not isinstance(selected_uids, set):
                        selected_uids = set(selected_uids)

                    # Select all / none
                    ca, cb = st.columns(2)
                    with ca:
                        if st.button("✅ Select all", key="sel_all", use_container_width=True):
                            selected_uids = {f["uid"] for f in filtered_forms}
                            st.session_state["kobo_selected_uids"] = selected_uids
                            st.rerun()
                    with cb:
                        if st.button("⬜ Clear all", key="sel_none", use_container_width=True):
                            selected_uids = set()
                            st.session_state["kobo_selected_uids"] = selected_uids
                            st.rerun()

                    st.markdown("<br>", unsafe_allow_html=True)

                    # Form list with checkboxes
                    for form in filtered_forms:
                        uid  = form.get("uid","")
                        name = form.get("name","Unnamed form")
                        nb   = form.get("deployment__submission_count", 0)
                        dt   = form.get("date_modified","")[:10] if form.get("date_modified") else "—"
                        sel  = uid in selected_uids
                        sel_class = "selected" if sel else ""

                        st.markdown(f"""<div class='form-item {sel_class}'>
                          <div style='flex:1;'>
                            <div class='form-name'>{name}</div>
                            <div class='form-meta'>{uid} &nbsp;·&nbsp; {nb:,} submissions &nbsp;·&nbsp; Modified: {dt}</div>
                          </div>
                          <span class='form-tag'>{'✓ Selected' if sel else 'Not selected'}</span>
                        </div>""", unsafe_allow_html=True)
                        chk = st.checkbox(f"Select: {name}", value=sel, key=f"chk_{uid}", label_visibility="collapsed")
                        if chk and uid not in selected_uids:
                            selected_uids.add(uid)
                            st.session_state["kobo_selected_uids"] = selected_uids
                        elif not chk and uid in selected_uids:
                            selected_uids.discard(uid)
                            st.session_state["kobo_selected_uids"] = selected_uids

                    st.markdown("<br>", unsafe_allow_html=True)
                    nb_sel = len(selected_uids)
                    if nb_sel > 0:
                        st.success(f"✅ {nb_sel} form(s) selected")
                        if st.button(f"⬇ Pull data from {nb_sel} form(s) & open dashboard →",
                                     use_container_width=True, key="btn_pull"):
                            srv = st.session_state.get("kobo_server", KOBO_BASE)
                            progress = st.progress(0, text="Pulling submissions…")
                            dfs = {}
                            for i, uid in enumerate(list(selected_uids)):
                                form_name = next((f["name"] for f in forms if f["uid"]==uid), uid)
                                progress.progress((i+1)/nb_sel, text=f"Loading: {form_name}…")
                                df_k, err = kobo_fetch_data_from_server(srv, kobo_token, uid)
                                if not df_k.empty:
                                    safe_name = form_name[:31]  # sheet name limit
                                    dfs[safe_name] = df_k
                                elif err:
                                    st.warning(f"⚠ {form_name}: {err}")
                            progress.empty()
                            if dfs:
                                st.session_state["dfs"] = dfs
                                st.session_state["data_source"] = "kobo"
                                st.session_state["ds_done"] = True
                                st.success(f"✅ Data pulled from {len(dfs)} form(s)! Opening dashboard…")
                                st.rerun()
                            else:
                                st.error("No data retrieved. Verify the selected forms have submissions.")
                    else:
                        st.info("Select at least one form to continue.")

                st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)  # max-width wrapper

    # ── Back to login ───────────────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    c1,c2,c3 = st.columns([1,0.4,1])
    with c2:
        if st.button("← Back to login", key="btn_back_login"):
            st.session_state.clear(); st.rerun()


# ── Server-aware wrappers (use session kobo_server) ──────────────────────────

def kobo_get_token_from_server(server, username, password):
    try:
        r = requests.post(f"{server}/token/?format=json",
                          data={"username": username, "password": password}, timeout=15)
        if r.status_code == 200:
            return r.json().get("token"), None
        return None, f"HTTP {r.status_code}: {r.text[:200]}"
    except Exception as e:
        return None, str(e)

def kobo_list_forms_from_server(server, token):
    try:
        r = requests.get(f"{server}/api/v2/assets/?format=json&asset_type=survey&limit=200",
                         headers={"Authorization": f"Token {token}"}, timeout=20)
        if r.status_code == 200:
            return r.json().get("results", []), None
        return [], f"HTTP {r.status_code}"
    except Exception as e:
        return [], str(e)

def kobo_fetch_data_from_server(server, token, uid):
    try:
        all_rows = []
        url = f"{server}/api/v2/assets/{uid}/data/?format=json&limit=500"
        while url:
            r = requests.get(url, headers={"Authorization": f"Token {token}"}, timeout=30)
            if r.status_code != 200:
                return pd.DataFrame(), f"HTTP {r.status_code}"
            j = r.json()
            all_rows.extend(j.get("results", []))
            url = j.get("next")
        if not all_rows:
            return pd.DataFrame(), None
        df = pd.json_normalize(all_rows)
        df.columns = [c.split("/")[-1] if "/" in c else c for c in df.columns]
        return df, None
    except Exception as e:
        return pd.DataFrame(), str(e)


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════
def main():
    # 1. Not authenticated → login
    if not st.session_state.get("auth"):
        login_page(); return

    # 2. Authenticated but data source not chosen/done yet → datasource page
    if not st.session_state.get("ds_done"):
        inject_css(DARK)
        page_datasource(); return

    # 3. Full dashboard
    inject_css(TH())
    top_nav()

    page = st.session_state.get("page","Overview")
    dfs  = st.session_state.get("dfs", {})

    if not dfs and page != "Report":
        st.markdown("""<div style='text-align:center;padding:5rem 2rem;
          background:var(--panel);border:1px dashed var(--border2);
          border-radius:14px;margin-top:2rem;'>
          <div style='font-size:2.5rem;margin-bottom:1rem;'>📂</div>
          <div style='font-size:1.1rem;font-weight:700;color:var(--text);margin-bottom:.5rem;'>No data loaded</div>
          <div style='font-size:.85rem;color:var(--muted);'>
            Go back to the data source page to upload an Excel file or connect KoBoToolbox.
          </div>
        </div>""", unsafe_allow_html=True)
        if st.button("← Change data source"):
            st.session_state["ds_done"] = False
            st.session_state.pop("dfs", None)
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
        return

    dispatch = {
        "Overview":   page_overview,
        "Map":        page_map,
        "WASH":       page_wash,
        "FSL":        page_fsl,
        "CVA":        page_cva,
        "Indicators": page_ind,
        "Raw Data":   page_raw,
        "Report":     page_report,
    }
    dispatch.get(page, page_overview)(dfs)
    st.markdown("</div>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()
