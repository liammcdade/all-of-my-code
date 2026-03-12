import pandas as pd
from sklearn.preprocessing import MinMaxScaler, OneHotEncoder
import numpy as np


class DataTransformer:
    """
    Applies various transformations to datasets.

    The class is initialized with data (ideally a pandas DataFrame).
    It provides methods for common data transformation tasks like scaling,
    encoding, and feature engineering.
    """

    def __init__(self, data):
        """
        Initializes the DataTransformer with the dataset.

        Args:
            data: The data to be transformed. Expected to be a pandas DataFrame
                  or convertible to one (e.g., list of lists with header).
        """
        if data is None:
            raise ValueError("Input data cannot be None.")

        if isinstance(data, pd.DataFrame):
            self.data = data
        elif isinstance(data, list):
            try:
                if data and isinstance(data[0], list):  # Assuming header row
                    self.data = pd.DataFrame(data[1:], columns=data[0])
                else:
                    self.data = pd.DataFrame(data)
            except Exception as e:
                raise ValueError(
                    f"Could not convert list to DataFrame for transformation: {e}"
                )
        else:
            raise TypeError(
                "Unsupported data type. Please provide a pandas DataFrame or a convertible list of lists."
            )

        if self.data.empty:
            print("Warning: Initialized DataTransformer with an empty DataFrame.")

        self.scalers = {}  # To store fitted scalers for inverse_transform if needed
        self.encoders = {}  # To store fitted encoders

    def transform_data(self, transformations):
        """
        Applies a series of specified transformations to the data.

        Args:
            transformations (list of dict): A list of transformation operations.
                Each dict should specify the 'method' name and 'params' for it.
                Example: [
                    {'method': 'scale_numerical_features', 'params': {'columns': ['age', 'salary'], 'scaler_type': 'minmax'}},
                    {'method': 'encode_categorical_features', 'params': {'columns': ['category'], 'encoder_type': 'onehot'}}
                ]

        Returns:
            pd.DataFrame: The transformed DataFrame.
        """
        if not isinstance(self.data, pd.DataFrame):
            print(
                "Warning: Data is not a pandas DataFrame. Transformation capabilities may be limited."
            )
            return self.data  # Or raise error

        transformed_df = self.data.copy()  # Work on a copy

        for trans_spec in transformations:
            method_name = trans_spec.get("method")
            params = trans_spec.get("params", {})

            if hasattr(self, method_name) and callable(getattr(self, method_name)):
                print(f"Applying transformation: {method_name} with params: {params}")
                try:
                    # Pass the current state of the DataFrame to the method
                    transformed_df = getattr(self, method_name)(
                        transformed_df, **params
                    )
                except Exception as e:
                    print(f"Error during transformation '{method_name}': {e}")
                    # Optionally, decide if to stop or continue
            else:
                print(
                    f"Warning: Unknown transformation method '{method_name}'. Skipping."
                )

        self.data = (
            transformed_df  # Update internal data with the fully transformed version
        )
        return self.data

    def scale_numerical_features(self, df, columns, scaler_type="minmax", **kwargs):
        """
        Scales specified numerical columns using a chosen scaler.

        Args:
            df (pd.DataFrame): The DataFrame to transform.
            columns (list of str): List of numerical column names to scale.
            scaler_type (str): Type of scaler to use ('minmax', 'standard', etc.).
                               Currently only 'minmax' is implemented.
            **kwargs: Additional arguments for the scaler.

        Returns:
            pd.DataFrame: DataFrame with scaled numerical features.
        """
        if not isinstance(df, pd.DataFrame) or df.empty:
            print("Data is not a valid DataFrame or is empty.")
            return df

        print(f"Scaling numerical features: {columns} using {scaler_type} scaler...")

        for col in columns:
            if col not in df.columns:
                print(f"Warning: Column '{col}' not found for scaling. Skipping.")
                continue
            if not pd.api.types.is_numeric_dtype(df[col]):
                print(f"Warning: Column '{col}' is not numeric. Skipping scaling.")
                continue

            feature_data = df[[col]].copy()  # Scaler expects 2D array

            # Handle NaN values before scaling: either error, impute, or skip.
            # For simplicity here, we'll proceed, but MinMaxScaler will error on NaNs.
            if feature_data.isnull().values.any():
                print(
                    f"Warning: Column '{col}' contains NaN values. Scaler may fail or produce NaNs."
                )
                # df[col] = df[col].fillna(df[col].mean()) # Example: Impute NaNs - careful with data leakage

            if scaler_type == "minmax":
                scaler = MinMaxScaler(**kwargs)
            # Elif scaler_type == 'standard':
            # from sklearn.preprocessing import StandardScaler
            #     scaler = StandardScaler(**kwargs)
            else:
                print(
                    f"Warning: Scaler type '{scaler_type}' not recognized. Skipping column '{col}'."
                )
                continue

            try:
                # Fit and transform the column
                scaled_values = scaler.fit_transform(feature_data)
                # Update the DataFrame column with scaled values
                df[col] = scaled_values
                self.scalers[col] = scaler  # Store the fitted scaler
            except Exception as e:
                print(f"Error scaling column '{col}': {e}")
        return df

    def encode_categorical_features(self, df, columns, encoder_type="onehot", **kwargs):
        """
        Encodes specified categorical columns.

        Args:
            df (pd.DataFrame): The DataFrame to transform.
            columns (list of str): List of categorical column names to encode.
            encoder_type (str): Type of encoder ('onehot', 'label').
                                Currently only 'onehot' is implemented.
            **kwargs: Additional arguments for the encoder (e.g., drop='first' for OneHotEncoder).

        Returns:
            pd.DataFrame: DataFrame with encoded categorical features.
                          Original categorical columns are typically dropped.
        """
        if not isinstance(df, pd.DataFrame) or df.empty:
            print("Data is not a valid DataFrame or is empty.")
            return df

        print(
            f"Encoding categorical features: {columns} using {encoder_type} encoder..."
        )

        for col in columns:
            if col not in df.columns:
                print(f"Warning: Column '{col}' not found for encoding. Skipping.")
                continue
            # It's good practice to ensure the column is treated as categorical/object
            # if not pd.api.types.is_object_dtype(df[col]) and not pd.api.types.is_categorical_dtype(df[col]):
            #     print(f"Warning: Column '{col}' may not be categorical. Proceeding with encoding.")

            if encoder_type == "onehot":
                # Handle NaN values before encoding if necessary.
                # OneHotEncoder can handle NaNs if configured (e.g., handle_unknown='ignore' or by imputation)
                # For simplicity, let's fill NaNs with a placeholder string if this is desired.
                # current_col_data = df[[col]].fillna('Unknown') # Example: fill NaNs
                current_col_data = df[[col]]

                # Default to drop=None which keeps all categories. 'first' drops the first to avoid multicollinearity.
                drop_behavior = kwargs.pop("drop", None)
                encoder = OneHotEncoder(
                    sparse_output=False,
                    handle_unknown="ignore",
                    drop=drop_behavior,
                    **kwargs,
                )

                try:
                    encoded_data = encoder.fit_transform(current_col_data)
                    feature_names = encoder.get_feature_names_out([col])

                    encoded_df = pd.DataFrame(
                        encoded_data, columns=feature_names, index=df.index
                    )

                    # Drop original column and concatenate new encoded columns
                    df = df.drop(col, axis=1)
                    df = pd.concat([df, encoded_df], axis=1)
                    self.encoders[col] = encoder  # Store fitted encoder
                except Exception as e:
                    print(f"Error encoding column '{col}' with OneHotEncoder: {e}")
            # Elif encoder_type == 'label':
            # from sklearn.preprocessing import LabelEncoder
            #     encoder = LabelEncoder(**kwargs)
            #     try:
            #         df[col] = encoder.fit_transform(df[col].astype(str)) # LabelEncoder prefers string input
            #         self.encoders[col] = encoder
            #     except Exception as e:
            # print(f"Error label encoding column '{col}': {e}")
            else:
                print(
                    f"Warning: Encoder type '{encoder_type}' not recognized. Skipping column '{col}'."
                )
        return df

    def get_transformed_data(self):
        """
        Returns the current state of the transformed data.
        """
        return self.data


