"""
Kaggle Food Prices Analysis

This script analyzes food price data from the World Food Programme (WFP) for Egypt.
It provides insights into food price trends, volatility, and market dynamics.

DATA SOURCE: This script requires food price data from Kaggle:
- World Food Programme Food Prices: https://www.kaggle.com/datasets/jboysen/world-food-programme-food-prices
- Alternative: https://www.kaggle.com/datasets/patelris/crop-recommendation-dataset
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os
from typing import Dict, List, Tuple
import logging


def setup_logging() -> None:
    """Setup logging configuration."""
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')


def get_file_path() -> str:
    """Get file path from user with helpful guidance."""
    print("=" * 80)
    print("🌾 KAGGLE FOOD PRICES ANALYSIS")
    print("=" * 80)
    print("\nThis analysis requires food price data from Kaggle.")
    print("📊 DATA SOURCES:")
    print("  • World Food Programme Food Prices: https://www.kaggle.com/datasets/jboysen/world-food-programme-food-prices")
    print("  • Alternative: https://www.kaggle.com/datasets/patelris/crop-recommendation-dataset")
    print("\nRequired CSV columns: date, commodity, price, market, country")
    print("\nPlease provide the path to your food prices CSV file:")
    print("💡 Suggestion: wfp_food_prices.csv")
    print("📁 Please enter the full path to your CSV file:")
    
    while True:
        file_path = input("File path: ").strip().strip('"')
        
        if not file_path:
            print("❌ Please provide a file path.")
            continue
            
        if not os.path.exists(file_path):
            print(f"❌ File not found: {file_path}")
            print("Please check the path and try again.")
            continue
            
        if not file_path.lower().endswith('.csv'):
            print("❌ Please provide a CSV file.")
            continue
            
        return file_path


def load_data(file_path: str) -> pd.DataFrame:
    """Load food price data from CSV file."""
    try:
        df = pd.read_csv(file_path, parse_dates=["date"], dayfirst=True)
        return df
    except FileNotFoundError:
        logging.error(f"File not found: {file_path}")
        raise
    except Exception as e:
        logging.error(f"Error loading file: {e}")
        raise


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """Clean and prepare the dataset."""
    # Remove rows with missing critical data
    df = df.dropna(subset=['date', 'commodity', 'price'])
    
    # Convert price to numeric, removing any currency symbols
    df['price'] = pd.to_numeric(df['price'].astype(str).str.replace(r'[^\d.]', '', regex=True), errors='coerce')
    
    # Remove rows with invalid prices
    df = df[df['price'] > 0]
    
    # Filter for Egypt data if available
    if 'country' in df.columns:
        df = df[df['country'].str.contains('Egypt', case=False, na=False)]
    
    return df


def analyze_price_trends(df: pd.DataFrame) -> Dict[str, float]:
    """Analyze price trends and statistics."""
    # Calculate basic statistics
    stats = {
        'total_records': len(df),
        'unique_commodities': df['commodity'].nunique(),
        'date_range': f"{df['date'].min().strftime('%Y-%m-%d')} to {df['date'].max().strftime('%Y-%m-%d')}",
        'avg_price': df['price'].mean(),
        'median_price': df['price'].median(),
        'price_std': df['price'].std(),
        'min_price': df['price'].min(),
        'max_price': df['price'].max()
    }
    
    # Calculate price volatility (coefficient of variation)
    stats['price_volatility'] = (df['price'].std() / df['price'].mean()) * 100
    
    return stats


def get_top_commodities(df: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    """Get top commodities by average price."""
    commodity_stats = df.groupby('commodity').agg({
        'price': ['mean', 'std', 'count']
    }).round(2)
    
    commodity_stats.columns = ['avg_price', 'price_std', 'record_count']
    commodity_stats = commodity_stats.sort_values('avg_price', ascending=False)
    
    return commodity_stats.head(n)


def calculate_price_changes(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate price changes over time for each commodity."""
    # Sort by commodity and date
    df_sorted = df.sort_values(['commodity', 'date'])
    
    # Calculate price changes
    price_changes = df_sorted.groupby('commodity').agg({
        'date': ['first', 'last'],
        'price': ['first', 'last']
    })
    
    price_changes.columns = ['start_date', 'end_date', 'start_price', 'end_price']
    price_changes['price_change'] = price_changes['end_price'] - price_changes['start_price']
    price_changes['price_change_pct'] = ((price_changes['end_price'] - price_changes['start_price']) / 
                                        price_changes['start_price']) * 100
    
    return price_changes.sort_values('price_change_pct', ascending=False)


def display_results(stats: Dict[str, float], top_commodities: pd.DataFrame, price_changes: pd.DataFrame) -> None:
    """Display analysis results."""
    print("\n" + "="*60)
    print("📊 FOOD PRICES ANALYSIS RESULTS")
    print("="*60)
    
    print(f"\n📈 DATASET OVERVIEW:")
    print(f"   Total Records: {stats['total_records']:,}")
    print(f"   Unique Commodities: {stats['unique_commodities']}")
    print(f"   Date Range: {stats['date_range']}")
    
    print(f"\n💰 PRICE STATISTICS:")
    print(f"   Average Price: {stats['avg_price']:.2f}")
    print(f"   Median Price: {stats['median_price']:.2f}")
    print(f"   Price Range: {stats['min_price']:.2f} - {stats['max_price']:.2f}")
    print(f"   Price Volatility: {stats['price_volatility']:.1f}%")
    
    print(f"\n🏆 TOP 10 COMMODITIES BY AVERAGE PRICE:")
    print(top_commodities.to_string())
    
    print(f"\n📈 TOP 10 COMMODITIES BY PRICE CHANGE:")
    top_changes = price_changes.head(10)
    for idx, row in top_changes.iterrows():
        change_symbol = "📈" if row['price_change_pct'] > 0 else "📉"
        print(f"   {change_symbol} {idx}: {row['price_change_pct']:+.1f}% "
              f"({row['start_price']:.2f} → {row['end_price']:.2f})")


def main() -> None:
    """Main function to run the food prices analysis."""
    setup_logging()
    
    try:
        # Get file path from user
        file_path = get_file_path()
        
        # Load and clean data
        df = load_data(file_path)
        df = clean_data(df)
        
        if df.empty:
            print("❌ No valid data found after cleaning.")
            return
        
        # Perform analysis
        stats = analyze_price_trends(df)
        top_commodities = get_top_commodities(df)
        price_changes = calculate_price_changes(df)
        
        # Display results
        display_results(stats, top_commodities, price_changes)
        
    except Exception as e:
        logging.error(f"Analysis failed: {e}")
        return


if __name__ == "__main__":
    main()
