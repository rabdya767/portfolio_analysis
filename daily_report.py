import os
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta

OUTPUT_DIR = "./output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ---- Portfolio stocks and info ----
portfolio_stocks = {
    "ICICIBANK.NS": {"sector": "Banking", "market_cap": None},
    "HDFCBANK.NS": {"sector": "Financial Services", "market_cap": None},
    "CDSL.NS": {"sector": "Financial Services", "market_cap": None},
    "ETERNAL.NS": {"sector": "Consumer Services", "market_cap": None},
}

# ---- Step 1: Download 3 months data ----
end_date = datetime.now()
start_date = end_date - timedelta(days=10)

def fetch_stock_data(tickers):
    data = {}
    for ticker in tickers:
        ticker_obj = yf.Ticker(ticker)
        hist = ticker_obj.history(start=start_date.strftime("%Y-%m-%d"), end=end_date.strftime("%Y-%m-%d"))
        if hist.empty:
            print(f"Warning: No data for {ticker}")
        data[ticker] = hist
    return data

stock_data = fetch_stock_data(portfolio_stocks.keys())

# ---- Step 2: Calculate daily returns heatmap ----
returns = pd.DataFrame()
date_fmt = lambda d: d.strftime('%d-%m-%Y')
for ticker, df in stock_data.items():
    if not df.empty and "Close" in df:
        df['Daily Return'] = df['Close'].pct_change()
        # Format index as dd-mm-YYYY
        df.index = [date_fmt(idx) for idx in df.index]
        returns[ticker] = df['Daily Return']
returns = returns.T
returns = returns.sort_index()

# Remove columns where all NaN
returns.dropna(axis=1, how='all', inplace=True)

# ---- Heatmap with square cells and vertical date labels ----
plt.figure(figsize=(max(8, len(returns.columns) * 0.6), max(4, len(returns) * 0.6)))
sns.heatmap(
    returns, 
    cmap="RdYlGn", 
    center=0, 
    linewidths=0.5, 
    linecolor='gray', 
    cbar_kws={'label': 'Daily Return'}, 
    square=True  # Make cells square
)
plt.title("Portfolio Daily Returns Heatmap (Last 10 days)")
plt.xlabel("Date")
plt.ylabel("Stock")
plt.xticks(
    ticks=np.arange(0.5, len(returns.columns)), 
    labels=returns.columns,
    rotation=90,
    ha='center',
    fontsize=8
)
plt.yticks(fontsize=10)
plt.tight_layout()
plt.savefig(f"{OUTPUT_DIR}/heatmap.png", dpi=300)
plt.close()

# ---- Step 3: Fetch Market Caps ----
def fetch_market_caps(tickers):
    for ticker in tickers:
        try:
            ticker_obj = yf.Ticker(ticker)
            info = ticker_obj.info
            market_cap = info.get("marketCap", None)
            portfolio_stocks[ticker]["market_cap"] = market_cap
        except Exception as e:
            print(f"Error fetching market cap for {ticker}: {e}")
            portfolio_stocks[ticker]["market_cap"] = None

fetch_market_caps(portfolio_stocks.keys())

# Build DataFrame for Market Cap and Sector
df_portfolio = pd.DataFrame.from_dict(portfolio_stocks, orient='index')
df_portfolio['market_cap_crore'] = df_portfolio['market_cap'] / 1e7  # Convert to crores
df_portfolio = df_portfolio.sort_values('market_cap_crore', ascending=False)

# ---- Step 4: Plot Market Cap Bar Chart ----
plt.figure(figsize=(8,5))
colors = sns.color_palette("Set2", len(df_portfolio))
sns.barplot(
    x='market_cap_crore', y=df_portfolio.index, 
    data=df_portfolio, 
    palette=colors
)
plt.xlabel("Market Cap (₹ Crore)")
plt.title("Market Capitalization of Portfolio Stocks")
plt.tight_layout()
plt.savefig(f"{OUTPUT_DIR}/marketcap.png", dpi=300)
plt.close()

