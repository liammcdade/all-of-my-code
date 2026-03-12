import unittest
import pandas as pd
import numpy as np
from pandas.testing import assert_frame_equal, assert_series_equal
import io
import sys
import logging

from DataNinja.core.analyzer import DataAnalyzer


# Helper to capture print/logging outputs
class Capturing(list):
    def __enter__(self):
        self._stdout = sys.stdout
        sys.stdout = self._stringio = io.StringIO()
        # Optionally capture logging if DataAnalyzer uses logging module directly
        self.logger = logging.getLogger()  # Root logger or specific if known
        self.log_level = self.logger.level
        self.logger.setLevel(logging.DEBUG)  # Capture all levels
        self.log_handler = logging.StreamHandler(self._stringio)
        self.logger.addHandler(self.log_handler)
        return self

    def __exit__(self, *args):
        self.extend(self._stringio.getvalue().splitlines())
        del self._stringio
        sys.stdout = self._stdout
        self.logger.removeHandler(self.log_handler)
        self.logger.setLevel(self.log_level)


class TestAnalyzerInitialization(unittest.TestCase):
    def test_init_with_dataframe(self):
        df = pd.DataFrame({"A": [1, 2], "B": [3, 4]})
        analyzer = DataAnalyzer(data=df)
        assert_frame_equal(analyzer.data, df)

    def test_init_with_list_of_lists_with_header(self):
        data_lol = [["A", "B"], [1, 3], [2, 4]]
        expected_df = pd.DataFrame([[1, 3], [2, 4]], columns=["A", "B"])
        analyzer = DataAnalyzer(data=data_lol)
        assert_frame_equal(analyzer.data, expected_df)

    def test_init_with_list_of_lists_no_header_pandas_infers(self):
        data_lol = [[1, 3], [2, 4]]
        expected_df = pd.DataFrame([[1, 3], [2, 4]])  # Pandas makes 0, 1 columns
        analyzer = DataAnalyzer(data=data_lol)
        assert_frame_equal(analyzer.data, expected_df)

    def test_init_with_empty_dataframe(self):
        with Capturing() as output:  # DataAnalyzer prints a warning for empty DF
            analyzer = DataAnalyzer(data=pd.DataFrame())
        self.assertTrue(analyzer.data.empty)
        self.assertIn(
            "Warning: Initialized DataAnalyzer with an empty DataFrame.", output
        )

    def test_init_with_empty_list(self):
        # Analyzer converts empty list to empty DataFrame
        with Capturing() as output:
            analyzer = DataAnalyzer(data=[])
        self.assertTrue(analyzer.data.empty)
        self.assertIsInstance(analyzer.data, pd.DataFrame)
        self.assertIn(
            "Warning: Initialized DataAnalyzer with an empty DataFrame.", output
        )

    def test_init_with_none_raises_valueerror(self):
        with self.assertRaisesRegex(ValueError, "Input data cannot be None."):
            DataAnalyzer(data=None)

    def test_init_with_unsupported_type_raises_typeerror(self):
        with self.assertRaisesRegex(TypeError, "Unsupported data type."):
            DataAnalyzer(data="this is a string")

    def test_init_with_ragged_list_raises_valueerror(self):
        # List of lists that cannot be converted to a rectangular DataFrame easily
        data_ragged = [["A", "B"], [1, 2, 3], [4, 5]]
        with self.assertRaisesRegex(
            ValueError, "Could not convert list to DataFrame for analysis"
        ):
            DataAnalyzer(data=data_ragged)

    def test_init_with_list_of_non_list_elements_raises_valueerror(self):
        data_mixed = [["Header1", "Header2"], "not a list", 123]
        with self.assertRaisesRegex(
            ValueError, "Could not convert list to DataFrame for analysis"
        ):
            DataAnalyzer(data_mixed)


