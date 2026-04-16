"""
═══════════════════════════════════════════════════════════════════════════════
  OPTIONS TERMINAL  —  Professional Gamma Exposure Dashboard
  Charles Schwab API · Real-time GEX / VEX / CEX / DEX · Dealer Flow Analytics
═══════════════════════════════════════════════════════════════════════════════

  Arquitectura (single-file por compat con Streamlit Cloud):

    1. CONFIG + CSS + THEME
    2. AUTH (OAuth Schwab)
    3. DATA LAYER (API fetch, parse, clean)
    4. MATH CORE (Black-Scholes, helpers)
    5. EXPOSURE ANALYTICS (GEX, VEX, CEX, DEX — convención dealer)
    6. KEY LEVELS (walls, zero-gamma, HVL, max pain)
    7. VOLATILITY ANALYTICS (HV, IV rank, cone, distribución)
    8. CHARTS (profiles profesionales + intraday)
    9. DECISION ENGINE (panel accionable basado en régimen)
   10. RENDER MODULES (GEX module, vol module, chain table)
   11. MAIN DASHBOARD
   12. ENTRY POINT

  Matemática (convención SqueezeMetrics / GEXbot):

    GEX(k) = Γ(k) × OI(k) × 100 × S² × 0.01 × sign(k)
    VEX(k) = V(k) × OI(k) × 100 × S   × 0.01 × sign(k)
    CEX(k) = Θ_Δ(k) × OI(k) × 100 × S ×        sign(k)
    DEX(k) = Δ(k) × OI(k) × 100 × S

    sign(call)=+1, sign(put)=−1  (dealer long calls, short puts)

    Unidades:
      GEX → $ delta que el dealer debe hedgear por cada 1% move
      VEX → $ delta que el dealer debe hedgear por cada 1 punto de IV
      CEX → $ delta que el dealer pierde/gana por día calendario
"""

import json
import base64
import datetime
import time
import warnings
from datetime import timezone
from urllib.parse import urlencode, urlparse, parse_qs

import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
import pytz
from scipy.stats import norm

warnings.filterwarnings("ignore")

_CDMX_TZ = pytz.timezone("America/Mexico_City")
_UTC     = timezone.utc


def _utcnow():
    return datetime.datetime.now(_UTC)


st.set_page_config(
    page_title="Options Terminal",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ═══════════════════════════════════════════════════════════════════════════════
#  1. BLOOMBERG DARK THEME CSS
# ═══════════════════════════════════════════════════════════════════════════════
CSS = """
<style>
html, body, [data-testid="stApp"], .main, .block-container {
    background-color: #080810 !important;
    color: #c8c8d8 !important;
}
.block-container { padding: 2rem 1.6rem 2rem !important; max-width: 100% !important; }

input, textarea, select,
[data-testid="stTextInput"] input,
[data-testid="stSelectbox"] div[data-baseweb="select"] {
    background: #12121e !important; color: #e0e0f0 !important;
    border-color: #2a2a3e !important; border-radius: 4px !important;
}
[data-testid="stTextInput"] label,
[data-testid="stSelectbox"] label { color: #6868a0 !important; font-size: 0.72rem !important; }

[data-testid="stButton"] button {
    background: transparent !important; border: 1px solid #2a2a3e !important;
    color: #c0c0d8 !important; border-radius: 4px !important;
    font-size: 0.78rem !important; font-family: 'JetBrains Mono', monospace !important;
    transition: all 0.15s;
}
[data-testid="stButton"] button:hover {
    border-color: #f97316 !important; color: #f97316 !important;
    background: rgba(249,115,22,0.08) !important;
}
button[kind="primary"] {
    background: #f97316 !important; border-color: #f97316 !important;
    color: #000 !important; font-weight: 700 !important;
}
button[kind="primary"]:hover { background: #fb923c !important; color: #000 !important; }
[data-testid="stLinkButton"] a {
    background: rgba(249,115,22,0.12) !important; border: 1px solid #f97316 !important;
    color: #f97316 !important; border-radius: 4px !important;
    padding: 8px 18px !important; font-size: 0.82rem !important;
    text-decoration: none !important; display: block !important; text-align: center !important;
}

[data-testid="stMetric"] {
    background: #0e0e1a !important; border: 1px solid #1e1e30 !important;
    border-radius: 4px !important; padding: 10px 14px !important;
}
[data-testid="stMetricLabel"] {
    font-size: 0.62rem !important; text-transform: uppercase; letter-spacing: 0.1em;
    font-weight: 600 !important; color: #606080 !important;
}
[data-testid="stMetricValue"] {
    font-size: 1.25rem !important; font-weight: 700 !important;
    color: #e8e8f8 !important;
    font-family: 'JetBrains Mono', 'Courier New', monospace !important;
}
[data-testid="stMetricDelta"] { font-size: 0.72rem !important; font-family: 'JetBrains Mono', monospace !important; }

.stTabs [data-baseweb="tab-list"] {
    background: #0e0e1a !important; border-radius: 4px !important;
    gap: 2px !important; padding: 2px !important;
    border: 1px solid #1e1e30 !important;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 3px !important; padding: 5px 18px !important;
    color: #606080 !important; font-size: 0.78rem !important;
    font-weight: 500 !important; font-family: 'JetBrains Mono', monospace !important;
}
.stTabs [aria-selected="true"] { background: #1e1e30 !important; color: #f97316 !important; }

.stCaption p, [data-testid="stCaptionContainer"] p { color: #505070 !important; font-size: 0.72rem !important; }
p, .stMarkdown p { color: #a0a0c0 !important; }
h1, h2, h3 { color: #e0e0f0 !important; }

[data-testid="stSidebar"] { background: #0a0a14 !important; border-right: 1px solid #1a1a2a !important; }
[data-testid="stSidebarContent"] * { color: #a0a0c0 !important; }
[data-testid="stSlider"] div { color: #a0a0c0 !important; }

[data-testid="stExpander"] {
    background: #0e0e1a !important; border: 1px solid #1e1e30 !important; border-radius: 4px !important;
}
[data-testid="stExpander"] summary { color: #8080a0 !important; }

.bb-header {
    font-family: 'JetBrains Mono', monospace; font-size: 0.68rem; font-weight: 700;
    text-transform: uppercase; letter-spacing: 0.12em;
    color: #f97316; border-left: 3px solid #f97316;
    padding-left: 10px; margin: 1.4rem 0 0.8rem;
}
.bb-divider { border: none; border-top: 1px solid #1a1a2a; margin: 1.2rem 0; }

.conn-logo  { font-size: 2.5rem; display: block; text-align: center; margin-bottom: 0.5rem; }
.conn-title { font-size: 1.5rem; font-weight: 800; color: #f97316; text-align: center;
              font-family: 'JetBrains Mono', monospace; margin: 0 0 0.2rem; letter-spacing: 0.05em; }
.conn-sub   { font-size: 0.82rem; color: #606080; text-align: center; margin: 0 0 2rem; }
.step-card  { background: #0e0e1a; border: 1px solid #1e1e30; border-radius: 6px;
              padding: 1.1rem 1.3rem; margin-bottom: 0.9rem; }
.step-num   { display: inline-flex; align-items: center; justify-content: center;
              background: #f97316; color: #000; border-radius: 50%;
              width: 22px; height: 22px; font-size: 0.7rem; font-weight: 800;
              margin-right: 8px; flex-shrink: 0; }
.step-label { font-size: 0.82rem; color: #9090b0; }

.chain-wrap { overflow-x: auto; border: 1px solid #1a1a2a; border-radius: 4px; }
.chain {
    width: 100%; border-collapse: collapse;
    font-size: 0.75rem; font-family: 'JetBrains Mono', 'Courier New', monospace;
}
.chain thead th {
    background: #0d0d1a; color: #505070; font-size: 0.62rem; font-weight: 700;
    text-transform: uppercase; letter-spacing: 0.08em;
    padding: 7px 10px; text-align: right; white-space: nowrap;
    border-bottom: 1px solid #1a1a2a;
}
.chain thead th.lft { text-align: left; }
.chain thead th.ctr { text-align: center; }
.chain tbody td {
    padding: 4px 10px; text-align: right; color: #9090b0;
    border-bottom: 1px solid #111120; white-space: nowrap;
    font-variant-numeric: tabular-nums;
}
.chain tbody td.lft { text-align: left; }
.chain tbody td.ctr { text-align: center; }
.chain tbody tr:last-child td { border-bottom: none; }
.chain tbody tr:hover td { background: #111120 !important; }
.itm-c td { background: rgba(34,197,94,0.04) !important; }
.itm-p td { background: rgba(244,63,94,0.04) !important; }
.atm-row td { background: rgba(249,115,22,0.07) !important; border-top: 1px solid rgba(249,115,22,0.3) !important; border-bottom: 1px solid rgba(249,115,22,0.3) !important; }
.strike     { font-weight: 700; color: #d0d0e8; }
.atm-strike { color: #f97316 !important; font-weight: 800; }
.pos { color: #22c55e !important; }
.neg { color: #f43f5e !important; }
.neu { color: #6060a0; }
.hi  { color: #e0e0f8 !important; font-weight: 600; }
.call-hdr { background: rgba(34,197,94,0.08) !important; color: #22c55e !important; font-weight: 700 !important; }
.put-hdr  { background: rgba(244,63,94,0.08) !important; color: #f43f5e !important; font-weight: 700 !important; }
.mid-hdr  { background: #0d0d1a !important; color: #f97316 !important; font-weight: 800 !important; }

.badge { display: inline-block; padding: 2px 8px; border-radius: 3px;
         font-size: 0.68rem; font-weight: 700; font-family: 'JetBrains Mono', monospace; }
.badge-green  { background: rgba(34,197,94,0.15); color: #22c55e; border: 1px solid rgba(34,197,94,0.3); }
.badge-red    { background: rgba(244,63,94,0.15); color: #f43f5e; border: 1px solid rgba(244,63,94,0.3); }
.badge-orange { background: rgba(249,115,22,0.15); color: #f97316; border: 1px solid rgba(249,115,22,0.3); }
.badge-gray   { background: rgba(100,100,150,0.15); color: #8080a0; border: 1px solid rgba(100,100,150,0.3); }

.stat-row { display:flex; gap:24px; align-items:baseline; margin-bottom:0.5rem; }
.stat-label { font-size:0.65rem; color:#505070; text-transform:uppercase; letter-spacing:0.08em; font-family:'JetBrains Mono',monospace; }
.stat-val   { font-size:1.1rem; font-weight:700; color:#e0e0f8; font-family:'JetBrains Mono',monospace; margin-top:2px; }

/* KPI panel (used by GEX header + Decision engine) */
.kpi-panel { background:#0e0e1a; border:1px solid #1e1e30; border-radius:6px;
             padding:0.9rem 1.4rem; display:flex; gap:2rem; align-items:center;
             flex-wrap:wrap; margin-bottom:0.8rem; }
.kpi-item { min-width:110px; }
.kpi-lbl  { font-size:0.58rem; color:#505070; font-family:'JetBrains Mono',monospace;
            text-transform:uppercase; letter-spacing:0.1em; margin-bottom:2px; }
.kpi-val  { font-size:1.05rem; font-weight:800; font-family:'JetBrains Mono',monospace; color:#e0e0f0; }
.kpi-sub  { font-size:0.6rem; color:#505070; font-family:'JetBrains Mono',monospace; }

/* Decision card */
.decision-card {
    background: linear-gradient(135deg, #0e0e1a 0%, #12121e 100%);
    border: 1px solid #2a2a3e; border-radius: 6px;
    padding: 1rem 1.3rem; margin: 0.8rem 0;
}
.decision-title {
    font-family: 'JetBrains Mono', monospace; font-size: 0.75rem;
    font-weight: 800; letter-spacing: 0.1em; text-transform: uppercase;
    margin-bottom: 0.6rem;
}
.decision-body {
    font-size: 0.82rem; color: #c0c0d8; line-height: 1.6;
    font-family: 'Inter', -apple-system, sans-serif;
}
.decision-body b { color: #e8e8f8; }
.decision-body code { background: #1a1a2a; color: #f97316; padding: 1px 6px;
                      border-radius: 3px; font-family: 'JetBrains Mono', monospace;
                      font-size: 0.78rem; }

.footer { text-align:center; font-size:0.65rem; color:#2a2a3a; margin-top:2rem;
          font-family:'JetBrains Mono',monospace; }
</style>
"""

# ═══════════════════════════════════════════════════════════════════════════════
#  PLOTLY THEME — Bloomberg dark
# ═══════════════════════════════════════════════════════════════════════════════
_BG_DARK   = "#0b0b14"
_BG_PLOT   = "#0e0e1a"
_GRID_CLR  = "rgba(255,255,255,0.04)"
_ORANGE    = "#f97316"
_GREEN     = "#22c55e"
_RED       = "#f43f5e"
_BLUE      = "#3b82f6"
_PURPLE    = "#a855f7"
_CYAN      = "#06b6d4"
_FONT_MONO = "JetBrains Mono, Courier New, monospace"

_BASE = dict(
    plot_bgcolor=_BG_PLOT, paper_bgcolor=_BG_DARK,
    font=dict(size=11, family=_FONT_MONO, color="#7070a0"),
    margin=dict(l=55, r=24, t=42, b=36),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                font=dict(size=10, color="#9090b0"), bgcolor="rgba(0,0,0,0)"),
    hoverlabel=dict(bgcolor="#1a1a2a", font_size=11, font_family=_FONT_MONO,
                    bordercolor="#3a3a4a", font_color="#e0e0f0"),
)
_AX = dict(
    showgrid=True, gridcolor=_GRID_CLR,
    linecolor="#1a1a2a", linewidth=1, showline=True,
    tickfont=dict(size=10, family=_FONT_MONO, color="#606080"),
    title_font=dict(size=10, color="#606080"),
)
_AX_ZERO   = dict(**_AX, zeroline=True, zerolinecolor="rgba(255,255,255,0.08)", zerolinewidth=1)
_AX_NOZERO = dict(**_AX, zeroline=False)


def _vline(fig, x, row=None, col=None, color=None, label=True, text=None):
    clr = color or "rgba(249,115,22,0.5)"
    kw = dict(x=x, line_dash="dot", line_color=clr, line_width=1.2)
    if label:
        kw.update(annotation_text=text or f"  ${x:.0f}",
                  annotation_font_size=9, annotation_font_color=clr)
    if row:
        kw.update(row=row, col=col)
    fig.add_vline(**kw)


def _hline(fig, y, color, label, width=1, dash="dot", row=None, col=None):
    kw = dict(y=y, line_dash=dash, line_color=color, line_width=width,
              annotation_text=f"  {label}",
              annotation_font_size=9, annotation_font_color=color,
              annotation_position="top right")
    if row:
        kw.update(row=row, col=col)
    fig.add_hline(**kw)


# ═══════════════════════════════════════════════════════════════════════════════
#  2. OAUTH — Charles Schwab (manual flow, Streamlit-Cloud compatible)
# ═══════════════════════════════════════════════════════════════════════════════
_AUTH_URL  = "https://api.schwabapi.com/v1/oauth/authorize"
_TOKEN_URL = "https://api.schwabapi.com/v1/oauth/token"
_BASE_URL  = "https://api.schwabapi.com"


def build_auth_url(app_key, callback_url):
    return f"{_AUTH_URL}?{urlencode({'client_id': app_key, 'redirect_uri': callback_url})}"


def _refresh_access_token():
    tok = st.session_state.get("tokens", {})
    if not tok:
        return
    expiry = tok.get("expiry")
    if expiry is None:
        expiry = datetime.datetime.min.replace(tzinfo=_UTC)
    elif expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=_UTC)
    if _utcnow() >= expiry - datetime.timedelta(seconds=60):
        try:
            creds = base64.b64encode(
                f"{st.session_state['app_key']}:{st.session_state['app_secret']}".encode()
            ).decode()
            r = requests.post(_TOKEN_URL,
                headers={"Authorization": f"Basic {creds}",
                         "Content-Type": "application/x-www-form-urlencoded"},
                data={"grant_type": "refresh_token",
                      "refresh_token": tok["refresh_token"]}, timeout=15)
            r.raise_for_status()
            new = r.json()
            tok.update({
                "access_token":  new["access_token"],
                "refresh_token": new.get("refresh_token", tok["refresh_token"]),
                "expiry": _utcnow() + datetime.timedelta(seconds=new.get("expires_in", 1800)),
            })
            st.session_state["tokens"] = tok
        except Exception as e:
            st.error(f"Token refresh failed: {e}")
            st.session_state.pop("tokens", None)
            st.session_state.pop("connected", None)
            st.rerun()


def api_get(path, params=None):
    _refresh_access_token()
    tok = st.session_state.get("tokens", {})
    if not tok:
        st.error("Sin tokens. Reconéctate.")
        st.stop()
    r = requests.get(f"{_BASE_URL}{path}",
        headers={"Authorization": f"Bearer {tok['access_token']}"},
        params={k: v for k, v in (params or {}).items() if v is not None},
        timeout=20)
    return r


def _secret(key, default=None):
    try:
        return st.secrets[key]
    except Exception:
        return default


def try_auto_connect():
    """Silent connect using st.secrets.APP_KEY / APP_SECRET / REFRESH_TOKEN."""
    if st.session_state.get("connected"):
        return True
    app_key       = _secret("APP_KEY")
    app_secret    = _secret("APP_SECRET")
    refresh_token = _secret("REFRESH_TOKEN")
    if not all([app_key, app_secret, refresh_token]):
        return False
    try:
        creds = base64.b64encode(f"{app_key}:{app_secret}".encode()).decode()
        r = requests.post(_TOKEN_URL,
            headers={"Authorization": f"Basic {creds}",
                     "Content-Type": "application/x-www-form-urlencoded"},
            data={"grant_type": "refresh_token", "refresh_token": refresh_token},
            timeout=15)
        r.raise_for_status()
        tok = r.json()
        st.session_state["app_key"]      = app_key
        st.session_state["app_secret"]   = app_secret
        st.session_state["callback_url"] = _secret("CALLBACK_URL", "https://127.0.0.1")
        st.session_state["tokens"] = {
            "access_token":  tok["access_token"],
            "refresh_token": tok.get("refresh_token", refresh_token),
            "expiry": _utcnow() + datetime.timedelta(seconds=tok.get("expires_in", 1800)),
        }
        st.session_state["connected"] = True
        return True
    except Exception:
        return False


