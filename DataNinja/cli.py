import typer
import pandas as pd
import os
import sys
import tempfile
import pickle
from pathlib import Path
from typing import Optional, List
from rich.console import Console
from rich.table import Table
from rich import box
import plotext as plt
import numpy as np

# Import format handlers
from DataNinja.formats.csv_handler import CSVHandler
from DataNinja.formats.json_handler import JSONHandler
from DataNinja.formats.excel_handler import ExcelHandler
from DataNinja.formats.sqlite_handler import SQLiteHandler
from DataNinja.formats.yaml_handler import YAMLHandler
from DataNinja.core.cleaner import DataCleaner
from DataNinja.plugins.geo import GeoProcessor
from DataNinja.plugins.ml import MLModel
from DataNinja.plugins.sql import SQLProcessor
from DataNinja.plugins.calculator import CalculatorProcessor # Import Calculator

app = typer.Typer(
    help="DataNinja: Unified CLI for data manipulation, cleaning, analysis, and visualization."
)
calc_app = typer.Typer(help="Scientific and unit conversion calculator.")
app.add_typer(calc_app, name="calc")

console = Console()

# Session management: store DataFrame in a temp file between commands
SESSION_FILE = os.path.join(tempfile.gettempdir(), "dataninja_session.pkl")


def save_session(df):
    with open(SESSION_FILE, "wb") as f:
        pickle.dump(df, f)


def load_session():
    if os.path.exists(SESSION_FILE):
        with open(SESSION_FILE, "rb") as f:
            return pickle.load(f)
    else:
        return None


def clear_session():
    if os.path.exists(SESSION_FILE):
        os.remove(SESSION_FILE)


def detect_format(filepath):
    ext = Path(filepath).suffix.lower()
    if ext in [".csv", ".tsv"]:
        return "csv"
    elif ext == ".json":
        return "json"
    elif ext in [".xlsx", ".xls"]:
        return "excel"
    elif ext in [".sqlite", ".db"]:
        return "sqlite"
    elif ext == ".yaml":
        return "yaml"
    # elif ext == ".xml":
    #     return "xml"
    else:
        return None


def load_data(filepath, **kwargs):
    fmt = detect_format(filepath)
    if fmt == "csv":
        return CSVHandler(filepath).load_data(**kwargs)
    elif fmt == "json":
        return JSONHandler(filepath).load_data(**kwargs)
    elif fmt == "excel":
        return ExcelHandler(filepath).load_data(**kwargs)
    elif fmt == "sqlite":
        # For now, load first table
        handler = SQLiteHandler(filepath)
        import sqlite3

        with sqlite3.connect(filepath) as conn:
            tables = pd.read_sql(
                "SELECT name FROM sqlite_master WHERE type='table'", conn
            )
            if not tables.empty:
                table_name = tables.iloc[0, 0]
                return handler.load_data(table_name=table_name)
            else:
                raise typer.Exit("No tables found in SQLite DB.")
    elif fmt == "yaml":
        return YAMLHandler(filepath).load_data(**kwargs)
    else:
        raise typer.Exit(f"Unsupported file format: {filepath}")


def save_data(df, filepath):
    fmt = detect_format(filepath)
    if fmt == "csv":
        return CSVHandler(filepath).save_data(df, target_path=filepath)
    elif fmt == "json":
        return JSONHandler(filepath).save_data(df, target_path=filepath)
    elif fmt == "excel":
        return ExcelHandler(filepath).save_data(df, target_path=filepath)
    elif fmt == "sqlite":
        # Save to table named 'data' by default
        return SQLiteHandler(filepath).save_data(
            df, table_name="data", if_exists="replace"
        )
    elif fmt == "yaml":
        return YAMLHandler(filepath).save_data(df, target_path=filepath)
    else:
        raise typer.Exit(f"Unsupported file format for saving: {filepath}")


# --- CLI Commands ---
@app.command()
def load(
    file: str = typer.Argument(
        ..., help="Input data file (csv, json, xlsx, sqlite, yaml)"
    ),
):
    """Load a data file and start a session."""
    df = load_data(file)
    save_session(df)
    console.print(f"[bold green]Loaded:[/bold green] {file}")
    # Show preview
    head_df = df.head(10)
    table = Table(show_header=True, header_style="bold magenta", box=box.SIMPLE)
    for col in head_df.columns:
        table.add_column(str(col))
    for _, row in head_df.iterrows():
        table.add_row(*[str(x) for x in row])
    console.print(table)
    console.print(
        f"[cyan]Shape:[/cyan] {df.shape}, [cyan]Columns:[/cyan] {list(df.columns)}"
    )


