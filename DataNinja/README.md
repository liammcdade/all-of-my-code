# DataNinja

DataNinja is a terminal-based data manipulation, exploration, and transformation utility designed to provide the functionality of tools like pandas, csvkit, jq, and awk — but entirely in a command-line interface, with zero Python knowledge required to use it.

It allows fast, scriptable interaction with datasets across formats (CSV, JSON, Excel, SQLite, YAML), and integrates data cleaning, basic analysis, format conversion, and visualization into a single unified CLI tool.

## Features

- Modular design for easy extension and customization
- Support for multiple data formats (CSV, JSON, Excel, SQLite, YAML)
- Data cleaning and preprocessing capabilities
- Data analysis and statistical functions
- Data visualization (ASCII plots in terminal)
- Plugin architecture for specialized tasks (e.g., machine learning, geospatial analysis, SQL)
- Fully scriptable and composable in shell pipelines

## Installation

```bash
pip install -r requirements.txt
# For SQL support:
pip install pandasql
```

## Usage

DataNinja maintains a "session" by storing your current dataset in a temporary file between commands. This allows you to chain operations.

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
- `dropna [--axis rows|columns] [--subset col1,col2] [--how any|all]`: Remove missing values.
- `fillna [--value val] [--columns col1,col2]`: Fill missing values.
- `dedup [--subset col1,col2] [--keep first|last|none]`: Remove duplicates.
- `filter <condition>`: Filter rows using pandas query syntax (e.g., `"age > 30"`).
- `select <columns>`, `rename <mapping>`, `cast <mapping>`: Manage columns.
  - Mapping format: `old:new,old2:new2` or `col:type`.
- `recode <column> <mapping>`: Map values (e.g., `"M:Male,F:Female"`).
- `trim <columns>`, `lowercase <columns>`, `normalize <columns>`.
- `groupby <by_cols> <agg_fn>`, `aggregate <agg_fn>`, `pivot <index> <cols> <vals>`.
- `sort <by_cols> [--ascending|--no-ascending]`.
- `map <column> <expression>`: Apply Python logic (e.g., `"x * 1.1"`).

### Visualization
- `plot <kind> <columns>`: Terminal ASCII plots.
  - Kinds: `histogram`, `bar`, `line`, `scatter`.
  - Options: `--bins`, `--width`, `--height`, `--save <file>`.

### Plugins
- **SQL**: `dataninja sql <query>`: Run SQL on the current data (use `data` as the table name).
- **ML**: `dataninja ml <train|predict> --target <col> [--model <path>]`.
  - Supports Logistic Regression and Random Forest (use `.rf.pkl` extension for RF).
- **Geo**: `dataninja geo <action>`.
  - `geocode --address "..."`
  - `distance --lat1 ... --lon1 ... --lat2 ... --lon2 ...`
- **Calculator (`calc`)**: Scientific math and unit conversions.
  - `sin`, `cos`, `tan`, `log`, `sqrt`, `convert`.

## Output Rendering

- Pretty tables: rich
- ASCII plots: plotext

## Development

- CLI framework: Typer
- Data backend: pandas
- File format I/O: pandas/openpyxl/sqlite3/pyyaml/json
- Rendering: rich/tabulate, plotext

## Contributing

Pull requests welcome! See issues for roadmap and feature requests.
