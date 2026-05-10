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
        c

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
        c
