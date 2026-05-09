"""
Product Analytics Dashboard — Streamlit.
Shopify-Admin / Stripe-inspired aesthetic: Inter font, #2563eb accent,
white cards on off-white canvas, pill tabs, custom insight callouts.
"""
from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from sqlalchemy import create_engine, text

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Product Analytics — REES46",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Design system ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

/* ── Global ── */
html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif !important;
}
.stApp { background-color: #fafbfc; }

/* ── Hide Streamlit chrome ── */
#MainMenu, footer, header { visibility: hidden; }
[data-testid="stToolbar"]      { display: none !important; }
[data-testid="stDecoration"]   { display: none !important; }
[data-testid="stStatusWidget"] { display: none !important; }

/* ── Canvas padding ── */
.block-container {
    padding-top: 2rem;
    padding-bottom: 3rem;
    max-width: 1280px;
}

/* ═══ KPI card ═══ */
.kpi-card {
    background: #ffffff;
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    padding: 1.25rem 1.5rem;
    height: 100%;
    transition: box-shadow 0.2s ease, transform 0.15s ease;
}
.kpi-card:hover {
    box-shadow: 0 4px 16px rgba(0,0,0,0.08);
    transform: translateY(-1px);
}
.kpi-label {
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: #64748b;
    margin: 0 0 8px 0;
}
.kpi-value {
    font-size: 30px;
    font-weight: 700;
    color: #0f172a;
    line-height: 1;
    margin: 0 0 6px 0;
    font-variant-numeric: tabular-nums;
}
.kpi-sub { font-size: 13px; color: #64748b; margin: 0; }
.badge-gray {
    display: inline-block;
    background: #f1f5f9; color: #64748b;
    font-size: 11px; font-weight: 500;
    padding: 2px 8px; border-radius: 9999px;
}

/* ═══ Section header ═══ */
.sec-head { font-size: 18px; font-weight: 600; color: #0f172a; margin: 0 0 2px 0; }
.sec-sub  { font-size: 13px; font-weight: 400; color: #64748b; margin: 0 0 1.25rem 0; }

/* ═══ Pill tab nav ═══ */
.stTabs [data-baseweb="tab-list"] {
    gap: 2px;
    background: #f1f5f9;
    padding: 3px;
    border-radius: 8px;
    border-bottom: none !important;
    width: fit-content;
    margin-bottom: 1.5rem;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 6px !important;
    padding: 6px 18px !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    color: #64748b !important;
    background: transparent !important;
    border: none !important;
    transition: color 0.15s;
}
.stTabs [aria-selected="true"] {
    background: #ffffff !important;
    color: #0f172a !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.10), 0 1px 2px rgba(0,0,0,0.06) !important;
}
.stTabs [data-baseweb="tab-highlight"],
.stTabs [data-baseweb="tab-border"] { display: none !important; }

/* ═══ Insight callout ═══ */
.callout {
    background: #eff6ff;
    border-left: 4px solid #2563eb;
    border-radius: 0 8px 8px 0;
    padding: 0.875rem 1.125rem;
    margin: 1rem 0;
}
.callout-head { margin: 0 0 4px 0; font-size: 13px; font-weight: 600; color: #1e40af; }
.callout-body { margin: 0; font-size: 13px; color: #374151; line-height: 1.6; }

/* ═══ Inline stat row ═══ */
.stat-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 10px 0;
    border-bottom: 1px solid #f1f5f9;
}
.stat-row:last-child { border-bottom: none; }
.stat-label { font-size: 13px; color: #64748b; }
.stat-value { font-size: 15px; font-weight: 600; color: #2563eb; }
.stat-value-dark { font-size: 15px; font-weight: 700; color: #0f172a; }

/* ═══ Container borders ═══ */
[data-testid="stVerticalBlockBorderWrapper"] {
    border-radius: 8px !important;
    border-color: #e5e7eb !important;
}
[data-testid="stExpander"] {
    border: 1px solid #e5e7eb !important;
    border-radius: 8px !important;
}

/* ═══ Footer ═══ */
.footer {
    text-align: center;
    font-size: 11px;
    color: #94a3b8;
    padding: 2rem 0 0;
    border-top: 1px solid #e5e7eb;
    margin-top: 2rem;
}
</style>
""", unsafe_allow_html=True)

# ── Data source ───────────────────────────────────────────────────────────────
# When POSTGRES_HOST is set (Docker / local dev) queries run against the live DB.
# On Streamlit Cloud (no DB), the app falls back to parquet snapshots in data/.
USE_LIVE_DB = bool(os.getenv("POSTGRES_HOST"))
DATA_DIR    = Path(__file__).parent / "data"

DATABASE_URL = (
    f"postgresql+psycopg2://"
    f"{os.getenv('POSTGRES_USER',     'analytics_user')}:"
    f"{os.getenv('POSTGRES_PASSWORD', 'analytics_pw')}@"
    f"{os.getenv('POSTGRES_HOST',     'localhost')}:"
    f"{os.getenv('POSTGRES_PORT',     '5433')}/"
    f"{os.getenv('POSTGRES_DB',       'analytics')}"
)
STAGING, INTERMEDIATE, MARTS = "staging", "intermediate", "marts"
ACCENT = "#2563eb"


@st.cache_resource
def get_engine():
    return create_engine(DATABASE_URL, pool_pre_ping=True)


@st.cache_data(ttl=600)
def q(sql: str) -> pd.DataFrame:
    return pd.read_sql(text(sql), get_engine())


def load(name: str, sql: str) -> pd.DataFrame:
    """Query live DB or fall back to parquet snapshot."""
    if USE_LIVE_DB:
        return q(sql)
    path = DATA_DIR / f"{name}.parquet"
    if not path.exists():
        st.error(f"Parquet snapshot not found: {path.name}. Run dashboard/data_export.py first.")
        st.stop()
    return pd.read_parquet(path)


# ── Shared Plotly theme ───────────────────────────────────────────────────────
_BASE = dict(
    plot_bgcolor="white",
    paper_bgcolor="white",
    font=dict(family="Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif",
              size=12, color="#475569"),
    margin=dict(l=10, r=10, t=10, b=10),
    hoverlabel=dict(bgcolor="white", bordercolor="#e5e7eb", font_size=12,
                    font_family="Inter, -apple-system, system-ui, sans-serif"),
    legend=dict(bgcolor="white", bordercolor="#e5e7eb", borderwidth=1,
                font=dict(size=11)),
)
_AXES = dict(
    xaxis=dict(showgrid=False,  linecolor="#e5e7eb", tickfont=dict(size=11)),
    yaxis=dict(gridcolor="#f1f5f9", linecolor="#e5e7eb", zeroline=False,
               tickfont=dict(size=11)),
)


def theme(fig, height: int = 400, **extra) -> go.Figure:
    """Apply brand theme to a Plotly figure; extra kwargs are merged in."""
    fig.update_layout(**_BASE, height=height)
    fig.update_layout(**_AXES)
    if extra:
        fig.update_layout(**extra)
    return fig


# ── UI helpers ────────────────────────────────────────────────────────────────
def callout(heading: str, body: str) -> None:
    st.markdown(
        f'<div class="callout">'
        f'<p class="callout-head">{heading}</p>'
        f'<p class="callout-body">{body}</p>'
        f'</div>',
        unsafe_allow_html=True,
    )


def chart_label(label: str, sub: str = "") -> None:
    st.markdown(
        f'<p style="font-size:18px;font-weight:600;color:#0f172a;margin:0 0 2px 0;">{label}</p>'
        + (f'<p style="font-size:13px;font-weight:400;color:#64748b;margin:0 0 0.75rem 0;">{sub}</p>'
           if sub else '<div style="margin-bottom:0.75rem;"></div>'),
        unsafe_allow_html=True,
    )


def fmt_money(n: float) -> str:
    if n >= 1_000_000:
        return f"${n / 1_000_000:.2f}M"
    if n >= 1_000:
        return f"${n / 1_000:.1f}K"
    return f"${n:,.0f}"


# ══════════════════════════════════════════════════════════════════════════════
# PAGE HEADER
# ══════════════════════════════════════════════════════════════════════════════
_mode_badge = (
    '<span style="background:#dcfce7;color:#166534;font-size:11px;font-weight:600;'
    'padding:2px 8px;border-radius:9999px;letter-spacing:0.04em;">Live DB</span>'
    if USE_LIVE_DB else
    '<span style="background:#f1f5f9;color:#64748b;font-size:11px;font-weight:600;'
    'padding:2px 8px;border-radius:9999px;letter-spacing:0.04em;">Demo mode</span>'
)
st.markdown(
    '<p style="font-size:2.25rem;font-weight:700;color:#0f172a;line-height:1.1;'
    'letter-spacing:-0.02em;margin:0 0 4px 0;">Product Analytics</p>'
    f'<p style="font-size:14px;font-weight:400;color:#64748b;margin:0 0 1.75rem 0;">'
    f'REES46 eCommerce &nbsp;·&nbsp; November 2019 &nbsp;·&nbsp; 5% user sample'
    f'&nbsp;&nbsp;{_mode_badge}'
    f'</p>',
    unsafe_allow_html=True,
)

# ── KPI data ──────────────────────────────────────────────────────────────────
kpi = load("kpi_summary", f"""
    SELECT
        COUNT(DISTINCT user_id)                                          AS users,
        COUNT(DISTINCT session_id)                                       AS sessions,
        COUNT(DISTINCT CASE WHEN event_type='purchase' THEN user_id END) AS buyers,
        COALESCE(SUM(CASE WHEN event_type='purchase' THEN price END), 0) AS gmv,
        COUNT(*)                                                         AS events
    FROM {STAGING}.stg_events
""").iloc[0]

conv_rate = (kpi["buyers"] / kpi["users"]) * 100 if kpi["users"] else 0
arppu     = (kpi["gmv"]    / kpi["buyers"])        if kpi["buyers"] else 0

# ── KPI section header ────────────────────────────────────────────────────────
st.markdown('<p class="sec-head">Overview</p>', unsafe_allow_html=True)
st.markdown('<p class="sec-sub">Last 30 days · November 2019</p>', unsafe_allow_html=True)

# ── Five KPI cards ────────────────────────────────────────────────────────────
c1, c2, c3, c4, c5 = st.columns(5)

with c1:
    st.markdown(f"""
    <div class="kpi-card">
      <p class="kpi-label">Total Users</p>
      <p class="kpi-value">{int(kpi['users']):,}</p>
      <p class="kpi-sub">Unique visitors</p>
    </div>""", unsafe_allow_html=True)

with c2:
    st.markdown(f"""
    <div class="kpi-card">
      <p class="kpi-label">Sessions</p>
      <p class="kpi-value">{int(kpi['sessions']):,}</p>
      <p class="kpi-sub">Distinct sessions</p>
    </div>""", unsafe_allow_html=True)

with c3:
    st.markdown(f"""
    <div class="kpi-card">
      <p class="kpi-label">Paying Users</p>
      <p class="kpi-value">{int(kpi['buyers']):,}</p>
      <p class="kpi-sub">{conv_rate:.1f}% conversion rate</p>
    </div>""", unsafe_allow_html=True)

with c4:
    st.markdown(f"""
    <div class="kpi-card">
      <p class="kpi-label">Gross Revenue</p>
      <p class="kpi-value" title="${kpi['gmv']:,.0f}">{fmt_money(kpi['gmv'])}</p>
      <p class="kpi-sub">Total purchase value</p>
    </div>""", unsafe_allow_html=True)

with c5:
    st.markdown(f"""
    <div class="kpi-card">
      <p class="kpi-label">ARPPU</p>
      <p class="kpi-value">${arppu:,.0f}</p>
      <p class="kpi-sub">
        <span class="badge-gray">per paying user</span>
      </p>
    </div>""", unsafe_allow_html=True)

st.markdown("<div style='margin-top:2rem;'></div>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# TABS
# ══════════════════════════════════════════════════════════════════════════════
tab_funnel, tab_retention, tab_activity, tab_categories = st.tabs(
    ["Funnel", "Retention", "Daily activity", "Categories"]
)

# ─────────────────────────────────────────────────────────────────────────────
# FUNNEL
# ─────────────────────────────────────────────────────────────────────────────
with tab_funnel:
    funnel = load("funnel", f"""
        SELECT stage, stage_order, users, pct_of_top, pct_of_prev
        FROM {MARTS}.funnel ORDER BY stage_order
    """)

    col_chart, col_insight = st.columns([3, 2])

    with col_chart:
        chart_label("Purchase funnel", "View → Cart → Purchase")
        funnel_text = [
            f"{int(v):,}  ({p:.0%})"
            for v, p in zip(funnel["users"], funnel["pct_of_top"])
        ]
        fig = go.Figure(go.Funnel(
            y=funnel["stage"].str.title(),
            x=funnel["users"],
            text=funnel_text,
            textposition="inside",
            textinfo="text",
            marker={"color": ["#93c5fd", "#3b82f6", "#1d4ed8"]},
            connector={"line": {"color": "#e5e7eb", "dash": "solid", "width": 1}},
        ))
        theme(fig, height=380)
        st.plotly_chart(fig, use_container_width=True)

    with col_insight:
        v2c     = funnel.loc[funnel["stage"] == "cart",     "pct_of_prev"].iloc[0] * 100
        c2p     = funnel.loc[funnel["stage"] == "purchase", "pct_of_prev"].iloc[0] * 100
        overall = funnel.loc[funnel["stage"] == "purchase", "pct_of_top" ].iloc[0] * 100

        chart_label("Stage-by-stage conversion")
        st.markdown(f"""
        <div>
          <div class="stat-row">
            <span class="stat-label">View → Cart</span>
            <span class="stat-value">{v2c:.1f}%</span>
          </div>
          <div class="stat-row">
            <span class="stat-label">Cart → Purchase</span>
            <span class="stat-value">{c2p:.1f}%</span>
          </div>
          <div class="stat-row">
            <span class="stat-label" style="font-weight:600;color:#0f172a;">Overall</span>
            <span class="stat-value-dark">{overall:.1f}%</span>
          </div>
        </div>
        """, unsafe_allow_html=True)

        callout(
            "Where to optimise first",
            f"Cart → purchase converts at <strong>{c2p:.0f}%</strong> — users who "
            f"reach the cart are highly motivated. The bigger leak is upstream: only "
            f"<strong>{v2c:.0f}%</strong> of viewers add to cart. "
            f"Focus on product discovery and view → cart conversion.",
        )

    with st.expander("Underlying data"):
        st.dataframe(funnel, use_container_width=True, hide_index=True)

# ─────────────────────────────────────────────────────────────────────────────
# RETENTION
# ─────────────────────────────────────────────────────────────────────────────
with tab_retention:
    matrix = load("retention", f"""
        SELECT cohort_week, week_number, retention_rate, cohort_users
        FROM {MARTS}.retention
        ORDER BY cohort_week, week_number
    """)

    if matrix.empty:
        st.info("No retention data yet.")
    else:
        col_heat, col_curve = st.columns([3, 2])

        with col_heat:
            chart_label("Cohort heatmap", "Retention % by week since first event")
            pivot = matrix.pivot(
                index="cohort_week", columns="week_number", values="retention_rate"
            ) * 100
            fig = px.imshow(
                pivot, text_auto=".1f", aspect="auto",
                color_continuous_scale=[
                    [0.0, "#eff6ff"], [0.25, "#93c5fd"],
                    [0.6, "#2563eb"], [1.0,  "#1e3a8a"],
                ],
                labels=dict(x="Weeks since first event", y="Cohort week", color="Retention %"),
                zmin=0, zmax=100,
            )
            theme(fig, height=360, xaxis=dict(side="bottom", showgrid=False),
                  yaxis=dict(showgrid=False))
            fig.update_coloraxes(colorbar=dict(
                thickness=10, len=0.75, tickfont=dict(size=10, color="#64748b"),
                title=dict(text=""),
            ))
            st.plotly_chart(fig, use_container_width=True)

        with col_curve:
            chart_label("Average retention curve", "Mean across all cohorts")
            curve = matrix.groupby("week_number", as_index=False)["retention_rate"].mean()
            curve["retention_pct"] = curve["retention_rate"] * 100
            fig2 = go.Figure()
            fig2.add_trace(go.Scatter(
                x=curve["week_number"], y=curve["retention_pct"],
                mode="lines+markers",
                line=dict(color=ACCENT, width=2),
                marker=dict(color=ACCENT, size=6, line=dict(color="white", width=1.5)),
                fill="tozeroy", fillcolor="rgba(37,99,235,0.06)",
                hovertemplate="Week %{x}: %{y:.1f}%<extra></extra>",
            ))
            theme(fig2, height=360,
                  xaxis=dict(showgrid=False, linecolor="#e5e7eb",
                             title=dict(text="Week", font=dict(size=11)),
                             tickfont=dict(size=11)),
                  yaxis=dict(gridcolor="#f1f5f9", linecolor="#e5e7eb", zeroline=False,
                             title=dict(text="Retention %", font=dict(size=11)),
                             tickfont=dict(size=11)))
            st.plotly_chart(fig2, use_container_width=True)

        w1 = (curve.loc[curve["week_number"] == 1, "retention_pct"].iloc[0]
              if 1 in curve["week_number"].values else None)
        w2 = (curve.loc[curve["week_number"] == 2, "retention_pct"].iloc[0]
              if 2 in curve["week_number"].values else None)
        if w1 and w2:
            callout(
                "Week-1 retention plateau",
                f"Week-1 retention is <strong>{w1:.1f}%</strong>, week-2 is "
                f"<strong>{w2:.1f}%</strong> — only a "
                f"<strong>{w1-w2:.1f}pp drop</strong>. The curve flattens fast: once a "
                f"user returns, they tend to stay. "
                f"<strong>Week 1 is the critical engagement window.</strong>",
            )

# ─────────────────────────────────────────────────────────────────────────────
# DAILY ACTIVITY
# ─────────────────────────────────────────────────────────────────────────────
with tab_activity:
    daily = load("daily_activity", f"""
        SELECT DATE_TRUNC('day', event_at)::date AS day,
               COUNT(DISTINCT user_id)            AS dau,
               COUNT(DISTINCT CASE WHEN event_type='purchase' THEN user_id END) AS buyers,
               COUNT(*)                           AS events,
               COALESCE(SUM(CASE WHEN event_type='purchase' THEN price END), 0) AS gmv
        FROM {STAGING}.stg_events
        GROUP BY 1
        ORDER BY 1
    """)

    chart_label("Daily Active Users — November 2019", "Unique users per day")

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=daily["day"], y=daily["dau"], name="DAU",
        line=dict(color=ACCENT, width=1.5),
        fill="tozeroy", fillcolor="rgba(37,99,235,0.08)",
        hovertemplate="<b>%{x}</b><br>DAU: %{y:,}<extra></extra>",
    ))

    bf = pd.Timestamp("2019-11-29").date()
    if bf in daily["day"].values:
        bf_dau = daily.loc[daily["day"] == bf, "dau"].iloc[0]
        fig.add_annotation(
            x=bf, y=bf_dau, text="Black Friday",
            showarrow=True, arrowhead=2, arrowcolor="#d62728",
            ax=0, ay=-44,
            font=dict(color="#d62728", size=11, family="Inter, system-ui"),
            bgcolor="white", bordercolor="#e5e7eb", borderwidth=1, borderpad=4,
        )

    theme(fig, height=360,
          xaxis=dict(showgrid=False, linecolor="#e5e7eb", tickfont=dict(size=11)),
          yaxis=dict(gridcolor="#f1f5f9", linecolor="#e5e7eb", zeroline=False,
                     title=dict(text="Distinct users", font=dict(size=11)),
                     tickfont=dict(size=11)))
    st.plotly_chart(fig, use_container_width=True)

    peak_col, gmv_col, _pad = st.columns([1, 1, 3])
    peak_day     = daily.loc[daily["dau"].idxmax()]
    peak_gmv_day = daily.loc[daily["gmv"].idxmax()]

    with peak_col:
        st.markdown(f"""
        <div class="kpi-card">
          <p class="kpi-label">Peak DAU day</p>
          <p class="kpi-value" style="font-size:1.5rem;">{peak_day['day'].strftime('%b %d')}</p>
          <p class="kpi-sub">{int(peak_day['dau']):,} users</p>
        </div>""", unsafe_allow_html=True)

    with gmv_col:
        st.markdown(f"""
        <div class="kpi-card">
          <p class="kpi-label">Peak revenue day</p>
          <p class="kpi-value" style="font-size:1.5rem;">{peak_gmv_day['day'].strftime('%b %d')}</p>
          <p class="kpi-sub">${peak_gmv_day['gmv']:,.0f}</p>
        </div>""", unsafe_allow_html=True)

    st.markdown("<div style='margin-top:1rem;'></div>", unsafe_allow_html=True)
    with st.expander("Daily breakdown"):
        st.dataframe(daily, use_container_width=True, hide_index=True)

# ─────────────────────────────────────────────────────────────────────────────
# CATEGORIES
# ─────────────────────────────────────────────────────────────────────────────
with tab_categories:
    top = load("top_categories", f"""
        SELECT COALESCE(category_code, 'unknown') AS category,
               COUNT(*)                            AS purchases,
               SUM(price)                          AS revenue,
               COUNT(DISTINCT user_id)             AS buyers
        FROM {STAGING}.stg_events
        WHERE event_type = 'purchase'
        GROUP BY 1
        ORDER BY revenue DESC
        LIMIT 15
    """)
    top["aov"] = top["revenue"] / top["purchases"]

    chart_label("Top 15 categories by revenue", "Purchases · Nov 2019")

    fig = px.bar(
        top.iloc[::-1], y="category", x="revenue", orientation="h",
        text=top.iloc[::-1]["revenue"].apply(lambda v: f"${v/1_000:,.0f}k"),
        labels={"revenue": "Revenue (USD)", "category": ""},
        color_discrete_sequence=[ACCENT],
    )
    fig.update_traces(
        textposition="outside",
        textfont=dict(size=11, color="#475569", family="Inter, system-ui"),
        marker_color=ACCENT,
        marker_line_width=0,
    )
    theme(fig, height=540,
          xaxis=dict(showgrid=False, linecolor="#e5e7eb", tickfont=dict(size=11)),
          yaxis=dict(gridcolor=None, linecolor="rgba(0,0,0,0)", zeroline=False,
                     tickfont=dict(size=11)))
    st.plotly_chart(fig, use_container_width=True)

    st.dataframe(
        top[["category", "purchases", "buyers", "revenue", "aov"]]
          .style.format({
              "revenue":   "${:,.0f}",
              "aov":       "${:,.0f}",
              "purchases": "{:,}",
              "buyers":    "{:,}",
          }),
        use_container_width=True, hide_index=True,
    )

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown(
    f'<div class="footer">'
    f'Pipeline: CSV → Postgres → dbt → marts → Streamlit &nbsp;·&nbsp; '
    f'Generated {datetime.now():%Y-%m-%d %H:%M} &nbsp;·&nbsp; '
    f'Source: REES46 Marketing Platform via Kaggle'
    f'</div>',
    unsafe_allow_html=True,
)
