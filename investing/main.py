import pandas as pd
import datetime

# Load data
stocks = pd.read_csv('C:/Users/liam/Documents/GitHub/All-code-in-one/investing/stocks.csv')
crypto = pd.read_csv('C:/Users/liam/Documents/GitHub/All-code-in-one/investing/cryptocurrency.csv')

# Current date and latest data timestamps
current_date = datetime.date.today()
print(f"Current date: {current_date}")
latest_stock_timestamp = stocks['timestamp'].max()
latest_crypto_timestamp = crypto['timestamp'].max()
print(f"Latest stock data timestamp: {latest_stock_timestamp}")
print(f"Latest crypto data timestamp: {latest_crypto_timestamp}")

# Process stocks: get latest entry for each stock
stocks['timestamp'] = pd.to_datetime(stocks['timestamp'])
stocks = stocks.sort_values('timestamp')
stocks_latest = stocks.groupby('name').last().reset_index()
stocks_latest['chg_%'] = stocks_latest['chg_%'].str.rstrip('%').astype(float)
stocks_latest['last'] = stocks_latest['last'].astype(float)

# Process crypto: get latest entry for each crypto
crypto['timestamp'] = pd.to_datetime(crypto['timestamp'])
crypto = crypto.sort_values('timestamp')
crypto_latest = crypto.groupby('name').last().reset_index()
crypto_latest['chg_24h'] = crypto_latest['chg_24h'].str.rstrip('%').astype(float)
crypto_latest['price_usd'] = crypto_latest['price_usd'].str.lstrip('$').str.replace(',', '').astype(float)

# Select top 12 stocks with positive chg_%
positive_stocks = stocks_latest[stocks_latest['chg_%'] > 0].sort_values('chg_%', ascending=False).head(12)

# Select top 12 cryptos with positive chg_24h
positive_crypto = crypto_latest[crypto_latest['chg_24h'] > 0].sort_values('chg_24h', ascending=False).head(12)

# Allocate budget
total_budget = 10000

# Compute average returns for dynamic allocation
avg_stock_return = positive_stocks['chg_%'].mean() if not positive_stocks.empty else 0
avg_crypto_return = positive_crypto['chg_24h'].mean() if not positive_crypto.empty else 0
total_avg_return = avg_stock_return + avg_crypto_return

if total_avg_return > 0:
    stock_budget = total_budget * (avg_stock_return / total_avg_return)
    crypto_budget = total_budget * (avg_crypto_return / total_avg_return)
else:
    stock_budget = total_budget / 2
    crypto_budget = total_budget / 2

# Function to allocate budget
def allocate_budget(selected, budget, price_col, change_col, symbol_col=None):
    num = len(selected)
    if num == 0:
        return [], 0
    total_change = selected[change_col].sum()
    allocations = []
    total_cost = 0
    for _, row in selected.iterrows():
        if total_change > 0:
            weight = row[change_col] / total_change
            asset_budget = budget * weight
        else:
            asset_budget = budget / num
        price = row[price_col]
        qty = int(asset_budget // price)
        cost = qty * price
        symbol = row[symbol_col] if symbol_col else row['name']
        allocations.append({
            'symbol': symbol,
            'name': row['name'],
            'price': price,
            'quantity': qty,
            'cost': cost,
            'expected_daily_return': row[change_col]
        })
        total_cost += cost
    return allocations, total_cost

# Allocate for stocks
stock_allocations, stock_total_cost = allocate_budget(positive_stocks, stock_budget, 'last', 'chg_%')

# Allocate for crypto
crypto_allocations, crypto_total_cost = allocate_budget(positive_crypto, crypto_budget, 'price_usd', 'chg_24h')

# Output results
print("Selected Stocks (Top 12 with positive daily change):")
for alloc in stock_allocations:
    print(f"{alloc['name']}: Buy {alloc['quantity']} shares at ${alloc['price']:.2f} each, Total: ${alloc['cost']:.2f}, Expected Daily Return: {alloc['expected_daily_return']:.2f}%")

print(f"\nTotal Stock Cost: ${stock_total_cost:.2f}")

print("\nSelected Cryptocurrencies (Top 12 with positive 24h change):")
for alloc in crypto_allocations:
    print(f"{alloc['name']}: Buy {alloc['quantity']} at ${alloc['price']:.2f} each, Total: ${alloc['cost']:.2f}, Expected Daily Return: {alloc['expected_daily_return']:.2f}%")

print(f"\nTotal Crypto Cost: ${crypto_total_cost:.2f}")
print(f"Total Budget Used: ${stock_total_cost + crypto_total_cost:.2f}")

# Create historical portfolio CSV
selected_names_stocks = positive_stocks['name'].tolist()
selected_names_crypto = positive_crypto['name'].tolist()
stocks_historical = stocks[stocks['name'].isin(selected_names_stocks)].copy()
crypto_historical = crypto[crypto['name'].isin(selected_names_crypto)].copy()
all_timestamps = sorted(set(stocks_historical['timestamp']).union(set(crypto_historical['timestamp'])))
portfolio_values = []
prev_value = None
for ts in all_timestamps:
    value = 0
    for alloc in stock_allocations:
        if alloc['quantity'] > 0:
            price_row = stocks_historical[(stocks_historical['timestamp'] == ts) & (stocks_historical['name'] == alloc['name'])]
            if not price_row.empty:
                price = float(price_row['last'].values[0])
                value += alloc['quantity'] * price
    for alloc in crypto_allocations:
        if alloc['quantity'] > 0:
            price_row = crypto_historical[(crypto_historical['timestamp'] == ts) & (crypto_historical['name'] == alloc['name'])]
            if not price_row.empty:
                price = float(price_row['price_usd'].values[0])
                value += alloc['quantity'] * price
    if value > 0:
        change_pct = 0 if prev_value is None else (value - prev_value) / prev_value * 100
        portfolio_values.append({
            'Date': ts.strftime('%Y-%m-%d'),
            'Price': value,
            'Open': value,
            'High': value,
            'Low': value,
            'Vol': 0,
            'Change %': change_pct
        })
        prev_value = value
df_portfolio = pd.DataFrame(portfolio_values)
df_portfolio.to_csv('portfolio.csv', index=False)
