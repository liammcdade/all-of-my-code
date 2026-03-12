import unittest
import pandas as pd
import numpy as np
from pandas.testing import assert_frame_equal, assert_series_equal
import io
import sys
import logging  # For capturing print output from the class

from DataNinja.core.transformer import DataTransformer
from sklearn.preprocessing import MinMaxScaler, OneHotEncoder  # For verifying behavior


# Helper to capture print/logging outputs
class Capturing(list):
    def __enter__(self):
        self._stdout = sys.stdout
        sys.stdout = self._stringio = io.StringIO()
        self.logger = logging.getLogger()  # Root logger or specific if known
        self.log_level = self.logger.level
        # self.logger.setLevel(logging.DEBUG) # Capture all levels if class uses logging
        # self.log_handler = logging.StreamHandler(self._stringio)
        # self.logger.addHandler(self.log_handler)
        # Current class uses print, so only stdout needs capture for warnings
        return self

    def __exit__(self, *args):
        self.extend(self._stringio.getvalue().splitlines())
        del self._stringio
        sys.stdout = self._stdout
        # self.logger.removeHandler(self.log_handler)
        # self.logger.setLevel(self.log_level)


class TestTransformerInitialization(unittest.TestCase):
    def test_init_with_dataframe(self):
        df = pd.DataFrame({"A": [1, 2]})
        transformer = DataTransformer(data=df)
        assert_frame_equal(transformer.data, df)
        self.assertIsNotNone(transformer.scalers)
        self.assertIsNotNone(transformer.encoders)

    def test_init_with_list_of_lists_with_header(self):
        data_lol = [["A", "B"], [1, 3], [2, 4]]
        expected_df = pd.DataFrame([[1, 3], [2, 4]], columns=["A", "B"])
        transformer = DataTransformer(data=data_lol)
        assert_frame_equal(transformer.data, expected_df)

    def test_init_with_empty_dataframe(self):
        with Capturing() as output:
            transformer = DataTransformer(data=pd.DataFrame())
        self.assertTrue(transformer.data.empty)
        self.assertIn(
            "Warning: Initialized DataTransformer with an empty DataFrame.", output
        )

    def test_init_with_none_raises_valueerror(self):
        with self.assertRaisesRegex(ValueError, "Input data cannot be None."):
            DataTransformer(data=None)

    def test_init_with_unsupported_type_raises_typeerror(self):
        with self.assertRaisesRegex(TypeError, "Unsupported data type."):
            DataTransformer(data="a string")

    def test_init_with_ragged_list_raises_valueerror(self):
        data_ragged = [["A", "B"], [1, 2, 3], [4, 5]]
        with self.assertRaisesRegex(
            ValueError, "Could not convert list to DataFrame for transformation"
        ):
            DataTransformer(data=data_ragged)