def show_connect_screen():
    st.markdown(CSS, unsafe_allow_html=True)
    st.markdown("<br><br>", unsafe_allow_html=True)
    _, col, _ = st.columns([1, 1.2, 1])
    has_secrets = bool(_secret("APP_KEY") and _secret("APP_SECRET"))
    is_expired  = has_secrets and not st.session_state.get("connected")
    with col:
        if is_expired:
            st.markdown("""
            <span class="conn-logo">⚠</span>
            <h1 class="conn-title" style="color:#f43f5e">TOKEN EXPIRADO</h1>
            <p class="conn-sub">Tu refresh token expiró (válido 7 días). Re-autoriza una vez y copia el nuevo token a Secrets.</p>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <span class="conn-logo">▤</span>
            <h1 class="conn-title">OPTIONS TERMINAL</h1>
            <p class="conn-sub">Primera configuración — Solo necesitas hacer esto una vez.</p>
            """, unsafe_allow_html=True)

        if not has_secrets:
            st.markdown('<div class="step-card">', unsafe_allow_html=True)
            st.markdown('<span class="step-num">0</span><span class="step-label"> Credenciales (primera vez):</span>', unsafe_allow_html=True)
            app_key    = st.text_input("APP KEY",    placeholder="developer.schwab.com → tu app")
            app_secret = st.text_input("APP SECRET", type="password", placeholder="••••••••••")
            callback   = st.text_input("CALLBACK URL", value="https://127.0.0.1",
                help="Streamlit Cloud → URL de tu app  |  Local → https://127.0.0.1")
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            app_key    = _secret("APP_KEY")
            app_secret = _secret("APP_SECRET")
            callback   = _secret("CALLBACK_URL", "https://127.0.0.1")
            st.info(f"✓ Credenciales cargadas desde Secrets. Callback: `{callback}`", icon="🔑")

        if not has_secrets:
            show_oauth = st.button("SIGUIENTE → GENERAR ENLACE", type="primary", use_container_width=True)
            if show_oauth:
                if not app_key or not app_secret:
                    st.error("Completa App Key y App Secret.")
                    return
                st.session_state.update({
                    "app_key": app_key.strip(), "app_secret": app_secret.strip(),
                    "callback_url": callback.strip(), "oauth_pending": True,
                })
                st.rerun()
            if "oauth_pending" not in st.session_state:
                return
        else:
            st.session_state["app_key"]      = app_key
            st.session_state["app_secret"]   = app_secret
            st.session_state["callback_url"] = callback

        auth_url = build_auth_url(st.session_state["app_key"], st.session_state["callback_url"])
        st.markdown('<div class="step-card">', unsafe_allow_html=True)
        st.markdown('<span class="step-num">1</span><span class="step-label"> Autoriza en Schwab:</span>', unsafe_allow_html=True)
        st.link_button("🔐  AUTORIZAR EN SCHWAB", auth_url, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

        callback = st.session_state.get("callback_url", "")
        is_streamlit_cloud = "streamlit.app" in callback or "streamlit.io" in callback
        if is_streamlit_cloud:
            st.info("✅ **Flujo automático activo.** Al autorizar en Schwab serás redirigido y el código se captura solo.", icon="🚀")
        else:
            st.warning("⚡ **Actúa rápido** — el código expira en ~30 segundos.", icon="⏱")
            st.markdown('<div class="step-card">', unsafe_allow_html=True)
            st.markdown('<span class="step-num">2</span><span class="step-label"> Pega la URL de redirección:</span>', unsafe_allow_html=True)
            redirect_url = st.text_input("redirect", label_visibility="collapsed",
                placeholder="https://127.0.0.1?code=Xxxx&session=...")
            st.markdown('</div>', unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            with c1:
                if st.button("← Cancelar", use_container_width=True):
                    for k in ["oauth_pending","app_key","app_secret","callback_url"]:
                        st.session_state.pop(k, None)
                    st.rerun()
            with c2:
                if st.button("CONECTAR →", type="primary", use_container_width=True):
                    if not redirect_url:
                        st.error("Pega la URL de redirección.")
                        return
                    _finish_oauth(redirect_url.strip())


def _finish_oauth(redirect_url):
    try:
        parsed   = urlparse(redirect_url.strip())
        params   = parse_qs(parsed.query)
        code     = params.get("code", [None])[0]
        callback = st.session_state.get("callback_url", "https://127.0.0.1")
        if not code:
            st.error("No se encontró `?code=` en la URL.")
            return
        with st.spinner("Intercambiando código…"):
            creds = base64.b64encode(
                f"{st.session_state['app_key']}:{st.session_state['app_secret']}".encode()
            ).decode()
            r = requests.post(_TOKEN_URL,
                headers={"Authorization": f"Basic {creds}",
                         "Content-Type": "application/x-www-form-urlencoded"},
                data={"grant_type": "authorization_code",
                      "code": code, "redirect_uri": callback}, timeout=15)
        if not r.ok:
            st.error(f"❌ Schwab HTTP {r.status_code}: `{r.text}`")
            if "invalid_grant" in r.text:
                st.warning("**Código expirado** (~30s de vida). Reintenta.")
            return
        tok = r.json()
        refresh_token = tok["refresh_token"]
        st.session_state["tokens"] = {
            "access_token":  tok["access_token"],
            "refresh_token": refresh_token,
            "expiry": _utcnow() + datetime.timedelta(seconds=tok.get("expires_in", 1800)),
        }
        st.session_state["connected"]     = True
        st.session_state["oauth_pending"] = False
        st.success("✅ Autenticado correctamente.")
        st.code(f'REFRESH_TOKEN = "{refresh_token}"', language="toml")
        st.caption("Guarda este token en Streamlit Secrets para auto-connect.")
        if st.button("ENTRAR AL DASHBOARD →", type="primary", use_container_width=True):
            st.rerun()
    except Exception as e:
        st.error(f"❌ Error inesperado: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
#  3. DATA LAYER — fetch / parse / clean
# ═══════════════════════════════════════════════════════════════════════════════
def fetch_chain(symbol, strike_count, from_date, to_date):
    try:
        r = api_get("/marketdata/v1/chains", params={
            "symbol": symbol, "contractType": "ALL",
            "strikeCount": strike_count, "includeUnderlyingQuote": "true",
            "fromDate": from_date, "toDate": to_date,
        })
    except Exception as e:
        return None, str(e)
    return (r.json(), None) if r.status_code == 200 else (None, f"HTTP {r.status_code}: {r.text[:300]}")


def fetch_price_history(symbol: str, period: int = 1, period_type: str = "year") -> tuple:
    try:
        r = api_get("/marketdata/v1/pricehistory", params={
            "symbol": symbol, "periodType": period_type, "period": period,
            "frequencyType": "daily", "frequency": 1,
            "needExtendedHoursData": "false",
        })
        if r.status_code != 200:
            return pd.DataFrame(), f"HTTP {r.status_code}: {r.text[:200]}"
        data = r.json()
        if data.get("empty", False):
            return pd.DataFrame(), f"Símbolo '{symbol}' no encontrado."
        candles = data.get("candles", [])
        if not candles:
            return pd.DataFrame(), "Sin velas en respuesta."
        df = pd.DataFrame(candles)
        df["date"] = pd.to_datetime(df["datetime"], unit="ms")
        df = df[["date","open","high","low","close","volume"]].copy()
        return df.sort_values("date").reset_index(drop=True), ""
    except Exception as e:
        return pd.DataFrame(), str(e)


def fetch_intraday(symbol: str, freq_min: int = 1, days: int = 1) -> tuple:
    try:
        r = api_get("/marketdata/v1/pricehistory", params={
            "symbol":                symbol,
            "periodType":            "day",
            "period":                str(min(max(int(days), 1), 10)),
            "frequencyType":         "minute",
            "frequency":             str(int(freq_min)),
            "needExtendedHoursData": "false",
        })
        if r.status_code != 200:
            try:    err_detail = r.json()
            except: err_detail = r.text[:300]
            return pd.DataFrame(), f"HTTP {r.status_code}: {err_detail}"
        data = r.json()
        if data.get("empty", False):
            return pd.DataFrame(), f"Sin datos intraday para '{symbol}'."
        candles = data.get("candles", [])
        if not candles:
            return pd.DataFrame(), "La API devolvió 0 velas. Mercado cerrado o sin datos."
        df = pd.DataFrame(candles)
        df["date"] = pd.to_datetime(df["datetime"], unit="ms", utc=True)
        df = df[["date","open","high","low","close","volume"]].copy()
        df = df.sort_values("date").reset_index(drop=True)
        df["_d"] = df["date"].dt.tz_convert(_CDMX_TZ).dt.date
        all_days = sorted(df["_d"].unique())
        keep     = set(all_days[-max(1, days):])
        df = df[df["_d"].isin(keep)].drop(columns=["_d"]).reset_index(drop=True)
        return df, ""
    except Exception as exc:
        return pd.DataFrame(), str(exc)


def parse_chain(data):
    rows_c, rows_p = [], []
    for rows, key in [(rows_c, "callExpDateMap"), (rows_p, "putExpDateMap")]:
        for exp_key, strikes in data.get(key, {}).items():
            exp, dte = exp_key.split(":")
            for opts in strikes.values():
                for o in opts:
                    o["_exp"] = exp
                    o["_dte"] = int(dte)
                    rows.append(o)
    c = pd.DataFrame(rows_c) if rows_c else pd.DataFrame()
    p = pd.DataFrame(rows_p) if rows_p else pd.DataFrame()
    return c, p, data.get("underlying", {})


_REMAP = {
    "strikePrice": "Strike", "_exp": "Expiry", "_dte": "DTE",
    "bid": "Bid", "ask": "Ask", "mark": "Mark", "last": "Last",
    "totalVolume": "Volume", "openInterest": "OI",
    "volatility": "IV%",
    "impliedVolatility": "IV%_alt",
    "delta": "Delta", "gamma": "Gamma",
    "theta": "Theta", "vega": "Vega", "rho": "Rho",
    "inTheMoney": "ITM", "theoreticalOptionValue": "Theo",
}


def clean(df):
    if df.empty:
        return df
    df = df.copy()
    if "volatility" not in df.columns and "impliedVolatility" in df.columns:
        df["volatility"] = df["impliedVolatility"]
    elif "volatility" not in df.columns:
        df["volatility"] = float("nan")
    cols = {k: v for k, v in _REMAP.items() if k in df.columns}
    df = df[list(cols)].rename(columns=cols).copy()
    df.drop(columns=["IV%_alt"], errors="ignore", inplace=True)
    for c, d in [("Bid",2), ("Ask",2), ("Mark",2), ("Last",2), ("Theo",2),
                 ("Delta",3), ("Theta",3), ("Gamma",4), ("Vega",4), ("Rho",4),
                 ("Strike",2)]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").round(d)
    if "IV%" in df.columns:
        df["IV%"] = (pd.to_numeric(df["IV%"], errors="coerce") * 100).round(2)
    if "OI" in df.columns:
        df["OI"] = pd.to_numeric(df["OI"], errors="coerce").fillna(0).astype(int)
    if "Volume" in df.columns:
        df["Volume"] = pd.to_numeric(df["Volume"], errors="coerce").fillna(0).astype(int)
    if "DTE" in df.columns:
        df["DTE"] = pd.to_numeric(df["DTE"], errors="coerce").fillna(0).astype(int)
    if "ITM" in df.columns:
        df["ITM"] = df["ITM"].astype(bool)
    return df


def by_exp(df, exp):
    return df[df["Expiry"] == exp].copy() if not df.empty and "Expiry" in df.columns else df


def filter_chain_for_exposure(df: pd.DataFrame, max_dte: int = 60,
                              min_oi: int = 0) -> pd.DataFrame:
    """
    Filtra la cadena para el cálculo de exposures:
      - Excluye opciones con OI <= min_oi (ruido, LEAPS ilíquidas)
      - Excluye DTE > max_dte (LEAPS con gamma residual irrelevante para dealer flow)
      - Requiere Gamma válido (no-NaN)
    """
    if df.empty:
        return df
    out = df.copy()
    required = ["Strike", "OI", "Gamma"]
    missing = [c for c in required if c not in out.columns]
    if missing:
        return pd.DataFrame()
    out = out[out["OI"] > min_oi]
    if "DTE" in out.columns:
        out = out[out["DTE"] <= max_dte]
    out = out.dropna(subset=["Strike", "Gamma"])
    out = out[out["Gamma"] > 0]
    return out.reset_index(drop=True)


# ═══════════════════════════════════════════════════════════════════════════════
#  4. MATH CORE — Black-Scholes & helpers (VECTORIZED)
# ═══════════════════════════════════════════════════════════════════════════════
def _get_rf_rate() -> float:
    try:
        return float(st.secrets.get("RF_RATE", 0.045))
    except Exception:
        return 0.045


def bs_d1(S, K, T, sigma, r):
    """Vectorized d1. Inputs can be arrays; invalid entries return NaN."""
    S = np.asarray(S, dtype=float)
    K = np.asarray(K, dtype=float)
    T = np.asarray(T, dtype=float)
    sigma = np.asarray(sigma, dtype=float)
    with np.errstate(divide="ignore", invalid="ignore"):
        d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    d1 = np.where((T > 0) & (sigma > 0) & (S > 0) & (K > 0), d1, np.nan)
    return d1


def bs_d2(d1, sigma, T):
    sigma = np.asarray(sigma, dtype=float)
    T     = np.asarray(T, dtype=float)
    return d1 - sigma * np.sqrt(T)


def bs_vanna_vec(S, K, T, sigma, r):
    """
    Vanna = ∂Δ/∂σ = -φ(d1) · d2 / σ   (per share)
    Vectorized. Input any shape. Returns same shape.
    Same for calls and puts (put-call parity, q=0).
    """
    d1 = bs_d1(S, K, T, sigma, r)
    d2 = bs_d2(d1, sigma, T)
    sigma = np.asarray(sigma, dtype=float)
    with np.errstate(divide="ignore", invalid="ignore"):
        vanna = -norm.pdf(d1) * d2 / sigma
    return np.where(np.isfinite(vanna), vanna, 0.0)


def bs_charm_vec(S, K, T, sigma, r):
    """
    Charm = ∂Δ/∂t  (per calendar day, q=0)
    For a call: Charm_year = -φ(d1) · [2rT - d2·σ√T] / (2T·σ√T)
    Divided by 365 to get per-day.
    Same for calls and puts (put-call parity, q=0).
    """
    d1 = bs_d1(S, K, T, sigma, r)
    d2 = bs_d2(d1, sigma, T)
    sigma = np.asarray(sigma, dtype=float)
    T     = np.asarray(T, dtype=float)
    with np.errstate(divide="ignore", invalid="ignore"):
        num = -norm.pdf(d1) * (2 * r * T - d2 * sigma * np.sqrt(T))
        den = 2 * T * sigma * np.sqrt(T)
        charm_year = num / den
    charm_day = charm_year / 365.0
    return np.where(np.isfinite(charm_day), charm_day, 0.0)


# ═══════════════════════════════════════════════════════════════════════════════
#  5. EXPOSURE ANALYTICS — convención SqueezeMetrics / GEXbot
#     Dealer long calls / short puts → call sign +1, put sign −1
# ═══════════════════════════════════════════════════════════════════════════════
#
#  Fórmulas:
#
#    GEX(k) = Γ(k) × OI(k) × 100 × S² × 0.01 × sign(k)
#        → $ de gamma que el dealer debe hedgear por cada 1% move del spot
#
#    VEX(k) = V(k) × OI(k) × 100 × S  × 0.01 × sign(k)
#        → $ de delta que el dealer debe ajustar por cada +1 pto de IV (0.01)
#
#    CEX(k) = Charm(k) × OI(k) × 100 × S × sign(k)
#        → $ de delta que decae en 1 día calendario
#
#    DEX(k) = Δ(k) × OI(k) × 100 × S      (directional bias, sin sign flip
#                                           porque el delta del put ya es negativo)
# ═══════════════════════════════════════════════════════════════════════════════

def _sign_df(df, side):
    """side ∈ {'call','put'}. Returns +1/-1 array aligned with df."""
    s = +1.0 if side == "call" else -1.0
    return np.full(len(df), s, dtype=float)


def compute_gex_profile(calls: pd.DataFrame, puts: pd.DataFrame,
                        spot: float, max_dte: int = 60,
                        min_oi: int = 0) -> tuple:
    """
    Perfil GEX por strike + agregados.
    Convención: dealer long calls, short puts → GEX calls +, puts −.
    Unidad: $ delta-change que el dealer debe hedgear por 1% move.

    Returns:
      df: DataFrame con Strike, C_GEX, P_GEX, Net_GEX, Abs_GEX, CumGEX
      summary: dict con regime, totals, flip, walls
    """
    if spot <= 0:
        return pd.DataFrame(), {}

    c = filter_chain_for_exposure(calls, max_dte=max_dte, min_oi=min_oi)
    p = filter_chain_for_exposure(puts,  max_dte=max_dte, min_oi=min_oi)

    if c.empty and p.empty:
        return pd.DataFrame(), {}

    SCALE = 100.0 * spot * spot * 0.01   # contract multiplier × S² × 1%

    # Vectorized per-row contribution
    c_gex = (c["Gamma"].to_numpy() * c["OI"].to_numpy() * SCALE * (+1.0)) if not c.empty else np.array([])
    p_gex = (p["Gamma"].to_numpy() * p["OI"].to_numpy() * SCALE * (-1.0)) if not p.empty else np.array([])

    # Group by strike
    c_g = (pd.DataFrame({"Strike": c["Strike"].to_numpy(), "C_GEX": c_gex})
           .groupby("Strike", as_index=False)["C_GEX"].sum()
           if not c.empty else pd.DataFrame(columns=["Strike", "C_GEX"]))
    p_g = (pd.DataFrame({"Strike": p["Strike"].to_numpy(), "P_GEX": p_gex})
           .groupby("Strike", as_index=False)["P_GEX"].sum()
           if not p.empty else pd.DataFrame(columns=["Strike", "P_GEX"]))

    df = c_g.merge(p_g, on="Strike", how="outer").fillna(0.0).sort_values("Strike")
    df["Net_GEX"] = df["C_GEX"] + df["P_GEX"]
    df["Abs_GEX"] = df["Net_GEX"].abs()
    df["CumGEX"]  = df["Net_GEX"].cumsum()
    df = df.reset_index(drop=True)

    total     = float(df["Net_GEX"].sum())
    call_tot  = float(df["C_GEX"].sum())
    put_tot   = float(df["P_GEX"].sum())

    # Zero-Gamma Level (gamma flip): strike where CumGEX crosses zero
    flip = None
    cum = df["CumGEX"].to_numpy()
    stk = df["Strike"].to_numpy()
    for i in range(1, len(cum)):
        if cum[i-1] * cum[i] < 0:
            w = abs(cum[i-1]) / (abs(cum[i-1]) + abs(cum[i]) + 1e-12)
            flip = float(stk[i-1] + (stk[i] - stk[i-1]) * w)
            break

    # Walls (strikes con mayor exposure)
    pos = df[df["Net_GEX"] > 0]
    neg = df[df["Net_GEX"] < 0]
    call_wall = float(pos.loc[pos["Net_GEX"].idxmax(), "Strike"]) if not pos.empty else None
    put_wall  = float(neg.loc[neg["Net_GEX"].idxmin(), "Strike"]) if not neg.empty else None

    # HVL — High Volume Level (strike con mayor |Net_GEX|, atractor dealer)
    hvl = float(df.loc[df["Abs_GEX"].idxmax(), "Strike"]) if not df.empty else None

    regime = "POSITIVE" if total > 0 else ("NEGATIVE" if total < 0 else "NEUTRAL")
    flip_pct = ((flip - spot) / spot * 100) if flip else None

    summary = dict(
        regime=regime,
        total_gex=total,
        call_gex=call_tot, put_gex=put_tot,
        gamma_flip=flip, flip_pct=flip_pct,
        call_wall=call_wall, put_wall=put_wall,
        hvl=hvl,
        n_strikes=int(len(df)),
        max_dte=max_dte,
    )
    return df, summary


def compute_vex_profile(calls: pd.DataFrame, puts: pd.DataFrame,
                        spot: float, max_dte: int = 60,
                        min_oi: int = 0, r: float = None) -> tuple:
    """
    Vanna Exposure $ profile.

      VEX(k) = Vanna(k) × OI(k) × 100 × S × 0.01 × sign(k)

    Unidad: $ delta que el dealer debe ajustar por cada +1 pto de IV (0.01).
    Positivo = dealer compra delta (buys spot) si IV sube.
    """
    if r is None:
        r = _get_rf_rate()
    if spot <= 0:
        return pd.DataFrame(), {}

    # Filter + require IV
    def _prep(df):
        if df.empty:
            return df
        d = filter_chain_for_exposure(df, max_dte=max_dte, min_oi=min_oi)
        if d.empty or "IV%" not in d.columns or "DTE" not in d.columns:
            return pd.DataFrame()
        d = d[(d["IV%"].notna()) & (d["IV%"] > 0.01)].copy()
        return d

    c = _prep(calls); p = _prep(puts)
    if c.empty and p.empty:
        return pd.DataFrame(), {}

    SCALE = 100.0 * spot * 0.01

    def _per_side(df, side_sign):
        if df.empty:
            return np.array([]), np.array([])
        K     = df["Strike"].to_numpy(dtype=float)
        iv    = df["IV%"].to_numpy(dtype=float) / 100.0
        T     = np.maximum(df["DTE"].to_numpy(dtype=float) / 365.0, 1e-6)
        vanna = bs_vanna_vec(spot, K, T, iv, r)
        vex   = vanna * df["OI"].to_numpy(dtype=float) * SCALE * side_sign
        return K, vex

    cK, cV = _per_side(c, +1.0)
    pK, pV = _per_side(p, -1.0)

    c_g = (pd.DataFrame({"Strike": cK, "C_VEX": cV}).groupby("Strike", as_index=False)["C_VEX"].sum()
           if len(cK) else pd.DataFrame(columns=["Strike", "C_VEX"]))
    p_g = (pd.DataFrame({"Strike": pK, "P_VEX": pV}).groupby("Strike", as_index=False)["P_VEX"].sum()
           if len(pK) else pd.DataFrame(columns=["Strike", "P_VEX"]))

    df = c_g.merge(p_g, on="Strike", how="outer").fillna(0.0).sort_values("Strike")
    df["Net_VEX"] = df["C_VEX"] + df["P_VEX"]
    df["Abs_VEX"] = df["Net_VEX"].abs()
    df = df.reset_index(drop=True)

    total = float(df["Net_VEX"].sum())
    summary = dict(
        total_vex=total,
        call_vex=float(df["C_VEX"].sum()),
        put_vex=float(df["P_VEX"].sum()),
        regime="LONG_VANNA" if total > 0 else ("SHORT_VANNA" if total < 0 else "NEUTRAL"),
        max_dte=max_dte,
    )
    return df, summary


def compute_cex_profile(calls: pd.DataFrame, puts: pd.DataFrame,
                        spot: float, max_dte: int = 60,
                        min_oi: int = 0, r: float = None) -> tuple:
    """
    Charm Exposure $ profile.

      CEX(k) = Charm(k) × OI(k) × 100 × S × sign(k)

    Unidad: $ delta que cambia para el dealer por 1 día calendario.
    Positivo = delta del dealer sube con el paso del tiempo (compra spot).
    """
    if r is None:
        r = _get_rf_rate()
    if spot <= 0:
        return pd.DataFrame(), {}

    def _prep(df):
        if df.empty:
            return df
        d = filter_chain_for_exposure(df, max_dte=max_dte, min_oi=min_oi)
        if d.empty or "IV%" not in d.columns or "DTE" not in d.columns:
            return pd.DataFrame()
        d = d[(d["IV%"].notna()) & (d["IV%"] > 0.01)].copy()
        return d

    c = _prep(calls); p = _prep(puts)
    if c.empty and p.empty:
        return pd.DataFrame(), {}

    SCALE = 100.0 * spot

    def _per_side(df, side_sign):
        if df.empty:
            return np.array([]), np.array([])
        K     = df["Strike"].to_numpy(dtype=float)
        iv    = df["IV%"].to_numpy(dtype=float) / 100.0
        T     = np.maximum(df["DTE"].to_numpy(dtype=float) / 365.0, 1e-6)
        charm = bs_charm_vec(spot, K, T, iv, r)
        cex   = charm * df["OI"].to_numpy(dtype=float) * SCALE * side_sign
        return K, cex

    cK, cV = _per_side(c, +1.0)
    pK, pV = _per_side(p, -1.0)

    c_g = (pd.DataFrame({"Strike": cK, "C_CEX": cV}).groupby("Strike", as_index=False)["C_CEX"].sum()
           if len(cK) else pd.DataFrame(columns=["Strike", "C_CEX"]))
    p_g = (pd.DataFrame({"Strike": pK, "P_CEX": pV}).groupby("Strike", as_index=False)["P_CEX"].sum()
           if len(pK) else pd.DataFrame(columns=["Strike", "P_CEX"]))

    df = c_g.merge(p_g, on="Strike", how="outer").fillna(0.0).sort_values("Strike")
    df["Net_CEX"] = df["C_CEX"] + df["P_CEX"]
    df["Abs_CEX"] = df["Net_CEX"].abs()
    df = df.reset_index(drop=True)

    total = float(df["Net_CEX"].sum())
    summary = dict(
        total_cex=total,
        call_cex=float(df["C_CEX"].sum()),
        put_cex=float(df["P_CEX"].sum()),
        regime="POS_CHARM" if total > 0 else ("NEG_CHARM" if total < 0 else "NEUTRAL"),
        max_dte=max_dte,
    )
    return df, summary


def compute_dex_profile(calls: pd.DataFrame, puts: pd.DataFrame,
                        spot: float, max_dte: int = 60,
                        min_oi: int = 0) -> tuple:
    """
    Delta Exposure (sesgo direccional). No se aplica sign flip porque
    el delta del put ya es negativo.
      DEX(k) = Δ(k) × OI(k) × 100 × S
    """
    if spot <= 0:
        return pd.DataFrame(), {}

    def _prep(df):
        if df.empty:
            return pd.DataFrame()
        d = df.copy()
        if "Delta" not in d.columns:
            return pd.DataFrame()
        if "DTE" in d.columns:
            d = d[d["DTE"] <= max_dte]
        d = d[(d["OI"] > min_oi)]
        d = d.dropna(subset=["Strike", "Delta"])
        return d

    c = _prep(calls); p = _prep(puts)
    if c.empty and p.empty:
        return pd.DataFrame(), {}

    SCALE = 100.0 * spot

    c_d = (c["Delta"].clip(0, 1).to_numpy() * c["OI"].to_numpy() * SCALE) if not c.empty else np.array([])
    p_d = (p["Delta"].clip(-1, 0).to_numpy() * p["OI"].to_numpy() * SCALE) if not p.empty else np.array([])

    c_g = (pd.DataFrame({"Strike": c["Strike"].to_numpy(), "C_DEX": c_d})
           .groupby("Strike", as_index=False)["C_DEX"].sum()
           if not c.empty else pd.DataFrame(columns=["Strike", "C_DEX"]))
    p_g = (pd.DataFrame({"Strike": p["Strike"].to_numpy(), "P_DEX": p_d})
           .groupby("Strike", as_index=False)["P_DEX"].sum()
           if not p.empty else pd.DataFrame(columns=["Strike", "P_DEX"]))

    df = c_g.merge(p_g, on="Strike", how="outer").fillna(0.0).sort_values("Strike")
    df["Net_DEX"] = df["C_DEX"] + df["P_DEX"]
    df = df.reset_index(drop=True)

    total = float(df["Net_DEX"].sum())
    bias  = "CALL-HEAVY" if total > 0 else ("PUT-HEAVY" if total < 0 else "NEUTRAL")
    summary = dict(
        total_dex=total,
        call_dex=float(df["C_DEX"].sum()),
        put_dex=float(df["P_DEX"].sum()),
        bias=bias,
    )
    return df, summary


def compute_gex_by_expiry(calls: pd.DataFrame, puts: pd.DataFrame,
                          spot: float, max_dte: int = 60,
                          min_oi: int = 0) -> pd.DataFrame:
    """Descomposición de Net GEX por vencimiento (en $M, per-1% convention)."""
    if spot <= 0 or (calls.empty and puts.empty):
        return pd.DataFrame()
    c = filter_chain_for_exposure(calls, max_dte=max_dte, min_oi=min_oi)
    p = filter_chain_for_exposure(puts,  max_dte=max_dte, min_oi=min_oi)
    if c.empty and p.empty:
        return pd.DataFrame()

    SCALE = 100.0 * spot * spot * 0.01

    rows = []
    exps = sorted(set(
        (c["Expiry"].tolist() if "Expiry" in c.columns else []) +
        (p["Expiry"].tolist() if "Expiry" in p.columns else [])
    ))
    for exp in exps:
        ce = c[c["Expiry"] == exp] if not c.empty else pd.DataFrame()
        pe = p[p["Expiry"] == exp] if not p.empty else pd.DataFrame()
        c_g = (ce["Gamma"] * ce["OI"]).sum() * SCALE if not ce.empty else 0.0
        p_g = (pe["Gamma"] * pe["OI"]).sum() * SCALE * (-1.0) if not pe.empty else 0.0
        dte = 0
        for d in (ce, pe):
            if not d.empty and "DTE" in d.columns:
                try: dte = int(d["DTE"].iloc[0]); break
                except: pass
        rows.append({
            "Expiry": exp, "DTE": dte,
            "Call_GEX_M": c_g / 1e6,
            "Put_GEX_M":  p_g / 1e6,
            "Net_GEX_M":  (c_g + p_g) / 1e6,
        })
    return pd.DataFrame(rows).sort_values("DTE").reset_index(drop=True)


def compute_second_order_greeks_vec(df: pd.DataFrame, side: str, spot: float,
                                    r: float = None) -> pd.DataFrame:
    """Adds 'Vanna' and 'Charm' columns (per-contract per-share) — vectorized."""
    if df.empty:
        return df
    if r is None:
        r = _get_rf_rate()
    required = {"Strike", "IV%", "DTE"}
    if not required.issubset(df.columns):
        return df
    out = df.copy()
    K  = out["Strike"].to_numpy(dtype=float)
    iv = out["IV%"].to_numpy(dtype=float) / 100.0
    T  = np.maximum(out["DTE"].to_numpy(dtype=float) / 365.0, 1e-6)
    out["Vanna"] = bs_vanna_vec(spot, K, T, iv, r).round(6)
    out["Charm"] = bs_charm_vec(spot, K, T, iv, r).round(6)
    return out


# ═══════════════════════════════════════════════════════════════════════════════
#  6. KEY LEVELS & MISC ANALYTICS — Max Pain, PCR, ATM IV, Expected Move
# ═══════════════════════════════════════════════════════════════════════════════
def calc_max_pain(c: pd.DataFrame, p: pd.DataFrame) -> float:
    if c.empty or p.empty or "OI" not in c.columns:
        return None
    strikes = np.array(sorted(set(c["Strike"].tolist() + p["Strike"].tolist())), dtype=float)
    if strikes.size == 0:
        return None
    co = c.set_index("Strike")["OI"].reindex(strikes, fill_value=0).to_numpy(dtype=float)
    po = p.set_index("Strike")["OI"].reindex(strikes, fill_value=0).to_numpy(dtype=float)
    diff_call = np.maximum(0.0, strikes[:, None] - strikes[None, :])
    diff_put  = np.maximum(0.0, strikes[None, :] - strikes[:, None])
    pain = diff_call @ co + diff_put @ po
    return float(strikes[int(np.argmin(pain))])


def calc_pcr(c: pd.DataFrame, p: pd.DataFrame) -> float:
    if c.empty or p.empty or "OI" not in c.columns:
        return None
    tot = c["OI"].sum()
    return round(p["OI"].sum() / tot, 2) if tot > 0 else None


def calc_atm_iv(c: pd.DataFrame, spot: float) -> float:
    if c.empty or "IV%" not in c.columns or spot == 0:
        return None
    valid = c[c["IV%"].notna() & (c["IV%"] > 0.01)].copy()
    if valid.empty:
        return None
    if "DTE" in valid.columns:
        valid = valid.sort_values("DTE")
    idx = (valid["Strike"] - spot).abs().idxmin()
    val = float(valid.loc[idx, "IV%"])
    return val if val > 0.01 else None


def calc_expected_move(spot, iv_pct, dte):
    if not all([spot, iv_pct, dte]):
        return None, None
    move = spot * (iv_pct / 100) * np.sqrt(dte / 365)
    return round(spot - move, 2), round(spot + move, 2)


def calc_iv_skew(c, p, spot):
    if c.empty or p.empty:
        return pd.DataFrame()
    if "IV%" not in c.columns or "Strike" not in c.columns:
        return pd.DataFrame()
    c2 = c[["Strike","IV%"] + (["DTE"] if "DTE" in c.columns else [])].copy()
    p2 = p[["Strike","IV%"] + (["DTE"] if "DTE" in p.columns else [])].copy()
    for df in [c2, p2]:
        df["IV%"]    = pd.to_numeric(df["IV%"], errors="coerce")
        df["Strike"] = pd.to_numeric(df["Strike"], errors="coerce")
        if "DTE" in df.columns:
            df["DTE"] = pd.to_numeric(df["DTE"], errors="coerce").fillna(9999)
    c2 = c2[c2["IV%"].notna() & (c2["IV%"] > 0.01)].dropna(subset=["Strike"])
    p2 = p2[p2["IV%"].notna() & (p2["IV%"] > 0.01)].dropna(subset=["Strike"])
    if c2.empty or p2.empty:
        return pd.DataFrame()
    if "DTE" in c2.columns and "DTE" in p2.columns:
        c_near = c2.sort_values("DTE").groupby("Strike")["IV%"].first().reset_index()
        p_near = p2.sort_values("DTE").groupby("Strike")["IV%"].first().reset_index()
    else:
        c_near = c2.groupby("Strike")["IV%"].mean().reset_index()
        p_near = p2.groupby("Strike")["IV%"].mean().reset_index()
    c_near.columns = ["Strike", "C_IV"]
    p_near.columns = ["Strike", "P_IV"]
    skew = c_near.merge(p_near, on="Strike", how="inner").dropna()
    if skew.empty:
        return pd.DataFrame()
    skew["Skew"] = skew["P_IV"] - skew["C_IV"]
    atm_idx = (skew["Strike"] - spot).abs().idxmin()
    atm_iv  = (skew.loc[atm_idx, "C_IV"] + skew.loc[atm_idx, "P_IV"]) / 2
    skew["Moneyness"] = ((skew["Strike"] - spot) / spot * 100).round(2)
    if atm_iv > 0:
        skew["Skew_norm"] = (skew["Skew"] / atm_iv * 100).round(2)
    return skew.sort_values("Strike").reset_index(drop=True)


def calc_term_structure(c_all, spot, p_all=None):
    if c_all.empty or "IV%" not in c_all.columns or "Expiry" not in c_all.columns:
        return pd.DataFrame()
    rows = []
    p_groups = {exp: g for exp, g in p_all.groupby("Expiry")} \
        if p_all is not None and not p_all.empty and "Expiry" in p_all.columns else {}
    for exp, grp in c_all.groupby("Expiry"):
        grp = grp.copy()
        grp["IV%"]    = pd.to_numeric(grp["IV%"], errors="coerce")
        grp["Strike"] = pd.to_numeric(grp["Strike"], errors="coerce")
        grp["DTE"]    = pd.to_numeric(grp.get("DTE", 0), errors="coerce").fillna(0)
        grp = grp.dropna(subset=["IV%", "Strike"])
        grp = grp[grp["IV%"] > 0.01]
        if grp.empty:
            continue
        dte_val = int(grp["DTE"].iloc[0])
        idx_c   = (grp["Strike"] - spot).abs().idxmin()
        atm_c   = float(grp.loc[idx_c, "IV%"])
        atm_p = None
        if exp in p_groups:
            pg = p_groups[exp].copy()
            pg["IV%"]    = pd.to_numeric(pg["IV%"], errors="coerce")
            pg["Strike"] = pd.to_numeric(pg["Strike"], errors="coerce")
            pg = pg.dropna(subset=["IV%", "Strike"])
            pg = pg[pg["IV%"] > 0.01]
            if not pg.empty:
                idx_p = (pg["Strike"] - spot).abs().idxmin()
                atm_p = float(pg.loc[idx_p, "IV%"])
        atm_iv = (atm_c + atm_p) / 2.0 if atm_p is not None else atm_c
        if atm_iv > 0:
            rows.append({"Expiry": exp, "DTE": dte_val, "ATM_IV": round(atm_iv, 2)})
    return pd.DataFrame(rows).sort_values("DTE").reset_index(drop=True)


# ═══════════════════════════════════════════════════════════════════════════════
#  7. VOLATILITY ANALYTICS — HV, IV Rank, Cone, Returns
# ═══════════════════════════════════════════════════════════════════════════════
def calc_hv(closes: pd.Series, window: int) -> pd.Series:
    lr = np.log(closes / closes.shift(1))
    return (lr.rolling(window).std() * np.sqrt(252) * 100).round(2)


def calc_vol_analytics(price_df: pd.DataFrame, atm_iv: float) -> dict:
    if price_df.empty or "close" not in price_df.columns or atm_iv is None:
        return {}
    closes = price_df["close"].dropna()
    if len(closes) < 30:
        return {}
    log_rets = np.log(closes / closes.shift(1)).dropna()
    hv20_s = calc_hv(closes, 20).dropna()
    hv30_s = calc_hv(closes, 30).dropna()
    hv60_s = calc_hv(closes, 60).dropna()
    hv90_s = calc_hv(closes, 90).dropna()

    def _last(s):
        return round(float(np.asarray(s.iloc[-1]).flat[0]), 2) if len(s) > 0 else None

    hv20, hv30, hv60, hv90 = _last(hv20_s), _last(hv30_s), _last(hv60_s), _last(hv90_s)
    iv_hv_ratio  = round(atm_iv / (hv30 + 1e-9), 2) if hv30 else None
    iv_hv_spread = round(atm_iv - hv30, 2)           if hv30 else None

    hv_pct = None
    if len(hv30_s) >= 20:
        hv_pct = round(float((hv30_s < hv30).mean() * 100), 1)

    iv_rank = None
    if len(hv30_s) >= 20:
        hv_min = float(hv30_s.min()); hv_max = float(hv30_s.max())
        if hv_max > hv_min:
            iv_rank = round(max(0.0, min(100.0, (atm_iv - hv_min) / (hv_max - hv_min) * 100)), 1)

    cone = {}
    for w, lbl in [(10,"HV10"),(20,"HV20"),(30,"HV30"),(60,"HV60"),(90,"HV90")]:
        s = calc_hv(closes, w).dropna()
        if len(s) >= w:
            cone[lbl] = {
                "p10": round(float(s.quantile(0.10)), 2),
                "p25": round(float(s.quantile(0.25)), 2),
                "p50": round(float(s.quantile(0.50)), 2),
                "p75": round(float(s.quantile(0.75)), 2),
                "p90": round(float(s.quantile(0.90)), 2),
                "current": round(float(s.iloc[-1]), 2),
            }

    if iv_hv_ratio is not None:
        if   iv_hv_ratio > 1.3: vol_regime = "IV CARA"
        elif iv_hv_ratio < 0.8: vol_regime = "IV BARATA"
        else:                    vol_regime = "IV NEUTRAL"
    else:
        vol_regime = "—"

    ann_ret  = round(float(log_rets.mean() * 252 * 100), 2)
    skewness = round(float(log_rets.skew()), 3)
    kurt     = round(float(log_rets.kurt()), 3)

    return {
        "hv20": hv20, "hv30": hv30, "hv60": hv60, "hv90": hv90,
        "iv_hv_ratio": iv_hv_ratio, "iv_hv_spread": iv_hv_spread,
        "hv_percentile": hv_pct, "iv_rank": iv_rank,
        "vol_regime": vol_regime, "cone": cone,
        "hv20_series": hv20_s, "hv30_series": hv30_s,
        "hv60_series": hv60_s, "log_returns": log_rets,
        "closes": closes, "ann_ret": ann_ret,
        "skewness": skewness, "kurtosis": kurt, "dates": price_df["date"],
    }


# ═══════════════════════════════════════════════════════════════════════════════
#  8. CHARTS — Professional GEXbot-style profiles
# ═══════════════════════════════════════════════════════════════════════════════

def _focus_range(df: pd.DataFrame, spot: float, pct: float = 0.10) -> pd.DataFrame:
    """Focus ±pct around spot. Fallback to full range if too narrow."""
    if df.empty:
        return df
    lo, hi = spot * (1 - pct), spot * (1 + pct)
    fd = df[(df["Strike"] >= lo) & (df["Strike"] <= hi)]
    return fd if len(fd) >= 5 else df


def _fmt_bn(x: float) -> str:
    if abs(x) >= 1e9: return f"${x/1e9:+.2f}B"
    if abs(x) >= 1e6: return f"${x/1e6:+.0f}M"
    if abs(x) >= 1e3: return f"${x/1e3:+.0f}K"
    return f"${x:+.0f}"


def chart_gex_profile(gex_df: pd.DataFrame, spot: float, summary: dict,
                      symbol: str, focus_pct: float = 0.08) -> go.Figure:
    """
    Profile vertical estilo gexbot: strikes en Y, Call GEX derecha (verde),
    Put GEX izquierda (rojo). Muestra Spot, Zero-Gamma, HVL, Call/Put Walls.
    """
    if gex_df.empty:
        return None

    df = _focus_range(gex_df, spot, focus_pct).copy()
    # Scale to millions for readability
    df["C_GEX_M"] = df["C_GEX"] / 1e6
    df["P_GEX_M"] = df["P_GEX"] / 1e6
    df["Net_GEX_M"] = df["Net_GEX"] / 1e6

    fig = go.Figure()

    # Calls (right side, positive)
    fig.add_trace(go.Bar(
        y=df["Strike"], x=df["C_GEX_M"], orientation="h", name="Call GEX",
        marker=dict(color="rgba(34,197,94,0.78)", line=dict(width=0)),
        hovertemplate="<b>Strike $%{y:.1f}</b><br>Call GEX: $%{x:.1f}M<extra></extra>",
    ))
    # Puts (left side, already negative)
    fig.add_trace(go.Bar(
        y=df["Strike"], x=df["P_GEX_M"], orientation="h", name="Put GEX",
        marker=dict(color="rgba(244,63,94,0.78)", line=dict(width=0)),
        hovertemplate="<b>Strike $%{y:.1f}</b><br>Put GEX: $%{x:.1f}M<extra></extra>",
    ))

    # Net GEX marker overlay (subtle line con puntos)
    fig.add_trace(go.Scatter(
        y=df["Strike"], x=df["Net_GEX_M"],
        mode="markers", name="Net GEX",
        marker=dict(symbol="diamond", size=5, color="#fbbf24",
                    line=dict(width=1, color="#000")),
        hovertemplate="<b>Strike $%{y:.1f}</b><br>Net GEX: $%{x:+.1f}M<extra></extra>",
    ))

    # Reference lines
    cw  = summary.get("call_wall")
    pw  = summary.get("put_wall")
    gf  = summary.get("gamma_flip")
    hvl = summary.get("hvl")

    fig.add_hline(y=spot, line_dash="solid", line_color=_ORANGE, line_width=2,
                  annotation_text=f"  SPOT ${spot:.2f}",
                  annotation_font_size=11, annotation_font_color=_ORANGE,
                  annotation_position="top right")
    if cw is not None:
        fig.add_hline(y=cw, line_dash="dashdot", line_color=_GREEN, line_width=1.2,
                      annotation_text=f"  CALL WALL ${cw:.0f}",
                      annotation_font_size=10, annotation_font_color=_GREEN,
                      annotation_position="top right")
    if pw is not None:
        fig.add_hline(y=pw, line_dash="dashdot", line_color=_RED, line_width=1.2,
                      annotation_text=f"  PUT WALL ${pw:.0f}",
                      annotation_font_size=10, annotation_font_color=_RED,
                      annotation_position="bottom right")
    if gf is not None and (not cw or abs(gf - cw) > 0.5) and (not pw or abs(gf - pw) > 0.5):
        fig.add_hline(y=gf, line_dash="dot", line_color=_PURPLE, line_width=1.4,
                      annotation_text=f"  ZERO Γ ${gf:.0f}",
                      annotation_font_size=10, annotation_font_color=_PURPLE,
                      annotation_position="top right")
    if hvl is not None and (not cw or abs(hvl - cw) > 0.5) and (not pw or abs(hvl - pw) > 0.5):
        fig.add_hline(y=hvl, line_dash="dashdot", line_color=_CYAN, line_width=1,
                      annotation_text=f"  HVL ${hvl:.0f}",
                      annotation_font_size=9, annotation_font_color=_CYAN,
                      annotation_position="bottom right")

    fig.add_vline(x=0, line_dash="solid", line_color="rgba(255,255,255,0.12)", line_width=1)

    regime    = summary.get("regime", "NEUTRAL")
    total_bn  = summary.get("total_gex", 0) / 1e9
    r_color   = _GREEN if regime == "POSITIVE" else (_RED if regime == "NEGATIVE" else _ORANGE)

    fig.update_layout(
        height=640, barmode="overlay",
        title=dict(
            text=f"  {symbol}  ·  {regime} Γ  ·  Net: ${total_bn:+.3f}B  ·  "
                 f"DTE ≤ {summary.get('max_dte',60)}d  ·  {summary.get('n_strikes',0)} strikes",
            font=dict(size=12, color=r_color, family=_FONT_MONO), x=0
        ),
        xaxis_title="Gamma Exposure ($M per 1% move)",
        yaxis_title="Strike",
        **_BASE,
    )
    fig.update_xaxes(**_AX_ZERO)
    fig.update_yaxes(**_AX_NOZERO, tickformat="$,.0f")
    return fig


def chart_cum_gex(gex_df: pd.DataFrame, spot: float, summary: dict) -> go.Figure:
    """Cumulative GEX profile — muestra el cruce por cero (gamma flip)."""
    if gex_df.empty or "CumGEX" not in gex_df.columns:
        return None
    df = gex_df.sort_values("Strike").copy()
    df["CumGEX_Bn"] = df["CumGEX"] / 1e9
    pos = df[df["CumGEX_Bn"] >= 0]
    neg = df[df["CumGEX_Bn"] < 0]

    fig = go.Figure()
    if not pos.empty:
        fig.add_trace(go.Scatter(
            x=pos["Strike"], y=pos["CumGEX_Bn"], mode="lines", name="+Cum GEX",
            line=dict(color=_GREEN, width=2),
            fill="tozeroy", fillcolor="rgba(34,197,94,0.10)",
            hovertemplate="Strike $%{x}<br>Cum GEX: $%{y:+.2f}B<extra></extra>",
        ))
    if not neg.empty:
        fig.add_trace(go.Scatter(
            x=neg["Strike"], y=neg["CumGEX_Bn"], mode="lines", name="−Cum GEX",
            line=dict(color=_RED, width=2),
            fill="tozeroy", fillcolor="rgba(244,63,94,0.10)",
            hovertemplate="Strike $%{x}<br>Cum GEX: $%{y:+.2f}B<extra></extra>",
        ))
    fig.add_hline(y=0, line_dash="dot", line_color="rgba(255,255,255,0.15)", line_width=1)
    _vline(fig, spot, text=f"  SPOT ${spot:.2f}")
    gf = summary.get("gamma_flip")
    if gf:
        fig.add_vline(x=gf, line_dash="dot", line_color=_PURPLE, line_width=1.4,
                      annotation_text=f"  ZERO Γ ${gf:.0f}",
                      annotation_font_size=10, annotation_font_color=_PURPLE)
    fig.update_layout(height=240, xaxis_title="Strike",
                      yaxis_title="Cum GEX ($B)", **_BASE)
    fig.update_xaxes(**_AX_NOZERO)
    fig.update_yaxes(**_AX_ZERO)
    return fig


def chart_vex_profile(vex_df: pd.DataFrame, spot: float, summary: dict,
                      symbol: str, focus_pct: float = 0.10) -> go.Figure:
    """
    Vanna Exposure profile.
      - Positivo = dealer debe COMPRAR delta si IV sube (bullish flow on vol expansion)
      - Negativo = dealer debe VENDER delta si IV sube (bearish flow on vol expansion)
    """
    if vex_df.empty:
        return None
    df = _focus_range(vex_df, spot, focus_pct).copy()
    df["C_VEX_M"] = df["C_VEX"] / 1e6
    df["P_VEX_M"] = df["P_VEX"] / 1e6
    df["Net_VEX_M"] = df["Net_VEX"] / 1e6

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df["Strike"], y=df["C_VEX_M"], name="Call VEX",
        marker=dict(color="rgba(34,197,94,0.72)", line=dict(width=0)),
        hovertemplate="Strike $%{x:.1f}<br>Call VEX: $%{y:+.2f}M<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        x=df["Strike"], y=df["P_VEX_M"], name="Put VEX",
        marker=dict(color="rgba(244,63,94,0.72)", line=dict(width=0)),
        hovertemplate="Strike $%{x:.1f}<br>Put VEX: $%{y:+.2f}M<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=df["Strike"], y=df["Net_VEX_M"], name="Net VEX",
        mode="lines+markers",
        line=dict(color="#fbbf24", width=2),
        marker=dict(size=5, color="#fbbf24", line=dict(width=1, color="#000")),
        hovertemplate="Strike $%{x:.1f}<br>Net VEX: $%{y:+.2f}M<extra></extra>",
    ))
    _vline(fig, spot, text=f"  SPOT ${spot:.2f}")
    fig.add_hline(y=0, line_dash="dot", line_color="rgba(255,255,255,0.12)", line_width=1)

    total_mn = summary.get("total_vex", 0) / 1e6
    regime   = summary.get("regime", "NEUTRAL")
    r_color  = _GREEN if total_mn > 0 else (_RED if total_mn < 0 else _ORANGE)

    fig.update_layout(
        height=320, barmode="relative",
        title=dict(
            text=f"  VANNA EXPOSURE  ·  {symbol}  ·  {regime}  ·  Net: ${total_mn:+.1f}M per +1 vol pt",
            font=dict(size=11, color=r_color, family=_FONT_MONO), x=0
        ),
        xaxis_title="Strike",
        yaxis_title="VEX ($M per +1 vol point)",
        **_BASE,
    )
    fig.update_xaxes(**_AX_NOZERO)
    fig.update_yaxes(**_AX_ZERO)
    return fig


def chart_cex_profile(cex_df: pd.DataFrame, spot: float, summary: dict,
                      symbol: str, focus_pct: float = 0.10) -> go.Figure:
    """
    Charm Exposure profile.
      - Positivo = dealer delta sube con el paso del tiempo (debe comprar spot)
      - Negativo = dealer delta baja (debe vender spot)
    Importante para 0DTE & decaimiento intradía.
    """
    if cex_df.empty:
        return None
    df = _focus_range(cex_df, spot, focus_pct).copy()
    df["C_CEX_M"] = df["C_CEX"] / 1e6
    df["P_CEX_M"] = df["P_CEX"] / 1e6
    df["Net_CEX_M"] = df["Net_CEX"] / 1e6

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df["Strike"], y=df["C_CEX_M"], name="Call CEX",
        marker=dict(color="rgba(34,197,94,0.72)", line=dict(width=0)),
        hovertemplate="Strike $%{x:.1f}<br>Call CEX: $%{y:+.2f}M/día<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        x=df["Strike"], y=df["P_CEX_M"], name="Put CEX",
        marker=dict(color="rgba(244,63,94,0.72)", line=dict(width=0)),
        hovertemplate="Strike $%{x:.1f}<br>Put CEX: $%{y:+.2f}M/día<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=df["Strike"], y=df["Net_CEX_M"], name="Net CEX",
        mode="lines+markers",
        line=dict(color="#fbbf24", width=2),
        marker=dict(size=5, color="#fbbf24", line=dict(width=1, color="#000")),
        hovertemplate="Strike $%{x:.1f}<br>Net CEX: $%{y:+.2f}M/día<extra></extra>",
    ))
    _vline(fig, spot, text=f"  SPOT ${spot:.2f}")
    fig.add_hline(y=0, line_dash="dot", line_color="rgba(255,255,255,0.12)", line_width=1)

    total_mn = summary.get("total_cex", 0) / 1e6
    regime   = summary.get("regime", "NEUTRAL").replace("_", " ")
    r_color  = _GREEN if total_mn > 0 else (_RED if total_mn < 0 else _ORANGE)

    fig.update_layout(
        height=320, barmode="relative",
        title=dict(
            text=f"  CHARM EXPOSURE  ·  {symbol}  ·  {regime}  ·  Net: ${total_mn:+.1f}M por día",
            font=dict(size=11, color=r_color, family=_FONT_MONO), x=0
        ),
        xaxis_title="Strike",
        yaxis_title="CEX ($M per 1 day of decay)",
        **_BASE,
    )
    fig.update_xaxes(**_AX_NOZERO)
    fig.update_yaxes(**_AX_ZERO)
    return fig


