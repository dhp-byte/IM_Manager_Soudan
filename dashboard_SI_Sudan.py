import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import folium
from folium.plugins import MarkerCluster, HeatMap
from streamlit_folium import st_folium
from datetime import datetime
import warnings
warnings.filterwarnings("ignore")

# ══════════════════════════════════════════════════════════════════════════════
# PAGE CONFIG
# ══════════════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="SI Sudan · IM Dashboard",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ══════════════════════════════════════════════════════════════════════════════
# THEME & CSS
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');

:root {
  --navy:   #060D1F;  --slate:  #0F1B2D;  --panel: #131F35;
  --border: rgba(99,140,210,0.12);  --border2: rgba(99,140,210,0.22);
  --accent: #3B82F6;  --accent2: #60A5FA;
  --red:    #EF4444;  --amber:   #F59E0B;  --green: #10B981;
  --teal:   #14B8A6;  --purple:  #8B5CF6;  --pink:  #EC4899;
  --text:   #E2E8F0;  --muted:   #64748B;  --dim:   #334155;
  --font:   'Outfit', sans-serif;  --mono: 'JetBrains Mono', monospace;
  --r: 10px;
}
*, *::before, *::after { box-sizing: border-box; }
html, body { font-family: var(--font); background: var(--navy); color: var(--text); }
[data-testid="stAppViewContainer"] { background: var(--navy) !important; }
[data-testid="stMain"]             { background: var(--navy) !important; }
[data-testid="block-container"]    { padding-top: 1.5rem !important; }
[data-testid="stHeader"]           { background: transparent !important; }
[data-testid="stSidebar"] {
  background: var(--slate) !important;
  border-right: 1px solid var(--border) !important;
}
[data-testid="stSidebar"] * { font-family: var(--font) !important; }

/* RADIO NAV */
[data-testid="stRadio"] > div { display:flex; flex-direction:column; gap:2px; }
[data-testid="stRadio"] label {
  background:transparent !important; border-radius:8px !important;
  padding:8px 12px !important; cursor:pointer;
  color:var(--muted) !important; font-size:0.88rem !important;
  font-weight:500 !important; transition:all 0.15s !important; border:none !important;
}
[data-testid="stRadio"] label:hover { background:var(--dim) !important; color:var(--text) !important; }
[data-testid="stRadio"] [role="radio"] { display:none !important; }

/* INPUTS */
[data-testid="stSelectbox"] > div > div {
  background:var(--panel) !important; border:1px solid var(--border2) !important;
  border-radius:var(--r) !important; color:var(--text) !important;
}
[data-testid="stTextInput"] > div > div > input {
  background:var(--panel) !important; border:1px solid var(--border2) !important;
  color:var(--text) !important; border-radius:var(--r) !important; font-family:var(--font) !important;
}
[data-baseweb="select"] * { color:var(--text) !important; }
[data-baseweb="menu"]    { background:var(--panel) !important; }
label, p { color:var(--muted) !important; font-size:0.82rem !important; }

/* BUTTONS */
.stButton > button {
  background:var(--accent) !important; color:#fff !important;
  border:none !important; border-radius:var(--r) !important;
  font-family:var(--font) !important; font-weight:600 !important;
  font-size:0.9rem !important; padding:0.6rem 1.4rem !important; transition:all 0.2s !important;
}
.stButton > button:hover { background:var(--accent2) !important; transform:translateY(-1px) !important; }
[data-testid="stDownloadButton"] > button {
  background:var(--panel) !important; border:1px solid var(--border2) !important;
  color:var(--text) !important; border-radius:var(--r) !important; font-family:var(--font) !important;
}
[data-testid="stFileUploader"] {
  background:var(--panel) !important; border:1px dashed var(--border2) !important; border-radius:var(--r) !important;
}
[data-testid="stDataFrame"] { border-radius:var(--r); overflow:hidden; }
::-webkit-scrollbar { width:4px; height:4px; }
::-webkit-scrollbar-thumb { background:var(--dim); border-radius:2px; }

