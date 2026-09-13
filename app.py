"""
Olist Retail Analytics Dashboard
─────────────────────────────────
Streamlit + SQLite + Plotly dashboard for the Brazilian E-Commerce dataset.
Run with:
    streamlit run app.py
"""

import sqlite3
from datetime import date, datetime

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import queries

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Olist Retail Analytics",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Plotly theme ─────────────────────────────────────────────────────────────
PLOTLY_TEMPLATE = "plotly_white"
PRIMARY_COLOR   = "#2563EB"   # blue
ACCENT_COLOR    = "#10B981"   # emerald

# ── DB connection (cached at session level) ───────────────────────────────────
@st.cache_resource
def get_connection():
    return sqlite3.connect("olist.db", check_same_thread=False)

conn = get_connection()

# ── Helper: inject filter clauses into SQL ────────────────────────────────────
def _in_clause(col: str, values: list[str]) -> str:
    if not values:
        return ""
    escaped = ", ".join(f"'{v}'" for v in values)
    return f"AND {col} IN ({escaped})"

def run_query(sql_template: str, params: dict, states=None, cats=None) -> pd.DataFrame:
    state_filter = _in_clause("c.customer_state", states) if states else ""
    cat_filter   = _in_clause("p.product_category_name", cats) if cats else ""
    sql = sql_template.format(state_filter=state_filter, cat_filter=cat_filter)
    return pd.read_sql_query(sql, conn, params=params)

def run_simple(sql_template: str, params: dict, states=None) -> pd.DataFrame:
    state_filter = _in_clause("c.customer_state", states) if states else ""
    sql = sql_template.format(state_filter=state_filter, cat_filter="")
    return pd.read_sql_query(sql, conn, params=params)

# ── Sidebar filters ───────────────────────────────────────────────────────────
with st.sidebar:
    st.title("🛒 Olist Analytics")
    st.markdown("---")

    # Date range
    st.subheader("📅 Date Range")
    min_date = date(2016, 9, 1)
    max_date = date(2018, 10, 31)
    date_range = st.date_input(
        "Order purchase date",
        value=(date(2017, 1, 1), max_date),
        min_value=min_date,
        max_value=max_date,
    )
    if len(date_range) == 2:
        start_date, end_date = str(date_range[0]), str(date_range[1])
    else:
        start_date, end_date = str(min_date), str(max_date)

    # State filter
    st.subheader("🗺️ Customer State")
    try:
        all_states = pd.read_sql_query(
            "SELECT DISTINCT customer_state FROM customers ORDER BY customer_state", conn
        )["customer_state"].tolist()
    except Exception:
        all_states = []
    
    select_all_states = st.checkbox("Include All States", value=True)
    if select_all_states:
        selected_states = []
        st.caption("Showing data for all 27 states.")
    else:
        selected_states = st.multiselect("Choose specific states", all_states, default=["SP", "RJ", "MG"])

    # Category filter
    st.subheader("🏷️ Product Category")
    try:
        all_cats = pd.read_sql_query(
            "SELECT DISTINCT product_category_name FROM products "
            "WHERE product_category_name IS NOT NULL ORDER BY product_category_name", conn
        )["product_category_name"].tolist()
    except Exception:
        all_cats = []
    
    select_all_cats = st.checkbox("Include All Categories", value=True)
    if select_all_cats:
        selected_cats = []
        st.caption("Showing data for all categories.")
    else:
        selected_cats = st.multiselect("Choose specific categories", all_cats, default=all_cats[:3] if all_cats else [])

    st.markdown("---")
    st.caption("Data: [Olist Brazilian E-Commerce](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce)")

# ── Shared params dict ────────────────────────────────────────────────────────
params = {"start_date": start_date, "end_date": end_date}

states_arg = selected_states if selected_states else None
cats_arg   = selected_cats   if selected_cats   else None

# ── Load KPIs (cached per filter combo) ──────────────────────────────────────
@st.cache_data(ttl=300)
def load_kpis(_params, _states, _cats):
    p = dict(_params)  # convert tuple-of-pairs back to dict for SQL binding
    kpi_sql = queries.KPIS.format(
        state_filter=_in_clause("c.customer_state", list(_states)),
        cat_filter=_in_clause("p.product_category_name", list(_cats)),
    )
    kpis = pd.read_sql_query(kpi_sql, conn, params=p).iloc[0]
    rev_sql = queries.AVG_REVIEW.format(
        state_filter=_in_clause("c.customer_state", list(_states)),
        cat_filter="",
    )
    avg_rev = pd.read_sql_query(rev_sql, conn, params=p).iloc[0]["avg_review_score"]
    rpt_sql = queries.CUSTOMER_REPEAT_RATE.format(state_filter="", cat_filter="")
    rpt     = pd.read_sql_query(rpt_sql, conn, params=p).iloc[0]
    return kpis, avg_rev, rpt

