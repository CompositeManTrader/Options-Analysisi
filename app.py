"""
Options Chain Analyzer — Charles Schwab API
Powered by Schwabdev + Streamlit + Plotly
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import schwabdev
import datetime
import warnings

warnings.filterwarnings("ignore")

# ─── Page Config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Options Analyzer",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─── Global CSS ───────────────────────────────────────────────────────────────
CSS = """
<style>
.block-container { padding-top: 1.2rem; padding-bottom: 2rem; }

/* Metrics */
[data-testid="stMetric"] {
    background: white;
    border: 1px solid #e8ecf0;
    border-radius: 10px;
    padding: 14px 18px !important;
    box-shadow: 0 1px 4px rgba(0,0,0,0.04);
}
[data-testid="stMetricLabel"] {
    font-size: 0.7rem !important;
    color: #9ca3af !important;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    font-weight: 600 !important;
}
[data-testid="stMetricValue"] {
    font-size: 1.35rem !important;
    font-weight: 700 !important;
    color: #111827 !important;
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    gap: 4px; background: #f3f4f6;
    border-radius: 8px; padding: 3px;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 6px; padding: 6px 22px;
    font-weight: 500; font-size: 0.84rem; color: #6b7280;
}
.stTabs [aria-selected="true"] {
    background: white !important;
    color: #111827 !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.10);
}

/* Section labels */
.sec {
    font-size: 0.68rem; font-weight: 700;
    text-transform: uppercase; letter-spacing: 0.1em;
    color: #9ca3af; margin: 0 0 0.6rem;
}

