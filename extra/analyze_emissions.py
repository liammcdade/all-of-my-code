import pandas as pd

# Load data
df = pd.read_csv("extra/historical_emissions.csv")  # Updated path

# Set 'country' as index
df.set_index('Country', inplace=True)

# Ensure columns are ordered by year
df.columns = df.columns.astype(str)
df = df[sorted(df.columns, key=lambda x: int(x))]

# Compute % change
pct_change = df.pct_change(axis=1) * 100

# Replace infinities from 0→nonzero with NA
pct_change = pct_change.replace([float('inf'), -float('inf')], pd.NA)

# Mask all values > 100% (likely bad data)
pct_change = pct_change.mask(pct_change > 1000)

# Drop rows or columns that are now entirely NA (optional)
pct_change = pct_change.dropna(how='all', axis=1)

# Find max % increase per country
max_pct_increase_per_country = pct_change.max(axis=1)
year_of_max_pct_increase = pct_change.idxmax(axis=1)

# Find country with the largest valid % increase
country_with_max = max_pct_increase_per_country.idxmax()
year_of_max = year_of_max_pct_increase[country_with_max]
max_value = max_pct_increase_per_country[country_with_max]

# Output
print("Country with largest % increase (≤100%):", country_with_max)
print("Year of increase:", year_of_max)
print("Percentage increase: {:.2f}%".format(max_value))