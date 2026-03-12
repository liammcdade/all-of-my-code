import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns


class DataPlotter:
    """
    Handles the creation of various plots for data visualization.

    The class is initialized with data (ideally a pandas DataFrame).
    It provides methods to generate common plots like histograms,
    scatter plots, bar charts, etc.
    """

    def __init__(self, data):
        """
        Initializes the DataPlotter with the dataset.

        Args:
            data: The data to be plotted. Expected to be a pandas DataFrame
                  or convertible to one.
        """
        if data is None:
            raise ValueError("Input data cannot be None.")

        if isinstance(data, pd.DataFrame):
            self.data = data
        elif isinstance(data, list):
            try:
                if data and isinstance(data[0], list):  # Header row
                    self.data = pd.DataFrame(data[1:], columns=data[0])
                else:
                    self.data = pd.DataFrame(data)
            except Exception as e:
                raise ValueError(
                    f"Could not convert list to DataFrame for plotting: {e}"
                )
        else:
            raise TypeError(
                "Unsupported data type. Please provide a pandas DataFrame or a convertible list."
            )

        if self.data.empty:
            print("Warning: Initialized DataPlotter with an empty DataFrame.")

        # Apply a default style for seaborn plots for better aesthetics
        sns.set_theme(style="whitegrid")

    def create_plot(self, plot_type, **kwargs):
        """
        Generic method to create a specified type of plot.

        Args:
            plot_type (str): The type of plot to create (e.g., 'histogram', 'scatter', 'bar', 'line', 'boxplot').
            **kwargs: Arguments specific to the chosen plot type.
                      These will be passed to the respective plotting methods.
                      Common arguments could include:
                      - x (str): Column name for x-axis.
                      - y (str): Column name for y-axis.
                      - column (str): Column name for univariate plots like histograms.
                      - title (str): Title of the plot.
                      - xlabel (str): Label for x-axis.
                      - ylabel (str): Label for y-axis.
                      - save_path (str, optional): If provided, saves the plot to this path.
                                                   Otherwise, displays the plot.

        Returns:
            matplotlib.figure.Figure or None: The figure object if plot is created, else None.
                                             Plot is displayed or saved directly.
        """
        if not isinstance(self.data, pd.DataFrame) or self.data.empty:
            print("Data is not a valid DataFrame or is empty. Cannot create plot.")
            return None

        plot_method_name = f"plot_{plot_type}"
        if hasattr(self, plot_method_name) and callable(
            getattr(self, plot_method_name)
        ):
            print(f"Creating '{plot_type}' plot with parameters: {kwargs}")
            try:
                fig = getattr(self, plot_method_name)(**kwargs)

                # Handle saving or showing the plot
                save_path = kwargs.get("save_path")
                if (
                    fig
                ):  # Some plot methods might handle show/save internally if complex
                    if save_path:
                        fig.savefig(save_path)
                        print(f"Plot saved to {save_path}")
                        plt.close(fig)  # Close the figure after saving to free memory
                    else:
                        plt.show()
                return fig
            except Exception as e:
                print(f"Error creating plot '{plot_type}': {e}")
                return None
        else:
            print(
                f"Warning: Plot type '{plot_type}' is not supported or method '{plot_method_name}' not found."
            )
            return None

    def plot_histogram(
        self, column, title=None, xlabel=None, ylabel="Frequency", bins=10, **kwargs
    ):
        """
        Generates a histogram for a specified column.

        Args:
            column (str): The name of the column for the histogram.
            title (str, optional): Title of the plot.
            xlabel (str, optional): Label for the x-axis. Defaults to column name.
            ylabel (str, optional): Label for the y-axis.
            bins (int): Number of bins for the histogram.
            **kwargs: Additional keyword arguments for sns.histplot().

        Returns:
            matplotlib.figure.Figure: The figure object.
        """
        if column not in self.data.columns:
            print(f"Column '{column}' not found in data.")
            return None
        if not pd.api.types.is_numeric_dtype(self.data[column]):
            print(
                f"Warning: Column '{column}' is not numeric. Histogram may not be meaningful."
            )
            # Potentially try to convert or handle, but for now, just warn.

        fig, ax = plt.subplots()
        sns.histplot(
            data=self.data,
            x=column,
            bins=bins,
            kde=kwargs.pop("kde", False),
            ax=ax,
            **kwargs,
        )

        ax.set_title(title if title else f"Histogram of {column}")
        ax.set_xlabel(xlabel if xlabel else column)
        ax.set_ylabel(ylabel)

        return fig

    def plot_scatter(
        self,
        x_column,
        y_column,
        title=None,
        xlabel=None,
        ylabel=None,
        hue=None,
        **kwargs,
    ):
        """
        Generates a scatter plot for two specified columns.

        Args:
            x_column (str): The name of the column for the x-axis.
            y_column (str): The name of the column for the y-axis.
            title (str, optional): Title of the plot.
            xlabel (str, optional): Label for the x-axis. Defaults to x_column name.
            ylabel (str, optional): Label for the y-axis. Defaults to y_column name.
            hue (str, optional): Column name for color encoding.
            **kwargs: Additional keyword arguments for sns.scatterplot().

        Returns:
            matplotlib.figure.Figure: The figure object.
        """
        if x_column not in self.data.columns or y_column not in self.data.columns:
            print(
                f"One or both columns ('{x_column}', '{y_column}') not found in data."
            )
            return None
        if hue and hue not in self.data.columns:
            print(f"Hue column '{hue}' not found in data. Ignoring.")
            hue = None

        fig, ax = plt.subplots()
        sns.scatterplot(
            data=self.data, x=x_column, y=y_column, hue=hue, ax=ax, **kwargs
        )

        ax.set_title(title if title else f"Scatter Plot of {y_column} vs {x_column}")
        ax.set_xlabel(xlabel if xlabel else x_column)
        ax.set_ylabel(ylabel if ylabel else y_column)

        return fig

    def plot_bar(
        self,
        x_column,
        y_column,
        title=None,
        xlabel=None,
        ylabel=None,
        estimator="mean",
        **kwargs,
    ):
        """
        Generates a bar plot. Useful for showing aggregated values of a numerical column
        against a categorical column.

        Args:
            x_column (str): The name of the column for the x-axis (typically categorical).
            y_column (str): The name of the column for the y-axis (typically numerical).
            title (str, optional): Title of the plot.
            xlabel (str, optional): Label for the x-axis. Defaults to x_column name.
            ylabel (str, optional): Label for the y-axis. Defaults to y_column name.
            estimator (str or callable): Statistical function to estimate within each categorical bin.
                                     Common: 'mean', 'sum', 'count'.
            **kwargs: Additional keyword arguments for sns.barplot().

        Returns:
            matplotlib.figure.Figure: The figure object.
        """
        if x_column not in self.data.columns or y_column not in self.data.columns:
            print(
                f"One or both columns ('{x_column}', '{y_column}') not found in data."
            )
            return None

        fig, ax = plt.subplots()
        # Seaborn's barplot default estimator is mean. For 'count', use sns.countplot directly or adjust.
        if estimator == "count":
            sns.countplot(data=self.data, x=x_column, ax=ax, **kwargs)
            ax.set_ylabel(ylabel if ylabel else "Count")
        else:
            # For other estimators, ensure y_column is numeric
            if not pd.api.types.is_numeric_dtype(self.data[y_column]):
                print(
                    f"Warning: y_column '{y_column}' must be numeric for estimators like 'mean' or 'sum'."
                )
                # return None # Or try to proceed if sns handles it

            # Convert estimator string to actual function if needed by barplot or if it's a custom string
            # sns.barplot handles 'mean', 'median', 'sum', 'std', etc. directly.
            sns.barplot(
                data=self.data,
                x=x_column,
                y=y_column,
                estimator=estimator,
                ax=ax,
                **kwargs,
            )
            ax.set_ylabel(
                ylabel if ylabel else f"{estimator.capitalize()} of {y_column}"
            )

        ax.set_title(title if title else f"Bar Plot: {y_column} by {x_column}")
        ax.set_xlabel(xlabel if xlabel else x_column)
        plt.xticks(
            rotation=45, ha="right"
        )  # Rotate x-axis labels for better readability
        plt.tight_layout()  # Adjust layout

        return fig


