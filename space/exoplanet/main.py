import os
import sys
import glob
import numpy as np
import pandas as pd

def get_latest_csv():
    """Finds the latest exoplanet CSV file in the script's directory."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    pattern = os.path.join(script_dir, "exoplanet.eu_catalog_*.csv")
    csv_files = glob.glob(pattern)
    
    if not csv_files:
        return None
    
    # Sort by modification time to get the latest
    latest_file = max(csv_files, key=os.path.getmtime)
    return latest_file

def load_data():
    """Loads exoplanet data from the local CSV file."""
    csv_path = get_latest_csv()
    
    if not csv_path:
        print("Error: No exoplanet CSV file found (expected 'exoplanet.eu_catalog_*.csv').", file=sys.stderr)
        return None
    
    try:
        print(f"Loading data from local CSV: {csv_path}...")
        # Exoplanet.eu CSVs usually use commas, but we handle errors gracefully.
        data = pd.read_csv(csv_path)
        return data
    except Exception as e:
        print(f"Error: Failed to load CSV ({e})", file=sys.stderr)
        return None

def calculate_missing_values(data):
    """Fills in missing astronomical values using specific formulas."""
    if data is None:
        return None
    
    print("Calculating missing values using astronomical formulas...")
    
    # angular_distance: semi_major_axis (AU) / star_distance (parsecs)
    if 'semi_major_axis' in data.columns and 'star_distance' in data.columns:
        # We use fillna so we don't overwrite existing values if they are already present
        calc_angular = data['semi_major_axis'] / data['star_distance']
        data['angular_distance'] = data['angular_distance'].fillna(calc_angular)
    
    # temp_calculated: star_teff * (star_radius / semi_major_axis)**0.5 / sqrt(2)
    if all(col in data.columns for col in ['star_teff', 'star_radius', 'semi_major_axis']):
        # Formula: T_eff * sqrt(R_star / a) / sqrt(2)
        # Avoid division by zero
        safe_semi = data['semi_major_axis'].replace(0, np.nan)
        calc_temp = data['star_teff'] * np.sqrt(data['star_radius'] / safe_semi) / np.sqrt(2)
        data['temp_calculated'] = data['temp_calculated'].fillna(calc_temp)
        
    # log_g: 3.394 + log10(mass) - 2 * log10(radius)
    if 'mass' in data.columns and 'radius' in data.columns:
        # astronomical data should be positive; filter out non-positive values for log
        mask = (data['mass'] > 0) & (data['radius'] > 0)
        calc_logg = 3.394 + np.log10(data.loc[mask, 'mass']) - 2 * np.log10(data.loc[mask, 'radius'])
        data.loc[mask, 'log_g'] = data.loc[mask, 'log_g'].fillna(calc_logg)
        
    return data

def display_summary(data):
    """Displays a summary of the exoplanet dataset."""
    if data is None:
        return

    print("\n--- Exoplanet Data Summary ---")
    print(f"Total entries: {len(data)}")
    print(f"Total columns: {len(data.columns)}")
    
    # Calculate cell completion percentage
    total_cells = data.size
    completed_cells = data.count().sum()
    completion_percentage = (completed_cells / total_cells) * 100 if total_cells > 0 else 0
    print(f"Data Completion: {completion_percentage:.2f}%")
    
    print("\nColumn Overview (First 10):")
    print(", ".join(data.columns[:10]))
    
    # Adding some basic stats if available
    if 'mass' in data.columns:
        valid_mass = data['mass'].dropna()
        if not valid_mass.empty:
            print(f"\nAverage Planet Mass: {valid_mass.mean():.4f} (units vary)")
    
    if 'discovered' in data.columns:
        years = data['discovered'].dropna()
        if not years.empty:
            print(f"Latest Discovery Year: {int(years.max())}")
            
    print("------------------------------\n")

def main():
    data = load_data()
    if data is not None:
        data = calculate_missing_values(data)
        display_summary(data)
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()
