import plotext as plt
import pandas as pd

def plot_generic_top_n(data_series: pd.Series, title: str, xlabel: str, ylabel: str, top_n: int = 10, sort_ascending=False) -> None:
    """Displays a generic bar chart for a pandas Series in the terminal."""
    sorted_series = data_series.sort_values(ascending=sort_ascending)
    top_data = sorted_series.head(top_n)
    items = top_data.index.tolist()
    values = top_data.values.tolist()

    plt.clf()
    plt.bar(items, values)
    plt.title(title)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.show() 