import logging
import os
import json
from datetime import datetime


# --- Configuration Loading ---
def load_config(config_path="config.json"):
    """
    Loads a JSON configuration file.

    Args:
        config_path (str): Path to the configuration file.

    Returns:
        dict: Configuration dictionary, or None if loading fails.
    """
    try:
        with open(config_path, "r") as f:
            config = json.load(f)
        return config
    except FileNotFoundError:
        print(f"Warning: Configuration file '{config_path}' not found.")
        return None
    except json.JSONDecodeError:
        print(f"Warning: Error decoding JSON from '{config_path}'.")
        return None
    except Exception as e:
        print(f"An unexpected error occurred while loading config '{config_path}': {e}")
        return None


# --- Logging Setup ---
def setup_logging(level=logging.INFO, log_file=None, module_name=None):
    """Simple logging setup for DataNinja modules."""
    logger = logging.getLogger(module_name or __name__)
    
    if logger.hasHandlers():
        return logger
        
    logger.setLevel(level)
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    
    # Console handler
    ch = logging.StreamHandler()
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    
    # File handler (optional)
    if log_file:
        fh = logging.FileHandler(log_file)
        fh.setFormatter(formatter)
        logger.addHandler(fh)
    
    return logger


# --- File System Utilities ---
def ensure_directory_exists(dir_path):
    """
    Ensures that a directory exists, creating it if necessary.

    Args:
        dir_path (str): The path to the directory.

    Returns:
        bool: True if the directory exists or was created successfully, False otherwise.
    """
    if not os.path.exists(dir_path):
        try:
            os.makedirs(dir_path)
            print(f"Directory created: {dir_path}")
            return True
        except OSError as e:
            print(f"Error creating directory {dir_path}: {e}")
            return False
    return True


def generate_timestamped_filename(base_name, extension, prefix=""):
    """
    Generates a filename with a timestamp. E.g., "prefix_basename_YYYYMMDD_HHMMSS.extension"

    Args:
        base_name (str): The main part of the filename.
        extension (str): The file extension (e.g., "csv", "png").
        prefix (str, optional): A prefix for the filename.

    Returns:
        str: The generated timestamped filename.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    clean_extension = extension.lstrip(".")
    if prefix:
        return f"{prefix}_{base_name}_{timestamp}.{clean_extension}"
    else:
        return f"{base_name}_{timestamp}.{clean_extension}"



