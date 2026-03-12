"""
EURO 2024 Team Analysis

This script analyzes and displays normalized squad metrics for Euro 2024 teams with live updates.
It provides real-time ranking updates as different weight combinations are applied.

DATA SOURCE: This script requires data from FBRef.com
- Team data: https://fbref.com/en/comps/676/stats/squads/
"""

import pandas as pd
import numpy as np
import os
import time
from pathlib import Path
from typing import List, Dict, Any
from sklearn.preprocessing import MinMaxScaler
from tabulate import tabulate
import logging
import plotext as plt # For terminal plotting
# pandas is already imported as pd


# Configuration
UPDATE_DELAY = 0.3  # seconds between updates
NUM_ITERATIONS = 20
WEIGHT_STEP = 0.05


def setup_logging() -> None:
    """Setup logging configuration."""
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')


def get_file_path() -> str:
    """Get file path from user with helpful guidance."""
    print("=" * 80)
    print("🏆 EURO 2024 TEAM ANALYSIS")
    print("=" * 80)
    print("\nThis analysis requires team statistics data from FBRef.com")
    print("📊 DATA SOURCE: https://fbref.com/en/comps/676/stats/squads/ (UEFA Euro)")
    print("\nPlease provide the path to your EURO 2024 team statistics CSV file:")
    print("💡 Suggestion: euro2024-team-stats.csv (from FBRef squad stats page)")
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
    """Load and validate team data."""
    try:
        df = pd.read_csv(file_path).rename(columns=str.strip)
        return df
    except FileNotFoundError:
        logging.error(f"File not found: {file_path}")
        raise
    except Exception as e:
        logging.error(f"Error loading file: {e}")
        raise


def get_numeric_columns() -> List[str]:
    """Get list of numeric columns for processing."""
    return [
        "Age", "Poss", "MP", "Starts", "Min", "90s", "Gls", "Ast", "G+A", "G-PK", 
        "PK", "PKatt", "CrdY", "CrdR", "xG", "npxG", "xAG", "npxG+xAG", "PrgC", "PrgP"
    ]


def process_per_90_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate per-90-minute statistics."""
    per_90_mappings = [
        ("Gls", "Goals_per_90"),
        ("Ast", "Assists_per_90"),
        ("PrgC", "PrgC_per_90"),
        ("PrgP", "PrgP_per_90"),
    ]
    
    for original_col, new_col in per_90_mappings:
        df[new_col] = df[original_col] / (df["Min"] / 90)
    
    return df


def calculate_derived_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate derived team metrics."""
    df = df.assign(
        xG_diff=df["Gls"] - df["xG"],
        xGA_diff=df["G+A"] - (df["xG"] + df["xAG"]),
        npxGxAG_per_90=df["npxG+xAG"] / (df["Min"] / 90),
        Discipline=(df["CrdY"] + 2 * df["CrdR"]) / df["Min"],
    )
    return df


def aggregate_squad_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate metrics per squad."""
    metrics_to_aggregate = [
        "Goals_per_90", "Assists_per_90", "xG_diff", "xGA_diff", "npxGxAG_per_90",
        "Poss", "PrgC_per_90", "PrgP_per_90", "Discipline"
    ]
    
    agg = df.groupby("Squad")[metrics_to_aggregate].mean().reset_index()
    return agg


def normalize_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize metrics using MinMaxScaler."""
    metrics = df.columns[1:]  # All except 'Squad'
    
    scaler = MinMaxScaler()
    normalized_data = scaler.fit_transform(df[metrics])
    
    norm_df = pd.DataFrame(normalized_data, columns=metrics)
    norm_df["Squad"] = df["Squad"]
    norm_df["Discipline"] *= -1  # Lower is better
    
    return norm_df


def clear_screen() -> None:
    """Clear the console screen."""
    os.system("cls" if os.name == "nt" else "clear")


def display_rankings(score_tracker: pd.DataFrame, weight: float, iteration: int) -> None:
    """Display current team rankings."""
    clear_screen()
    print(f"🔄 Weight: {weight:.2f} | Iteration {iteration}/{NUM_ITERATIONS}\n")
    
    display_df = (
        score_tracker[["Squad", "AvgScore"]]
        .sort_values("AvgScore", ascending=False)
        .reset_index(drop=True)
    )
    
    print(tabulate(display_df.head(24), headers="keys", tablefmt="fancy_grid", showindex=True))


