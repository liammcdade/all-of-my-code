#!/usr/bin/env python3
import os
import sys
import inspect
from pathlib import Path
import importlib.util

PROJECT_ROOT = Path(__file__).resolve().parent.parent
README_PATH = PROJECT_ROOT / "README.md"

SCRIPT_DIRS = [
    ("DataNinja", "DataNinja"),
    ("streamyutilities", "Streamy Utilities"),
    ("sports analysis", "Sports Analysis"),
]
PLUGIN_DIR = PROJECT_ROOT / "DataNinja/plugins"

def extract_docstring(filepath):
    """Extract the top-level docstring from a Python file."""
    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()
    doc = ""
    in_doc = False
    for line in lines:
        if line.strip().startswith('"""') or line.strip().startswith("'''"):
            if not in_doc:
                in_doc = True
                doc += line.strip().strip('"\'') + "\n"
            else:
                break
        elif in_doc:
            doc += line
    return doc.strip()

def generate_docs():
    docs = ["# Project Documentation\n"]
    for dir_name, display_name in SCRIPT_DIRS:
        dir_path = PROJECT_ROOT / dir_name
        if not dir_path.exists():
            continue
        docs.append(f"## {display_name}\n")
        for root, _, files in os.walk(dir_path):
            for f in files:
                if f.endswith(".py") and not f.startswith("__"):
                    rel_path = os.path.relpath(os.path.join(root, f), PROJECT_ROOT)
                    doc = extract_docstring(os.path.join(root, f))
                    docs.append(f"### `{rel_path}`\n")
                    if doc:
                        docs.append(f"{doc}\n")
                    else:
                        docs.append("_No docstring found._\n")
    # Plugins
    if PLUGIN_DIR.exists():
        docs.append("## DataNinja Plugins\n")
        for f in PLUGIN_DIR.glob("*.py"):
            if not f.name.startswith("__"):
                rel_path = os.path.relpath(f, PROJECT_ROOT)
                doc = extract_docstring(f)
                docs.append(f"### `{rel_path}`\n")
                if doc:
                    docs.append(f"{doc}\n")
                else:
                    docs.append("_No docstring found._\n")
    # Write to README
    with open(README_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(docs))
    print(f"Documentation generated in {README_PATH}")

if __name__ == "__main__":
    generate_docs() 