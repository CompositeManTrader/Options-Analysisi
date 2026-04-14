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
import os
import datetime
import warnings

warnings.filterwarnings("ignore")

# ─── Page Config ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Options Analyzer | Schwab",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Custom CSS ───────────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
        /* Metric cards */
        [data-testid="metric-container"] {
            background-color: #f8f9fa;
            border: 1px solid #dee2e6;
            border-radius: 8px;
            padding: 12px 16px;
        }
        /* Sidebar */
        [data-testid="stSidebar"] { background-color: #fafafa; }
        /* Tab styling */
        .stTabs [data-baseweb="tab-list"] { gap: 8px; }
        .stTabs [data-baseweb="tab"] {
            background-color: #f0f2f6;
            border-radius: 6px;
            padding: 6px 18px;
        }
        /* Dataframe header */
        thead tr th { background-color: #e9ecef !important; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ─── Auth ─────────────────────────────────────────────────────────────────────
def _get_secret(key: str, default: str | None = None) -> str | None:
    """
    Lee credenciales con doble fallback:
      1. st.secrets  → Streamlit Cloud (o .streamlit/secrets.toml local)
      2. os.environ  → variables de entorno del sistema
    Nunca hardcodees valores aquí.
    """
    try:
        return st.secrets[key]
    except (KeyError, FileNotFoundError):
        return os.environ.get(key, default)


@st.cache_resource(show_spinner="Autenticando con Schwab...")
def get_client():
    app_key    = _get_secret("APP_KEY")
    app_secret = _get_secret("APP_SECRET")
    callback   = _get_secret("CALLBACK_URL", "https://127.0.0.1")

    if not app_key or not app_secret:
        st.error(
            "❌ **Credenciales no encontradas.**\n\n"
            "**Local:** crea `.streamlit/secrets.toml` con `APP_KEY` y `APP_SECRET` "
            "(copia `.streamlit/secrets.toml.example` como referencia).\n\n"
            "**Streamlit Cloud:** ve a *Settings → Secrets* en el dashboard de tu app "
            "y agrega las mismas claves."
        )
        st.stop()

    try:
        client = schwabdev.Client(app_key, app_secret, callback)
        return client
    except Exception as exc:
        st.error(f"❌ Error de autenticación: {exc}")
        st.stop()


# ─── Data Fetching ────────────────────────────────────────────────────────────
def fetch_option_chain(symbol: str, contract_type: str, strike_count: int,
                       from_date: str, to_date: str):
    """Fetch raw option chain from Schwab API. Returns (data_dict, error_str)."""
    client = get_client()
    try:
        resp = client.option_chains(
            symbol=symbol,
            contractType=contract_type,
            strikeCount=strike_count,
            includeUnderlyingQuote=True,
            fromDate=from_date,
            toDate=to_date,
        )
    except Exception as exc:
        return None, str(exc)

    if resp.status_code == 200:
        return resp.json(), None
    return None, f"HTTP {resp.status_code}: {resp.text[:300]}"


# ─── Parsing ──────────────────────────────────────────────────────────────────
def parse_option_chain(data: dict):
    """
    Flatten the nested callExpDateMap / putExpDateMap structures
    into two clean DataFrames (calls, puts) + underlying dict.
    """
    calls_rows, puts_rows = [], []

    for row_list, exp_map_key in [
        (calls_rows, "callExpDateMap"),
        (puts_rows,  "putExpDateMap"),
    ]:
        for exp_key, strikes in data.get(exp_map_key, {}).items():
            exp_date, dte_str = exp_key.split(":")
            dte = int(dte_str)
            for strike_str, options in strikes.items():
                for opt in options:
                    opt["expiration_date"] = exp_date
                    opt["dte"]             = dte
                    row_list.append(opt)

    calls_df = pd.DataFrame(calls_rows) if calls_rows else pd.DataFrame()
    puts_df  = pd.DataFrame(puts_rows)  if puts_rows  else pd.DataFrame()
    underlying = data.get("underlying", {})

    return calls_df, puts_df, underlying


_COLUMN_MAP = {
    "strikePrice":            "Strike",
    "expiration_date":        "Expiry",
    "dte":                    "DTE",
    "bid":                    "Bid",
    "ask":                    "Ask",
    "mark":                   "Mark",
    "last":                   "Last",
    "totalVolume":            "Volume",
    "openInterest":           "OI",
    "impliedVolatility":      "IV%",
    "delta":                  "Delta",
    "gamma":                  "Gamma",
    "theta":                  "Theta",
    "vega":                   "Vega",
    "rho":                    "Rho",
    "inTheMoney":             "ITM",
    "theoreticalOptionValue": "TheoVal",
}


def clean_df(df: pd.DataFrame) -> pd.DataFrame:
    """Rename columns and round values to display-friendly precision."""
    if df.empty:
        return df

    available = {k: v for k, v in _COLUMN_MAP.items() if k in df.columns}
    df = df[list(available.keys())].rename(columns=available).copy()

    # Precision
    for col, decimals in [
        ("Bid", 2), ("Ask", 2), ("Mark", 2), ("Last", 2), ("TheoVal", 2),
        ("Delta", 3), ("Theta", 3),
        ("Gamma", 4), ("Vega", 4), ("Rho", 4),
        ("Strike", 2),
    ]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").round(decimals)

    # IV as percentage
    if "IV%" in df.columns:
        df["IV%"] = (pd.to_numeric(df["IV%"], errors="coerce") * 100).round(2)

    return df


# ─── Analytics ────────────────────────────────────────────────────────────────
def calc_max_pain(calls_df: pd.DataFrame, puts_df: pd.DataFrame):
    """Max pain strike = strike that causes greatest loss for option buyers."""
    if calls_df.empty or puts_df.empty:
        return None
    if "OI" not in calls_df.columns or "OI" not in puts_df.columns:
        return None

    strikes = sorted(
        set(calls_df["Strike"].tolist() + puts_df["Strike"].tolist())
    )
    calls_oi = calls_df.set_index("Strike")["OI"].to_dict()
    puts_oi  = puts_df.set_index("Strike")["OI"].to_dict()

    pain = {}
    for exp_s in strikes:
        c_loss = sum(max(0.0, exp_s - s) * calls_oi.get(s, 0) for s in strikes)
        p_loss = sum(max(0.0, s - exp_s) * puts_oi.get(s, 0) for s in strikes)
        pain[exp_s] = c_loss + p_loss

    return min(pain, key=pain.get) if pain else None


def calc_pcr(calls_df: pd.DataFrame, puts_df: pd.DataFrame):
    """Put / Call ratio by open interest."""
    if "OI" not in calls_df.columns or "OI" not in puts_df.columns:
        return None
    call_oi = calls_df["OI"].sum()
    put_oi  = puts_df["OI"].sum()
    return round(put_oi / call_oi, 2) if call_oi > 0 else None


def get_atm_iv(calls_df: pd.DataFrame, spot: float) -> float | None:
    """IV of the call closest to ATM."""
    if calls_df.empty or "IV%" not in calls_df.columns:
        return None
    idx = (calls_df["Strike"] - spot).abs().idxmin()
    return calls_df.loc[idx, "IV%"]


# ─── Charts ───────────────────────────────────────────────────────────────────
_CALL_COLOR = "#2196F3"
_PUT_COLOR  = "#F44336"
_GRID_COLOR = "rgba(128,128,128,0.12)"
_BG         = "rgba(0,0,0,0)"

_BASE_LAYOUT = dict(
    plot_bgcolor=_BG,
    paper_bgcolor=_BG,
    font=dict(size=12),
    margin=dict(l=50, r=30, t=50, b=40),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
)


def _axis_style():
    return dict(showgrid=True, gridcolor=_GRID_COLOR, zeroline=False)


def _add_spot_line(fig, spot, row=None, col=None):
    kwargs = dict(
        x=spot, line_dash="dot", line_color="rgba(120,120,120,0.6)", line_width=1.2,
        annotation_text=f"  ${spot:.2f}", annotation_position="top right",
        annotation_font_size=10,
    )
    if row is not None:
        kwargs["row"] = row
        kwargs["col"] = col
    fig.add_vline(**kwargs)


def plot_greeks(calls_df: pd.DataFrame, puts_df: pd.DataFrame, spot: float):
    """2×2 subplot: Delta, Gamma, Theta, IV Smile."""
    titles = ("Delta", "Gamma", "Theta (por día)", "IV Smile (%)")
    fig = make_subplots(rows=2, cols=2, subplot_titles=titles,
                        vertical_spacing=0.18, horizontal_spacing=0.10)

    greek_pairs = [
        ("Delta",  1, 1),
        ("Gamma",  1, 2),
        ("Theta",  2, 1),
        ("IV%",    2, 2),
    ]

    for greek, row, col in greek_pairs:
        show_legend = (row == 1 and col == 1)
        for df, label, color in [
            (calls_df, "Call", _CALL_COLOR),
            (puts_df,  "Put",  _PUT_COLOR),
        ]:
            if df.empty or greek not in df.columns:
                continue
            d = df.sort_values("Strike")
            fig.add_trace(
                go.Scatter(
                    x=d["Strike"],
                    y=d[greek],
                    name=f"{label}",
                    line=dict(color=color, width=2),
                    mode="lines+markers",
                    marker=dict(size=4),
                    showlegend=show_legend,
                    legendgroup=label,
                ),
                row=row, col=col,
            )
        _add_spot_line(fig, spot, row=row, col=col)

    fig.update_layout(height=560, **_BASE_LAYOUT)
    fig.update_xaxes(**_axis_style())
    fig.update_yaxes(**_axis_style())
    # Zero line for Delta and Theta
    fig.update_yaxes(zeroline=True, zerolinecolor="rgba(128,128,128,0.3)",
                     zerolinewidth=1, row=1, col=1)
    fig.update_yaxes(zeroline=True, zerolinecolor="rgba(128,128,128,0.3)",
                     zerolinewidth=1, row=2, col=1)
    return fig


def plot_oi_volume(calls_df: pd.DataFrame, puts_df: pd.DataFrame, spot: float):
    """Side-by-side bars: Open Interest & Volume by strike."""
    fig = make_subplots(rows=1, cols=2,
                        subplot_titles=("Open Interest por Strike", "Volumen por Strike"),
                        horizontal_spacing=0.10)

    for metric, col in [("OI", 1), ("Volume", 2)]:
        show_legend = (col == 1)
        for df, label, color in [
            (calls_df, "Call", "rgba(33,150,243,0.65)"),
            (puts_df,  "Put",  "rgba(244,67,54,0.65)"),
        ]:
            if df.empty or metric not in df.columns:
                continue
            d = df.sort_values("Strike")
            fig.add_trace(
                go.Bar(x=d["Strike"], y=d[metric],
                       name=label, marker_color=color,
                       showlegend=show_legend, legendgroup=label),
                row=1, col=col,
            )
        _add_spot_line(fig, spot, row=1, col=col)

    fig.update_layout(height=360, barmode="overlay", **_BASE_LAYOUT)
    fig.update_xaxes(**_axis_style())
    fig.update_yaxes(**_axis_style())
    return fig


def plot_iv_surface(calls_df: pd.DataFrame, puts_df: pd.DataFrame):
    """IV by Strike coloured by DTE — useful for smiles across expirations."""
    frames = []
    for df, label, color in [
        (calls_df, "Calls", _CALL_COLOR),
        (puts_df,  "Puts",  _PUT_COLOR),
    ]:
        if df.empty or "IV%" not in df.columns:
            continue
        frames.append(
            go.Scatter(
                x=df["Strike"], y=df["IV%"],
                mode="markers",
                marker=dict(
                    size=7,
                    color=df["DTE"] if "DTE" in df.columns else 0,
                    colorscale="Viridis",
                    showscale=(label == "Calls"),
                    colorbar=dict(title="DTE", thickness=12) if label == "Calls" else None,
                    opacity=0.8,
                ),
                name=label,
            )
        )

    fig = go.Figure(data=frames)
    fig.update_layout(
        height=380,
        xaxis_title="Strike",
        yaxis_title="IV (%)",
        **_BASE_LAYOUT,
    )
    fig.update_xaxes(**_axis_style())
    fig.update_yaxes(**_axis_style())
    return fig


def plot_delta_exposure(calls_df: pd.DataFrame, puts_df: pd.DataFrame):
    """
    Dealer Delta Exposure (GEX proxy): OI × Delta × 100 per strike.
    Positive = calls dominate, negative = puts dominate.
    """
    if calls_df.empty or puts_df.empty:
        return None
    if not {"OI", "Delta"}.issubset(calls_df.columns):
        return None

    c = calls_df.copy()
    p = puts_df.copy()
    c["DDE"] =  c["OI"] * c["Delta"] * 100
    p["DDE"] = -p["OI"] * p["Delta"].abs() * 100

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=c["Strike"], y=c["DDE"],
        name="Call exposure", marker_color="rgba(33,150,243,0.7)"
    ))
    fig.add_trace(go.Bar(
        x=p["Strike"], y=p["DDE"],
        name="Put exposure", marker_color="rgba(244,67,54,0.7)"
    ))
    fig.update_layout(
        height=340, barmode="relative",
        xaxis_title="Strike", yaxis_title="Delta Exposure (OI × Δ × 100)",
        **_BASE_LAYOUT,
    )
    fig.update_xaxes(**_axis_style())
    fig.update_yaxes(**_axis_style(), zeroline=True,
                     zerolinecolor="rgba(128,128,128,0.4)", zerolinewidth=1)
    return fig


