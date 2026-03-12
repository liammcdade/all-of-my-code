#!/usr/bin/env python3
import os
import sys
import subprocess
import argparse
from pathlib import Path

# Directories to scan for scripts
SCRIPT_DIRS = [
    ("DataNinja", "DataNinja"),
    ("sportsanalysis", "Sports Analysis"),
    ("scripts", "Utility Scripts"), # Added scripts directory
    ("extra", "Extra Scripts"),     # Added extra directory
    # ("streamyutilities", "Streamy Utilities"), # This directory does not seem to exist
]
PLUGIN_DIR = Path("DataNinja/plugins")


def list_scripts():
    """List all available scripts in the main directories and plugins."""
    scripts = []
    for dir_name, display_name in SCRIPT_DIRS:
        dir_path = Path(dir_name)
        if not dir_path.exists():
            continue
        for root, _, files in os.walk(dir_path):
            for f in files:
                if f.endswith(".py") and not f.startswith("__"):
                    scripts.append((display_name, os.path.relpath(os.path.join(root, f))))
    # Plugins
    if PLUGIN_DIR.exists():
        for f in PLUGIN_DIR.glob("*.py"):
            if not f.name.startswith("__"):
                scripts.append(("DataNinja Plugin", str(f)))
    return scripts


def run_script(script_path, script_args):
    """Run a script with the given arguments."""
    cmd = [sys.executable, script_path] + script_args
    subprocess.run(cmd)


def show_script_help(script_path):
    """Show help for a script (by running with --help or -h)."""
    try:
        subprocess.run([sys.executable, script_path, "--help"])
    except Exception:
        subprocess.run([sys.executable, script_path, "-h"])


def main():
    parser = argparse.ArgumentParser(
        description="All-in-One Codebase CLI Launcher",
        epilog="Use this tool to list, run, and get help for any script in the project."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # List scripts
    parser_list = subparsers.add_parser("list", help="List all available scripts and plugins.")

    # Run script
    parser_run = subparsers.add_parser("run", help="Run a script by name or path.")
    parser_run.add_argument("script", help="Script name or relative path (as shown in list).")
    parser_run.add_argument("args", nargs=argparse.REMAINDER, help="Arguments to pass to the script.")

    # Show help for script
    parser_help = subparsers.add_parser("help", help="Show help for a script.")
    parser_help.add_argument("script", help="Script name or relative path (as shown in list).")

    # Generate docs
    parser_docs = subparsers.add_parser("gendocs", help="Generate/refresh documentation for all scripts.")

    # Check dependencies
    parser_deps = subparsers.add_parser("checkdeps", help="Check for missing Python dependencies.")

    # Run tests/coverage
    parser_cov = subparsers.add_parser("coverage", help="Run all tests and show coverage report.")

    args = parser.parse_args()

    if args.command == "list":
        scripts = list_scripts()
        print("\nAvailable Scripts and Plugins:")
        for group, path in scripts:
            print(f"  [{group}] {path}")
        print("\nUse 'allcode.py run <script>' to run, or 'allcode.py help <script>' for help.")

    elif args.command == "run":
        scripts = list_scripts()
        # Allow running by name or path
        match = [p for g, p in scripts if args.script in p or args.script == os.path.basename(p)]
        if not match:
            print(f"Script '{args.script}' not found. Use 'allcode.py list' to see available scripts.")
            sys.exit(1)
        run_script(match[0], args.args)

    elif args.command == "help":
        scripts = list_scripts()
        match = [p for g, p in scripts if args.script in p or args.script == os.path.basename(p)]
        if not match:
            print(f"Script '{args.script}' not found. Use 'allcode.py list' to see available scripts.")
            sys.exit(1)
        show_script_help(match[0])

    elif args.command == "gendocs":
        from scripts.gendocs import generate_docs
        generate_docs()

    elif args.command == "checkdeps":
        from scripts.checkdeps import check_dependencies
        check_dependencies()

    elif args.command == "coverage":
        subprocess.run([sys.executable, "-m", "coverage", "run", "-m", "pytest"])
        subprocess.run([sys.executable, "-m", "coverage", "report", "-m"])
        subprocess.run([sys.executable, "-m", "coverage", "html"])
        print("HTML coverage report generated in 'htmlcov/index.html'.")

if __name__ == "__main__":
    main() 