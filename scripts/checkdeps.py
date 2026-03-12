#!/usr/bin/env python3
import os
import sys
import importlib
from pathlib import Path
import pkgutil
import subprocess

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCRIPT_DIRS = [
    "DataNinja",
    "streamyutilities",
    "sports analysis",
]
PLUGIN_DIR = PROJECT_ROOT / "DataNinja/plugins"

# Standard library modules (Python 3.8+)
stdlib_mods = None
try:
    import stdlib_list
    stdlib_mods = set(stdlib_list.stdlib_list())
except ImportError:
    # If stdlib_list is not found, it will be added to missing dependencies
    pass

if stdlib_mods is None: # Happens if import stdlib_list failed
    stdlib_mods = set(sys.builtin_module_names)


def find_imports():
    """Scan all scripts for import statements."""
    imports = set()
    for dir_name in SCRIPT_DIRS:
        dir_path = PROJECT_ROOT / dir_name
        if not dir_path.exists():
            continue
        for root, _, files in os.walk(dir_path):
            for f in files:
                if f.endswith(".py") and not f.startswith("__"):
                    with open(os.path.join(root, f), "r", encoding="utf-8") as file:
                        for line in file:
                            line = line.strip()
                            if line.startswith("import "):
                                parts = line.split()
                                if len(parts) > 1:
                                    imports.add(parts[1].split(".")[0])
                            elif line.startswith("from "):
                                parts = line.split()
                                if len(parts) > 1:
                                    imports.add(parts[1].split(".")[0])
    # Plugins
    if PLUGIN_DIR.exists():
        for f in PLUGIN_DIR.glob("*.py"):
            with open(f, "r", encoding="utf-8") as file:
                for line in file:
                    line = line.strip()
                    if line.startswith("import "):
                        parts = line.split()
                        if len(parts) > 1:
                            imports.add(parts[1].split(".")[0])
                    elif line.startswith("from "):
                        parts = line.split()
                        if len(parts) > 1:
                            imports.add(parts[1].split(".")[0])
    return imports

def check_dependencies():
    imports = find_imports()
    missing = []
    print("\nChecking dependencies...")

    # Check for stdlib_list first
    if pkgutil.find_loader("stdlib_list") is None:
        print("Missing: stdlib_list (recommended for better accuracy)")
        missing.append("stdlib_list")

    for mod in sorted(imports):
        if mod in stdlib_mods: # stdlib_mods will be sys.builtin_module_names if stdlib_list is missing
            continue
        if mod == "stdlib_list": # Already handled
            continue
        if pkgutil.find_loader(mod) is None:
            print(f"Missing: {mod}")
            missing.append(mod)
        else:
            print(f"Found: {mod}")
    if missing:
        print("\nSome dependencies are missing:")
        print(" ".join(missing))
        if input("Install missing packages with pip? [y/N]: ").lower() == "y":
            subprocess.run([sys.executable, "-m", "pip", "install"] + missing)
    else:
        print("\nAll dependencies are installed!")

if __name__ == "__main__":
    check_dependencies() 