"""
2026 Senate Control Dashboard
=============================
Displays both Polymarket prediction markets (Democrat / Republican Senate control
after the 2026 midterms) side-by-side, plus live prices from Polymarket's API.

Run with:
    streamlit run senate_dashboard.py

Requires:
    pip install streamlit pandas altair
"""

import json
import urllib.request
from datetime import datetime, timezone

import altair as alt
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

# --------------------------------------------------------------------------- #
# Config
# --------------------------------------------------------------------------- #
st.set_page_config(
    page_title="2026 Senate Control — Polymarket",
    page_icon="🏛️",
    layout="wide",
)

EVENT_URL = "https://polymarket.com/event/which-party-will-win-the-senate-in-2026"

MARKETS = {
    "dem": {
        "label": "Democratic Party",
        "slug": "will-the-democratic-party-control-the-senate-after-the-2026-midterm-elections",
        "title": "Will the Democratic Party control the Senate after the 2026 Midterm elections?",
        "fallback": (74.0, 27.0),   # (Yes %, No %) — from the embed markup
        "color": "#2E6FE0",
    },
    "rep": {
        "label": "Republican Party",
        "slug": "will-the-republican-party-control-the-senate-after-the-2026-midterm-elections",
        "title": "Will the Republican Party control the Senate after the 2026 Midterm elections?",
        "fallback": (27.0, 74.0),
        "color": "#D63B3B",
    },
}

# --------------------------------------------------------------------------- #
# Data: live fetch from Polymarket's public Gamma API (falls back to static)
# --------------------------------------------------------------------------- #
@st.cache_data(ttl=60, show_spinner=False)
def fetch_prices(slug: str):
    """Return (yes_pct, no_pct, is_live). Falls back to (None, None, False)."""
    url = f"https://gamma-api.polymarket.com/markets?slug={slug}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "senate-dashboard/1.0"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.load(resp)

        market = data[0]
        prices = market.get("outcomePrices")
        if isinstance(prices, str):
            prices = json.loads(prices)

        yes, no = float(prices[0]) * 100, float(prices[1]) * 100
        return round(yes, 1), round(no, 1), True
    except Exception:
        return None, None, False


def get_market(key: str):
    m = MARKETS[key]
    yes, no, live = fetch_prices(m["slug"])
    if not live:
        yes, no = m["fallback"]
    return {**m, "yes": yes, "no": no, "live": live}


# --------------------------------------------------------------------------- #
# Embed helper
# --------------------------------------------------------------------------- #
def polymarket_embed(slug: str, title: str, height: int = 300, width: int = 400) -> str:
    src = (
        f"https://embed.polymarket.com/market?market={slug}"
        f"&theme=dark&liveactivity=true&height={height}"
    )
    return f"""
    <div style="display:flex;justify-content:center;">
      <iframe title="{title}" src="{src}"
              width="{width}" height="{height}" frameborder="0"
              allowtransparency="true"
              style="border-radius:14px;background:#0e1117;"></iframe>
    </div>
    """


# --------------------------------------------------------------------------- #
# Sidebar
# --------------------------------------------------------------------------- #
with st.sidebar:
    st.header("Controls")
    if st.button("🔄 Refresh data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.caption(
        "Live prices refresh automatically every 60 s via Polymarket's public "
        "Gamma API. If the API is unreachable, the last-known values from the "
        "embed markup are used."
    )
    st.divider()
    st.markdown(f"[View full event on Polymarket ↗]({EVENT_URL})")

# --------------------------------------------------------------------------- #
# Header
# --------------------------------------------------------------------------- #
st.title("🏛️ Senate Control after the 2026 Midterms")
st.caption(
    f"Prediction market dashboard · Polymarket · "
    f"updated {datetime.now(timezone.utc):%Y-%m-%d %H:%M UTC}"
)

dem = get_market("dem")
rep = get_market("rep")

# --------------------------------------------------------------------------- #
# Top KPIs
# --------------------------------------------------------------------------- #
c1, c2, c3, c4 = st.columns(4)
c1.metric("🔵 Democrats — Yes", f"{dem['yes']:.0f}%", help="Chance Dems control the Senate")
c2.metric("🔴 Republicans — Yes", f"{rep['yes']:.0f}%", help="Chance GOP controls the Senate")
c3.metric("Spread (D − R)", f"{dem['yes'] - rep['yes']:+.0f} pts")
status = "🟢 Live" if (dem["live"] and rep["live"]) else "🟡 Cached"
c4.metric("Data source", status)

st.divider()

# --------------------------------------------------------------------------- #
# Side-by-side embeds
# --------------------------------------------------------------------------- #
st.subheader("Live markets")
left, right = st.columns(2)

with left:
    st.markdown(f"#### 🔵 {dem['label']}")
    components.html(polymarket_embed(dem["slug"], dem["title"]), height=320)

with right:
    st.markdown(f"#### 🔴 {rep['label']}")
    components.html(polymarket_embed(rep["slug"], rep["title"]), height=320)

st.divider()

# --------------------------------------------------------------------------- #
# Comparison chart
# --------------------------------------------------------------------------- #
st.subheader("Probability comparison")

chart_df = pd.DataFrame(
    [
        {"Party": "Democrats", "Outcome": "Yes", "Probability": dem["yes"]},
        {"Party": "Democrats", "Outcome": "No", "Probability": dem["no"]},
        {"Party": "Republicans", "Outcome": "Yes", "Probability": rep["yes"]},
        {"Party": "Republicans", "Outcome": "No", "Probability": rep["no"]},
    ]
)

chart = (
    alt.Chart(chart_df)
    .mark_bar(cornerRadiusTopLeft=6, cornerRadiusTopRight=6)
    .encode(
        x=alt.X("Party:N", axis=alt.Axis(labelAngle=0, title=None)),
        xOffset="Outcome:N",
        y=alt.Y("Probability:Q", scale=alt.Scale(domain=[0, 100]), title="Probability (%)"),
        color=alt.Color(
            "Outcome:N",
            scale=alt.Scale(domain=["Yes", "No"], range=["#4C9AFF", "#3A3F4B"]),
            legend=alt.Legend(title=None, orient="top"),
        ),
        tooltip=["Party", "Outcome", alt.Tooltip("Probability:Q", format=".1f")],
    )
    .properties(height=340)
)

st.altair_chart(chart, use_container_width=True)

# --------------------------------------------------------------------------- #
# Raw table
# --------------------------------------------------------------------------- #
with st.expander("Raw data"):
    st.dataframe(
        chart_df.pivot(index="Party", columns="Outcome", values="Probability")
        .reset_index()
        .rename_axis(None, axis=1),
        hide_index=True,
        use_container_width=True,
    )
    st.caption(
        "Note: Polymarket probabilities can sum to slightly more than 100% "
        "because of the bid/ask spread."
    )