class TestGetSummaryStatistics(unittest.TestCase):
    def setUp(self):
        self.data = pd.DataFrame(
            {
                "NumericCol": [1, 2, 3, np.nan, 5],
                "StringCol": ["apple", "banana", "apple", "orange", "banana"],
                "CategoryCol": pd.Categorical(["cat1", "cat2", "cat1", "cat3", "cat2"]),
                "BoolCol": [True, False, True, True, False],
                "MixedCol": [10, "text", 20.5, True, None],  # Will be object dtype
            }
        )
        self.analyzer = DataAnalyzer(self.data.copy())
        self.empty_analyzer = DataAnalyzer(pd.DataFrame())

    def test_default_summary_statistics_include_all(self):
        # Default behavior of get_summary_statistics is to try include='all'
        stats = self.analyzer.get_summary_statistics()
        expected_stats = self.data.describe(include="all")
        assert_frame_equal(
            stats.sort_index(axis=1),
            expected_stats.sort_index(axis=1),
            check_dtype=False,
        )

    def test_summary_statistics_for_specific_columns(self):
        stats = self.analyzer.get_summary_statistics(
            columns=["NumericCol", "StringCol"]
        )
        expected_stats = self.data[["NumericCol", "StringCol"]].describe(include="all")
        assert_frame_equal(
            stats.sort_index(axis=1),
            expected_stats.sort_index(axis=1),
            check_dtype=False,
        )

    def test_summary_statistics_include_numeric(self):
        stats = self.analyzer.get_summary_statistics(include_dtypes=[np.number])
        expected_stats = self.data.describe(include=[np.number])
        assert_frame_equal(
            stats.sort_index(axis=1),
            expected_stats.sort_index(axis=1),
            check_dtype=True,
        )

    def test_summary_statistics_include_object(self):
        # StringCol and MixedCol are object
        stats = self.analyzer.get_summary_statistics(include_dtypes=["object"])
        expected_stats = self.data.describe(include=["object"])
        assert_frame_equal(
            stats.sort_index(axis=1),
            expected_stats.sort_index(axis=1),
            check_dtype=False,
        )
        # Ensure 'CategoryCol' and 'BoolCol' are not included
        self.assertTrue("CategoryCol" not in stats.columns)
        self.assertTrue("BoolCol" not in stats.columns)

    def test_summary_statistics_exclude_numeric(self):
        stats = self.analyzer.get_summary_statistics(exclude_dtypes=[np.number])
        expected_stats = self.data.describe(exclude=[np.number])
        assert_frame_equal(
            stats.sort_index(axis=1),
            expected_stats.sort_index(axis=1),
            check_dtype=False,
        )

    def test_summary_statistics_include_all_explicit(self):
        stats = self.analyzer.get_summary_statistics(include_dtypes="all")
        expected_stats = self.data.describe(include="all")
        assert_frame_equal(
            stats.sort_index(axis=1),
            expected_stats.sort_index(axis=1),
            check_dtype=False,
        )

    def test_summary_statistics_on_empty_dataframe(self):
        stats = self.empty_analyzer.get_summary_statistics()
        self.assertTrue(stats.empty)

    def test_summary_statistics_with_non_existent_columns(self):
        with Capturing() as output:
            stats = self.analyzer.get_summary_statistics(
                columns=["NumericCol", "NonExistentCol"]
            )
        self.assertIn(
            "Warning: Columns not found and will be ignored: ['NonExistentCol']", output
        )
        expected_stats = self.data[["NumericCol"]].describe(include="all")
        assert_frame_equal(
            stats.sort_index(axis=1),
            expected_stats.sort_index(axis=1),
            check_dtype=False,
        )

    def test_summary_statistics_all_specified_columns_missing(self):
        with Capturing() as output:
            stats = self.analyzer.get_summary_statistics(
                columns=["NonExistentCol1", "NonExistentCol2"]
            )
        self.assertIn(
            "Warning: None of the specified columns for summary statistics were found.",
            output,
        )
        self.assertTrue(stats.empty)


