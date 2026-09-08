import pandas as pd
import numpy as np
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.impute import SimpleImputer
from sklearn.metrics import roc_auc_score, log_loss
from sklearn.pipeline import Pipeline
from tqdm import tqdm
import warnings
warnings.filterwarnings("ignore")

# -------------------------------
# 1. Load data
# -------------------------------
train = pd.read_csv(r"C:\Users\liam\Documents\GitHub\all-of-my-code\kaggle\train.csv")
test = pd.read_csv(r"C:\Users\liam\Documents\GitHub\all-of-my-code\kaggle\test.csv")

# -------------------------------
# 2. Feature engineering
# -------------------------------
def engineer_features(df):
    df = df.copy()
    
    df["total_charging"] = df["Charging_Stations_Near_Home"] + df["Charging_Stations_Near_Work"]
    df["charging_ratio"] = df["Charging_Stations_Near_Work"] / (df["Charging_Stations_Near_Home"] + 1)
    df["commute_per_income"] = df["Daily_Commute_km"] / (df["Annual_Income_USD"] + 1)
    df["log_income"] = np.log1p(df["Annual_Income_USD"])
    df["age_squared"] = df["Age"] ** 2
    df["cars_charging"] = df["Number_of_Cars_Owned"] * df["total_charging"]
    median_income = df["Annual_Income_USD"].median()
    df["home_charging_high_income"] = ((df["Home_Charging_Possible"] == "Yes") & 
                                        (df["Annual_Income_USD"] > median_income)).astype(int)
    range_map = {"Low": 0, "Medium": 1, "High": 2}
    df["range_anxiety_num"] = df["Range_Anxiety_Level"].map(range_map)
    
    return df

# Show a progress bar while engineering (only if you have many features)
print("Engineering features...")
train = engineer_features(train)
test = engineer_features(test)

X = train.drop(columns=["id", "Will_Buy_EV"])
y = train["Will_Buy_EV"]

# -------------------------------
# 3. Preprocessing
# -------------------------------
num_cols = X.select_dtypes(include=["int64", "float64"]).columns.tolist()
cat_cols = X.select_dtypes(include=["object"]).columns.tolist()

preprocessor = ColumnTransformer([
    ("num", Pipeline([("imputer", SimpleImputer(strategy="median")),
                      ("scaler", StandardScaler())]), num_cols),
    ("cat", Pipeline([("imputer", SimpleImputer(strategy="constant", fill_value="missing")),
                      ("onehot", OneHotEncoder(handle_unknown="ignore"))]), cat_cols)
])

X_prep = preprocessor.fit_transform(X)
X_test_prep = preprocessor.transform(test.drop(columns=["id"]))

# -------------------------------
# 4. Model
# -------------------------------
model = LogisticRegression(
    C=0.5,
    penalty='l2',
    solver='liblinear',
    class_weight=None,
    max_iter=1000,
    random_state=42
)

# -------------------------------
# 5. Cross‑validation with progress bar
# -------------------------------
cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
scores = []
y_pred_full = np.zeros(len(y))

print("Running cross‑validation...")
for train_idx, val_idx in tqdm(cv.split(X_prep, y), total=5, desc="CV folds"):
    X_tr, X_val = X_prep[train_idx], X_prep[val_idx]
    y_tr, y_val = y.iloc[train_idx], y.iloc[val_idx]
    
    model.fit(X_tr, y_tr)
    proba = model.predict_proba(X_val)[:, 1]
    scores.append(roc_auc_score(y_val, proba))
    y_pred_full[val_idx] = proba

print(f"Cross‑validation AUC: {np.mean(scores):.4f} (±{np.std(scores):.4f})")
print(f"Cross‑validation Log‑Loss: {log_loss(y, y_pred_full):.4f}")

# -------------------------------
# 6. Train final model and predict
# -------------------------------
model.fit(X_prep, y)
proba_test = model.predict_proba(X_test_prep)[:, 1]

submission = pd.DataFrame({
    "id": test["id"],
    "Will_Buy_EV": proba_test
})
submission.to_csv("submission_final.csv", index=False)
print("Submission saved to submission_final.csv")