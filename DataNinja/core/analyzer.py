import pandas as pd
import numpy as np


class DataAnalyzer:
    def __init__(self, data):
        if data is None:
            raise ValueError("Input data cannot be None.")

        if isinstance(data, pd.DataFrame):
            self.data = data
        elif isinstance(data, list):
            if data and isinstance(data[0], list):
                self.data = pd.DataFrame(data[1:], columns=data[0])
            else:
                self.data = pd.DataFrame(data)
        else:
            raise TypeError("Unsupported data type.")

        if self.data.empty:
            print("Warning: Empty DataFrame.")

    def analyze_data(self, analysis_types=None):
        """
        Performs a series of analyses on the data.

        Args:
            analysis_types (list of dict, optional): A list of analyses to perform.
                Each dict can specify the analysis method and its arguments.
                Example: [{'method': 'get_summary_statistics'},
                          {'method': 'get_correlation_matrix', 'params': {'columns': ['col1', 'col2']}}]
                If None, this method might perform a default set of analyses.

        Returns:
            dict: A dictionary containing results from the performed analyses.
        """
        if not isinstance(self.data, pd.DataFrame):
            print(
                "Warning: Data is not a pandas DataFrame. Analysis capabilities may be limited."
            )
            return {}  # Or raise error

        results = {}
        if analysis_types:
            for analysis in analysis_types:
                method_name = analysis.get("method")
                params = analysis.get("params", {})
                if hasattr(self, method_name) and callable(getattr(self, method_name)):
                    print(f"Performing analysis: {method_name} with params: {params}")
                    try:
                        result = getattr(self, method_name)(**params)
                        results[method_name] = result
                    except Exception as e:
                        print(f"Error during analysis '{method_name}': {e}")
                        results[method_name] = {"error": str(e)}
                else:
                    print(
                        f"Warning: Unknown analysis method '{method_name}'. Skipping."
                    )
                    results[method_name] = {"error": f"Unknown method {method_name}"}
        else:
            # Default analysis if none specified
            print(
                "No specific analyses requested. Performing default summary statistics."
            )
            results["summary_statistics"] = self.get_summary_statistics()
            # results['correlation_matrix'] = self.get_correlation_matrix() # Example default

        return results

    def get_summary_statistics(
        self, columns=None, include_dtypes=None, exclude_dtypes=None
    ):
        """
        Calculates descriptive statistics for numerical and categorical columns.

        Args:
            columns (list of str, optional): Specific columns to get statistics for.
                                            If None, statistics for all columns are returned.
            include_dtypes (list of types or str, optional): A list of dtypes to include.
                                                            Defaults to numeric types if 'all' is not used.
                                                            Can also be 'all'.
            exclude_dtypes (list of types or str, optional): A list of dtypes to exclude.

        Returns:
            pd.DataFrame: A DataFrame containing summary statistics.
                          For numerical data, includes count, mean, std, min, max, quartiles.
                          For object/categorical data, includes count, unique, top, freq.
        """
        if not isinstance(self.data, pd.DataFrame) or self.data.empty:
            print(
                "Data is not a valid DataFrame or is empty. Cannot compute summary statistics."
            )
            return pd.DataFrame()

        df_to_analyze = self.data
        if columns:
            missing_cols = [col for col in columns if col not in df_to_analyze.columns]
            if missing_cols:
                print(f"Warning: Columns not found and will be ignored: {missing_cols}")
            df_to_analyze = df_to_analyze[
                [col for col in columns if col in df_to_analyze.columns]
            ]
            if df_to_analyze.empty and columns:  # All specified columns were missing
                print(
                    "Warning: None of the specified columns for summary statistics were found."
                )
                return pd.DataFrame()

        print(f"Calculating summary statistics...")
        # The describe() method intelligently handles mixed types if include/exclude are not overly restrictive.
        # Default behavior of describe():
        # - If DataFrame has mixed dtypes, only numeric columns are returned.
        # - If include='all', it includes all columns, providing relevant stats for each.
        # - If include=['object'], it provides stats for object/string columns.
        # - If include=['number'], it provides stats for numeric columns.

        # Let's try to be a bit more explicit for clarity
        if include_dtypes is None and exclude_dtypes is None:
            # Default: describe numeric and if available, object columns separately and combine
            numeric_stats = df_to_analyze.describe(include=[np.number])
            object_stats = df_to_analyze.describe(include=["object", "category"])

            if not numeric_stats.empty and not object_stats.empty:
                # If both have results, it's tricky to combine them elegantly into one describe-like frame
                # unless `include='all'` is used. For now, return them potentially separately or prioritize.
                # Pandas describe with include='all' does a good job.
                return df_to_analyze.describe(include="all")
            elif not numeric_stats.empty:
                return numeric_stats
            elif not object_stats.empty:
                return object_stats
            else:  # If neither, it might be all boolean or other types not typically in 'number' or 'object'
                return df_to_analyze.describe(include="all")  # Fallback to 'all'
        else:
            # User specified include/exclude
            return df_to_analyze.describe(
                include=include_dtypes, exclude=exclude_dtypes
            )

    def get_correlation_matrix(self, columns=None, method="pearson"):
        """
        Calculates the pairwise correlation of specified columns.

        Args:
            columns (list of str, optional): A list of column names for which to compute correlations.
                                            If None, attempts to use all numerical columns.
            method (str or callable): The method of correlation:
                - 'pearson' (default): standard correlation coefficient
                - 'kendall': Kendall Tau correlation coefficient
                - 'spearman': Spearman rank correlation
                - callable: callable with input two 1d ndarrays and returning a float.

        Returns:
            pd.DataFrame: A DataFrame representing the correlation matrix.
                          Returns an empty DataFrame if no suitable columns are found or an error occurs.
        """
        if not isinstance(self.data, pd.DataFrame) or self.data.empty:
            print(
                "Data is not a valid DataFrame or is empty. Cannot compute correlation matrix."
            )
            return pd.DataFrame()

        df_for_corr = self.data
        if columns:
            missing_cols = [col for col in columns if col not in df_for_corr.columns]
            if missing_cols:
                print(
                    f"Warning: Columns for correlation not found and will be ignored: {missing_cols}"
                )
            df_for_corr = df_for_corr[
                [col for col in columns if col in df_for_corr.columns]
            ]

        # Select only numeric columns for correlation from the (potentially subsetted) DataFrame
        numeric_df = df_for_corr.select_dtypes(include=np.number)

        if numeric_df.empty:
            print("Warning: No numeric columns found to calculate correlation.")
            return pd.DataFrame()

        if numeric_df.shape[1] < 2:
            print(
                "Warning: At least two numeric columns are required to calculate a correlation matrix."
            )
            return pd.DataFrame()

        print(f"Calculating correlation matrix (method: {method})...")
        try:
            correlation_matrix = numeric_df.corr(method=method)
            return correlation_matrix
        except Exception as e:
            print(f"Error calculating correlation matrix: {e}")
            return pd.DataFrame()

    def get_value_counts(self, column, normalize=False):
        """
        Computes the frequency of unique values in a specified column.

        Args:
            column (str): The name of the column.
            normalize (bool): If True, returns relative frequencies (proportions).

        Returns:
            pd.Series: A Series containing value counts, sorted by frequency.
                       Returns an empty Series if the column doesn't exist or an error occurs.
        """
        if not isinstance(self.data, pd.DataFrame) or self.data.empty:
            print("Data is not a valid DataFrame or is empty.")
            return pd.Series(dtype="object")

        if column not in self.data.columns:
            print(f"Warning: Column '{column}' not found.")
            return pd.Series(dtype="object")

        print(f"Calculating value counts for column '{column}'...")
        try:
            return self.data[column].value_counts(normalize=normalize)
        except Exception as e:
            print(f"Error calculating value counts for column '{column}': {e}")
            return pd.Series(dtype="object")