@app.command()
def head(
    n: int = typer.Option(10, help="Number of rows to show"),
    output: str = typer.Option("table", help="Output mode: table, csv, json, silent"),
):
    """Show the first N rows of the current session."""
    df = load_session()
    if df is None:
        console.print("[red]No data loaded. Use 'dataninja load <file>' first.")
        raise typer.Exit()
    dfh = df.head(n)
    if output == "table":
        table = Table(show_header=True, header_style="bold magenta", box=box.SIMPLE)
        for col in dfh.columns:
            table.add_column(str(col))
        for _, row in dfh.iterrows():
            table.add_row(*[str(x) for x in row])
        console.print(table)
    elif output == "csv":
        typer.echo(dfh.to_csv(index=False))
    elif output == "json":
        typer.echo(dfh.to_json(orient="records"))
    elif output == "silent":
        pass
    else:
        console.print(f"[red]Unknown output mode: {output}")


@app.command()
def info():
    """Show info about the current session DataFrame, including dtypes, nulls, unique, and field distribution."""
    df = load_session()
    if df is None:
        console.print("[red]No data loaded. Use 'dataninja load <file>' first.")
        raise typer.Exit()
    # Show DataFrame info
    buf = []
    import io

    sio = io.StringIO()
    df.info(buf=sio)
    sio.seek(0)
    console.print(sio.read())
    console.print(f"[cyan]Shape:[/cyan] {df.shape}")
    console.print(f"[cyan]Columns:[/cyan] {list(df.columns)}")
    console.print(f"[cyan]Dtypes:[/cyan] {df.dtypes.to_dict()}")
    # Show nulls and unique counts
    table = Table(show_header=True, header_style="bold magenta", box=box.SIMPLE)
    table.add_column("Column")
    table.add_column("Nulls")
    table.add_column("Unique")
    for col in df.columns:
        table.add_row(str(col), str(df[col].isnull().sum()), str(df[col].nunique()))
    console.print(table)
    # Show field distribution for first 3 columns
    for col in df.columns[:3]:
        console.print(f"[bold]{col}[/bold] value counts:")
        vc = df[col].value_counts(dropna=False).head(5)
        for idx, cnt in vc.items():
            console.print(f"  {repr(idx)}: {cnt}")
        if df[col].nunique() > 5:
            console.print(f"  ... ({df[col].nunique()-5} more)")


@app.command()
def save(
    output: str = typer.Argument(
        ..., help="Output file path (csv, json, xlsx, sqlite, yaml)"
    ),
):
    """Save the current session DataFrame to a file."""
    df = load_session()
    if df is None:
        console.print("[red]No data loaded. Use 'dataninja load <file>' first.")
        raise typer.Exit()
    save_data(df, output)
    console.print(f"[green]Saved to:[/green] {output}")


@app.command()
def convert(
    input: str = typer.Argument(..., help="Input file (csv, json, xlsx, sqlite, yaml)"),
    output: str = typer.Argument(
        ..., help="Output file (csv, json, xlsx, sqlite, yaml)"
    ),
):
    """Convert between supported file formats."""
    df = load_data(input)
    save_data(df, output)
    console.print(f"[green]Converted {input} -> {output}")


@app.command()
def tail(
    n: int = typer.Option(10, help="Number of rows to show"),
    output: str = typer.Option("table", help="Output mode: table, csv, json, silent"),
):
    """Show the last N rows of the current session."""
    df = load_session()
    if df is None:
        console.print("[red]No data loaded. Use 'dataninja load <file>' first.")
        raise typer.Exit()
    dft = df.tail(n)
    if output == "table":
        table = Table(show_header=True, header_style="bold magenta", box=box.SIMPLE)
        for col in dft.columns:
            table.add_column(str(col))
        for _, row in dft.iterrows():
            table.add_row(*[str(x) for x in row])
        console.print(table)
    elif output == "csv":
        typer.echo(dft.to_csv(index=False))
    elif output == "json":
        typer.echo(dft.to_json(orient="records"))
    elif output == "silent":
        pass
    else:
        console.print(f"[red]Unknown output mode: {output}")