# ---- Step 5: Sector Allocation Pie Chart ----
sector_caps = df_portfolio.groupby('sector')['market_cap_crore'].sum()
sector_percentage = sector_caps / sector_caps.sum() * 100
plt.figure(figsize=(6,6))
palette = sns.color_palette("Set2", len(sector_caps))
plt.pie(sector_percentage, labels=sector_caps.index, autopct='%1.1f%%', colors=palette, startangle=140)
plt.title("Portfolio Sector Allocation (%)")
plt.tight_layout()
plt.savefig(f"{OUTPUT_DIR}/sector_allocation.png", dpi=300)
plt.close()

# ---- Step 6: Plot 3-month Closing Price Line Chart ----
plt.figure(figsize=(12,6))
highlight_stock = "HDFCBANK.NS"
for ticker, data in stock_data.items():
    if data.empty:
        continue
    prices = data['Close']
    prices.index = [date_fmt(idx) for idx in prices.index]
    if ticker == highlight_stock:
        plt.plot(prices.index, prices, label=ticker, linewidth=3)
    else:
        plt.plot(prices.index, prices, label=ticker, linewidth=1.5, alpha=0.7)
plt.title("3-Month Stock Price Trends")
plt.xlabel("Date")
plt.ylabel("Price (₹)")
plt.legend()
plt.xticks(rotation=90, fontsize=8)
plt.tight_layout()
plt.savefig(f"{OUTPUT_DIR}/price_trends.png", dpi=300)
plt.close()

# ---- Step 7: Compose HTML Email Body ----
def generate_email_body():
    gainers_html = "<li>RELIANCE: ₹2,500 (+2.5%)</li><li>TCS: ₹3,500 (+1.7%)</li>... (add more)</ul>"
    losers_html = "<li>BHARTIARTL: ₹600 (-3.5%)</li><li>ZEEL: ₹180 (-2.1%)</li>... (add more)</ul>"
    marketcap_table_rows = "".join(
        f"<tr><td>{idx}</td><td>{row.Index}</td><td>{row.market_cap_crore:,.1f}</td><td>{row.sector}</td></tr>"
        for idx, row in enumerate(df_portfolio.itertuples(), 1)
    )
    sector_table_rows = "".join(
        f"<tr><td>{idx}</td><td>{sector}</td><td>{value:,.1f}</td><td>{percentage:.2f}%</td></tr>"
        for idx, (sector, value) in enumerate(sector_caps.iteritems(), 1)
        for percentage in [sector_percentage[sector]]
    )
    body = f"""
    <html>
    <body>
    <h2>Daily Portfolio Analysis Report</h2>
    <p>Attached charts include heatmap, market cap distribution, sector allocation, and 3-month price trends.</p>
    <h3>Top 10 Gainers Today</h3>
    <ul>{gainers_html}</ul>
    <h3>Top 10 Losers Today</h3>
    <ul>{losers_html}</ul>
    <h3>Portfolio Market Capitalization (₹ Crores)</h3>
    <table border="1" cellpadding="5" style="border-collapse: collapse;">
      <tr><th>#</th><th>Stock</th><th>Market Cap</th><th>Sector</th></tr>
      {marketcap_table_rows}
    </table>
    <h3>Sector Allocation</h3>
    <table border="1" cellpadding="5" style="border-collapse: collapse;">
      <tr><th>#</th><th>Sector</th><th>Market Cap</th><th>Allocation %</th></tr>
      {sector_table_rows}
    </table>
    <p>For detailed visuals, please see attached PNG charts.</p>
    </body>
    </html>
    """
    return body

email_body_html = generate_email_body()
with open(f"{OUTPUT_DIR}/email_body.html", 'w', encoding='utf-8') as f:
    f.write(email_body_html)

print("Daily report generated with charts and email summary.")

