import unittest
from unittest.mock import patch, MagicMock, ANY
import pandas as pd
import numpy as np
import os
import tempfile
import shutil
import io  # For Capturing
import sys  # For Capturing

from DataNinja.core.plotter import DataPlotter

# matplotlib.pyplot is implicitly imported by DataPlotter,
# and its functions like show() or savefig() are what we'll often mock.


# Helper to capture print/logging outputs
class Capturing(list):
    def __enter__(self):
        self._stdout = sys.stdout
        sys.stdout = self._stringio = io.StringIO()
        return self

    def __exit__(self, *args):
        self.extend(self._stringio.getvalue().splitlines())
        del self._stringio
        sys.stdout = self._stdout


class TestPlotterInitialization(unittest.TestCase):
    def test_init_with_dataframe(self):
        df = pd.DataFrame({"A": [1, 2]})
        plotter = DataPlotter(data=df)
        assert_frame_equal(plotter.data, df)

    def test_init_with_list_of_lists_with_header(self):
        data_lol = [["A", "B"], [1, 3], [2, 4]]
        expected_df = pd.DataFrame([[1, 3], [2, 4]], columns=["A", "B"])
        plotter = DataPlotter(data=data_lol)
        assert_frame_equal(plotter.data, expected_df)

    def test_init_with_empty_dataframe(self):
        with Capturing() as output:
            plotter = DataPlotter(data=pd.DataFrame())
        self.assertTrue(plotter.data.empty)
        self.assertIn(
            "Warning: Initialized DataPlotter with an empty DataFrame.", output
        )

    def test_init_with_none_raises_valueerror(self):
        with self.assertRaisesRegex(ValueError, "Input data cannot be None."):
            DataPlotter(data=None)

    def test_init_with_unsupported_type_raises_typeerror(self):
        with self.assertRaisesRegex(TypeError, "Unsupported data type."):
            DataPlotter(data="a string")


class TestCreatePlotMethodDispatch(unittest.TestCase):
    def setUp(self):
        self.df = pd.DataFrame({"A": [1, 2, 3], "B": [4, 5, 6], "C": ["x", "y", "x"]})
        self.plotter = DataPlotter(self.df)

    @patch("DataNinja.core.plotter.DataPlotter.plot_histogram")
    @patch("matplotlib.pyplot.show")  # create_plot calls show
    def test_create_plot_dispatches_to_histogram(self, mock_show, mock_plot_histogram):
        # Mock plot_histogram to return a MagicMock(figure) so create_plot can call show/savefig
        mock_fig = MagicMock()
        mock_plot_histogram.return_value = mock_fig

        self.plotter.create_plot("histogram", column="A", bins=5)
        mock_plot_histogram.assert_called_once_with(column="A", bins=5)
        mock_show.assert_called_once()

    @patch("DataNinja.core.plotter.DataPlotter.plot_scatter")
    @patch("matplotlib.pyplot.show")
    def test_create_plot_dispatches_to_scatter(self, mock_show, mock_plot_scatter):
        mock_fig = MagicMock()
        mock_plot_scatter.return_value = mock_fig

        self.plotter.create_plot("scatter", x_column="A", y_column="B")
        mock_plot_scatter.assert_called_once_with(x_column="A", y_column="B")
        mock_show.assert_called_once()

    @patch("DataNinja.core.plotter.DataPlotter.plot_bar")
    @patch("matplotlib.pyplot.show")
    def test_create_plot_dispatches_to_bar(self, mock_show, mock_plot_bar):
        mock_fig = MagicMock()
        mock_plot_bar.return_value = mock_fig

        self.plotter.create_plot("bar", x_column="C", y_column="A")
        mock_plot_bar.assert_called_once_with(x_column="C", y_column="A")
        mock_show.assert_called_once()

    def test_create_plot_unsupported_type(self):
        with Capturing() as output:
            # Patch the specific plot methods to ensure they are NOT called.
            with patch.object(
                self.plotter, "plot_histogram"
            ) as mock_hist, patch.object(
                self.plotter, "plot_scatter"
            ) as mock_scatter, patch.object(
                self.plotter, "plot_bar"
            ) as mock_bar:

                result_fig = self.plotter.create_plot("unknown_plot_type", column="A")

                mock_hist.assert_not_called()
                mock_scatter.assert_not_called()
                mock_bar.assert_not_called()

        self.assertIn(
            "Warning: Plot type 'unknown_plot_type' is not supported", output[0]
        )
        self.assertIsNone(result_fig)