class TestScaleNumericalFeatures(unittest.TestCase):
    def setUp(self):
        self.data = pd.DataFrame(
            {
                "Numeric1": [10.0, 20.0, 30.0, 40.0, 50.0],  # Use float for consistency
                "Numeric2": [1.0, 2.0, 3.0, 4.0, np.nan],
                "StringCol": ["a", "b", "c", "d", "e"],
                "Numeric3_all_same": [5.0, 5.0, 5.0, 5.0, 5.0],
            }
        )
        # For methods that modify df passed as argument, instantiate transformer with a dummy/copy
        self.transformer_instance = DataTransformer(self.data.copy())

    def test_minmax_scaling_basic(self):
        df_copy = self.data.copy()
        scaled_df = self.transformer_instance.scale_numerical_features(
            df=df_copy, columns=["Numeric1"], scaler_type="minmax"
        )
        self.assertTrue(
            (scaled_df["Numeric1"] >= 0).all() and (scaled_df["Numeric1"] <= 1).all()
        )
        self.assertEqual(scaled_df["Numeric1"].min(), 0.0)
        self.assertEqual(scaled_df["Numeric1"].max(), 1.0)
        assert_series_equal(
            scaled_df["Numeric2"], self.data["Numeric2"], check_dtype=False
        )  # Unchanged
        self.assertIn(
            "Numeric1", self.transformer_instance.scalers
        )  # Check scaler stored

    def test_minmax_scaling_with_nan_column_is_skipped_due_to_error(self):
        df_copy = self.data.copy()
        with Capturing() as output:
            scaled_df = self.transformer_instance.scale_numerical_features(
                df=df_copy,
                columns=["Numeric2"],  # This column has NaN
                scaler_type="minmax",
            )
        # MinMaxScaler raises ValueError on NaN. The transformer catches this, logs, and returns df unchanged for that col.
        self.assertTrue(
            any("Error scaling column 'Numeric2'" in line for line in output)
        )
        assert_series_equal(
            scaled_df["Numeric2"], self.data["Numeric2"], check_dtype=False
        )  # Column remains unscaled
        self.assertNotIn(
            "Numeric2", self.transformer_instance.scalers
        )  # Scaler not stored due to error

    def test_scaling_non_numeric_column_is_skipped(self):
        df_copy = self.data.copy()
        with Capturing() as output:
            scaled_df = self.transformer_instance.scale_numerical_features(
                df=df_copy, columns=["StringCol"], scaler_type="minmax"
            )
        self.assertIn(
            "Warning: Column 'StringCol' is not numeric. Skipping scaling.", output
        )
        assert_series_equal(scaled_df["StringCol"], self.data["StringCol"])  # Unchanged
        self.assertNotIn("StringCol", self.transformer_instance.scalers)

    def test_scaling_non_existent_column_is_skipped(self):
        df_copy = self.data.copy()
        with Capturing() as output:
            scaled_df = self.transformer_instance.scale_numerical_features(
                df=df_copy, columns=["NonExistentCol"], scaler_type="minmax"
            )
        self.assertIn(
            "Warning: Column 'NonExistentCol' not found for scaling. Skipping.", output
        )
        self.assertNotIn("NonExistentCol", self.transformer_instance.scalers)

    def test_scaling_on_empty_dataframe(self):
        empty_df = pd.DataFrame()
        transformer_empty = DataTransformer(empty_df.copy())  # Init with empty
        with Capturing() as output:  # Method also prints warning
            scaled_df = transformer_empty.scale_numerical_features(
                df=empty_df.copy(),  # Pass empty df to method
                columns=["AnyCol"],
                scaler_type="minmax",
            )
        self.assertTrue(scaled_df.empty)
        self.assertIn("Data is not a valid DataFrame or is empty.", output)

    def test_unrecognized_scaler_type_is_skipped(self):
        df_copy = self.data.copy()
        with Capturing() as output:
            scaled_df = self.transformer_instance.scale_numerical_features(
                df=df_copy, columns=["Numeric1"], scaler_type="unknown_scaler"
            )
        self.assertIn(
            "Warning: Scaler type 'unknown_scaler' not recognized. Skipping column 'Numeric1'.",
            output,
        )
        assert_series_equal(scaled_df["Numeric1"], self.data["Numeric1"])  # Unchanged
        self.assertNotIn("Numeric1", self.transformer_instance.scalers)

    def test_minmax_scaling_column_with_all_same_values(self):
        # MinMaxScaler should handle this by scaling all to 0 if min == max,
        # unless feature_range is different or clip=True. Default behavior is 0.
        df_copy = self.data.copy()
        scaled_df = self.transformer_instance.scale_numerical_features(
            df=df_copy, columns=["Numeric3_all_same"], scaler_type="minmax"
        )
        # All values should be 0 or a constant within [0,1] depending on min==max handling
        # For MinMaxScaler, if min==max, it results in all 0s.
        self.assertTrue((scaled_df["Numeric3_all_same"] == 0.0).all())
        self.assertIn("Numeric3_all_same", self.transformer_instance.scalers)