if __name__ == "__main__":
    print("--- DataAnalyzer Demonstration ---")

    # Sample data: list of lists (header in first row)
    data_lol = [
        ["Name", "Age", "City", "Salary", "Experience"],
        ["Alice", 28, "New York", 70000, 5.0],
        ["Bob", 35, "Los Angeles", 80000, 10.2],
        ["Charlie", 22, "Chicago", 55000, 2.5],
        ["David", 45, "New York", 120000, 20.0],
        ["Eve", 30, "Chicago", 75000, 7.0],
        ["Frank", 28, "New York", 72000, 4.5],
        ["Grace", None, "Los Angeles", 60000, 3.0],  # Missing Age
    ]

    print("\n--- Example 1: Using List of Lists ---")
    try:
        analyzer1 = DataAnalyzer(data_lol)

        print("\nInitial DataFrame from LoL:")
        print(analyzer1.data.head())

        print("\nSummary Statistics (default):")
        summary_stats = analyzer1.get_summary_statistics()
        print(summary_stats)

        print("\nSummary Statistics (specific columns - Age, Salary):")
        summary_specific = analyzer1.get_summary_statistics(
            columns=["Age", "Salary", "MissingCol"]
        )
        print(summary_specific)

        print("\nCorrelation Matrix (default numeric columns):")
        correlation_matrix = analyzer1.get_correlation_matrix()
        print(correlation_matrix)

        print("\nValue Counts for 'City':")
        city_counts = analyzer1.get_value_counts(column="City")
        print(city_counts)

        print("\nValue Counts for 'Age' (normalized):")
        age_counts_norm = analyzer1.get_value_counts(column="Age", normalize=True)
        print(age_counts_norm)

        print("\nOrchestrated Analysis:")
        analysis_plan = [
            {"method": "get_summary_statistics", "params": {"include_dtypes": "all"}},
            {"method": "get_correlation_matrix"},
            {"method": "get_value_counts", "params": {"column": "City"}},
        ]
        all_results = analyzer1.analyze_data(analysis_plan)
        for key, res in all_results.items():
            print(f"--- Results for {key} ---")
            print(res)
            print("--------------------------")

    except Exception as e:
        print(f"Error in Example 1: {e}")

    # Example 2: Using an existing Pandas DataFrame
    print("\n--- Example 2: Using Pandas DataFrame ---")
    data_df = pd.DataFrame(
        {
            "ID": range(5),
            "Score": [88, 92, 75, 92, 80.5],
            "Attempts": [1, 3, 2, 3, 1],
            "Category": ["X", "Y", "X", "Y", "Z"],
        }
    )
    try:
        analyzer2 = DataAnalyzer(data_df.copy())
        print("\nInitial DataFrame:")
        print(analyzer2.data)

        print("\nSummary Statistics (for 'Score' and 'Attempts'):")
        stats2 = analyzer2.get_summary_statistics(columns=["Score", "Attempts"])
        print(stats2)

        print("\nCorrelation (Spearman):")
        corr2 = analyzer2.get_correlation_matrix(method="spearman")
        print(corr2)

    except Exception as e:
        print(f"Error in Example 2: {e}")

    # Example 3: Empty DataFrame
    print("\n--- Example 3: Empty DataFrame ---")
    try:
        empty_df = pd.DataFrame({"A": [], "B": []})
        analyzer_empty = DataAnalyzer(empty_df)
        print(analyzer_empty.get_summary_statistics())
        print(analyzer_empty.get_correlation_matrix())
    except Exception as e:
        print(f"Error in Example 3: {e}")

    # Example 4: Init with None
    print("\n--- Example 4: Initialization with None ---")
    try:
        analyzer_none = DataAnalyzer(None)
    except ValueError as e:
        print(f"Caught expected error: {e}")
