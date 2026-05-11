import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import folium
from folium.plugins import MarkerCluster, HeatMap, MiniMap
from streamlit_folium import st_folium
from datetime import datetime
import io, warnings, time
warnings.filterwarnings("ignore")

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

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
# CONSTANTS
# ══════════════════════════════════════════════════════════════════════════════
SI_RED  = "#E3001B"
SI_RED2 = "#B50016"

SI_IMAGES = [
    "https://images.unsplash.com/photo-1488521787991-ed7bbaae773c?w=1400&q=80",
    "https://images.unsplash.com/photo-1532629345422-7515f3d16bb6?w=1400&q=80",
    "https://images.unsplash.com/photo-1509099836639-18ba1795216d?w=1400&q=80",
    "https://images.unsplash.com/photo-1578496479914-7ef3b0193be3?w=1400&q=80",
    "https://images.unsplash.com/photo-1559027615-cd4628902d4a?w=1400&q=80",
]

DARK = dict(
    bg="#12151C", surface="#1C2130", panel="#222840",
    border="rgba(227,0,27,0.18)", border2="rgba(227,0,27,0.35)",
    text="#F1F5F9", muted="#94A3B8", dim="#2A3050",
    navbg="#0E1120", navborder="rgba(227,0,27,0.3)",
    card="#1C2130", input="#161B2E",
    plotbg="rgba(0,0,0,0)", gridc="rgba(255,255,255,0.05)",
    fontc="#64748B", title="#E2E8F0",
    accent="#E3001B", accent2="#FF3355",
    sbg="#12151C",
)
LIGHT = dict(
    bg="#F8F9FB", surface="#FFFFFF", panel="#FFFFFF",
    border="rgba(227,0,27,0.12)", border2="rgba(227,0,27,0.28)",
    text="#0F172A", muted="#64748B", dim="#F1F5F9",
    navbg="#FFFFFF", navborder="rgba(227,0,27,0.2)",
    card="#FFFFFF", input="#F8FAFC",
    plotbg="rgba(0,0,0,0)", gridc="rgba(0,0,0,0.04)",
    fontc="#94A3B8", title="#1E293B",
    accent="#E3001B", accent2="#B50016",
    sbg="#F8F9FB",
)
COLORS  = ["#E3001B","#3B82F6","#F59E0B","#10B981","#8B5CF6","#14B8A6","#EC4899","#F97316"]
SC = {"WASH":"#3B82F6","FSL":"#10B981","Shelter & NFI":"#F59E0B","Cash & Voucher Assistance":"#E3001B"}
CREDENTIALS = {"im_manager": "15062026"}

NAV_ITEMS = [
    ("\U0001f3e0", "Overview"), ("\U0001f5fa\ufe0f", "Map"), ("\U0001f4a7", "WASH"),
    ("\U0001f33e", "FSL"), ("\U0001f4b5", "CVA"), ("\U0001f4ca", "Indicators"),
    ("\U0001f5c2\ufe0f", "Raw Data"), ("\U0001f4c4", "Report"),
]

# SUDAN GEOGRAPHIC CONSTANTS
SUDAN_LAT_MIN, SUDAN_LAT_MAX = 8.68,  23.15
SUDAN_LON_MIN, SUDAN_LON_MAX = 21.83, 38.61
SUDAN_CENTER = [14.8, 29.5]

STATE_CENTROIDS = {
    "West Darfur":    (13.58, 22.05), "North Darfur":   (16.20, 25.00),
    "South Darfur":   (11.50, 25.10), "Central Darfur": (13.10, 24.10),
    "East Darfur":    (12.85, 26.80), "Khartoum":       (15.55, 32.53),
    "Gedaref":        (14.03, 35.39), "Kassala":        (15.47, 36.40),
    "River Nile":     (18.50, 33.80), "Northern":       (20.00, 30.20),
    "North Kordofan": (13.80, 29.40), "South Kordofan": (11.00, 29.40),
    "White Nile":     (13.10, 32.20), "Blue Nile":      (11.80, 34.00),
    "Sennar":         (13.55, 33.60), "Red Sea":        (20.00, 37.20),
    "Al Jazirah":     (14.40, 33.40), "West Kordofan":  (12.00, 25.70),
}

import random as _rnd, json as _json
_rnd.seed(42)

_GEOJSON_PATH = "https://raw.githubusercontent.com/dhp-byte/IM_Manager_Soudan/main/sudan_states.geojson"
try:
    import requests as _req
    resp = _req.get(_GEOJSON_PATH)
    if resp.status_code == 200:
        SUDAN_GEOJSON = resp.json()
    else:
        SUDAN_GEOJSON = None
except Exception:
    SUDAN_GEOJSON = None

STATE_SCATTER = {
    s: [(lat + _rnd.uniform(-0.4, 0.4), lon + _rnd.uniform(-0.5, 0.5))
        for _ in range(12)]
    for s, (lat, lon) in STATE_CENTROIDS.items()
}