def chart_gex_by_expiry_pro(exp_df: pd.DataFrame) -> go.Figure:
    """Descomposición por vencimiento — barras stacked."""
    if exp_df.empty or len(exp_df) < 1:
        return None
    df = exp_df.copy()
    df["Abs"] = df["Net_GEX_M"].abs()
    df = df.nlargest(14, "Abs").sort_values("DTE")
    labels = [f"{str(r['Expiry'])[5:]}  ({r['DTE']}d)" for _, r in df.iterrows()]
    fig = go.Figure([
        go.Bar(x=labels, y=df["Call_GEX_M"], name="Calls",
               marker=dict(color="rgba(34,197,94,0.75)", line=dict(width=0)),
               hovertemplate="%{x}<br>Call GEX: $%{y:.1f}M<extra></extra>"),
        go.Bar(x=labels, y=df["Put_GEX_M"], name="Puts",
               marker=dict(color="rgba(244,63,94,0.75)", line=dict(width=0)),
               hovertemplate="%{x}<br>Put GEX: $%{y:.1f}M<extra></extra>"),
    ])
    fig.update_layout(height=280, barmode="relative",
                      xaxis_title="Expiración", yaxis_title="GEX ($M)", **_BASE)
    fig.update_xaxes(**_AX_NOZERO, tickangle=-40)
    fig.update_yaxes(**_AX_ZERO)
    return fig


