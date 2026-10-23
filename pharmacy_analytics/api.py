"""Flask REST API for pharmacy transaction revenue prediction.
Run: python api.py
Endpoint: POST http://127.0.0.1:5000/predict
"""
from pathlib import Path
import pandas as pd
from flask import Flask, request, jsonify
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from sklearn.impute import SimpleImputer
from sklearn.ensemble import RandomForestRegressor

BASE = Path(__file__).parent
DATA_PATH = BASE / "data" / "pharmacy_sales.csv"
app = Flask(__name__)
FEATURES = ["Quantity","Unit_Price_LKR","Discount_Rate","Customer_Age","Customer_Gender",
            "Medicine_Category","Dosage_Form","Branch_Name","Month"]
NUMERIC = ["Quantity","Unit_Price_LKR","Discount_Rate","Customer_Age","Month"]
CATEGORICAL = ["Customer_Gender","Medicine_Category","Dosage_Form","Branch_Name"]

def train_model():
    df = pd.read_csv(DATA_PATH)
    df["Revenue"] = pd.to_numeric(df["Line_Total_LKR"], errors="coerce")
    df["Transaction_Date"] = pd.to_datetime(df["Transaction_Date"], errors="coerce")
    df["Month"] = df["Transaction_Date"].dt.month
    df = df.dropna(subset=["Revenue"])
    pre = ColumnTransformer([
        ("num", SimpleImputer(strategy="median"), NUMERIC),
        ("cat", Pipeline([("imputer", SimpleImputer(strategy="most_frequent")),
                          ("onehot", OneHotEncoder(handle_unknown="ignore"))]), CATEGORICAL)
    ])
    model = Pipeline([("preprocess", pre), ("model", RandomForestRegressor(
        n_estimators=100, max_depth=14, min_samples_leaf=3, random_state=42, n_jobs=-1))])
    model.fit(df[FEATURES], df["Revenue"])
    return model, df

model, source_data = train_model()

@app.get("/")
def home():
    return jsonify({
        "name": "Pharmacy Revenue Prediction API",
        "status": "running",
        "endpoint": "POST /predict",
        "required_fields": FEATURES
    })

@app.get("/health")
def health():
    return jsonify({"status":"ok"})

@app.post("/predict")
def predict():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"error":"Send a JSON object in the request body."}), 400
    missing = [f for f in FEATURES if f not in payload]
    if missing:
        return jsonify({"error":"Missing required fields", "missing_fields":missing}), 400
    try:
        row = {k: payload[k] for k in FEATURES}
        row["Quantity"] = int(row["Quantity"])
        row["Unit_Price_LKR"] = float(row["Unit_Price_LKR"])
        row["Discount_Rate"] = float(row["Discount_Rate"])
        row["Customer_Age"] = int(row["Customer_Age"])
        row["Month"] = int(row["Month"])
        if row["Quantity"] < 1 or row["Unit_Price_LKR"] < 0:
            raise ValueError("Quantity must be positive and price must be non-negative.")
        if not 0 <= row["Discount_Rate"] <= 1:
            raise ValueError("Discount_Rate must be between 0 and 1 (e.g. 0.05 for 5%).")
        if not 1 <= row["Customer_Age"] <= 120 or not 1 <= row["Month"] <= 12:
            raise ValueError("Customer_Age must be 1–120 and Month must be 1–12.")
        prediction = max(0.0, float(model.predict(pd.DataFrame([row], columns=FEATURES))[0]))
        return jsonify({"predicted_revenue_lkr": round(prediction, 2),
                        "currency":"LKR", "model":"RandomForestRegressor",
                        "warning":"Estimate only; not a guaranteed sale amount."})
    except (TypeError, ValueError) as exc:
        return jsonify({"error":str(exc)}), 400

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
