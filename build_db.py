"""
Builds olist.db from the real Olist Brazilian E-Commerce CSVs.

Place all 9 CSV files in this folder, then run:
    python build_db.py

Tables created:
    customers, sellers, products, orders,
    order_items, payments, reviews

Notes:
  - product_category_name_translation is merged into products so
    the dashboard gets English category names automatically.
  - geolocation CSV is intentionally skipped (58 MB, not needed for queries).
  - Indexes are created on all join columns for fast query performance.
"""

import sqlite3
import sys
from pathlib import Path

import pandas as pd

DB_PATH = Path("olist.db")
CSV_DIR = Path(".")

CSV_FILES = {
    "customers":  "olist_customers_dataset.csv",
    "sellers":    "olist_sellers_dataset.csv",
    "products":   "olist_products_dataset.csv",
    "orders":     "olist_orders_dataset.csv",
    "order_items":"olist_order_items_dataset.csv",
    "payments":   "olist_order_payments_dataset.csv",
    "reviews":    "olist_order_reviews_dataset.csv",
    "translation":"product_category_name_translation.csv",
}

def load_csv(key: str) -> pd.DataFrame:
    path = CSV_DIR / CSV_FILES[key]
    if not path.exists():
        print(f"  [!]  Missing: {path}  - skipping.")
        return pd.DataFrame()
    df = pd.read_csv(path)
    print(f"  [ok]  {key:15s}  {len(df):>8,} rows   ({path.stat().st_size / 1e6:.1f} MB)")
    return df

print("=" * 55)
print("  Olist DB Builder — loading real CSVs")
print("=" * 55)

# ── Load all CSVs ───────────────────────────────────────────
customers   = load_csv("customers")
sellers     = load_csv("sellers")
orders      = load_csv("orders")
order_items = load_csv("order_items")
payments    = load_csv("payments")
reviews     = load_csv("reviews")
products_raw = load_csv("products")
translation  = load_csv("translation")

# ── Merge English category names into products ───────────────
if not products_raw.empty and not translation.empty:
    products = products_raw.merge(
        translation,
        on="product_category_name",
        how="left",
    )
    # Use English name where available, fall back to Portuguese
    products["product_category_name"] = products.get(
        "product_category_name_english", products["product_category_name"]
    ).fillna(products["product_category_name"])
    # Drop the extra translation column if it was merged in
    products = products.drop(
        columns=["product_category_name_english"], errors="ignore"
    )
else:
    products = products_raw

# ── Slim down reviews to needed columns ─────────────────────
if not reviews.empty:
    keep_cols = [c for c in ["order_id", "review_score", "review_comment_message"] if c in reviews.columns]
    reviews = reviews[keep_cols].drop_duplicates(subset=["order_id"])

# ── Write to SQLite ──────────────────────────────────────────
print(f"\nWriting to {DB_PATH} …")
conn = sqlite3.connect(DB_PATH)
conn.execute("PRAGMA journal_mode=WAL;")
conn.execute("PRAGMA synchronous=NORMAL;")

TABLES = {
    "customers":   customers,
    "sellers":     sellers,
    "products":    products,
    "orders":      orders,
    "order_items": order_items,
    "payments":    payments,
    "reviews":     reviews,
}

for name, df in TABLES.items():
    if df.empty:
        print(f"  skip  {name}")
        continue
    df.to_sql(name, conn, if_exists="replace", index=False)
    print(f"  wrote {name}")

# ── Indexes for fast joins ───────────────────────────────────
print("\nCreating indexes ...")
indexes = [
    "CREATE INDEX IF NOT EXISTS idx_orders_customer  ON orders(customer_id);",
    "CREATE INDEX IF NOT EXISTS idx_orders_status    ON orders(order_status);",
    "CREATE INDEX IF NOT EXISTS idx_oi_order         ON order_items(order_id);",
    "CREATE INDEX IF NOT EXISTS idx_oi_product       ON order_items(product_id);",
    "CREATE INDEX IF NOT EXISTS idx_oi_seller        ON order_items(seller_id);",
    "CREATE INDEX IF NOT EXISTS idx_payments_order   ON payments(order_id);",
    "CREATE INDEX IF NOT EXISTS idx_reviews_order    ON reviews(order_id);",
    "CREATE INDEX IF NOT EXISTS idx_products_cat     ON products(product_category_name);",
    "CREATE INDEX IF NOT EXISTS idx_sellers_state    ON sellers(seller_state);",
    "CREATE INDEX IF NOT EXISTS idx_customers_state  ON customers(customer_state);",
]
for sql in indexes:
    conn.execute(sql)
conn.commit()
conn.close()

db_mb = DB_PATH.stat().st_size / 1e6
print(f"\n[DONE]  olist.db ready  ({db_mb:.1f} MB)")
print("   Run:  streamlit run app.py")