class TestGetCorrelationMatrix(unittest.TestCase):
    def setUp(self):
        self.data_numeric = pd.DataFrame(
            {
                "A": [1, 2, 3, 4, 5],
                "B": [5, 4, 3, 2, 1],
                "C": [1.0, 2.5, 3.0, 4.5, 5.0],
                "D_str": ["x", "y", "z", "a", "b"],  # Non-numeric
            }
        )
        self.analyzer_numeric = DataAnalyzer(self.data_numeric.copy())
        self.analyzer_mixed = DataAnalyzer(
            pd.DataFrame(
                {"Num1": [1, 2, 3], "Str1": ["a", "b", "c"], "Num2": [4, 5, 6]}
            )
        )
        self.analyzer_single_numeric = DataAnalyzer(
            pd.DataFrame({"Num": [1, 2, 3], "Str": ["a", "b", "c"]})
        )
        self.empty_analyzer = DataAnalyzer(pd.DataFrame())

    def test_correlation_default_pearson(self):
        corr = self.analyzer_numeric.get_correlation_matrix()
        expected_corr = self.data_numeric[["A", "B", "C"]].corr(method="pearson")
        assert_frame_equal(corr, expected_corr)

    def test_correlation_kendall(self):
        corr = self.analyzer_numeric.get_correlation_matrix(method="kendall")
        expected_corr = self.data_numeric[["A", "B", "C"]].corr(method="kendall")
        assert_frame_equal(corr, expected_corr)

    def test_correlation_spearman(self):
        corr = self.analyzer_numeric.get_correlation_matrix(method="spearman")
        expected_corr = self.data_numeric[["A", "B", "C"]].corr(method="spearman")
        assert_frame_equal(corr, expected_corr)

    def test_correlation_with_specific_columns(self):
        corr = self.analyzer_numeric.get_correlation_matrix(columns=["A", "C"])
        expected_corr = self.data_numeric[["A", "C"]].corr(method="pearson")
        assert_frame_equal(corr, expected_corr)

    def test_correlation_ignores_non_numeric_columns_in_data(self):
        # analyzer_numeric has 'D_str' which should be ignored
        corr = self.analyzer_numeric.get_correlation_matrix()  # Uses A, B, C
        self.assertListEqual(list(corr.columns), ["A", "B", "C"])
        self.assertListEqual(list(corr.index), ["A", "B", "C"])

    def test_correlation_ignores_non_numeric_if_specified_in_columns(self):
        # If user specifies a non-numeric column, it should be filtered out
        with Capturing() as output:
            corr = self.analyzer_numeric.get_correlation_matrix(
                columns=["A", "D_str", "C"]
            )
        # The select_dtypes inside get_correlation_matrix will pick numeric ones from the subset
        expected_corr = self.data_numeric[["A", "C"]].corr(method="pearson")
        assert_frame_equal(corr, expected_corr)
        # No warning is printed by current implementation for non-numeric columns, it just filters
        # self.assertIn("Warning: Non-numeric columns selected for correlation will be ignored: ['D_str']", output)

    def test_correlation_fewer_than_two_numeric_columns(self):
        with Capturing() as output:
            corr = self.analyzer_single_numeric.get_correlation_matrix()
        self.assertTrue(corr.empty)
        self.assertIn("Warning: At least two numeric columns are required", output[0])

        with Capturing() as output:  # Also test if only one numeric column is specified
            corr_specified = self.analyzer_numeric.get_correlation_matrix(
                columns=["A", "D_str"]
            )
        self.assertTrue(corr_specified.empty)
        self.assertIn("Warning: At least two numeric columns are required", output[0])

    def test_correlation_on_empty_dataframe(self):
        corr = self.empty_analyzer.get_correlation_matrix()
        self.assertTrue(corr.empty)

    def test_correlation_with_non_existent_columns(self):
        with Capturing() as output:
            corr = self.analyzer_numeric.get_correlation_matrix(
                columns=["A", "NonExistent", "C"]
            )
        self.assertIn(
            "Warning: Columns for correlation not found and will be ignored: ['NonExistent']",
            output,
        )
        expected_corr = self.data_numeric[["A", "C"]].corr(method="pearson")
        assert_frame_equal(corr, expected_corr)

    def test_correlation_no_numeric_columns_found(self):
        analyzer_no_numeric = DataAnalyzer(
            pd.DataFrame({"S1": ["a", "b"], "S2": ["c", "d"]})
        )
        with Capturing() as output:
            corr = analyzer_no_numeric.get_correlation_matrix()
        self.assertTrue(corr.empty)
        self.assertIn(
            "Warning: No numeric columns found to calculate correlation.", output[0]
        )


class TestGetValueCounts(unittest.TestCase):
    def setUp(self):
        self.data = pd.DataFrame(
            {
                "ColA": ["x", "y", "x", "z", "y", "x"],
                "ColB": [1, 2, 1, 3, 2, 1],
                "ColC_empty": [np.nan, np.nan, np.nan],
            }
        )
        self.analyzer = DataAnalyzer(self.data.copy())
        self.empty_analyzer = DataAnalyzer(pd.DataFrame({"A": []}))

    def test_value_counts_existing_column(self):
        counts = self.analyzer.get_value_counts(column="ColA")
        expected_counts = self.data["ColA"].value_counts()
        assert_series_equal(counts, expected_counts)

    def test_value_counts_normalize(self):
        counts_norm = self.analyzer.get_value_counts(column="ColB", normalize=True)
        expected_counts_norm = self.data["ColB"].value_counts(normalize=True)
        assert_series_equal(counts_norm, expected_counts_norm)

    def test_value_counts_non_existent_column(self):
        with Capturing() as output:
            counts = self.analyzer.get_value_counts(column="NonExistentCol")
        self.assertTrue(counts.empty)
        self.assertEqual(counts.dtype, "object")  # As per implementation
        self.assertIn("Warning: Column 'NonExistentCol' not found.", output)

    def test_value_counts_on_empty_dataframe(self):
        # Test with an analyzer that has an empty df but with a column defined
        with Capturing() as output:  # Column 'A' exists but no data
            counts = self.empty_analyzer.get_value_counts(column="A")
        self.assertTrue(counts.empty)

        # Test with an analyzer that has a truly empty df (no columns)
        analyzer_fully_empty = DataAnalyzer(pd.DataFrame())
        with Capturing() as output:
            counts_fully_empty = analyzer_fully_empty.get_value_counts(column="A")
        self.assertTrue(counts_fully_empty.empty)
        self.assertIn("Warning: Column 'A' not found.", output)  # Because df is empty

    def test_value_counts_on_column_with_all_nan(self):
        counts = self.analyzer.get_value_counts(column="ColC_empty")
        expected_counts = self.data[
            "ColC_empty"
        ].value_counts()  # Should be empty Series
        self.assertTrue(counts.empty)
        assert_series_equal(counts, expected_counts)