class TestSpecificPlotMethodExecution(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.df = pd.DataFrame(
            {
                "NumericCol": np.random.rand(20) * 10,
                "NumericCol2": np.random.rand(20) * 5,
                "CategoryCol": np.random.choice(["X", "Y", "Z", "W"], 20),
            }
        )
        self.plotter = DataPlotter(self.df.copy())
        self.empty_plotter = DataPlotter(pd.DataFrame())  # For testing with empty data

    def tearDown(self):
        shutil.rmtree(self.temp_dir)
        plt.close("all")  # Close all figures to avoid state leakage between tests

    # Test plot_histogram
    @patch("matplotlib.pyplot.show")  # Mock show for create_plot
    def test_plot_histogram_runs_via_create_plot_no_error(self, mock_show):
        try:
            fig = self.plotter.create_plot("histogram", column="NumericCol", bins=5)
            self.assertIsNotNone(fig)
            mock_show.assert_called_once()
        except Exception as e:
            self.fail(f"create_plot for histogram raised an exception: {e}")

    @patch("matplotlib.figure.Figure.savefig")
    def test_plot_histogram_saves_file_via_create_plot(self, mock_savefig):
        save_path = os.path.join(self.temp_dir, "hist.png")
        with patch(
            "matplotlib.pyplot.show"
        ) as mock_show:  # Ensure show is not called if saving
            fig = self.plotter.create_plot(
                "histogram", column="NumericCol", save_path=save_path
            )
            mock_show.assert_not_called()

        self.assertIsNotNone(fig)
        mock_savefig.assert_called_once_with(save_path)
        # Actual file existence check can be done if savefig is not fully mocked,
        # or by checking side_effect if mock_savefig creates the file.
        # For now, call to savefig is the main check.

    def test_plot_histogram_direct_call_missing_column(self):
        with Capturing() as output:
            fig = self.plotter.plot_histogram(column="NonExistentCol")
        self.assertIsNone(fig)
        self.assertIn("Column 'NonExistentCol' not found in data.", output)

    def test_plot_histogram_direct_call_non_numeric_column(self):
        with Capturing() as output:
            fig = self.plotter.plot_histogram(column="CategoryCol")
        # Plotter warns but seaborn might still try to plot or error depending on version
        # Current plotter code only warns and proceeds.
        self.assertIsNotNone(fig)  # Figure is created
        self.assertIn(
            "Warning: Column 'CategoryCol' is not numeric. Histogram may not be meaningful.",
            output,
        )
        plt.close(fig)  # Clean up the figure

    # Test plot_scatter
    @patch("matplotlib.pyplot.show")
    def test_plot_scatter_runs_via_create_plot_no_error(self, mock_show):
        try:
            fig = self.plotter.create_plot(
                "scatter", x_column="NumericCol", y_column="NumericCol2"
            )
            self.assertIsNotNone(fig)
            mock_show.assert_called_once()
        except Exception as e:
            self.fail(f"create_plot for scatter raised an exception: {e}")

    def test_plot_scatter_direct_call_missing_column(self):
        with Capturing() as output:
            fig = self.plotter.plot_scatter(
                x_column="NonExistent", y_column="NumericCol2"
            )
        self.assertIsNone(fig)
        self.assertIn(
            "One or both columns ('NonExistent', 'NumericCol2') not found in data.",
            output,
        )

    # Test plot_bar
    @patch("matplotlib.pyplot.show")
    def test_plot_bar_runs_via_create_plot_no_error(self, mock_show):
        try:
            fig = self.plotter.create_plot(
                "bar", x_column="CategoryCol", y_column="NumericCol"
            )
            self.assertIsNotNone(fig)
            mock_show.assert_called_once()
        except Exception as e:
            self.fail(f"create_plot for bar raised an exception: {e}")

    @patch("matplotlib.pyplot.show")
    def test_plot_bar_estimator_count_via_create_plot(self, mock_show):
        try:
            fig = self.plotter.create_plot(
                "bar", x_column="CategoryCol", y_column="NumericCol", estimator="count"
            )
            self.assertIsNotNone(fig)
            mock_show.assert_called_once()
        except Exception as e:
            self.fail(
                f"create_plot for bar with estimator='count' raised an exception: {e}"
            )

    def test_plot_bar_direct_call_missing_y_column(self):
        with Capturing() as output:
            fig = self.plotter.plot_bar(x_column="CategoryCol", y_column="NonExistentY")
        self.assertIsNone(fig)
        self.assertIn(
            "One or both columns ('CategoryCol', 'NonExistentY') not found in data.",
            output,
        )

    def test_plot_bar_direct_call_non_numeric_y_for_mean_estimator(self):
        # Add a string column to test this
        self.plotter.data["StringY"] = "test"
        with Capturing() as output:
            fig = self.plotter.plot_bar(
                x_column="CategoryCol", y_column="StringY", estimator="mean"
            )
        self.assertIsNotNone(
            fig
        )  # Plotter proceeds, seaborn might error or produce weird plot
        self.assertIn(
            "Warning: y_column 'StringY' must be numeric for estimators like 'mean' or 'sum'.",
            output,
        )
        plt.close(fig)


class TestPlottingWithEmptyOrInvalidData(unittest.TestCase):
    def setUp(self):
        self.empty_df = pd.DataFrame()
        self.plotter_empty_df = DataPlotter(self.empty_df.copy())

        # For testing plotter with data that is not a DataFrame internally
        # This state is hard to achieve as init usually converts or errors.
        # We can simulate it by manually setting plotter.data to something invalid AFTER init.
        self.plotter_invalid_internal_data = DataPlotter(
            pd.DataFrame({"A": [1]})
        )  # Valid init
        self.plotter_invalid_internal_data.data = (
            "not a dataframe"  # Force invalid state
        )

    @patch("matplotlib.pyplot.show")
    def test_create_plot_with_empty_dataframe_in_plotter(self, mock_show):
        with Capturing() as output:
            fig = self.plotter_empty_df.create_plot("histogram", column="A")
        self.assertIsNone(fig)
        self.assertIn(
            "Data is not a valid DataFrame or is empty. Cannot create plot.", output
        )
        mock_show.assert_not_called()

    @patch("matplotlib.pyplot.show")
    def test_create_plot_with_invalid_internal_data_in_plotter(self, mock_show):
        with Capturing() as output:
            fig = self.plotter_invalid_internal_data.create_plot(
                "histogram", column="A"
            )
        self.assertIsNone(fig)
        self.assertIn(
            "Data is not a valid DataFrame or is empty. Cannot create plot.", output
        )
        mock_show.assert_not_called()

    # Individual plot methods also check for empty/invalid data
    def test_plot_histogram_direct_call_with_empty_df_in_plotter(self):
        # This specific scenario is tricky: plot_histogram itself doesn't re-check self.data.empty
        # It relies on the column check. If self.data is empty, it has no columns.
        with Capturing() as output:
            fig = self.plotter_empty_df.plot_histogram(column="AnyCol")
        self.assertIsNone(fig)
        self.assertIn("Column 'AnyCol' not found in data.", output)


if __name__ == "__main__":
    unittest.main(argv=["first-arg-is-ignored"], exit=False)
