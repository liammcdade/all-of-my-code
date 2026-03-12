import os
import importlib.util
from pathlib import Path

PLUGIN_DIR = Path(__file__).resolve().parent.parent / "DataNinja/plugins"

def discover_plugins():
    plugins = []
    if PLUGIN_DIR.exists():
        for f in PLUGIN_DIR.glob("*.py"):
            if not f.name.startswith("__"):
                plugins.append(f)
    return plugins

def load_plugin(plugin_path):
    spec = importlib.util.spec_from_file_location(plugin_path.stem, plugin_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def run_plugin(plugin_name, *args):
    for plugin_path in discover_plugins():
        if plugin_name in plugin_path.name:
            mod = load_plugin(plugin_path)
            if hasattr(mod, "main"):
                return mod.main(*args)
            else:
                print(f"Plugin {plugin_name} has no 'main' function.")
                return None
    print(f"Plugin {plugin_name} not found.")
    return None 