kpis, avg_review, repeat = load_kpis(
    tuple(sorted(params.items())),
    tuple(selected_states),
    tuple(selected_cats),
)

# ── Header + KPI row ─────────────────────────────────────────────────────────
st.title("🛒 Olist Retail Analytics Dashboard")
st.caption("SQL-driven insights from the Brazilian E-Commerce dataset · Filters applied from sidebar")

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("📦 Delivered Orders",  f"{int(kpis['total_orders']):,}")
c2.metric("💰 Total Revenue",     f"R\$ {kpis['total_revenue']:,.0f}")
c3.metric("🏷️ Avg. Item Price",   f"R\$ {kpis['avg_item_price']:,.2f}")
c4.metric("⭐ Avg. Review Score", f"{avg_review:.2f} / 5")
c5.metric("👥 Unique Customers",  f"{int(kpis['unique_customers']):,}")

st.markdown("---")

# ── Tabs ─────────────────────────────────────────────────────────────────────
tab_overview, tab_geo, tab_products, tab_logistics, tab_payments, tab_sellers = st.tabs([
    "📈 Overview",
    "🗺️ Geography",
    "🏷️ Products",
    "🚚 Logistics",
    "💳 Payments",
    "🏆 Sellers",
])

# ═════════════════════════════════════════════════════════════════════════════
# TAB 1 — OVERVIEW
# ═════════════════════════════════════════════════════════════════════════════
with tab_overview:
    @st.cache_data(ttl=300)
    def load_revenue(_params, _states, _cats):
        return run_query(queries.REVENUE_BY_MONTH, dict(_params), list(_states), list(_cats))

    rev_df = load_revenue(
        tuple(sorted(params.items())), tuple(selected_states), tuple(selected_cats)
    )

    if rev_df.empty:
        st.info("No data for the selected filters.")
    else:
        # Dual-axis: revenue (bar) + orders (line)
        fig = go.Figure()
        fig.add_bar(
            x=rev_df["month"], y=rev_df["revenue"],
            name="Revenue (R$)", marker_color=PRIMARY_COLOR, opacity=0.85,
        )
        fig.add_scatter(
            x=rev_df["month"], y=rev_df["num_orders"],
            name="# Orders", yaxis="y2",
            line=dict(color=ACCENT_COLOR, width=2.5), mode="lines+markers",
        )
        fig.update_layout(
            title="Monthly Revenue & Order Volume",
            template=PLOTLY_TEMPLATE,
            yaxis=dict(title="Revenue (R$)"),
            yaxis2=dict(title="# Orders", overlaying="y", side="right", showgrid=False),
            legend=dict(orientation="h", y=1.08),
            hovermode="x unified",
        )
        st.plotly_chart(fig, use_container_width=True)

    # Status breakdown (small, bottom of overview)
    @st.cache_data(ttl=300)
    def load_status(_params):
        sql = queries.ORDER_STATUS_BREAKDOWN.format(state_filter="", cat_filter="")
        return pd.read_sql_query(sql, conn, params=dict(_params))

    status_df = load_status(tuple(sorted(params.items())))
    fig_status = px.pie(
        status_df, names="order_status", values="num_orders",
        title="Order Status Breakdown",
        template=PLOTLY_TEMPLATE,
        color_discrete_sequence=px.colors.qualitative.Set2,
        hole=0.4,
    )
    fig_status.update_traces(textinfo="percent+label")
    col_a, col_b = st.columns([1, 2])
    col_a.plotly_chart(fig_status, use_container_width=True)
    col_b.subheader("Status Detail")
    col_b.dataframe(status_df, use_container_width=True, hide_index=True)

