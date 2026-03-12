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


class CSVHandler(DataLoader):
    """Handles CSV file loading and saving operations."""
    
    def load_data(self, **kwargs):
        """Load CSV data from source file."""
        if not os.path.exists(self.source):
            raise FileNotFoundError(f"File not found: {self.source}")
        
        try:
            return pd.read_csv(self.source, **kwargs)
        except pd.errors.EmptyDataError:
            return pd.DataFrame()
        except Exception as e:
            raise Exception(f"Error loading {self.source}: {e}")

    def save_data(self, data, target_path=None, **kwargs):
        """Save DataFrame to CSV file."""
        if target_path is None:
            raise ValueError("Target path is required")
        
        if not isinstance(data, pd.DataFrame):
            raise ValueError("Data must be a pandas DataFrame")
        
        # Create directory if needed
        target_dir = os.path.dirname(target_path)
        if target_dir and not os.path.exists(target_dir):
            os.makedirs(target_dir)
        
        data.to_csv(target_path, index=False, **kwargs)