class TestEncodeCategoricalFeatures(unittest.TestCase):
    def setUp(self):
        self.data = pd.DataFrame(
            {
                "Category1": ["A", "B", "A", "C", "B"],
                "Category2": ["X", "Y", np.nan, "X", "Y"],  # With NaN
                "NumericCol": [1, 2, 3, 4, 5],
                "IntCategory": [
                    10,
                    20,
                    10,
                    30,
                    20,
                ],  # Numeric but could be treated as categorical
            }
        )
        self.transformer_instance = DataTransformer(self.data.copy())

    def test_onehot_encoding_basic(self):
        df_copy = self.data.copy()
        encoded_df = self.transformer_instance.encode_categorical_features(
            df=df_copy, columns=["Category1"], encoder_type="onehot"
        )
        self.assertNotIn("Category1", encoded_df.columns)
        self.assertIn("Category1_A", encoded_df.columns)
        self.assertIn("Category1_B", encoded_df.columns)
        self.assertIn("Category1_C", encoded_df.columns)
        self.assertTrue(
            (
                encoded_df[["Category1_A", "Category1_B", "Category1_C"]].sum(axis=1)
                == 1
            ).all()
        )
        self.assertIn("Category1", self.transformer_instance.encoders)

    def test_onehot_encoding_with_drop_first(self):
        df_copy = self.data.copy()
        encoded_df = self.transformer_instance.encode_categorical_features(
            df=df_copy,
            columns=["Category1"],
            encoder_type="onehot",
            drop="first",  # Passed as kwarg
        )
        self.assertNotIn("Category1", encoded_df.columns)
        # One of the categories will be dropped. Check if total number of new columns is num_categories - 1
        # Categories for 'Category1' are A, B, C. So 2 columns expected.
        generated_cols = [
            col for col in encoded_df.columns if col.startswith("Category1_")
        ]
        self.assertEqual(len(generated_cols), 2)
        self.assertIn("Category1", self.transformer_instance.encoders)

    def test_onehot_encoding_with_nan_values(self):
        # OneHotEncoder's handle_unknown='ignore' (default in our code) means it will learn NaNs if present during fit.
        # If NaNs are seen during transform but not fit, they get all zeros for the new columns.
        # Our current code applies fit_transform on the column data directly.
        # Pandas get_dummies treats NaNs as a category if dummy_na=True. OHE is different.
        # OHE by default will error on NaNs if not handled.
        # The current implementation in DataTransformer doesn't explicitly fill NaNs before OHE.
        # OHE(sparse=False, handle_unknown='ignore') will treat NaN as a distinct category if present during fit.
        df_copy = self.data.copy()
        encoded_df = self.transformer_instance.encode_categorical_features(
            df=df_copy,
            columns=["Category2"],  # This column has NaN
            encoder_type="onehot",
        )
        self.assertNotIn("Category2", encoded_df.columns)
        # Expect columns for 'X', 'Y', and 'nan' if OHE treats nan as a category
        # OHE's get_feature_names_out creates names like 'Category2_X', 'Category2_Y', 'Category2_nan'
        self.assertIn("Category2_X", encoded_df.columns)
        self.assertIn("Category2_Y", encoded_df.columns)
        self.assertIn("Category2_nan", encoded_df.columns)  # Check for NaN category
        self.assertIn("Category2", self.transformer_instance.encoders)

    def test_encoding_numeric_column_as_category(self):
        # OneHotEncoder can technically encode numeric columns if they are passed.
        # It will treat each unique number as a category.
        df_copy = self.data.copy()
        encoded_df = self.transformer_instance.encode_categorical_features(
            df=df_copy, columns=["IntCategory"], encoder_type="onehot"
        )
        self.assertNotIn("IntCategory", encoded_df.columns)
        self.assertIn("IntCategory_10", encoded_df.columns)
        self.assertIn("IntCategory_20", encoded_df.columns)
        self.assertIn("IntCategory_30", encoded_df.columns)
        self.assertIn("IntCategory", self.transformer_instance.encoders)

    def test_encoding_non_existent_column_is_skipped(self):
        df_copy = self.data.copy()
        with Capturing() as output:
            encoded_df = self.transformer_instance.encode_categorical_features(
                df=df_copy, columns=["NonExistentCat"], encoder_type="onehot"
            )
        self.assertIn(
            "Warning: Column 'NonExistentCat' not found for encoding. Skipping.", output
        )
        assert_frame_equal(encoded_df, self.data)  # Should be unchanged
        self.assertNotIn("NonExistentCat", self.transformer_instance.encoders)

    def test_encoding_on_empty_dataframe(self):
        empty_df = pd.DataFrame(columns=["A"])
        transformer_empty = DataTransformer(empty_df.copy())
        with Capturing() as output:
            scaled_df = transformer_empty.encode_categorical_features(
                df=empty_df.copy(), columns=["A"], encoder_type="onehot"
            )
        self.assertTrue(scaled_df.empty)
        # This message is from the start of the method if df is empty
        self.assertIn("Data is not a valid DataFrame or is empty.", output)

    def test_unrecognized_encoder_type_is_skipped(self):
        df_copy = self.data.copy()
        with Capturing() as output:
            encoded_df = self.transformer_instance.encode_categorical_features(
                df=df_copy, columns=["Category1"], encoder_type="unknown_encoder"
            )
        self.assertIn(
            "Warning: Encoder type 'unknown_encoder' not recognized. Skipping column 'Category1'.",
            output,
        )
        assert_frame_equal(encoded_df, self.data)  # Should be unchanged
        self.assertNotIn("Category1", self.transformer_instance.encoders)