if __name__ == "__main__":
    print("--- DataTransformer Demonstration ---")

    # Sample data
    data_dict = {
        "ID": [1, 2, 3, 4, 5, 6],
        "Age": [25, 30, 22, 35, 28, 40.0],  # Added float for MinMax an NaN test
        "Salary": [50000, 60000, 45000, 75000, 58000, np.nan],  # Added NaN
        "City": [
            "New York",
            "Los Angeles",
            "Chicago",
            "New York",
            "Chicago",
            "Los Angeles",
        ],
        "Gender": ["Male", "Female", "Male", "Female", "Male", "Female"],
    }
    sample_df = pd.DataFrame(data_dict)

    print("\n--- Example 1: Scaling and Encoding ---")
    try:
        transformer1 = DataTransformer(sample_df.copy())
        print("Original DataFrame:")
        print(transformer1.get_transformed_data())

        transformations = [
            {
                "method": "scale_numerical_features",
                "params": {"columns": ["Age", "Salary"], "scaler_type": "minmax"},
            },
            {
                "method": "encode_categorical_features",
                "params": {
                    "columns": ["City", "Gender"],
                    "encoder_type": "onehot",
                    "drop": "first",
                },
            },
        ]

        transformer1.transform_data(transformations)
        print("\nTransformed DataFrame:")
        print(transformer1.get_transformed_data().head())

        # Check stored scalers/encoders
        print("\nStored Scalers:", transformer1.scalers.keys())
        print("Stored Encoders:", transformer1.encoders.keys())

    except Exception as e:
        print(f"Error in Example 1: {e}")

    print("\n--- Example 2: Handling missing columns and types ---")
    try:
        transformer2 = DataTransformer(sample_df.copy())
        transformations_err = [
            {
                "method": "scale_numerical_features",
                "params": {
                    "columns": ["Age", "NonExistentColumn"],
                    "scaler_type": "minmax",
                },
            },
            {
                "method": "encode_categorical_features",
                "params": {"columns": ["Salary"], "encoder_type": "onehot"},
            },  # Salary is numeric
        ]
        transformer2.transform_data(transformations_err)
        print("\nDataFrame after transformations with warnings/errors:")
        print(transformer2.get_transformed_data().head())
    except Exception as e:
        print(f"Error in Example 2: {e}")

    print("\n--- Example 3: List of Lists initialization ---")
    data_lol = [
        ["Name", "Score", "Grade"],
        ["Alice", 85, "A"],
        ["Bob", 92, "A+"],
        ["Charlie", 70, "B"],
    ]
    try:
        transformer3 = DataTransformer(data_lol)
        print("\nOriginal DataFrame from LoL:")
        print(transformer3.get_transformed_data())

        transformations_lol = [
            {"method": "scale_numerical_features", "params": {"columns": ["Score"]}},
            {
                "method": "encode_categorical_features",
                "params": {"columns": ["Grade"], "drop": "first"},
            },
        ]
        transformer3.transform_data(transformations_lol)
        print("\nTransformed DataFrame from LoL:")
        print(transformer3.get_transformed_data())

    except Exception as e:
        print(f"Error in Example 3: {e}")