if __name__ == "__main__":
    # This block will only run if plotter.py is executed directly.
    # It requires matplotlib to be able to show plots.
    # In a real application, you'd import and use DataPlotter.
    print("--- DataPlotter Demonstration ---")

    # Sample Data
    sample_data_plot = pd.DataFrame(
        {
            "Age": [25, 30, 22, 35, 28, 40, 30, 22, 35, 28],
            "Salary": [
                50000,
                60000,
                45000,
                75000,
                58000,
                90000,
                62000,
                48000,
                70000,
                60000,
            ],
            "Department": [
                "HR",
                "Engineering",
                "Marketing",
                "Engineering",
                "HR",
                "Management",
                "Engineering",
                "Marketing",
                "HR",
                "Engineering",
            ],
            "Experience": [2, 5, 1, 10, 3, 15, 6, 2, 9, 4],
        }
    )

    plotter = DataPlotter(sample_data_plot)

    print("\n--- Plotting Histogram (Age) ---")
    # To actually see the plot, ensure your environment supports GUI pop-ups
    # or save it to a file. For automated tests, saving is better.
    # plotter.plot_histogram(column='Age', bins=5, title="Distribution of Age", save_path="age_histogram.png")
    plotter.create_plot(
        plot_type="histogram",
        column="Age",
        bins=8,
        title="Distribution of Age",
        kde=True,
        save_path="age_histogram.png",
    )
    print("Histogram for Age saved to age_histogram.png (if matplotlib is working).")

    print("\n--- Plotting Scatter (Salary vs Experience) ---")
    # plotter.plot_scatter(x_column='Experience', y_column='Salary', hue='Department', title="Salary vs. Experience by Department", save_path="salary_experience_scatter.png")
    plotter.create_plot(
        plot_type="scatter",
        x_column="Experience",
        y_column="Salary",
        hue="Department",
        title="Salary vs. Experience",
        save_path="salary_vs_experience.png",
    )
    print("Scatter plot for Salary vs Experience saved to salary_vs_experience.png.")

    print("\n--- Plotting Bar Chart (Average Salary by Department) ---")
    # plotter.plot_bar(x_column='Department', y_column='Salary', title="Average Salary by Department", estimator='mean', save_path="avg_salary_by_dept.png")
    plotter.create_plot(
        plot_type="bar",
        x_column="Department",
        y_column="Salary",
        title="Average Salary by Department",
        estimator="mean",
        save_path="avg_salary_by_dept.png",
    )
    print("Bar chart for Average Salary by Department saved to avg_salary_by_dept.png.")

    print("\n--- Plotting Bar Chart (Count by Department) ---")
    plotter.create_plot(
        plot_type="bar",
        x_column="Department",
        y_column="Experience",  # y_column is ignored for count
        title="Employee Count by Department",
        estimator="count",
        save_path="count_by_dept.png",
    )
    print("Bar chart for Count by Department saved to count_by_dept.png.")

    print("\n--- Attempting to plot non-existent column ---")
    plotter.create_plot(
        plot_type="histogram", column="NonExistent", save_path="should_not_save.png"
    )

    print("\n--- Demonstration Complete ---")
    print(
        "Note: Plots are saved to files. To display them interactively, run in an environment that supports it and remove/comment out 'save_path'."
    )