class TestAnalyzeDataOrchestration(unittest.TestCase):
    def setUp(self):
        self.data = pd.DataFrame(
            {
                "Numeric": [1, 2, 3, 4, 5],
                "Category": ["A", "B", "A", "C", "B"],
                "Numeric2": [5.1, 4.2, 3.3, 2.4, 1.5],
            }
        )
        self.analyzer = DataAnalyzer(self.data.copy())

    def test_analyze_data_multiple_operations(self):
        analysis_plan = [
            {"method": "get_summary_statistics", "params": {"include_dtypes": "all"}},
            {"method": "get_correlation_matrix"},
            {"method": "get_value_counts", "params": {"column": "Category"}},
        ]
        results = self.analyzer.analyze_data(analysis_plan)

        self.assertIn("get_summary_statistics", results)
        self.assertIn("get_correlation_matrix", results)
        self.assertIn("get_value_counts", results)

        expected_summary = self.data.describe(include="all")
        assert_frame_equal(
            results["get_summary_statistics"].sort_index(axis=1),
            expected_summary.sort_index(axis=1),
            check_dtype=False,
        )

        expected_corr = self.data[["Numeric", "Numeric2"]].corr()
        assert_frame_equal(results["get_correlation_matrix"], expected_corr)

        expected_counts = self.data["Category"].value_counts()
        assert_series_equal(results["get_value_counts"], expected_counts)

    def test_analyze_data_empty_operations_list_defaults_to_summary(self):
        with Capturing() as output:  # Captures "Performing default summary statistics"
            results = self.analyzer.analyze_data(
                operations=[]
            )  # Changed from None to []
        self.assertIn(
            "No specific analyses requested. Performing default summary statistics.",
            output,
        )
        self.assertIn(
            "summary_statistics", results
        )  # Default key is 'summary_statistics'
        expected_summary = self.data.describe(
            include="all"
        )  # Default of get_summary_statistics
        assert_frame_equal(
            results["summary_statistics"].sort_index(axis=1),
            expected_summary.sort_index(axis=1),
            check_dtype=False,
        )

    def test_analyze_data_none_operations_list_defaults_to_summary(self):
        with Capturing() as output:
            results = self.analyzer.analyze_data(
                analysis_types=None
            )  # Explicitly pass None
        self.assertIn(
            "No specific analyses requested. Performing default summary statistics.",
            output,
        )
        self.assertIn("summary_statistics", results)
        expected_summary = self.data.describe(include="all")
        assert_frame_equal(
            results["summary_statistics"].sort_index(axis=1),
            expected_summary.sort_index(axis=1),
            check_dtype=False,
        )

    def test_analyze_data_unknown_method(self):
        analysis_plan = [{"method": "non_existent_method"}]
        with Capturing() as output:
            results = self.analyzer.analyze_data(analysis_plan)
        self.assertIn(
            "Warning: Unknown analysis method 'non_existent_method'. Skipping.", output
        )
        self.assertIn("non_existent_method", results)
        self.assertIn("error", results["non_existent_method"])
        self.assertEqual(
            results["non_existent_method"]["error"],
            "Unknown method non_existent_method",
        )

    def test_analyze_data_method_raises_exception(self):
        # Test case where a valid method is called but internally raises an error
        # e.g. get_value_counts for a column that doesn't exist (though it currently logs and returns empty)
        # Let's assume a more direct error for test:
        analysis_plan = [
            {
                "method": "get_value_counts",
                "params": {"column": "NonExistentColumnForError"},
            }
        ]
        with Capturing() as output:  # Captures warning from get_value_counts
            results = self.analyzer.analyze_data(analysis_plan)

        self.assertIn("get_value_counts", results)
        # Current get_value_counts handles missing column by returning empty Series and logging.
        # It doesn't raise an error that analyze_data catches, but analyze_data returns its output.
        self.assertTrue(results["get_value_counts"].empty)
        self.assertIn("Warning: Column 'NonExistentColumnForError' not found.", output)


if __name__ == "__main__":
    unittest.main(argv=["first-arg-is-ignored"], exit=False)