/* Chain table */
.chain-wrap { overflow-x: auto; border-radius: 10px; border: 1px solid #e5e7eb; }
.chain { width: 100%; border-collapse: collapse; font-size: 0.8rem; }
.chain thead th {
    background: #f9fafb; color: #9ca3af;
    font-size: 0.68rem; font-weight: 700;
    text-transform: uppercase; letter-spacing: 0.07em;
    padding: 9px 12px; text-align: right;
    border-bottom: 1px solid #e5e7eb; white-space: nowrap;
}
.chain thead th.lft { text-align: left; }
.chain thead th.ctr { text-align: center; }
.chain tbody td {
    padding: 6px 12px; text-align: right;
    border-bottom: 1px solid #f3f4f6;
    font-variant-numeric: tabular-nums;
    color: #374151; white-space: nowrap;
}
.chain tbody td.lft { text-align: left; }
.chain tbody td.ctr { text-align: center; }
.chain tbody tr:last-child td { border-bottom: none; }
.chain tbody tr:hover td { background: #f9fafb !important; }
.itm-c td { background: rgba(16,185,129,0.05) !important; }
.itm-p td { background: rgba(239,68,68,0.05) !important; }
.atm   td { background: rgba(99,102,241,0.06) !important; }
.strike     { font-weight: 700; font-size: 0.85rem; color: #1f2937; }
.atm-strike { color: #4f46e5; font-weight: 800; }
.pos { color: #059669; font-weight: 500; }
.neg { color: #dc2626; font-weight: 500; }
.dim { color: #9ca3af; font-size: 0.75rem; }
.call-hdr { background: #f0fdf4 !important; color: #059669 !important; }
.put-hdr  { background: #fef2f2 !important; color: #dc2626 !important; }
.mid-hdr  { background: #f9fafb !important; color: #6b7280 !important; }

hr { border: none; border-top: 1px solid #f3f4f6; margin: 1.5rem 0; }

/* Connect screen */
.connect-logo  { font-size: 3rem; display: block; text-align: center; margin-bottom: 0.5rem; }
.connect-title { font-size: 1.6rem; font-weight: 800; color: #111827; text-align: center; margin: 0 0 0.3rem; }
.connect-sub   { font-size: 0.88rem; color: #6b7280; text-align: center; margin: 0 0 2rem; }

.footer { text-align: center; font-size: 0.7rem; color: #d1d5db; margin-top: 2.5rem; }
</style>
"""

# ═══════════════════════════════════════════════════════════════════
#  CONNECT SCREEN
# ═══════════════════════════════════════════════════════════════════
def show_connect_screen():
    st.markdown(CSS, unsafe_allow_html=True)
    st.markdown("<br><br>", unsafe_allow_html=True)

    _, col, _ = st.columns([1, 1.1, 1])
    with col:
        st.markdown("""
        <span class="connect-logo">📊</span>
        <h1 class="connect-title">Options Analyzer</h1>
        <p class="connect-sub">Ingresa tus credenciales de Charles Schwab para comenzar</p>
        """, unsafe_allow_html=True)

        app_key = st.text_input(
            "App Key",
            placeholder="Tu App Key de developer.schwab.com",
        )
        app_secret = st.text_input(
            "App Secret",
            type="password",
            placeholder="Tu App Secret",
        )
        with st.expander("⚙️ Callback URL (avanzado)"):
            callback = st.text_input(
                "Callback URL",
                value="https://127.0.0.1",
                help="Debe coincidir exactamente con la URL registrada en tu app de Schwab.",
            )

        if st.button("🔗 Conectar con Schwab", type="primary", use_container_width=True):
            if not app_key or not app_secret:
                st.error("Ingresa App Key y App Secret para continuar.")
                return
            with st.spinner("Conectando…"):
                try:
                    client = schwabdev.Client(app_key.strip(), app_secret.strip(), callback.strip())
                    st.session_state.client    = client
                    st.session_state.connected = True
                    st.rerun()
                except Exception as exc:
                    st.error(f"Error de conexión: {exc}")

        st.markdown("""
        <p style="text-align:center; font-size:0.78rem; color:#9ca3af; margin-top:1rem;">
            ¿Sin credenciales? →
            <a href="https://developer.schwab.com" target="_blank"
               style="color:#6366f1; text-decoration:none;">developer.schwab.com</a>
        </p>
        """, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════
#  DATA LAYER
# ═══════════════════════════════════════════════════════════════════
def fetch_chain(symbol, strike_count, from_date, to_date):
    try:
        r = st.session_state.client.option_chains(
            symbol=symbol, contractType="ALL",
            strikeCount=strike_count, includeUnderlyingQuote=True,
            fromDate=from_date, toDate=to_date,
        )
    except Exception as e:
        return None, str(e)
    return (r.json(), None) if r.status_code == 200 else (None, f"HTTP {r.status_code}")


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
    "impliedVolatility": "IV%", "delta": "Delta", "gamma": "Gamma",
    "theta": "Theta", "vega": "Vega", "rho": "Rho",
    "inTheMoney": "ITM", "theoreticalOptionValue": "Theo",
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
    return df


def by_exp(df, exp):
    return (df[df["Expiry"] == exp].copy()
            if not df.empty and "Expiry" in df.columns else df)


# ═══════════════════════════════════════════════════════════════════
#  ANALYTICS
# ═══════════════════════════════════════════════════════════════════
def calc_max_pain(c, p):
    if c.empty or p.empty or "OI" not in c.columns:
        return None
    strikes = sorted(set(c["Strike"].tolist() + p["Strike"].tolist()))
    co = c.set_index("Strike")["OI"].to_dict()
    po = p.set_index("Strike")["OI"].to_dict()
    pain = {s: sum(max(0., s-x)*co.get(x,0) + max(0., x-s)*po.get(x,0)
                   for x in strikes) for s in strikes}
    return min(pain, key=pain.get) if pain else None


def calc_pcr(c, p):
    if "OI" not in c.columns or "OI" not in p.columns:
        return None
    tot = c["OI"].sum()
    return round(p["OI"].sum() / tot, 2) if tot > 0 else None


def calc_atm_iv(c, spot):
    if c.empty or "IV%" not in c.columns or spot == 0:
        return None
    return c.loc[(c["Strike"] - spot).abs().idxmin(), "IV%"]


# ═══════════════════════════════════════════════════════════════════
#  HTML TABLE
# ═══════════════════════════════════════════════════════════════════
_CHAIN_COLS = ["Bid","Ask","Mark","Volume","OI","IV%","Delta","Gamma","Theta","Vega"]


def _fmt(v, col=""):
    if pd.isna(v):
        return '<span class="dim">—</span>'
    try:
        f = float(v)
    except (TypeError, ValueError):
        return str(v)
    if col == "IV%":
        return f"{f:.1f}%"
    if col in ("Volume","OI"):
        return f"{int(f):,}"
    if col == "Delta":
        cls = "pos" if f > 0 else ("neg" if f < 0 else "")
        return f'<span class="{cls}">{f:.3f}</span>'
    if col in ("Gamma","Vega","Rho"):
        return f"{f:.4f}"
    if col == "Theta":
        cls = "neg" if f < 0 else ""
        return f'<span class="{cls}">{f:.3f}</span>'
    return f"{f:.2f}"


def build_table(c_df, p_df, spot, mode):
    c_df = c_df.sort_values("Strike") if not c_df.empty else c_df
    p_df = p_df.sort_values("Strike") if not p_df.empty else p_df
    strikes = sorted(set(
        (c_df["Strike"].tolist() if not c_df.empty else []) +
        (p_df["Strike"].tolist() if not p_df.empty else [])
    ))
    if not strikes:
        return "<p>Sin datos.</p>"

    atm_s  = min(strikes, key=lambda s: abs(s - spot))
    c_idx  = c_df.set_index("Strike").to_dict("index") if not c_df.empty else {}
    p_idx  = p_df.set_index("Strike").to_dict("index") if not p_df.empty else {}
    c_cols = [c for c in _CHAIN_COLS if not c_df.empty and c in c_df.columns]
    p_cols = [c for c in _CHAIN_COLS if not p_df.empty and c in p_df.columns]

    def hdr(cols, side):
        cls = "call-hdr" if side == "call" else ("put-hdr" if side == "put" else "mid-hdr")
        return "".join(f'<th class="{cls} ctr">{c}</th>' for c in cols)

    def cells(row, cols):
        return "".join(f"<td>{_fmt(row.get(c, np.nan), c)}</td>" for c in cols)

    h = '<div class="chain-wrap"><table class="chain">'

    if mode == "calls":
        h += "<thead><tr>"
        h += '<th class="lft">Strike</th>'
        h += hdr(c_cols, "call")
        h += "</tr></thead><tbody>"
        for s in strikes:
            r   = c_idx.get(s, {})
            itm = r.get("ITM", False)
            rc  = "atm" if s == atm_s else ("itm-c" if itm else "")
            sc  = "atm-strike" if s == atm_s else "strike"
            h  += f'<tr class="{rc}"><td class="lft"><span class="{sc}">${s:.1f}</span></td>'
            h  += cells(r, c_cols)
            h  += "</tr>"

    elif mode == "puts":
        h += "<thead><tr>"
        h += '<th class="lft">Strike</th>'
        h += hdr(p_cols, "put")
        h += "</tr></thead><tbody>"
        for s in strikes:
            r   = p_idx.get(s, {})
            itm = r.get("ITM", False)
            rc  = "atm" if s == atm_s else ("itm-p" if itm else "")
            sc  = "atm-strike" if s == atm_s else "strike"
            h  += f'<tr class="{rc}"><td class="lft"><span class="{sc}">${s:.1f}</span></td>'
            h  += cells(r, p_cols)
            h  += "</tr>"

    else:  # both
        h += "<thead>"
        h += "<tr>"
        h += f'<th colspan="{len(c_cols)}" class="call-hdr ctr" style="border-right:2px solid #d1fae5;">▲ CALLS</th>'
        h += '<th class="mid-hdr ctr" style="border-left:2px solid #d1fae5;border-right:2px solid #fee2e2;">$</th>'
        h += f'<th colspan="{len(p_cols)}" class="put-hdr ctr" style="border-left:2px solid #fee2e2;">▼ PUTS</th>'
        h += "</tr><tr>"
        h += hdr(c_cols, "call")
        h += '<th class="mid-hdr ctr" style="border-left:2px solid #d1fae5;border-right:2px solid #fee2e2;">Strike</th>'
        h += hdr(p_cols, "put")
        h += "</tr></thead><tbody>"

        for s in strikes:
            cr   = c_idx.get(s, {})
            pr   = p_idx.get(s, {})
            c_itm = cr.get("ITM", False)
            p_itm = pr.get("ITM", False)
            is_atm = s == atm_s
            h += "<tr>"
            for col in c_cols:
                bg  = "background:rgba(16,185,129,0.06);" if c_itm and not is_atm else ""
                bld = "font-weight:700;" if is_atm else ""
                h  += f'<td style="{bg}{bld}">{_fmt(cr.get(col, np.nan), col)}</td>'
            mid = ("background:rgba(99,102,241,0.08);color:#4f46e5;font-weight:800;font-size:.88rem;"
                   if is_atm else
                   "background:#f9fafb;color:#374151;font-weight:600;font-size:.85rem;")
            h += (f'<td class="ctr" style="{mid} border-left:2px solid #d1fae5;'
                  f'border-right:2px solid #fee2e2;">${s:.1f}</td>')
            for col in p_cols:
                bg  = "background:rgba(239,68,68,0.06);" if p_itm and not is_atm else ""
                bld = "font-weight:700;" if is_atm else ""
                h  += f'<td style="{bg}{bld}">{_fmt(pr.get(col, np.nan), col)}</td>'
            h += "</tr>"

    h += "</tbody></table></div>"
    return h


# ═══════════════════════════════════════════════════════════════════
#  CHARTS
# ═══════════════════════════════════════════════════════════════════
_CC   = "#10b981"
_PC   = "#ef4444"
_GRID = "rgba(0,0,0,0.05)"
_BG   = "rgba(0,0,0,0)"
_BASE = dict(
    plot_bgcolor=_BG, paper_bgcolor=_BG,
    font=dict(size=11, family="Inter, sans-serif"),
    margin=dict(l=55, r=20, t=45, b=40),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    hoverlabel=dict(bgcolor="white", font_size=12, bordercolor="#e5e7eb"),
)
_AX = dict(showgrid=True, gridcolor=_GRID, zeroline=False,
           linecolor="#e5e7eb", linewidth=1, showline=True)


def _vline(fig, x, row=None, col=None):
    kw = dict(x=x, line_dash="dot", line_color="rgba(99,102,241,0.5)",
              line_width=1.5, annotation_text=f"  ${x:.0f}",
              annotation_font_size=10, annotation_font_color="#6366f1")
    if row:
        kw.update(row=row, col=col)
    fig.add_vline(**kw)


def chart_greeks(c, p, spot):
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=["<b>Delta</b>","<b>Gamma</b>","<b>Theta</b> (decay/día)","<b>IV Smile</b>"],
        vertical_spacing=0.2, horizontal_spacing=0.10,
    )
    for g, r, cc in [("Delta",1,1),("Gamma",1,2),("Theta",2,1),("IV%",2,2)]:
        first = r == 1 and cc == 1
        for df, lbl, clr in [(c,"Calls",_CC),(p,"Puts",_PC)]:
            if df.empty or g not in df.columns:
                continue
            d = df.sort_values("Strike")
            fig.add_trace(go.Scatter(
                x=d["Strike"], y=d[g], name=lbl,
                line=dict(color=clr, width=2.5),
                mode="lines+markers", marker=dict(size=5),
                showlegend=first, legendgroup=lbl,
                hovertemplate=f"Strike: %{{x}}<br>{g}: %{{y}}<extra>{lbl}</extra>",
            ), row=r, col=cc)
        _vline(fig, spot, row=r, col=cc)
    fig.update_layout(height=520, **_BASE)
    fig.update_xaxes(**_AX, title_text="Strike")
    fig.update_yaxes(**_AX)
    for r, cc in [(1,1),(2,1)]:
        fig.update_yaxes(zeroline=True, zerolinecolor="rgba(0,0,0,0.1)",
                         zerolinewidth=1.2, row=r, col=cc)
    fig.update_yaxes(title_text="IV (%)", row=2, col=2)
    return fig


def chart_oi_vol(c, p, spot):
    fig = make_subplots(rows=1, cols=2,
                        subplot_titles=["<b>Open Interest</b>","<b>Volumen</b>"],
                        horizontal_spacing=0.10)
    for metric, col in [("OI",1),("Volume",2)]:
        for df, lbl, clr in [(c,"Calls","rgba(16,185,129,0.72)"),(p,"Puts","rgba(239,68,68,0.72)")]:
            if df.empty or metric not in df.columns:
                continue
            d = df.sort_values("Strike")
            fig.add_trace(go.Bar(
                x=d["Strike"], y=d[metric], name=lbl,
                marker_color=clr, showlegend=(col==1), legendgroup=lbl,
                hovertemplate=f"Strike: %{{x}}<br>{metric}: %{{y:,}}<extra>{lbl}</extra>",
            ), row=1, col=col)
        _vline(fig, spot, row=1, col=col)
    fig.update_layout(height=340, barmode="overlay", **_BASE)
    fig.update_xaxes(**_AX, title_text="Strike")
    fig.update_yaxes(**_AX)
    return fig


def chart_iv_surface(c, p):
    fig = go.Figure()
    for df, lbl in [(c,"Calls"),(p,"Puts")]:
        if df.empty or "IV%" not in df.columns:
            continue
        dte_col = df["DTE"].tolist() if "DTE" in df.columns else [0]*len(df)
        fig.add_trace(go.Scatter(
            x=df["Strike"], y=df["IV%"], mode="markers", name=lbl,
            marker=dict(size=8, color=dte_col, colorscale="Viridis",
                        showscale=(lbl=="Calls"),
                        colorbar=dict(title="DTE", thickness=14, len=0.85,
                                      tickfont=dict(size=10)) if lbl=="Calls" else None,
                        opacity=0.8, line=dict(width=1, color="rgba(255,255,255,0.6)")),
            hovertemplate="Strike: %{x}<br>IV: %{y:.1f}%<extra>" + lbl + "</extra>",
        ))
    fig.update_layout(height=360, xaxis_title="Strike", yaxis_title="IV (%)", **_BASE)
    fig.update_xaxes(**_AX)
    fig.update_yaxes(**_AX)
    return fig


def chart_delta_exp(c, p):
    if c.empty or not {"OI","Delta"}.issubset(c.columns):
        return None
    c2, p2 = c.copy(), p.copy()
    c2["DE"] =  c2["OI"] * c2["Delta"] * 100
    p2["DE"] = -p2["OI"] * p2["Delta"].abs() * 100
    fig = go.Figure([
        go.Bar(x=c2["Strike"], y=c2["DE"], name="Calls",
               marker_color="rgba(16,185,129,0.72)",
               hovertemplate="Strike: %{x}<br>ΔExp: %{y:,.0f}<extra>Calls</extra>"),
        go.Bar(x=p2["Strike"], y=p2["DE"], name="Puts",
               marker_color="rgba(239,68,68,0.72)",
               hovertemplate="Strike: %{x}<br>ΔExp: %{y:,.0f}<extra>Puts</extra>"),
    ])
    fig.update_layout(height=320, barmode="relative",
                      xaxis_title="Strike", yaxis_title="OI × Δ × 100", **_BASE)
    fig.update_xaxes(**_AX)
    fig.update_yaxes(**_AX, zeroline=True,
                     zerolinecolor="rgba(0,0,0,0.15)", zerolinewidth=1.2)
    return fig


# ═══════════════════════════════════════════════════════════════════
#  MAIN APP
# ═══════════════════════════════════════════════════════════════════
def main():
    st.markdown(CSS, unsafe_allow_html=True)

    if not st.session_state.get("connected"):
        show_connect_screen()
        return

    # ── Top bar ───────────────────────────────────────────────────
    t1, t2, t3, _, t4 = st.columns([1.4, 1.3, 1.8, 2.5, 0.65])

    with t1:
        st.markdown("### 📊 Options Analyzer")

    with t2:
        symbol = st.text_input(
            "sym", value=st.session_state.get("symbol","AAPL"),
            placeholder="SPY, AAPL…", label_visibility="collapsed",
        ).upper().strip()

    today = datetime.date.today()
    need_load = symbol and (
        st.session_state.get("last_sym") != symbol
        or "chain_data" not in st.session_state
    )

    if need_load:
        with st.spinner(f"Cargando {symbol}…"):
            data, err = fetch_chain(
                symbol, 25,
                today.strftime("%Y-%m-%d"),
                (today + datetime.timedelta(days=120)).strftime("%Y-%m-%d"),
            )
        if err:
            st.error(f"❌ {err}")
            return
        if not data or data.get("status") == "FAILED":
            st.warning(f"No se encontraron opciones para **{symbol}**.")
            return
        st.session_state.chain_data = data
        st.session_state.last_sym   = symbol
        st.session_state.symbol     = symbol

    if "chain_data" not in st.session_state:
        st.info("Ingresa un símbolo arriba.")
        return

    data = st.session_state.chain_data
    calls_raw, puts_raw, ul = parse_chain(data)
    calls_c = clean(calls_raw)
    puts_c  = clean(puts_raw)

    all_exps = sorted(set(
        (calls_c["Expiry"].tolist() if not calls_c.empty and "Expiry" in calls_c.columns else []) +
        (puts_c["Expiry"].tolist()  if not puts_c.empty  and "Expiry" in puts_c.columns  else [])
    ))

    with t3:
        sel_exp = st.selectbox("exp", options=all_exps, label_visibility="collapsed")

    with t4:
        if st.button("Salir", use_container_width=True):
            for k in ["client","connected","chain_data","last_sym","symbol"]:
                st.session_state.pop(k, None)
            st.rerun()

    # ── Filter by expiration ──────────────────────────────────────
    calls = by_exp(calls_c, sel_exp).sort_values("Strike") if not calls_c.empty else calls_c
    puts  = by_exp(puts_c,  sel_exp).sort_values("Strike") if not puts_c.empty  else puts_c

    spot  = float(ul.get("mark") or ul.get("last") or ul.get("close") or 0)
    chg   = float(ul.get("netChange", 0) or 0)
    chg_p = float(ul.get("percentChange", 0) or 0)
    bid_u = float(ul.get("bid", 0) or 0)
    ask_u = float(ul.get("ask", 0) or 0)

    # ── Metrics ───────────────────────────────────────────────────
    dte_v = int(calls["DTE"].iloc[0]) if not calls.empty and "DTE" in calls.columns else 0
    iv_a  = calc_atm_iv(calls, spot)
    p_c   = calc_pcr(calls, puts)
    mp    = calc_max_pain(calls, puts)

    m1,m2,m3,m4,m5,m6 = st.columns(6)
    m1.metric("Precio",    f"${spot:.2f}",  f"{chg:+.2f} ({chg_p:+.1f}%)")
    m2.metric("Bid / Ask", f"${bid_u:.2f} / ${ask_u:.2f}")
    m3.metric("DTE",       f"{dte_v} días")
    m4.metric("ATM IV",    f"{iv_a:.1f}%" if iv_a else "—")
    m5.metric("P/C Ratio", f"{p_c:.2f}"   if p_c  else "—")
    m6.metric("Max Pain",  f"${mp:.0f}"   if mp   else "—")

    st.markdown("<hr>", unsafe_allow_html=True)

    # ── Options chain ─────────────────────────────────────────────
    st.markdown('<p class="sec">Cadena de Opciones</p>', unsafe_allow_html=True)

    tab_c, tab_p, tab_b = st.tabs(["🟢  Calls", "🔴  Puts", "🔄  Vista Completa"])
    with tab_c:
        st.markdown(build_table(calls, puts, spot, "calls"), unsafe_allow_html=True)
    with tab_p:
        st.markdown(build_table(calls, puts, spot, "puts"),  unsafe_allow_html=True)
    with tab_b:
        st.markdown(build_table(calls, puts, spot, "both"),  unsafe_allow_html=True)

    st.markdown("<hr>", unsafe_allow_html=True)

    # ── Greeks ────────────────────────────────────────────────────
    st.markdown('<p class="sec">Greeks por Strike</p>', unsafe_allow_html=True)
    st.plotly_chart(chart_greeks(calls, puts, spot), use_container_width=True)

    st.markdown("<hr>", unsafe_allow_html=True)

    # ── OI / Volume ───────────────────────────────────────────────
    st.markdown('<p class="sec">Open Interest & Volumen</p>', unsafe_allow_html=True)
    st.plotly_chart(chart_oi_vol(calls, puts, spot), use_container_width=True)

    st.markdown("<hr>", unsafe_allow_html=True)

    # ── IV Surface (all expirations) ──────────────────────────────
    st.markdown('<p class="sec">Superficie de Volatilidad Implícita</p>', unsafe_allow_html=True)
    st.caption("Todos los vencimientos · Color = DTE (más oscuro = más tiempo restante)")
    st.plotly_chart(chart_iv_surface(calls_c, puts_c), use_container_width=True)

    st.markdown("<hr>", unsafe_allow_html=True)

    # ── Delta Exposure ────────────────────────────────────────────
    st.markdown('<p class="sec">Delta Exposure — proxy GEX</p>', unsafe_allow_html=True)
    st.caption("Positivo = calls dominan el OI · Negativo = puts dominan")
    fig_de = chart_delta_exp(calls, puts)
    if fig_de:
        st.plotly_chart(fig_de, use_container_width=True)

    st.markdown(
        f'<p class="footer">Actualizado {datetime.datetime.now().strftime("%H:%M:%S")} · '
        "Charles Schwab API · No constituye asesoramiento financiero</p>",
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
