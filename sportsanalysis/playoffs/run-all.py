"""Run every playoff league simulation in this directory and print their results.

Each league script (championship.py, league-1.py, league-2.py, ...) is executed
as an isolated subprocess so its own namespace and random state stay clean. The
tqdm progress bars stream live on stderr, while each script's stdout (its printed
tables, stats and reports) is captured and echoed here after that league finishes.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

PLAYOFFS_DIR = Path(__file__).resolve().parent
PREMIER_LEAGUE_DIR = PLAYOFFS_DIR.parent / "premier-league"
PREMIER_LEAGUE_SCRIPT = PREMIER_LEAGUE_DIR / "26-27-season.py"
EXCLUDE_FILES = frozenset({"run-all.py", "__init__.py"})


def discover_league_scripts() -> list[Path]:
    """Return all runnable league scripts to execute.

    Playoff league scripts are discovered in this directory. The Premier
    League season simulation lives in its own package and is appended
    explicitly (its directory also contains non-simulation files such as
    ``modules.py`` and ``fpl.py`` that must not be executed here).
    """
    scripts: list[Path] = []
    for path in sorted(PLAYOFFS_DIR.glob("*.py")):
        if path.name in EXCLUDE_FILES or path.name.startswith("_"):
            continue
        scripts.append(path)
    if PREMIER_LEAGUE_SCRIPT.is_file():
        scripts.append(PREMIER_LEAGUE_SCRIPT)
    return scripts


def run_league(script: Path) -> str:
    """Run a single league script, returning its captured stdout.

    Each script runs from its own directory so local imports (e.g. the
    Premier League's ``modules``) resolve correctly. stderr (tqdm
    progress bars) is inherited so the bars stream live.
    """
    result = subprocess.run(
        [sys.executable, str(script)],
        cwd=script.parent,
        stdout=subprocess.PIPE,
        text=True,
    )
    if result.returncode != 0:
        sys.stderr.write(
            f"ERROR running {script.name} (exit {result.returncode})\n"
        )
    return result.stdout


def _extract_table_solved(output: str) -> float | None:
    """Extract the 'Combined table solved %' value from a league's stdout.

    Returns the percentage as a float (0-100), or None if the line is absent.
    """
    for line in output.splitlines():
        stripped = line.strip()
        if stripped.startswith("Combined table solved %:"):
            value_str = stripped.split(":", 1)[-1].strip().rstrip("%")
            try:
                return float(value_str)
            except ValueError:
                return None
    return None


def _print_overall_solved(
    outputs: list[tuple[str, str]],
) -> None:
    """Multiply all leagues' 'Combined table solved %' and print."""
    print("=" * 80)
    print("OVERALL TABLE SOLVED — ALL LEAGUES MULTIPLIED TOGETHER")
    print("=" * 80)

    overall = 1.0
    found = False
    for name, output in outputs:
        solved = _extract_table_solved(output)
        if solved is None:
            print(f"  {name}: (no 'Combined table solved %' found)")
            continue
        found = True
        print(f"  {name}: {solved:.20e}%")
        overall *= solved / 100.0

    if not found:
        print("  No 'Combined table solved %' found in any output.")
        return

    print(
        f"\n  Overall multiplied table solved %: {overall * 100:.20e}%"
    )


def main() -> None:
    """Run each league in turn and print all of its output."""
    scripts = discover_league_scripts()
    if not scripts:
        print("No league scripts found in the playoffs directory.")
        return

    outputs: list[tuple[str, str]] = []

    for script in scripts:
        print("=" * 80)
        print(f"Running {script.name}")
        print("=" * 80)
        output = run_league(script)
        print(output, end="")
        print()
        outputs.append((script.name, output))

    _print_overall_solved(outputs)


if __name__ == "__main__":
    main()
