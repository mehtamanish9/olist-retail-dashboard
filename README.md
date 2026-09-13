# Olist Retail Analytics Dashboard

An interactive, production-ready Streamlit dashboard delivering SQL-driven business analytics on the **Olist Brazilian E-Commerce dataset**.

Built with **Python**, **SQLite**, **Pandas**, **Plotly**, and **Streamlit**.

---

## 🌟 Key Features

- **Dynamic Interactive Filtering**: Filter all analytics simultaneously by order purchase date range, customer state, and product category from the sidebar.
- **Top-level KPIs**: Total Delivered Orders, Total Revenue, Average Item Price, Average Review Score, and Unique Customers with caching for instant updates.
- **6 Comprehensive Analytics Tabs**:
  1. 📈 **Overview**: Dual-axis monthly revenue and order volume trends, alongside an interactive donut chart of order statuses.
  2. 🗺️ **Geography**: Brazil state-level choropleth map powered by local GeoJSON and top 20 cities ranked by order volume.
  3. 🏷️ **Products**: Top categories by revenue with SQL running totals (`SUM() OVER`), plus freight cost burden analysis (% freight vs. price). Category names automatically translated to English.
  4. 🚚 **Logistics**: Average delivery days per Brazilian state, and correlation between delivery speed and customer review scores (1–5 stars).
  5. 💳 **Payments**: Payment method distribution (Credit Card, Boleto, Voucher, Debit) and average installment count by payment type.
  6. 🏆 **Sellers**: Top 20 sellers ranked by total revenue using SQL `RANK()` window functions.

---

## 📁 Project Structure

```
olist-dashboard/
├── brazil_states.geojson    # Local Brazil state boundary shapes for the choropleth map
├── build_placeholder_db.py  # Builds olist.db from CSVs, translates categories, creates SQL indexes
├── queries.py               # SQL queries (CTEs, window functions, aggregates)
├── app.py                   # Streamlit multi-tab dashboard application
├── olist.db                 # SQLite database loaded with real dataset (~90 MB)
├── requirements.txt         # Project dependencies
└── README.md
```

---

## 🚀 Setup & Running Locally

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **(Optional) Rebuild the database from CSVs**:
   ```bash
   python build_placeholder_db.py
   ```

3. **Launch the dashboard**:
   ```bash
   streamlit run app.py
   ```
   Open [http://localhost:8501](http://localhost:8501) in your browser.

---

## ☁️ Deployment (Streamlit Community Cloud)

1. Push this repository to GitHub.
2. Visit [share.streamlit.io](https://share.streamlit.io) and log in with your GitHub account.
3. Click **New app**, select the repository, branch, and set `app.py` as the main file path.
4. Click **Deploy**.