@app.command()
def describe(
    output: str = typer.Option("table", help="Output mode: table, csv, json, silent"),
):
    """Show summary statistics of the current session."""
    df = load_session()
    if df is None:
        console.print("[red]No data loaded. Use 'dataninja load <file>' first.")
        raise typer.Exit()
    desc = df.describe(include="all").fillna("")
    if output == "table":
        table = Table(show_header=True, header_style="bold magenta", box=box.SIMPLE)
        table.add_column("stat")
        for col in desc.columns:
            table.add_column(str(col))
        for idx, row in desc.iterrows():
            table.add_row(str(idx), *[str(x) for x in row])
        console.print(table)
    elif output == "csv":
        typer.echo(desc.to_csv())
    elif output == "json":
        typer.echo(desc.to_json())
    elif output == "silent":
        pass
    else:
        console.print(f"[red]Unknown output mode: {output}")


@app.command()
def schema():
    """Show schema (column names, types, null counts, unique counts) of the current session."""
    df = load_session()
    if df is None:
        console.print("[red]No data loaded. Use 'dataninja load <file>' first.")
        raise typer.Exit()
    table = Table(show_header=True, header_style="bold magenta", box=box.SIMPLE)
    table.add_column("Column")
    table.add_column("Type")
    table.add_column("Nulls")
    table.add_column("Unique")
    for col in df.columns:
        table.add_row(
            str(col),
            str(df[col].dtype),
            str(df[col].isnull().sum()),
            str(df[col].nunique()),
        )
    console.print(table)


@app.command()
def summary():
    """Show field distribution summaries and basic outlier detection."""
    df = load_session()
    if df is None:
        console.print("[red]No data loaded. Use 'dataninja load <file>' first.")
        raise typer.Exit()
    for col in df.columns:
        console.print(f"[bold]{col}[/bold] (type: {df[col].dtype})")
        if pd.api.types.is_numeric_dtype(df[col]):
            vals = df[col].dropna()
            if not vals.empty:
                q1 = vals.quantile(0.25)
                q3 = vals.quantile(0.75)
                iqr = q3 - q1
                lower = q1 - 1.5 * iqr
                upper = q3 + 1.5 * iqr
                outliers = vals[(vals < lower) | (vals > upper)]
                console.print(
                    f"  min: {vals.min()}, max: {vals.max()}, mean: {vals.mean():.2f}, std: {vals.std():.2f}, median: {vals.median()} (outliers: {len(outliers)})"
                )
            else:
                console.print("  No numeric data.")
        else:
            vc = df[col].value_counts(dropna=False)
            top = vc.head(5)
            for idx, cnt in top.items():
                console.print(f"  {repr(idx)}: {cnt}")
            if len(vc) > 5:
                console.print(f"  ... ({len(vc)-5} more)")
        console.print("")


@app.command()
def dropna(
    axis: str = typer.Option("rows", help="Drop missing data from 'rows' or 'columns'"),
    subset: Optional[str] = typer.Option(
        None, help="Comma-separated columns to consider for NA"
    ),
    how: str = typer.Option("any", help="'any' or 'all' NAs to drop"),
):
    """Drop rows or columns with missing data."""
    df = load_session()
    if df is None:
        console.print("[red]No data loaded. Use 'dataninja load <file>' first.")
        raise typer.Exit()
    axis_num = 0 if axis == "rows" else 1
    subset_cols = [c.strip() for c in subset.split(",")] if subset else None
    df2 = df.dropna(axis=axis_num, how=how, subset=subset_cols)
    save_session(df2)
    console.print(f"[green]Dropped NA from {axis} (how={how}, subset={subset_cols})")
    head(n=10)


@app.command()
def fillna(
    value: Optional[str] = typer.Option(
        None, help="Value to fill NA with (or 'mean', 'median', 'mode')"
    ),
    columns: Optional[str] = typer.Option(None, help="Comma-separated columns to fill"),
):
    """Fill missing values."""
    df = load_session()
    if df is None:
        console.print("[red]No data loaded. Use 'dataninja load <file>' first.")
        raise typer.Exit()
    cols = [c.strip() for c in columns.split(",")] if columns else df.columns
    df2 = df.copy()
    for col in cols:
        if value == "mean" and pd.api.types.is_numeric_dtype(df2[col]):
            df2[col] = df2[col].fillna(df2[col].mean())
        elif value == "median" and pd.api.types.is_numeric_dtype(df2[col]):
            df2[col] = df2[col].fillna(df2[col].median())
        elif value == "mode":
            mode_val = df2[col].mode().iloc[0] if not df2[col].mode().empty else None
            df2[col] = df2[col].fillna(mode_val)
        else:
            df2[col] = df2[col].fillna(value)
    save_session(df2)
    console.print(f"[green]Filled NA in columns {cols} with '{value}'")
    head(n=10)