# ═════════════════════════════════════════════════════════════════════════════
# TAB 2 — GEOGRAPHY
with tab_geo:
    @st.cache_data(ttl=300)
    def load_state_rev(_params, _states, _cats):
        return run_query(queries.REVENUE_BY_STATE, dict(_params), list(_states), list(_cats))

    col_map_opt1, col_map_opt2 = st.columns([1, 1])
    with col_map_opt1:
        map_metric = st.radio(
            "Map Metric Display:",
            ["Total Revenue (R$)", "Order Count"],
            horizontal=True
        )
    with col_map_opt2:
        geo_category = st.selectbox(
            "Filter Map by Product Category:",
            ["All Product Categories"] + (all_cats if all_cats else []),
            index=0
        )

    # Use in-tab category if specified, otherwise fall back to sidebar filter
    active_cats = [geo_category] if geo_category != "All Product Categories" else selected_cats

    state_df = load_state_rev(tuple(sorted(params.items())), tuple(selected_states), tuple(active_cats))

    @st.cache_data
    def load_brazil_geojson():
        import json
        with open("brazil_states.geojson", encoding="utf-8") as f:
            return json.load(f)

    if not state_df.empty:
        brazil_geojson = load_brazil_geojson()
        
        color_col = "revenue" if "Revenue" in map_metric else "num_orders"
        color_title = "Revenue (R$)" if color_col == "revenue" else "Delivered Orders"
        subtitle = f" — Category: {geo_category}" if geo_category != "All Product Categories" else " — All Product Categories Combined"

        fig_map = px.choropleth(
            state_df,
            geojson=brazil_geojson,
            locations="state",
            featureidkey="properties.sigla",
            color=color_col,
            hover_name="state",
            hover_data={"revenue": ":,.2f", "num_orders": ":,", "num_customers": ":,", "state": False},
            color_continuous_scale="YlGnBu",
            title=f"Geographic Distribution — {color_title} by State{subtitle}",
            labels={color_col: color_title}
        )
        # Add crisp state borders so every state shape is clearly visible
        fig_map.update_traces(
            marker_line_width=1.2,
            marker_line_color="#475569"
        )
        fig_map.update_geos(fitbounds="locations", visible=False)
        fig_map.update_layout(
            template=PLOTLY_TEMPLATE,
            margin={"r": 0, "t": 40, "l": 0, "b": 0},
            height=520
        )
        st.plotly_chart(fig_map, use_container_width=True)
    else:
        st.info("No geographic data for the selected filters.")

    # Top cities table
    @st.cache_data(ttl=300)
    def load_cities(_params, _states, _cats):
        return run_query(queries.TOP_CITIES, dict(_params), list(_states), list(_cats))

    cities_df = load_cities(tuple(sorted(params.items())), tuple(selected_states), tuple(active_cats))
    st.subheader(f"🏙️ Top 20 Cities by Orders{subtitle if not state_df.empty else ''}")
    st.dataframe(cities_df, use_container_width=True, hide_index=True)

# ═════════════════════════════════════════════════════════════════════════════
# TAB 3 — PRODUCTS
# ═════════════════════════════════════════════════════════════════════════════
with tab_products:
    @st.cache_data(ttl=300)
    def load_categories(_params, _states, _cats):
        return run_query(queries.TOP_CATEGORIES, dict(_params), list(_states), list(_cats))

    @st.cache_data(ttl=300)
    def load_freight(_params, _states, _cats):
        return run_query(queries.FREIGHT_RATIO_BY_CATEGORY, dict(_params), list(_states), list(_cats))

    cat_df     = load_categories(tuple(sorted(params.items())), tuple(selected_states), tuple(selected_cats))
    freight_df = load_freight(tuple(sorted(params.items())), tuple(selected_states), tuple(selected_cats))

    col_l, col_r = st.columns(2)

    with col_l:
        st.subheader("Top Categories by Revenue")
        if not cat_df.empty:
            fig_cat = px.bar(
                cat_df.head(15), x="revenue", y="category", orientation="h",
                text="pct_of_total_revenue",
                labels={"revenue": "Revenue (R$)", "category": ""},
                template=PLOTLY_TEMPLATE, color="revenue",
                color_continuous_scale="Blues",
            )
            fig_cat.update_traces(texttemplate="%{text}%", textposition="outside")
            fig_cat.update_layout(yaxis={"categoryorder": "total ascending"}, coloraxis_showscale=False)
            st.plotly_chart(fig_cat, use_container_width=True)

        with st.expander("📋 Full category table (with window function running total)"):
            st.dataframe(cat_df, use_container_width=True, hide_index=True)

    with col_r:
        st.subheader("Freight Cost % by Category")
        if not freight_df.empty:
            fig_freight = px.bar(
                freight_df, x="freight_pct", y="category", orientation="h",
                labels={"freight_pct": "Freight as % of Item Price", "category": ""},
                template=PLOTLY_TEMPLATE, color="freight_pct",
                color_continuous_scale="OrRd",
            )
            fig_freight.update_layout(yaxis={"categoryorder": "total ascending"}, coloraxis_showscale=False)
            st.plotly_chart(fig_freight, use_container_width=True)
            st.caption("Categories with the highest shipping burden relative to product price.")

