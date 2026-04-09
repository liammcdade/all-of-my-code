import os
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parent.parent

EXCLUDE_DIRS = {
    ".git", "__pycache__", "node_modules", ".venv", "venv",
    "env", ".env", ".kilo", ".cache.sqlite",
    "computed_data", "sim_results", "extra",
}

CODE_EXTENSIONS = {
    ".py"
}


def is_code_file(path: Path) -> bool:
    return path.suffix.lower() in CODE_EXTENSIONS


def should_skip(dirpath: Path) -> bool:
    return any(part in EXCLUDE_DIRS for part in dirpath.parts)


def count_lines(filepath: Path) -> int:
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            return sum(1 for line in f if line.strip())
    except Exception:
        return 0


def scan_projects(root: Path) -> dict:
    results = defaultdict(lambda: {"lines": 0, "files": 0, "functions": 0, "by_ext": defaultdict(int)})

    for dirpath, dirnames, filenames in os.walk(root):
        dirpath = Path(dirpath)
        if should_skip(dirpath):
            dirnames.clear()
            continue

        # Determine project name: top-level directory under root
        rel = dirpath.relative_to(root)
        project = rel.parts[0] if rel.parts else "root"

        for fname in filenames:
            fpath = dirpath / fname
            if not is_code_file(fpath):
                continue

            lines = count_lines(fpath)
            if lines == 0:
                continue

            results[project]["lines"] += lines
            results[project]["files"] += 1
            results[project]["by_ext"][fpath.suffix.lower()] += lines

            if fpath.suffix == ".py":
                results[project]["functions"] += count_python_functions(fpath)

    return results


def count_python_functions(filepath: Path) -> int:
    count = 0
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                stripped = line.lstrip()
                if stripped.startswith("def ") or stripped.startswith("async def "):
                    count += 1
    except Exception:
        pass
    return count


def print_report(results: dict):
    total_lines = sum(p["lines"] for p in results.values())
    total_files = sum(p["files"] for p in results.values())
    total_funcs = sum(p["functions"] for p in results.values())

    print("=" * 60)
    print("  CODE PROGRESS METER — ALL PROJECTS")
    print("=" * 60)
    print()

    for project in sorted(results, key=lambda k: results[k]["lines"], reverse=True):
        data = results[project]
        print(f"  {project}")
        print(f"    Lines: {data['lines']:,}  |  Files: {data['files']}  |  Functions: {data['functions']}")

        ext_str = ", ".join(
            f"{ext}={n:,}" for ext, n in
            sorted(data["by_ext"].items(), key=lambda x: -x[1])[:5]
        )
        print(f"    Top extensions: {ext_str}")
        print()

    print("-" * 60)
    print(f"  TOTALS")
    print(f"    Lines written:  {total_lines:,}")
    print(f"    Files touched:  {total_files:,}")
    print(f"    Functions added: {total_funcs:,}  (Python only)")
    print("=" * 60)


if __name__ == "__main__":
    results = scan_projects(ROOT)
    print_report(results)
