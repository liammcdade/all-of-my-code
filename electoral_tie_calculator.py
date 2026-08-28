import csv
import sys
import re
from pathlib import Path

def is_number(value: str) -> bool:
    """Return True if the string can be parsed as a number."""
    try:
        float(value)
        return True
    except (ValueError, TypeError):
        return False

def count_numeric_cells(file_path):
    """
    Try UTF-8 first; if that fails, fall back to Latin-1.
    Returns (numeric_count, error_message) or (0, error).
    """
    for encoding in ('utf-8', 'latin-1'):
        try:
            with open(file_path, 'r', newline='', encoding=encoding) as f:
                reader = csv.reader(f)
                count = 0
                for row in reader:
                    for cell in row:
                        stripped = cell.strip()
                        if stripped and is_number(stripped):
                            count += 1
                return count, None
        except UnicodeDecodeError:
            continue
        except Exception as e:
            return 0, str(e)
    return 0, "Unsupported encoding"

def update_readme(readme_path: Path, total: int):
    """Update the README.md file with the new total number of numeric cells."""
    if not readme_path.exists():
        print(f"WARNING: {readme_path} not found – skipping update.")
        return

    content = readme_path.read_text(encoding='utf-8')

    # Pattern: prefix + the number (with optional commas)
    pattern = r'(\*\*Total data points \(numeric cells\):\*\*\s*)([\d,]+)'

    def repl(match):
        return match.group(1) + f"{total:,}"

    new_content, count = re.subn(pattern, repl, content)

    if count == 0:
        # Line not found – append it
        new_content = content.rstrip() + f"\n\n- **Total data points (numeric cells):** {total:,}\n"
        print("INFO: 'Total data points' line not found – appended to README.")
    else:
        print(f"INFO: Updated README with new total: {total:,}")

    readme_path.write_text(new_content, encoding='utf-8')

def main():
    # -------- CONFIGURATION --------
    default_dir = r"C:\Users\liam\Documents\GitHub\Footballdata"
    # -------------------------------

    if len(sys.argv) > 1:
        root_dir = sys.argv[1]
    else:
        root_dir = default_dir

    root_path = Path(root_dir)

    if not root_path.exists():
        print(f"ERROR: Folder not found: {root_dir}")
        input("Press Enter to exit...")
        return

    print(f"Scanning: {root_dir}")
    print("=" * 70)

    # Deduplicate (important on Windows)
    csv_files = list({p.resolve() for p in root_path.rglob("*.csv")})

    if not csv_files:
        print("No CSV files found.")
        input("Press Enter to exit...")
        return

    print(f"Found {len(csv_files)} CSV file(s). Processing...\n")

    grand_total = 0

    for idx, file_path in enumerate(csv_files, 1):
        count, error = count_numeric_cells(file_path)
        grand_total += count

        status = "OK" if error is None else f"ERROR: {error}"
        print(f"[{idx}/{len(csv_files)}] {file_path.name:<40} -> {count:>8} numeric cells  ({status})")

    print("\n" + "=" * 70)
    print(f"GRAND TOTAL numeric cells across all CSV files: {grand_total:,}")
    print("=" * 70)

    # ----- NEW: Update README.md -----
    readme_path = root_path / "README.md"
    update_readme(readme_path, grand_total)
    # ---------------------------------

    input("\nPress Enter to exit...")

if __name__ == "__main__":
    main()