# ═════════════════════════════════════════════════════════════════════════════
# TAB 4 — LOGISTICS
# ═════════════════════════════════════════════════════════════════════════════
with tab_logistics:
    @st.cache_data(ttl=300)
    def load_delivery(_params, _states):
        return run_simple(queries.DELIVERY_TIME_BY_STATE, dict(_params), list(_states))

    @st.cache_data(ttl=300)
    def load_reviews(_params, _states):
        return run_simple(queries.REVIEWS_VS_DELIVERY, dict(_params), list(_states))

    delivery_df = load_delivery(tuple(sorted(params.items())), tuple(selected_states))
    reviews_df  = load_reviews(tuple(sorted(params.items())), tuple(selected_states))

    col_l, col_r = st.columns(2)

    with col_l:
        st.subheader("Avg. Delivery Time by State")
        if not delivery_df.empty:
            fig_del = px.bar(
                delivery_df, x="state", y="avg_delivery_days",
                error_y=None,
                labels={"state": "State", "avg_delivery_days": "Avg. Days"},
                template=PLOTLY_TEMPLATE,
                color="avg_delivery_days", color_continuous_scale="RdYlGn_r",
            )
            fig_del.update_layout(coloraxis_showscale=False)
            st.plotly_chart(fig_del, use_container_width=True)
            st.dataframe(delivery_df, use_container_width=True, hide_index=True)

    with col_r:
        st.subheader("Review Score vs. Delivery Time")
        if not reviews_df.empty:
            fig_rev = px.bar(
                reviews_df, x="review_score", y="avg_delivery_days",
                text="avg_delivery_days",
                labels={"review_score": "Review Score (1–5)", "avg_delivery_days": "Avg. Delivery Days"},
                template=PLOTLY_TEMPLATE,
                color="avg_delivery_days", color_continuous_scale="RdYlGn_r",
            )
            fig_rev.update_traces(texttemplate="%{text} days", textposition="outside")
            fig_rev.update_layout(coloraxis_showscale=False)
            st.plotly_chart(fig_rev, use_container_width=True)
            st.caption("⬇️ Lower review scores correlate with longer delivery times.")

# ═════════════════════════════════════════════════════════════════════════════
# TAB 5 — PAYMENTS
# ═════════════════════════════════════════════════════════════════════════════
with tab_payments:
    @st.cache_data(ttl=300)
    def load_payments(_params):
        sql = queries.PAYMENT_BREAKDOWN.format(state_filter="", cat_filter="")
        return pd.read_sql_query(sql, conn, params=dict(_params))

    pay_df = load_payments(tuple(sorted(params.items())))

    col_l, col_r = st.columns(2)

    with col_l:
        st.subheader("Payment Method Breakdown")
        if not pay_df.empty:
            fig_pay = px.pie(
                pay_df, names="payment_type", values="num_orders",
                template=PLOTLY_TEMPLATE,
                color_discrete_sequence=px.colors.qualitative.Pastel,
                hole=0.45,
            )
            fig_pay.update_traces(textinfo="percent+label")
            st.plotly_chart(fig_pay, use_container_width=True)

    with col_r:
        st.subheader("Total Value & Avg. Installments")
        if not pay_df.empty:
            fig_inst = px.bar(
                pay_df, x="payment_type", y="avg_installments",
                text="avg_installments",
                labels={"payment_type": "Payment Type", "avg_installments": "Avg. Installments"},
                template=PLOTLY_TEMPLATE, color="total_value",
                color_continuous_scale="Blues",
            )
            fig_inst.update_traces(texttemplate="%{text:.1f}", textposition="outside")
            fig_inst.update_layout(coloraxis_showscale=False)
            st.plotly_chart(fig_inst, use_container_width=True)

    st.subheader("Payment Detail Table")
    if not pay_df.empty:
        st.dataframe(pay_df, use_container_width=True, hide_index=True)

# ═════════════════════════════════════════════════════════════════════════════
# TAB 6 — SELLERS
# ═════════════════════════════════════════════════════════════════════════════
with tab_sellers:
    @st.cache_data(ttl=300)
    def load_sellers(_params, _states):
        sql = queries.SELLER_PERFORMANCE.format(
            state_filter=_in_clause("c.customer_state", list(_states)),
            cat_filter="",
        )
        return pd.read_sql_query(sql, conn, params=dict(_params))

    seller_df = load_sellers(tuple(sorted(params.items())), tuple(selected_states))

    st.subheader("🏆 Top 20 Sellers by Revenue")
    if not seller_df.empty:
        fig_sell = px.bar(
            seller_df, x="total_revenue", y="seller_id", orientation="h",
            color="seller_state",
            labels={"total_revenue": "Revenue (R$)", "seller_id": "Seller"},
            template=PLOTLY_TEMPLATE,
            color_discrete_sequence=px.colors.qualitative.Set3,
        )
        fig_sell.update_layout(yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(fig_sell, use_container_width=True)

        st.subheader("Seller Detail Table")
        st.dataframe(seller_df, use_container_width=True, hide_index=True)

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("---")
st.caption(
    f"Olist Brazilian E-Commerce Dataset · "
    f"Filters: {start_date} → {end_date} · "
    f"States: {', '.join(selected_states) if selected_states else 'All'} · "
    f"Categories: {', '.join(selected_cats) if selected_cats else 'All'}"
)