@app.command()
def dedup(
    subset: Optional[str] = typer.Option(
        None, help="Comma-separated columns to consider for duplicates"
    ),
    keep: str = typer.Option(
        "first", help="Which duplicates to keep: 'first', 'last', or 'none'"
    ),
):
    """Remove duplicate rows."""
    df = load_session()
    if df is None:
        console.print("[red]No data loaded. Use 'dataninja load <file>' first.")
        raise typer.Exit()
    subset_cols = [c.strip() for c in subset.split(",")] if subset else None
    keep_val = False if keep == "none" else keep
    df2 = df.drop_duplicates(subset=subset_cols, keep=keep_val)
    save_session(df2)
    console.print(f"[green]Removed duplicates (subset={subset_cols}, keep={keep})")
    head(n=10)


@app.command()
def filter(
    where: str = typer.Argument(
        ..., help="Filter condition, e.g. 'age > 30 and country == \"UK\"'"
    ),
):
    """Filter rows by condition (pandas query syntax)."""
    df = load_session()
    if df is None:
        console.print("[red]No data loaded. Use 'dataninja load <file>' first.")
        raise typer.Exit()
    try:
        df2 = df.query(where)
    except Exception as e:
        console.print(f"[red]Query error: {e}")
        raise typer.Exit()
    save_session(df2)
    console.print(f"[green]Filtered rows where: {where}")
    head(n=10)


@app.command()
def select(
    columns: str = typer.Argument(
        ..., help="Comma-separated columns to select, e.g. 'name,age'"
    ),
):
    """Select columns."""
    df = load_session()
    if df is None:
        console.print("[red]No data loaded. Use 'dataninja load <file>' first.")
        raise typer.Exit()
    cols = [c.strip() for c in columns.split(",")]
    df2 = df[cols]
    save_session(df2)
    console.print(f"[green]Selected columns: {cols}")
    head(n=10)


@app.command()
def rename(
    mapping: str = typer.Argument(
        ..., help="Rename columns, e.g. 'old1:new1,old2:new2'"
    ),
):
    """Rename columns."""
    df = load_session()
    if df is None:
        console.print("[red]No data loaded. Use 'dataninja load <file>' first.")
        raise typer.Exit()
    pairs = [m.split(":") for m in mapping.split(",")]
    rename_dict = {old: new for old, new in pairs}
    df2 = df.rename(columns=rename_dict)
    save_session(df2)
    console.print(f"[green]Renamed columns: {rename_dict}")
    head(n=10)


@app.command()
def cast(
    mapping: str = typer.Argument(
        ..., help="Cast columns, e.g. 'age:int,salary:float'"
    ),
):
    """Change column types."""
    df = load_session()
    if df is None:
        console.print("[red]No data loaded. Use 'dataninja load <file>' first.")
        raise typer.Exit()
    pairs = [m.split(":") for m in mapping.split(",")]
    cast_dict = {col: typ for col, typ in pairs}
    df2 = df.copy()
    for col, typ in cast_dict.items():
        try:
            df2[col] = df2[col].astype(typ)
        except Exception as e:
            console.print(f"[red]Cast error for {col}: {e}")
    save_session(df2)
    console.print(f"[green]Casted columns: {cast_dict}")
    head(n=10)


@app.command()
def recode(
    column: str = typer.Argument(..., help="Column to recode"),
    mapping: str = typer.Argument(
        ..., help="Recode mapping, e.g. 'old1:new1,old2:new2'"
    ),
):
    """Recode values in a column."""
    df = load_session()
    if df is None:
        console.print("[red]No data loaded. Use 'dataninja load <file>' first.")
        raise typer.Exit()
    pairs = [m.split(":") for m in mapping.split(",")]
    recode_dict = {old: new for old, new in pairs}
    df2 = df.copy()
    df2[column] = df2[column].replace(recode_dict)
    save_session(df2)
    console.print(f"[green]Recoded column {column}: {recode_dict}")
    head(n=10)