# ─── Style helpers ────────────────────────────────────────────────────────────
def style_calls(df: pd.DataFrame):
    def row_color(row):
        itm = row.get("ITM", False)
        color = "background-color: rgba(33,150,243,0.12)" if itm else ""
        return [color] * len(row)
    return df.style.apply(row_color, axis=1)


def style_puts(df: pd.DataFrame):
    def row_color(row):
        itm = row.get("ITM", False)
        color = "background-color: rgba(244,67,54,0.12)" if itm else ""
        return [color] * len(row)
    return df.style.apply(row_color, axis=1)


# ─── Main ─────────────────────────────────────────────────────────────────────
def main():
    # Header
    st.markdown("## 📊 Options Chain Analyzer")
    st.caption("Charles Schwab API · Greeks en tiempo real · Powered by Schwabdev")

    # ── Sidebar ──
    with st.sidebar:
        st.header("⚙️ Parámetros")

        symbol = st.text_input("Símbolo", value="AAPL", max_chars=10).upper().strip()

        contract_type = st.selectbox(
            "Tipo de contrato",
            options=["ALL", "CALL", "PUT"],
            index=0,
        )

        strike_count = st.slider(
            "Número de strikes (cada lado)",
            min_value=5, max_value=60, value=20, step=5,
        )

        today = datetime.date.today()
        col_a, col_b = st.columns(2)
        from_date = col_a.date_input("Desde", value=today)
        to_date   = col_b.date_input("Hasta", value=today + datetime.timedelta(days=90))

        fetch_btn = st.button("🔄 Cargar cadena", type="primary", use_container_width=True)

        st.divider()
        st.info(
            "**Primera vez:**\n"
            "Al hacer clic se abrirá el navegador para autenticar con tu cuenta Schwab. "
            "Es un proceso de un solo uso."
        )

    # ── Fetch ──
    trigger = fetch_btn or ("chain_data" not in st.session_state)

    if trigger and symbol:
        with st.spinner(f"Cargando opciones de **{symbol}**..."):
            data, error = fetch_option_chain(
                symbol,
                contract_type,
                strike_count,
                from_date.strftime("%Y-%m-%d"),
                to_date.strftime("%Y-%m-%d"),
            )
        if error:
            st.error(f"❌ {error}")
            st.stop()
        if not data or data.get("status") == "FAILED":
            st.warning(
                f"⚠️ No se encontraron opciones para **{symbol}** en ese rango de fechas. "
                "Intenta ampliar las fechas o verifica el símbolo."
            )
            st.stop()

        st.session_state.chain_data = data
        st.session_state.symbol     = symbol

    if "chain_data" not in st.session_state:
        st.info("👈 Ingresa un símbolo en la barra lateral y presiona **Cargar cadena**.")
        return

    # ── Parse ──
    data                           = st.session_state.chain_data
    calls_raw, puts_raw, underlying = parse_option_chain(data)
    sym                            = st.session_state.symbol

    if calls_raw.empty and puts_raw.empty:
        st.warning("No se encontraron contratos para este símbolo y rango.")
        return

    # ── Expiration selector ──
    all_exps = sorted(
        set(
            (calls_raw["expiration_date"].tolist() if not calls_raw.empty else [])
            + (puts_raw["expiration_date"].tolist() if not puts_raw.empty else [])
        )
    )

    col_sym, col_exp, col_spacer = st.columns([1, 2, 4])
    with col_sym:
        st.markdown(f"### {sym}")
    with col_exp:
        selected_exp = st.selectbox("Expiración", options=all_exps, label_visibility="collapsed")

    # Filter by selected expiration
    def filter_exp(df):
        if df.empty or "expiration_date" not in df.columns:
            return df
        return df[df["expiration_date"] == selected_exp]

    calls_df = clean_df(filter_exp(calls_raw))
    puts_df  = clean_df(filter_exp(puts_raw))

    # Spot price
    spot = float(
        underlying.get("mark") or underlying.get("last") or
        underlying.get("close") or 0
    )

    # ── Metric Cards ──
    dte_val   = int(calls_df["DTE"].iloc[0]) if not calls_df.empty and "DTE" in calls_df.columns else 0
    atm_iv    = get_atm_iv(calls_df, spot)
    pcr       = calc_pcr(calls_df, puts_df)
    max_pain  = calc_max_pain(calls_df, puts_df)
    bid_ask   = underlying.get("bid", 0), underlying.get("ask", 0)
    spread    = round(bid_ask[1] - bid_ask[0], 2) if all(bid_ask) else None

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Precio",     f"${spot:.2f}")
    c2.metric("Bid / Ask",  f"${bid_ask[0]:.2f} / ${bid_ask[1]:.2f}" if all(bid_ask) else "—")
    c3.metric("DTE",        f"{dte_val} días")
    c4.metric("ATM IV",     f"{atm_iv:.1f}%" if atm_iv else "—")
    c5.metric("P/C Ratio",  f"{pcr:.2f}"     if pcr     else "—")
    c6.metric("Max Pain",   f"${max_pain:.0f}" if max_pain else "—")

    st.divider()

    # ── Options Chain Table ──
    st.subheader("📋 Cadena de Opciones")

    DISPLAY_COLS = [
        "Strike", "Bid", "Ask", "Mark", "Volume", "OI",
        "IV%", "Delta", "Gamma", "Theta", "Vega", "ITM",
    ]

    tab_calls, tab_puts, tab_both = st.tabs(["📈 Calls", "📉 Puts", "🔄 Ambas"])

    def show_table(df, style_fn, height=420):
        if df.empty:
            st.info("Sin datos para esta selección.")
            return
        cols = [c for c in DISPLAY_COLS if c in df.columns]
        st.dataframe(
            style_fn(df[cols].sort_values("Strike")),
            use_container_width=True,
            height=height,
        )

    with tab_calls:
        show_table(calls_df, style_calls)

    with tab_puts:
        show_table(puts_df, style_puts)

    with tab_both:
        bc, bp = st.columns(2)
        with bc:
            st.caption("**CALLS**")
            show_table(calls_df, style_calls, height=400)
        with bp:
            st.caption("**PUTS**")
            show_table(puts_df, style_puts, height=400)

    st.divider()

    # ── Greeks Charts ──
    st.subheader("📐 Greeks por Strike")
    calls_s = calls_df.sort_values("Strike") if not calls_df.empty else pd.DataFrame()
    puts_s  = puts_df.sort_values("Strike")  if not puts_df.empty  else pd.DataFrame()

    st.plotly_chart(plot_greeks(calls_s, puts_s, spot), use_container_width=True)

    # ── OI & Volume ──
    st.divider()
    st.subheader("📊 Open Interest y Volumen")
    st.plotly_chart(plot_oi_volume(calls_s, puts_s, spot), use_container_width=True)

    # ── IV Surface ──
    st.divider()
    st.subheader("🌊 Superficie de Volatilidad Implícita")
    st.caption("Cada punto = un contrato. Color = DTE (más oscuro = más tiempo).")
    # Use all expirations for this chart (not filtered by single expiration)
    all_calls = clean_df(calls_raw)
    all_puts  = clean_df(puts_raw)
    st.plotly_chart(plot_iv_surface(all_calls, all_puts), use_container_width=True)

    # ── Delta Exposure ──
    st.divider()
    st.subheader("⚡ Delta Exposure por Strike")
    st.caption("Proxy de GEX (Gamma Exposure). Positivo = calls dominan, negativo = puts dominan.")
    fig_dde = plot_delta_exposure(calls_s, puts_s)
    if fig_dde:
        st.plotly_chart(fig_dde, use_container_width=True)
    else:
        st.info("Necesitas datos de OI y Delta para mostrar este gráfico.")

    # ── Footer ──
    st.divider()
    st.caption(
        f"Última actualización: {datetime.datetime.now().strftime('%H:%M:%S')} · "
        "Datos provistos por Charles Schwab API. No constituye asesoramiento financiero."
    )


if __name__ == "__main__":
    main()
