import os
import pandas as pd
try:
    from ..core.loader import DataLoader
except ImportError:
    # Fallback for direct execution
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).parent.parent))
    from core.loader import DataLoader


class ExcelHandler(DataLoader):
    """Handles Excel file loading and saving operations."""
    
    def load_data(self, sheet_name=0, **kwargs):
        """Load Excel data from source file."""
        if not os.path.exists(self.source):
            raise FileNotFoundError(f"File not found: {self.source}")
        
        try:
            return pd.read_excel(self.source, sheet_name=sheet_name, engine="openpyxl", **kwargs)
        except Exception as e:
            raise Exception(f"Error loading {self.source}: {e}")

    def save_data(self, data, target_path=None, sheet_name="Sheet1", **kwargs):
        """Save data to Excel file."""
        if target_path is None:
            raise ValueError("Target path is required")
        
        # Create directory if needed
        target_dir = os.path.dirname(target_path)
        if target_dir:
            os.makedirs(target_dir, exist_ok=True)
        
        index = kwargs.pop("index", False)
        
        if isinstance(data, pd.DataFrame):
            data.to_excel(target_path, sheet_name=sheet_name, index=index, engine="openpyxl", **kwargs)
        elif isinstance(data, dict):
            if not all(isinstance(df, pd.DataFrame) for df in data.values()):
                raise TypeError("All dict values must be pandas DataFrames")
            
            with pd.ExcelWriter(target_path, engine="openpyxl") as writer:
                for sheet, df in data.items():
                    df.to_excel(writer, sheet_name=sheet, index=index, **kwargs)
        else:
            raise TypeError("Data must be a pandas DataFrame or dict of DataFrames")