@app.command()
def normalize(
    columns: str = typer.Argument(
        ..., help="Comma-separated columns to normalize (min-max)"
    ),
):
    """Normalize columns to 0-1 range."""
    df = load_session()
    if df is None:
        console.print("[red]No data loaded. Use 'dataninja load <file>' first.")
        raise typer.Exit()
    cols = [c.strip() for c in columns.split(",")]
    df2 = df.copy()
    for col in cols:
        minv = df2[col].min()
        maxv = df2[col].max()
        df2[col] = (df2[col] - minv) / (maxv - minv)
    save_session(df2)
    console.print(f"[green]Normalized columns: {cols}")
    head(n=10)


@app.command()
def trim(
    columns: str = typer.Argument(
        ..., help="Comma-separated columns to trim whitespace"
    ),
):
    """Trim whitespace from string columns."""
    df = load_session()
    if df is None:
        console.print("[red]No data loaded. Use 'dataninja load <file>' first.")
        raise typer.Exit()
    cols = [c.strip() for c in columns.split(",")]
    df2 = df.copy()
    for col in cols:
        df2[col] = df2[col].astype(str).str.strip()
    save_session(df2)
    console.print(f"[green]Trimmed whitespace in columns: {cols}")
    head(n=10)


@app.command()
def lowercase(
    columns: str = typer.Argument(..., help="Comma-separated columns to lowercase"),
):
    """Convert string columns to lowercase."""
    df = load_session()
    if df is None:
        console.print("[red]No data loaded. Use 'dataninja load <file>' first.")
        raise typer.Exit()
    cols = [c.strip() for c in columns.split(",")]
    df2 = df.copy()
    for col in cols:
        df2[col] = df2[col].astype(str).str.lower()
    save_session(df2)
    console.print(f"[green]Lowercased columns: {cols}")
    head(n=10)


@app.command()
def groupby(
    by: str = typer.Argument(..., help="Comma-separated columns to group by"),
    agg: str = typer.Argument(
        ..., help="Aggregation, e.g. 'sum', 'mean', 'count', or col:agg,col2:agg2"
    ),
):
    """Group data and aggregate."""
    df = load_session()
    if df is None:
        console.print("[red]No data loaded. Use 'dataninja load <file>' first.")
        raise typer.Exit()
    by_cols = [c.strip() for c in by.split(",")]
    if ":" in agg:
        agg_dict = {k: v for k, v in (a.split(":") for a in agg.split(","))}
    else:
        agg_dict = agg
    df2 = df.groupby(by_cols).agg(agg_dict).reset_index()
    save_session(df2)
    console.print(f"[green]Grouped by {by_cols} with aggregation {agg_dict}")
    head(n=10)


@app.command()
def aggregate(
    agg: str = typer.Argument(
        ..., help="Aggregation, e.g. 'sum', 'mean', 'count', or col:agg,col2:agg2"
    ),
):
    """Aggregate data (no groupby)."""
    df = load_session()
    if df is None:
        console.print("[red]No data loaded. Use 'dataninja load <file>' first.")
        raise typer.Exit()
    if ":" in agg:
        agg_dict = {k: v for k, v in (a.split(":") for a in agg.split(","))}
    else:
        agg_dict = agg
    df2 = df.agg(agg_dict)
    console.print(df2)


@app.command()
def pivot(
    index: str = typer.Argument(..., help="Index column(s) (comma-separated)"),
    columns: str = typer.Argument(..., help="Columns to pivot (comma-separated)"),
    values: str = typer.Argument(..., help="Values column(s) (comma-separated)"),
):
    """Pivot table."""
    df = load_session()
    if df is None:
        console.print("[red]No data loaded. Use 'dataninja load <file>' first.")
        raise typer.Exit()
    idx = [c.strip() for c in index.split(",")]
    cols = [c.strip() for c in columns.split(",")]
    vals = [c.strip() for c in values.split(",")]
    df2 = df.pivot_table(
        index=idx, columns=cols, values=vals, aggfunc="mean"
    ).reset_index()
    save_session(df2)
    console.print(f"[green]Pivoted table (index={idx}, columns={cols}, values={vals})")
    head(n=10)


@app.command()
def splitcol(
    column: str = typer.Argument(..., help="Column to split"),
    sep: str = typer.Argument(..., help="Separator or regex"),
    into: str = typer.Argument(..., help="Comma-separated new column names"),
):
    """Split a column into multiple columns."""
    df = load_session()
    if df is None:
        console.print("[red]No data loaded. Use 'dataninja load <file>' first.")
        raise typer.Exit()
    new_cols = [c.strip() for c in into.split(",")]
    splits = df[column].astype(str).str.split(sep, expand=True)
    splits.columns = new_cols
    df2 = df.drop(columns=[column]).join(splits)
    save_session(df2)
    console.print(f"[green]Split column {column} into {new_cols}")
    head(n=10)