class TestTransformDataOrchestration(unittest.TestCase):
    def setUp(self):
        self.data = pd.DataFrame(
            {
                "Num": [10.0, 20.0, 30.0, np.nan],  # Float for scaling, with NaN
                "Cat": ["P", "Q", "P", "Q"],
                "Cat2": ["X", "Y", "X", np.nan],  # Categorical with NaN
            }
        )
        # For transform_data, the transformer instance's self.data is modified
        self.transformer = DataTransformer(self.data.copy())

    def test_transform_data_sequence_scale_and_encode(self):
        transformations = [
            {
                "method": "scale_numerical_features",
                "params": {"columns": ["Num"], "scaler_type": "minmax"},
            },
            {
                "method": "encode_categorical_features",
                "params": {
                    "columns": ["Cat"],
                    "encoder_type": "onehot",
                    "drop": "first",
                },
            },
        ]

        # Before transform, self.data is original
        assert_frame_equal(self.transformer.get_transformed_data(), self.data)

        with Capturing() as output:  # To check for error on scaling 'Num' with NaN
            self.transformer.transform_data(transformations)

        transformed_df = self.transformer.get_transformed_data()

        # Check scaling of 'Num' (should be unchanged due to NaN causing error in MinMax, caught by transformer)
        self.assertTrue(any("Error scaling column 'Num'" in line for line in output))
        assert_series_equal(
            transformed_df["Num"], self.data["Num"], check_dtype=False
        )  # Unchanged

        # Check encoding of 'Cat'
        self.assertNotIn("Cat", transformed_df.columns)
        # Depending on which category ('P' or 'Q') is dropped first
        cat_cols_present = [
            col for col in transformed_df.columns if col.startswith("Cat_")
        ]
        self.assertEqual(len(cat_cols_present), 1)  # One column because drop='first'
        self.assertTrue("Cat_P" in cat_cols_present or "Cat_Q" in cat_cols_present)

        # Check that Cat2 is still there and unchanged
        assert_series_equal(transformed_df["Cat2"], self.data["Cat2"])

    def test_transform_data_empty_operations_list(self):
        original_df_copy = self.transformer.data.copy()
        self.transformer.transform_data(transformations=[])
        transformed_df = self.transformer.get_transformed_data()
        assert_frame_equal(transformed_df, original_df_copy)  # Should be unchanged

    def test_transform_data_unknown_method_is_skipped(self):
        original_df_copy = self.transformer.data.copy()
        transformations = [{"method": "non_existent_transform", "params": {}}]
        with Capturing() as output:
            self.transformer.transform_data(transformations)
        transformed_df = self.transformer.get_transformed_data()
        self.assertIn(
            "Warning: Unknown transformation method 'non_existent_transform'. Skipping.",
            output,
        )
        assert_frame_equal(transformed_df, original_df_copy)  # Unchanged

    def test_transform_data_operation_fails_midway_continues(self):
        # First op: scale 'Num' (will error due to NaN but is caught, Num remains same)
        # Second op: encode 'Cat2' (should proceed)
        transformations = [
            {
                "method": "scale_numerical_features",
                "params": {"columns": ["Num"], "scaler_type": "minmax"},
            },
            {
                "method": "encode_categorical_features",
                "params": {"columns": ["Cat2"], "encoder_type": "onehot"},
            },
        ]
        with Capturing() as output:
            self.transformer.transform_data(transformations)

        transformed_df = self.transformer.get_transformed_data()

        self.assertTrue(
            any("Error scaling column 'Num'" in line for line in output)
        )  # Scaling error
        assert_series_equal(
            transformed_df["Num"], self.data["Num"], check_dtype=False
        )  # Num unchanged

        # Encoding of 'Cat2' should have happened
        self.assertNotIn("Cat2", transformed_df.columns)
        self.assertIn("Cat2_X", transformed_df.columns)
        self.assertIn("Cat2_Y", transformed_df.columns)
        self.assertIn("Cat2_nan", transformed_df.columns)  # NaN category from Cat2

        # Original 'Cat' column should be untouched
        assert_series_equal(transformed_df["Cat"], self.data["Cat"])


if __name__ == "__main__":
    unittest.main(argv=["first-arg-is-ignored"], exit=False)
