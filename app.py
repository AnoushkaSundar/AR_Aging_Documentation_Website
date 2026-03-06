"""
app.py — AR Aging Interactive Dashboard
Streamlit + Supabase + Plotly
"""
import os
import io
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AR Aging Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    /* Import font */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    /* Background */
    .stApp { background: #0f1117; }

    /* Sidebar */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1a1f2e 0%, #161b27 100%);
        border-right: 1px solid #2d3348;
    }
    section[data-testid="stSidebar"] * { color: #e2e8f0 !important; }

    /* KPI cards */
    .kpi-card {
        background: linear-gradient(135deg, #1e2535 0%, #252d40 100%);
        border: 1px solid #2d3757;
        border-radius: 14px;
        padding: 22px 24px 18px;
        text-align: center;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
        box-shadow: 0 4px 20px rgba(0,0,0,0.3);
    }
    .kpi-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 8px 30px rgba(99,179,237,0.15);
    }
    .kpi-label {
        font-size: 11px;
        font-weight: 600;
        letter-spacing: 1.2px;
        text-transform: uppercase;
        color: #8899b3 !important;
        margin-bottom: 8px;
    }
    .kpi-value {
        font-size: 28px;
        font-weight: 700;
        color: #e2e8f0 !important;
        line-height: 1.1;
    }
    .kpi-sub {
        font-size: 12px;
        color: #6b7fa3 !important;
        margin-top: 6px;
    }
    .kpi-icon { font-size: 22px; margin-bottom: 8px; }

    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        background: #1a1f2e;
        border-radius: 10px;
        padding: 4px;
        gap: 4px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        color: #8899b3;
        font-weight: 500;
        padding: 8px 20px;
    }
    .stTabs [aria-selected="true"] {
        background: #3b82f6 !important;
        color: white !important;
    }

    /* Headers */
    h1, h2, h3 { color: #e2e8f0 !important; }
    h1 { font-weight: 700; font-size: 1.8rem !important; }

    /* Upload area */
    .upload-section {
        background: #1a1f2e;
        border: 1px dashed #3b4d6b;
        border-radius: 12px;
        padding: 18px;
        margin-bottom: 20px;
    }

    /* Section title */
    .section-title {
        font-size: 13px;
        font-weight: 600;
        letter-spacing: 0.8px;
        text-transform: uppercase;
        color: #4a90d9;
        margin: 20px 0 10px;
    }

    /* Success / warning badges */
    .badge-green { color: #68d391 !important; font-weight: 600; }
    .badge-yellow { color: #f6e05e !important; font-weight: 600; }
    .badge-red { color: #fc8181 !important; font-weight: 600; }

    /* DataFrame */
    .dataframe { color: #e2e8f0 !important; }

    /* Divider */
    hr { border-color: #2d3348 !important; }

    /* Hide Streamlit branding */
    #MainMenu, footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# ── Lazy Supabase init ─────────────────────────────────────────────────────────
@st.cache_resource(show_spinner=False)
def get_supabase():
    try:
        from config import supabase_client, TABLE_NAME, LOG_TABLE
        return supabase_client, TABLE_NAME, LOG_TABLE
    except EnvironmentError:
        return None, "ar_aging", "upload_log"
    except Exception:
        return None, "ar_aging", "upload_log"


# ── Data loading ───────────────────────────────────────────────────────────────
@st.cache_data(ttl=60, show_spinner=False)
def load_data(_client, table: str) -> pd.DataFrame:
    """Fetch all rows from Supabase, return as DataFrame."""
    try:
        resp = _client.table(table).select("*").execute()
        if resp.data:
            df = pd.DataFrame(resp.data)
            # Drop Supabase meta columns from display (but keep for filtering)
            meta = {"id", "_row_index", "_row_hash", "_uploaded_at"}
            return df, [c for c in df.columns if c not in meta]
        return pd.DataFrame(), []
    except Exception as e:
        st.error(f"Failed to load data: {e}")
        return pd.DataFrame(), []


@st.cache_data(ttl=60, show_spinner=False)
def load_logs(_client, log_table: str) -> pd.DataFrame:
    try:
        resp = _client.table(log_table).select("*").order("uploaded_at", desc=True).limit(30).execute()
        return pd.DataFrame(resp.data or [])
    except Exception:
        return pd.DataFrame()


# ── Formatting helpers ─────────────────────────────────────────────────────────
def fmt_currency(val):
    if val is None or (isinstance(val, float) and val != val):
        return "—"
    if abs(val) >= 1_00_00_000:
        return f"₹{val/1_00_00_000:.2f} Cr"
    if abs(val) >= 1_00_000:
        return f"₹{val/1_00_000:.2f} L"
    return f"₹{val:,.0f}"


def fmt_number(val):
    if val is None:
        return "—"
    return f"{val:,.0f}"


# ── Plotly theme ───────────────────────────────────────────────────────────────
CHART_COLORS = [
    "#3b82f6", "#8b5cf6", "#06b6d4", "#10b981",
    "#f59e0b", "#ef4444", "#ec4899", "#84cc16",
]
CHART_BG = "#1a1f2e"
GRID_COLOR = "#2d3348"
TEXT_COLOR = "#c7d3e8"

def plotly_layout(fig, title="", height=420):
    fig.update_layout(
        title=dict(text=title, font=dict(size=15, color=TEXT_COLOR), x=0.02),
        paper_bgcolor=CHART_BG,
        plot_bgcolor=CHART_BG,
        font=dict(color=TEXT_COLOR, family="Inter"),
        height=height,
        margin=dict(l=20, r=20, t=50, b=30),
        legend=dict(
            bgcolor="rgba(0,0,0,0)",
            bordercolor=GRID_COLOR,
            font=dict(color=TEXT_COLOR),
        ),
        xaxis=dict(gridcolor=GRID_COLOR, linecolor=GRID_COLOR, zerolinecolor=GRID_COLOR),
        yaxis=dict(gridcolor=GRID_COLOR, linecolor=GRID_COLOR, zerolinecolor=GRID_COLOR),
    )
    return fig


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN APP
# ═══════════════════════════════════════════════════════════════════════════════

# ── Header ─────────────────────────────────────────────────────────────────────
col_logo, col_title = st.columns([1, 8])
with col_title:
    st.markdown("# 📊 AR Aging Dashboard")
    st.markdown(
        "<p style='color:#6b7fa3;font-size:14px;margin-top:-10px;'>"
        "Accounts Receivable Analytics · Sandvik</p>",
        unsafe_allow_html=True,
    )

st.markdown("---")

# ── Supabase connection ────────────────────────────────────────────────────────
supabase_client, TABLE_NAME, LOG_TABLE = get_supabase()
connected = supabase_client is not None

# ── Setup banner (shown when not connected) ───────────────────────────────────
if not connected:
    st.markdown("""
    <div style="background:linear-gradient(135deg,#1e2535,#252d40);border:1px solid #3b4d6b;
    border-radius:16px;padding:32px 36px;margin-bottom:28px;">
        <h2 style="color:#63b3ed;margin:0 0 8px">🚀 One-time Setup Required</h2>
        <p style="color:#8899b3;margin:0 0 24px;font-size:14px;">
            Follow these 3 steps to connect your Supabase database, then reload the page.</p>
    </div>
    """, unsafe_allow_html=True)

    s1, s2, s3 = st.columns(3)
    with s1:
        st.markdown("""
        <div class="kpi-card" style="text-align:left;padding:20px;">
            <div style="font-size:24px;margin-bottom:8px">1️⃣</div>
            <div style="font-weight:700;color:#e2e8f0;margin-bottom:6px">Run the SQL Schema</div>
            <div style="color:#8899b3;font-size:13px">Open <b>Supabase → SQL Editor</b>, paste the contents of <code>schema.sql</code> and click <b>Run</b>.</div>
        </div>""", unsafe_allow_html=True)
    with s2:
        st.markdown("""
        <div class="kpi-card" style="text-align:left;padding:20px;">
            <div style="font-size:24px;margin-bottom:8px">2️⃣</div>
            <div style="font-weight:700;color:#e2e8f0;margin-bottom:6px">Create your .env file</div>
            <div style="color:#8899b3;font-size:13px">Copy <code>.env.example</code> → <code>.env</code> and fill in your <b>SUPABASE_URL</b> and <b>SUPABASE_KEY</b> from Supabase → Settings → API.</div>
        </div>""", unsafe_allow_html=True)
    with s3:
        st.markdown("""
        <div class="kpi-card" style="text-align:left;padding:20px;">
            <div style="font-size:24px;margin-bottom:8px">3️⃣</div>
            <div style="font-weight:700;color:#e2e8f0;margin-bottom:6px">Restart & Upload</div>
            <div style="color:#8899b3;font-size:13px">Restart the app, then drag your <b>AR Aging.xlsx</b> onto the sidebar uploader and click <b>Upload to Supabase</b>.</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    with st.expander("📋 View schema.sql (copy this into Supabase SQL Editor)", expanded=False):
        import pathlib
        sql_path = pathlib.Path(__file__).parent / "schema.sql"
        if sql_path.exists():
            st.code(sql_path.read_text(), language="sql")
        else:
            st.warning("schema.sql not found in app directory.")
    st.stop()


# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🔗 Data Source")

    if connected:
        st.success("✅ Supabase Connected", icon="🟢")
    else:
        st.error("⚠️ Supabase not configured — fill in .env file")

    st.markdown("---")
    st.markdown("### 📤 Upload Excel File")

    uploaded_file = st.file_uploader(
        "Drop AR Aging .xlsx here",
        type=["xlsx", "xls"],
        help="Headers should be on row 6 (standard Sandvik AR Aging format)",
    )

    if uploaded_file and connected:
        if st.button("⬆️ Upload to Supabase", use_container_width=True, type="primary"):
            with st.spinner("Processing & uploading…"):
                try:
                    from uploader import upload_excel
                    result = upload_excel(
                        uploaded_file,
                        supabase_client,
                        TABLE_NAME,
                        LOG_TABLE,
                        uploaded_file.name,
                    )
                    st.success(
                        f"✅ Done! **{result['added']}** new rows · "
                        f"**{result['unchanged']}** unchanged"
                    )
                    st.cache_data.clear()
                except Exception as e:
                    st.error(f"Upload failed: {e}")

    elif uploaded_file and not connected:
        st.warning("Configure Supabase credentials first.")

    st.markdown("---")

    # ── Load data for filters ────────────────────────────────────────────────
    if connected:
        with st.spinner("Loading data…"):
            df_full, display_cols = load_data(supabase_client, TABLE_NAME)
    else:
        df_full, display_cols = pd.DataFrame(), []

    df = df_full.copy() if not df_full.empty else pd.DataFrame()

    # ── Filters ──────────────────────────────────────────────────────────────
    st.markdown("### 🔍 Filters")

    # Primary filter columns (as specified by user)
    PRIMARY_FILTERS = {
        "source_file":      "Source File",
        "customer_name":    "Customer Name",
        "customer_number":  "Customer ID",
        "profit_center":    "Profit Center",
        "segment":          "Segment",
        "region":           "Region",
    }

    active_filters = {}

    for col_key, label in PRIMARY_FILTERS.items():
        # Try to find the column (exact or partial match)
        matched = None
        if not df.empty:
            for c in df.columns:
                if c == col_key or col_key.replace("_", " ") in c.replace("_", " "):
                    matched = c
                    break

        if matched and matched in df.columns:
            opts = sorted(df[matched].dropna().astype(str).unique().tolist())
            if opts:
                sel = st.multiselect(label, options=opts, key=f"filter_{col_key}")
                if sel:
                    active_filters[matched] = sel

    # ── Extra category expander ───────────────────────────────────────────────
    with st.expander("➕ Add more filter categories"):
        if not df.empty:
            categorical_cols = [
                c for c in display_cols
                if c not in PRIMARY_FILTERS
                and df[c].dtype == object
                and df[c].nunique() < 200
                and c not in {"_row_hash", "origacct", "dseq", "salesman"}
            ]
            for col_key in categorical_cols[:20]:
                label = col_key.replace("_", " ").title()
                opts = sorted(df[col_key].dropna().astype(str).unique().tolist())
                if opts:
                    sel = st.multiselect(label, options=opts, key=f"extra_{col_key}")
                    if sel:
                        active_filters[col_key] = sel
        else:
            st.info("Upload data first to see extra filter options.")

    # Apply all filters
    if not df.empty:
        for col, vals in active_filters.items():
            if col in df.columns:
                df = df[df[col].astype(str).isin(vals)]

    # Reset button
    if active_filters:
        if st.button("🔄 Clear All Filters", use_container_width=True):
            st.cache_data.clear()
            st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN CONTENT — Tabs
# ═══════════════════════════════════════════════════════════════════════════════

tab_overview, tab_charts, tab_table, tab_log = st.tabs([
    "📊 Overview", "📈 Charts", "📋 Data Table", "📁 Upload Log"
])

# ══════════════════════════════════════════════════════
# TAB 1 — OVERVIEW
# ══════════════════════════════════════════════════════
with tab_overview:

    if df.empty:
        st.info("📂 No data yet. Upload your Excel file from the sidebar.")
    else:
        # KPI calculations
        total_records = len(df)

        # Outstanding value
        ov_col = next((c for c in df.columns if "outstanding" in c), None)
        total_outstanding = df[ov_col].sum() if ov_col else 0

        # Overdue days
        od_col = next((c for c in df.columns if "overdue_days" in c), None)
        avg_overdue = df[od_col].mean() if od_col else 0
        count_overdue = int((df[od_col] > 0).sum()) if od_col else 0

        # Original / goods amount
        oa_col = next((c for c in df.columns if "original_amount" in c), None)
        total_original = df[oa_col].sum() if oa_col else 0

        # ── KPI Row 1 ─────────────────────────────────────────────────────────
        k1, k2, k3, k4 = st.columns(4)
        with k1:
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-icon">📋</div>
                <div class="kpi-label">Total Records</div>
                <div class="kpi-value">{fmt_number(total_records)}</div>
                <div class="kpi-sub">Active invoices / advances</div>
            </div>""", unsafe_allow_html=True)
        with k2:
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-icon">💰</div>
                <div class="kpi-label">Outstanding Value</div>
                <div class="kpi-value">{fmt_currency(total_outstanding)}</div>
                <div class="kpi-sub">Total AR outstanding</div>
            </div>""", unsafe_allow_html=True)
        with k3:
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-icon">⏰</div>
                <div class="kpi-label">Avg Overdue Days</div>
                <div class="kpi-value">{avg_overdue:.0f} days</div>
                <div class="kpi-sub">Across filtered records</div>
            </div>""", unsafe_allow_html=True)
        with k4:
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-icon">⚠️</div>
                <div class="kpi-label">Overdue Invoices</div>
                <div class="kpi-value">{fmt_number(count_overdue)}</div>
                <div class="kpi-sub">Records with overdue > 0 days</div>
            </div>""", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # ── KPI Row 2 ─────────────────────────────────────────────────────────
        k5, k6, k7, k8 = st.columns(4)

        # Unique customers
        cust_col = next((c for c in df.columns if "customer_name" in c), None)
        unique_customers = df[cust_col].nunique() if cust_col else 0

        # Unique regions
        reg_col = next((c for c in df.columns if c == "region"), None)
        unique_regions = df[reg_col].nunique() if reg_col else 0

        # High risk (>90 days overdue)
        high_risk = int((df[od_col] > 90).sum()) if od_col else 0

        # Currencies
        ccy_col = next((c for c in df.columns if c == "ccy"), None)
        currencies = ", ".join(df[ccy_col].dropna().unique()[:5]) if ccy_col else "—"

        with k5:
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-icon">👤</div>
                <div class="kpi-label">Unique Customers</div>
                <div class="kpi-value">{fmt_number(unique_customers)}</div>
                <div class="kpi-sub">Distinct customer names</div>
            </div>""", unsafe_allow_html=True)
        with k6:
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-icon">🌍</div>
                <div class="kpi-label">Regions Covered</div>
                <div class="kpi-value">{unique_regions}</div>
                <div class="kpi-sub">Active regions in filter</div>
            </div>""", unsafe_allow_html=True)
        with k7:
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-icon">🔴</div>
                <div class="kpi-label">High Risk (>90 days)</div>
                <div class="kpi-value">{fmt_number(high_risk)}</div>
                <div class="kpi-sub">Critically overdue invoices</div>
            </div>""", unsafe_allow_html=True)
        with k8:
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-icon">💱</div>
                <div class="kpi-label">Currency</div>
                <div class="kpi-value" style="font-size:18px;">{currencies}</div>
                <div class="kpi-sub">Transaction currencies</div>
            </div>""", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # ── Quick bucket breakdown ─────────────────────────────────────────────
        bucket_col = next((c for c in df.columns if c == "bucket"), None)
        if bucket_col:
            st.markdown("<div class='section-title'>Aging Bucket Breakdown</div>", unsafe_allow_html=True)
            bucket_summary = (
                df.groupby(bucket_col)[ov_col].sum()
                .reset_index()
                .rename(columns={bucket_col: "Bucket", ov_col: "Outstanding Value"})
                .sort_values("Bucket")
            ) if ov_col else None

            if bucket_summary is not None and not bucket_summary.empty:
                bc1, bc2 = st.columns([2, 1])
                with bc1:
                    fig_bucket = px.bar(
                        bucket_summary,
                        x="Bucket",
                        y="Outstanding Value",
                        color="Bucket",
                        color_discrete_sequence=CHART_COLORS,
                        text_auto=".2s",
                    )
                    fig_bucket = plotly_layout(fig_bucket, "Outstanding Value by Aging Bucket")
                    fig_bucket.update_traces(textfont_color=TEXT_COLOR)
                    st.plotly_chart(fig_bucket, use_container_width=True)
                with bc2:
                    st.dataframe(
                        bucket_summary.style.background_gradient(
                            subset=["Outstanding Value"], cmap="Blues"
                        ).format({"Outstanding Value": "{:,.0f}"}),
                        use_container_width=True,
                        height=300,
                    )


# ══════════════════════════════════════════════════════
# TAB 2 — CHARTS
# ══════════════════════════════════════════════════════
with tab_charts:

    if df.empty:
        st.info("📂 No data yet. Upload your Excel file from the sidebar.")
    else:
        ov_col = next((c for c in df.columns if "outstanding" in c), None)
        od_col = next((c for c in df.columns if "overdue_days" in c), None)
        cust_col = next((c for c in df.columns if "customer_name" in c), None)
        reg_col = next((c for c in df.columns if c == "region"), None)
        seg_col = next((c for c in df.columns if c == "segment" and "1" not in c), None)
        pc_col = next((c for c in df.columns if "profit_center" in c), None)
        bucket_col = next((c for c in df.columns if c == "bucket"), None)

        # ── Row 1: Region bar + Segment pie ──────────────────────────────────
        ch1, ch2 = st.columns(2)

        with ch1:
            if reg_col and ov_col:
                reg_data = (
                    df.groupby(reg_col)[ov_col].sum()
                    .reset_index()
                    .rename(columns={reg_col: "Region", ov_col: "Outstanding Value"})
                    .sort_values("Outstanding Value", ascending=False)
                )
                fig = px.bar(
                    reg_data, x="Region", y="Outstanding Value",
                    color="Region", color_discrete_sequence=CHART_COLORS,
                    text_auto=".2s",
                )
                fig = plotly_layout(fig, "📍 Outstanding Value by Region")
                fig.update_traces(textfont_color=TEXT_COLOR)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Region / Outstanding Value column not found.")

        with ch2:
            if seg_col and ov_col:
                seg_data = (
                    df.groupby(seg_col)[ov_col].sum()
                    .reset_index()
                    .rename(columns={seg_col: "Segment", ov_col: "Outstanding Value"})
                )
                fig = px.pie(
                    seg_data, names="Segment", values="Outstanding Value",
                    color_discrete_sequence=CHART_COLORS, hole=0.45,
                )
                fig = plotly_layout(fig, "🏷️ Segment Distribution (Outstanding Value)")
                fig.update_traces(
                    textposition="outside", textinfo="percent+label",
                    textfont_color=TEXT_COLOR,
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Segment / Outstanding Value column not found.")

        # ── Row 2: Top customers + Profit Center ─────────────────────────────
        ch3, ch4 = st.columns(2)

        with ch3:
            if cust_col and ov_col:
                top_cust = (
                    df.groupby(cust_col)[ov_col].sum()
                    .reset_index()
                    .rename(columns={cust_col: "Customer", ov_col: "Outstanding"})
                    .sort_values("Outstanding", ascending=False)
                    .head(15)
                )
                fig = px.bar(
                    top_cust, x="Outstanding", y="Customer",
                    orientation="h", color="Outstanding",
                    color_continuous_scale=["#1e3a5f", "#3b82f6", "#93c5fd"],
                    text_auto=".2s",
                )
                fig = plotly_layout(fig, "🏆 Top 15 Customers by Outstanding Value", height=480)
                fig.update_traces(textfont_color=TEXT_COLOR)
                fig.update_coloraxes(showscale=False)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Customer Name / Outstanding Value column not found.")

        with ch4:
            if pc_col and ov_col:
                pc_data = (
                    df.groupby(pc_col)[ov_col].sum()
                    .reset_index()
                    .rename(columns={pc_col: "Profit Center", ov_col: "Outstanding Value"})
                    .sort_values("Outstanding Value", ascending=False)
                    .head(15)
                )
                fig = px.bar(
                    pc_data, x="Outstanding Value", y="Profit Center",
                    orientation="h", color_discrete_sequence=["#8b5cf6"],
                    text_auto=".2s",
                )
                fig = plotly_layout(fig, "🏭 Outstanding Value by Profit Center", height=480)
                fig.update_traces(textfont_color=TEXT_COLOR)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Profit Center / Outstanding Value column not found.")

        st.markdown("---")

        # ── Row 3: Aging bucket stacked + Overdue scatter ─────────────────────
        ch5, ch6 = st.columns(2)

        with ch5:
            if bucket_col and seg_col and ov_col:
                pivot = (
                    df.groupby([seg_col, bucket_col])[ov_col].sum()
                    .reset_index()
                )
                fig = px.bar(
                    pivot, x=seg_col, y=ov_col, color=bucket_col,
                    barmode="stack",
                    color_discrete_sequence=CHART_COLORS,
                    labels={seg_col: "Segment", ov_col: "Outstanding Value"},
                )
                fig = plotly_layout(fig, "📅 Aging Buckets by Segment (Stacked)")
                st.plotly_chart(fig, use_container_width=True)
            elif bucket_col and ov_col:
                bd = (
                    df.groupby(bucket_col)[ov_col].sum()
                    .reset_index()
                    .sort_values("bucket")
                )
                fig = px.bar(bd, x=bucket_col, y=ov_col,
                             color_discrete_sequence=CHART_COLORS)
                fig = plotly_layout(fig, "📅 Outstanding by Aging Bucket")
                st.plotly_chart(fig, use_container_width=True)

        with ch6:
            if od_col and ov_col and cust_col:
                scatter_df = df[[cust_col, od_col, ov_col]].dropna().copy()
                scatter_df[ov_col] = pd.to_numeric(scatter_df[ov_col], errors="coerce")
                scatter_df[od_col] = pd.to_numeric(scatter_df[od_col], errors="coerce")
                scatter_df = scatter_df[scatter_df[od_col] > 0].head(500)
                if not scatter_df.empty:
                    fig = px.scatter(
                        scatter_df,
                        x=od_col, y=ov_col,
                        hover_name=cust_col,
                        color=ov_col,
                        color_continuous_scale=["#1e3a5f", "#3b82f6", "#ef4444"],
                        labels={od_col: "Overdue Days", ov_col: "Outstanding Value"},
                        size_max=15,
                    )
                    fig = plotly_layout(fig, "🔍 Overdue Days vs Outstanding Value")
                    st.plotly_chart(fig, use_container_width=True)

        # ── Row 4: Region × Segment heatmap ────────────────────────────────
        if reg_col and seg_col and ov_col:
            st.markdown("<div class='section-title'>Region × Segment Heatmap</div>",
                        unsafe_allow_html=True)
            heat_data = (
                df.groupby([reg_col, seg_col])[ov_col].sum()
                .unstack(fill_value=0)
            )
            fig_heat = px.imshow(
                heat_data.values,
                x=heat_data.columns.tolist(),
                y=heat_data.index.tolist(),
                color_continuous_scale="Blues",
                text_auto=".2s",
                labels=dict(x="Segment", y="Region", color="Outstanding"),
                aspect="auto",
            )
            fig_heat = plotly_layout(fig_heat, "🗺️ Outstanding Value Heatmap (Region × Segment)", height=380)
            fig_heat.update_traces(textfont_color="white")
            st.plotly_chart(fig_heat, use_container_width=True)


# ══════════════════════════════════════════════════════
# TAB 3 — DATA TABLE
# ══════════════════════════════════════════════════════
with tab_table:

    if df.empty:
        st.info("📂 No data yet. Upload your Excel file from the sidebar.")
    else:
        # Column selector
        all_display = [c for c in display_cols if c in df.columns]

        default_cols = [c for c in [
            "source_file", "customer_name", "customer_number", "profit_center", "segment",
            "region", "outstanding_value", "overdue_days", "bucket",
            "document_date", "pduedate", "payment_terms", "ccy", "original_amount",
        ] if c in all_display] or all_display[:12]

        with st.expander("🗂️ Choose columns to display", expanded=False):
            chosen_cols = st.multiselect(
                "Select columns",
                options=all_display,
                default=default_cols,
                key="col_picker",
            )
        if not chosen_cols:
            chosen_cols = default_cols

        # Quick search
        search = st.text_input("🔎 Search anywhere in table", placeholder="Type to filter rows…")
        view_df = df[chosen_cols].copy()
        if search:
            mask = view_df.astype(str).apply(lambda col: col.str.contains(search, case=False, na=False)).any(axis=1)
            view_df = view_df[mask]

        st.markdown(
            f"<p style='color:#6b7fa3;font-size:13px;'>Showing "
            f"<b style='color:#e2e8f0'>{len(view_df):,}</b> rows · "
            f"<b style='color:#e2e8f0'>{len(chosen_cols)}</b> columns</p>",
            unsafe_allow_html=True,
        )

        st.dataframe(view_df, use_container_width=True, height=480)

        # CSV download
        csv = view_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="⬇️ Download as CSV",
            data=csv,
            file_name=f"ar_aging_export_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv",
            use_container_width=True,
        )

        # ── Summary pivot ──────────────────────────────────────────────────────
        st.markdown("---")
        st.markdown("<div class='section-title'>Pivot Summary</div>", unsafe_allow_html=True)

        group_opts = [c for c in [
            "region", "segment", "profit_center", "bucket", "customer_type",
            "pa_division", "dealer", "payment_terms",
        ] if c in df.columns]
        num_opts = [c for c in ["outstanding_value", "original_amount", "overdue_days"]
                    if c in df.columns]

        pc1, pc2, pc3 = st.columns(3)
        with pc1:
            piv_group = st.selectbox("Group by", group_opts, key="piv_group") if group_opts else None
        with pc2:
            piv_val = st.selectbox("Value", num_opts, key="piv_val") if num_opts else None
        with pc3:
            piv_agg = st.selectbox("Aggregation", ["Sum", "Mean", "Count", "Max"], key="piv_agg")

        if piv_group and piv_val:
            agg_map = {"Sum": "sum", "Mean": "mean", "Count": "count", "Max": "max"}
            pivot = (
                df.groupby(piv_group)[piv_val]
                .agg(agg_map[piv_agg])
                .reset_index()
                .rename(columns={piv_val: f"{piv_agg} of {piv_val}"})
                .sort_values(f"{piv_agg} of {piv_val}", ascending=False)
            )
            val_col_name = f"{piv_agg} of {piv_val}"
            st.dataframe(
                pivot.style.background_gradient(subset=[val_col_name], cmap="Blues")
                     .format({val_col_name: "{:,.2f}"}),
                use_container_width=True,
                height=350,
            )


# ══════════════════════════════════════════════════════
# TAB 4 — UPLOAD LOG
# ══════════════════════════════════════════════════════
with tab_log:

    if not connected:
        st.info("Configure Supabase credentials to see upload history.")
    else:
        logs = load_logs(supabase_client, LOG_TABLE)
        if logs.empty:
            st.info("No uploads recorded yet. Upload a file from the sidebar to get started.")
        else:
            st.markdown(f"**Last {len(logs)} upload sessions**")
            display_log = logs.copy()
            if "id" in display_log.columns:
                display_log.drop(columns=["id"], inplace=True)
            if "uploaded_at" in display_log.columns:
                display_log["uploaded_at"] = pd.to_datetime(
                    display_log["uploaded_at"]
                ).dt.strftime("%Y-%m-%d %H:%M UTC")
            st.dataframe(display_log, use_container_width=True, height=400)

            # Mini analytics
            if "rows_added" in logs.columns:
                total_uploaded = logs["rows_added"].sum()
                st.metric("Total rows uploaded across all sessions", f"{total_uploaded:,}")
