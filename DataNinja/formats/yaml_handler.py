import os
import yaml
try:
    from ..core.loader import DataLoader
except ImportError:
    # Fallback for direct execution
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).parent.parent))
    from core.loader import DataLoader


class YAMLHandler(DataLoader):
    """Handles YAML file loading and saving operations."""
    
    def load_data(self, **kwargs):
        """Load YAML data from source file."""
        if not os.path.exists(self.source):
            raise FileNotFoundError(f"File not found: {self.source}")
        
        encoding = kwargs.pop("encoding", "utf-8")
        
        try:
            with open(self.source, "r", encoding=encoding) as stream:
                return yaml.safe_load(stream, **kwargs)
        except yaml.YAMLError as e:
            raise Exception(f"YAML parsing error in {self.source}: {e}")
        except Exception as e:
            raise Exception(f"Error loading {self.source}: {e}")

    def save_data(self, data, target_path=None, **kwargs):
        """Save data to YAML file."""
        if target_path is None:
            raise ValueError("Target path is required")
        
        # Create directory if needed
        target_dir = os.path.dirname(target_path)
        if target_dir:
            os.makedirs(target_dir, exist_ok=True)
        
        # Extract YAML-specific options
        encoding = kwargs.pop("encoding", "utf-8")
        sort_keys = kwargs.pop("sort_keys", False)
        allow_unicode = kwargs.pop("allow_unicode", True)
        
        try:
            with open(target_path, "w", encoding=encoding) as stream:
                yaml.dump(data, stream, sort_keys=sort_keys, 
                         allow_unicode=allow_unicode, **kwargs)
        except (yaml.YAMLError, TypeError) as e:
            raise Exception(f"Error saving YAML to {target_path}: {e}")


