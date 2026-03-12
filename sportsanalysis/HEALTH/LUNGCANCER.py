"""
Lung Cancer Data Analysis

This script analyzes lung cancer dataset to provide insights and visualizations.

DATA SOURCE: This script requires medical data from various sources:
- Kaggle Medical Datasets: https://www.kaggle.com/datasets?search=lung+cancer
- UCI Machine Learning Repository: https://archive.ics.uci.edu/ml/datasets/Lung+Cancer
- Medical Data Exchange: https://medlineplus.gov/
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
    print("🫁 LUNG CANCER DATA ANALYSIS")
    print("=" * 80)
    print("\nThis analysis requires medical data from various sources.")
    print("📊 DATA SOURCES:")
    print("  • Kaggle Medical Datasets: https://www.kaggle.com/datasets?search=lung+cancer")
    print("  • UCI Machine Learning Repository: https://archive.ics.uci.edu/ml/datasets/Lung+Cancer")
    print("  • Medical Data Exchange: https://medlineplus.gov/")
    print("\nRequired CSV columns: Various medical indicators and diagnosis")
    print("\nPlease provide the path to your lung cancer dataset CSV file:")
    print("💡 Suggestion: lung_cancer_data.csv")
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
    """Load lung cancer data from CSV file."""
    try:
        df = pd.read_csv(file_path)
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
    df = df.dropna()
    
    # Convert numeric columns
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    
    return df


def analyze_data(df: pd.DataFrame) -> Dict[str, any]:
    """Analyze the lung cancer dataset."""
    analysis = {}
    
    # Basic statistics
    analysis['total_records'] = len(df)
    analysis['total_features'] = len(df.columns)
    analysis['missing_values'] = df.isnull().sum().sum()
    
    # Numeric columns analysis
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    if len(numeric_cols) > 0:
        analysis['numeric_stats'] = df[numeric_cols].describe()
    
    # Categorical columns analysis
    categorical_cols = df.select_dtypes(include=['object']).columns
    if len(categorical_cols) > 0:
        analysis['categorical_stats'] = {}
        for col in categorical_cols:
            analysis['categorical_stats'][col] = df[col].value_counts()
    
    return analysis


def display_results(analysis: Dict[str, any]) -> None:
    """Display analysis results."""
    print("\n" + "="*60)
    print("🫁 LUNG CANCER DATA ANALYSIS RESULTS")
    print("="*60)
    
    print(f"\n📊 DATASET OVERVIEW:")
    print(f"   Total Records: {analysis['total_records']:,}")
    print(f"   Total Features: {analysis['total_features']}")
    print(f"   Missing Values: {analysis['missing_values']}")
    
    if 'numeric_stats' in analysis:
        print(f"\n📈 NUMERIC FEATURES STATISTICS:")
        print(analysis['numeric_stats'])
    
    if 'categorical_stats' in analysis:
        print(f"\n📋 CATEGORICAL FEATURES DISTRIBUTION:")
        for col, stats in analysis['categorical_stats'].items():
            print(f"\n   {col}:")
            print(stats.head(10))


def main() -> None:
    """Main function to run the lung cancer analysis."""
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
        analysis = analyze_data(df)
        
        # Display results
        display_results(analysis)
        
    except Exception as e:
        logging.error(f"Analysis failed: {e}")
        return


if __name__ == "__main__":
    main()