@app.command()
def mergecols(
    columns: str = typer.Argument(..., help="Comma-separated columns to merge"),
    sep: str = typer.Argument("_", help="Separator for merged values"),
    new: str = typer.Argument(..., help="Name of new column"),
):
    """Merge columns into a single column."""
    df = load_session()
    if df is None:
        console.print("[red]No data loaded. Use 'dataninja load <file>' first.")
        raise typer.Exit()
    cols = [c.strip() for c in columns.split(",")]
    df2 = df.copy()
    df2[new] = df2[cols].astype(str).agg(sep.join, axis=1)
    df2 = df2.drop(columns=cols)
    save_session(df2)
    console.print(f"[green]Merged columns {cols} into {new}")
    head(n=10)


@app.command()
def sort(
    by: str = typer.Argument(..., help="Comma-separated columns to sort by"),
    ascending: bool = typer.Option(True, help="Sort ascending (default True)"),
):
    """Sort rows by column(s)."""
    df = load_session()
    if df is None:
        console.print("[red]No data loaded. Use 'dataninja load <file>' first.")
        raise typer.Exit()
    by_cols = [c.strip() for c in by.split(",")]
    df2 = df.sort_values(by=by_cols, ascending=ascending)
    save_session(df2)
    console.print(f"[green]Sorted by {by_cols} (ascending={ascending})")
    head(n=10)


@app.command()
def map(
    column: str = typer.Argument(..., help="Column to map"),
    expr: str = typer.Argument(
        ..., help="Python expression, e.g. 'x*2' or 'x.upper()'"
    ),
):
    """Apply a mapping expression to a column."""
    df = load_session()
    if df is None:
        console.print("[red]No data loaded. Use 'dataninja load <file>' first.")
        raise typer.Exit()
    df2 = df.copy()
    try:
        df2[column] = df2[column].apply(lambda x: eval(expr, {"x": x}))
    except Exception as e:
        console.print(f"[red]Map error: {e}")
        raise typer.Exit()
    save_session(df2)
    console.print(f"[green]Mapped column {column} with '{expr}'")
    head(n=10)


@app.command()
def sample(
    n: int = typer.Option(5, help="Number of rows to sample"),
    frac: Optional[float] = typer.Option(
        None, help="Fraction of rows to sample (overrides n)"
    ),
    random_state: Optional[int] = typer.Option(None, help="Random seed"),
):
    """Sample rows."""
    df = load_session()
    if df is None:
        console.print("[red]No data loaded. Use 'dataninja load <file>' first.")
        raise typer.Exit()
    if frac is not None:
        df2 = df.sample(frac=frac, random_state=random_state)
    else:
        df2 = df.sample(n=n, random_state=random_state)
    save_session(df2)
    console.print(f"[green]Sampled rows (n={n}, frac={frac})")
    head(n=10)


@app.command()
def split(
    frac: float = typer.Argument(0.8, help="Fraction for training set (rest is test)"),
    shuffle: bool = typer.Option(True, help="Shuffle before splitting"),
    random_state: Optional[int] = typer.Option(None, help="Random seed"),
):
    """Split into training/test sets."""
    df = load_session()
    if df is None:
        console.print("[red]No data loaded. Use 'dataninja load <file>' first.")
        raise typer.Exit()
    df2 = df.sample(frac=1, random_state=random_state) if shuffle else df
    n_train = int(len(df2) * frac)
    train = df2.iloc[:n_train]
    test = df2.iloc[n_train:]
    # Save both to temp files
    train_path = os.path.join(tempfile.gettempdir(), "dataninja_train.csv")
    test_path = os.path.join(tempfile.gettempdir(), "dataninja_test.csv")
    train.to_csv(train_path, index=False)
    test.to_csv(test_path, index=False)
    console.print(
        f"[green]Split: train ({len(train)}) -> {train_path}, test ({len(test)}) -> {test_path}"
    )


