# Documentation Audit Report: DataNinja CLI

**Date:** June 17, 2024
**Auditor:** Jules, Senior Technical Writer & Software Documentation Auditor
**Project:** DataNinja (Unified CLI for data manipulation)

---

## 1. Mismatches & Inconsistencies

### 1.1 Missing Commands in Documentation
The following commands are implemented in `DataNinja/cli.py` but are entirely absent from the `DataNinja/README.md` "Supported Commands" section:
- `schema` (Line 316): Displays column types, null counts, and unique counts.
- `summary` (Line 349): Provides field distribution and basic outlier detection for numeric columns.
- `recode` (Line 524): Recodes values in a specific column using a mapping.
- `normalize` (Line 546): Min-max normalization for numeric columns.
- `trim` (Line 566): Whitespace removal from string columns.
- `lowercase` (Line 584): Case conversion for string columns.

### 1.2 Undocumented Parameters and Options
Most commands in the README list only their primary argument (if any), ignoring significant options that alter behavior:
- `head` / `tail` / `describe`: Missing the `--output` option (values: `table`, `csv`, `json`, `silent`) and the `--n` option for row count.
- `dropna`: Missing `--axis` (`rows` or `columns`), `--subset`, and `--how` (`any` or `all`) parameters.
- `plot`: The README only lists the types, but missing `--bins`, `--width`, `--height`, `--show`, and `--save` (to file) options.
- `ml`: Missing all sub-parameters. Implemented as `dataninja ml <action> [--target <col>] [--model <file>] [--features <cols>] [--input <file>]`. Actions: `train`, `predict`.
- `geo`: Missing all sub-parameters. Implemented as `dataninja geo <action> [--address <addr>] [--lat1 <val>] ...`. Actions: `geocode`, `distance`.

### 1.3 Missing Dependency in Setup/Requirements
- **`pandasql`**: The `sql` command (Line 815) imports `pandasql`. This package is missing from both `DataNinja/requirements.txt` and `DataNinja/setup.py`, causing the command to fail in a standard installation.

### 1.4 Hardcoded Logic / Side Effects
- **ML Model Selection**: The `ml` command (Line 847) has a non-obvious feature where it switches from `LogisticRegression` to `RandomForestClassifier` if the `--model` filename ends in `.rf.pkl`. This is undocumented.
- **Session Persistence**: The README mentions "start a session" but doesn't explain that data is persisted in a temporary pickle file (`dataninja_session.pkl`) in the system temp directory between command executions.

---

## 2. Suggested Clarifications

### 2.1 Mapping Syntax
Commands like `rename`, `cast`, and `recode` use a colon-separated string for mapping (e.g., `old:new,old2:new2`). The documentation should explicitly define this format to avoid user trial-and-error.

### 2.2 Query Syntax for Filters
The `filter` command uses "pandas query syntax" (Line 460). For an audience with "zero Python knowledge," this should be explained or linked to examples like `'age > 30 and country == "UK"'`.

### 2.3 Python Expressions in Map
The `map` command (Line 705) uses Python's `eval()` on a variable `x`. This is highly flexible but requires users to understand basic Python string/numeric methods (e.g., `x.upper()` or `x * 2`), which contradicts the "zero Python knowledge" value proposition. This should be clarified or simplified.

---

## 3. Proposed Documentation Update

Below is the proposed update for the **Usage** and **Supported Commands** sections of `DataNinja/README.md`.

```markdown
## Installation

```bash
pip install -r requirements.txt
# For SQL support:
pip install pandasql
```

## Usage

DataNinja maintains a "session" by storing your current dataset in a temporary file. This allows you to chain operations.

1. **Load data**: `dataninja load data.csv`
2. **Transform**: `dataninja filter "age > 25"`
3. **Clean**: `dataninja trim name`
4. **Inspect**: `dataninja summary`
5. **Save**: `dataninja save cleaned_data.json`

### Output Options
Most inspection commands (`head`, `tail`, `describe`) support an `--output` option:
- `table` (Default): Pretty-printed table for terminal viewing.
- `csv` / `json`: Raw data for piping to other tools.

## Supported Commands

### Data Inspection
- `load <file>`: Load a dataset (CSV, JSON, Excel, SQLite, YAML).
- `head [--n 10]`, `tail [--n 10]`: View first/last rows.
- `info`, `describe`, `schema`, `summary`: Statistical and structural summaries.

### Cleaning & Transformation
- `dropna [--axis rows|columns] [--subset col1,col2]`: Remove missing values.
- `fillna [--value val] [--columns col1,col2]`: Fill missing values.
- `dedup [--subset col1,col2] [--keep first|last|none]`: Remove duplicates.
- `filter <condition>`: Filter rows (e.g., `"age > 30"`).
- `select <columns>`, `rename <mapping>`, `cast <mapping>`: Manage columns.
- `recode <column> <mapping>`: Change values (e.g., `"M:Male,F:Female"`).
- `trim <columns>`, `lowercase <columns>`, `normalize <columns>`.
- `groupby <by_cols> <agg_fn>`, `aggregate <agg_fn>`, `pivot <index> <cols> <vals>`.
- `sort <by_cols> [--ascending|--no-ascending]`.
- `map <column> <expression>`: Apply Python logic (e.g., `"x * 1.1"`).

### Visualization
- `plot <kind> <columns>`: Terminal ASCII plots.
  - Kinds: `histogram`, `bar`, `line`, `scatter`.
  - Options: `--bins`, `--width`, `--height`, `--save <file>`.

### Plugins
- **SQL**: `dataninja sql "SELECT * FROM data WHERE ..."` (Uses `data` as table name).
- **ML**: `dataninja ml <train|predict> --target <col> [--model <path>]`.
  - Supports Logistic Regression and Random Forest (use `.rf.pkl` extension).
- **Geo**: `dataninja geo <geocode|distance>`.
  - `geocode --address "..."`
  - `distance --lat1 ... --lon1 ... --lat2 ... --lon2 ...`
- **Calculator (`calc`)**: Scientific math and unit conversions.
  - `sin`, `cos`, `tan`, `log`, `sqrt`, `convert`.
```
