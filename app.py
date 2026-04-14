"""
Options Chain Analyzer — Charles Schwab API
Bloomberg-style dark UI · Greeks · GEX · IV Skew · Term Structure
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests, base64, datetime, time, warnings
from urllib.parse import urlencode, urlparse, parse_qs

warnings.filterwarnings("ignore")

st.set_page_config(
    page_title="Options Terminal",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ═══════════════════════════════════════════════════════════════════════════════
#  BLOOMBERG DARK THEME CSS
# ═══════════════════════════════════════════════════════════════════════════════
CSS = """
<style>
/* ── Root overrides ─────────────────────────────────────────────────────── */
html, body, [data-testid="stApp"], .main, .block-container {
    background-color: #080810 !important;
    color: #c8c8d8 !important;
}
.block-container { padding: 2rem 1.6rem 2rem !important; max-width: 100% !important; }

/* ── Inputs & selects ───────────────────────────────────────────────────── */
input, textarea, select,
[data-testid="stTextInput"] input,
[data-testid="stSelectbox"] div[data-baseweb="select"] {
    background: #12121e !important;
    color: #e0e0f0 !important;
    border-color: #2a2a3e !important;
    border-radius: 4px !important;
}
[data-testid="stTextInput"] label,
[data-testid="stSelectbox"] label { color: #6868a0 !important; font-size: 0.72rem !important; }

/* ── Buttons ────────────────────────────────────────────────────────────── */
[data-testid="stButton"] button {
    background: transparent !important;
    border: 1px solid #2a2a3e !important;
    color: #c0c0d8 !important;
    border-radius: 4px !important;
    font-size: 0.78rem !important;
    font-family: 'JetBrains Mono', monospace !important;
    transition: all 0.15s;
}
[data-testid="stButton"] button:hover {
    border-color: #f97316 !important;
    color: #f97316 !important;
    background: rgba(249,115,22,0.08) !important;
}
button[kind="primary"] {
    background: #f97316 !important;
    border-color: #f97316 !important;
    color: #000 !important;
    font-weight: 700 !important;
}
button[kind="primary"]:hover {
    background: #fb923c !important; color: #000 !important;
}
[data-testid="stLinkButton"] a {
    background: rgba(249,115,22,0.12) !important;
    border: 1px solid #f97316 !important;
    color: #f97316 !important;
    border-radius: 4px !important;
    padding: 8px 18px !important;
    font-size: 0.82rem !important;
    text-decoration: none !important;
    display: block !important;
    text-align: center !important;
}

/* ── Metrics ────────────────────────────────────────────────────────────── */
[data-testid="stMetric"] {
    background: #0e0e1a !important;
    border: 1px solid #1e1e30 !important;
    border-radius: 4px !important;
    padding: 10px 14px !important;
}
[data-testid="stMetricLabel"] {
    font-size: 0.62rem !important; color: #5050780 !important;
    text-transform: uppercase; letter-spacing: 0.1em; font-weight: 600 !important;
    color: #606080 !important;
}
[data-testid="stMetricValue"] {
    font-size: 1.25rem !important; font-weight: 700 !important;
    color: #e8e8f8 !important;
    font-family: 'JetBrains Mono', 'Courier New', monospace !important;
}
[data-testid="stMetricDelta"] {
    font-size: 0.72rem !important;
    font-family: 'JetBrains Mono', monospace !important;
}

/* ── Tabs ───────────────────────────────────────────────────────────────── */
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
.stTabs [aria-selected="true"] {
    background: #1e1e30 !important; color: #f97316 !important;
}

/* ── Captions & markdown ────────────────────────────────────────────────── */
.stCaption p, [data-testid="stCaptionContainer"] p {
    color: #505070 !important; font-size: 0.72rem !important;
}
p, .stMarkdown p { color: #a0a0c0 !important; }
h1, h2, h3 { color: #e0e0f0 !important; }

/* ── Sidebar ────────────────────────────────────────────────────────────── */
[data-testid="stSidebar"] { background: #0a0a14 !important; border-right: 1px solid #1a1a2a !important; }
[data-testid="stSidebarContent"] * { color: #a0a0c0 !important; }
[data-testid="stSlider"] div { color: #a0a0c0 !important; }

/* ── Expander ───────────────────────────────────────────────────────────── */
[data-testid="stExpander"] {
    background: #0e0e1a !important; border: 1px solid #1e1e30 !important;
    border-radius: 4px !important;
}
[data-testid="stExpander"] summary { color: #8080a0 !important; }

/* ── Section headers ────────────────────────────────────────────────────── */
.bb-header {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.68rem; font-weight: 700;
    text-transform: uppercase; letter-spacing: 0.12em;
    color: #f97316; border-left: 3px solid #f97316;
    padding-left: 10px; margin: 1.4rem 0 0.8rem;
}
.bb-divider { border: none; border-top: 1px solid #1a1a2a; margin: 1.2rem 0; }

/* ── Connect screen ─────────────────────────────────────────────────────── */
.conn-logo  { font-size: 2.5rem; display: block; text-align: center; margin-bottom: 0.5rem; }
.conn-title { font-size: 1.5rem; font-weight: 800; color: #f97316; text-align: center;
              font-family: 'JetBrains Mono', monospace; margin: 0 0 0.2rem; letter-spacing: 0.05em; }
.conn-sub   { font-size: 0.82rem; color: #606080; text-align: center; margin: 0 0 2rem; }
.step-card {
    background: #0e0e1a; border: 1px solid #1e1e30; border-radius: 6px;
    padding: 1.1rem 1.3rem; margin-bottom: 0.9rem;
}
.step-num {
    display: inline-flex; align-items: center; justify-content: center;
    background: #f97316; color: #000; border-radius: 50%;
    width: 22px; height: 22px; font-size: 0.7rem; font-weight: 800;
    margin-right: 8px; flex-shrink: 0;
}
.step-label { font-size: 0.82rem; color: #9090b0; }

/* ── Options chain table ────────────────────────────────────────────────── */
.chain-wrap { overflow-x: auto; border: 1px solid #1a1a2a; border-radius: 4px; }
.chain {
    width: 100%; border-collapse: collapse;
    font-size: 0.75rem;
    font-family: 'JetBrains Mono', 'Courier New', monospace;
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
/* ITM rows */
.itm-c td { background: rgba(34,197,94,0.04) !important; }
.itm-p td { background: rgba(244,63,94,0.04) !important; }
/* ATM row */
.atm-row td { background: rgba(249,115,22,0.07) !important; border-top: 1px solid rgba(249,115,22,0.3) !important; border-bottom: 1px solid rgba(249,115,22,0.3) !important; }
/* Cell colors */
.strike     { font-weight: 700; color: #d0d0e8; }
.atm-strike { color: #f97316 !important; font-weight: 800; }
.pos   { color: #22c55e !important; }
.neg   { color: #f43f5e !important; }
.neu   { color: #6060a0; }
.hi    { color: #e0e0f8 !important; font-weight: 600; }
/* Section headers in table */
.call-hdr { background: rgba(34,197,94,0.08) !important; color: #22c55e !important; font-weight: 700 !important; }
.put-hdr  { background: rgba(244,63,94,0.08) !important; color: #f43f5e !important; font-weight: 700 !important; }
.mid-hdr  { background: #0d0d1a !important; color: #f97316 !important; font-weight: 800 !important; }

/* ── Info badge ─────────────────────────────────────────────────────────── */
.badge {
    display: inline-block; padding: 2px 8px; border-radius: 3px;
    font-size: 0.68rem; font-weight: 700; font-family: 'JetBrains Mono', monospace;
}
.badge-green { background: rgba(34,197,94,0.15); color: #22c55e; border: 1px solid rgba(34,197,94,0.3); }
.badge-red   { background: rgba(244,63,94,0.15);  color: #f43f5e; border: 1px solid rgba(244,63,94,0.3); }
.badge-orange{ background: rgba(249,115,22,0.15); color: #f97316; border: 1px solid rgba(249,115,22,0.3); }
.badge-gray  { background: rgba(100,100,150,0.15);color: #8080a0; border: 1px solid rgba(100,100,150,0.3); }

/* ── Stat row ───────────────────────────────────────────────────────────── */
.stat-row { display:flex; gap:24px; align-items:baseline; margin-bottom:0.5rem; }
.stat-label { font-size:0.65rem; color:#505070; text-transform:uppercase; letter-spacing:0.08em; font-family:'JetBrains Mono',monospace; }
.stat-val   { font-size:1.1rem; font-weight:700; color:#e0e0f8; font-family:'JetBrains Mono',monospace; margin-top:2px; }

/* ── Footer ─────────────────────────────────────────────────────────────── */
.footer { text-align:center; font-size:0.65rem; color:#2a2a3a; margin-top:2rem;
          font-family:'JetBrains Mono',monospace; }
</style>
"""

# ═══════════════════════════════════════════════════════════════════════════════
#  PLOTLY BLOOMBERG THEME
# ═══════════════════════════════════════════════════════════════════════════════
_BG_DARK  = "#0b0b14"
_BG_PLOT  = "#0e0e1a"
_GRID_CLR = "rgba(255,255,255,0.04)"
_ORANGE   = "#f97316"
_GREEN    = "#22c55e"
_RED      = "#f43f5e"
_BLUE     = "#3b82f6"
_PURPLE   = "#a855f7"
_FONT_MONO = "JetBrains Mono, Courier New, monospace"

_BASE = dict(
    plot_bgcolor=_BG_PLOT, paper_bgcolor=_BG_DARK,
    font=dict(size=11, family=_FONT_MONO, color="#7070a0"),
    margin=dict(l=55, r=24, t=42, b=36),
    legend=dict(
        orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
        font=dict(size=10, color="#9090b0"), bgcolor="rgba(0,0,0,0)",
    ),
    hoverlabel=dict(bgcolor="#1a1a2a", font_size=11, font_family=_FONT_MONO,
                    bordercolor="#3a3a4a", font_color="#e0e0f0"),
)
_AX = dict(
    showgrid=True, gridcolor=_GRID_CLR,
    linecolor="#1a1a2a", linewidth=1, showline=True,
    tickfont=dict(size=10, family=_FONT_MONO, color="#606080"),
    title_font=dict(size=10, color="#606080"),
)
_AX_ZERO = dict(**_AX, zeroline=True, zerolinecolor="rgba(255,255,255,0.08)", zerolinewidth=1)
_AX_NOZERO = dict(**_AX, zeroline=False)


def _vline(fig, x, row=None, col=None, color=None, label=True):
    clr = color or "rgba(249,115,22,0.5)"
    kw = dict(x=x, line_dash="dot", line_color=clr, line_width=1.2)
    if label:
        kw.update(annotation_text=f"  ${x:.0f}",
                  annotation_font_size=9, annotation_font_color=clr)
    if row:
        kw.update(row=row, col=col)
    fig.add_vline(**kw)


# ═══════════════════════════════════════════════════════════════════════════════
#  OAUTH — manual (no schwabdev, works on Streamlit Cloud)
# ═══════════════════════════════════════════════════════════════════════════════
_AUTH_URL  = "https://api.schwabapi.com/v1/oauth/authorize"
_TOKEN_URL = "https://api.schwabapi.com/v1/oauth/token"
_BASE_URL  = "https://api.schwabapi.com"


def build_auth_url(app_key, callback_url):
    return f"{_AUTH_URL}?{urlencode({'client_id': app_key, 'redirect_uri': callback_url})}"


def exchange_code(app_key, app_secret, code, callback_url):
    creds = base64.b64encode(f"{app_key}:{app_secret}".encode()).decode()
    r = requests.post(_TOKEN_URL,
        headers={"Authorization": f"Basic {creds}",
                 "Content-Type": "application/x-www-form-urlencoded"},
        data={"grant_type": "authorization_code", "code": code,
              "redirect_uri": callback_url}, timeout=15)
    r.raise_for_status()
    return r.json()


def _refresh_access_token():
    tok = st.session_state.get("tokens", {})
    if not tok:
        return
    expiry = tok.get("expiry", datetime.datetime.min)
    if datetime.datetime.utcnow() >= expiry - datetime.timedelta(seconds=60):
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
                "expiry": datetime.datetime.utcnow() + datetime.timedelta(
                    seconds=new.get("expires_in", 1800)),
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


# ═══════════════════════════════════════════════════════════════════════════════
#  AUTO-CONNECT via Streamlit Secrets
# ═══════════════════════════════════════════════════════════════════════════════
def _secret(key, default=None):
    """Read from st.secrets, fall back to default."""
    try:
        return st.secrets[key]
    except Exception:
        return default


def try_auto_connect():
    """
    Try to connect silently using credentials stored in st.secrets.
    Returns True if connected successfully, False otherwise.
    Secrets required:
        APP_KEY       = "..."
        APP_SECRET    = "..."
        CALLBACK_URL  = "https://yourapp.streamlit.app"
        REFRESH_TOKEN = "..."   ← obtained once via OAuth
    """
    if st.session_state.get("connected"):
        return True

    app_key       = _secret("APP_KEY")
    app_secret    = _secret("APP_SECRET")
    refresh_token = _secret("REFRESH_TOKEN")

    if not all([app_key, app_secret, refresh_token]):
        return False  # secrets not configured → show connect screen

    try:
        creds = base64.b64encode(f"{app_key}:{app_secret}".encode()).decode()
        r = requests.post(
            _TOKEN_URL,
            headers={"Authorization": f"Basic {creds}",
                     "Content-Type": "application/x-www-form-urlencoded"},
            data={"grant_type": "refresh_token", "refresh_token": refresh_token},
            timeout=15,
        )
        r.raise_for_status()
        tok = r.json()

        st.session_state["app_key"]    = app_key
        st.session_state["app_secret"] = app_secret
        st.session_state["callback_url"] = _secret("CALLBACK_URL", "https://127.0.0.1")
        st.session_state["tokens"] = {
            "access_token":  tok["access_token"],
            "refresh_token": tok.get("refresh_token", refresh_token),
            "expiry": datetime.datetime.utcnow() + datetime.timedelta(
                seconds=tok.get("expires_in", 1800)),
        }
        st.session_state["connected"] = True
        return True
    except Exception:
        return False  # refresh_token expired → show connect screen


# ═══════════════════════════════════════════════════════════════════════════════
#  CONNECT / RE-AUTH SCREEN  (only shown when secrets missing or token expired)
# ═══════════════════════════════════════════════════════════════════════════════
def show_connect_screen():
    st.markdown(CSS, unsafe_allow_html=True)
    st.markdown("<br><br>", unsafe_allow_html=True)
    _, col, _ = st.columns([1, 1.2, 1])

    # Detect if this is first-time setup or an expired token
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

        # ── Step 0: credentials (only if not in secrets yet) ──────────────
        if not has_secrets:
            st.markdown('<div class="step-card">', unsafe_allow_html=True)
            st.markdown('<span class="step-num">0</span><span class="step-label"> Credenciales (solo primera vez):</span>', unsafe_allow_html=True)
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

        # ── Step 1: OAuth link ─────────────────────────────────────────────
        if not has_secrets:
            show_oauth = st.button("SIGUIENTE → GENERAR ENLACE", type="primary",
                                   use_container_width=True)
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
        st.markdown('<span class="step-num">1</span><span class="step-label"> Haz clic para autorizar en Schwab:</span>', unsafe_allow_html=True)
        st.link_button("🔐  AUTORIZAR EN SCHWAB", auth_url, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

        # ── Step 2: paste redirect URL ─────────────────────────────────────
        st.markdown('<div class="step-card">', unsafe_allow_html=True)
        st.markdown('<span class="step-num">2</span><span class="step-label"> Pega la URL completa de la redirección:</span>', unsafe_allow_html=True)
        redirect_url = st.text_input("redirect", label_visibility="collapsed",
            placeholder="https://tuapp.streamlit.app?code=Xxxx&session=...")
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
        code = parse_qs(urlparse(redirect_url).query).get("code", [None])[0]
        if not code:
            st.error("No se encontró ?code= en la URL. Copia la URL completa de la barra de direcciones.")
            return
        with st.spinner("Intercambiando código…"):
            tok = exchange_code(st.session_state["app_key"], st.session_state["app_secret"],
                                code, st.session_state["callback_url"])

        refresh_token = tok["refresh_token"]
        st.session_state["tokens"] = {
            "access_token":  tok["access_token"],
            "refresh_token": refresh_token,
            "expiry": datetime.datetime.utcnow() + datetime.timedelta(
                seconds=tok.get("expires_in", 1800)),
        }
        st.session_state["connected"]     = True
        st.session_state["oauth_pending"] = False

        # ── Show refresh token so user can save it to Secrets ──────────────
        st.success("✅ Autenticado correctamente.")
        st.markdown("""
        <div style="background:#0e0e1a;border:1px solid #f97316;border-radius:6px;padding:1rem 1.2rem;margin-top:1rem;">
        <p style="color:#f97316;font-family:JetBrains Mono,monospace;font-size:0.75rem;font-weight:700;margin:0 0 0.5rem;">
        ⭐ GUARDA ESTE REFRESH TOKEN EN STREAMLIT SECRETS — no tendrás que volver a autenticarte por 7 días:
        </p>
        """, unsafe_allow_html=True)
        st.code(f'REFRESH_TOKEN = "{refresh_token}"', language="toml")
        st.markdown("""
        <p style="color:#606080;font-family:JetBrains Mono,monospace;font-size:0.7rem;margin:0.5rem 0 0;">
        En Streamlit Cloud: <b>Manage App → Settings → Secrets</b> → agrega la línea de arriba.
        </p></div>
        """, unsafe_allow_html=True)
        st.button("ENTRAR AL DASHBOARD →", type="primary", use_container_width=True,
                  on_click=lambda: st.rerun())
    except Exception as e:
        st.error(f"Error al obtener tokens: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
#  DATA LAYER
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


def fetch_quote(symbol):
    try:
        r = api_get(f"/marketdata/v1/{symbol}/quotes")
        if r.status_code == 200:
            d = r.json()
            return d.get(symbol, {}).get("quote", {})
    except Exception:
        pass
    return {}


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
    "strikePrice":"Strike","_exp":"Expiry","_dte":"DTE",
    "bid":"Bid","ask":"Ask","mark":"Mark","last":"Last",
    "totalVolume":"Volume","openInterest":"OI",
    "impliedVolatility":"IV%","delta":"Delta","gamma":"Gamma",
    "theta":"Theta","vega":"Vega","rho":"Rho",
    "inTheMoney":"ITM","theoreticalOptionValue":"Theo",
    "daysToExpiration":"DTE",
}

def clean(df):
    if df.empty:
        return df
    cols = {k: v for k, v in _REMAP.items() if k in df.columns}
    df = df[list(cols)].rename(columns=cols).copy()
    for c, d in [("Bid",2),("Ask",2),("Mark",2),("Last",2),("Theo",2),
                 ("Delta",3),("Theta",3),("Gamma",4),("Vega",4),("Rho",4),("Strike",2)]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").round(d)
    if "IV%" in df.columns:
        df["IV%"] = (pd.to_numeric(df["IV%"], errors="coerce") * 100).round(2)
    if "OI" in df.columns:
        df["OI"] = pd.to_numeric(df["OI"], errors="coerce").fillna(0).astype(int)
    if "Volume" in df.columns:
        df["Volume"] = pd.to_numeric(df["Volume"], errors="coerce").fillna(0).astype(int)
    return df


def by_exp(df, exp):
    return df[df["Expiry"] == exp].copy() if not df.empty and "Expiry" in df.columns else df


# ═══════════════════════════════════════════════════════════════════════════════
#  ANALYTICS
# ═══════════════════════════════════════════════════════════════════════════════
def calc_max_pain(c, p):
    if c.empty or p.empty or "OI" not in c.columns:
        return None
    strikes = sorted(set(c["Strike"].tolist() + p["Strike"].tolist()))
    co = c.set_index("Strike")["OI"].to_dict()
    po = p.set_index("Strike")["OI"].to_dict()
    pain = {s: sum(max(0.,s-x)*co.get(x,0)+max(0.,x-s)*po.get(x,0) for x in strikes) for s in strikes}
    return min(pain, key=pain.get) if pain else None


def calc_pcr(c, p):
    if c.empty or p.empty or "OI" not in c.columns:
        return None
    tot = c["OI"].sum()
    return round(p["OI"].sum() / tot, 2) if tot > 0 else None


def calc_atm_iv(c, spot):
    if c.empty or "IV%" not in c.columns or spot == 0:
        return None
    return float(c.loc[(c["Strike"] - spot).abs().idxmin(), "IV%"])


def calc_expected_move(spot, iv_pct, dte):
    """1σ expected move: ±S × IV × √(DTE/365)"""
    if not all([spot, iv_pct, dte]):
        return None, None
    move = spot * (iv_pct / 100) * np.sqrt(dte / 365)
    return round(spot - move, 2), round(spot + move, 2)


def calc_gex(c, p, spot):
    """
    GEX = (Call_OI × Call_Gamma − Put_OI × Put_Gamma) × 100 × Spot²
    Positive GEX → MM long gamma → suppresses volatility
    Negative GEX → MM short gamma → amplifies volatility
    """
    if c.empty or "Gamma" not in c.columns:
        return pd.DataFrame()
    c2, p2 = c.copy(), p.copy()
    c2["GEX"] =  c2["OI"] * c2["Gamma"] * 100 * spot**2
    p2["GEX"] = -p2["OI"] * p2["Gamma"].abs() * 100 * spot**2
    merged = (
        c2[["Strike","GEX"]].rename(columns={"GEX":"C_GEX"})
        .merge(p2[["Strike","GEX"]].rename(columns={"GEX":"P_GEX"}), on="Strike", how="outer")
        .fillna(0)
    )
    merged["Net_GEX"] = merged["C_GEX"] + merged["P_GEX"]
    return merged.sort_values("Strike")


def calc_iv_skew(c, p, spot):
    """IV Skew: Put IV − Call IV at matched strikes, normalized by ATM IV."""
    if c.empty or p.empty or "IV%" not in c.columns:
        return pd.DataFrame()
    c2 = c[["Strike","IV%"]].rename(columns={"IV%":"C_IV"})
    p2 = p[["Strike","IV%"]].rename(columns={"IV%":"P_IV"})
    skew = c2.merge(p2, on="Strike", how="inner")
    skew["Skew"] = skew["P_IV"] - skew["C_IV"]
    atm_idx = (skew["Strike"] - spot).abs().idxmin()
    atm_iv  = (skew.loc[atm_idx,"C_IV"] + skew.loc[atm_idx,"P_IV"]) / 2
    skew["Moneyness"] = ((skew["Strike"] - spot) / spot * 100).round(2)
    if atm_iv > 0:
        skew["Skew_norm"] = (skew["Skew"] / atm_iv * 100).round(2)
    else:
        skew["Skew_norm"] = skew["Skew"]
    return skew.sort_values("Strike")


def calc_term_structure(c_all, spot):
    """ATM IV per expiration → term structure."""
    if c_all.empty or "IV%" not in c_all.columns:
        return pd.DataFrame()
    rows = []
    for exp, grp in c_all.groupby("Expiry"):
        dte = int(grp["DTE"].iloc[0]) if "DTE" in grp.columns else 0
        idx = (grp["Strike"] - spot).abs().idxmin()
        atm_iv = grp.loc[idx, "IV%"]
        rows.append({"Expiry": exp, "DTE": dte, "ATM_IV": atm_iv})
    return pd.DataFrame(rows).sort_values("DTE")


def calc_charm(c, p, dte):
    """Approximate charm (delta decay): Theta/Spot × DTE proxy."""
    if c.empty or "Delta" not in c.columns or "Theta" not in c.columns:
        return c, p
    for df in [c, p]:
        if "Theta" in df.columns and "Delta" in df.columns and dte > 0:
            df["Charm"] = (-df["Theta"] / (365 * abs(df["Delta"]) + 1e-9) ).round(4)
    return c, p


# ═══════════════════════════════════════════════════════════════════════════════
#  HTML CHAIN TABLE
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

    else:  # both
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
#  CHARTS
# ═══════════════════════════════════════════════════════════════════════════════
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


def chart_gex(gex_df, spot):
    if gex_df.empty:
        return None
    total_gex = gex_df["Net_GEX"].sum() / 1e9
    flip_candidates = gex_df[gex_df["Net_GEX"].diff().apply(np.sign).diff() != 0]

    fig = go.Figure()
    colors = [_GREEN if v >= 0 else _RED for v in gex_df["Net_GEX"]]
    fig.add_trace(go.Bar(
        x=gex_df["Strike"], y=gex_df["Net_GEX"] / 1e6,
        marker_color=colors,
        marker_line=dict(width=0),
        name="Net GEX",
        hovertemplate="Strike: %{x}<br>GEX: %{y:.1f}M<extra></extra>",
    ))
    _vline(fig, spot)
    # GEX flip point
    sign_change = gex_df[gex_df["Net_GEX"] * gex_df["Net_GEX"].shift(1) < 0]
    for _, row in sign_change.iterrows():
        fig.add_vline(x=row["Strike"], line_dash="dashdot",
                      line_color="rgba(249,115,22,0.3)", line_width=1)
    fig.update_layout(
        height=320,
        xaxis_title="Strike",
        yaxis_title="Net GEX ($ Millones)",
        title=dict(text=f"  GAMMA EXPOSURE  |  Net GEX: {'${:.2f}B'.format(total_gex)}  |  {'LONG GAMMA ▲' if total_gex >= 0 else 'SHORT GAMMA ▼'}",
                   font=dict(size=11, color=_GREEN if total_gex >= 0 else _RED, family=_FONT_MONO), x=0),
        **_BASE,
    )
    fig.update_xaxes(**_AX_NOZERO, title_text="Strike")
    fig.update_yaxes(**_AX_ZERO)
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
        hovertemplate="Strike: %{x}<br>Call IV: %{y:.1f}%<extra></extra>",
    ), row=1, col=1)
    fig.add_trace(go.Scatter(
        x=skew_df["Strike"], y=skew_df["P_IV"], name="Put IV",
        line=dict(color=_RED, width=2), mode="lines",
        hovertemplate="Strike: %{x}<br>Put IV: %{y:.1f}%<extra></extra>",
    ), row=1, col=1)
    _vline(fig, spot, row=1, col=1)

    skew_colors = [_RED if v > 0 else _GREEN for v in skew_df["Skew"]]
    fig.add_trace(go.Bar(
        x=skew_df["Strike"], y=skew_df["Skew"],
        marker_color=skew_colors, marker_line_width=0,
        name="Skew", showlegend=False,
        hovertemplate="Strike: %{x}<br>Skew: %{y:.1f}%<extra></extra>",
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
    if ts_df.empty or len(ts_df) < 2:
        return None
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=ts_df["DTE"], y=ts_df["ATM_IV"],
        mode="lines+markers",
        line=dict(color=_ORANGE, width=2.5),
        marker=dict(size=7, color=_ORANGE, line=dict(width=1, color="#0b0b14")),
        hovertemplate="DTE: %{x}<br>ATM IV: %{y:.1f}%<extra></extra>",
        fill="tozeroy", fillcolor="rgba(249,115,22,0.06)",
    ))
    # Annotate each point
    for _, row in ts_df.iterrows():
        fig.add_annotation(x=row["DTE"], y=row["ATM_IV"],
                           text=f"  {row['Expiry'][:10]}",
                           showarrow=False, font=dict(size=9, color="#505070", family=_FONT_MONO),
                           xanchor="left")
    fig.update_layout(
        height=280,
        xaxis_title="DTE (días a expiración)",
        yaxis_title="ATM IV (%)",
        **_BASE,
    )
    fig.update_xaxes(**_AX_NOZERO)
    fig.update_yaxes(**_AX_NOZERO)
    return fig


def chart_oi_volume(c, p, spot, em_low=None, em_high=None):
    fig = make_subplots(rows=1, cols=2,
        subplot_titles=["OPEN INTEREST  POR STRIKE", "VOLUMEN  POR STRIKE"],
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
                hovertemplate=f"Strike: %{{x}}<br>{metric}: %{{y:,}}<extra>{lbl}</extra>",
            ), row=1, col=col)
        _vline(fig, spot, row=1, col=col)
        # Expected move range
        if em_low and em_high:
            for em_val, em_lbl in [(em_low,"EM−"),(em_high,"EM+")]:
                fig.add_vline(x=em_val, line_dash="dashdot",
                              line_color="rgba(168,85,247,0.4)", line_width=1,
                              annotation_text=f"  {em_lbl} ${em_val:.0f}",
                              annotation_font_size=8, annotation_font_color="#a855f7",
                              row=1, col=col)
    fig.update_layout(height=320, barmode="overlay", **_BASE)
    fig.update_xaxes(**_AX_NOZERO, title_text="Strike")
    fig.update_yaxes(**_AX_NOZERO)
    for ann in fig.layout.annotations:
        ann.font.update(size=10, color="#606080", family=_FONT_MONO)
    return fig


def chart_delta_exp(c, p, spot):
    if c.empty or not {"OI","Delta"}.issubset(c.columns):
        return None
    c2, p2 = c.copy(), p.copy()
    c2["DE"] =  c2["OI"] * c2["Delta"] * 100
    p2["DE"] = -p2["OI"] * p2["Delta"].abs() * 100
    fig = go.Figure([
        go.Bar(x=c2["Strike"], y=c2["DE"], name="Calls",
               marker_color="rgba(34,197,94,0.65)", marker_line_width=0,
               hovertemplate="Strike: %{x}<br>ΔExp: %{y:,.0f}<extra>Calls</extra>"),
        go.Bar(x=p2["Strike"], y=p2["DE"], name="Puts",
               marker_color="rgba(244,63,94,0.65)", marker_line_width=0,
               hovertemplate="Strike: %{x}<br>ΔExp: %{y:,.0f}<extra>Puts</extra>"),
    ])
    _vline(fig, spot)
    fig.update_layout(height=300, barmode="relative",
                      xaxis_title="Strike", yaxis_title="OI × Δ × 100", **_BASE)
    fig.update_xaxes(**_AX_NOZERO)
    fig.update_yaxes(**_AX_ZERO)
    return fig


# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN DASHBOARD
# ═══════════════════════════════════════════════════════════════════════════════
def show_dashboard():
    st.markdown(CSS, unsafe_allow_html=True)
    st.markdown("<div style='height:0.6rem'></div>", unsafe_allow_html=True)

    # ── Top bar ─────────────────────────────────────────────────────────────
    b1, b2, b3, b4, b5, b6 = st.columns([1.0, 1.4, 1.8, 1.0, 1.0, 0.6])

    with b1:
        st.markdown("<span style='font-family:JetBrains Mono,monospace;font-size:1rem;font-weight:800;color:#f97316;letter-spacing:0.12em;line-height:2.4;display:block'>▤ OPTIONS</span>", unsafe_allow_html=True)

    with b2:
        symbol = st.text_input("sym", value=st.session_state.get("symbol","AAPL"),
            placeholder="SPY, AAPL, QQQ…", label_visibility="collapsed").upper().strip()

    with b3:
        today  = datetime.date.today()
        all_exps = st.session_state.get("all_exps", ["—"])
        sel_exp  = st.selectbox("exp", options=all_exps, label_visibility="collapsed",
                                key="sel_exp")

    with b4:
        strike_count = st.selectbox("strikes", options=[10,15,20,25,30,40,50],
                                    index=3, label_visibility="collapsed")

    with b5:
        auto_refresh = st.toggle("Auto 30s", value=False, key="auto_refresh_toggle")

    with b6:
        if st.button("EXIT", use_container_width=True):
            for k in ["tokens","connected","chain_data","last_sym","symbol",
                      "app_key","app_secret","callback_url","oauth_pending","all_exps"]:
                st.session_state.pop(k, None)
            st.rerun()

    st.markdown('<hr class="bb-divider">', unsafe_allow_html=True)

    # ── Load data ────────────────────────────────────────────────────────────
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

        # Update expiration list
        calls_r, puts_r, _ = parse_chain(data)
        calls_c = clean(calls_r)
        exps = sorted(set(calls_c["Expiry"].tolist() if not calls_c.empty and "Expiry" in calls_c.columns else []))
        st.session_state.all_exps = exps
        st.rerun()

    if "chain_data" not in st.session_state:
        st.markdown('<p style="color:#404060;text-align:center;margin-top:3rem;font-family:JetBrains Mono,monospace;font-size:0.85rem;">Ingresa un símbolo para comenzar</p>', unsafe_allow_html=True)
        return

    # ── Parse ────────────────────────────────────────────────────────────────
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

    # ── Analytics ────────────────────────────────────────────────────────────
    dte_v  = int(calls["DTE"].dropna().values[0]) if not calls.empty and "DTE" in calls.columns and len(calls["DTE"].dropna()) > 0 else 0
    iv_atm = calc_atm_iv(calls, spot)
    p_c    = calc_pcr(calls, puts)
    mp     = calc_max_pain(calls, puts)
    em_lo, em_hi = calc_expected_move(spot, iv_atm, dte_v)
    gex_df = calc_gex(calls, puts, spot)
    total_gex = gex_df["Net_GEX"].sum() / 1e9 if not gex_df.empty else None
    skew_df = calc_iv_skew(calls, puts, spot)
    ts_df   = calc_term_structure(calls_all, spot)
    last_refresh = st.session_state.get("last_refresh", datetime.datetime.now())

    # ── Metrics row ──────────────────────────────────────────────────────────
    chg_color  = "#22c55e" if chg >= 0 else "#f43f5e"
    gex_color  = "#22c55e" if (total_gex or 0) >= 0 else "#f43f5e"
    pcr_color  = "#22c55e" if (p_c or 1) < 0.9 else ("#f43f5e" if (p_c or 1) > 1.1 else "#f97316")

    m1,m2,m3,m4,m5,m6,m7,m8 = st.columns(8)
    m1.metric("PRECIO",    f"${spot:.2f}",    f"{chg:+.2f}  {chg_p:+.1f}%")
    m2.metric("BID / ASK", f"{bid_u:.2f} / {ask_u:.2f}")
    m3.metric("VOLUMEN",   f"{vol_u:,}")
    m4.metric("DTE",       f"{dte_v}d")
    m5.metric("ATM IV",    f"{iv_atm:.1f}%" if iv_atm else "—")
    m6.metric("P/C RATIO", f"{p_c:.2f}"    if p_c    else "—")
    m7.metric("MAX PAIN",  f"${mp:.0f}"    if mp     else "—")
    m8.metric("NET GEX",   f"{'${:.2f}B'.format(total_gex)}" if total_gex is not None else "—",
              "LONG Γ" if (total_gex or 0) >= 0 else "SHORT Γ")

    # Expected move info
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

    # ── Chain table ──────────────────────────────────────────────────────────
    st.markdown('<p class="bb-header">OPTIONS CHAIN</p>', unsafe_allow_html=True)
    tab_c, tab_p, tab_b = st.tabs(["▲  CALLS", "▼  PUTS", "⇅  COMPLETA"])
    with tab_c: st.markdown(build_table(calls, puts, spot, "calls"), unsafe_allow_html=True)
    with tab_p: st.markdown(build_table(calls, puts, spot, "puts"),  unsafe_allow_html=True)
    with tab_b: st.markdown(build_table(calls, puts, spot, "both"),  unsafe_allow_html=True)

    st.markdown('<hr class="bb-divider">', unsafe_allow_html=True)

    # ── Greeks ───────────────────────────────────────────────────────────────
    st.markdown('<p class="bb-header">GREEKS</p>', unsafe_allow_html=True)
    st.plotly_chart(chart_greeks(calls, puts, spot), use_container_width=True)

    st.markdown('<hr class="bb-divider">', unsafe_allow_html=True)

    # ── GEX ──────────────────────────────────────────────────────────────────
    st.markdown('<p class="bb-header">GAMMA EXPOSURE  (GEX)</p>', unsafe_allow_html=True)
    c_gex, c_gex_info = st.columns([3, 1])
    with c_gex:
        fig_gex = chart_gex(gex_df, spot)
        if fig_gex:
            st.plotly_chart(fig_gex, use_container_width=True)
    with c_gex_info:
        gex_sign = "LONG" if (total_gex or 0) >= 0 else "SHORT"
        gex_badge = "badge-green" if gex_sign == "LONG" else "badge-red"
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown(f'<span class="badge {gex_badge}">{gex_sign} GAMMA</span>', unsafe_allow_html=True)
        st.markdown(f"""
        <div style="margin-top:1rem;font-size:0.75rem;color:#505070;font-family:JetBrains Mono,monospace;line-height:1.8;">
        <b style="color:#808090">¿Qué es el GEX?</b><br><br>
        GEX = (OI_Call × Γ_Call − OI_Put × Γ_Put) × 100 × S²<br><br>
        <span style="color:#22c55e">▲ GEX positivo</span><br>
        Market makers están <i>long gamma</i>. Venden rallies y compran caídas → volatilidad comprimida.<br><br>
        <span style="color:#f43f5e">▼ GEX negativo</span><br>
        Market makers están <i>short gamma</i>. Amplifican los movimientos → mayor volatilidad.<br><br>
        Las líneas punteadas naranjas indican puntos de <i>GEX flip</i> (gamma neutral).
        </div>
        """, unsafe_allow_html=True)

    st.markdown('<hr class="bb-divider">', unsafe_allow_html=True)

    # ── IV Skew ───────────────────────────────────────────────────────────────
    st.markdown('<p class="bb-header">IV SKEW  &  VOLATILITY SMILE</p>', unsafe_allow_html=True)
    fig_skew = chart_iv_skew(skew_df, spot)
    if fig_skew:
        st.plotly_chart(fig_skew, use_container_width=True)

    st.markdown('<hr class="bb-divider">', unsafe_allow_html=True)

    # ── Term Structure ────────────────────────────────────────────────────────
    st.markdown('<p class="bb-header">TERM STRUCTURE  (IV por vencimiento)</p>', unsafe_allow_html=True)
    c_ts, c_ts_tbl = st.columns([3, 1])
    with c_ts:
        fig_ts = chart_term_structure(ts_df)
        if fig_ts:
            st.plotly_chart(fig_ts, use_container_width=True)
        else:
            st.caption("Necesitas más de 1 vencimiento disponible.")
    with c_ts_tbl:
        if not ts_df.empty:
            st.markdown("<br>", unsafe_allow_html=True)
            tbl_html = '<table style="font-family:JetBrains Mono,monospace;font-size:0.72rem;width:100%;">'
            tbl_html += '<tr><th style="color:#505070;text-align:left">Exp</th><th style="color:#505070;text-align:right">DTE</th><th style="color:#505070;text-align:right">ATM IV</th></tr>'
            for _, row in ts_df.iterrows():
                iv_c = _GREEN if row["ATM_IV"] < 30 else (_RED if row["ATM_IV"] > 60 else _ORANGE)
                tbl_html += f'<tr><td style="color:#7070a0">{row["Expiry"][:10]}</td><td style="text-align:right;color:#9090b0">{int(row["DTE"])}</td><td style="text-align:right;color:{iv_c}">{row["ATM_IV"]:.1f}%</td></tr>'
            tbl_html += "</table>"
            st.markdown(tbl_html, unsafe_allow_html=True)

    st.markdown('<hr class="bb-divider">', unsafe_allow_html=True)

    # ── OI / Volume ───────────────────────────────────────────────────────────
    st.markdown('<p class="bb-header">OPEN INTEREST  &  VOLUME</p>', unsafe_allow_html=True)
    st.plotly_chart(chart_oi_volume(calls, puts, spot, em_lo, em_hi), use_container_width=True)

    st.markdown('<hr class="bb-divider">', unsafe_allow_html=True)

    # ── Delta Exposure ────────────────────────────────────────────────────────
    st.markdown('<p class="bb-header">DELTA EXPOSURE</p>', unsafe_allow_html=True)
    fig_de = chart_delta_exp(calls, puts, spot)
    if fig_de:
        st.plotly_chart(fig_de, use_container_width=True)

    # ── Footer ────────────────────────────────────────────────────────────────
    st.markdown(
        f'<p class="footer">OPTIONS TERMINAL  ·  {symbol}  ·  {last_refresh.strftime("%Y-%m-%d %H:%M:%S")} UTC'
        f'  ·  Charles Schwab API  ·  Datos en tiempo real (requiere cuenta con fondos)'
        f'  ·  No constituye asesoramiento financiero</p>',
        unsafe_allow_html=True,
    )

    # ── Auto-refresh ──────────────────────────────────────────────────────────
    if auto_refresh:
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
#  ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════
def main():
    # 1. Try to connect silently using Streamlit Secrets (no UI needed)
    if not st.session_state.get("connected"):
        try_auto_connect()

    # 2. Go straight to dashboard, or show connect screen if needed
    if st.session_state.get("connected"):
        show_dashboard()
    else:
        show_connect_screen()


if __name__ == "__main__":
    main()