def chart_dex_profile(dex_df: pd.DataFrame, spot: float, summary: dict,
                      symbol: str, focus_pct: float = 0.10) -> go.Figure:
    """Delta Exposure profile."""
    if dex_df.empty:
        return None
    df = _focus_range(dex_df, spot, focus_pct).copy()
    df["C_DEX_M"] = df["C_DEX"] / 1e6
    df["P_DEX_M"] = df["P_DEX"] / 1e6
    df["Net_DEX_M"] = df["Net_DEX"] / 1e6

    fig = make_subplots(rows=2, cols=1, vertical_spacing=0.14,
                        row_heights=[0.62, 0.38],
                        subplot_titles=["DELTA EXPOSURE POR STRIKE",
                                        "NET DEX ACUMULADO"])
    fig.add_trace(go.Bar(
        x=df["Strike"], y=df["C_DEX_M"], name="Call DEX",
        marker=dict(color="rgba(34,197,94,0.72)", line=dict(width=0)),
        hovertemplate="Strike $%{x}<br>Call DEX: $%{y:+.1f}M<extra></extra>",
    ), row=1, col=1)
    fig.add_trace(go.Bar(
        x=df["Strike"], y=df["P_DEX_M"], name="Put DEX",
        marker=dict(color="rgba(244,63,94,0.72)", line=dict(width=0)),
        hovertemplate="Strike $%{x}<br>Put DEX: $%{y:+.1f}M<extra></extra>",
    ), row=1, col=1)
    _vline(fig, spot, row=1, col=1, text=f"  SPOT ${spot:.2f}")

    cum = df["Net_DEX"].cumsum() / 1e6
    fig.add_trace(go.Scatter(
        x=df["Strike"], y=cum, name="Cum Net DEX",
        line=dict(color=_PURPLE, width=2),
        fill="tozeroy", fillcolor="rgba(168,85,247,0.07)",
        hovertemplate="Strike $%{x}<br>Cum DEX: $%{y:+.1f}M<extra></extra>",
    ), row=2, col=1)
    fig.add_hline(y=0, line_dash="dot", line_color="rgba(255,255,255,0.1)", row=2, col=1)
    _vline(fig, spot, row=2, col=1)

    total = summary.get("total_dex", 0) / 1e6
    bias  = summary.get("bias", "")
    clr   = _GREEN if total > 0 else _RED

    fig.update_layout(
        height=520, barmode="relative",
        title=dict(text=f"  {symbol}  ·  DEX Total: ${total:+.0f}M  ·  {bias}",
                   font=dict(size=11, color=clr, family=_FONT_MONO), x=0),
        **_BASE,
    )
    fig.update_xaxes(**_AX_NOZERO, title_text="Strike")
    fig.update_yaxes(**_AX_ZERO, title_text="DEX ($M)", row=1, col=1)
    fig.update_yaxes(**_AX_ZERO, title_text="Cum DEX ($M)", row=2, col=1)
    for ann in fig.layout.annotations:
        ann.font.update(size=10, color="#606080", family=_FONT_MONO)
    return fig


