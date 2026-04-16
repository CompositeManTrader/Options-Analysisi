"""Sanity test for exposure math — isolated from Streamlit."""
import numpy as np
import pandas as pd
from scipy.stats import norm

# ── Replicate key math functions from app.py ──
def bs_d1(S, K, T, sigma, r):
    S = np.asarray(S, dtype=float); K = np.asarray(K, dtype=float)
    T = np.asarray(T, dtype=float); sigma = np.asarray(sigma, dtype=float)
    with np.errstate(divide="ignore", invalid="ignore"):
        d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    return np.where((T > 0) & (sigma > 0) & (S > 0) & (K > 0), d1, np.nan)

def bs_d2(d1, sigma, T):
    return d1 - np.asarray(sigma) * np.sqrt(np.asarray(T))

def bs_vanna_vec(S, K, T, sigma, r):
    d1 = bs_d1(S, K, T, sigma, r); d2 = bs_d2(d1, sigma, T)
    with np.errstate(divide="ignore", invalid="ignore"):
        vanna = -norm.pdf(d1) * d2 / np.asarray(sigma)
    return np.where(np.isfinite(vanna), vanna, 0.0)

def bs_charm_vec(S, K, T, sigma, r):
    d1 = bs_d1(S, K, T, sigma, r); d2 = bs_d2(d1, sigma, T)
    sigma = np.asarray(sigma); T = np.asarray(T)
    with np.errstate(divide="ignore", invalid="ignore"):
        num = -norm.pdf(d1) * (2 * r * T - d2 * sigma * np.sqrt(T))
        den = 2 * T * sigma * np.sqrt(T)
        charm_year = num / den
    charm_day = charm_year / 365.0
    return np.where(np.isfinite(charm_day), charm_day, 0.0)

# ── Scenario: SPY at $580 ──
S = 580.0
r = 0.045

# Scalar value test — ATM option, 30 DTE, 20% IV
K = 580.0
T = 30/365
iv = 0.20

d1_val = bs_d1(S, K, T, iv, r).item()
gamma_at_atm = norm.pdf(d1_val) / (S * iv * np.sqrt(T))
vanna_val = bs_vanna_vec(S, K, T, iv, r).item()
charm_val = bs_charm_vec(S, K, T, iv, r).item()

print("=" * 60)
print("Black-Scholes sanity — SPY ATM $580, 30 DTE, 20% IV")
print("=" * 60)
print(f"d1          = {d1_val:+.6f}   (typical ATM ~0.05-0.10)")
print(f"Gamma       = {gamma_at_atm:.6f}   (per share, dΔ/dS)")
print(f"Vanna       = {vanna_val:+.6f}   (dΔ/dσ per share)")
print(f"Charm/day   = {charm_val:+.6f}   (dΔ/dt per day)")
print()

# ── GEX on realistic chain ──
print("=" * 60)
print("SPY chain simulation — 11 strikes, 1000 OI each, DTE=30")
print("=" * 60)
strikes = np.array([560, 565, 570, 575, 578, 580, 582, 585, 590, 595, 600], dtype=float)
oi_calls = np.array([500, 800, 1200, 2000, 3500, 5000, 4000, 2500, 1500, 800, 400])
oi_puts  = np.array([400, 700, 1100, 2500, 3800, 5200, 3500, 2000, 1200, 700, 350])
T_arr = np.full_like(strikes, T)
iv_arr = np.full_like(strikes, iv)

d1 = bs_d1(S, strikes, T_arr, iv_arr, r)
gammas = norm.pdf(d1) / (S * iv_arr * np.sqrt(T_arr))

# GEX per strike (per 1% move, SqueezeMetrics convention)
SCALE_GEX = 100 * S**2 * 0.01
c_gex = gammas * oi_calls * SCALE_GEX * (+1)
p_gex = gammas * oi_puts  * SCALE_GEX * (-1)
net_gex = c_gex + p_gex

total_gex = net_gex.sum()
print(f"Total Net GEX     = ${total_gex/1e6:+,.1f}M (per 1% move)")
print(f"Total Call GEX    = ${c_gex.sum()/1e6:+,.1f}M")
print(f"Total Put GEX     = ${p_gex.sum()/1e6:+,.1f}M")
print()
print("Per-strike breakdown:")
df = pd.DataFrame({
    "Strike": strikes, "Gamma": gammas.round(5),
    "Call_OI": oi_calls, "Put_OI": oi_puts,
    "C_GEX_M": (c_gex/1e6).round(1),
    "P_GEX_M": (p_gex/1e6).round(1),
    "Net_GEX_M": (net_gex/1e6).round(1),
})
print(df.to_string(index=False))
print()

# VEX (per 1 vol point)
vannas = bs_vanna_vec(S, strikes, T_arr, iv_arr, r)
SCALE_VEX = 100 * S * 0.01
c_vex = vannas * oi_calls * SCALE_VEX * (+1)
p_vex = vannas * oi_puts  * SCALE_VEX * (-1)
net_vex = c_vex + p_vex
print(f"Total Net VEX     = ${net_vex.sum()/1e6:+,.2f}M (per +1 vol point)")

# CEX (per day)
charms = bs_charm_vec(S, strikes, T_arr, iv_arr, r)
SCALE_CEX = 100 * S
c_cex = charms * oi_calls * SCALE_CEX * (+1)
p_cex = charms * oi_puts  * SCALE_CEX * (-1)
net_cex = c_cex + p_cex
print(f"Total Net CEX     = ${net_cex.sum()/1e6:+,.2f}M (per 1 day decay)")
print()

print("=" * 60)
print("Comparison vs OLD app.py convention (no × 0.01)")
print("=" * 60)
old_scale = 100 * S**2  # missing 0.01
old_net = (gammas * oi_calls * old_scale * (+1) + gammas * oi_puts * old_scale * (-1)).sum()
print(f"OLD Net GEX       = ${old_net/1e9:+.2f}B   ← what your original code reports")
print(f"NEW Net GEX       = ${total_gex/1e9:+.3f}B  ← gexbot convention (per 1% move)")
print(f"Ratio             = {old_net/total_gex:.1f}x (= 1/0.01 = 100x)")
print()

print("=" * 60)
print("Unit sanity — what do these numbers MEAN?")
print("=" * 60)
print(f"Net GEX = ${total_gex/1e6:+.1f}M per 1%")
if total_gex > 0:
    print(f"  → Dealers net long-gamma. For every 1% rally, they must SELL ~${total_gex/1e6:.1f}M spot.")
    print(f"  → For every 1% drop, they must BUY ~${abs(total_gex)/1e6:.1f}M spot.")
    print(f"  → This is the STABILIZING flow — fades moves.")
else:
    print(f"  → Dealers net short-gamma. For every 1% rally, they must BUY ~${abs(total_gex)/1e6:.1f}M.")
    print(f"  → For every 1% drop, they must SELL ~${abs(total_gex)/1e6:.1f}M.")
    print(f"  → This is the DESTABILIZING flow — accelerates moves.")