@app.command()
def plot(
    kind: str = typer.Argument(..., help="Plot type: histogram, bar, line, scatter"),
    columns: str = typer.Argument(
        ..., help="Column(s) to plot (comma-separated, e.g. 'age' or 'age,salary')"
    ),
    bins: int = typer.Option(10, help="Number of bins for histogram"),
    width: int = typer.Option(80, help="Plot width in characters"),
    height: int = typer.Option(20, help="Plot height in characters"),
    show: bool = typer.Option(True, help="Show plot in terminal (default True)"),
    save: Optional[str] = typer.Option(None, help="Save plot to file (txt or png)"),
):
    """Plot data (histogram, bar, line, scatter) in ASCII in the terminal."""
    df = load_session()
    if df is None:
        console.print("[red]No data loaded. Use 'dataninja load <file>' first.")
        raise typer.Exit()
    cols = [c.strip() for c in columns.split(",")]
    plt.clf()
    plt.plotsize(width, height)
    if kind == "histogram":
        col = cols[0]
        plt.hist(df[col].dropna(), bins=bins, label=col)
        plt.title(f"Histogram of {col}")
    elif kind == "bar":
        x, y = cols[0], cols[1] if len(cols) > 1 else None
        if y:
            plt.bar(df[x].astype(str), df[y], label=f"{y} by {x}")
            plt.title(f"Bar plot: {y} by {x}")
        else:
            vc = df[x].value_counts()
            plt.bar(vc.index.astype(str), vc.values, label=x)
            plt.title(f"Bar plot: {x}")
    elif kind == "line":
        x, y = cols[0], cols[1] if len(cols) > 1 else None
        if y:
            plt.plot(df[x], df[y], label=f"{y} vs {x}")
            plt.title(f"Line plot: {y} vs {x}")
        else:
            plt.plot(df[x], label=x)
            plt.title(f"Line plot: {x}")
    elif kind == "scatter":
        x, y = cols[0], cols[1]
        plt.scatter(df[x], df[y], label=f"{y} vs {x}")
        plt.title(f"Scatter plot: {y} vs {x}")
    else:
        console.print(f"[red]Unknown plot kind: {kind}")
        raise typer.Exit()
    plt.legend(True)
    if save:
        plt.savefig(save)
        console.print(f"[green]Plot saved to {save}")
    if show:
        plt.show()


@app.command()
def sql(
    query: str = typer.Argument(
        ..., help="SQL query to run on the current data (use 'data' as the table name)"
    ),
):
    """Run SQL queries on the data (use 'data' as the table name)."""
    df = load_session()
    if df is None:
        console.print("[red]No data loaded. Use 'dataninja load <file>' first.")
        raise typer.Exit()
    try:
        import pandasql
    except ImportError:
        console.print(
            "[red]pandasql is required for SQL queries. Install with 'pip install pandasql'."
        )
        raise typer.Exit()
    pysqldf = lambda q: pandasql.sqldf(q, {"data": df})
    try:
        result = pysqldf(query)
    except Exception as e:
        console.print(f"[red]SQL error: {e}")
        raise typer.Exit()
    save_session(result)
    console.print(f"[green]SQL query executed. Result:")
    head(n=10)


@app.command()
def ml(
    action: str = typer.Argument(..., help="Action: train or predict"),
    target: Optional[str] = typer.Option(None, help="Target column for training"),
    model: Optional[str] = typer.Option(None, help="Model file to save/load"),
    features: Optional[str] = typer.Option(
        None, help="Comma-separated feature columns (default: all except target)"
    ),
    input: Optional[str] = typer.Option(
        None, help="Input file for prediction (if not using session)"
    ),
):
    """Machine learning: train or predict (LogisticRegression, RandomForest)."""
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.linear_model import LogisticRegression
    import pickle

    if action == "train":
        df = load_session()
        if df is None:
            console.print("[red]No data loaded. Use 'dataninja load <file>' first.")
            raise typer.Exit()
        if not target:
            console.print("[red]Specify --target for training.")
            raise typer.Exit()
        X = (
            df.drop(columns=[target])
            if not features
            else df[[c.strip() for c in features.split(",")]]
        )
        y = df[target]
        model_obj = (
            RandomForestClassifier()
            if model and model.endswith(".rf.pkl")
            else LogisticRegression()
        )
        model_obj.fit(X, y)
        model_path = model or "dataninja_model.pkl"
        with open(model_path, "wb") as f:
            pickle.dump(model_obj, f)
        console.print(f"[green]Model trained and saved to {model_path}")
    elif action == "predict":
        model_path = model or "dataninja_model.pkl"
        with open(model_path, "rb") as f:
            model_obj = pickle.load(f)
        if input:
            df = load_data(input)
        else:
            df = load_session()
        X = df if not features else df[[c.strip() for c in features.split(",")]]
        preds = model_obj.predict(X)
        df2 = df.copy()
        df2["prediction"] = preds
        save_session(df2)
        console.print(f"[green]Predictions added to session DataFrame.")
        head(n=10)
    else:
        console.print("[red]Unknown ML action. Use 'train' or 'predict'.")
        raise typer.Exit()