def run_live_analysis(df: pd.DataFrame) -> pd.DataFrame:
    """Run the live analysis with progressive weight updates."""
    # Process data
    numeric_cols = get_numeric_columns()
    df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors="coerce")
    df = df[df["Min"] > 0].dropna(subset=["Squad"])
    
    # Calculate per-90 metrics
    df = process_per_90_metrics(df)
    
    # Calculate derived metrics
    df = calculate_derived_metrics(df)
    
    # Aggregate per squad
    agg = aggregate_squad_metrics(df)
    
    # Normalize metrics
    norm = normalize_metrics(agg)
    
    # Initialize score tracking
    score_tracker = pd.DataFrame({
        "Squad": norm["Squad"], 
        "CumulativeScore": 0.0,
        "AvgScore": 0.0
    })
    
    metrics = norm.columns[1:]  # All except 'Squad'
    
    # Live update loop
    for i, weight in enumerate(np.arange(WEIGHT_STEP, 1.05, WEIGHT_STEP), 1):
        # Update cumulative score
        score_tracker["CumulativeScore"] += (norm[metrics] * weight).sum(axis=1)
        score_tracker["AvgScore"] = score_tracker["CumulativeScore"] / i
        
        # Display current rankings
        display_rankings(score_tracker, weight, i)
        
        # Delay for visual effect
        time.sleep(UPDATE_DELAY)
    
    return score_tracker


def display_final_results(score_tracker: pd.DataFrame) -> None:
    """Display final analysis results."""
    clear_screen()
    print("🏆 FINAL EURO 2024 TEAM RANKINGS\n")
    
    final_rankings = (
        score_tracker[["Squad", "AvgScore"]]
        .sort_values("AvgScore", ascending=False)
        .reset_index(drop=True)
    )
    
    print(tabulate(final_rankings, headers="keys", tablefmt="fancy_grid", showindex=True))
    
    # Show top 3 teams
    print(f"\n🥇 Top Team: {final_rankings.iloc[0]['Squad']} (Score: {final_rankings.iloc[0]['AvgScore']:.3f})")
    if len(final_rankings) > 1:
        print(f"🥈 Second: {final_rankings.iloc[1]['Squad']} (Score: {final_rankings.iloc[1]['AvgScore']:.3f})")
    if len(final_rankings) > 2:
        print(f"🥉 Third: {final_rankings.iloc[2]['Squad']} (Score: {final_rankings.iloc[2]['AvgScore']:.3f})")

    # Plot the final rankings
    # Create a Series from the final_rankings DataFrame for plotting
    # Ensure 'Squad' is index and 'AvgScore' is value
    if not final_rankings.empty:
        plot_data = final_rankings.set_index('Squad')['AvgScore']
        plot_generic_top_n(plot_data, "Final Euro Team Rankings by AvgScore", "Team (Squad)", "Average Score", top_n=len(plot_data), sort_ascending=False)


def main() -> None:
    """Main function to run the EURO 2024 team analysis."""
    setup_logging()
    
    try:
        # Get file path from user
        file_path = get_file_path()
        
        # Load data
        df = load_data(file_path)
        
        # Run live analysis
        score_tracker = run_live_analysis(df)
        
        # Display final results
        display_final_results(score_tracker)
        
    except Exception as e:
        logging.error(f"Analysis failed: {e}")
        return


if __name__ == "__main__":
    main()


def plot_generic_top_n(data_series: pd.Series, title: str, xlabel: str, ylabel: str, top_n: int = 10, sort_ascending=False) -> None:
    """Displays a generic bar chart for a pandas Series in the terminal."""
    # Sort before taking top_n if specified
    sorted_series = data_series.sort_values(ascending=sort_ascending)
    top_data = sorted_series.head(top_n)

    items = top_data.index.tolist()
    values = top_data.values.tolist()

    plt.clf()
    plt.bar(items, values)
    plt.title(title)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.show()
