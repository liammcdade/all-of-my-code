import os
import json
import pandas as pd
try:
    from ..core.loader import DataLoader
except ImportError:
    # Fallback for direct execution
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).parent.parent))
    from core.loader import DataLoader


class JSONHandler(DataLoader):
    """Handles JSON file loading and saving operations."""
    
    def load_data(self, **kwargs):
        """Load JSON data from source file."""
        if not os.path.exists(self.source):
            raise FileNotFoundError(f"File not found: {self.source}")
        
        try:
            # Try pandas first for tabular JSON
            return pd.read_json(self.source, **kwargs)
        except ValueError:
            # Fallback to standard JSON for complex structures
            json_kwargs = {k: v for k, v in kwargs.items() 
                          if k not in ['orient', 'lines', 'dtype', 'convert_dates']}
            with open(self.source, 'r', encoding=kwargs.get('encoding', 'utf-8')) as f:
                return json.load(f, **json_kwargs)
        except Exception as e:
            raise Exception(f"Error loading {self.source}: {e}")

    def save_data(self, data, target_path=None, **kwargs):
        """Save data to JSON file."""
        if target_path is None:
            raise ValueError("Target path is required")
        
        # Create directory if needed
        target_dir = os.path.dirname(target_path)
        if target_dir:
            os.makedirs(target_dir, exist_ok=True)
        
        if isinstance(data, pd.DataFrame):
            orient = kwargs.pop('orient', 'records')
            lines = kwargs.pop('lines', orient == 'records')
            indent = kwargs.pop('indent', None if lines else 4)
            data.to_json(target_path, orient=orient, lines=lines, indent=indent, **kwargs)
        elif isinstance(data, (dict, list)):
            indent = kwargs.pop('indent', 4)
            with open(target_path, 'w', encoding=kwargs.get('encoding', 'utf-8')) as f:
                json.dump(data, f, indent=indent, **kwargs)
        else:
            raise TypeError(f"Unsupported data type: {type(data)}")


