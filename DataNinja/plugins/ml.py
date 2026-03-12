import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score


class MLModel:
    """Machine learning model wrapper with training and evaluation."""
    
    def __init__(self, model_type: str = "logistic_regression", params: dict = None):
        """Initialize ML model."""
        self.model_type = model_type
        self.params = params or {}
        
        if model_type == "logistic_regression":
            self.model = LogisticRegression(**self.params)
        else:
            raise ValueError(f"Unsupported model_type: {model_type}")

    def train(self, X: np.ndarray, y: np.ndarray) -> None:
        """Train the model with features X and target y."""
        if self.model is None:
            raise RuntimeError("Model not initialized")
        self.model.fit(X, y)

    def predict(self, X: np.ndarray) -> np.ndarray:
        """Make predictions using the trained model."""
        if not isinstance(X, np.ndarray):
            raise ValueError("Input data must be a numpy array")
        if self.model is None:
            raise RuntimeError("Model not initialized")
        return self.model.predict(X)

    def evaluate(self, X_test: np.ndarray, y_test: np.ndarray, average_method: str = "binary") -> dict:
        """Evaluate model performance on test data."""
        if not isinstance(X_test, np.ndarray) or not isinstance(y_test, np.ndarray):
            raise ValueError("Test data must be numpy arrays")
        
        y_pred = self.predict(X_test)
        
        return {
            "accuracy": accuracy_score(y_test, y_pred),
            "precision": precision_score(y_test, y_pred, average=average_method, zero_division=0),
            "recall": recall_score(y_test, y_pred, average=average_method, zero_division=0)
        }