def chart_greeks(c, p, spot):
    fig = make_subplots(rows=2, cols=2,
        subplot_titles=["DELTA","GAMMA","THETA  (decay / day)","IV SMILE"],
        vertical_spacing=0.22, horizontal_spacing=0.10)
    for g, r, cc in [("Delta",1,1),("Gamma",1,2),("Theta",2,1),("IV%",2,2)]:
        for df, lbl, clr in [(c,"Calls",_GREEN),(p,"Puts",_RED)]:
            if df.empty or g not in df.columns:
                continue
            d = df.sort_values("Strike")
            fig.add_trace(go.Scatter(
                x=d["Strike"], y=d[g], name=lbl,
                line=dict(color=clr, width=2), mode="lines+markers",
                marker=dict(size=4, color=clr),
                showlegend=(r==1 and cc==1), legendgroup=lbl,
                hovertemplate=f"Strike: %{{x}}<br>{g}: %{{y:.4f}}<extra>{lbl}</extra>",
            ), row=r, col=cc)
        _vline(fig, spot, row=r, col=cc)
    fig.update_layout(height=500, **_BASE)
    fig.update_xaxes(**_AX_NOZERO, title_text="Strike")
    fig.update_yaxes(**_AX_ZERO, row=1, col=1)
    fig.update_yaxes(**_AX_NOZERO, row=1, col=2)
    fig.update_yaxes(**_AX_ZERO, row=2, col=1)
    fig.update_yaxes(**_AX_NOZERO, title_text="IV (%)", row=2, col=2)
    for ann in fig.layout.annotations:
        ann.font.update(size=10, color="#606080", family=_FONT_MONO)
    return fig


def chart_iv_skew(skew_df, spot):
    if skew_df.empty:
        return None
    fig = make_subplots(rows=1, cols=2,
        subplot_titles=["IV POR STRIKE  (Calls vs Puts)", "SKEW  (Put IV − Call IV)"],
        horizontal_spacing=0.10)
    fig.add_trace(go.Scatter(
        x=skew_df["Strike"], y=skew_df["C_IV"], name="Call IV",
        line=dict(color=_GREEN, width=2), mode="lines",
        hovertemplate="Strike %{x}<br>Call IV: %{y:.1f}%<extra></extra>",
    ), row=1, col=1)
    fig.add_trace(go.Scatter(
        x=skew_df["Strike"], y=skew_df["P_IV"], name="Put IV",
        line=dict(color=_RED, width=2), mode="lines",
        hovertemplate="Strike %{x}<br>Put IV: %{y:.1f}%<extra></extra>",
    ), row=1, col=1)
    _vline(fig, spot, row=1, col=1)
    skew_colors = [_RED if v > 0 else _GREEN for v in skew_df["Skew"]]
    fig.add_trace(go.Bar(
        x=skew_df["Strike"], y=skew_df["Skew"],
        marker_color=skew_colors, marker_line_width=0,
        name="Skew", showlegend=False,
        hovertemplate="Strike %{x}<br>Skew: %{y:.1f}%<extra></extra>",
    ), row=1, col=2)
    fig.add_hline(y=0, line_dash="dot", line_color="rgba(255,255,255,0.08)", row=1, col=2)
    _vline(fig, spot, row=1, col=2)
    fig.update_layout(height=320, **_BASE)
    fig.update_xaxes(**_AX_NOZERO, title_text="Strike")
    fig.update_yaxes(**_AX_NOZERO, title_text="IV (%)", row=1, col=1)
    fig.update_yaxes(**_AX_ZERO, title_text="Put IV − Call IV (%)", row=1, col=2)
    for ann in fig.layout.annotations:
        ann.font.update(size=10, color="#606080", family=_FONT_MONO)
    return fig


def chart_term_structure(ts_df):
    if ts_df.empty:
        return None
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=ts_df["DTE"], y=ts_df["ATM_IV"], mode="lines+markers",
        line=dict(color=_ORANGE, width=2.5),
        marker=dict(size=8, color=_ORANGE, line=dict(width=1.5, color="#0b0b14")),
        hovertemplate="DTE: %{x}d<br>ATM IV: %{y:.1f}%<extra></extra>",
        fill="tozeroy", fillcolor="rgba(249,115,22,0.05)",
    ))
    for _, row in ts_df.iterrows():
        fig.add_annotation(x=row["DTE"], y=row["ATM_IV"],
            text=f"  {str(row['Expiry'])[:10]}",
            showarrow=False,
            font=dict(size=9, color="#505070", family=_FONT_MONO),
            xanchor="left")
    fig.update_layout(height=260, xaxis_title="DTE (días)", yaxis_title="ATM IV (%)", **_BASE)
    fig.update_xaxes(**_AX_NOZERO)
    fig.update_yaxes(**_AX_NOZERO)
    return fig


def chart_oi_volume(c, p, spot, em_low=None, em_high=None):
    fig = make_subplots(rows=1, cols=2,
        subplot_titles=["OPEN INTEREST POR STRIKE", "VOLUMEN POR STRIKE"],
        horizontal_spacing=0.10)
    for metric, col in [("OI",1),("Volume",2)]:
        for df, lbl, clr in [(c,"Calls","rgba(34,197,94,0.65)"),(p,"Puts","rgba(244,63,94,0.65)")]:
            if df.empty or metric not in df.columns:
                continue
            d = df.sort_values("Strike")
            fig.add_trace(go.Bar(
                x=d["Strike"], y=d[metric], name=lbl,
                marker_color=clr, marker_line_width=0,
                showlegend=(col==1), legendgroup=lbl,
                hovertemplate=f"Strike %{{x}}<br>{metric}: %{{y:,}}<extra>{lbl}</extra>",
            ), row=1, col=col)
        _vline(fig, spot, row=1, col=col)
        if em_low and em_high:
            for em_val, em_lbl in [(em_low,"EM−"),(em_high,"EM+")]:
                fig.add_vline(x=em_val, line_dash="dashdot",
                    line_color="rgba(168,85,247,0.4)", line_width=1,
                    annotation_text=f"  {em_lbl} ${em_val:.0f}",
                    annotation_font_size=8, annotation_font_color="#a855f7",
                    row=1, col=col)
    fig.update_layout(height=300, barmode="overlay", **_BASE)
    fig.update_xaxes(**_AX_NOZERO, title_text="Strike")
    fig.update_yaxes(**_AX_NOZERO)
    for ann in fig.layout.annotations:
        ann.font.update(size=10, color="#606080", family=_FONT_MONO)
    return fig


def chart_vol_cone(analytics: dict, atm_iv: float, symbol: str):
    cone = analytics.get("cone", {})
    if not cone:
        return None
    windows = list(cone.keys())
    p10 = [cone[w]["p10"]  for w in windows]
    p25 = [cone[w]["p25"]  for w in windows]
    p50 = [cone[w]["p50"]  for w in windows]
    p75 = [cone[w]["p75"]  for w in windows]
    p90 = [cone[w]["p90"]  for w in windows]
    curr = [cone[w]["current"] for w in windows]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=windows + windows[::-1], y=p90 + p10[::-1],
        fill="toself", fillcolor="rgba(59,130,246,0.06)",
        line=dict(color="rgba(0,0,0,0)"), showlegend=True, name="P10–P90", hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=windows + windows[::-1], y=p75 + p25[::-1],
        fill="toself", fillcolor="rgba(59,130,246,0.14)",
        line=dict(color="rgba(0,0,0,0)"), showlegend=True, name="P25–P75", hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=windows, y=p50, name="Mediana HV",
        line=dict(color=_BLUE, width=1.5, dash="dot"),
        hovertemplate="%{x}: Mediana %{y:.1f}%<extra></extra>"))
    fig.add_trace(go.Scatter(x=windows, y=curr, name="HV Actual",
        line=dict(color=_ORANGE, width=2.5), mode="lines+markers", marker=dict(size=6),
        hovertemplate="%{x}: HV Actual %{y:.1f}%<extra></extra>"))
    if atm_iv:
        fig.add_hline(y=atm_iv, line_dash="dash", line_color=_GREEN, line_width=1.5,
            annotation_text=f"  ATM IV {atm_iv:.1f}%",
            annotation_font_color=_GREEN, annotation_font_size=10)
    fig.update_layout(height=320, xaxis_title="Ventana lookback",
        yaxis_title="Volatilidad (%)",
        title=dict(text=f"  VOLATILITY CONE · {symbol}",
                   font=dict(size=11, color="#606080", family=_FONT_MONO), x=0),
        **_BASE)
    fig.update_xaxes(**_AX_NOZERO)
    fig.update_yaxes(**_AX_NOZERO)
    return fig


def chart_iv_hv_history(analytics: dict, atm_iv: float):
    hv30_s = analytics.get("hv30_series")
    dates  = analytics.get("dates")
    if hv30_s is None or dates is None or len(hv30_s) < 10:
        return None
    hv30_s = hv30_s.dropna()
    try:
        hv_dates = dates.iloc[hv30_s.index].reset_index(drop=True)
    except Exception:
        hv_dates = pd.Series(range(len(hv30_s)))
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=hv_dates, y=hv30_s.values, name="HV30",
        line=dict(color=_ORANGE, width=2), fill="tozeroy",
        fillcolor="rgba(249,115,22,0.06)",
        hovertemplate="%{x|%Y-%m-%d}<br>HV30: %{y:.1f}%<extra></extra>"))
    if atm_iv:
        fig.add_hline(y=atm_iv, line_dash="dash", line_color=_GREEN, line_width=1.5,
            annotation_text=f"  ATM IV {atm_iv:.1f}%",
            annotation_font_color=_GREEN, annotation_font_size=10)
    if len(hv30_s) > 0:
        last_date = hv_dates.iloc[-1] if hasattr(hv_dates, "iloc") else hv_dates[len(hv_dates)-1]
        last_hv   = float(hv30_s.iloc[-1])
        fig.add_trace(go.Scatter(x=[last_date], y=[last_hv], mode="markers",
            marker=dict(size=9, color=_ORANGE, line=dict(width=2, color="#0b0b14")),
            name="HV30 actual", showlegend=True,
            hovertemplate=f"HV30 actual: {last_hv:.1f}%<extra></extra>"))
    fig.update_layout(height=260, xaxis_title="Fecha", yaxis_title="Volatilidad (%)", **_BASE)
    fig.update_xaxes(**_AX_NOZERO)
    fig.update_yaxes(**_AX_NOZERO)
    return fig


def chart_returns_dist(analytics: dict, symbol: str):
    log_rets = analytics.get("log_returns")
    if log_rets is None or len(log_rets) < 20:
        return None
    rets_pct = (log_rets * 100).dropna()
    mu, sig = float(rets_pct.mean()), float(rets_pct.std())
    fig = go.Figure()
    fig.add_trace(go.Histogram(x=rets_pct, name="Retornos", nbinsx=60,
        marker_color="rgba(59,130,246,0.55)", marker_line=dict(width=0),
        histnorm="probability density",
        hovertemplate="Retorno: %{x:.2f}%<br>Densidad: %{y:.4f}<extra></extra>"))
    x_norm = np.linspace(rets_pct.min(), rets_pct.max(), 200)
    y_norm = (1/(sig * np.sqrt(2*np.pi))) * np.exp(-0.5*((x_norm - mu)/sig)**2)
    fig.add_trace(go.Scatter(x=x_norm, y=y_norm, name="Normal",
        line=dict(color=_ORANGE, width=2, dash="dot"), hoverinfo="skip"))
    for n, clr, lbl in [(1, "rgba(34,197,94,0.5)", "±1σ"), (2, "rgba(244,63,94,0.4)", "±2σ")]:
        for sign in [-1, 1]:
            fig.add_vline(x=mu + sign*n*sig, line_dash="dot", line_color=clr, line_width=1,
                annotation_text=f" {lbl}" if sign > 0 else "",
                annotation_font_size=9, annotation_font_color=clr)
    fig.add_vline(x=0, line_dash="dot", line_color="rgba(255,255,255,0.1)", line_width=1)
    skew = analytics.get("skewness", 0); kurt = analytics.get("kurtosis", 0)
    fig.update_layout(height=260, xaxis_title="Retorno diario (%)",
        yaxis_title="Densidad",
        title=dict(text=f"  DISTRIBUCIÓN DE RETORNOS · {symbol} · μ={mu:.2f}% σ={sig:.2f}% Skew={skew:.2f} Kurt={kurt:.2f}",
                   font=dict(size=11, color="#606080", family=_FONT_MONO), x=0),
        **_BASE)
    fig.update_xaxes(**_AX_NOZERO)
    fig.update_yaxes(**_AX_NOZERO)
    return fig