/* KPI CARDS */
.kpi-card {
  background:var(--panel); border:1px solid var(--border);
  border-radius:var(--r); padding:1.1rem 1.2rem 1rem;
  position:relative; overflow:hidden; margin-bottom:4px;
}
.kpi-card::after {
  content:''; position:absolute; bottom:0; left:0; right:0; height:2px;
}
.kpi-blue::after   { background:linear-gradient(90deg,#3B82F6,#60A5FA); }
.kpi-green::after  { background:linear-gradient(90deg,#10B981,#34D399); }
.kpi-amber::after  { background:linear-gradient(90deg,#F59E0B,#FCD34D); }
.kpi-red::after    { background:linear-gradient(90deg,#EF4444,#F87171); }
.kpi-purple::after { background:linear-gradient(90deg,#8B5CF6,#A78BFA); }
.kpi-teal::after   { background:linear-gradient(90deg,#14B8A6,#5EEAD4); }
.kpi-label { font-size:0.66rem; font-weight:700; letter-spacing:.1em; text-transform:uppercase; color:var(--muted); margin-bottom:0.45rem; }
.kpi-value { font-size:1.75rem; font-weight:800; color:#fff; line-height:1; font-family:var(--font); }
.kpi-sub   { font-size:0.7rem; color:var(--muted); margin-top:0.3rem; }
.kpi-icon  { position:absolute; top:0.9rem; right:1rem; font-size:1.3rem; opacity:0.15; }
.kpi-delta { font-size:0.7rem; font-weight:700; margin-top:0.35rem; display:inline-flex;
             align-items:center; gap:3px; padding:1px 7px; border-radius:20px; }
.d-up   { background:rgba(16,185,129,0.15); color:#34D399; }
.d-down { background:rgba(239,68,68,0.15);  color:#F87171; }
.d-mid  { background:rgba(245,158,11,0.15); color:#FCD34D; }

/* SECTION HEADER */
.sh {
  font-size:0.68rem; font-weight:700; letter-spacing:.12em; text-transform:uppercase;
  color:var(--accent2); margin:1.6rem 0 0.9rem;
  display:flex; align-items:center; gap:8px;
}
.sh::after { content:''; flex:1; height:1px; background:var(--border); }

/* PAGE HEADER */
.ph { border-bottom:1px solid var(--border); margin-bottom:1.6rem; padding-bottom:1rem; }
.ph h1 { font-size:1.65rem; font-weight:800; color:#fff; margin:0 0 3px; font-family:var(--font); }
.ph p  { font-size:0.82rem; color:var(--muted) !important; margin:0; }

/* BADGE */
.badge { display:inline-block; padding:2px 9px; border-radius:20px; font-size:0.67rem; font-weight:700; letter-spacing:.04em; }
.bg { background:rgba(16,185,129,0.18);  color:#34D399; }
.ba { background:rgba(245,158,11,0.18);  color:#FCD34D; }
.br { background:rgba(239,68,68,0.18);   color:#F87171; }
.bn { background:rgba(100,116,139,0.18); color:#94A3B8; }

/* PROGRESS */
.pbar-wrap { background:rgba(255,255,255,0.06); border-radius:4px; height:5px; overflow:hidden; margin:5px 0 3px; }
.pbar { height:100%; border-radius:4px; }

/* INDICATOR CARD */
.ind-card {
  background:var(--panel); border:1px solid var(--border);
  border-radius:var(--r); padding:0.9rem 1.1rem; margin-bottom:0.5rem;
}
.ind-name { font-size:0.86rem; font-weight:500; color:var(--text); }
.ind-vals { font-size:0.72rem; color:var(--muted); font-family:var(--mono); }

/* ALERT BANNER */
.alert-banner {
  background:rgba(239,68,68,0.07); border:1px solid rgba(239,68,68,0.2);
  border-left:3px solid var(--red); border-radius:var(--r);
  padding:0.75rem 1rem; margin-bottom:0.6rem; display:flex; align-items:center; gap:10px;
}
.alert-banner span { font-size:0.83rem; color:#FCA5A5; }

/* LOGIN */
.login-card {
  width:400px; background:var(--slate); border:1px solid var(--border2);
  border-radius:18px; padding:2.8rem 2.5rem; box-shadow:0 40px 80px rgba(0,0,0,0.5);
}
.login-badge {
  display:inline-block; background:rgba(59,130,246,0.15); color:var(--accent2);
  font-size:0.69rem; font-weight:700; letter-spacing:.1em; text-transform:uppercase;
  padding:3px 10px; border-radius:20px; margin-bottom:1rem;
}
.login-title { font-size:1.6rem; font-weight:800; color:#fff; margin-bottom:0.3rem; font-family:var(--font); }
.login-sub   { font-size:0.82rem; color:var(--muted); margin-bottom:2rem; }

/* SIDEBAR */
.sb-logo { font-size:1.05rem; font-weight:800; color:#fff; margin-bottom:2px; font-family:var(--font); }
.sb-sub  { font-size:0.67rem; color:var(--muted); letter-spacing:.07em; text-transform:uppercase; }
.sb-sep  { border:none; border-top:1px solid var(--border); margin:13px 0; }
.sb-sec  { font-size:0.63rem; font-weight:700; letter-spacing:.1em; text-transform:uppercase; color:var(--dim); margin:10px 0 5px; }
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ══════════════════════════════════════════════════════════════════════════════
CREDENTIALS = {"im_manager": "15062026"}
COLORS = ["#3B82F6","#10B981","#F59E0B","#EF4444","#8B5CF6","#14B8A6","#EC4899","#F97316"]
SECTOR_COLORS = {
    "WASH": "#3B82F6", "FSL": "#10B981",
    "Shelter & NFI": "#F59E0B", "Cash & Voucher Assistance": "#EF4444",
}
BG = "rgba(0,0,0,0)"; FONT_C = "#64748B"; GRID_C = "rgba(255,255,255,0.05)"

NAV = {
    "🏠  Overview":         "overview",
    "🗺️  Geographic Map":   "map",
    "💧  WASH":             "wash",
    "🌾  FSL Distribution": "fsl",
    "💵  CVA / Cash":       "cva",
    "📊  Indicators":       "ind",
    "🗂️  Raw Data":         "raw",
}

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
def ph(title, sub): st.markdown(f"<div class='ph'><h1>{title}</h1><p>{sub}</p></div>", unsafe_allow_html=True)
def pc(fig): st.plotly_chart(fig, use_container_width=True, config={"displayModeBar":False})

def T(fig, h=340, leg=True):
    fig.update_layout(
        height=h, paper_bgcolor=BG, plot_bgcolor=BG,
        font=dict(family="Outfit", color=FONT_C, size=11),
        margin=dict(l=12,r=12,t=36,b=12), showlegend=leg,
        legend=dict(bgcolor=BG, font=dict(color="#94A3B8",size=10),
                    borderwidth=0, orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        colorway=COLORS,
        title_font=dict(size=12, color="#CBD5E1", family="Outfit"),
    )
    fig.update_xaxes(showgrid=False, zeroline=False, color=FONT_C,
                     tickfont=dict(size=10,color=FONT_C), linecolor="rgba(255,255,255,0.05)")
    fig.update_yaxes(gridcolor=GRID_C, zeroline=False, color=FONT_C,
                     tickfont=dict(size=10,color=FONT_C), linewidth=0)
    return fig

# ══════════════════════════════════════════════════════════════════════════════
# DATA
# ══════════════════════════════════════════════════════════════════════════════
@st.cache_data(show_spinner="Loading data…")
def load_data(file):
    xls = pd.ExcelFile(file, engine="openpyxl")
    out = {}
    for name in xls.sheet_names:
        try: out[name] = pd.read_excel(xls, sheet_name=name)
        except Exception: pass
    return out

# ══════════════════════════════════════════════════════════════════════════════
# LOGIN
# ══════════════════════════════════════════════════════════════════════════════
def login_page():
    c1, c2, c3 = st.columns([1,1.2,1])
    with c2:
        st.markdown("""<div class='login-card'>
          <div class='login-badge'>🌍 Restricted Access</div>
          <div class='login-title'>SI Sudan IM</div>
          <div class='login-sub'>Information Management Dashboard<br>Solidarites International · Sudan Mission 2025–2026</div>
        </div>""", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        user = st.text_input("Username", placeholder="im_manager", label_visibility="collapsed")
        pw   = st.text_input("Password", type="password", placeholder="Password", label_visibility="collapsed")
        if st.button("Sign in →", use_container_width=True):
            if CREDENTIALS.get(user) == pw:
                st.session_state.update(auth=True, user=user); st.rerun()
            else: st.error("Invalid credentials.")
        st.markdown("<div style='text-align:center;font-size:.7rem;color:#334155;margin-top:1.2rem;'>Confidential · SI © 2026</div>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════
def sidebar():
    with st.sidebar:
        st.markdown("<div class='sb-logo'>🌍 SI Sudan</div><div class='sb-sub'>Information Management</div><hr class='sb-sep'>", unsafe_allow_html=True)
        up = st.file_uploader("Load Excel database", type=["xlsx"], label_visibility="collapsed")
        if up:
            data = load_data(up)
            st.session_state["dfs"] = data
            st.success(f"✅ {len(data)} sheets loaded")
        st.markdown("<hr class='sb-sep'><div class='sb-sec'>Navigation</div>", unsafe_allow_html=True)
        page = st.radio(" ", list(NAV.keys()), label_visibility="collapsed")
        st.markdown("<hr class='sb-sep'>", unsafe_allow_html=True)
        st.markdown(f"<div style='font-size:.7rem;color:#334155;line-height:1.9;'>👤 <span style='color:#64748B;'>{st.session_state.get('user','—')}</span><br>🕐 <span style='color:#64748B;'>{datetime.now().strftime('%d %b %Y %H:%M')}</span></div><br>", unsafe_allow_html=True)
        if st.button("Logout", use_container_width=True):
            st.session_state.clear(); st.rerun()
    return NAV[page], st.session_state.get("dfs", {})

# ══════════════════════════════════════════════════════════════════════════════
# MAP
# ══════════════════════════════════════════════════════════════════════════════
def make_map(df):
    m = folium.Map(location=[14.5,29.5], zoom_start=5, tiles="CartoDB dark_matter", attr="CartoDB")
    if not (has(df,"GPS_Latitude") and has(df,"GPS_Longitude")): return m
    dfm = df.copy()
    dfm["GPS_Latitude"]  = pd.to_numeric(dfm["GPS_Latitude"],  errors="coerce")
    dfm["GPS_Longitude"] = pd.to_numeric(dfm["GPS_Longitude"], errors="coerce")
    dfm = dfm.dropna(subset=["GPS_Latitude","GPS_Longitude"])
    dfm = dfm[dfm["GPS_Latitude"].between(8,24) & dfm["GPS_Longitude"].between(20,40)]
    if dfm.empty: return m
    # Heatmap
    HeatMap(dfm[["GPS_Latitude","GPS_Longitude"]].values.tolist(), radius=12, blur=15, min_opacity=0.25).add_to(m)
    # Clustered markers
    cl = MarkerCluster(options={"maxClusterRadius":40,"showCoverageOnHover":False}).add_to(m)
    for _, row in dfm.iterrows():
        sector = str(row.get("Sector","")) if has(df,"Sector") else ""
        color  = SECTOR_COLORS.get(sector,"#64748B")
        pop = f"""<div style='font-family:Outfit,sans-serif;font-size:12px;min-width:160px;'>
          <b>{row.get('Beneficiary_ID','—')}</b><br>
          <span style='color:#64748b;'>State:</span> {row.get('State','—')}<br>
          <span style='color:#64748b;'>Sector:</span> <b style='color:{color};'>{sector}</b><br>
          <span style='color:#64748b;'>Displacement:</span> {row.get('Displacement_Status','—')}<br>
          <span style='color:#64748b;'>Vulnerability:</span> {row.get('Vulnerability_Level','—')}
        </div>"""
        folium.CircleMarker(
            location=[row["GPS_Latitude"], row["GPS_Longitude"]],
            radius=6, color=color, fill=True, fill_color=color, fill_opacity=0.8, weight=1,
            popup=folium.Popup(pop, max_width=220),
            tooltip=f"{row.get('Locality','—')} · {sector}"
        ).add_to(cl)
    # Legend
    leg = "<div style='position:fixed;bottom:28px;right:16px;z-index:9999;background:rgba(13,23,48,0.95);border:1px solid rgba(99,140,210,0.2);border-radius:10px;padding:12px 16px;font-family:Outfit,sans-serif;'><div style='font-weight:700;font-size:11px;color:#e2e8f0;margin-bottom:8px;letter-spacing:.07em;text-transform:uppercase;'>Sectors</div>"
    for s, c in SECTOR_COLORS.items():
        leg += f"<div style='display:flex;align-items:center;gap:7px;margin-bottom:4px;'><span style='width:9px;height:9px;border-radius:50%;background:{c};display:inline-block;'></span><span style='font-size:11px;color:#94a3b8;'>{s}</span></div>"
    leg += "</div>"
    m.get_root().html.add_child(folium.Element(leg))
    return m

def page_map(dfs):
    ph("Geographic Coverage", "Interactive map — beneficiary locations with clustering & heatmap overlay")
    df = dfs.get("Beneficiary_Registration", pd.DataFrame())
    if df.empty: st.info("Load the Excel database to view the map."); return

    c1,c2,c3,c4 = st.columns(4)
    with c1: s1 = st.selectbox("State",        sopts(df,"State"),               key="m_s")
    with c2: s2 = st.selectbox("Sector",       sopts(df,"Sector"),              key="m_sec")
    with c3: s3 = st.selectbox("Displacement", sopts(df,"Displacement_Status"), key="m_d")
    with c4: s4 = st.selectbox("Vulnerability",sopts(df,"Vulnerability_Level"), key="m_v")

    df_f = sfilt(sfilt(sfilt(sfilt(df.copy(),"State",s1),"Sector",s2),"Displacement_Status",s3),"Vulnerability_Level",s4)
    nb  = len(df_f)
    fem = slen(df_f,"Sex","Female")

    c1,c2,c3,c4,c5 = st.columns(5)
    c1.markdown(kpi("Shown",     N(nb),                 "beneficiaries","blue",  "📍"), unsafe_allow_html=True)
    c2.markdown(kpi("States",    N(suniq(df_f,"State")),"","teal",  "🗺️"), unsafe_allow_html=True)
    c3.markdown(kpi("Localities",N(suniq(df_f,"Locality")),"","amber","📌"), unsafe_allow_html=True)
    c4.markdown(kpi("Female",    f"{100*fem/nb:.0f}%" if nb else "—","","purple","♀"), unsafe_allow_html=True)
    c5.markdown(kpi("Active",    N(slen(df_f,"Registration_Status","Active")),"","green","✅"), unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    col_map, col_r = st.columns([3,1])
    with col_map:
        st_folium(make_map(df_f), use_container_width=True, height=520, returned_objects=[])
    with col_r:
        if has(df_f,"State") and nb > 0:
            by_s = df_f.groupby("State").size().reset_index(name="n").sort_values("n")
            fig = px.bar(by_s, x="n", y="State", orientation="h",
                         color="n", color_continuous_scale=["#1E3A6E","#60A5FA"], title="By State")
            fig.update_layout(coloraxis_showscale=False)
            pc(T(fig, h=240, leg=False))
        if has(df_f,"Sector") and nb > 0:
            by_sec = df_f.groupby("Sector").size().reset_index(name="n")
            fig = px.pie(by_sec, values="n", names="Sector", hole=0.55,
                         color="Sector", color_discrete_map=SECTOR_COLORS, title="By Sector")
            fig.update_traces(textinfo="none", marker=dict(line=dict(color="#060D1F",width=2)))
            pc(T(fig, h=260))

# ══════════════════════════════════════════════════════════════════════════════
# OVERVIEW
# ══════════════════════════════════════════════════════════════════════════════
def page_overview(dfs):
    ph("Program Overview", "Consolidated key metrics — all sectors · Sudan Mission 2025–2026")
    df_b = dfs.get("Beneficiary_Registration", pd.DataFrame())
    df_w = dfs.get("WASH_Monitoring",           pd.DataFrame())
    df_f = dfs.get("FSL_Distribution",          pd.DataFrame())
    df_c = dfs.get("CVA_Cash_Transfers",        pd.DataFrame())
    df_i = dfs.get("Indicator_Tracker",         pd.DataFrame())

    tot   = len(df_b)
    act   = slen(df_b,"Registration_Status","Active")
    wr    = int(ssum(df_w,"Reached_Beneficiaries"))
    fhh   = int(ssum(df_f,"HH_Reached"))
    paid  = sfilt(df_c,"Transfer_Status","Paid")
    usd   = paid["Transfer_Value_USD"].sum() if has(paid,"Transfer_Value_USD") and len(paid)>0 else 0
    on_t  = slen(df_i,"Status","On track")
    ti    = len(df_i)

    sh("Programme Scale")
    c1,c2,c3,c4,c5,c6 = st.columns(6)
    c1.markdown(kpi("Beneficiaries",N(tot),  f"{act:,} active",   "blue",  "👤", f"↑ {act/tot:.0%} active" if tot else None,"up"), unsafe_allow_html=True)
    c2.markdown(kpi("WASH Reached", N(wr),   "cumulative",        "teal",  "💧"), unsafe_allow_html=True)
    c3.markdown(kpi("FSL HH",       N(fhh),  "households reached","green", "🌾"), unsafe_allow_html=True)
    c4.markdown(kpi("Cash Paid",    f"${N(usd)}","USD disbursed", "amber", "💵"), unsafe_allow_html=True)
    c5.markdown(kpi("States",       str(suniq(df_b,"State")),"covered","purple","🗺️"), unsafe_allow_html=True)
    c6.markdown(kpi("On Track",     f"{on_t}/{ti}","indicators",  "green", "📊", f"↑ {on_t/ti:.0%}" if ti else None,"up"), unsafe_allow_html=True)

    # Alerts
    alerts = []
    pb = slen(df_f,"Pipeline_Status","Pipeline break")
    if pb: alerts.append(f"⚠️  <b>{pb}</b> pipeline breaks detected in FSL supply chain")
    fa = slen(df_c,"Transfer_Status","Failed")
    if fa: alerts.append(f"❌  <b>{fa}</b> failed cash transfers require investigation")
    ot = slen(df_i,"Status","Off track")
    if ot: alerts.append(f"🔴  <b>{ot}</b> program indicators are off track")
    if alerts:
        sh("Active Alerts")
        for a in alerts:
            st.markdown(f"<div class='alert-banner'><span>{a}</span></div>", unsafe_allow_html=True)

    sh("Beneficiary Profile")
    c1,c2,c3 = st.columns([1.1,1,1])
    with c1:
        if not df_b.empty and has(df_b,"Sector"):
            d = df_b.groupby("Sector").size().reset_index(name="n")
            fig = px.pie(d, values="n", names="Sector", hole=0.58,
                         color="Sector", color_discrete_map=SECTOR_COLORS, title="Beneficiaries by Sector")
            fig.update_traces(textinfo="percent", textfont_size=10,
                              marker=dict(line=dict(color="#060D1F",width=2)))
            pc(T(fig, h=300))
    with c2:
        if not df_b.empty and has(df_b,"Displacement_Status"):
            d = df_b["Displacement_Status"].value_counts().reset_index()
            d.columns = ["Status","Count"]
            fig = px.bar(d, x="Count", y="Status", orientation="h",
                         color="Count", color_continuous_scale=["#1E3A6E","#3B82F6"],
                         title="Displacement Status")
            fig.update_layout(coloraxis_showscale=False)
            pc(T(fig, h=300, leg=False))
    with c3:
        if not df_b.empty and has(df_b,"Sex") and has(df_b,"Vulnerability_Level"):
            ct = df_b.groupby(["Vulnerability_Level","Sex"]).size().reset_index(name="n")
            fig = px.bar(ct, x="Vulnerability_Level", y="n", color="Sex", barmode="stack",
                         color_discrete_map={"Female":"#EC4899","Male":"#3B82F6"},
                         title="Vulnerability × Sex")
            pc(T(fig, h=300))

    sh("Registration Trend")
    if not df_b.empty and has(df_b,"Registration_Date"):
        df_t = df_b.copy()
        df_t["Registration_Date"] = pd.to_datetime(df_t["Registration_Date"], errors="coerce")
        df_t = df_t.dropna(subset=["Registration_Date"])
        df_t["Month"] = df_t["Registration_Date"].dt.to_period("M").astype(str)
        if has(df_t,"Sector"):
            trend = df_t.groupby(["Month","Sector"]).size().reset_index(name="Count")
            fig = px.area(trend, x="Month", y="Count", color="Sector",
                          color_discrete_map=SECTOR_COLORS, title="Monthly Registrations by Sector")
            fig.update_traces(line_width=2)
            pc(T(fig, h=290))

    if not df_b.empty and has(df_b,"State") and has(df_b,"Sector"):
        sh("Coverage Heatmap — State × Sector")
        heat = df_b.groupby(["State","Sector"]).size().reset_index(name="Count")
        fig = px.density_heatmap(heat, x="Sector", y="State", z="Count",
                                 color_continuous_scale="Blues", title="Beneficiaries by State × Sector")
        fig.update_layout(coloraxis_colorbar=dict(tickfont=dict(color=FONT_C)))
        pc(T(fig, h=280, leg=False))

# ══════════════════════════════════════════════════════════════════════════════
# WASH
# ══════════════════════════════════════════════════════════════════════════════
def page_wash(dfs):
    ph("WASH Monitoring", "Water, Sanitation & Hygiene — activity performance and gender disaggregation")
    df = dfs.get("WASH_Monitoring", pd.DataFrame())
    if df.empty: st.info("No WASH_Monitoring sheet found."); return

    c1,c2 = st.columns(2)
    with c1: s1 = st.selectbox("State",         sopts(df,"State"),        key="w_s")
    with c2: s2 = st.selectbox("Activity Type", sopts(df,"Activity_Type"),key="w_a")
    df_f = sfilt(sfilt(df.copy(),"State",s1),"Activity_Type",s2)

    reached = int(ssum(df_f,"Reached_Beneficiaries"))
    target  = int(ssum(df_f,"Target_Beneficiaries")) or 1
    pct     = reached/target
    wv      = int(ssum(df_f,"Water_Volume_Liters"))
    lat     = int(ssum(df_f,"Latrine_Units_Built"))
    hyg     = int(ssum(df_f,"Hygiene_Kits_Dist"))
    nfi     = int(ssum(df_f,"NFI_Kits_Dist"))

    sh("Key Indicators")
    c1,c2,c3,c4,c5 = st.columns(5)
    dd = "up" if pct>=0.8 else "mid" if pct>=0.6 else "down"
    c1.markdown(kpi("Reached",  N(reached),f"of {N(target)} target","blue",  "💧",f"{pct:.0%} coverage",dd), unsafe_allow_html=True)
    c2.markdown(kpi("Water",    N(wv)+" L","litres",             "teal",  "🚰"), unsafe_allow_html=True)
    c3.markdown(kpi("Latrines", N(lat),    "units built",         "green", "🏗️"), unsafe_allow_html=True)
    c4.markdown(kpi("Hyg Kits", N(hyg),    "distributed",         "amber", "🧴"), unsafe_allow_html=True)
    c5.markdown(kpi("NFI Kits", N(nfi),    "distributed",         "purple","📦"), unsafe_allow_html=True)

    sh("Activity Performance")
    c1,c2 = st.columns(2)
    with c1:
        if has(df_f,"Activity_Type"):
            grp = df_f.groupby("Activity_Type")[["Target_Beneficiaries","Reached_Beneficiaries"]].sum().reset_index()
            fig = go.Figure()
            fig.add_bar(name="Target", x=grp["Activity_Type"], y=grp["Target_Beneficiaries"],
                        marker_color="rgba(59,130,246,0.2)", marker_line_color="#3B82F6", marker_line_width=1)
            fig.add_bar(name="Reached",x=grp["Activity_Type"], y=grp["Reached_Beneficiaries"],
                        marker_color="#3B82F6")
            fig.update_layout(barmode="group", title="Target vs Reached")
            pc(T(fig, h=330))
    with c2:
        if has(df_f,"Functionality_Status"):
            func = df_f["Functionality_Status"].value_counts().reset_index()
            func.columns = ["Status","Count"]
            cmap = {"Fully Functional":"#10B981","Partially Functional":"#F59E0B",
                    "Non-Functional":"#EF4444","Under Construction":"#8B5CF6"}
            fig = px.pie(func, values="Count", names="Status", hole=0.55,
                         color="Status", color_discrete_map=cmap, title="Infrastructure Functionality")
            fig.update_traces(textinfo="percent+label", textfont_size=9,
                              marker=dict(line=dict(color="#060D1F",width=2)))
            pc(T(fig, h=330))

    sh("Gender Disaggregation")
    if has(df_f,"Reached_Female") and has(df_f,"Reached_Male"):
        c1,c2,c3 = st.columns(3)
        tf = df_f["Reached_Female"].sum(); tm = df_f["Reached_Male"].sum()
        with c1:
            fig = go.Figure(go.Bar(x=["Female","Male"], y=[tf,tm],
                                   marker_color=["#EC4899","#3B82F6"],
                                   text=[N(tf),N(tm)], textposition="outside",
                                   textfont=dict(color="#fff",size=11)))
            fig.update_layout(title="Sex Disaggregation")
            pc(T(fig, h=280, leg=False))
        with c2:
            if has(df_f,"State"):
                sg = df_f.groupby("State")[["Reached_Female","Reached_Male"]].sum().reset_index()
                fig = px.bar(sg, x="State", y=["Reached_Female","Reached_Male"], barmode="stack",
                             color_discrete_map={"Reached_Female":"#EC4899","Reached_Male":"#3B82F6"},
                             title="Sex by State")
                pc(T(fig, h=280))
        with c3:
            if has(df_f,"Reached_Children_U5"):
                tc5 = df_f["Reached_Children_U5"].sum()
                fig = go.Figure(go.Pie(labels=["Children U5","Adults"],
                                       values=[tc5, max(0,(tf+tm)-tc5)], hole=0.55,
                                       marker=dict(colors=["#F59E0B","#3B82F6"],
                                                   line=dict(color="#060D1F",width=2))))
                fig.update_layout(title="Children U5 vs Adults")
                pc(T(fig, h=280))

    sh("Reporting Compliance")
    if has(df_f,"Cluster_Reporting"):
        c1,c2 = st.columns(2)
        with c1:
            cr = df_f["Cluster_Reporting"].value_counts().reset_index(); cr.columns = ["Status","Count"]
            fig = px.pie(cr, values="Count", names="Status", hole=0.55,
                         color="Status",
                         color_discrete_map={"Reported":"#10B981","Not reported":"#EF4444"},
                         title="Cluster Reporting Compliance")
            fig.update_traces(marker=dict(line=dict(color="#060D1F",width=2)), textinfo="percent")
            pc(T(fig, h=270))
        with c2:
            if has(df_f,"State"):
                grp2 = df_f.groupby(["State","Cluster_Reporting"]).size().reset_index(name="n")
                fig = px.bar(grp2, x="State", y="n", color="Cluster_Reporting",
                             color_discrete_map={"Reported":"#10B981","Not reported":"#EF4444"},
                             title="Reporting Status by State")
                pc(T(fig, h=270))

# ══════════════════════════════════════════════════════════════════════════════
# FSL
# ══════════════════════════════════════════════════════════════════════════════
def page_fsl(dfs):
    ph("Food Security & Livelihoods", "Distribution tracking — commodities, pipeline status, donor coverage")
    df = dfs.get("FSL_Distribution", pd.DataFrame())
    if df.empty: st.info("No FSL_Distribution sheet found."); return

    c1,c2,c3 = st.columns(3)
    with c1: s1 = st.selectbox("State",     sopts(df,"State"),         key="f_s")
    with c2: s2 = st.selectbox("Commodity", sopts(df,"Commodity_Type"),key="f_c")
    with c3: s3 = st.selectbox("Donor",     sopts(df,"Donor"),         key="f_d")
    df_f = sfilt(sfilt(sfilt(df.copy(),"State",s1),"Commodity_Type",s2),"Donor",s3)

    hht = int(ssum(df_f,"HH_Targeted")); hhr = int(ssum(df_f,"HH_Reached"))
    qp  = ssum(df_f,"Quantity_Planned"); qd  = ssum(df_f,"Quantity_Distributed")
    fem = int(ssum(df_f,"Female_HHH_Reached"))
    pb  = slen(df_f,"Pipeline_Status","Pipeline break")
    cov = hhr/hht if hht else 0

    sh("Key Indicators")
    c1,c2,c3,c4,c5 = st.columns(5)
    dd = "up" if cov>=0.8 else "mid" if cov>=0.6 else "down"
    c1.markdown(kpi("HH Reached",   N(hhr),f"of {N(hht)} targeted","green","🏠",f"{cov:.0%} coverage",dd), unsafe_allow_html=True)
    c2.markdown(kpi("Qty Dist.",    N(qd), f"of {N(qp)} planned",  "blue", "📦"), unsafe_allow_html=True)
    c3.markdown(kpi("Female HHH",   N(fem),f"{fem/hhr:.0%} of reached" if hhr else "—","purple","♀"), unsafe_allow_html=True)
    c4.markdown(kpi("Pipeline ⚠️",  str(pb),"supply breaks",       "red" if pb else "green","⚠️"), unsafe_allow_html=True)
    c5.markdown(kpi("Records",      N(len(df_f)),"in selection",   "teal","📋"), unsafe_allow_html=True)

    sh("Distribution Analysis")
    c1,c2,c3 = st.columns(3)
    with c1:
        if has(df_f,"Commodity_Type"):
            comm = df_f.groupby("Commodity_Type")["HH_Reached"].sum().reset_index()
            comm = comm.sort_values("HH_Reached",ascending=True).tail(10)
            comm.columns = ["Commodity","HH_Reached"]
            fig = px.bar(comm, x="HH_Reached", y="Commodity", orientation="h",
                         color="HH_Reached", color_continuous_scale=["#14532D","#34D399"],
                         title="HH Reached by Commodity")
            fig.update_layout(coloraxis_showscale=False)
            pc(T(fig, h=350, leg=False))
    with c2:
        if has(df_f,"Pipeline_Status"):
            pipe = df_f["Pipeline_Status"].value_counts().reset_index(); pipe.columns = ["Status","Count"]
            cmap = {"In stock":"#10B981","Low stock":"#F59E0B","Pipeline break":"#EF4444","Awaiting delivery":"#8B5CF6"}
            fig = px.pie(pipe, values="Count", names="Status", hole=0.55,
                         color="Status", color_discrete_map=cmap, title="Pipeline Status")
            fig.update_traces(marker=dict(line=dict(color="#060D1F",width=2)), textinfo="percent")
            pc(T(fig, h=350))
    with c3:
        if has(df_f,"Donor"):
            don = df_f.groupby("Donor")["HH_Reached"].sum().reset_index()
            fig = px.bar(don, x="Donor", y="HH_Reached", color="Donor",
                         color_discrete_sequence=COLORS, title="HH Reached by Donor",
                         text="HH_Reached")
            fig.update_traces(texttemplate="%{text:,.0f}", textposition="outside",
                              textfont=dict(color="#fff",size=9))
            fig.update_layout(showlegend=False)
            pc(T(fig, h=350, leg=False))

    sh("Distribution Timeline")
    if has(df_f,"Distribution_Date"):
        df_t = df_f.copy()
        df_t["Distribution_Date"] = pd.to_datetime(df_t["Distribution_Date"], errors="coerce")
        df_t = df_t.dropna(subset=["Distribution_Date"])
        df_t["Month"] = df_t["Distribution_Date"].dt.to_period("M").astype(str)
        if has(df_t,"Donor"):
            monthly = df_t.groupby(["Month","Donor"])["HH_Reached"].sum().reset_index()
            fig = px.area(monthly, x="Month", y="HH_Reached", color="Donor",
                          title="Monthly HH Reached by Donor", color_discrete_sequence=COLORS)
            fig.update_traces(line_width=1.5)
            pc(T(fig, h=270))

    sh("Post-Distribution Monitoring")
    c1,c2 = st.columns(2)
    with c1:
        if has(df_f,"Beneficiary_Satisfaction"):
            sat = df_f["Beneficiary_Satisfaction"].value_counts().reset_index(); sat.columns = ["Level","Count"]
            cmap = {"Above 80%":"#10B981","60–80%":"#F59E0B","Below 60%":"#EF4444","N/A":"#475569"}
            fig = px.bar(sat, x="Level", y="Count", color="Level",
                         color_discrete_map=cmap, title="Beneficiary Satisfaction", text="Count")
            fig.update_traces(textposition="outside", textfont=dict(color="#fff"))
            fig.update_layout(showlegend=False)
            pc(T(fig, h=270))
    with c2:
        if has(df_f,"Post_Dist_Monitor"):
            pdm = df_f["Post_Dist_Monitor"].value_counts().reset_index(); pdm.columns = ["Status","Count"]
            fig = px.pie(pdm, values="Count", names="Status", hole=0.5,
                         title="PDM Completion Status", color_discrete_sequence=COLORS)
            fig.update_traces(marker=dict(line=dict(color="#060D1F",width=2)), textinfo="percent")
            pc(T(fig, h=270))

# ══════════════════════════════════════════════════════════════════════════════
# CVA
# ══════════════════════════════════════════════════════════════════════════════
def page_cva(dfs):
    ph("Cash & Voucher Assistance", "Transfer tracking — payment status, modalities, and beneficiary profile")
    df = dfs.get("CVA_Cash_Transfers", pd.DataFrame())
    if df.empty: st.info("No CVA_Cash_Transfers sheet found."); return

    c1,c2,c3 = st.columns(3)
    with c1: s1 = st.selectbox("State",         sopts(df,"State"),        key="c_s")
    with c2: s2 = st.selectbox("Transfer Type", sopts(df,"Transfer_Type"),key="c_t")
    with c3: s3 = st.selectbox("Round",         sopts(df,"Round"),        key="c_r")
    df_f = sfilt(sfilt(sfilt(df.copy(),"State",s1),"Transfer_Type",s2),"Round",s3)

    paid_df = sfilt(df_f,"Transfer_Status","Paid")
    pend_df = sfilt(df_f,"Transfer_Status","Pending")
    fail_df = sfilt(df_f,"Transfer_Status","Failed")
    usd     = paid_df["Transfer_Value_USD"].sum() if has(paid_df,"Transfer_Value_USD") and len(paid_df)>0 else 0
    avg_v   = paid_df["Transfer_Value_USD"].mean() if has(paid_df,"Transfer_Value_USD") and len(paid_df)>0 else 0
    fem_pct = slen(df_f,"Female_Headed_HH","Yes")/len(df_f) if len(df_f)>0 and has(df_f,"Female_Headed_HH") else 0

    sh("Key Indicators")
    c1,c2,c3,c4,c5,c6 = st.columns(6)
    c1.markdown(kpi("Total Paid",  f"${N(usd)}","USD",        "blue",  "💵"), unsafe_allow_html=True)
    c2.markdown(kpi("Paid",        N(len(paid_df)),"completed","green", "✅"), unsafe_allow_html=True)
    c3.markdown(kpi("Pending",     N(len(pend_df)),"awaiting", "amber", "⏳"), unsafe_allow_html=True)
    c4.markdown(kpi("Failed",      N(len(fail_df)),"check",    "red" if len(fail_df) else "green","❌"), unsafe_allow_html=True)
    c5.markdown(kpi("Avg Transfer",f"${avg_v:.0f}","per HH",  "teal",  "📊"), unsafe_allow_html=True)
    c6.markdown(kpi("Female HHH",  f"{fem_pct:.0%}","",        "purple","♀"), unsafe_allow_html=True)

    if len(fail_df)>0:
        st.markdown(f"<div class='alert-banner'><span>❌ <b>{len(fail_df)}</b> failed transfers detected — require verification before next payment round.</span></div>", unsafe_allow_html=True)

    sh("Transfer Analysis")
    c1,c2 = st.columns(2)
    with c1:
        if has(df_f,"Transfer_Status"):
            sc = df_f["Transfer_Status"].value_counts().reset_index(); sc.columns = ["Status","Count"]
            cmap = {"Paid":"#10B981","Pending":"#F59E0B","Failed":"#EF4444","Cancelled":"#8B5CF6"}
            fig = px.pie(sc, values="Count", names="Status", hole=0.58,
                         color="Status", color_discrete_map=cmap, title="Transfer Status")
            fig.update_traces(marker=dict(line=dict(color="#060D1F",width=2)), textinfo="percent")
            pc(T(fig, h=310))
    with c2:
        if has(df_f,"Payment_Method") and has(df_f,"Transfer_Value_USD"):
            pm = df_f.groupby("Payment_Method")["Transfer_Value_USD"].sum().reset_index()
            pm = pm.sort_values("Transfer_Value_USD", ascending=True)
            fig = px.bar(pm, x="Transfer_Value_USD", y="Payment_Method", orientation="h",
                         color="Transfer_Value_USD", color_continuous_scale=["#1E3A6E","#60A5FA"],
                         title="USD by Payment Method", text="Transfer_Value_USD")
            fig.update_traces(texttemplate="$%{text:,.0f}", textposition="outside",
                              textfont=dict(color="#fff",size=9))
            fig.update_layout(coloraxis_showscale=False)
            pc(T(fig, h=310, leg=False))

    sh("Transfer Timeline")
    if has(df_f,"Transfer_Date") and has(df_f,"Transfer_Value_USD"):
        df_t = df_f.copy()
        df_t["Transfer_Date"] = pd.to_datetime(df_t["Transfer_Date"], errors="coerce")
        df_t = df_t.dropna(subset=["Transfer_Date"])
        df_t["Month"] = df_t["Transfer_Date"].dt.to_period("M").astype(str)
        if has(df_t,"Transfer_Status"):
            agg = df_t.groupby(["Month","Transfer_Status"])["Transfer_Value_USD"].sum().reset_index()
            cmap = {"Paid":"#10B981","Pending":"#F59E0B","Failed":"#EF4444","Cancelled":"#8B5CF6"}
            fig = px.bar(agg, x="Month", y="Transfer_Value_USD", color="Transfer_Status",
                         color_discrete_map=cmap, title="Monthly Transfer Volume (USD) by Status")
            pc(T(fig, h=270))

    sh("Beneficiary Profile")
    c1,c2 = st.columns(2)
    with c1:
        if has(df_f,"Transfer_Type") and has(df_f,"Transfer_Value_USD"):
            tt = df_f.groupby("Transfer_Type")["Transfer_Value_USD"].sum().reset_index()
            tt.columns = ["Type","Total"]
            fig = px.bar(tt, x="Type", y="Total", color="Type",
                         color_discrete_sequence=COLORS, title="USD by Transfer Type", text="Total")
            fig.update_traces(texttemplate="%{text:,.0f}", textposition="outside",
                              textfont=dict(color="#fff",size=9))
            fig.update_layout(showlegend=False)
            pc(T(fig, h=270))
    with c2:
        if has(df_f,"State") and has(df_f,"Transfer_Value_USD"):
            st_g = df_f.groupby("State")["Transfer_Value_USD"].sum().reset_index()
            fig = px.pie(st_g, values="Transfer_Value_USD", names="State", hole=0.5,
                         title="Transfer Value by State", color_discrete_sequence=COLORS)
            fig.update_traces(marker=dict(line=dict(color="#060D1F",width=2)), textinfo="percent")
            pc(T(fig, h=270))

# ══════════════════════════════════════════════════════════════════════════════
# INDICATORS
# ══════════════════════════════════════════════════════════════════════════════
def page_ind(dfs):
    ph("Indicator Tracker", "Results-based management — progress vs annual targets by sector")
    df = dfs.get("Indicator_Tracker", pd.DataFrame())
    if df.empty: st.info("No Indicator_Tracker sheet found."); return

    on_t = slen(df,"Status","On track")
    at_r = slen(df,"Status","At risk")
    off  = slen(df,"Status","Off track")
    tot  = len(df)

    c1,c2,c3,c4 = st.columns(4)
    c1.markdown(kpi("Total",     str(tot),  "indicators",        "blue",  "📋"), unsafe_allow_html=True)
    c2.markdown(kpi("On Track",  str(on_t), f"{on_t/tot:.0%}",   "green", "✅", f"↑ {on_t/tot:.0%}","up"), unsafe_allow_html=True)
    c3.markdown(kpi("At Risk",   str(at_r), f"{at_r/tot:.0%}",   "amber", "⚠️"), unsafe_allow_html=True)
    c4.markdown(kpi("Off Track", str(off),  f"{off/tot:.0%}",    "red",   "❌"), unsafe_allow_html=True)

    sh("Performance Overview")
    c1,c2 = st.columns([1,2])
    with c1:
        fig = go.Figure(go.Pie(
            labels=["On Track","At Risk","Off Track"], values=[on_t,at_r,off], hole=0.62,
            marker=dict(colors=["#10B981","#F59E0B","#EF4444"],
                        line=dict(color="#060D1F",width=3)), textinfo="none"
        ))
        fig.add_annotation(text=f"<b>{tot}</b><br><span style='font-size:9px'>Total</span>",
                           x=0.5, y=0.5, font_size=18, showarrow=False, font_color="#fff")
        fig.update_layout(title="Overall Status")
        pc(T(fig, h=280))
    with c2:
        if has(df,"Sector") and has(df,"Status"):
            perf = df.groupby(["Sector","Status"]).size().reset_index(name="Count")
            cmap = {"On track":"#10B981","At risk":"#F59E0B","Off track":"#EF4444"}
            fig = px.bar(perf, x="Sector", y="Count", color="Status",
                         color_discrete_map=cmap, barmode="stack", title="Indicator Status by Sector")
            pc(T(fig, h=280))

    if has(df,"Sector"):
        for sec in sorted(df["Sector"].dropna().unique()):
            df_sec = df[df["Sector"]==sec]
            sh(f"Sector — {sec}")
            for _, row in df_sec.iterrows():
                ind_name = str(row.get("Indicator",""))
                unit     = str(row.get("Unit",""))
                target   = row.get("Annual Target", None)
                cumul    = row.get("Cumulative", None)
                q1 = float(row.get("Q1 Achieved",0) or 0)
                q2 = float(row.get("Q2 Achieved",0) or 0)
                q3 = float(row.get("Q3 Achieved",0) or 0)
                q4 = float(row.get("Q4 (Partial)",0) or 0)
                status = str(row.get("Status",""))

                has_target = pd.notna(target) and str(target) not in ["","nan","None"]
                if has_target:
                    try:
                        t = float(str(target).replace(",","").replace("%",""))
                        cv = float(str(cumul).replace(",","").replace("%","")) if pd.notna(cumul) else 0
                        pct = min(cv/t,1.0) if t > 0 else 0
                    except: t,cv,pct = 0,0,0
                    bc = "#10B981" if pct>=0.8 else "#F59E0B" if pct>=0.6 else "#EF4444"
                    st.markdown(f"""<div class='ind-card'>
                      <div style='display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:7px;'>
                        <div>
                          <div class='ind-name'>{ind_name}</div>
                          <div class='ind-vals'>Target: {N(t)} {unit} &nbsp;·&nbsp; Achieved: {N(cv)} &nbsp;·&nbsp; {pct*100:.1f}%</div>
                        </div>
                        <div>{bdg(status)}</div>
                      </div>
                      <div class='pbar-wrap'><div class='pbar' style='width:{pct*100:.1f}%;background:{bc};'></div></div>
                      <div style='display:flex;gap:16px;margin-top:5px;'>
                        <span class='ind-vals'>Q1: {N(q1)}</span><span class='ind-vals'>Q2: {N(q2)}</span>
                        <span class='ind-vals'>Q3: {N(q3)}</span><span class='ind-vals'>Q4: {N(q4)}</span>
                        <span class='ind-vals' style='margin-left:auto;color:#60A5FA;'>Cumul: {N(q1+q2+q3+q4)}</span>
                      </div>
                    </div>""", unsafe_allow_html=True)
                else:
                    st.markdown(f"""<div class='ind-card' style='display:flex;justify-content:space-between;align-items:center;'>
                      <div><div class='ind-name'>{ind_name}</div><div class='ind-vals'>Count indicator — no annual target</div></div>
                      <div style='display:flex;align-items:center;gap:10px;'>
                        <span style='font-size:1.1rem;font-weight:700;color:#fff;'>{N(cumul) if pd.notna(cumul) else "—"} <span style='font-size:.7rem;color:#64748B;'>{unit}</span></span>
                        {bdg(status)}
                      </div>
                    </div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# RAW DATA
# ══════════════════════════════════════════════════════════════════════════════
def page_raw(dfs):
    ph("Raw Data Explorer", "Browse, filter and export program datasets")
    sheet = st.selectbox("Select dataset", list(dfs.keys()))
    df = dfs[sheet]
    c1,c2 = st.columns([3,1])
    with c1: st.markdown(f"<div style='padding:.5rem 0;font-size:.8rem;color:#64748B;'>{len(df):,} rows · {len(df.columns)} columns</div>", unsafe_allow_html=True)
    with c2: st.download_button("⬇ Download CSV", df.to_csv(index=False).encode(), file_name=f"{sheet}.csv", mime="text/csv", use_container_width=True)
    num_cols = df.select_dtypes(include="number").columns.tolist()
    if num_cols:
        sh("Quick Statistics")
        st.dataframe(df[num_cols].describe().round(2), use_container_width=True)
    sh("Data Table")
    st.dataframe(df, use_container_width=True, height=500)

# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════
def main():
    if not st.session_state.get("auth"):
        login_page(); return
    page_key, dfs = sidebar()
    if not dfs:
        ph("Welcome","Load the database to get started")
        st.markdown("""<div style='text-align:center;padding:5rem 2rem;background:#131F35;border:1px dashed rgba(99,140,210,0.22);border-radius:14px;margin-top:2rem;'>
          <div style='font-size:2.5rem;margin-bottom:1rem;'>📂</div>
          <div style='font-size:1.1rem;font-weight:700;color:#fff;margin-bottom:.5rem;'>No database loaded</div>
          <div style='font-size:.85rem;color:#64748B;'>Upload <code>SI_Sudan_Program_Database.xlsx</code> using the sidebar.</div>
        </div>""", unsafe_allow_html=True)
        return
    dispatch = {
        "overview": page_overview, "map": page_map, "wash": page_wash,
        "fsl": page_fsl, "cva": page_cva, "ind": page_ind, "raw": page_raw,
    }
    dispatch.get(page_key, page_overview)(dfs)

if __name__ == "__main__":
    main()
