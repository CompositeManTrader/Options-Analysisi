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
    if not r.ok:
        raise ValueError(f"HTTP {r.status_code} — {r.text}")
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

        callback = st.session_state.get("callback_url", "")
        is_streamlit_cloud = "streamlit.app" in callback or "streamlit.io" in callback

        if is_streamlit_cloud:
            st.info(
                "✅ **Flujo automático activo.**  \n"
                "Al autorizar en Schwab serás redirigido de vuelta a esta app "
                "y el código se captura solo. No necesitas copiar ni pegar nada.",
                icon="🚀",
            )
        else:
            # Local flow: still needs manual paste but with clear timing warning
            st.warning(
                "⚡ **Actúa rápido** — el código expira en ~30 segundos.  \n"
                "Autoriza → copia la URL de redirección → pégala aquí de inmediato.",
                icon="⏱",
            )
            st.markdown('<div class="step-card">', unsafe_allow_html=True)
            st.markdown('<span class="step-num">2</span><span class="step-label"> Pega la URL completa de la redirección (tienes ~30s):</span>', unsafe_allow_html=True)
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
            st.error("No se encontró `?code=` en la URL. Copia la URL completa de la barra de direcciones.")
            return

        with st.spinner("Intercambiando código…"):
            creds = base64.b64encode(
                f"{st.session_state['app_key']}:{st.session_state['app_secret']}".encode()
            ).decode()
            r = requests.post(
                _TOKEN_URL,
                headers={"Authorization": f"Basic {creds}",
                         "Content-Type": "application/x-www-form-urlencoded"},
                data={"grant_type": "authorization_code",
                      "code": code,
                      "redirect_uri": callback},
                timeout=15,
            )

        if not r.ok:
            body = r.text
            st.error(f"❌ Schwab respondió HTTP {r.status_code}: `{body}`")

            if "invalid_grant" in body or "Authorization code" in body:
                st.warning(
                    "**Código expirado o ya usado.** "
                    "Los códigos de autorización de Schwab duran solo ~30 segundos. "
                    "Haz clic en **AUTORIZAR EN SCHWAB** de nuevo y pega la URL "
                    "en la app **de inmediato**, sin demora."
                )
            elif "redirect_uri" in body.lower():
                st.warning(
                    f"**Mismatch de Callback URL.**  \n"
                    f"La URL que se envió: `{callback}`  \n"
                    "Debe ser **exactamente igual** a la registrada en tu app de Schwab "
                    "(sin barra final, mismo protocolo https, mismo dominio).  \n"
                    "Verifica en [developer.schwab.com](https://developer.schwab.com) → tu app → Callback URL."
                )
            elif "invalid_client" in body or r.status_code == 401:
                st.warning(
                    "**App Key o App Secret incorrectos.** "
                    "Verifica que coincidan exactamente con los de "
                    "[developer.schwab.com](https://developer.schwab.com)."
                )
            return

        tok = r.json()
        refresh_token = tok["refresh_token"]
        st.session_state["tokens"] = {
            "access_token":  tok["access_token"],
            "refresh_token": refresh_token,
            "expiry": datetime.datetime.utcnow() + datetime.timedelta(
                seconds=tok.get("expires_in", 1800)),
        }
        st.session_state["connected"]     = True
        st.session_state["oauth_pending"] = False

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
        Streamlit Cloud → <b>Manage App → Settings → Secrets</b> → agrega la línea de arriba → Save.
        </p></div>
        """, unsafe_allow_html=True)
        if st.button("ENTRAR AL DASHBOARD →", type="primary", use_container_width=True):
            st.rerun()

    except Exception as e:
        st.error(f"❌ Error inesperado: {e}")


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


def fetch_price_history(symbol: str, period: int = 1, period_type: str = "year") -> pd.DataFrame:
    """
    Fetch daily OHLCV price history from Schwab.
    Returns DataFrame with columns: date, open, high, low, close, volume.
    Returns empty DataFrame on failure.
    """
    try:
        r = api_get("/marketdata/v1/pricehistory", params={
            "symbol":        symbol,
            "periodType":    period_type,
            "period":        period,
            "frequencyType": "daily",
            "frequency":     1,
        })
        if r.status_code != 200:
            return pd.DataFrame()
        data = r.json()
        candles = data.get("candles", [])
        if not candles:
            return pd.DataFrame()
        df = pd.DataFrame(candles)
        df["date"] = pd.to_datetime(df["datetime"], unit="ms")
        df = df[["date","open","high","low","close","volume"]].copy()
        df = df.sort_values("date").reset_index(drop=True)
        return df
    except Exception:
        return pd.DataFrame()


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


_RF_RATE = 0.045  # Risk-free rate (~Fed funds); update periodically

def _sf(x, d=0.0):
    try: return float(x)
    except: return d

def _bs_d1d2(S, K, T, sigma, r=_RF_RATE):
    if T <= 0 or sigma <= 0 or S <= 0 or K <= 0:
        return None, None
    try:
        d1 = (np.log(S/K) + (r + 0.5*sigma**2)*T) / (sigma*np.sqrt(T))
        return d1, d1 - sigma*np.sqrt(T)
    except:
        return None, None

def _phi(x):
    return np.exp(-x**2/2) / np.sqrt(2*np.pi)

def bs_vanna(S, K, T, sigma, r=_RF_RATE):
    """Vanna = dDelta/dVol = -exp(-d1²/2)/(√2π) × d2/sigma"""
    d1, d2 = _bs_d1d2(S, K, T, sigma, r)
    if d1 is None: return 0.0
    return -_phi(d1) * d2 / sigma

def bs_charm(S, K, T, sigma, r=_RF_RATE):
    """Charm = dDelta/dt — delta decay per day"""
    d1, d2 = _bs_d1d2(S, K, T, sigma, r)
    if d1 is None or T <= 0: return 0.0
    return _phi(d1) * (2*r*T - d2*sigma*np.sqrt(T)) / (2*T*sigma*np.sqrt(T))


def calc_gex_advanced(c_all, p_all, spot):
    """
    Full GEX across ALL expirations. Returns:
    - gex_df: per-strike DataFrame with Call_GEX, Put_GEX, Net_GEX
    - key: dict with regime, total_gex_bn, gex_per_1pct_mn, gamma_flip,
            call_wall, put_wall, zero_gamma_pct
    """
    if c_all.empty or "Gamma" not in c_all.columns:
        return pd.DataFrame(), {}

    c2 = c_all[["Strike","OI","Gamma"]].copy()
    p2 = p_all[["Strike","OI","Gamma"]].copy() if not p_all.empty else pd.DataFrame()

    c2["C_GEX"] = c2["OI"] * c2["Gamma"] * 100 * spot**2
    if not p2.empty:
        p2["P_GEX"] = -p2["OI"] * p2["Gamma"].abs() * 100 * spot**2

    c_grp = c2.groupby("Strike")["C_GEX"].sum().reset_index()
    p_grp = p2.groupby("Strike")["P_GEX"].sum().reset_index() if not p2.empty else pd.DataFrame(columns=["Strike","P_GEX"])

    gex = c_grp.merge(p_grp, on="Strike", how="outer").fillna(0).sort_values("Strike")
    gex["Net_GEX"] = gex["C_GEX"] + gex["P_GEX"]
    gex["Abs_GEX"] = gex["Net_GEX"].abs()

    total      = gex["Net_GEX"].sum()
    total_bn   = round(total / 1e9, 2)
    per_1pct_mn = round(abs(total) * 0.01 / 1e6, 1)

    # Gamma Flip (HVL): cumulative GEX crossing zero from low to high strikes
    gex_s = gex.sort_values("Strike").copy()
    gex_s["CumGEX"] = gex_s["Net_GEX"].cumsum()
    gamma_flip = None
    cum = gex_s["CumGEX"].values; stk = gex_s["Strike"].values
    for i in range(1, len(cum)):
        if cum[i-1] * cum[i] < 0:
            w = abs(cum[i-1]) / (abs(cum[i-1]) + abs(cum[i]) + 1e-9)
            gamma_flip = round(float(stk[i-1] + (stk[i]-stk[i-1]) * w), 2)
            break

    # Call Wall: highest positive Net_GEX strike
    pos = gex[gex["Net_GEX"] > 0]
    call_wall = round(float(pos.loc[pos["Net_GEX"].idxmax(), "Strike"]), 2) if not pos.empty else None
    # Put Wall: most negative Net_GEX strike
    neg = gex[gex["Net_GEX"] < 0]
    put_wall  = round(float(neg.loc[neg["Net_GEX"].idxmin(), "Strike"]), 2) if not neg.empty else None

    regime = "POSITIVE" if total > 0 else ("NEGATIVE" if total < 0 else "NEUTRAL")
    zero_pct = round((gamma_flip - spot) / spot * 100, 2) if gamma_flip else None

    key = dict(
        total_gex=total, total_gex_bn=total_bn,
        gex_per_1pct_mn=per_1pct_mn, regime=regime,
        gamma_flip=gamma_flip, call_wall=call_wall, put_wall=put_wall,
        zero_gamma_pct=zero_pct,
    )
    gex_s["CumGEX_Bn"] = gex_s["CumGEX"] / 1e9
    return gex_s, key


def calc_gex_by_expiry(c_all, p_all, spot):
    """Net GEX contribution per expiration."""
    if c_all.empty: return pd.DataFrame()
    all_exps = sorted(set(
        (c_all["Expiry"].dropna().tolist() if "Expiry" in c_all.columns else []) +
        (p_all["Expiry"].dropna().tolist() if not p_all.empty and "Expiry" in p_all.columns else [])
    ))
    rows = []
    for exp in all_exps:
        c = c_all[c_all["Expiry"] == exp] if "Expiry" in c_all.columns else pd.DataFrame()
        p = p_all[p_all["Expiry"] == exp] if not p_all.empty and "Expiry" in p_all.columns else pd.DataFrame()
        # Safe DTE extraction — handles numpy scalars, arrays, strings
        dte = 0
        if not c.empty and "DTE" in c.columns:
            try:
                dte = int(float(np.asarray(c["DTE"].dropna().values[0]).flat[0]))
            except Exception:
                dte = 0
        c_gex = (c["Gamma"] * c["OI"] * 100 * spot**2).sum() if not c.empty and "Gamma" in c.columns else 0
        p_gex = -(p["Gamma"] * p["OI"] * 100 * spot**2).sum() if not p.empty and "Gamma" in p.columns else 0
        rows.append({"Expiry": exp, "DTE": dte,
                     "Call_GEX": c_gex / 1e9, "Put_GEX": p_gex / 1e9,
                     "Net_GEX": (c_gex + p_gex) / 1e9})
    return pd.DataFrame(rows).sort_values("DTE")


def calc_second_order_greeks(calls, puts, spot, r=_RF_RATE):
    """Add Vanna and Charm columns using Black-Scholes."""
    for df, opt_t in [(calls, "call"), (puts, "put")]:
        if df.empty or not all(c in df.columns for c in ["Strike","IV%","DTE"]):
            continue
        vannas, charms = [], []
        for _, row in df.iterrows():
            K  = _sf(row.get("Strike", 0))
            iv = _sf(row.get("IV%", 0)) / 100
            T  = max(_sf(row.get("DTE", 0)) / 365, 1e-6)
            sign = -1 if opt_t == "put" else 1
            v = bs_vanna(spot, K, T, iv, r)
            c = bs_charm(spot, K, T, iv, r)
            vannas.append(round(sign * v, 6))
            charms.append(round(sign * c, 6))
        df = df.copy()
        df["Vanna"] = vannas
        df["Charm"] = charms
    return calls, puts


def calc_gex(c, p, spot):
    """Backward-compat wrapper used by the metrics row."""
    gex_df, _ = calc_gex_advanced(c, p, spot)
    return gex_df


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
#  VOLATILITY ANALYTICS — HV, IV Rank, Cone, Regime
# ═══════════════════════════════════════════════════════════════════════════════

def calc_hv(closes: pd.Series, window: int) -> pd.Series:
    """Annualized historical volatility (close-to-close) as percentage."""
    lr = np.log(closes / closes.shift(1))
    return (lr.rolling(window).std() * np.sqrt(252) * 100).round(2)


def calc_vol_analytics(price_df: pd.DataFrame, atm_iv: float) -> dict:
    """
    Full volatility analysis from price history + current ATM IV.
    Returns a dict with all metrics and series needed for charts.
    """
    if price_df.empty or "close" not in price_df.columns or atm_iv is None:
        return {}

    closes = price_df["close"].dropna()
    if len(closes) < 30:
        return {}

    log_rets = np.log(closes / closes.shift(1)).dropna()

    # Rolling HV series
    hv20_s = calc_hv(closes, 20).dropna()
    hv30_s = calc_hv(closes, 30).dropna()
    hv60_s = calc_hv(closes, 60).dropna()
    hv90_s = calc_hv(closes, 90).dropna()

    # Current values (safe extraction)
    def _last(s):
        return round(float(np.asarray(s.iloc[-1]).flat[0]), 2) if len(s) > 0 else None

    hv20 = _last(hv20_s)
    hv30 = _last(hv30_s)
    hv60 = _last(hv60_s)
    hv90 = _last(hv90_s)

    # IV/HV ratio and spread
    iv_hv_ratio  = round(atm_iv / (hv30 + 1e-9), 2) if hv30 else None
    iv_hv_spread = round(atm_iv - hv30, 2)           if hv30 else None

    # HV Percentile: where does current HV30 rank in its 1-year history?
    hv_pct = None
    if len(hv30_s) >= 20:
        hv_pct = round(float((hv30_s < hv30).mean() * 100), 1)

    # IV Rank proxy: (IV - HV_min) / (HV_max - HV_min) × 100
    iv_rank = None
    if len(hv30_s) >= 20:
        hv_min = float(hv30_s.min())
        hv_max = float(hv30_s.max())
        if hv_max > hv_min:
            iv_rank = round(max(0.0, min(100.0, (atm_iv - hv_min) / (hv_max - hv_min) * 100)), 1)

    # Volatility Cone: percentile distribution of HV at multiple windows
    cone = {}
    for w, lbl in [(10,"HV10"),(20,"HV20"),(30,"HV30"),(60,"HV60"),(90,"HV90")]:
        s = calc_hv(closes, w).dropna()
        if len(s) >= w:
            cone[lbl] = {
                "p10":     round(float(s.quantile(0.10)), 2),
                "p25":     round(float(s.quantile(0.25)), 2),
                "p50":     round(float(s.quantile(0.50)), 2),
                "p75":     round(float(s.quantile(0.75)), 2),
                "p90":     round(float(s.quantile(0.90)), 2),
                "current": round(float(s.iloc[-1]), 2),
            }

    # Vol regime classification
    if iv_hv_ratio is not None:
        if iv_hv_ratio > 1.3:
            vol_regime = "IV CARA"
        elif iv_hv_ratio < 0.8:
            vol_regime = "IV BARATA"
        else:
            vol_regime = "IV NEUTRAL"
    else:
        vol_regime = "—"

    # Returns distribution stats
    ann_ret  = round(float(log_rets.mean() * 252 * 100), 2)
    skewness = round(float(log_rets.skew()), 3)
    kurt     = round(float(log_rets.kurt()), 3)

    return {
        "hv20": hv20, "hv30": hv30, "hv60": hv60, "hv90": hv90,
        "iv_hv_ratio":  iv_hv_ratio,
        "iv_hv_spread": iv_hv_spread,
        "hv_percentile": hv_pct,
        "iv_rank":       iv_rank,
        "vol_regime":    vol_regime,
        "cone":          cone,
        "hv20_series":   hv20_s,
        "hv30_series":   hv30_s,
        "hv60_series":   hv60_s,
        "log_returns":   log_rets,
        "closes":        closes,
        "ann_ret":       ann_ret,
        "skewness":      skewness,
        "kurtosis":      kurt,
        "dates":         price_df["date"],
    }


def calc_dex_advanced(c_all: pd.DataFrame, p_all: pd.DataFrame, spot: float) -> dict:
    """
    Delta Exposure (DEX) — net directional bias of options positioning.
    DEX(k) = OI(k) × Delta(k) × 100 × S
    """
    if c_all.empty or "Delta" not in c_all.columns:
        return {}
    c2 = c_all[["Strike","OI","Delta"]].copy()
    p2 = p_all[["Strike","OI","Delta"]].copy() if not p_all.empty else pd.DataFrame()

    c2["DEX"] = c2["OI"] * c2["Delta"].clip(0, 1) * 100 * spot
    if not p2.empty:
        p2["DEX"] = p2["OI"] * p2["Delta"].clip(-1, 0) * 100 * spot  # already negative

    c_grp = c2.groupby("Strike")["DEX"].sum().reset_index().rename(columns={"DEX":"C_DEX"})
    p_grp = p2.groupby("Strike")["DEX"].sum().reset_index().rename(columns={"DEX":"P_DEX"}) \
            if not p2.empty else pd.DataFrame(columns=["Strike","P_DEX"])

    dex = c_grp.merge(p_grp, on="Strike", how="outer").fillna(0).sort_values("Strike")
    dex["Net_DEX"] = dex["C_DEX"] + dex["P_DEX"]

    total_net = dex["Net_DEX"].sum()
    bias = "CALL-HEAVY (alcista)" if total_net > 0 else ("PUT-HEAVY (bajista)" if total_net < 0 else "NEUTRAL")

    return {
        "df": dex,
        "total_net_mn": round(total_net / 1e6, 1),
        "total_call_mn": round(dex["C_DEX"].sum() / 1e6, 1),
        "total_put_mn":  round(dex["P_DEX"].sum() / 1e6, 1),
        "bias": bias,
    }


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


def chart_gex_ladder(gex_df, spot, key, iv_adj=0.0):
    """
    Horizontal GEX ladder — GEXBot signature chart.
    Calls extend RIGHT (green), Puts LEFT (red).
    Y-axis = strike prices. Focus ±15% of spot.
    iv_adj: optional IV adjustment multiplier for sensitivity analysis.
    """
    if gex_df.empty: return None
    rng  = spot * 0.16
    df   = gex_df[(gex_df["Strike"] >= spot-rng) & (gex_df["Strike"] <= spot+rng)].copy()
    if df.empty: df = gex_df.copy()

    adj  = 1.0 + iv_adj   # simple scaling for sensitivity
    sc   = 1e9

    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=df["Strike"], x=df["C_GEX"]*adj/sc, orientation="h", name="Call GEX",
        marker=dict(color="rgba(34,197,94,0.72)", line=dict(width=0)),
        hovertemplate="Strike: $%{y:.1f}<br>Call GEX: $%{x:.2f}B<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        y=df["Strike"], x=df["P_GEX"]*adj/sc, orientation="h", name="Put GEX",
        marker=dict(color="rgba(244,63,94,0.72)", line=dict(width=0)),
        hovertemplate="Strike: $%{y:.1f}<br>Put GEX: $%{x:.2f}B<extra></extra>",
    ))

    # Spot line
    fig.add_hline(y=spot, line_dash="solid", line_color=_ORANGE, line_width=1.8,
                  annotation_text=f"  SPOT  ${spot:.2f}", annotation_font_size=10,
                  annotation_font_color=_ORANGE, annotation_position="top right")

    # Gamma Flip / HVL
    gf = key.get("gamma_flip")
    if gf:
        fig.add_hline(y=gf, line_dash="dot", line_color="#a855f7", line_width=1.2,
                      annotation_text=f"  HVL  ${gf:.0f}", annotation_font_size=9,
                      annotation_font_color="#a855f7", annotation_position="bottom right")

    # Call Wall
    cw = key.get("call_wall")
    if cw:
        fig.add_hline(y=cw, line_dash="dashdot", line_color=_GREEN, line_width=1,
                      annotation_text=f"  CALL WALL  ${cw:.0f}", annotation_font_size=9,
                      annotation_font_color=_GREEN, annotation_position="bottom right")

    # Put Wall
    pw = key.get("put_wall")
    if pw:
        fig.add_hline(y=pw, line_dash="dashdot", line_color=_RED, line_width=1,
                      annotation_text=f"  PUT WALL  ${pw:.0f}", annotation_font_size=9,
                      annotation_font_color=_RED, annotation_position="bottom right")

    # Zero GEX center line
    fig.add_vline(x=0, line_dash="dot", line_color="rgba(255,255,255,0.08)", line_width=1)

    regime_clr = _GREEN if key.get("regime") == "POSITIVE" else _RED
    fig.update_layout(
        height=600, barmode="overlay",
        xaxis_title="GEX ($B)",
        yaxis=dict(**_AX_NOZERO, tickformat="$,.0f", title="Strike"),
        xaxis=dict(**_AX_ZERO),
        title=dict(
            text=f"  {key.get('regime','?')} GAMMA  |  Net: ${key.get('total_gex_bn',0):+.2f}B"
                 f"  |  GEX/1%: ${key.get('gex_per_1pct_mn',0):.0f}M"
                 + (f"  |  IV adj: {iv_adj:+.0%}" if iv_adj != 0 else ""),
            font=dict(size=11, color=regime_clr, family=_FONT_MONO), x=0
        ),
        **_BASE,
    )
    return fig


def chart_gex_cumulative(gex_df, spot, key):
    """Cumulative GEX profile — shows gamma flip crossing."""
    if gex_df.empty or "CumGEX_Bn" not in gex_df.columns: return None
    df = gex_df.sort_values("Strike")
    pos = df[df["CumGEX_Bn"] >= 0]
    neg = df[df["CumGEX_Bn"] < 0]
    fig = go.Figure()
    if not pos.empty:
        fig.add_trace(go.Scatter(
            x=pos["Strike"], y=pos["CumGEX_Bn"], mode="lines", name="+GEX",
            line=dict(color=_GREEN, width=2),
            fill="tozeroy", fillcolor="rgba(34,197,94,0.08)",
            hovertemplate="Strike: $%{x}<br>Cum GEX: $%{y:.2f}B<extra></extra>",
        ))
    if not neg.empty:
        fig.add_trace(go.Scatter(
            x=neg["Strike"], y=neg["CumGEX_Bn"], mode="lines", name="-GEX",
            line=dict(color=_RED, width=2),
            fill="tozeroy", fillcolor="rgba(244,63,94,0.08)",
            hovertemplate="Strike: $%{x}<br>Cum GEX: $%{y:.2f}B<extra></extra>",
        ))
    fig.add_hline(y=0, line_dash="dot", line_color="rgba(255,255,255,0.12)", line_width=1)
    _vline(fig, spot)
    gf = key.get("gamma_flip")
    if gf:
        fig.add_vline(x=gf, line_dash="dot", line_color="#a855f7", line_width=1.2,
                      annotation_text=f"  HVL ${gf:.0f}", annotation_font_size=9,
                      annotation_font_color="#a855f7")
    fig.update_layout(height=240, xaxis_title="Strike", yaxis_title="Cum GEX ($B)", **_BASE)
    fig.update_xaxes(**_AX_NOZERO)
    fig.update_yaxes(**_AX_ZERO)
    return fig


def chart_gex_by_expiry(expiry_df):
    """Stacked bar: GEX contribution per expiration."""
    if expiry_df.empty or len(expiry_df) < 2: return None
    df = expiry_df.copy()
    df["Abs"] = df["Net_GEX"].abs()
    df = df.nlargest(14, "Abs").sort_values("DTE")
    labels = [f"{r['Expiry'][5:]}  ({r['DTE']}d)" for _, r in df.iterrows()]
    fig = go.Figure([
        go.Bar(x=labels, y=df["Call_GEX"], name="Calls",
               marker=dict(color="rgba(34,197,94,0.72)", line=dict(width=0)),
               hovertemplate="%{x}<br>Call GEX: $%{y:.2f}B<extra></extra>"),
        go.Bar(x=labels, y=df["Put_GEX"], name="Puts",
               marker=dict(color="rgba(244,63,94,0.72)", line=dict(width=0)),
               hovertemplate="%{x}<br>Put GEX: $%{y:.2f}B<extra></extra>"),
    ])
    fig.update_layout(height=300, barmode="relative",
                      xaxis_title="Expiración", yaxis_title="GEX ($B)", **_BASE)
    fig.update_xaxes(**_AX_NOZERO, tickangle=-40)
    fig.update_yaxes(**_AX_ZERO)
    return fig


def chart_vanna_charm(calls, puts, spot):
    """2nd-order Greeks: Vanna and Charm."""
    has_vanna = "Vanna" in calls.columns or "Vanna" in puts.columns
    has_charm = "Charm" in calls.columns or "Charm" in puts.columns
    if not has_vanna and not has_charm: return None

    fig = make_subplots(rows=1, cols=2,
        subplot_titles=["VANNA  dΔ/dVol", "CHARM  dΔ/dt  (delta decay/día)"],
        horizontal_spacing=0.10)
    for col_name, r, cc in [("Vanna",1,1), ("Charm",1,2)]:
        for df, lbl, clr in [(calls,"Calls",_GREEN),(puts,"Puts",_RED)]:
            if df.empty or col_name not in df.columns: continue
            d = df.sort_values("Strike")
            fig.add_trace(go.Scatter(
                x=d["Strike"], y=d[col_name], name=lbl,
                line=dict(color=clr, width=2), mode="lines",
                showlegend=(r==1 and cc==1), legendgroup=lbl,
                hovertemplate=f"Strike: %{{x}}<br>{col_name}: %{{y:.5f}}<extra>{lbl}</extra>",
            ), row=r, col=cc)
        _vline(fig, spot, row=r, col=cc)
    fig.update_layout(height=280, **_BASE)
    fig.update_xaxes(**_AX_NOZERO, title_text="Strike")
    fig.update_yaxes(**_AX_ZERO)
    for ann in fig.layout.annotations:
        ann.font.update(size=10, color="#606080", family=_FONT_MONO)
    return fig


def render_gex_module(calls_all, puts_all, calls_exp, puts_exp, spot):
    """
    Full professional GEX module — GEXBot-style.
    Includes: regime header, ladder, cumulative profile,
    expiry breakdown, 2nd-order Greeks, IV sensitivity.
    """
    gex_df, key = calc_gex_advanced(calls_all, puts_all, spot)
    expiry_df   = calc_gex_by_expiry(calls_all, puts_all, spot)
    calls_v, puts_v = calc_second_order_greeks(
        calls_exp.copy(), puts_exp.copy(), spot)

    regime    = key.get("regime", "N/A")
    r_color   = _GREEN if regime == "POSITIVE" else (_RED if regime == "NEGATIVE" else _ORANGE)
    total_bn  = key.get("total_gex_bn", 0)
    gex_sign  = "+" if total_bn >= 0 else ""
    gf        = key.get("gamma_flip")
    cw        = key.get("call_wall")
    pw        = key.get("put_wall")
    zp        = key.get("zero_gamma_pct")

    # ── Regime header ──────────────────────────────────────────────────────
    def _kv(label, value, color="#e0e0f0"):
        return (f'<div style="min-width:110px">'
                f'<div style="font-size:0.58rem;color:#505070;font-family:{_FONT_MONO};'
                f'text-transform:uppercase;letter-spacing:0.1em;margin-bottom:2px">{label}</div>'
                f'<div style="font-size:1.05rem;font-weight:800;color:{color};'
                f'font-family:{_FONT_MONO}">{value}</div></div>')

    hdr = (f'<div style="background:#0e0e1a;border:1px solid #1e1e30;border-radius:6px;'
           f'padding:0.9rem 1.4rem;display:flex;gap:2rem;align-items:center;flex-wrap:wrap;'
           f'margin-bottom:0.8rem;">')
    hdr += _kv("Régimen", f"{regime} Γ", r_color)
    hdr += _kv("Net GEX", f"${gex_sign}{total_bn:.2f}B", r_color)
    hdr += _kv("GEX / 1% move", f"${key.get('gex_per_1pct_mn',0):.0f}M")
    hdr += _kv("HVL / Gamma Flip", f"${gf:.0f}" if gf else "—", "#a855f7")
    if gf and zp is not None:
        sign = "▲" if zp > 0 else "▼"
        hdr += _kv("Spot → HVL", f"{sign} {abs(zp):.1f}%",
                   _GREEN if zp > 0 else _RED)
    hdr += _kv("Call Wall", f"${cw:.0f}" if cw else "—", _GREEN)
    hdr += _kv("Put Wall",  f"${pw:.0f}" if pw else "—", _RED)
    hdr += "</div>"
    st.markdown(hdr, unsafe_allow_html=True)

    # Interpretation
    if regime == "POSITIVE":
        msg = ("🟢 <b>Long Gamma (estabilizador)</b> — Los MMs venden rallies y compran "
               "caídas. Espera rangos más estrechos y comportamiento <i>mean-reverting</i>. "
               f"El spot debe superar el HVL (<b>${gf:.0f}</b>) para cambiar de régimen." if gf else
               "🟢 <b>Long Gamma</b> — régimen estabilizador.")
    elif regime == "NEGATIVE":
        msg = ("🔴 <b>Short Gamma (amplificador)</b> — Los MMs compran rallies y venden "
               "caídas. Los movimientos tienden a <i>acelerarse</i>. "
               f"Vigilar el HVL en <b>${gf:.0f}</b> como pivote de régimen." if gf else
               "🔴 <b>Short Gamma</b> — régimen amplificador.")
    else:
        msg = "🟡 <b>Gamma Neutral / Transitional</b> — mercado en equilibrio cerca del flip point."
    st.markdown(
        f'<p style="font-size:0.73rem;color:#7070a0;font-family:{_FONT_MONO};'
        f'margin:0 0 1rem;line-height:1.6">{msg}</p>',
        unsafe_allow_html=True)

    # ── IV Sensitivity slider ──────────────────────────────────────────────
    iv_adj = st.slider(
        "IV Sensitivity — ajusta la IV implícita para ver cómo cambia el GEX",
        min_value=-50, max_value=50, value=0, step=5,
        format="%d%%", key="gex_iv_adj",
    ) / 100.0

    # ── Main 2-column layout ───────────────────────────────────────────────
    col_l, col_r = st.columns([3, 1])

    with col_l:
        st.markdown('<p class="bb-header" style="margin-top:0.3rem">GEX LADDER  (todos los vencimientos)</p>',
                    unsafe_allow_html=True)
        st.caption("Calls → derecha (verde) · Puts → izquierda (rojo) · HVL = Gamma Flip")
        fig_lad = chart_gex_ladder(gex_df, spot, key, iv_adj)
        if fig_lad: st.plotly_chart(fig_lad, use_container_width=True)

    with col_r:
        st.markdown('<p class="bb-header" style="margin-top:0.3rem">GEX POR VENCIMIENTO</p>',
                    unsafe_allow_html=True)
        fig_exp = chart_gex_by_expiry(expiry_df)
        if fig_exp:
            st.plotly_chart(fig_exp, use_container_width=True)
        else:
            st.caption("Requiere >1 vencimiento.")

    # ── Cumulative profile ─────────────────────────────────────────────────
    st.markdown('<p class="bb-header">PERFIL ACUMULADO</p>', unsafe_allow_html=True)
    st.caption("Suma acumulada de GEX desde el strike más bajo al más alto. "
               "El cruce por cero = Gamma Flip / HVL — donde el régimen cambia.")
    fig_cum = chart_gex_cumulative(gex_df, spot, key)
    if fig_cum: st.plotly_chart(fig_cum, use_container_width=True)

    # ── 2nd-order Greeks ───────────────────────────────────────────────────
    st.markdown('<p class="bb-header">GREEKS DE 2° ORDEN  —  Vanna & Charm</p>',
                unsafe_allow_html=True)
    st.caption(
        "**Vanna** (dΔ/dVol): cuánto cambia Delta si la IV sube/baja — clave para "
        "rallies/sell-offs con expansión de volatilidad. "
        "**Charm** (dΔ/dt): decaimiento del Delta por día — esencial para 0DTE y estrategias "
        "de delta-hedging intradía. Calculados con Black-Scholes."
    )
    fig_vc = chart_vanna_charm(calls_v, puts_v, spot)
    if fig_vc: st.plotly_chart(fig_vc, use_container_width=True)
    else: st.caption("Requiere columnas IV% y DTE en la cadena.")


# ═══════════════════════════════════════════════════════════════════════════════
#  VOLATILITY CHARTS
# ═══════════════════════════════════════════════════════════════════════════════

def chart_vol_cone(analytics: dict, atm_iv: float, symbol: str):
    """
    Volatility Cone: historical percentile bands of HV vs current HV and IV.
    Shows whether options are cheap or expensive relative to realized vol.
    """
    cone = analytics.get("cone", {})
    if not cone:
        return None

    windows = list(cone.keys())
    p10  = [cone[w]["p10"]  for w in windows]
    p25  = [cone[w]["p25"]  for w in windows]
    p50  = [cone[w]["p50"]  for w in windows]
    p75  = [cone[w]["p75"]  for w in windows]
    p90  = [cone[w]["p90"]  for w in windows]
    curr = [cone[w]["current"] for w in windows]

    fig = go.Figure()

    # P10-P90 band
    fig.add_trace(go.Scatter(
        x=windows + windows[::-1],
        y=p90 + p10[::-1],
        fill="toself", fillcolor="rgba(59,130,246,0.06)",
        line=dict(color="rgba(0,0,0,0)"), showlegend=True, name="P10–P90",
        hoverinfo="skip",
    ))
    # P25-P75 band
    fig.add_trace(go.Scatter(
        x=windows + windows[::-1],
        y=p75 + p25[::-1],
        fill="toself", fillcolor="rgba(59,130,246,0.14)",
        line=dict(color="rgba(0,0,0,0)"), showlegend=True, name="P25–P75",
        hoverinfo="skip",
    ))
    # Median
    fig.add_trace(go.Scatter(
        x=windows, y=p50, name="Mediana HV",
        line=dict(color=_BLUE, width=1.5, dash="dot"),
        hovertemplate="%{x}: Mediana %{y:.1f}%<extra></extra>",
    ))
    # Current HV
    fig.add_trace(go.Scatter(
        x=windows, y=curr, name="HV Actual",
        line=dict(color=_ORANGE, width=2.5),
        mode="lines+markers", marker=dict(size=6),
        hovertemplate="%{x}: HV Actual %{y:.1f}%<extra></extra>",
    ))
    # ATM IV horizontal line
    if atm_iv:
        fig.add_hline(
            y=atm_iv, line_dash="dash", line_color=_GREEN, line_width=1.5,
            annotation_text=f"  ATM IV {atm_iv:.1f}%",
            annotation_font_color=_GREEN, annotation_font_size=10,
        )

    fig.update_layout(
        height=320,
        xaxis_title="Ventana de lookback",
        yaxis_title="Volatilidad (%)",
        title=dict(text=f"  VOLATILITY CONE  ·  {symbol}  ·  Bandas históricas P10/P25/P75/P90",
                   font=dict(size=11, color="#606080", family=_FONT_MONO), x=0),
        **_BASE,
    )
    fig.update_xaxes(**_AX_NOZERO)
    fig.update_yaxes(**_AX_NOZERO)
    return fig


def chart_iv_hv_history(analytics: dict, atm_iv: float):
    """IV vs HV30 time series — shows historical relationship over 1 year."""
    hv30_s = analytics.get("hv30_series")
    dates  = analytics.get("dates")
    if hv30_s is None or dates is None or len(hv30_s) < 10:
        return None

    # Align dates with HV series
    hv30_s = hv30_s.dropna()
    try:
        hv_dates = dates.iloc[hv30_s.index].reset_index(drop=True)
    except Exception:
        hv_dates = pd.Series(range(len(hv30_s)))

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=hv_dates, y=hv30_s.values,
        name="HV30", line=dict(color=_ORANGE, width=2),
        fill="tozeroy", fillcolor="rgba(249,115,22,0.06)",
        hovertemplate="Fecha: %{x|%Y-%m-%d}<br>HV30: %{y:.1f}%<extra></extra>",
    ))
    if atm_iv:
        fig.add_hline(
            y=atm_iv, line_dash="dash", line_color=_GREEN, line_width=1.5,
            annotation_text=f"  ATM IV {atm_iv:.1f}%",
            annotation_font_color=_GREEN, annotation_font_size=10,
        )

    # Highlight current position
    if len(hv30_s) > 0:
        last_date = hv_dates.iloc[-1] if hasattr(hv_dates, "iloc") else hv_dates[len(hv_dates)-1]
        last_hv   = float(hv30_s.iloc[-1])
        fig.add_trace(go.Scatter(
            x=[last_date], y=[last_hv],
            mode="markers", marker=dict(size=9, color=_ORANGE, line=dict(width=2, color="#0b0b14")),
            name="HV30 actual", showlegend=True,
            hovertemplate=f"HV30 actual: {last_hv:.1f}%<extra></extra>",
        ))

    fig.update_layout(
        height=260,
        xaxis_title="Fecha",
        yaxis_title="Volatilidad (%)",
        **_BASE,
    )
    fig.update_xaxes(**_AX_NOZERO)
    fig.update_yaxes(**_AX_NOZERO)
    return fig


def chart_returns_dist(analytics: dict, symbol: str):
    """Daily returns histogram with normal distribution overlay."""
    log_rets = analytics.get("log_returns")
    if log_rets is None or len(log_rets) < 20:
        return None

    rets_pct = (log_rets * 100).dropna()
    mu  = float(rets_pct.mean())
    sig = float(rets_pct.std())

    # Histogram
    fig = go.Figure()
    fig.add_trace(go.Histogram(
        x=rets_pct, name="Retornos",
        nbinsx=60,
        marker_color="rgba(59,130,246,0.55)",
        marker_line=dict(width=0),
        histnorm="probability density",
        hovertemplate="Retorno: %{x:.2f}%<br>Densidad: %{y:.4f}<extra></extra>",
    ))

    # Normal overlay
    x_norm = np.linspace(rets_pct.min(), rets_pct.max(), 200)
    y_norm = (1/(sig * np.sqrt(2*np.pi))) * np.exp(-0.5*((x_norm - mu)/sig)**2)
    fig.add_trace(go.Scatter(
        x=x_norm, y=y_norm, name="Normal",
        line=dict(color=_ORANGE, width=2, dash="dot"),
        hoverinfo="skip",
    ))

    # ±1σ, ±2σ lines
    for n, clr, lbl in [(1, "rgba(34,197,94,0.5)", "±1σ"), (2, "rgba(244,63,94,0.4)", "±2σ")]:
        for sign in [-1, 1]:
            fig.add_vline(x=mu + sign*n*sig, line_dash="dot", line_color=clr, line_width=1,
                          annotation_text=f" {lbl}" if sign > 0 else "",
                          annotation_font_size=9, annotation_font_color=clr)
    fig.add_vline(x=0, line_dash="dot", line_color="rgba(255,255,255,0.1)", line_width=1)

    skew = analytics.get("skewness", 0)
    kurt = analytics.get("kurtosis", 0)
    fig.update_layout(
        height=280,
        xaxis_title="Retorno diario (%)",
        yaxis_title="Densidad",
        title=dict(
            text=(f"  DISTRIBUCIÓN DE RETORNOS  ·  {symbol}  ·  "
                  f"μ={mu:.2f}%  σ={sig:.2f}%  Asimetría={skew:.2f}  Curtosis={kurt:.2f}"),
            font=dict(size=11, color="#606080", family=_FONT_MONO), x=0
        ),
        **_BASE,
    )
    fig.update_xaxes(**_AX_NOZERO)
    fig.update_yaxes(**_AX_NOZERO)
    return fig


def chart_dex(dex_data: dict, spot: float):
    """Proper Delta Exposure chart with call/put split and net bias."""
    if not dex_data or dex_data.get("df") is None:
        return None
    df = dex_data["df"]
    if df.empty:
        return None

    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=["DELTA EXPOSURE POR STRIKE", "NET DEX ACUMULADO"],
        vertical_spacing=0.18, row_heights=[0.65, 0.35],
    )

    # Bars
    fig.add_trace(go.Bar(
        x=df["Strike"], y=df["C_DEX"] / 1e6, name="Call DEX",
        marker=dict(color="rgba(34,197,94,0.72)", line=dict(width=0)),
        hovertemplate="Strike: %{x}<br>Call DEX: $%{y:.1f}M<extra></extra>",
    ), row=1, col=1)
    fig.add_trace(go.Bar(
        x=df["Strike"], y=df["P_DEX"] / 1e6, name="Put DEX",
        marker=dict(color="rgba(244,63,94,0.72)", line=dict(width=0)),
        hovertemplate="Strike: %{x}<br>Put DEX: $%{y:.1f}M<extra></extra>",
    ), row=1, col=1)
    _vline(fig, spot, row=1, col=1)

    # Cumulative net DEX
    cum = df["Net_DEX"].cumsum() / 1e6
    fig.add_trace(go.Scatter(
        x=df["Strike"], y=cum,
        name="Cum. Net DEX", line=dict(color=_PURPLE, width=2),
        fill="tozeroy", fillcolor="rgba(168,85,247,0.07)",
        hovertemplate="Strike: %{x}<br>Cum DEX: $%{y:.1f}M<extra></extra>",
    ), row=2, col=1)
    fig.add_hline(y=0, line_dash="dot", line_color="rgba(255,255,255,0.08)", row=2, col=1)
    _vline(fig, spot, row=2, col=1)

    bias  = dex_data.get("bias", "")
    net   = dex_data.get("total_net_mn", 0)
    sign  = "+" if net >= 0 else ""
    clr   = _GREEN if net >= 0 else _RED

    fig.update_layout(
        height=460, barmode="relative",
        title=dict(
            text=f"  DEX TOTAL: ${sign}{net:.0f}M  ·  {bias}",
            font=dict(size=11, color=clr, family=_FONT_MONO), x=0,
        ),
        **_BASE,
    )
    fig.update_xaxes(**_AX_NOZERO, title_text="Strike")
    fig.update_yaxes(**_AX_ZERO, title_text="DEX ($M)", row=1, col=1)
    fig.update_yaxes(**_AX_ZERO, title_text="Cum DEX ($M)", row=2, col=1)
    for ann in fig.layout.annotations:
        ann.font.update(size=10, color="#606080", family=_FONT_MONO)
    return fig


def render_vol_module(symbol: str, atm_iv: float, spot: float, price_df: pd.DataFrame):
    """
    Full volatility analysis module.
    Requires 1 year of daily price history.
    """
    if price_df.empty:
        st.caption("No se pudo cargar el historial de precios para el análisis de volatilidad.")
        return

    analytics = calc_vol_analytics(price_df, atm_iv)
    if not analytics:
        st.caption("Datos insuficientes para el análisis de volatilidad.")
        return

    hv20 = analytics.get("hv20")
    hv30 = analytics.get("hv30")
    hv60 = analytics.get("hv60")
    hv90 = analytics.get("hv90")
    ratio = analytics.get("iv_hv_ratio")
    spread = analytics.get("iv_hv_spread")
    hv_pct = analytics.get("hv_percentile")
    iv_rank = analytics.get("iv_rank")
    regime = analytics.get("vol_regime", "—")
    skew = analytics.get("skewness")
    kurt = analytics.get("kurtosis")
    ann_ret = analytics.get("ann_ret")

    regime_clr = (_RED if regime == "IV CARA" else
                  (_GREEN if regime == "IV BARATA" else _ORANGE))

    # ── Metrics panel ──────────────────────────────────────────────────────
    def _kv(label, value, color="#e0e0f0", sub=None):
        sub_html = f'<div style="font-size:0.6rem;color:#505070;font-family:{_FONT_MONO}">{sub}</div>' if sub else ""
        return (f'<div style="min-width:110px">'
                f'<div style="font-size:0.58rem;color:#505070;font-family:{_FONT_MONO};'
                f'text-transform:uppercase;letter-spacing:0.1em;margin-bottom:2px">{label}</div>'
                f'<div style="font-size:1.05rem;font-weight:800;color:{color};'
                f'font-family:{_FONT_MONO}">{value}</div>{sub_html}</div>')

    hdr = (f'<div style="background:#0e0e1a;border:1px solid #1e1e30;border-radius:6px;'
           f'padding:0.9rem 1.4rem;display:flex;gap:2rem;align-items:flex-start;'
           f'flex-wrap:wrap;margin-bottom:0.8rem;">')
    hdr += _kv("Régimen vol", regime, regime_clr)
    hdr += _kv("ATM IV",   f"{atm_iv:.1f}%" if atm_iv else "—")
    hdr += _kv("HV20",     f"{hv20:.1f}%"   if hv20  else "—", sub="20 días")
    hdr += _kv("HV30",     f"{hv30:.1f}%"   if hv30  else "—", sub="30 días")
    hdr += _kv("HV60",     f"{hv60:.1f}%"   if hv60  else "—", sub="60 días")
    hdr += _kv("HV90",     f"{hv90:.1f}%"   if hv90  else "—", sub="90 días")
    hdr += _kv("IV / HV30", f"{ratio:.2f}x" if ratio  else "—",
               regime_clr,  sub="> 1.30 cara · < 0.80 barata")
    hdr += _kv("IV − HV30", (f"+{spread:.1f}%" if spread >= 0 else f"{spread:.1f}%") if spread is not None else "—",
               _RED if (spread or 0) > 0 else _GREEN,
               sub="prima (+) o descuento (−)")
    hdr += _kv("HV Percentile", f"{hv_pct:.0f}°" if hv_pct is not None else "—",
               sub="vs historial 1 año")
    hdr += _kv("IV Rank (proxy)", f"{iv_rank:.0f}" if iv_rank is not None else "—",
               sub="0=mín histórico 100=máx")
    hdr += _kv("Asimetría", f"{skew:.3f}"  if skew  is not None else "—",
               _RED if (skew or 0) < -0.5 else "#e0e0f0",
               sub="< 0 = cola izquierda")
    hdr += _kv("Curtosis ex.", f"{kurt:.3f}" if kurt is not None else "—",
               sub="> 0 = colas gruesas")
    hdr += "</div>"
    st.markdown(hdr, unsafe_allow_html=True)

    # Interpretation
    if ratio is not None:
        if ratio > 1.3:
            interp = (f"📛 <b>IV cara</b> — Las opciones cotizan {ratio:.1f}x la HV30 realizada. "
                      "Estrategias de venta de volatilidad (credit spreads, iron condors, covered calls) "
                      "tienen ventaja estadística. La prima pagada por el mercado excede la vol realizada.")
        elif ratio < 0.8:
            interp = (f"💚 <b>IV barata</b> — Las opciones cotizan {ratio:.1f}x la HV30 realizada. "
                      "Comprar volatilidad (straddles, debit spreads, calendars) es favorable. "
                      "El mercado está subestimando la volatilidad que realmente está ocurriendo.")
        else:
            interp = (f"🟡 <b>IV neutral</b> — Las opciones cotizan {ratio:.1f}x la HV30. "
                      "Sin ventaja clara para compradores o vendedores de volatilidad. "
                      "Prioriza estrategias direccionales con spreads definidos.")
    else:
        interp = "Datos insuficientes para determinar el régimen de volatilidad."

    st.markdown(
        f'<p style="font-size:0.73rem;color:#7070a0;font-family:{_FONT_MONO};'
        f'margin:0 0 1rem;line-height:1.6">{interp}</p>',
        unsafe_allow_html=True,
    )

    # ── Charts ─────────────────────────────────────────────────────────────
    c_cone, c_hist = st.columns([3, 2])
    with c_cone:
        st.markdown('<p class="bb-header" style="margin-top:0">VOLATILITY CONE</p>',
                    unsafe_allow_html=True)
        st.caption("Bandas históricas de HV. La línea verde = ATM IV actual. "
                   "IV sobre la banda P75 → cara. Bajo P25 → barata.")
        fig_cone = chart_vol_cone(analytics, atm_iv, symbol)
        if fig_cone: st.plotly_chart(fig_cone, use_container_width=True)

    with c_hist:
        st.markdown('<p class="bb-header" style="margin-top:0">HV30 HISTÓRICA vs ATM IV</p>',
                    unsafe_allow_html=True)
        st.caption("Serie temporal de la volatilidad realizada a 30 días.")
        fig_hv = chart_iv_hv_history(analytics, atm_iv)
        if fig_hv: st.plotly_chart(fig_hv, use_container_width=True)

    # Returns distribution
    st.markdown('<p class="bb-header">DISTRIBUCIÓN DE RETORNOS DIARIOS</p>',
                unsafe_allow_html=True)
    st.caption(
        "Histograma de retornos reales vs distribución normal teórica. "
        "Curtosis > 0 = colas gruesas (fat tails) = riesgo extremo mayor de lo que la vol implica."
    )
    fig_rd = chart_returns_dist(analytics, symbol)
    if fig_rd: st.plotly_chart(fig_rd, use_container_width=True)
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
    dte_v = 0
    if not calls.empty and "DTE" in calls.columns:
        _dte_vals = calls["DTE"].dropna()
        if len(_dte_vals) > 0:
            try:
                dte_v = int(float(str(_dte_vals.values[0]).split(".")[0]))
            except Exception:
                dte_v = 0
    iv_atm = calc_atm_iv(calls, spot)
    p_c    = calc_pcr(calls, puts)
    mp     = calc_max_pain(calls, puts)
    em_lo, em_hi = calc_expected_move(spot, iv_atm, dte_v)
    _, gex_key  = calc_gex_advanced(calls_all, puts_all, spot)
    total_gex   = gex_key.get("total_gex_bn")
    skew_df = calc_iv_skew(calls, puts, spot)
    ts_df   = calc_term_structure(calls_all, spot)
    dex_data = calc_dex_advanced(calls_all, puts_all, spot)
    last_refresh = st.session_state.get("last_refresh", datetime.datetime.now())

    # ── Price history (cached per symbol per day) ─────────────────────────────
    ph_key = f"ph_{symbol}_{today}"
    if ph_key not in st.session_state:
        # Silently fetch — don't block the rest of the UI
        ph_df = fetch_price_history(symbol)
        st.session_state[ph_key] = ph_df
    price_df = st.session_state.get(ph_key, pd.DataFrame())

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

    # ── GEX MODULE ────────────────────────────────────────────────────────────
    st.markdown('<p class="bb-header">GAMMA EXPOSURE  ·  GEXBot-style</p>', unsafe_allow_html=True)
    render_gex_module(calls_all, puts_all, calls, puts, spot)

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

    # ── DELTA EXPOSURE (DEX) — Tier 2 ────────────────────────────────────────
    st.markdown('<p class="bb-header">DELTA EXPOSURE  (DEX)  ·  Tier 2</p>', unsafe_allow_html=True)
    st.caption(
        "DEX = OI × Delta × 100 × Spot. Mide el sesgo direccional neto del mercado de opciones. "
        "Call-heavy = soporte implícito de hedging debajo del spot. "
        "Put-heavy = resistencia implícita de hedging encima del spot."
    )
    fig_dex = chart_dex(dex_data, spot)
    if fig_dex:
        st.plotly_chart(fig_dex, use_container_width=True)

    st.markdown('<hr class="bb-divider">', unsafe_allow_html=True)

    # ── VOLATILITY ANALYSIS — Tier 2 ─────────────────────────────────────────
    st.markdown('<p class="bb-header">VOLATILITY ANALYSIS  ·  HV · IV Rank · Cone · Returns</p>',
                unsafe_allow_html=True)
    render_vol_module(symbol, iv_atm, spot, price_df)

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
    # ── 1. Capture OAuth code from URL IMMEDIATELY and clear it ──────────
    # Streamlit reruns the script on every interaction. If we don't clear
    # the URL right away, the app tries to re-exchange an already-used/expired code.
    if "code" in st.query_params:
        if not st.session_state.get("connected") and "oauth_code" not in st.session_state:
            st.session_state["oauth_code"] = st.query_params["code"]
        st.query_params.clear()   # always clear — even on reloads
        st.rerun()                # rerun with clean URL before doing anything else
        return

    # ── 2. Process captured code (runs on the clean-URL rerun) ───────────
    if "oauth_code" in st.session_state and not st.session_state.get("connected"):
        code     = st.session_state.pop("oauth_code")   # consume once, no retries
        callback = st.session_state.get("callback_url") or _secret("CALLBACK_URL", "https://127.0.0.1")
        app_key  = st.session_state.get("app_key")      or _secret("APP_KEY")
        app_sec  = st.session_state.get("app_secret")   or _secret("APP_SECRET")

        st.markdown(CSS, unsafe_allow_html=True)
        _, col, _ = st.columns([1, 1.2, 1])
        with col:
            if not app_key or not app_sec:
                st.error("No se encontraron APP_KEY / APP_SECRET en Secrets ni en sesión.")
                return

            with st.spinner("Autenticando con Schwab…"):
                creds = base64.b64encode(f"{app_key}:{app_sec}".encode()).decode()
                r = requests.post(
                    _TOKEN_URL,
                    headers={"Authorization": f"Basic {creds}",
                             "Content-Type": "application/x-www-form-urlencoded"},
                    data={"grant_type": "authorization_code",
                          "code": code,
                          "redirect_uri": callback},
                    timeout=15,
                )

            if r.ok:
                tok = r.json()
                st.session_state.update({
                    "app_key": app_key, "app_secret": app_sec,
                    "callback_url": callback, "connected": True,
                    "tokens": {
                        "access_token":  tok["access_token"],
                        "refresh_token": tok["refresh_token"],
                        "expiry": datetime.datetime.utcnow() + datetime.timedelta(
                            seconds=tok.get("expires_in", 1800)),
                    },
                })
                st.success("✅ Conectado correctamente.")
                st.markdown(
                    '<p style="color:#f97316;font-family:JetBrains Mono,monospace;'
                    'font-size:0.8rem;font-weight:700;margin:1rem 0 0.4rem;">'
                    '⭐ Guarda este Refresh Token en Secrets para no volver a autenticarte:</p>',
                    unsafe_allow_html=True,
                )
                st.code(f'REFRESH_TOKEN = "{tok["refresh_token"]}"', language="toml")
                st.caption("Streamlit Cloud → Manage App → Settings → Secrets → pega la línea → Save")
                if st.button("ENTRAR AL DASHBOARD →", type="primary", use_container_width=True):
                    st.rerun()
            else:
                body = r.text
                st.error(f"Error {r.status_code}: `{body}`")
                if "expired" in body or "invalid_grant" in body:
                    st.warning(
                        "El código de autorización expiró. "
                        "Vuelve a la pantalla anterior y haz clic en **AUTORIZAR EN SCHWAB** de nuevo. "
                        "Al volver a la app el código se captura automáticamente, sin copiar ni pegar."
                    )
                if st.button("← VOLVER", use_container_width=True):
                    st.rerun()
        return

    # ── 3. Auto-connect via Secrets (silent, no UI) ───────────────────────
    if not st.session_state.get("connected"):
        try_auto_connect()

    # ── 4. Dashboard or connect screen ───────────────────────────────────
    if st.session_state.get("connected"):
        show_dashboard()
    else:
        show_connect_screen()


if __name__ == "__main__":
    main()