def render_tv_chart(price_df: pd.DataFrame, spot: float, gex_summary: dict,
                    mp: float = None, em_lo: float = None, em_hi: float = None,
                    freq_min: int = 1):
    """Candlestick + volume + GEX structural levels via lightweight-charts v4."""
    if price_df.empty:
        st.caption("Sin datos de precio para mostrar la gráfica.")
        return
    df = price_df.copy().dropna(subset=["open","high","low","close"])
    if df.empty:
        st.caption("Sin velas válidas.")
        return

    def _unix(dt):
        t = pd.Timestamp(dt)
        if t.tzinfo is None:
            t = t.tz_localize("UTC")
        return int(t.timestamp())

    candles = [{"time": _unix(r.date),
                "open":  round(float(r.open),  4),
                "high":  round(float(r.high),  4),
                "low":   round(float(r.low),   4),
                "close": round(float(r.close), 4)}
               for r in df.itertuples()]
    volumes = [{"time": _unix(r.date),
                "value": float(r.volume),
                "color": "#26a69a88" if r.close >= r.open else "#ef535088"}
               for r in df.itertuples()]

    cw  = gex_summary.get("call_wall")
    pw  = gex_summary.get("put_wall")
    gf  = gex_summary.get("gamma_flip")
    hvl = gex_summary.get("hvl")

    def _pl(price, color, title, style=0, width=1):
        if not price or float(price) <= 0:
            return None
        return {"price": round(float(price), 2), "color": color,
                "lineWidth": width, "lineStyle": style,
                "axisLabelVisible": True, "title": title}

    gex_lines = [l for l in [
        _pl(spot,  "#f97316", f"SPOT {spot:.2f}",          0, 2),
        _pl(cw,    "#22c55e", f"CW {cw:.2f}"   if cw  else "", 2, 1),
        _pl(pw,    "#ef4444", f"PW {pw:.2f}"   if pw  else "", 2, 1),
        _pl(gf,    "#a855f7", f"GF {gf:.2f}"   if gf  else "", 1, 1),
        _pl(hvl,   "#06b6d4", f"HVL {hvl:.2f}" if hvl else "", 4, 1),
        _pl(mp,    "#94a3b8", f"MP {mp:.2f}"   if mp  else "", 4, 1),
        _pl(em_hi, "#c084fc", f"EM+ {em_hi:.2f}" if em_hi else "", 3, 1),
        _pl(em_lo, "#c084fc", f"EM- {em_lo:.2f}" if em_lo else "", 3, 1),
    ] if l is not None]

    last_c   = float(df["close"].iloc[-1])
    open_p   = float(df["open"].iloc[0])
    chg      = last_c - open_p
    chg_pct  = chg / open_p * 100 if open_p else 0
    chg_clr  = "#26a69a" if chg >= 0 else "#ef5350"
    freq_lbl = f"{freq_min}m"
    now_cdmx = datetime.datetime.now(_CDMX_TZ)

    chips = "".join(filter(None, [
        f'<span class="cg">CW&nbsp;{cw:.0f}</span>' if cw else "",
        f'<span class="cr">PW&nbsp;{pw:.0f}</span>' if pw else "",
        f'<span class="cp">GF&nbsp;{gf:.0f}</span>' if gf else "",
        f'<span class="cy">HVL&nbsp;{hvl:.0f}</span>' if hvl else "",
        f'<span class="cs">MP&nbsp;{mp:.0f}</span>' if mp else "",
    ]))

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:#131722;color:#d1d4dc;font-family:'Courier New',monospace;overflow:hidden}}
#h{{display:flex;align-items:center;gap:8px;padding:5px 12px;background:#1e222d;border-bottom:1px solid #2a2e39;flex-wrap:wrap;font-size:11px}}
#pr{{font-weight:700;font-size:14px}}
#dl{{color:{chg_clr};font-weight:600}}
span.co{{padding:2px 6px;border-radius:3px;font-size:10px;font-weight:700;background:rgba(249,115,22,.15);color:#f97316}}
span.cg{{padding:2px 6px;border-radius:3px;font-size:10px;font-weight:700;background:rgba(38,166,154,.15);color:#26a69a}}
span.cr{{padding:2px 6px;border-radius:3px;font-size:10px;font-weight:700;background:rgba(239,83,80,.15);color:#ef5350}}
span.cp{{padding:2px 6px;border-radius:3px;font-size:10px;font-weight:700;background:rgba(168,85,247,.15);color:#a855f7}}
span.cy{{padding:2px 6px;border-radius:3px;font-size:10px;font-weight:700;background:rgba(6,182,212,.15);color:#06b6d4}}
span.cs{{padding:2px 6px;border-radius:3px;font-size:10px;font-weight:700;background:rgba(148,163,184,.12);color:#94a3b8}}
#tz{{margin-left:auto;color:#535964;font-size:10px;text-align:right;line-height:1.4}}
#w{{position:relative;width:100%}}
#tip{{position:absolute;top:40px;left:10px;font-size:10px;color:#9598a1;pointer-events:none;z-index:10;background:rgba(19,23,34,.92);padding:3px 8px;border-radius:3px;border:1px solid #2a2e39;display:none}}
#mc{{width:100%;height:440px}}
#vc{{width:100%;height:70px}}
</style></head><body>
<div id="h">
  <span id="pr">{last_c:.2f}</span>
  <span id="dl">{chg:+.2f}&nbsp;({chg_pct:+.2f}%)</span>
  <span class="co">{freq_lbl}</span>
  {chips}
  <span id="tz">CDMX (UTC-6)<br>{now_cdmx.strftime('%H:%M:%S')}</span>
</div>
<div id="w">
  <div id="tip"></div>
  <div id="mc"></div>
  <div id="vc"></div>
</div>
<script src="https://unpkg.com/lightweight-charts@4.1.3/dist/lightweight-charts.standalone.production.js"></script>
<script>
const C={json.dumps(candles)};
const V={json.dumps(volumes)};
const G={json.dumps(gex_lines)};
const TFmt=new Intl.DateTimeFormat("es-MX",{{timeZone:"America/Mexico_City",hour:"2-digit",minute:"2-digit",hour12:false}});
const DFmt=new Intl.DateTimeFormat("es-MX",{{timeZone:"America/Mexico_City",month:"short",day:"numeric",hour:"2-digit",minute:"2-digit",hour12:false}});
const fmt=s=>TFmt.format(new Date(s*1000));
const CFG={{
  layout:{{background:{{type:"solid",color:"#131722"}},textColor:"#535964",fontFamily:"'Courier New',monospace",fontSize:11}},
  grid:{{vertLines:{{color:"rgba(42,46,57,.5)",style:1}},horzLines:{{color:"rgba(42,46,57,.5)",style:1}}}},
  crosshair:{{mode:LightweightCharts.CrosshairMode.Normal,
    vertLine:{{color:"#758696",width:1,style:1,labelBackgroundColor:"#363a45"}},
    horzLine:{{color:"#758696",width:1,style:1,labelBackgroundColor:"#363a45"}}}},
  rightPriceScale:{{borderColor:"#2a2e39"}},
  timeScale:{{borderColor:"#2a2e39",timeVisible:true,secondsVisible:false,tickMarkFormatter:s=>fmt(s)}},
  localization:{{timeFormatter:s=>DFmt.format(new Date(s*1000))}},
  handleScroll:{{mouseWheel:true,pressedMouseMove:true,horzTouchDrag:true}},
  handleScale:{{mouseWheel:true,pinch:true,axisPressedMouseMove:true}},
}};
const W=document.getElementById("mc").offsetWidth||900;
const mc=LightweightCharts.createChart(document.getElementById("mc"),{{...CFG,width:W,height:440}});
const cs=mc.addCandlestickSeries({{upColor:"#26a69a",downColor:"#ef5350",borderUpColor:"#26a69a",borderDownColor:"#ef5350",wickUpColor:"#26a69a",wickDownColor:"#ef5350"}});
cs.setData(C);
G.forEach(l=>cs.createPriceLine(l));
const vc=LightweightCharts.createChart(document.getElementById("vc"),{{...CFG,width:W,height:70,timeScale:{{...CFG.timeScale,visible:false}},rightPriceScale:{{visible:false}},leftPriceScale:{{visible:false}}}});
const vs=vc.addHistogramSeries({{priceScaleId:"v",lastValueVisible:false,priceLineVisible:false}});
vs.setData(V);
let _syncing=false;
function syncRange(src,dst){{
  if(_syncing) return;
  const r=src.timeScale().getVisibleLogicalRange();
  if(!r) return;
  _syncing=true;
  dst.timeScale().setVisibleLogicalRange(r);
  _syncing=false;
}}
mc.timeScale().subscribeVisibleLogicalRangeChange(()=>syncRange(mc,vc));
vc.timeScale().subscribeVisibleLogicalRangeChange(()=>syncRange(vc,mc));
const tip=document.getElementById("tip");
mc.subscribeCrosshairMove(p=>{{
  if(!p.time||!p.seriesData.has(cs)){{tip.style.display="none";return;}}
  const r=p.seriesData.get(cs),d=r.close-r.open,pct=(d/r.open*100).toFixed(2),cl=d>=0?"#26a69a":"#ef5350";
  tip.style.display="block";
  tip.innerHTML=`<span style="color:#787b86">${{fmt(p.time)}}</span>&ensp;`
    +`<span style="color:${{cl}}">O:${{r.open.toFixed(2)}} H:${{r.high.toFixed(2)}} L:${{r.low.toFixed(2)}} C:${{r.close.toFixed(2)}}&nbsp;<b>${{d>=0?"+":""}}${{d.toFixed(2)}} (${{pct}}%)</b></span>`;
}});
new ResizeObserver(()=>{{const w=document.getElementById("w").offsetWidth;if(w>10){{mc.applyOptions({{width:w}});vc.applyOptions({{width:w}});}}}}).observe(document.getElementById("w"));
mc.timeScale().scrollToRealTime();
</script></body></html>"""
    components.html(html, height=548, scrolling=False)


# ═══════════════════════════════════════════════════════════════════════════════
#  9. DECISION ENGINE — Panel accionable basado en régimen GEX/VEX/CEX
# ═══════════════════════════════════════════════════════════════════════════════
def build_decision_panel(spot: float, gex_sum: dict, vex_sum: dict, cex_sum: dict,
                         dex_sum: dict, iv_atm: float, em_lo, em_hi,
                         dte_v: int, vol_regime: str = None) -> str:
    """
    Genera el análisis accionable. HTML string listo para st.markdown.
    """
    regime    = gex_sum.get("regime", "NEUTRAL")
    total_bn  = gex_sum.get("total_gex", 0) / 1e9
    gf        = gex_sum.get("gamma_flip")
    cw        = gex_sum.get("call_wall")
    pw        = gex_sum.get("put_wall")
    hvl       = gex_sum.get("hvl")
    flip_pct  = gex_sum.get("flip_pct")

    vex_total = vex_sum.get("total_vex", 0) / 1e6
    cex_total = cex_sum.get("total_cex", 0) / 1e6

    # Régimen principal
    if regime == "POSITIVE":
        reg_color   = _GREEN
        reg_title   = "🟢 LONG GAMMA  (régimen estabilizador)"
        reg_thesis  = (
            "Los dealers están <b>long gamma</b>: compran en caídas y venden en rallies. "
            "Esperá <b>rangos estrechos</b>, <b>mean-reversion intradía</b>, "
            "y <b>compresión de realized vol</b>. El spot tiende a ser atraído hacia el "
            f"<b>HVL en <code>${hvl:.0f}</code></b> (máximo hedging dealer)."
            if hvl else
            "Dealers long gamma — espera rangos estrechos y mean-reversion intradía."
        )
    elif regime == "NEGATIVE":
        reg_color   = _RED
        reg_title   = "🔴 SHORT GAMMA  (régimen amplificador)"
        reg_thesis  = (
            "Los dealers están <b>short gamma</b>: compran en rallies y venden en caídas, "
            "<b>amplificando</b> los movimientos. Esperá <b>volatilidad realizada alta</b>, "
            "<b>extension de trends</b>, y <b>potencial gap-through</b> de niveles clave. "
            f"Cruces por el <b>Zero Gamma (<code>${gf:.0f}</code>)</b> cambian el régimen."
            if gf else
            "Dealers short gamma — trend-following, momentum se acelera, risk-off elevado."
        )
    else:
        reg_color   = _ORANGE
        reg_title   = "🟡 NEUTRAL / TRANSITIONAL"
        reg_thesis  = "Mercado en equilibrio cerca del flip-point. Espera transición inminente."

    # Trade ideas basadas en régimen
    if regime == "POSITIVE":
        trade_bias = (
            f"<b>Estrategias favorecidas:</b> iron condors y credit spreads al ATM, "
            f"venta de straddles/strangles intradía, fade de los bordes del rango "
            f"(<code>${pw:.0f}</code> — <code>${cw:.0f}</code>). "
            f"<b>Evitar:</b> long gamma / long straddles; te decaen sin movimiento."
        )
    elif regime == "NEGATIVE":
        trade_bias = (
            f"<b>Estrategias favorecidas:</b> compra de volatilidad (long straddle/strangle ATM), "
            f"debit spreads direccionales con stop en Zero Gamma, <b>breakouts</b> de "
            f"<code>${cw:.0f}</code> (upside) o <code>${pw:.0f}</code> (downside). "
            f"<b>Evitar:</b> vender premium cerca de strikes con alto OI — "
            f"dealer hedging te perforará."
        )
    else:
        trade_bias = (
            f"Evita tomar posiciones direccionales hasta que el régimen se defina. "
            f"Vigilar cruce de spot sobre/bajo <code>${gf:.0f}</code> para confirmar."
        )

    # Vanna / Charm implications
    vanna_msg = ""
    if abs(vex_total) > 1:  # > $1M per vol point
        if vex_total > 0:
            vanna_msg = (f"<b>Vanna positiva (${vex_total:+.0f}M/vol pt):</b> "
                         f"si la IV sube (ej. VIX expansion), los dealers "
                         f"<b>compran spot</b> — flow de soporte. Si la IV baja "
                         f"(vol crush post-evento), <b>venden spot</b>.")
        else:
            vanna_msg = (f"<b>Vanna negativa (${vex_total:+.0f}M/vol pt):</b> "
                         f"si la IV sube, los dealers <b>venden spot</b> — "
                         f"amplifica sell-offs con vol expansion. Si la IV baja, "
                         f"<b>compran spot</b> — rally on vol crush.")

    charm_msg = ""
    if abs(cex_total) > 0.5:  # > $500K/day
        if cex_total > 0:
            charm_msg = (f"<b>Charm positivo (${cex_total:+.1f}M/día):</b> "
                         f"con el paso del tiempo, los dealers acumulan delta positiva "
                         f"y <b>compran</b> en los últimos minutos (bullish EOD flow). "
                         f"Especialmente notable en 0DTE y vencimiento.")
        else:
            charm_msg = (f"<b>Charm negativo (${cex_total:+.1f}M/día):</b> "
                         f"dealers pierden delta con el tiempo, <b>venden spot</b> al cierre. "
                         f"Sell-flow conforme se acerca el vencimiento.")

    # Niveles críticos
    levels_html = ""
    if cw: levels_html += f'<li><b>Call Wall</b> <code>${cw:.0f}</code> — resistencia; rally suele fallar/pausar aquí.</li>'
    if pw: levels_html += f'<li><b>Put Wall</b> <code>${pw:.0f}</code> — soporte; caída suele encontrar hedging dealer que amortigua.</li>'
    if gf: levels_html += f'<li><b>Zero Gamma</b> <code>${gf:.0f}</code> ({flip_pct:+.1f}% del spot) — cruce cambia el régimen.</li>' if flip_pct is not None else f'<li><b>Zero Gamma</b> <code>${gf:.0f}</code> — cruce cambia el régimen.</li>'
    if hvl and regime == "POSITIVE": levels_html += f'<li><b>HVL</b> <code>${hvl:.0f}</code> — punto de atracción del hedging en régimen long-gamma.</li>'
    if em_lo and em_hi: levels_html += f'<li><b>1σ Expected Move ({dte_v}d)</b> <code>${em_lo:.0f} — ${em_hi:.0f}</code> — rango estadístico esperado.</li>'

    # Vol context
    vol_html = ""
    if vol_regime and vol_regime != "—":
        vol_html = f'<p style="margin:0.6rem 0 0">🎯 <b>IV context:</b> {vol_regime}.</p>'

    panel = f"""
    <div class="decision-card">
      <div class="decision-title" style="color:{reg_color}">{reg_title}</div>
      <div class="decision-body">
        <p style="margin:0 0 0.7rem">{reg_thesis}</p>
        <p style="margin:0 0 0.5rem">📍 <b>Niveles clave:</b></p>
        <ul style="margin:0 0 0.7rem 1.4rem;padding:0;line-height:1.7">{levels_html}</ul>
        <p style="margin:0 0 0.5rem">⚡ <b>Playbook:</b></p>
        <p style="margin:0 0 0.7rem;padding-left:0.5rem;border-left:2px solid {reg_color}80">{trade_bias}</p>
        {'<p style="margin:0 0 0.5rem">📈 ' + vanna_msg + '</p>' if vanna_msg else ''}
        {'<p style="margin:0 0 0.5rem">⏰ ' + charm_msg + '</p>' if charm_msg else ''}
        {vol_html}
      </div>
    </div>
    """
    return panel


# ═══════════════════════════════════════════════════════════════════════════════
#  10. CHAIN TABLE
# ═══════════════════════════════════════════════════════════════════════════════
_CHAIN_COLS = ["Bid","Ask","Mark","Volume","OI","IV%","Delta","Gamma","Theta","Vega"]


def _fmt(v, col=""):
    if pd.isna(v):
        return '<span class="neu">—</span>'
    try:
        f = float(v)
    except (TypeError, ValueError):
        return str(v)
    if col == "IV%":
        color = "pos" if f < 30 else ("neg" if f > 60 else "hi")
        return f'<span class="{color}">{f:.1f}%</span>'
    if col in ("Volume","OI"):
        s = f"{int(f):,}"
        return f'<span class="hi">{s}</span>' if f > 0 else f'<span class="neu">{s}</span>'
    if col == "Delta":
        cls = "pos" if f > 0.5 else ("neg" if f < -0.5 else ("hi" if abs(f) > 0.3 else "neu"))
        return f'<span class="{cls}">{f:+.3f}</span>'
    if col in ("Gamma","Vega"):
        return f'<span class="hi">{f:.4f}</span>' if f > 0 else f'<span class="neu">{f:.4f}</span>'
    if col == "Theta":
        return f'<span class="neg">{f:.3f}</span>'
    if col in ("Bid","Ask","Mark"):
        return f'<span class="hi">{f:.2f}</span>' if f > 0 else f'<span class="neu">—</span>'
    return f"{f:.2f}"


def build_table(c_df, p_df, spot, mode):
    c_df = c_df.sort_values("Strike") if not c_df.empty else c_df
    p_df = p_df.sort_values("Strike") if not p_df.empty else p_df
    strikes = sorted(set(
        (c_df["Strike"].tolist() if not c_df.empty else []) +
        (p_df["Strike"].tolist() if not p_df.empty else [])
    ))
    if not strikes:
        return "<p style='color:#404060;padding:1rem'>Sin datos para esta selección.</p>"
    atm_s = min(strikes, key=lambda s: abs(s - spot))
    c_idx = c_df.set_index("Strike").to_dict("index") if not c_df.empty else {}
    p_idx = p_df.set_index("Strike").to_dict("index") if not p_df.empty else {}
    c_cols = [c for c in _CHAIN_COLS if not c_df.empty and c in c_df.columns]
    p_cols = [c for c in _CHAIN_COLS if not p_df.empty and c in p_df.columns]

    def hdr(cols, side):
        cls = "call-hdr" if side == "call" else ("put-hdr" if side == "put" else "mid-hdr")
        return "".join(f'<th class="{cls} ctr">{c}</th>' for c in cols)

    def cells(row, cols):
        return "".join(f"<td>{_fmt(row.get(c, float('nan')), c)}</td>" for c in cols)

    h = '<div class="chain-wrap"><table class="chain">'
    if mode == "calls":
        h += "<thead><tr><th class='lft'>STRIKE</th>" + hdr(c_cols, "call") + "</tr></thead><tbody>"
        for s in strikes:
            r = c_idx.get(s, {})
            itm = r.get("ITM", False)
            rc  = "atm-row" if s == atm_s else ("itm-c" if itm else "")
            sc  = "atm-strike" if s == atm_s else "strike"
            pct = f'<span style="font-size:0.6rem;color:#404060;margin-left:4px">{(s/spot-1)*100:+.1f}%</span>'
            h  += f'<tr class="{rc}"><td class="lft"><span class="{sc}">${s:.1f}</span>{pct}</td>'
            h  += cells(r, c_cols) + "</tr>"
    elif mode == "puts":
        h += "<thead><tr><th class='lft'>STRIKE</th>" + hdr(p_cols, "put") + "</tr></thead><tbody>"
        for s in strikes:
            r = p_idx.get(s, {})
            itm = r.get("ITM", False)
            rc  = "atm-row" if s == atm_s else ("itm-p" if itm else "")
            sc  = "atm-strike" if s == atm_s else "strike"
            pct = f'<span style="font-size:0.6rem;color:#404060;margin-left:4px">{(s/spot-1)*100:+.1f}%</span>'
            h  += f'<tr class="{rc}"><td class="lft"><span class="{sc}">${s:.1f}</span>{pct}</td>'
            h  += cells(r, p_cols) + "</tr>"
    else:
        h += ("<thead><tr>"
              f'<th colspan="{len(c_cols)}" class="call-hdr ctr" style="border-right:1px solid #22c55e33;">▲ CALLS</th>'
              '<th class="mid-hdr ctr" style="border-left:1px solid #22c55e33;border-right:1px solid #f43f5e33;">STRIKE</th>'
              f'<th colspan="{len(p_cols)}" class="put-hdr ctr" style="border-left:1px solid #f43f5e33;">▼ PUTS</th>'
              "</tr><tr>"
              + hdr(c_cols, "call")
              + '<th class="mid-hdr ctr" style="border-left:1px solid #22c55e33;border-right:1px solid #f43f5e33;">$</th>'
              + hdr(p_cols, "put") + "</tr></thead><tbody>")
        for s in strikes:
            cr, pr = c_idx.get(s, {}), p_idx.get(s, {})
            c_itm, p_itm = cr.get("ITM", False), pr.get("ITM", False)
            is_atm = s == atm_s
            h += "<tr>"
            for col in c_cols:
                bg  = "background:rgba(34,197,94,0.04);" if c_itm and not is_atm else ""
                h  += f'<td style="{bg}">{_fmt(cr.get(col, float("nan")), col)}</td>'
            mid = ("background:rgba(249,115,22,0.1);color:#f97316;font-weight:800;"
                   if is_atm else "background:#0d0d1a;color:#9090b0;font-weight:600;")
            pct  = f'{(s/spot-1)*100:+.1f}%'
            h   += (f'<td class="ctr" style="{mid}border-left:1px solid #22c55e22;'
                    f'border-right:1px solid #f43f5e22;">'
                    f'${s:.1f} <span style="font-size:0.6rem;opacity:0.5">{pct}</span></td>')
            for col in p_cols:
                bg  = "background:rgba(244,63,94,0.04);" if p_itm and not is_atm else ""
                h  += f'<td style="{bg}">{_fmt(pr.get(col, float("nan")), col)}</td>'
            h += "</tr>"
    return h + "</tbody></table></div>"


# ═══════════════════════════════════════════════════════════════════════════════
#  11. RENDER MODULES
# ═══════════════════════════════════════════════════════════════════════════════

def _kv(label, value, color="#e0e0f0", sub=None):
    sub_html = f'<div class="kpi-sub">{sub}</div>' if sub else ""
    return (f'<div class="kpi-item">'
            f'<div class="kpi-lbl">{label}</div>'
            f'<div class="kpi-val" style="color:{color}">{value}</div>'
            f'{sub_html}</div>')


def render_gex_module(symbol: str, calls_all: pd.DataFrame, puts_all: pd.DataFrame,
                      spot: float, max_dte: int, min_oi: int,
                      focus_pct: float, dte_v: int, iv_atm: float,
                      em_lo, em_hi, vol_regime: str = None):
    """
    Módulo GEX completo estilo gexbot.com:
      - KPI panel con régimen, totals, flip, walls, HVL
      - Decision panel accionable
      - GEX profile principal (vertical bars)
      - Cumulative GEX
      - GEX por expiración
      - Vanna Exposure profile
      - Charm Exposure profile
    """
    gex_df, gex_sum = compute_gex_profile(calls_all, puts_all, spot,
                                          max_dte=max_dte, min_oi=min_oi)
    vex_df, vex_sum = compute_vex_profile(calls_all, puts_all, spot,
                                          max_dte=max_dte, min_oi=min_oi)
    cex_df, cex_sum = compute_cex_profile(calls_all, puts_all, spot,
                                          max_dte=max_dte, min_oi=min_oi)
    dex_df, dex_sum = compute_dex_profile(calls_all, puts_all, spot,
                                          max_dte=max_dte, min_oi=min_oi)
    exp_df          = compute_gex_by_expiry(calls_all, puts_all, spot,
                                            max_dte=max_dte, min_oi=min_oi)

    if gex_df.empty:
        st.warning("No hay datos suficientes para calcular GEX. Revisa el filtro DTE y min OI, "
                   "o verifica que la cadena tenga Gamma/OI válidos.")
        return None, None

    # ── KPI HEADER ──────────────────────────────────────────────────────────
    regime    = gex_sum.get("regime", "NEUTRAL")
    r_color   = _GREEN if regime == "POSITIVE" else (_RED if regime == "NEGATIVE" else _ORANGE)
    total_bn  = gex_sum.get("total_gex", 0) / 1e9
    per1_mn   = abs(gex_sum.get("total_gex", 0)) / 1e6
    call_bn   = gex_sum.get("call_gex", 0) / 1e9
    put_bn    = gex_sum.get("put_gex", 0) / 1e9
    gf        = gex_sum.get("gamma_flip")
    cw        = gex_sum.get("call_wall")
    pw        = gex_sum.get("put_wall")
    hvl       = gex_sum.get("hvl")
    flip_pct  = gex_sum.get("flip_pct")

    hdr = '<div class="kpi-panel">'
    hdr += _kv("Régimen", f"{regime} Γ", r_color)
    hdr += _kv("Net GEX", f"${total_bn:+.2f}B", r_color, sub="per 1% move")
    hdr += _kv("Call GEX", f"${call_bn:+.2f}B", _GREEN)
    hdr += _kv("Put GEX",  f"${put_bn:+.2f}B", _RED)
    hdr += _kv("Zero Γ", f"${gf:.0f}" if gf else "—", _PURPLE,
               sub=f"{flip_pct:+.1f}% spot" if flip_pct is not None else None)
    hdr += _kv("Call Wall", f"${cw:.0f}" if cw else "—", _GREEN)
    hdr += _kv("Put Wall",  f"${pw:.0f}" if pw else "—", _RED)
    hdr += _kv("HVL", f"${hvl:.0f}" if hvl else "—", _CYAN, sub="attractor")
    hdr += '</div>'
    st.markdown(hdr, unsafe_allow_html=True)

    # ── DECISION PANEL ──────────────────────────────────────────────────────
    panel = build_decision_panel(spot, gex_sum, vex_sum, cex_sum, dex_sum,
                                 iv_atm, em_lo, em_hi, dte_v, vol_regime)
    st.markdown(panel, unsafe_allow_html=True)

    # ── MAIN GEX PROFILE ────────────────────────────────────────────────────
    st.markdown('<p class="bb-header">GEX PROFILE  ·  Gamma Exposure por Strike</p>',
                unsafe_allow_html=True)
    st.caption(
        "Calls → derecha (verde), Puts → izquierda (rojo), Net GEX → diamantes amarillos. "
        "Líneas: SPOT (naranja), Call/Put Walls (verde/rojo), Zero Γ (morado), HVL (cyan). "
        "Unidad: $M per 1% move."
    )
    fig_gex = chart_gex_profile(gex_df, spot, gex_sum, symbol, focus_pct=focus_pct)
    if fig_gex:
        st.plotly_chart(fig_gex, use_container_width=True)

    # ── CUMULATIVE + BY EXPIRY ──────────────────────────────────────────────
    col_l, col_r = st.columns([3, 2])
    with col_l:
        st.markdown('<p class="bb-header" style="margin-top:0.3rem">PERFIL ACUMULADO</p>',
                    unsafe_allow_html=True)
        st.caption("Cruce por cero = Zero Gamma (cambio de régimen).")
        fig_cum = chart_cum_gex(gex_df, spot, gex_sum)
        if fig_cum:
            st.plotly_chart(fig_cum, use_container_width=True)
    with col_r:
        st.markdown('<p class="bb-header" style="margin-top:0.3rem">GEX POR VENCIMIENTO</p>',
                    unsafe_allow_html=True)
        st.caption("Top 14 expiraciones por |Net GEX|.")
        fig_exp = chart_gex_by_expiry_pro(exp_df)
        if fig_exp:
            st.plotly_chart(fig_exp, use_container_width=True)
        else:
            st.caption("Requiere ≥ 1 vencimiento con datos.")

    # ── VEX (VANNA EXPOSURE) ────────────────────────────────────────────────
    st.markdown('<p class="bb-header">VANNA EXPOSURE  ·  $ Delta por +1 pto IV</p>',
                unsafe_allow_html=True)
    st.caption(
        "**VEX(k) = Vanna × OI × 100 × S × 0.01 × sign**. "
        "Positivo → dealer compra spot si IV sube (buy-flow on vol expansion). "
        "Negativo → dealer vende spot en vol expansion. "
        "Clave para entender flow en eventos de vol (FOMC, CPI, earnings)."
    )
    if not vex_df.empty:
        fig_vex = chart_vex_profile(vex_df, spot, vex_sum, symbol, focus_pct=focus_pct)
        if fig_vex:
            st.plotly_chart(fig_vex, use_container_width=True)
    else:
        st.caption("VEX requiere IV% y DTE válidos en la cadena.")

    # ── CEX (CHARM EXPOSURE) ────────────────────────────────────────────────
    st.markdown('<p class="bb-header">CHARM EXPOSURE  ·  $ Delta decay por día</p>',
                unsafe_allow_html=True)
    st.caption(
        "**CEX(k) = Charm × OI × 100 × S × sign**. "
        "Decaimiento del delta del dealer por día calendario. "
        "Positivo → dealer acumula delta long con el tiempo (buy-flow EOD/cerca vencimiento). "
        "Esencial para 0DTE y pin risk en OPEX."
    )
    if not cex_df.empty:
        fig_cex = chart_cex_profile(cex_df, spot, cex_sum, symbol, focus_pct=focus_pct)
        if fig_cex:
            st.plotly_chart(fig_cex, use_container_width=True)
    else:
        st.caption("CEX requiere IV% y DTE válidos en la cadena.")

    # ── DEX (DELTA EXPOSURE) ────────────────────────────────────────────────
    st.markdown('<p class="bb-header">DELTA EXPOSURE  ·  Sesgo direccional</p>',
                unsafe_allow_html=True)
    st.caption(
        "DEX = Σ Δ × OI × 100 × S. Call-heavy → soporte implícito. Put-heavy → resistencia implícita."
    )
    if not dex_df.empty:
        fig_dex = chart_dex_profile(dex_df, spot, dex_sum, symbol, focus_pct=focus_pct)
        if fig_dex:
            st.plotly_chart(fig_dex, use_container_width=True)

    return gex_sum, gex_df


def render_vol_module(symbol: str, atm_iv: float, spot: float, price_df: pd.DataFrame):
    if price_df.empty:
        st.caption("No se pudo cargar el historial para el análisis de vol.")
        return None
    analytics = calc_vol_analytics(price_df, atm_iv)
    if not analytics:
        st.caption("Datos insuficientes.")
        return None

    hv20 = analytics.get("hv20"); hv30 = analytics.get("hv30")
    hv60 = analytics.get("hv60"); hv90 = analytics.get("hv90")
    ratio = analytics.get("iv_hv_ratio"); spread = analytics.get("iv_hv_spread")
    hv_pct = analytics.get("hv_percentile"); iv_rank = analytics.get("iv_rank")
    regime = analytics.get("vol_regime", "—")
    skew = analytics.get("skewness"); kurt = analytics.get("kurtosis")

    regime_clr = (_RED if regime == "IV CARA" else
                  (_GREEN if regime == "IV BARATA" else _ORANGE))

    hdr = '<div class="kpi-panel">'
    hdr += _kv("Régimen vol", regime, regime_clr)
    hdr += _kv("ATM IV",   f"{atm_iv:.1f}%" if atm_iv else "—")
    hdr += _kv("HV20", f"{hv20:.1f}%" if hv20 else "—", sub="20d")
    hdr += _kv("HV30", f"{hv30:.1f}%" if hv30 else "—", sub="30d")
    hdr += _kv("HV60", f"{hv60:.1f}%" if hv60 else "—", sub="60d")
    hdr += _kv("IV / HV30", f"{ratio:.2f}x" if ratio else "—", regime_clr,
               sub=">1.30 cara · <0.80 barata")
    hdr += _kv("IV − HV30", (f"+{spread:.1f}%" if spread >= 0 else f"{spread:.1f}%") if spread is not None else "—",
               _RED if (spread or 0) > 0 else _GREEN)
    hdr += _kv("IV Rank", f"{iv_rank:.0f}" if iv_rank is not None else "—", sub="0-100")
    hdr += _kv("Skew", f"{skew:.3f}" if skew is not None else "—",
               _RED if (skew or 0) < -0.5 else "#e0e0f0")
    hdr += _kv("Kurt ex.", f"{kurt:.3f}" if kurt is not None else "—")
    hdr += '</div>'
    st.markdown(hdr, unsafe_allow_html=True)

    if ratio is not None:
        if ratio > 1.3:
            interp = (f"📛 <b>IV cara</b> — opciones cotizan {ratio:.1f}x la HV30. "
                      "Ventaja estadística: venta de vol (credit spreads, iron condors).")
        elif ratio < 0.8:
            interp = (f"💚 <b>IV barata</b> — opciones cotizan {ratio:.1f}x la HV30. "
                      "Ventaja: compra de vol (straddles, debit spreads, calendars).")
        else:
            interp = f"🟡 <b>IV neutral</b> — {ratio:.1f}x la HV30. Prioriza direccionales."
    else:
        interp = "Datos insuficientes."

    st.markdown(
        f'<p style="font-size:0.73rem;color:#7070a0;font-family:{_FONT_MONO};'
        f'margin:0 0 1rem;line-height:1.6">{interp}</p>',
        unsafe_allow_html=True)

    c_cone, c_hist = st.columns([3, 2])
    with c_cone:
        st.markdown('<p class="bb-header" style="margin-top:0">VOLATILITY CONE</p>',
                    unsafe_allow_html=True)
        fig_cone = chart_vol_cone(analytics, atm_iv, symbol)
        if fig_cone:
            st.plotly_chart(fig_cone, use_container_width=True)
    with c_hist:
        st.markdown('<p class="bb-header" style="margin-top:0">HV30 vs ATM IV</p>',
                    unsafe_allow_html=True)
        fig_hv = chart_iv_hv_history(analytics, atm_iv)
        if fig_hv:
            st.plotly_chart(fig_hv, use_container_width=True)

    st.markdown('<p class="bb-header">DISTRIBUCIÓN DE RETORNOS</p>',
                unsafe_allow_html=True)
    fig_rd = chart_returns_dist(analytics, symbol)
    if fig_rd:
        st.plotly_chart(fig_rd, use_container_width=True)

    return regime


# ═══════════════════════════════════════════════════════════════════════════════
#  12. MAIN DASHBOARD
# ═══════════════════════════════════════════════════════════════════════════════
def show_dashboard():
    st.markdown(CSS, unsafe_allow_html=True)
    st.markdown("<div style='height:0.6rem'></div>", unsafe_allow_html=True)

    today = datetime.date.today()

    # ── TOP BAR ─────────────────────────────────────────────────────────────
    b1, b2, b3, b4, b5, b6 = st.columns([1.0, 1.4, 1.8, 1.0, 1.0, 0.6])
    with b1:
        st.markdown("<span style='font-family:JetBrains Mono,monospace;font-size:1rem;font-weight:800;color:#f97316;letter-spacing:0.12em;line-height:2.4;display:block'>▤ OPTIONS</span>", unsafe_allow_html=True)
    with b2:
        symbol = st.text_input("sym", value=st.session_state.get("symbol","SPY"),
            placeholder="SPY, AAPL, QQQ…", label_visibility="collapsed").upper().strip()
    with b3:
        all_exps = st.session_state.get("all_exps", ["—"])
        sel_exp  = st.selectbox("exp", options=all_exps, label_visibility="collapsed",
                                key="sel_exp")
    with b4:
        strike_count = st.selectbox("strikes", options=[10,15,20,25,30,40,50,60],
                                    index=4, label_visibility="collapsed")
    with b5:
        auto_refresh = st.toggle("Auto 30s", value=False, key="auto_refresh_toggle")
    with b6:
        if st.button("EXIT", use_container_width=True):
            for k in ["tokens","connected","chain_data","last_sym","last_strikes",
                      "symbol","app_key","app_secret","callback_url",
                      "oauth_pending","oauth_code","all_exps","sel_exp",
                      "_last_refresh_count"]:
                st.session_state.pop(k, None)
            for k in [k for k in list(st.session_state.keys())
                      if k.startswith("intra_") or k.startswith("ph_")]:
                st.session_state.pop(k, None)
            st.rerun()

    # ── ADVANCED FILTERS ────────────────────────────────────────────────────
    with st.expander("⚙️ Filtros avanzados (GEX calibration)", expanded=False):
        f1, f2, f3 = st.columns(3)
        with f1:
            max_dte = st.slider(
                "Max DTE (para exposures)", 7, 365, 60, step=1,
                help="Filtra opciones con DTE > este valor. 45-60d = estándar gexbot. "
                     "Incluye LEAPS solo si subes el límite."
            )
        with f2:
            min_oi = st.slider(
                "Min OI por strike", 0, 1000, 0, step=50,
                help="Filtra strikes ilíquidos. 100+ recomendado para SPY/QQQ, 0 para tickers pequeños."
            )
        with f3:
            focus_pct = st.slider(
                "Focus ± % del spot", 3, 25, 8, step=1, format="±%d%%",
                help="Rango de strikes a mostrar en los charts. 8-10% estándar para índices."
            ) / 100.0

    st.markdown('<hr class="bb-divider">', unsafe_allow_html=True)

    # ── LOAD CHAIN ──────────────────────────────────────────────────────────
    need_load = symbol and (
        st.session_state.get("last_sym") != symbol
        or st.session_state.get("last_strikes") != strike_count
        or "chain_data" not in st.session_state
    )
    if need_load:
        with st.spinner(f"Fetching {symbol}…"):
            data, err = fetch_chain(
                symbol, strike_count,
                today.strftime("%Y-%m-%d"),
                (today + datetime.timedelta(days=180)).strftime("%Y-%m-%d"),
            )
        if err:
            st.error(f"❌ {err}")
            return
        if not data or data.get("status") == "FAILED":
            st.warning(f"No se encontraron opciones para **{symbol}**.")
            return
        st.session_state.chain_data    = data
        st.session_state.last_sym      = symbol
        st.session_state.last_strikes  = strike_count
        st.session_state.symbol        = symbol
        st.session_state.last_refresh  = datetime.datetime.now()
        calls_r, puts_r, _ = parse_chain(data)
        calls_c = clean(calls_r)
        exps = sorted(set(calls_c["Expiry"].tolist() if not calls_c.empty and "Expiry" in calls_c.columns else []))
        st.session_state.all_exps = exps
        for k in list(st.session_state.keys()):
            if k.startswith("intra_") and not k.startswith(f"intra_{symbol}_"):
                del st.session_state[k]
        st.rerun()

    if "chain_data" not in st.session_state:
        st.markdown('<p style="color:#404060;text-align:center;margin-top:3rem;font-family:JetBrains Mono,monospace;font-size:0.85rem;">Ingresa un símbolo para comenzar</p>', unsafe_allow_html=True)
        return

    # ── PARSE ───────────────────────────────────────────────────────────────
    data = st.session_state.chain_data
    calls_raw, puts_raw, ul = parse_chain(data)
    calls_all = clean(calls_raw)
    puts_all  = clean(puts_raw)

    sel_exp = st.session_state.get("sel_exp", (st.session_state.get("all_exps") or [""])[0])
    calls = by_exp(calls_all, sel_exp).sort_values("Strike") if not calls_all.empty else calls_all
    puts  = by_exp(puts_all,  sel_exp).sort_values("Strike") if not puts_all.empty  else puts_all

    spot  = float(ul.get("mark") or ul.get("last") or ul.get("close") or 0)
    chg   = float(ul.get("netChange", 0) or 0)
    chg_p = float(ul.get("percentChange", 0) or 0)
    bid_u = float(ul.get("bid", 0) or 0)
    ask_u = float(ul.get("ask", 0) or 0)
    vol_u = int(ul.get("totalVolume", 0) or 0)

    # ── ANALYTICS ───────────────────────────────────────────────────────────
    dte_v = 0
    if not calls.empty and "DTE" in calls.columns:
        _dte_vals = calls["DTE"].dropna()
        if len(_dte_vals) > 0:
            try: dte_v = int(float(str(_dte_vals.values[0]).split(".")[0]))
            except Exception: dte_v = 0

    iv_atm = calc_atm_iv(calls_all, spot) or calc_atm_iv(calls, spot)
    p_c    = calc_pcr(calls, puts)
    mp     = calc_max_pain(calls, puts)
    em_lo, em_hi = calc_expected_move(spot, iv_atm, dte_v)
    skew_df = calc_iv_skew(calls_all, puts_all, spot)
    ts_df   = calc_term_structure(calls_all, spot, puts_all)
    last_refresh = st.session_state.get("last_refresh", datetime.datetime.now())

    # Compute GEX upfront for top metrics (using default filters to match module)
    _, _top_gex_sum = compute_gex_profile(calls_all, puts_all, spot,
                                          max_dte=max_dte, min_oi=min_oi)
    total_gex_bn = _top_gex_sum.get("total_gex", 0) / 1e9 if _top_gex_sum else None

    # Price history (1yr daily) for vol analytics — cached per symbol/day
    ph_key = f"ph_{symbol}_{today}"
    if ph_key not in st.session_state:
        ph_df, ph_err = fetch_price_history(symbol)
        st.session_state[ph_key]          = ph_df
        st.session_state[ph_key + "_err"] = ph_err
    price_df  = st.session_state.get(ph_key, pd.DataFrame())
    price_err = st.session_state.get(ph_key + "_err", "")

    # ── DIAGNOSTICS ─────────────────────────────────────────────────────────
    with st.expander("🔍 Diagnóstico", expanded=False):
        d1, d2, d3, d4 = st.columns(4)
        d1.metric("calls_all",  len(calls_all))
        d2.metric("puts_all",   len(puts_all))
        d3.metric("ATM IV",     f"{iv_atm:.1f}%" if iv_atm else "None ⚠️")
        d4.metric("price rows", len(price_df))
        d5, d6, d7, d8 = st.columns(4)
        iv_c = int((calls_all["IV%"] > 0.01).sum() if "IV%" in calls_all.columns else 0)
        iv_p = int((puts_all["IV%"]  > 0.01).sum() if "IV%" in puts_all.columns  else 0)
        d5.metric("IV válidos calls", iv_c)
        d6.metric("IV válidos puts",  iv_p)
        d7.metric("skew rows",  len(skew_df))
        d8.metric("ts rows",    len(ts_df))
        if price_err:
            st.error(f"Price history: {price_err}")

    # ── METRICS ROW ─────────────────────────────────────────────────────────
    m1,m2,m3,m4,m5,m6,m7,m8 = st.columns(8)
    m1.metric("PRECIO",    f"${spot:.2f}",    f"{chg:+.2f}  {chg_p:+.1f}%")
    m2.metric("BID / ASK", f"{bid_u:.2f} / {ask_u:.2f}")
    m3.metric("VOLUMEN",   f"{vol_u:,}")
    m4.metric("DTE",       f"{dte_v}d")
    m5.metric("ATM IV",    f"{iv_atm:.1f}%" if iv_atm else "—")
    m6.metric("P/C RATIO", f"{p_c:.2f}" if p_c else "—")
    m7.metric("MAX PAIN",  f"${mp:.0f}" if mp else "—")
    m8.metric("NET GEX",   f"${total_gex_bn:+.2f}B" if total_gex_bn is not None else "—",
              "LONG Γ" if (total_gex_bn or 0) >= 0 else "SHORT Γ")

    if em_lo and em_hi:
        move_pct = round((em_hi - spot) / spot * 100, 1)
        st.markdown(
            f'<p style="font-size:0.72rem;color:#404060;font-family:JetBrains Mono,monospace;margin:0.3rem 0 0;">'
            f'1σ Expected Move ({dte_v}d): '
            f'<span style="color:#a855f7">${em_lo:.2f} — ${em_hi:.2f}</span>'
            f'  <span style="color:#505070">(±{move_pct}%)</span>'
            f'  &nbsp;·&nbsp; Actualizado: {last_refresh.strftime("%H:%M:%S")}'
            f'</p>',
            unsafe_allow_html=True,
        )

    st.markdown('<hr class="bb-divider">', unsafe_allow_html=True)

    # ── VOL ANALYTICS first (para pasar regime al decision engine) ──────────
    # Pero renderizamos GEX primero con el regime como input
    vol_regime_str = None
    analytics = calc_vol_analytics(price_df, iv_atm) if (not price_df.empty and iv_atm) else {}
    if analytics:
        vol_regime_str = analytics.get("vol_regime")

    # ── GEX MODULE (main event) ─────────────────────────────────────────────
    st.markdown('<p class="bb-header">GAMMA EXPOSURE MODULE  ·  Dealer Flow Analytics</p>',
                unsafe_allow_html=True)
    gex_sum, gex_df = render_gex_module(
        symbol, calls_all, puts_all, spot,
        max_dte=max_dte, min_oi=min_oi, focus_pct=focus_pct,
        dte_v=dte_v, iv_atm=iv_atm, em_lo=em_lo, em_hi=em_hi,
        vol_regime=vol_regime_str,
    )

    st.markdown('<hr class="bb-divider">', unsafe_allow_html=True)

    # ── INTRADAY CHART ──────────────────────────────────────────────────────
    st.markdown('<p class="bb-header">PRECIO INTRADAY  ·  CANDLESTICK + NIVELES GEX</p>',
                unsafe_allow_html=True)
    st.caption(
        "Interactiva: rueda=pan · Ctrl+rueda=zoom · doble-click=reset. "
        "Niveles proyectados: SPOT · CW · PW · GF · HVL · MP · EM± . Hora CDMX (UTC-6)."
    )
    c_ctrl1, c_ctrl2, _ = st.columns([1, 1, 4])
    with c_ctrl1:
        intra_freq = st.selectbox("Frecuencia", [1, 5], index=0,
                                  format_func=lambda x: f"{x} min",
                                  key="intra_freq")
    with c_ctrl2:
        intra_days = st.selectbox("Días", [1, 2, 3, 5], index=0, key="intra_days")

    _now_cdmx = datetime.datetime.now(_CDMX_TZ)
    _bucket_min = (_now_cdmx.minute // 5) * 5
    now_cdmx_str = _now_cdmx.strftime("%Y%m%d_%H") + f"{_bucket_min:02d}"
    intra_key = f"intra_{symbol}_{intra_freq}_{intra_days}_{now_cdmx_str}"
    intra_err_key = intra_key + "_err"

    stale = [k for k in list(st.session_state.keys())
             if k.startswith(f"intra_{symbol}_")
             and k not in (intra_key, intra_err_key)]
    for k in stale:
        del st.session_state[k]

    if intra_key not in st.session_state:
        with st.spinner(f"Cargando velas {intra_freq}min…"):
            intra_df, intra_err = fetch_intraday(symbol, intra_freq, intra_days)
        st.session_state[intra_key]     = intra_df
        st.session_state[intra_err_key] = intra_err
    intra_df  = st.session_state.get(intra_key, pd.DataFrame())
    intra_err = st.session_state.get(intra_err_key, "")

    _, col_ref = st.columns([5, 1])
    with col_ref:
        if st.button("↺ Refresh", key="intra_refresh"):
            for k in [intra_key, intra_key + "_err"]:
                st.session_state.pop(k, None)
            st.rerun()

    if not intra_df.empty and gex_sum:
        render_tv_chart(intra_df, spot, gex_sum, mp, em_lo, em_hi, freq_min=intra_freq)
    else:
        if not intra_df.empty:
            st.caption("GEX data no disponible para proyectar niveles en el chart.")
        else:
            st.caption("Datos intraday no disponibles. "
                + (f"Error: `{intra_err}`" if intra_err else "Mercado cerrado o símbolo sin datos."))

    st.markdown('<hr class="bb-divider">', unsafe_allow_html=True)

    # ── GREEKS surface (for selected expiry) ───────────────────────────────
    st.markdown('<p class="bb-header">GREEKS SURFACE  (vencimiento seleccionado)</p>',
                unsafe_allow_html=True)
    st.plotly_chart(chart_greeks(calls, puts, spot), use_container_width=True)

    st.markdown('<hr class="bb-divider">', unsafe_allow_html=True)

    # ── IV SKEW ─────────────────────────────────────────────────────────────
    st.markdown('<p class="bb-header">IV SKEW  &  VOLATILITY SMILE</p>',
                unsafe_allow_html=True)
    if not skew_df.empty:
        fig_skew = chart_iv_skew(skew_df, spot)
        if fig_skew:
            st.plotly_chart(fig_skew, use_container_width=True)
    else:
        st.caption("IV Skew: requiere calls y puts con strikes compartidos. Aumenta el # de strikes.")

    st.markdown('<hr class="bb-divider">', unsafe_allow_html=True)

    # ── TERM STRUCTURE ──────────────────────────────────────────────────────
    st.markdown('<p class="bb-header">TERM STRUCTURE  (IV por vencimiento)</p>',
                unsafe_allow_html=True)
    if not ts_df.empty:
        c_ts, c_ts_tbl = st.columns([3, 1])
        with c_ts:
            fig_ts = chart_term_structure(ts_df)
            if fig_ts:
                st.plotly_chart(fig_ts, use_container_width=True)
        with c_ts_tbl:
            st.markdown("<br>", unsafe_allow_html=True)
            tbl = '<table style="font-family:JetBrains Mono,monospace;font-size:0.72rem;width:100%;">'
            tbl += ('<tr><th style="color:#505070;text-align:left;padding:2px 6px">Exp</th>'
                    '<th style="color:#505070;text-align:right;padding:2px 6px">DTE</th>'
                    '<th style="color:#505070;text-align:right;padding:2px 6px">ATM IV</th></tr>')
            for _, row in ts_df.iterrows():
                iv_c = (_GREEN if row["ATM_IV"] < 30 else
                        (_RED if row["ATM_IV"] > 60 else _ORANGE))
                tbl += (f'<tr>'
                        f'<td style="color:#7070a0;padding:2px 6px">{str(row["Expiry"])[:10]}</td>'
                        f'<td style="text-align:right;color:#9090b0;padding:2px 6px">{int(row["DTE"])}</td>'
                        f'<td style="text-align:right;color:{iv_c};padding:2px 6px">{row["ATM_IV"]:.1f}%</td>'
                        f'</tr>')
            tbl += "</table>"
            st.markdown(tbl, unsafe_allow_html=True)
    else:
        st.caption("Term Structure no disponible.")

    st.markdown('<hr class="bb-divider">', unsafe_allow_html=True)

    # ── OI / VOLUME ─────────────────────────────────────────────────────────
    st.markdown('<p class="bb-header">OPEN INTEREST  &  VOLUME</p>', unsafe_allow_html=True)
    st.plotly_chart(chart_oi_volume(calls, puts, spot, em_lo, em_hi), use_container_width=True)

    st.markdown('<hr class="bb-divider">', unsafe_allow_html=True)

    # ── VOL ANALYSIS ────────────────────────────────────────────────────────
    st.markdown('<p class="bb-header">VOLATILITY ANALYSIS  ·  HV · IV Rank · Cone · Returns</p>',
                unsafe_allow_html=True)
    if not price_df.empty:
        render_vol_module(symbol, iv_atm, spot, price_df)
    else:
        st.caption(f"Análisis no disponible. " + (f"Error: `{price_err}`" if price_err else ""))

    st.markdown('<hr class="bb-divider">', unsafe_allow_html=True)

    # ── CHAIN TABLE ─────────────────────────────────────────────────────────
    st.markdown('<p class="bb-header">OPTIONS CHAIN  (vencimiento seleccionado)</p>',
                unsafe_allow_html=True)
    mode = st.radio("Vista", ["both", "calls", "puts"], index=0, horizontal=True,
                    key="chain_mode", label_visibility="collapsed")
    st.markdown(build_table(calls, puts, spot, mode), unsafe_allow_html=True)

    # ── FOOTER ──────────────────────────────────────────────────────────────
    st.markdown(
        f'<p class="footer">OPTIONS TERMINAL  ·  {symbol}  ·  {last_refresh.strftime("%Y-%m-%d %H:%M:%S")} UTC'
        f'  ·  Charles Schwab API  ·  Datos en tiempo real'
        f'  ·  No constituye asesoramiento financiero</p>',
        unsafe_allow_html=True,
    )

    # ── AUTO-REFRESH ────────────────────────────────────────────────────────
    if auto_refresh:
        try:
            from streamlit_autorefresh import st_autorefresh
            count = st_autorefresh(interval=30_000, key="chain_autorefresh")
            if count and count != st.session_state.get("_last_refresh_count"):
                st.session_state["_last_refresh_count"] = count
                st.session_state.pop("chain_data", None)
                st.rerun()
            st.caption("🔄 Auto-refresh activo cada 30s (no bloqueante).")
        except ImportError:
            elapsed = (datetime.datetime.now() - last_refresh).seconds
            remaining = max(0, 30 - elapsed)
            if remaining == 0:
                st.session_state.pop("chain_data", None)
                st.rerun()
            else:
                st.caption(f"🔄 Actualizando en {remaining}s…")
                time.sleep(1)
                st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
#  13. ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════
def main():
    # Capture OAuth code from URL
    if "code" in st.query_params:
        if not st.session_state.get("connected") and "oauth_code" not in st.session_state:
            st.session_state["oauth_code"] = st.query_params["code"]
        st.query_params.clear()
        st.rerun()
        return

    # Process captured code
    if "oauth_code" in st.session_state and not st.session_state.get("connected"):
        code     = st.session_state.pop("oauth_code")
        callback = st.session_state.get("callback_url") or _secret("CALLBACK_URL", "https://127.0.0.1")
        app_key  = st.session_state.get("app_key")      or _secret("APP_KEY")
        app_sec  = st.session_state.get("app_secret")   or _secret("APP_SECRET")
        st.markdown(CSS, unsafe_allow_html=True)
        _, col, _ = st.columns([1, 1.2, 1])
        with col:
            if not app_key or not app_sec:
                st.error("No se encontraron APP_KEY / APP_SECRET.")
                return
            with st.spinner("Autenticando…"):
                creds = base64.b64encode(f"{app_key}:{app_sec}".encode()).decode()
                r = requests.post(_TOKEN_URL,
                    headers={"Authorization": f"Basic {creds}",
                             "Content-Type": "application/x-www-form-urlencoded"},
                    data={"grant_type": "authorization_code",
                          "code": code, "redirect_uri": callback}, timeout=15)
            if r.ok:
                tok = r.json()
                st.session_state.update({
                    "app_key": app_key, "app_secret": app_sec,
                    "callback_url": callback, "connected": True,
                    "tokens": {
                        "access_token":  tok["access_token"],
                        "refresh_token": tok["refresh_token"],
                        "expiry": _utcnow() + datetime.timedelta(seconds=tok.get("expires_in", 1800)),
                    },
                })
                st.success("✅ Conectado.")
                st.code(f'REFRESH_TOKEN = "{tok["refresh_token"]}"', language="toml")
                if st.button("ENTRAR →", type="primary", use_container_width=True):
                    st.rerun()
            else:
                st.error(f"Error {r.status_code}: `{r.text}`")
                if st.button("← VOLVER", use_container_width=True):
                    st.rerun()
        return

    # Auto-connect
    if not st.session_state.get("connected"):
        try_auto_connect()

    # Dashboard or connect screen
    if st.session_state.get("connected"):
        show_dashboard()
    else:
        show_connect_screen()


if __name__ == "__main__":
    main()