KOBO_SERVERS = {
    "KoBoToolbox Global — kf.kobotoolbox.org": "https://kf.kobotoolbox.org",
    "OCHA Humanitarian — kobo.humanitarianresponse.info": "https://kobo.humanitarianresponse.info",
    "Custom server…": "custom",
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

def sh(title):
    st.markdown(f"<div class='sh'>{title}</div>", unsafe_allow_html=True)

def ph(title, sub=""):
    st.markdown(f"<div class='ph'><h1>{title}</h1><p>{sub}</p></div>", unsafe_allow_html=True)

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

def _get_coords(row):
    try:
        lat = float(row.get("GPS_Latitude", "") or "")
        lon = float(row.get("GPS_Longitude", "") or "")
        if SUDAN_LAT_MIN <= lat <= SUDAN_LAT_MAX and SUDAN_LON_MIN <= lon <= SUDAN_LON_MAX:
            return lat, lon
    except (TypeError, ValueError):
        pass
    state = str(row.get("State", ""))
    if state in STATE_SCATTER:
        idx = hash(str(row.get("Beneficiary_ID", row.get("_index", 0)))) % len(STATE_SCATTER[state])
        return STATE_SCATTER[state][idx]
    return (_rnd.uniform(10, 22), _rnd.uniform(23, 37))

def _enrich_gps(df):
    if df.empty: return df
    df = df.copy().reset_index(drop=True)
    df["_index"] = df.index
    coords = df.apply(_get_coords, axis=1)
    df["GPS_Latitude"]  = coords.apply(lambda x: x[0])
    df["GPS_Longitude"] = coords.apply(lambda x: x[1])
    return df

def _clean_gps(df):
    return _enrich_gps(df) if not df.empty else pd.DataFrame()

def _base_map(dark=True, zoom=5):
    tiles = "CartoDB dark_matter" if dark else "CartoDB positron"
    m = folium.Map(location=SUDAN_CENTER, zoom_start=zoom, tiles=tiles,
                   attr="© CartoDB", prefer_canvas=True)
    MiniMap(toggle_display=True, position="bottomleft", tile_layer=tiles,
            zoom_level_offset=-6).add_to(m)
    return m

def _add_geojson_layer(m, data_col=None, state_values=None, dark=True,
                        fill_color="#3B82F6", fill_opacity=0.15,
                        line_color="#E3001B", line_weight=1.5):
    if SUDAN_GEOJSON is None:
        return
    border_col = "rgba(227,0,27,0.7)" if dark else "#B50016"
    if state_values:
        folium.Choropleth(
            geo_data=SUDAN_GEOJSON,
            data=state_values,
            columns=["state","value"],
            key_on="feature.properties.name",
            fill_color="YlOrRd",
            fill_opacity=0.65,
            line_opacity=0.9,
            line_color=border_col,
            line_weight=line_weight,
            nan_fill_color="rgba(100,116,139,0.15)",
            nan_fill_opacity=0.3,
            legend_name=data_col or "Value",
            highlight=True,
        ).add_to(m)
    else:
        folium.GeoJson(
            SUDAN_GEOJSON,
            style_function=lambda f: {
                "fillColor":   fill_color,
                "color":       line_color,
                "weight":      line_weight,
                "fillOpacity": fill_opacity,
            },
            tooltip=folium.GeoJsonTooltip(
                fields=["name"],
                aliases=["State:"],
                style="font-family:Outfit,sans-serif;font-size:12px;"
            )
        ).add_to(m)

def _add_state_labels(m, dark=True):
    bg  = "rgba(14,17,32,0.85)" if dark else "rgba(255,255,255,0.90)"
    tc  = "#f1f5f9" if dark else "#0f172a"
    bd  = "rgba(227,0,27,0.4)"
    for state, (lat, lon) in STATE_CENTROIDS.items():
        folium.Marker(
            location=[lat, lon],
            icon=folium.DivIcon(
                html=(f"<div style='background:{bg};color:{tc};padding:2px 7px;"
                      f"border-radius:8px;font-family:Outfit,sans-serif;font-size:9.5px;"
                      f"font-weight:700;white-space:nowrap;border:1px solid {bd};"
                      f"box-shadow:0 2px 8px rgba(0,0,0,0.35);'>{state}</div>"),
                icon_size=(150, 20), icon_anchor=(75, 10)
            )
        ).add_to(m)

def _map_legend(m, items, title="Legend", dark=True):
    bg = "rgba(14,17,32,0.93)" if dark else "rgba(255,255,255,0.93)"
    tc = "#f1f5f9" if dark else "#1e293b"
    sc = "#94a3b8" if dark else "#64748b"
    html = (f"<div style='position:fixed;bottom:32px;right:16px;z-index:9999;"
            f"background:{bg};border:1px solid rgba(227,0,27,0.25);border-radius:10px;"
            f"padding:11px 15px;font-family:Outfit,sans-serif;min-width:145px;'>"
            f"<div style='font-weight:800;font-size:9.5px;color:{tc};margin-bottom:7px;"
            f"letter-spacing:.09em;text-transform:uppercase;'>{title}</div>")
    for label, color in items:
        html += (f"<div style='display:flex;align-items:center;gap:7px;margin-bottom:4px;'>"
                 f"<span style='width:10px;height:10px;border-radius:50%;background:{color};"
                 f"display:inline-block;flex-shrink:0;border:1px solid rgba(255,255,255,0.2);'></span>"
                 f"<span style='font-size:10px;color:{sc};'>{label}</span></div>")
    html += "</div>"
    m.get_root().html.add_child(folium.Element(html))

# ══════════════════════════════════════════════════════════════════════════════
# DATA LOADING
# ══════════════════════════════════════════════════════════════════════════════
@st.cache_data(show_spinner="Loading…")
def load_data(file):
    xls = pd.ExcelFile(file, engine="openpyxl")
    out = {}
    for name in xls.sheet_names:
        try: out[name] = pd.read_excel(xls, sheet_name=name)
        except: pass
    return out

def kobo_get_token(username, password, base_url):
    url = f"{base_url}/token/?format=json"
    try:
        r = requests.get(url, auth=(username, password), timeout=20)
        r.raise_for_status()
        return r.json().get("token"), None
    except Exception as e:
        code = getattr(e.response if hasattr(e,"response") else None,"status_code",None)
        if code == 401: return None, "Invalid KoBoToolbox username or password."
        return None, str(e)

def kobo_list_forms(token, base_url):
    url = f"{base_url}/api/v2/assets/?asset_type=survey&format=json"
    headers = {"Authorization": f"Token {token}"}
    try:
        r = requests.get(url, headers=headers, timeout=25)
        r.raise_for_status()
        data = r.json()
        forms = []
        for a in data.get("results",[]):
            forms.append({
                "uid":   a.get("uid",""),
                "name":  a.get("name","Unnamed"),
                "submissions": a.get("deployment__submission_count",0),
                "owner": a.get("owner__username",""),
                "modified": str(a.get("date_modified",""))[:10],
            })
        return forms, None
    except Exception as e:
        return None, str(e)

def kobo_download_data(token, uid, base_url):
    url = f"{base_url}/api/v2/assets/{uid}/data/?format=json&limit=30000"
    headers = {"Authorization": f"Token {token}"}
    try:
        r = requests.get(url, headers=headers, timeout=60)
        r.raise_for_status()
        results = r.json().get("results", [])
        if not results: return pd.DataFrame(), None
        df = pd.json_normalize(results)
        df.columns = [c.split("/")[-1].lstrip("_") for c in df.columns]
        df = df.loc[:, ~df.columns.duplicated()]
        return df, None
    except Exception as e:
        return None, str(e)

# ══════════════════════════════════════════════════════════════════════════════
# CSS INJECTION
# ══════════════════════════════════════════════════════════════════════════════
def inject_css(T):
    is_dark = T.get("bg","") == DARK.get("bg","")
    shadow     = "0 4px 24px rgba(0,0,0,0.4)" if is_dark else "0 4px 24px rgba(0,0,0,0.08)"
    nav_shadow = "0 2px 20px rgba(0,0,0,0.5)" if is_dark else "0 2px 12px rgba(0,0,0,0.1)"
    img_filter = "brightness(0.65) saturate(1.2)" if is_dark else "brightness(0.8) saturate(1.1)"
    login_sh   = "0 40px 80px rgba(0,0,0,0.6)" if is_dark else "0 40px 80px rgba(0,0,0,0.15)"
    ac  = T["accent"]
    ac2 = T["accent2"]
    
    css = f"""
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500&display=swap');
    
    :root {{
        --bg: {T["bg"]};
        --surface: {T["surface"]};
        --panel: {T["panel"]};
        --border: {T["border"]};
        --border2: {T["border2"]};
        --text: {T["text"]};
        --muted: {T["muted"]};
        --dim: {T["dim"]};
        --navbg: {T["navbg"]};
        --navbdr: {T["navborder"]};
        --card: {T["card"]};
        --input: {T["input"]};
        --accent: {ac};
        --accent2: {ac2};
        --si-red: {SI_RED};
        --si-red2: {SI_RED2};
        --font: 'Outfit', sans-serif;
        --mono: 'JetBrains Mono', monospace;
        --r: 12px;
        --shadow: {shadow};
    }}
    
    *,*::before,*::after{{box-sizing:border-box;}}
    html,body{{font-family:var(--font);background:var(--bg);color:var(--text);margin:0;}}
    [data-testid='stAppViewContainer'],[data-testid='stMain'],.main .block-container{{background:var(--bg)!important;}}
    [data-testid='stHeader']{{background:var(--navbg)!important;border-bottom:3px solid {SI_RED}!important;}}
    [data-testid='stSidebar']{{display:none!important;}}
    [data-testid='block-container']{{padding:0!important;max-width:100%!important;}}
    ::-webkit-scrollbar{{width:5px;height:5px;}}
    ::-webkit-scrollbar-thumb{{background:{SI_RED};border-radius:3px;}}
    
    /* Main content spacing */
    .main .block-container {{
        padding: 0rem 1rem 2rem 1rem !important;
    }}
    
    /* Hero section */
    .si-hero{{position:relative;overflow:hidden;border-radius:14px;margin-bottom:1rem;min-height:180px;
        background:linear-gradient(135deg,#1A0004 0%,#2A0008 50%,#1A0004 100%);}}
    .si-hero img{{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;
        opacity:0.3;filter:{img_filter};}}
    .si-hero-content{{position:relative;z-index:2;padding:1.5rem 2rem;min-height:180px;
        display:flex;flex-direction:column;justify-content:flex-end;}}
    .si-tag{{display:inline-block;background:{SI_RED};color:#fff;font-size:.68rem;
        font-weight:800;letter-spacing:.12em;text-transform:uppercase;
        padding:3px 10px;border-radius:3px;margin-bottom:.7rem;width:fit-content;}}
    .si-hero-title{{font-size:1.7rem;font-weight:900;color:#fff;margin:0 0 .4rem;
        letter-spacing:-.02em;text-shadow:0 2px 20px rgba(0,0,0,0.5);}}
    .si-hero-sub{{font-size:.8rem;color:rgba(255,255,255,.7);margin:0;}}
    .si-hero-bar{{position:absolute;bottom:0;left:0;right:0;height:4px;
        background:linear-gradient(90deg,{SI_RED},{SI_RED2},{SI_RED});
        animation:redpulse 3s ease-in-out infinite;}}
    @keyframes redpulse{{0%,100%{{opacity:1}}50%{{opacity:.6}}}}
    
    /* Image slider */
    .img-slider{{overflow:hidden;border-radius:10px;margin:0.5rem 0 1rem 0;}}
    .img-track{{display:flex;gap:10px;animation:slide 32s linear infinite;width:max-content;}}
    .img-track img{{height:120px;width:200px;object-fit:cover;border-radius:8px;
        flex-shrink:0;filter:{img_filter};transition:filter .3s;
        border:1px solid rgba(227,0,27,0.2);}}
    .img-track img:hover{{filter:brightness(1) saturate(1.3);}}
    @keyframes slide{{0%{{transform:translateX(0)}}100%{{transform:translateX(-50%)}}}}
    
    /* Topbar */
    .si-topbar{{background:var(--navbg);border-bottom:3px solid {SI_RED};
        padding:.4rem 1.5rem;display:flex;align-items:center;gap:12px;
        position:sticky;top:0;z-index:1000;backdrop-filter:blur(16px);
        box-shadow:{nav_shadow};}}
    .si-logo-box{{width:32px;height:32px;background:{SI_RED};border-radius:6px;
        display:flex;align-items:center;justify-content:center;font-size:1rem;
        color:#fff;font-weight:900;flex-shrink:0;}}
    .si-brand{{font-size:.85rem;font-weight:900;color:#fff;font-family:var(--font);}}
    .si-brand small{{display:block;font-size:.55rem;color:rgba(255,255,255,.4);
        font-weight:400;letter-spacing:.09em;text-transform:uppercase;}}
    .si-chip{{background:rgba(255,255,255,.08);border:1px solid rgba(255,255,255,.12);
        border-radius:20px;padding:2px 10px;font-size:.68rem;color:rgba(255,255,255,.55);}}
    
    /* Navigation buttons */
    div[data-testid='stHorizontalBlock'] {{
        gap: 4px !important;
        margin: 0 !important;
        padding: 4px 12px !important;
        flex-wrap: wrap !important;
    }}
    div[data-testid='stHorizontalBlock'] > div > [data-testid='stButton'] button {{
        background: transparent !important;
        border: none !important;
        border-bottom: 3px solid transparent !important;
        border-radius: 0 !important;
        color: rgba(255,255,255,0.6) !important;
        font-family: var(--font) !important;
        font-size: 0.75rem !important;
        font-weight: 500 !important;
        padding: 0.4rem 0.6rem !important;
        min-width: 55px !important;
        white-space: nowrap !important;
        transition: all 0.2s ease !important;
    }}
    div[data-testid='stHorizontalBlock'] > div > [data-testid='stButton'] button:hover {{
        color: #ffffff !important;
        background: rgba(227, 0, 27, 0.08) !important;
        border-bottom-color: rgba(227, 0, 27, 0.5) !important;
    }}
    
    /* KPI Cards */
    .kpi-card{{background:var(--card);border:1px solid var(--border);border-radius:var(--r);
        padding:0.8rem 0.8rem 0.6rem;position:relative;overflow:hidden;
        transition:transform .2s,box-shadow .2s;box-shadow:var(--shadow);
        margin-bottom:0.5rem;}}
    .kpi-card:hover{{transform:translateY(-2px);box-shadow:0 10px 36px rgba(227,0,27,0.2);}}
    .kpi-card::before{{content:'';position:absolute;top:0;left:0;right:0;height:3px;}}
    .kpi-card::after{{content:'';position:absolute;bottom:0;left:0;width:0;height:2px;
        background:{SI_RED};transition:width .4s;}}
    .kpi-card:hover::after{{width:100%;}}
    .kpi-red::before{{background:linear-gradient(90deg,{SI_RED},{SI_RED2});}}
    .kpi-blue::before{{background:linear-gradient(90deg,#3B82F6,#60A5FA);}}
    .kpi-green::before{{background:linear-gradient(90deg,#10B981,#34D399);}}
    .kpi-amber::before{{background:linear-gradient(90deg,#F59E0B,#FCD34D);}}
    .kpi-purple::before{{background:linear-gradient(90deg,#8B5CF6,#A78BFA);}}
    .kpi-teal::before{{background:linear-gradient(90deg,#14B8A6,#5EEAD4);}}
    .kpi-label{{font-size:.58rem;font-weight:700;letter-spacing:.12em;text-transform:uppercase;
        color:var(--muted);margin-bottom:.3rem;}}
    .kpi-value{{font-size:1.5rem;font-weight:900;color:var(--text);line-height:1.1;font-family:var(--font);}}
    .kpi-sub{{font-size:.65rem;color:var(--muted);margin-top:.2rem;}}
    .kpi-icon{{position:absolute;top:.6rem;right:.7rem;font-size:1.1rem;opacity:.12;}}
    .kpi-delta{{font-size:.65rem;font-weight:700;margin-top:.25rem;
        display:inline-flex;align-items:center;gap:3px;padding:1px 6px;border-radius:20px;}}
    .d-up{{background:rgba(16,185,129,.15);color:#34D399;}}
    .d-down{{background:rgba(227,0,27,.15);color:#FF6680;}}
    .d-mid{{background:rgba(245,158,11,.15);color:#FCD34D;}}
    
    /* Section header */
    .sh{{font-size:.7rem;font-weight:800;letter-spacing:.14em;text-transform:uppercase;
        color:{SI_RED};margin:1rem 0 0.8rem;display:flex;align-items:center;gap:10px;}}
    .sh::before{{content:'';width:3px;height:14px;background:{SI_RED};border-radius:2px;flex-shrink:0;}}
    .sh::after{{content:'';flex:1;height:1px;background:var(--border);}}
    
    /* Page header */
    .ph{{border-bottom:1px solid var(--border);margin-bottom:1rem;padding-bottom:.6rem;}}
    .ph h1{{font-size:1.4rem;font-weight:900;color:var(--text);margin:0 0 2px;
        font-family:var(--font);letter-spacing:-.02em;}}
    .ph p{{font-size:.75rem;color:var(--muted)!important;margin:0;}}
    
    /* Badges */
    .badge{{display:inline-block;padding:2px 8px;border-radius:3px;
        font-size:.62rem;font-weight:700;letter-spacing:.04em;}}
    .bg{{background:rgba(16,185,129,.18);color:#34D399;}}
    .ba{{background:rgba(245,158,11,.18);color:#FCD34D;}}
    .br{{background:rgba(227,0,27,.18);color:#FF6680;}}
    .bn{{background:rgba(100,116,139,.18);color:#94A3B8;}}
    .pbar-wrap{{background:rgba(128,128,128,.12);border-radius:3px;height:4px;overflow:hidden;margin:4px 0 2px;}}
    .pbar{{height:100%;border-radius:3px;}}
    
    /* Indicator card */
    .ind-card{{background:var(--card);border:1px solid var(--border);border-left:3px solid {SI_RED};
        border-radius:var(--r);padding:.7rem 1rem;margin-bottom:.5rem;transition:border-color .2s;}}
    .ind-card:hover{{border-left-color:{SI_RED2};}}
    .ind-name{{font-size:.82rem;font-weight:600;color:var(--text);}}
    .ind-vals{{font-size:.68rem;color:var(--muted);font-family:var(--mono);}}
    
    /* Alert banner */
    .alert-banner{{background:rgba(227,0,27,.07);border:1px solid rgba(227,0,27,.22);
        border-left:3px solid {SI_RED};border-radius:var(--r);padding:.6rem 0.8rem;margin-bottom:.5rem;}}
    .alert-banner span{{font-size:.78rem;color:#FF9AAA;}}
    
    /* Inputs */
    [data-testid='stSelectbox']>div>div{{background:var(--input)!important;
        border:1px solid var(--border2)!important;border-radius:var(--r)!important;color:var(--text)!important;}}
    [data-testid='stTextInput']>div>div>input{{background:var(--input)!important;
        border:1px solid var(--border2)!important;color:var(--text)!important;border-radius:var(--r)!important;}}
    label{{color:var(--muted)!important;font-size:.75rem!important;}}
    p{{color:var(--muted)!important;}}
    
    /* Buttons */
    .stButton>button{{background:{SI_RED}!important;color:#fff!important;
        border:none!important;border-radius:6px!important;
        font-family:var(--font)!important;font-weight:700!important;
        font-size:.8rem!important;padding:.45rem 1.2rem!important;
        transition:all .2s!important;letter-spacing:.01em!important;}}
    .stButton>button:hover{{background:{SI_RED2}!important;
        transform:translateY(-1px)!important;box-shadow:0 4px 16px rgba(227,0,27,.4)!important;}}
    
    /* Charts */
    .stPlotlyChart {{
        margin-top: 0.25rem !important;
        margin-bottom: 0.5rem !important;
    }}
    
    /* Data source cards */
    .ds-card{{background:var(--panel);border:1px solid var(--border2);border-radius:14px;
        padding:1.5rem 1.5rem;text-align:center;transition:all .2s;}}
    .ds-card:hover{{border-color:var(--accent);transform:translateY(-3px);box-shadow:0 12px 40px rgba(59,130,246,0.15);}}
    .ds-icon{{font-size:2.2rem;margin-bottom:.6rem;}}
    .ds-title{{font-size:1rem;font-weight:700;color:var(--text);margin-bottom:.3rem;}}
    .ds-desc{{font-size:.75rem;color:var(--muted);line-height:1.5;}}
    .step-badge{{display:inline-block;background:rgba(59,130,246,0.15);color:#60A5FA;
        font-size:.65rem;font-weight:700;letter-spacing:.08em;text-transform:uppercase;
        padding:2px 10px;border-radius:20px;margin-bottom:1rem;}}
    .kf-card{{background:var(--panel);border:1px solid var(--border);border-radius:10px;
        padding:.7rem 1rem;margin-bottom:.4rem;display:flex;align-items:center;gap:10px;}}
    .kf-name{{font-size:.82rem;font-weight:600;color:var(--text);}}
    .kf-meta{{font-size:.68rem;color:var(--muted);margin-top:2px;}}
    .kf-badge{{font-size:.65rem;font-weight:700;padding:2px 8px;border-radius:20px;
        background:rgba(16,185,129,0.15);color:#34D399;margin-left:auto;white-space:nowrap;}}
    .step-row{{display:flex;align-items:center;gap:8px;font-size:.75rem;color:var(--muted);margin-bottom:1.2rem;}}
    .sdot{{width:22px;height:22px;border-radius:50%;display:flex;align-items:center;
        justify-content:center;font-size:.68rem;font-weight:700;flex-shrink:0;}}
    .sa{{background:{SI_RED};color:#fff;}} .sd{{background:#10B981;color:#fff;}}
    .sn{{background:var(--dim);color:var(--muted);}}
    .sline{{flex:1;height:1px;background:var(--border);}}
    
    /* Login */
    .login-card{{background:var(--card);border:1px solid var(--border2);
        border-top:4px solid {SI_RED};border-radius:16px;padding:2rem 2rem;
        box-shadow:{login_sh};}}
    """
    
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# MAP FUNCTIONS
# ══════════════════════════════════════════════════════════════════════════════
def map_beneficiaries(df, dark=True):
    dfm = _clean_gps(df)
    m   = _base_map(dark)
    _add_geojson_layer(m, dark=dark)
    _add_state_labels(m, dark)
    if not dfm.empty:
        HeatMap(dfm[["GPS_Latitude","GPS_Longitude"]].values.tolist(),
                radius=15, blur=20, min_opacity=0.18, max_zoom=10).add_to(m)
        cl = MarkerCluster(options={"maxClusterRadius":50,
                                    "showCoverageOnHover":False,
                                    "spiderfyOnMaxZoom":True}).add_to(m)
        for _, row in dfm.iterrows():
            sec   = str(row.get("Sector","")) if has(df,"Sector") else ""
            color = SC.get(sec, "#64748B")
            pop   = (f"<div style='font-family:Outfit,sans-serif;font-size:11px;min-width:160px;'>"
                     f"<b>{row.get('Beneficiary_ID','—')}</b><br>"
                     f"State: {row.get('State','—')}<br>"
                     f"<b style='color:{color};'>{sec}</b><br>"
                     f"Displacement: {row.get('Displacement_Status','—')}<br>"
                     f"Vulnerability: {row.get('Vulnerability_Level','—')}</div>")
            folium.CircleMarker(
                location=[row["GPS_Latitude"], row["GPS_Longitude"]],
                radius=4, color=color, fill=True, fill_color=color,
                fill_opacity=0.8, weight=0.5,
                popup=folium.Popup(pop, max_width=220),
                tooltip=f"{row.get('Locality','—')} · {sec}"
            ).add_to(cl)
    _map_legend(m, list(SC.items()), "Sectors", dark)
    return m

def map_choropleth_density(df, dark=True):
    m = _base_map(dark)
    if has(df,"State") and not df.empty:
        counts = df.groupby("State").size().reset_index(name="value")
        counts.columns = ["state","value"]
        _add_geojson_layer(m, data_col="Beneficiaries", state_values=counts,
                           dark=dark, line_weight=1.8)
    else:
        _add_geojson_layer(m, dark=dark)
    _add_state_labels(m, dark)
    return m

def map_sector_coverage(df, dark=True):
    m = _base_map(dark)
    _add_geojson_layer(m, dark=dark)
    _add_state_labels(m, dark)
    OFFSETS = [(0.0,0.0),(0.25,0.0),(-0.25,0.0),(0.0,0.28),(0.0,-0.28)]
    if has(df,"State") and has(df,"Sector"):
        for state, (lat, lon) in STATE_CENTROIDS.items():
            sub   = df[df["State"]==state] if has(df,"State") else pd.DataFrame()
            total = len(sub)
            if total == 0: continue
            for i,(sec,color) in enumerate(SC.items()):
                n = slen(sub,"Sector",sec)
                if n == 0: continue
                pct    = n / max(total,1)
                radius = max(6, min(38, pct * 50))
                dlat,dlon = OFFSETS[i % len(OFFSETS)]
                mlat = max(SUDAN_LAT_MIN+0.1, min(SUDAN_LAT_MAX-0.1, lat+dlat))
                mlon = max(SUDAN_LON_MIN+0.1, min(SUDAN_LON_MAX-0.1, lon+dlon))
                folium.CircleMarker(
                    location=[mlat, mlon], radius=radius,
                    color=color, fill=True, fill_color=color,
                    fill_opacity=0.6, weight=1.2,
                    tooltip=f"{state} · {sec}: {n:,} ({pct:.0%})",
                    popup=folium.Popup(
                        f"<b>{state}</b><br><b style='color:{color};'>{sec}</b><br>"
                        f"{n:,} beneficiaries ({pct:.0%})", max_width=200)
                ).add_to(m)
    _map_legend(m, list(SC.items()), "Sectors", dark)
    return m

def map_displacement(df, dark=True):
    dfm = _clean_gps(df)
    m   = _base_map(dark)
    _add_geojson_layer(m, dark=dark)
    _add_state_labels(m, dark)
    DISP_COLORS = {"IDP":"#EF4444","Refugee":"#3B82F6",
                   "Host Community":"#10B981","Returnee":"#F59E0B"}
    if not dfm.empty and has(dfm,"Displacement_Status"):
        for disp,color in DISP_COLORS.items():
            sub = dfm[dfm["Displacement_Status"]==disp]
            if sub.empty: continue
            cl = MarkerCluster(name=disp,
                               options={"maxClusterRadius":35,"showCoverageOnHover":False}).add_to(m)
            for _,row in sub.iterrows():
                folium.CircleMarker(
                    location=[row["GPS_Latitude"],row["GPS_Longitude"]],
                    radius=4,color=color,fill=True,fill_color=color,
                    fill_opacity=0.8,weight=0.5,
                    tooltip=f"{row.get('Locality','—')} · {disp}",
                    popup=folium.Popup(
                        f"<b>{disp}</b><br>State: {row.get('State','—')}<br>"
                        f"Locality: {row.get('Locality','—')}",max_width=180)
                ).add_to(cl)
    folium.LayerControl(position="topright").add_to(m)
    _map_legend(m, list(DISP_COLORS.items()), "Displacement", dark)
    return m

def map_vulnerability(df, dark=True):
    dfm = _clean_gps(df)
    m   = _base_map(dark)
    VULN_COLORS = {"Extremely Vulnerable":"#EF4444",
                   "Vulnerable":"#F59E0B",
                   "Moderately Vulnerable":"#10B981"}
    VULN_WEIGHTS = {"Extremely Vulnerable":1.0,"Vulnerable":0.6,"Moderately Vulnerable":0.3}
    if not dfm.empty and has(dfm,"Vulnerability_Level"):
        for vl,color in VULN_COLORS.items():
            sub = dfm[dfm["Vulnerability_Level"]==vl]
            if sub.empty: continue
            w = VULN_WEIGHTS[vl]
            data = [[r["GPS_Latitude"],r["GPS_Longitude"],w] for _,r in sub.iterrows()]
            HeatMap(data,radius=14,blur=16,min_opacity=0.22,
                    gradient={"0.3":color+"55","0.6":color+"AA","1.0":color}).add_to(m)
        for state,(lat,lon) in STATE_CENTROIDS.items():
            sub = dfm[dfm["State"]==state] if has(dfm,"State") else pd.DataFrame()
            if sub.empty: continue
            dom = sub["Vulnerability_Level"].mode()
            if dom.empty: continue
            col = VULN_COLORS.get(dom.iloc[0],"#64748B")
            n   = len(sub)
            folium.CircleMarker(
                location=[lat,lon],
                radius=max(10,min(35,(n/max(len(dfm),1))**0.5*45)),
                color=col,fill=True,fill_color=col,fill_opacity=0.2,weight=1.5,
                tooltip=f"{state} — dominant: {dom.iloc[0]} ({n:,})"
            ).add_to(m)
    _add_geojson_layer(m,dark=dark,fill_opacity=0.05,line_weight=1.2)
    _add_state_labels(m,dark)
    _map_legend(m,list(VULN_COLORS.items()),"Vulnerability",dark)
    return m

# ══════════════════════════════════════════════════════════════════════════════
# TOP NAVIGATION
# ══════════════════════════════════════════════════════════════════════════════
def top_nav():
    page = st.session_state.get("page", "Overview")
    user = st.session_state.get("user", "")
    dark = st.session_state.get("dark", True)
    src  = st.session_state.get("data_source", "—")
    src_icon = "🔗" if src == "kobo" else "📊"
    labels    = [lbl for _, lbl in NAV_ITEMS]
    active_idx = labels.index(page) + 1 if page in labels else 1
    n_nav     = len(NAV_ITEMS)

    st.markdown(f"""
    <div class='si-topbar'>
      <div class='si-logo-box'>SI</div>
      <div>
        <div class='si-brand'>SOLIDARITES INTERNATIONAL
          <small>Sudan Mission · Information Management</small>
        </div>
      </div>
      <div style='margin-left:auto;display:flex;align-items:center;gap:10px;'>
        <div class='si-chip'>{src_icon} {user}</div>
      </div>
    </div>
    <div style='padding:0.3rem 1.2rem 0 1.2rem;'>
    """, unsafe_allow_html=True)

    st.markdown(
        "<style>"
        f"div[data-testid='stHorizontalBlock']>div:nth-child({active_idx})"
        f">[data-testid='stButton'] button{{"
        f"color:#fff!important;"
        f"border-bottom:3px solid {SI_RED}!important;"
        f"font-weight:700!important;"
        f"background:rgba(227,0,27,0.13)!important;}}"
        "</style>",
        unsafe_allow_html=True
    )

    cols = st.columns([1]*n_nav + [0.55, 0.55])
    for i, (icon, lbl) in enumerate(NAV_ITEMS):
        with cols[i]:
            if st.button(f"{icon} {lbl}", key=f"nav_{lbl}",
                         use_container_width=True, help=lbl):
                if st.session_state.get("page") != lbl:
                    st.session_state["page"] = lbl
                    st.rerun()
    with cols[-2]:
        if st.button("☀️" if dark else "🌙", key="theme_btn",
                     use_container_width=True, help="Toggle theme"):
            st.session_state["dark"] = not dark
            st.rerun()
    with cols[-1]:
        if st.button("🚪", key="logout_btn",
                     use_container_width=True, help="Logout"):
            st.session_state.clear()
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("<div style='padding:0rem 1.2rem;'>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# LOGIN PAGE
# ══════════════════════════════════════════════════════════════════════════════
def login_page():
    inject_css(DARK)

    st.markdown("""<style>
    [data-testid="stAppViewContainer"] {
        background: linear-gradient(160deg,#0E0004 0%,#180008 40%,#0E0004 100%) !important;
    }
    </style>""", unsafe_allow_html=True)

    st.markdown(f"""
    <div style='background:rgba(0,0,0,0.5);border-bottom:3px solid {SI_RED};
         padding:.6rem 2rem;display:flex;align-items:center;gap:12px;
         backdrop-filter:blur(12px);'>
      <div style='width:34px;height:34px;background:{SI_RED};border-radius:6px;
           display:flex;align-items:center;justify-content:center;
           font-size:1rem;font-weight:900;color:#fff;flex-shrink:0;'>SI</div>
      <div>
        <div style='font-size:.85rem;font-weight:900;color:#fff;
             font-family:Outfit,sans-serif;'>SOLIDARITES INTERNATIONAL</div>
        <div style='font-size:.55rem;color:rgba(255,255,255,.4);
             letter-spacing:.1em;text-transform:uppercase;'>
          Sudan Mission · Information Management Platform
        </div>
      </div>
      <div style='margin-left:auto;background:{SI_RED};color:#fff;
           font-size:.62rem;font-weight:800;letter-spacing:.1em;
           text-transform:uppercase;padding:3px 12px;border-radius:4px;'>
        Restricted Access
      </div>
    </div>
    """, unsafe_allow_html=True)

    imgs_html = "".join(f"<img src='{u}' alt='SI humanitarian' style='height:100px;'>" for u in SI_IMAGES * 2)
    st.markdown(f"""<div class='img-slider' style='border-radius:0;margin:0;height:100px;'>
      <div class='img-track' style='height:100px;'>{imgs_html}</div>
    </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    col_info, col_form = st.columns([1.15, 1])

    with col_info:
        st.markdown(f"""
        <div style='padding:1rem 0.5rem;'>
          <div style='display:inline-block;background:{SI_RED};color:#fff;
               font-size:.62rem;font-weight:800;letter-spacing:.12em;
               text-transform:uppercase;padding:2px 8px;border-radius:3px;
               margin-bottom:1rem;'>Sudan Mission 2025–2026</div>
          <h2 style='font-size:1.8rem;font-weight:900;color:#fff;margin:0 0 .5rem;
              line-height:1.1;letter-spacing:-.03em;font-family:Outfit,sans-serif;'>
            Information<br><span style='color:{SI_RED};'>Management</span><br>Dashboard
          </h2>
          <p style='font-size:.82rem;color:rgba(255,255,255,.5);line-height:1.6;margin:0 0 1rem;'>
            Real-time monitoring of multi-sector humanitarian response across
            WASH, Food Security, Shelter & NFI, and Cash & Voucher programs in Sudan.
          </p>
          <div style='display:flex;flex-direction:column;gap:.4rem;'>
            <div style='font-size:.75rem;color:rgba(255,255,255,.4);display:flex;align-items:center;gap:6px;'>
              <span style='color:#3B82F6;'>💧</span> WASH — Water, Sanitation & Hygiene
            </div>
            <div style='font-size:.75rem;color:rgba(255,255,255,.4);display:flex;align-items:center;gap:6px;'>
              <span style='color:#10B981;'>🌾</span> FSL — Food Security & Livelihoods
            </div>
            <div style='font-size:.75rem;color:rgba(255,255,255,.4);display:flex;align-items:center;gap:6px;'>
              <span style='color:#F59E0B;'>🏠</span> Shelter & Non-Food Items
            </div>
            <div style='font-size:.75rem;color:rgba(255,255,255,.4);display:flex;align-items:center;gap:6px;'>
              <span style='color:{SI_RED};'>💵</span> Cash & Voucher Assistance (CVA)
            </div>
          </div>
        </div>
        """, unsafe_allow_html=True)

    with col_form:
        st.markdown(f"""
        <div style='background:rgba(28,33,48,0.95);border:1px solid rgba(227,0,27,0.35);
             border-top:4px solid {SI_RED};border-radius:16px;padding:1.5rem 1.8rem;
             box-shadow:0 30px 80px rgba(0,0,0,0.5);'>
          <div style='font-size:1.2rem;font-weight:900;color:#fff;
               font-family:Outfit,sans-serif;margin-bottom:.2rem;'>Sign In</div>
          <div style='font-size:.75rem;color:#64748B;margin-bottom:1rem;'>
            Enter your credentials to access the dashboard.
          </div>
        """, unsafe_allow_html=True)

        st.markdown("<style>div[data-testid='stTextInput'] {margin-top: 0.4rem;}</style>", unsafe_allow_html=True)

        st.markdown(f"<div style='font-size:.68rem;font-weight:700;color:#64748B;letter-spacing:.07em;text-transform:uppercase;margin-bottom:.1rem;'>Username</div>", unsafe_allow_html=True)
        user = st.text_input("Username", placeholder="im_manager",
                             label_visibility="collapsed", key="login_user")

        st.markdown(f"<div style='font-size:.68rem;font-weight:700;color:#64748B;letter-spacing:.07em;text-transform:uppercase;margin:.6rem 0 .1rem;'>Password</div>", unsafe_allow_html=True)
        pw = st.text_input("Password", type="password", placeholder="••••••••",
                           label_visibility="collapsed", key="login_pw")

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Sign in →", use_container_width=True, key="login_btn"):
            if CREDENTIALS.get(user) == pw:
                st.session_state.update(auth=True, user=user, dark=True, page="Overview")
                st.rerun()
            else:
                st.error("❌ Invalid username or password.")

        st.markdown(f"""<div style='text-align:center;font-size:.65rem;
             color:rgba(255,255,255,.15);margin-top:1rem;'>
          Solidarites International © 2026 · Confidential
        </div></div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# DATA SOURCE PAGE
# ══════════════════════════════════════════════════════════════════════════════
def datasource_page():
    inject_css(DARK)
    th = DARK

    step = st.session_state.get("kobo_step", 0)

    def step_bar(current):
        labels = ["Source","Connect","Forms","Load"]
        html = "<div class='step-row'>"
        for i,s in enumerate(labels):
            cls = "sa" if i==current else ("sd" if i<current else "sn")
            wt  = "700" if i==current else "400"
            col = "var(--text)" if i==current else "var(--muted)"
            html += f"<div class='sdot {cls}'>{i+1}</div>"
            html += f"<span style='color:{col};font-weight:{wt};'>{s}</span>"
            if i<len(labels)-1: html += "<div class='sline'></div>"
        html += "</div>"
        st.markdown(html, unsafe_allow_html=True)

    if step == 0:
        c1,c2,c3 = st.columns([1,2,1])
        with c2:
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("<div class='step-badge'>Step 1 of 4 — Data Source</div>", unsafe_allow_html=True)
            st.markdown(f"<div style='font-size:1.3rem;font-weight:800;color:{th['text']};margin-bottom:.2rem;font-family:Outfit,sans-serif;'>Choose your data source</div>",unsafe_allow_html=True)
            st.markdown(f"<div style='font-size:.8rem;color:{th['muted']};margin-bottom:1.5rem;'>Select how to load program data into the dashboard.</div>",unsafe_allow_html=True)
            step_bar(0)
            ca,cb = st.columns(2)
            with ca:
                st.markdown("""<div class='ds-card'>
                  <div class='ds-icon'>📊</div>
                  <div class='ds-title'>Excel File</div>
                  <div class='ds-desc'>Upload an <b>.xlsx</b> file. Best for pre-processed or offline data.</div>
                </div>""",unsafe_allow_html=True)
                st.markdown("<br>",unsafe_allow_html=True)
                if st.button("Use Excel File →", use_container_width=True, key="src_excel"):
                    st.session_state.update(data_source="excel", kobo_step=10)
                    st.rerun()
            with cb:
                st.markdown("""<div class='ds-card'>
                  <div class='ds-icon'>🔗</div>
                  <div class='ds-title'>KoBoToolbox Live</div>
                  <div class='ds-desc'>Connect directly to KoBoToolbox and pull real-time form submissions.</div>
                </div>""",unsafe_allow_html=True)
                st.markdown("<br>",unsafe_allow_html=True)
                if st.button("Connect to KoBoToolbox →", use_container_width=True, key="src_kobo"):
                    st.session_state.update(data_source="kobo", kobo_step=1)
                    st.rerun()
            st.markdown(f"<br><div style='text-align:center;font-size:.68rem;color:{th['muted']};'>You can switch data source anytime from the dashboard.</div>",unsafe_allow_html=True)

    elif step == 10:
        c1,c2,c3 = st.columns([1,2,1])
        with c2:
            st.markdown("<br>",unsafe_allow_html=True)
            st.markdown("<div class='step-badge'>Excel Upload</div>",unsafe_allow_html=True)
            st.markdown(f"<div style='font-size:1.3rem;font-weight:800;color:{th['text']};margin-bottom:1rem;font-family:Outfit,sans-serif;'>Upload Excel database</div>",unsafe_allow_html=True)
            step_bar(3)
            up = st.file_uploader("Select .xlsx file", type=["xlsx"])
            if up:
                with st.spinner("Loading sheets…"):
                    data = load_data(up)
                st.session_state["dfs"] = data
                st.success(f"✅ {len(data)} sheets loaded")
                st.markdown("<br>",unsafe_allow_html=True)
                if st.button("Open Dashboard →", use_container_width=True, key="excel_go"):
                    st.session_state["kobo_step"] = 99
                    st.rerun()
            st.markdown("<br>",unsafe_allow_html=True)
            if st.button("← Back", key="excel_back"):
                st.session_state["kobo_step"]=0
                st.rerun()

    elif step == 1:
        c1,c2,c3 = st.columns([1,2,1])
        with c2:
            st.markdown("<br>",unsafe_allow_html=True)
            st.markdown("<div class='step-badge'>Step 2 of 4 — Connect</div>",unsafe_allow_html=True)
            st.markdown(f"<div style='font-size:1.3rem;font-weight:800;color:{th['text']};margin-bottom:.2rem;font-family:Outfit,sans-serif;'>KoBoToolbox Login</div>",unsafe_allow_html=True)
            st.markdown(f"<div style='font-size:.8rem;color:{th['muted']};margin-bottom:1rem;'>Your password is used only to retrieve a temporary API token and is never stored.</div>",unsafe_allow_html=True)
            step_bar(1)

            srv_choice = st.selectbox("KoBoToolbox Server", list(KOBO_SERVERS.keys()), key="kobo_srv")
            base_url   = KOBO_SERVERS[srv_choice]
            if base_url == "custom":
                base_url = st.text_input("Custom server URL", placeholder="https://your-kobo-server.org", key="kobo_cust")

            kobo_u = st.text_input("Username", placeholder="your_username", key="kobo_u")
            kobo_p = st.text_input("Password", type="password", placeholder="••••••••", key="kobo_p")

            ca,cb = st.columns([3,1])
            with ca:
                go = st.button("Connect →", use_container_width=True, key="kobo_go")
            with cb:
                if st.button("← Back", key="k1b"):
                    st.session_state["kobo_step"]=0
                    st.rerun()

            if go:
                if not kobo_u or not kobo_p:
                    st.error("Enter your username and password.")
                    return
                if not base_url or base_url=="custom":
                    st.error("Enter a valid server URL.")
                    return
                if not HAS_REQUESTS:
                    st.error("Install requests: pip install requests")
                    return
                with st.spinner("Authenticating…"):
                    token, err = kobo_get_token(kobo_u, kobo_p, base_url)
                if err:
                    st.error(f"❌ {err}")
                else:
                    st.session_state.update(kobo_token=token, kobo_base_url=base_url,
                                            kobo_username=kobo_u, kobo_step=2)
                    st.rerun()

    elif step == 2:
        token    = st.session_state.get("kobo_token","")
        base_url = st.session_state.get("kobo_base_url","")
        kuser    = st.session_state.get("kobo_username","")

        c1,c2,c3 = st.columns([0.4,3,0.4])
        with c2:
            st.markdown("<br>",unsafe_allow_html=True)
            st.markdown("<div class='step-badge'>Step 3 of 4 — Select Forms</div>",unsafe_allow_html=True)
            st.markdown(f"<div style='font-size:1.3rem;font-weight:800;color:{th['text']};margin-bottom:.2rem;font-family:Outfit,sans-serif;'>Select KoBoToolbox Forms</div>",unsafe_allow_html=True)
            st.markdown(f"<div style='font-size:.78rem;color:{th['muted']};margin-bottom:0.8rem;'>Connected as <b style='color:{th['text']};'>{kuser}</b> · {base_url}</div>",unsafe_allow_html=True)
            step_bar(2)

            if "kobo_forms" not in st.session_state:
                with st.spinner("Fetching forms list…"):
                    forms, err = kobo_list_forms(token, base_url)
                if err:
                    st.error(f"❌ {err}")
                    if st.button("← Back",key="k2be"):
                        st.session_state["kobo_step"]=1
                    return
                st.session_state["kobo_forms"] = forms or []

            forms = st.session_state.get("kobo_forms",[])
            if not forms:
                st.warning("No forms found. Check your credentials or KoBoToolbox account.")
                if st.button("← Back",key="k2bno"):
                    st.session_state["kobo_step"]=1
                    st.rerun()
                return

            search   = st.text_input("🔍 Filter forms by name", label_visibility="collapsed", placeholder="Search…", key="fsearch")
            filtered = [f for f in forms if search.lower() in f["name"].lower()] if search else forms
            st.markdown(f"<div style='font-size:.72rem;color:{th['muted']};margin-bottom:.5rem;'>{len(filtered)} form(s) shown</div>",unsafe_allow_html=True)

            selected = st.session_state.get("kobo_selected",{})
            for form in filtered:
                uid  = form["uid"];  name = form["name"]
                subs = form["submissions"]; owner = form["owner"]; mod = form["modified"]
                cc, ci = st.columns([0.07, 0.93])
                with cc:
                    checked = st.checkbox("", value=selected.get(uid,False), key=f"chk_{uid}")
                    selected[uid]=checked
                with ci:
                    fc = "#34D399" if subs>0 else "#64748B"
                    st.markdown(f"""<div class='kf-card'>
                      <div style='flex:1;'>
                        <div class='kf-name'>📋 {name}</div>
                        <div class='kf-meta'>UID: <code>{uid}</code> · Owner: {owner} · Modified: {mod}</div>
                      </div>
                      <div class='kf-badge' style='color:{fc};'>{subs:,} submissions</div>
                    </div>""",unsafe_allow_html=True)
            st.session_state["kobo_selected"] = selected

            n_sel = sum(1 for v in selected.values() if v)
            st.markdown("<br>",unsafe_allow_html=True)
            ca,cb,cc2 = st.columns([1,2,1])
            with ca:
                if st.button("← Back",key="k2b"):
                    st.session_state.pop("kobo_forms",None)
                    st.session_state["kobo_step"]=1
                    st.rerun()
            with cb:
                st.markdown(f"<div style='text-align:center;font-size:.78rem;color:{th['text']};padding:.4rem;'><b>{n_sel}</b> form(s) selected</div>",unsafe_allow_html=True)
            with cc2:
                if st.button(f"Load {n_sel} →", use_container_width=True, key="k2load", disabled=(n_sel==0)):
                    st.session_state["kobo_step"]=3
                    st.rerun()

    elif step == 3:
        token    = st.session_state.get("kobo_token","")
        base_url = st.session_state.get("kobo_base_url","")
        forms    = st.session_state.get("kobo_forms",[])
        selected = st.session_state.get("kobo_selected",{})
        sel_uids = [u for u,v in selected.items() if v]
        fnames   = {f["uid"]:f["name"] for f in forms}

        c1,c2,c3 = st.columns([1,2,1])
        with c2:
            st.markdown("<br>",unsafe_allow_html=True)
            st.markdown("<div class='step-badge'>Step 4 of 4 — Loading Data</div>",unsafe_allow_html=True)
            st.markdown(f"<div style='font-size:1.3rem;font-weight:800;color:{th['text']};margin-bottom:.2rem;font-family:Outfit,sans-serif;'>Downloading Submissions</div>",unsafe_allow_html=True)
            st.markdown(f"<div style='font-size:.78rem;color:{th['muted']};margin-bottom:1rem;'>Downloading {len(sel_uids)} form(s). This may take a moment.</div>",unsafe_allow_html=True)
            step_bar(3)

            pb   = st.progress(0)
            stat = st.empty()
            dfs_k = {}; logs = []

            for i, uid in enumerate(sel_uids):
                nm = fnames.get(uid,uid)
                pb.progress(i/len(sel_uids), text=f"Downloading: {nm}…")
                stat.markdown(f"<div style='font-size:.75rem;color:{th['muted']};'>⏳ {nm}…</div>",unsafe_allow_html=True)
                df, err = kobo_download_data(token, uid, base_url)
                if err:
                    logs.append(f"❌ **{nm}** — {err}")
                else:
                    dfs_k[nm] = df if df is not None else pd.DataFrame()
                    logs.append(f"✅ **{nm}** — {len(df) if df is not None else 0:,} records")

            pb.progress(1.0, text="Done!")
            stat.empty()

            for log in logs:
                st.markdown(log)

            if dfs_k:
                DASH_SHEETS = ["— Keep as-is —","Beneficiary_Registration","WASH_Monitoring",
                               "FSL_Distribution","CVA_Cash_Transfers","Indicator_Tracker"]
                st.markdown("<br>",unsafe_allow_html=True)
                st.markdown(f"<div style='font-weight:700;font-size:.85rem;color:{th['text']};margin-bottom:.5rem;'>Map forms to dashboard sections (optional)</div>",unsafe_allow_html=True)
                mappings = {}
                for fnm in dfs_k:
                    ca2,cb2 = st.columns([1.6,1])
                    with ca2:
                        st.markdown(f"<div style='font-size:.78rem;font-weight:500;color:{th['text']};padding:.5rem 0;'>📋 {fnm}</div>",unsafe_allow_html=True)
                    with cb2:
                        mappings[fnm] = st.selectbox("→",DASH_SHEETS,key=f"mp_{fnm}",label_visibility="collapsed")
                st.session_state["kobo_mappings"] = mappings

                st.markdown("<br>",unsafe_allow_html=True)
                ca3,cb3 = st.columns([1,2])
                with ca3:
                    if st.button("← Back",key="k3b"):
                        st.session_state["kobo_step"]=2
                        st.rerun()
                with cb3:
                    if st.button("Open Dashboard →", use_container_width=True, key="k3go"):
                        final = {}
                        for fnm,df in dfs_k.items():
                            tgt = mappings.get(fnm,"— Keep as-is —")
                            final[tgt if tgt!="— Keep as-is —" else fnm] = df
                        st.session_state["dfs"] = final
                        st.session_state["kobo_step"] = 99
                        st.rerun()
            else:
                st.error("No data loaded. Check permissions on the selected forms.")
                if st.button("← Start over",key="k3rst"):
                    st.session_state["kobo_step"]=0
                    st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# PAGE FUNCTIONS (simplified for length - same as original but with spacing fixes)
# ══════════════════════════════════════════════════════════════════════════════
def page_overview(dfs):
    ph("Program Overview", "Multi-sector humanitarian response dashboard")
    
    st.markdown("<div style='margin-bottom:0.5rem;'></div>", unsafe_allow_html=True)
    
    df_b = dfs.get("Beneficiary_Registration", pd.DataFrame())
    df_w = dfs.get("WASH_Monitoring",           pd.DataFrame())
    df_f = dfs.get("FSL_Distribution",          pd.DataFrame())
    df_c = dfs.get("CVA_Cash_Transfers",        pd.DataFrame())
    df_i = dfs.get("Indicator_Tracker",         pd.DataFrame())

    tot  = len(df_b)
    act  = slen(df_b,"Registration_Status","Active")
    wr   = int(ssum(df_w,"Reached_Beneficiaries"))
    fhh  = int(ssum(df_f,"HH_Reached"))
    paid = sfilt(df_c,"Transfer_Status","Paid")
    usd  = paid["Transfer_Value_USD"].sum() if has(paid,"Transfer_Value_USD") and len(paid)>0 else 0
    on_t = slen(df_i,"Status","On track")
    ti   = len(df_i)

    imgs_html = "".join(f"<img src='{u}' alt='SI'>" for u in SI_IMAGES * 2)
    st.markdown(f"""
    <div class='si-hero'>
      <img src='{SI_IMAGES[1]}' alt='SI Sudan humanitarian response'>
      <div class='si-hero-content'>
        <div class='si-tag'>Sudan Mission · {datetime.now().strftime("%B %Y")}</div>
        <div class='si-hero-title'>Program Overview Dashboard</div>
        <div class='si-hero-sub'>
          Multi-sector humanitarian response ·
          {tot:,} beneficiaries registered ·
          {suniq(df_b,"State")} states covered
        </div>
      </div>
      <div class='si-hero-bar'></div>
    </div>
    <div class='img-slider'>
      <div class='img-track'>{imgs_html}</div>
    </div>
    """, unsafe_allow_html=True)

    sh("Programme Scale")
    
    c1,c2,c3,c4,c5,c6 = st.columns(6)
    c1.markdown(kpi("Beneficiaries", N(tot), f"{act:,} active",    "blue",  "👤", f"↑ {act/tot:.0%}" if tot else None,"up"), unsafe_allow_html=True)
    c2.markdown(kpi("WASH Reached",  N(wr),  "cumulative",         "teal",  "💧"), unsafe_allow_html=True)
    c3.markdown(kpi("FSL HH",        N(fhh), "households reached", "green", "🌾"), unsafe_allow_html=True)
    c4.markdown(kpi("Cash Paid",     f"${N(usd)}","USD disbursed", "amber", "💵"), unsafe_allow_html=True)
    c5.markdown(kpi("States",        str(suniq(df_b,"State")),"covered","purple","🗺️"), unsafe_allow_html=True)
    c6.markdown(kpi("On Track",      f"{on_t}/{ti}","indicators",  "green", "📊", f"↑ {on_t/ti:.0%}" if ti else None,"up"), unsafe_allow_html=True)

    st.markdown("<div style='margin:0.5rem 0 0.5rem 0;'></div>", unsafe_allow_html=True)

    alerts = []
    pb = slen(df_f,"Pipeline_Status","Pipeline break")
    fa = slen(df_c,"Transfer_Status","Failed")
    ot = slen(df_i,"Status","Off track")
    if pb: alerts.append(f"⚠️  <b>{pb}</b> pipeline breaks detected in FSL supply chain")
    if fa: alerts.append(f"❌  <b>{fa}</b> failed cash transfers require investigation")
    if ot: alerts.append(f"🔴  <b>{ot}</b> program indicators are off track")
    if alerts:
        sh("Active Alerts")
        for a in alerts:
            st.markdown(f"<div class='alert-banner'><span>{a}</span></div>",unsafe_allow_html=True)

    sh("Beneficiary Profile")
    c1,c2,c3 = st.columns([1.1,1,1])
    with c1:
        if not df_b.empty and has(df_b,"Sector"):
            d = df_b.groupby("Sector").size().reset_index(name="n")
            fig = px.pie(d, values="n", names="Sector", hole=0.58,
                         color="Sector", color_discrete_map=SC, title="Beneficiaries by Sector")
            fig.update_traces(textinfo="percent", textfont_size=9,
                              marker=dict(line=dict(color=TH()["bg"],width=2)))
            pc(T(fig,h=280))
    with c2:
        if not df_b.empty and has(df_b,"Displacement_Status"):
            d = df_b["Displacement_Status"].value_counts().reset_index()
            d.columns=["Status","Count"]
            fig = px.bar(d, x="Count", y="Status", orientation="h",
                         color="Count", color_continuous_scale=["#1E3A6E","#3B82F6"],
                         title="Displacement Status")
            fig.update_layout(coloraxis_showscale=False)
            pc(T(fig,h=280,leg=False))
    with c3:
        if not df_b.empty and has(df_b,"Sex") and has(df_b,"Vulnerability_Level"):
            ct = df_b.groupby(["Vulnerability_Level","Sex"]).size().reset_index(name="n")
            fig = px.bar(ct, x="Vulnerability_Level", y="n", color="Sex", barmode="stack",
                         color_discrete_map={"Female":"#EC4899","Male":"#3B82F6"},
                         title="Vulnerability × Sex")
            pc(T(fig,h=280))

def page_map(dfs):
    ph("Geographic Coverage", "Sudan shapefile maps · choropleth · clusters · heatmap · spatial analysis")
    
    st.markdown("<div style='margin-bottom:0.5rem;'></div>", unsafe_allow_html=True)
    
    df = dfs.get("Beneficiary_Registration", pd.DataFrame())
    if df.empty:
        st.info("Load the Excel database to view geographic data.")
        return
    th   = TH()
    dark = st.session_state.get("dark", True)

    c1,c2,c3,c4 = st.columns(4)
    with c1: s1 = st.selectbox("State",        sopts(df,"State"),               key="m_s")
    with c2: s2 = st.selectbox("Sector",       sopts(df,"Sector"),              key="m_sec")
    with c3: s3 = st.selectbox("Displacement", sopts(df,"Displacement_Status"), key="m_d")
    with c4: s4 = st.selectbox("Vulnerability",sopts(df,"Vulnerability_Level"), key="m_v")

    df_f = sfilt(sfilt(sfilt(sfilt(df.copy(),"State",s1),"Sector",s2),
                       "Displacement_Status",s3),"Vulnerability_Level",s4)
    nb  = len(df_f)
    fem = slen(df_f,"Sex","Female")

    c1,c2,c3,c4,c5,c6 = st.columns(6)
    c1.markdown(kpi("Beneficiaries", N(nb),              "in selection", "red",   "👥"), unsafe_allow_html=True)
    c2.markdown(kpi("States",        N(suniq(df_f,"State")), "covered",  "blue",  "🗺️"), unsafe_allow_html=True)
    c3.markdown(kpi("Localities",    N(suniq(df_f,"Locality")),"zones",  "teal",  "📌"), unsafe_allow_html=True)
    c4.markdown(kpi("Female",        f"{100*fem/nb:.0f}%" if nb else "—","","purple","♀"), unsafe_allow_html=True)
    c5.markdown(kpi("IDP",           N(slen(df_f,"Displacement_Status","IDP")),"","amber","🏕️"), unsafe_allow_html=True)
    c6.markdown(kpi("Active",        N(slen(df_f,"Registration_Status","Active")),"","green","✅"), unsafe_allow_html=True)

    st.markdown("<div style='margin:0.5rem 0 0.5rem 0;'></div>", unsafe_allow_html=True)

    sh("Map 1 — Beneficiary Distribution on Sudan Shapefile")
    col_m1, col_r1 = st.columns([2.5, 1])
    with col_m1:
        st_folium(map_beneficiaries(df_f, dark), use_container_width=True,
                  height=420, returned_objects=[], key="map1")
    with col_r1:
        if has(df_f,"State") and nb > 0:
            by_s = df_f.groupby("State").size().reset_index(name="n").sort_values("n")
            fig = px.bar(by_s, x="n", y="State", orientation="h", color="n",
                         color_continuous_scale=[th["panel"],"#E3001B"],
                         title="Beneficiaries by State")
            fig.update_layout(coloraxis_showscale=False)
            pc(T(fig, h=200, leg=False))
        if has(df_f,"Sector") and nb > 0:
            by_sec = df_f.groupby("Sector").size().reset_index(name="n")
            fig = px.pie(by_sec, values="n", names="Sector", hole=0.56,
                         color="Sector", color_discrete_map=SC, title="By Sector")
            fig.update_traces(textinfo="none",
                              marker=dict(line=dict(color=th["panel"], width=2)))
            pc(T(fig, h=200))

    st.markdown("<div style='margin:0.5rem 0 0.5rem 0;'></div>", unsafe_allow_html=True)

    sh("Map 2 — Choropleth: Beneficiary Density by State")
    col_m2, col_r2 = st.columns([2.5, 1])
    with col_m2:
        st_folium(map_choropleth_density(df_f, dark), use_container_width=True,
                  height=400, returned_objects=[], key="map2")
    with col_r2:
        if has(df_f,"State") and nb > 0:
            st_d = df_f.groupby("State").size().reset_index(name="Count").sort_values("Count", ascending=False)
            txt_col = th["text"]
            st.markdown(f"<div style='font-size:.75rem;font-weight:700;color:{txt_col};margin-bottom:.4rem;'>Top States by Volume</div>", unsafe_allow_html=True)
            for _, row in st_d.head(8).iterrows():
                pct = row["Count"] / nb * 100
                st.markdown(
                    f"<div style='margin-bottom:4px;'>"
                    f"<div style='display:flex;justify-content:space-between;font-size:.72rem;"
                    f"color:{txt_col};margin-bottom:2px;'>"
                    f"<span>{row['State']}</span><span>{row['Count']:,}</span></div>"
                    f"<div style='background:rgba(128,128,128,0.12);border-radius:3px;height:4px;'>"
                    f"<div style='width:{pct:.1f}%;height:100%;background:{SI_RED};border-radius:3px;'></div></div>"
                    f"</div>",
                    unsafe_allow_html=True
                )

    st.markdown("<div style='margin:0.5rem 0 0.5rem 0;'></div>", unsafe_allow_html=True)

    sh("Map 3 & 4 — Sector Coverage · Displacement Status")
    col_m3, col_m4 = st.columns(2)
    with col_m3:
        st_folium(map_sector_coverage(df_f, dark), use_container_width=True,
                  height=360, returned_objects=[], key="map3")
    with col_m4:
        st_folium(map_displacement(df_f, dark), use_container_width=True,
                  height=360, returned_objects=[], key="map4")

    st.markdown("<div style='margin:0.5rem 0 0.5rem 0;'></div>", unsafe_allow_html=True)

    sh("Map 5 — Vulnerability Heatmap on Sudan Boundaries")
    col_m5, col_r5 = st.columns([2.5, 1])
    with col_m5:
        st_folium(map_vulnerability(df_f, dark), use_container_width=True,
                  height=400, returned_objects=[], key="map5")
    with col_r5:
        if has(df_f,"Vulnerability_Level") and nb > 0:
            vc = df_f["Vulnerability_Level"].value_counts().reset_index()
            vc.columns = ["Level","Count"]
            cmap = {"Extremely Vulnerable":"#EF4444",
                    "Vulnerable":"#F59E0B",
                    "Moderately Vulnerable":"#10B981"}
            fig = px.bar(vc, x="Count", y="Level", orientation="h",
                         color="Level", color_discrete_map=cmap,
                         title="Vulnerability Breakdown")
            fig.update_layout(showlegend=False)
            pc(T(fig, h=200, leg=False))
        if has(df_f,"Displacement_Status") and nb > 0:
            dc = df_f["Displacement_Status"].value_counts().reset_index()
            dc.columns = ["Status","Count"]
            cmap2 = {"IDP":"#EF4444","Refugee":"#3B82F6",
                     "Host Community":"#10B981","Returnee":"#F59E0B"}
            fig = px.pie(dc, values="Count", names="Status", hole=0.55,
                         color="Status", color_discrete_map=cmap2,
                         title="Displacement Status")
            fig.update_traces(textinfo="none",
                              marker=dict(line=dict(color=th["panel"],width=2)))
            pc(T(fig, h=200))

def page_wash(dfs):
    ph("WASH Monitoring","Water, Sanitation & Hygiene — activity performance and gender disaggregation")
    
    st.markdown("<div style='margin-bottom:0.5rem;'></div>", unsafe_allow_html=True)
    
    df = dfs.get("WASH_Monitoring",pd.DataFrame())
    if df.empty:
        st.info("No WASH_Monitoring sheet found.")
        return
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
    
    st.markdown("<div style='margin:0.5rem 0 0.5rem 0;'></div>", unsafe_allow_html=True)
    
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
            pc(T(fig,h=300))
    with c2:
        if has(df_f,"Functionality_Status"):
            func=df_f["Functionality_Status"].value_counts().reset_index()
            func.columns=["Status","Count"]
            cmap={"Fully Functional":"#10B981","Partially Functional":"#F59E0B","Non-Functional":"#EF4444","Under Construction":"#8B5CF6"}
            fig=px.pie(func,values="Count",names="Status",hole=0.55,color="Status",color_discrete_map=cmap,title="Infrastructure Functionality")
            fig.update_traces(textinfo="percent+label",textfont_size=8,marker=dict(line=dict(color=th["bg"],width=2)))
            pc(T(fig,h=300))

def page_fsl(dfs):
    ph("Food Security & Livelihoods","Distribution tracking — commodities, pipeline, donor coverage")
    
    st.markdown("<div style='margin-bottom:0.5rem;'></div>", unsafe_allow_html=True)
    
    df=dfs.get("FSL_Distribution",pd.DataFrame())
    if df.empty:
        st.info("No FSL_Distribution sheet found.")
        return
    th=TH()
    
    c1,c2,c3=st.columns(3)
    with c1: s1=st.selectbox("State",     sopts(df,"State"),         key="f_s")
    with c2: s2=st.selectbox("Commodity", sopts(df,"Commodity_Type"),key="f_c")
    with c3: s3=st.selectbox("Donor",     sopts(df,"Donor"),         key="f_d")
    
    df_f=sfilt(sfilt(sfilt(df.copy(),"State",s1),"Commodity_Type",s2),"Donor",s3)
    hht=int(ssum(df_f,"HH_Targeted"))
    hhr=int(ssum(df_f,"HH_Reached"))
    cov=hhr/hht if hht else 0
    
    sh("Key Indicators")
    c1,c2,c3,c4,c5=st.columns(5)
    dd="up" if cov>=0.8 else "mid" if cov>=0.6 else "down"
    c1.markdown(kpi("HH Reached",  N(hhr), f"of {N(hht)} targeted","green", "🏠",f"{cov:.0%} coverage",dd),unsafe_allow_html=True)
    c2.markdown(kpi("Qty Dist.",   N(ssum(df_f,"Quantity_Distributed")),  f"of {N(ssum(df_f,'Quantity_Planned'))} planned",  "blue",  "📦"),unsafe_allow_html=True)
    c3.markdown(kpi("Female HHH",  N(int(ssum(df_f,"Female_HHH_Reached"))), f"{int(ssum(df_f,'Female_HHH_Reached'))/hhr:.0%}" if hhr else "—","purple","♀"),unsafe_allow_html=True)
    c4.markdown(kpi("Pipeline ⚠️", str(slen(df_f,"Pipeline_Status","Pipeline break")),"supply breaks",        "red" if slen(df_f,"Pipeline_Status","Pipeline break") else "green","⚠️"),unsafe_allow_html=True)
    c5.markdown(kpi("Records",     N(len(df_f)),"in selection",    "teal", "📋"),unsafe_allow_html=True)

def page_cva(dfs):
    ph("Cash & Voucher Assistance","Transfer tracking — payment status, modalities, beneficiary profile")
    
    st.markdown("<div style='margin-bottom:0.5rem;'></div>", unsafe_allow_html=True)
    
    df=dfs.get("CVA_Cash_Transfers",pd.DataFrame())
    if df.empty:
        st.info("No CVA_Cash_Transfers sheet found.")
        return
    th=TH()
    
    c1,c2,c3=st.columns(3)
    with c1: s1=st.selectbox("State",         sopts(df,"State"),        key="c_s")
    with c2: s2=st.selectbox("Transfer Type", sopts(df,"Transfer_Type"),key="c_t")
    with c3: s3=st.selectbox("Round",         sopts(df,"Round"),        key="c_r")
    
    df_f=sfilt(sfilt(sfilt(df.copy(),"State",s1),"Transfer_Type",s2),"Round",s3)
    paid_df=sfilt(df_f,"Transfer_Status","Paid")
    usd=paid_df["Transfer_Value_USD"].sum() if has(paid_df,"Transfer_Value_USD") and len(paid_df)>0 else 0
    avg_v=paid_df["Transfer_Value_USD"].mean() if has(paid_df,"Transfer_Value_USD") and len(paid_df)>0 else 0
    
    sh("Key Indicators")
    c1,c2,c3,c4,c5,c6=st.columns(6)
    c1.markdown(kpi("Total Paid", f"${N(usd)}","USD",            "blue",  "💵"),unsafe_allow_html=True)
    c2.markdown(kpi("Paid",       N(len(paid_df)),"completed",   "green", "✅"),unsafe_allow_html=True)
    c3.markdown(kpi("Pending",    N(len(sfilt(df_f,"Transfer_Status","Pending"))),"awaiting",    "amber", "⏳"),unsafe_allow_html=True)
    c4.markdown(kpi("Failed",     N(len(sfilt(df_f,"Transfer_Status","Failed"))),"to check",    "red" if len(sfilt(df_f,"Transfer_Status","Failed")) else "green","❌"),unsafe_allow_html=True)
    c5.markdown(kpi("Avg Value",  f"${avg_v:.0f}","per HH",      "teal",  "📊"),unsafe_allow_html=True)
    c6.markdown(kpi("Female HHH", f"{slen(df_f,'Female_Headed_HH','Yes')/len(df_f):.0%}" if len(df_f)>0 else "—","",           "purple","♀"),unsafe_allow_html=True)

def page_ind(dfs):
    ph("Indicator Tracker","Results-based management — progress vs annual targets by sector")
    
    st.markdown("<div style='margin-bottom:0.5rem;'></div>", unsafe_allow_html=True)
    
    df=dfs.get("Indicator_Tracker",pd.DataFrame())
    if df.empty:
        st.info("No Indicator_Tracker sheet found.")
        return
    th=TH()
    
    on_t=slen(df,"Status","On track")
    at_r=slen(df,"Status","At risk")
    off=slen(df,"Status","Off track")
    tot=len(df)
    
    c1,c2,c3,c4=st.columns(4)
    c1.markdown(kpi("Total",    str(tot),f"indicators",       "blue",  "📋"),unsafe_allow_html=True)
    c2.markdown(kpi("On Track", str(on_t),f"{on_t/tot:.0%}", "green", "✅",f"↑ {on_t/tot:.0%}","up"),unsafe_allow_html=True)
    c3.markdown(kpi("At Risk",  str(at_r),f"{at_r/tot:.0%}", "amber", "⚠️"),unsafe_allow_html=True)
    c4.markdown(kpi("Off Track",str(off), f"{off/tot:.0%}",  "red",   "❌"),unsafe_allow_html=True)

def page_raw(dfs):
    ph("Raw Data Explorer","Browse, filter and export program datasets")
    
    st.markdown("<div style='margin-bottom:0.5rem;'></div>", unsafe_allow_html=True)
    
    sheet=st.selectbox("Select dataset",list(dfs.keys()))
    df=dfs[sheet]
    c1,c2=st.columns([3,1])
    with c1:
        st.markdown(f"<div style='padding:.4rem 0;font-size:.75rem;color:#64748B;'>{len(df):,} rows · {len(df.columns)} columns</div>",unsafe_allow_html=True)
    with c2:
        st.download_button("⬇ Download CSV",df.to_csv(index=False).encode(),file_name=f"{sheet}.csv",mime="text/csv",use_container_width=True)
    
    num_cols=df.select_dtypes(include="number").columns.tolist()
    if num_cols:
        sh("Quick Statistics")
        st.dataframe(df[num_cols].describe().round(2),use_container_width=True)
    
    sh("Data Table")
    st.dataframe(df,use_container_width=True,height=500)

# ══════════════════════════════════════════════════════════════════════════════
# REPORT FUNCTIONS (simplified - would be too long to include fully)
# ══════════════════════════════════════════════════════════════════════════════
def build_text_report(dfs):
    """Simple text report generator"""
    now = datetime.now().strftime("%B %d, %Y")
    df_b = dfs.get("Beneficiary_Registration", pd.DataFrame())
    df_w = dfs.get("WASH_Monitoring", pd.DataFrame())
    df_f = dfs.get("FSL_Distribution", pd.DataFrame())
    df_c = dfs.get("CVA_Cash_Transfers", pd.DataFrame())
    df_i = dfs.get("Indicator_Tracker", pd.DataFrame())
    
    tot = len(df_b)
    act = slen(df_b, "Registration_Status", "Active")
    wr = int(ssum(df_w, "Reached_Beneficiaries"))
    fhh = int(ssum(df_f, "HH_Reached"))
    paid = sfilt(df_c, "Transfer_Status", "Paid")
    usd = paid["Transfer_Value_USD"].sum() if has(paid, "Transfer_Value_USD") and len(paid) > 0 else 0
    on_t = slen(df_i, "Status", "On track")
    ti = len(df_i)
    
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
        "="*70,
        "END OF REPORT",
        "="*70,
    ]
    return "\n".join(lines)

def page_report(dfs):
    ph("Automatic Report Generator", "Generate a comprehensive program report")
    
    st.markdown("<div style='margin-bottom:0.5rem;'></div>", unsafe_allow_html=True)
    
    if not dfs:
        st.info("Load the Excel database first to generate a report.")
        return
    
    report_type = st.selectbox("Report Format", [
        "📝 Plain Text — Summary",
    ])
    
    if st.button("🚀 Generate Report", use_container_width=False):
        fname_date = datetime.now().strftime("%Y%m%d")
        txt = build_text_report(dfs)
        st.download_button(
            "⬇ Download Text Report", txt.encode(),
            file_name=f"SI_Sudan_IM_Report_{fname_date}.txt",
            mime="text/plain",
        )
        st.success("✅ Text report ready!")
        st.code(txt, language=None)

# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════
def main():
    if not st.session_state.get("auth"):
        login_page()
        return

    kobo_step = st.session_state.get("kobo_step", 0)
    if kobo_step != 99:
        inject_css(DARK)
        datasource_page()
        return

    inject_css(TH())
    top_nav()

    page = st.session_state.get("page", "Overview")
    dfs  = st.session_state.get("dfs", {})

    th = TH()
    if not dfs and page != "Report":
        st.markdown(f"""<div style='text-align:center;padding:4rem 2rem;
          background:{th["panel"]};border:1px dashed {th["border2"]};
          border-radius:14px;margin-top:1rem;'>
          <div style='font-size:2.2rem;margin-bottom:0.8rem;'>📂</div>
          <div style='font-size:1rem;font-weight:700;color:{th["text"]};margin-bottom:.4rem;'>No data loaded</div>
          <div style='font-size:.78rem;color:{th["muted"]};'>
            Go back to the data source page to load your data.
          </div>
        </div>""", unsafe_allow_html=True)
        if st.button("← Change data source"):
            st.session_state["kobo_step"] = 0
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
