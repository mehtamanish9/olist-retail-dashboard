<div align="center">

# 🛒 Olist Brazilian E-Commerce Analytics Dashboard

An end-to-end retail analytics platform built with **Python**, **SQLite**, **Streamlit**, and **Plotly** to uncover business insights from 100,000+ real e-commerce transactions in Brazil.

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://share.streamlit.io)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Database: SQLite](https://img.shields.io/badge/Database-SQLite-003B57?logo=sqlite&logoColor=white)](https://www.sqlite.org/)

</div>

---

## 📌 Motivation & Problem Statement

E-commerce marketplaces face complex logistics, shifting consumer demand across vast geographic regions, and razor-thin margins. Using the public **Olist dataset** (covering orders between 2016 and 2018 across Brazil), I built this dashboard to answer key business questions:

1. **Regional Demand**: How heavily is revenue concentrated in the Southeast (São Paulo/Rio) vs. emerging northern regions?
2. **Logistics Bottlenecks**: How drastically do delivery lead times affect customer review scores (1-star vs. 5-star)?
3. **Category Profitability & Freight Burden**: Which product categories have high shipping overhead relative to product value?
4. **Seller Performance**: Who are the top marketplace sellers, and does seller location dictate delivery performance?
5. **Payment Behavior**: What are the predominant payment methods and installment preferences across customer segments?

---

## 💡 Key Business Findings

* 📍 **Geographic Concentration**: **São Paulo (`SP`)** alone accounts for **~38% of total revenue** (over R\$ 5.06M). The top 3 states (`SP`, `RJ`, `MG`) contribute nearly **65%** of all marketplace GMV.
* 🚚 **Logistics Directly Drives Satisfaction**: Orders rated **1 star** averaged **19.1 days** in transit, whereas **5-star** orders were delivered in an average of **10.2 days**. Delivery delay is the single largest predictor of negative customer reviews.
* 💳 **Credit Card & Installment Culture**: Over **75% of purchases** are completed via credit card, with an average of **3.5 installments**. Boleto (bank slip) represents the second most common method at ~19%.
* 📦 **Shipping Cost Burden**: Categories like heavy furniture and bulky housewares experience freight costs exceeding **35-40% of item value**, creating friction for regional buyers outside major metropolitan hubs.

---

## 🧭 Dashboard Architecture & Analytics Modules

The dashboard is structured into **6 targeted tabs** with interactive sidebar filters (Date Range, State selection, and Category filters):

| Tab | What It Analyzes | Key Visualizations |
| :--- | :--- | :--- |
| **📈 Overview** | Macro trends, monthly GMV, and fulfillment rates | Dual-axis monthly revenue vs. order volume, Order status donut |
| **🗺️ Geography** | State-by-state revenue distribution & city rankings | Interactive Brazil GeoJSON choropleth map, Top 20 cities table |
| **🏷️ Products** | Category sales volume & shipping cost burden | Category revenue bars (with window running totals), Freight % ratio |
| **🚚 Logistics** | Delivery speed across states and review impact | State transit duration comparison, Review score vs. delivery days |
| **💳 Payments** | Customer payment preferences and installment depth | Payment type distribution pie, Installment count bar chart |
| **🏆 Sellers** | Marketplace seller revenue ranking and location | Top 20 sellers bar chart (SQL `RANK()`), Seller state distribution |

---

## 🛠️ Advanced SQL Highlights

All business logic and metrics are computed directly in SQLite using analytical SQL features (CTEs, Window Functions, and Date Parsing):

<details>
<summary><b>1. Running Total & Revenue Share (Window Functions)</b></summary>

```sql
WITH category_revenue AS (
    SELECT
        COALESCE(NULLIF(p.product_category_name,''), 'Unknown') AS category,
        ROUND(SUM(oi.price), 2)  AS revenue,
        COUNT(*)                 AS num_items_sold
    FROM order_items oi
    JOIN products p  ON oi.product_id = p.product_id
    JOIN orders   o  ON oi.order_id   = o.order_id
    WHERE o.order_status = 'delivered'
    GROUP BY p.product_category_name
)
SELECT
    category,
    revenue,
    num_items_sold,
    ROUND(SUM(revenue) OVER (ORDER BY revenue DESC), 2) AS running_total_revenue,
    ROUND(100.0 * revenue / SUM(revenue) OVER (), 2)    AS pct_of_total_revenue
FROM category_revenue
ORDER BY revenue DESC;
```
</details>

<details>
<summary><b>2. Seller Ranking using <code>RANK() OVER</code></b></summary>

```sql
WITH seller_revenue AS (
    SELECT
        oi.seller_id,
        s.seller_state,
        s.seller_city,
        ROUND(SUM(oi.price), 2)     AS total_revenue,
        COUNT(DISTINCT oi.order_id) AS num_orders
    FROM order_items oi
    JOIN sellers s ON oi.seller_id = s.seller_id
    JOIN orders  o ON oi.order_id  = o.order_id
    WHERE o.order_status = 'delivered'
    GROUP BY oi.seller_id, s.seller_state, s.seller_city
)
SELECT
    seller_id,
    seller_state,
    seller_city,
    total_revenue,
    num_orders,
    RANK() OVER (ORDER BY total_revenue DESC) AS revenue_rank
FROM seller_revenue
ORDER BY revenue_rank
LIMIT 20;
```
</details>

<details>
<summary><b>3. Logistics Transit Time Calculation (Date Arithmetic)</b></summary>

```sql
SELECT
    c.customer_state AS state,
    ROUND(AVG(julianday(o.order_delivered_customer_date) - julianday(o.order_purchase_timestamp)), 1) AS avg_delivery_days,
    COUNT(*) AS num_delivered_orders
FROM orders o
JOIN customers c ON o.customer_id = c.customer_id
WHERE o.order_status = 'delivered'
  AND o.order_delivered_customer_date IS NOT NULL
GROUP BY c.customer_state
ORDER BY avg_delivery_days DESC;
```
</details>

---

## 📂 Project Structure

```text
olist-retail-dashboard/
├── brazil_states.geojson    # GeoJSON boundary data for the Brazil choropleth map
├── build_db.py              # Ingestion pipeline: loads CSVs, translates categories, builds indexes
├── queries.py               # SQL queries featuring CTEs, window functions, and filters
├── app.py                   # Main Streamlit web application with caching
├── olist.db                 # SQLite database loaded with 100k+ real records (~90 MB)
├── requirements.txt         # Pinned Python dependencies
├── LICENSE                  # MIT License
└── README.md                # Project documentation
```

---

## ⚡ Quickstart & Local Setup

### 1. Clone the repository
```bash
git clone https://github.com/mehtamanish9/olist-retail-dashboard.git
cd olist-retail-dashboard
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Run the dashboard
```bash
streamlit run app.py
```
Your default browser will automatically open [http://localhost:8501](http://localhost:8501).

---

## 🚀 Deployment (Streamlit Community Cloud)

1. Fork or push this repository to your GitHub account.
2. Visit **[share.streamlit.io](https://share.streamlit.io)** and log in with GitHub.
3. Click **"New app"**, select this repository, set `app.py` as the main entry point, and hit **"Deploy"**.

---

## 👨‍💻 Author

**Manish Mehta**  
* GitHub: [@mehtamanish9](https://github.com/mehtamanish9)  
* Dataset: [Olist Brazilian E-Commerce on Kaggle](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce)

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).