@app.command()
def geo(
    action: str = typer.Argument(..., help="Action: geocode or distance"),
    address: Optional[str] = typer.Option(
        None, help="Address to geocode (for geocode action)"
    ),
    lat1: Optional[float] = typer.Option(None, help="Latitude 1 (for distance)"),
    lon1: Optional[float] = typer.Option(None, help="Longitude 1 (for distance)"),
    lat2: Optional[float] = typer.Option(None, help="Latitude 2 (for distance)"),
    lon2: Optional[float] = typer.Option(None, help="Longitude 2 (for distance)"),
    unit: str = typer.Option("km", help="Unit for distance: km or miles"),
):
    """Geolocation/geo-cleaning: geocode address or calculate distance."""
    geo = GeoProcessor()
    if action == "geocode":
        if not address:
            console.print("[red]Specify --address for geocoding.")
            raise typer.Exit()
        result = geo.geocode_address(address)
        console.print(result)
    elif action == "distance":
        if None in (lat1, lon1, lat2, lon2):
            console.print("[red]Specify --lat1, --lon1, --lat2, --lon2 for distance.")
            raise typer.Exit()
        dist = geo.calculate_distance(lat1, lon1, lat2, lon2, unit=unit)
        console.print(f"[green]Distance: {dist:.2f} {unit}")
    else:
        console.print("[red]Unknown geo action. Use 'geocode' or 'distance'.")
        raise typer.Exit()

# --- Calculator Commands ---
calculator_processor = CalculatorProcessor()

@calc_app.command("sin")
def calc_sin(value: float = typer.Argument(..., help="Input value (in radians)")):
    """Calculates the sine of a value."""
    try:
        result = calculator_processor.sin(value)
        console.print(f"sin({value}) = {result}")
    except Exception as e:
        console.print(f"[red]Error: {e}")

@calc_app.command("cos")
def calc_cos(value: float = typer.Argument(..., help="Input value (in radians)")):
    """Calculates the cosine of a value."""
    try:
        result = calculator_processor.cos(value)
        console.print(f"cos({value}) = {result}")
    except Exception as e:
        console.print(f"[red]Error: {e}")

@calc_app.command("tan")
def calc_tan(value: float = typer.Argument(..., help="Input value (in radians)")):
    """Calculates the tangent of a value."""
    try:
        result = calculator_processor.tan(value)
        console.print(f"tan({value}) = {result}")
    except Exception as e:
        console.print(f"[red]Error: {e}")

@calc_app.command("log")
def calc_log(
    value: float = typer.Argument(..., help="Input value"),
    base: Optional[float] = typer.Option(None, help="Logarithm base (default: natural log 'e')")
):
    """Calculates the logarithm of a value."""
    try:
        result = calculator_processor.log(value, base)
        console.print(f"log({value}, base={base if base else 'e'}) = {result}")
    except Exception as e:
        console.print(f"[red]Error: {e}")

@calc_app.command("sqrt")
def calc_sqrt(value: float = typer.Argument(..., help="Input value")):
    """Calculates the square root of a value."""
    try:
        result = calculator_processor.sqrt(value)
        console.print(f"sqrt({value}) = {result}")
    except Exception as e:
        console.print(f"[red]Error: {e}")

@calc_app.command("convert")
def calc_convert(
    value: float = typer.Argument(..., help="Value to convert"),
    from_unit: str = typer.Argument(..., help="Unit to convert from (e.g., km, kg, C)"),
    to_unit: str = typer.Argument(..., help="Unit to convert to (e.g., m, lb, F)"),
    category: str = typer.Argument(..., help="Category of conversion (length, weight, temperature)")
):
    """Converts a value between units."""
    try:
        result = calculator_processor.convert_unit(value, from_unit, to_unit, category)
        console.print(f"{value} {from_unit} = {result} {to_unit} (category: {category})")
    except Exception as e:
        console.print(f"[red]Error: {e}")

if __name__ == "__main__":
    app()
