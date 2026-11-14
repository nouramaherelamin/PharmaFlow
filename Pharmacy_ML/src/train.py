"""Step 3 - modeling.  Run:  python -m src.train"""
import json

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from .config import (CAT_FEATURES, CLEAN_CSV, HISTORY_CSV, METRICS_DIR, MODEL_PATH, NUM_FEATURES, TARGET)
from .features import FEATURE_COLUMNS, add_features, build_panel, train_test_split_time


def make_preprocessor(scale):
    return ColumnTransformer([("num", StandardScaler() if scale else "passthrough", NUM_FEATURES),
                              ("cat", OneHotEncoder(handle_unknown="ignore"), CAT_FEATURES)])


def make_models():
    return {
        "Ridge": Pipeline([("pre", make_preprocessor(True)), ("m", Ridge(alpha=10))]),
        "RandomForest": Pipeline([("pre", make_preprocessor(False)), ("m", RandomForestRegressor(
            n_estimators=300, min_samples_leaf=5, max_features=0.5, random_state=42, n_jobs=-1))]),
        "GradientBoosting": Pipeline([("pre", make_preprocessor(False)), ("m", GradientBoostingRegressor(
            n_estimators=200, learning_rate=0.05, max_depth=3, subsample=0.8, random_state=42))]),
    }


def metrics(y, p):
    return {"MAE": float(mean_absolute_error(y, p)), "RMSE": float(np.sqrt(mean_squared_error(y, p))),
            "R2": float(r2_score(y, p)), "WAPE_%": float(np.abs(y - p).sum() / np.abs(y).sum() * 100)}


def main():
    df = pd.read_csv(CLEAN_CSV, parse_dates=["Transaction_Date"])
    panel = build_panel(df)
    data = add_features(panel)
    train, test = train_test_split_time(data)
    print(f"Panel {panel.shape} | train {len(train)} | test {len(test)}")

    results = {"Baseline: last month": metrics(test[TARGET], test.Rev_lag1),
               "Baseline: 3-month mean": metrics(test[TARGET], test.Rev_roll3_mean)}
    models = make_models()

    # expanding-window time-series CV on the last 4 training months
    cv = {}
    for name, pipe in models.items():
        maes = []
        for mth in sorted(train.Period_str.unique())[-4:]:
            tr, va = train[train.Period_str < mth], train[train.Period_str == mth]
            pipe.fit(tr[FEATURE_COLUMNS], tr[TARGET])
            maes.append(mean_absolute_error(va[TARGET], pipe.predict(va[FEATURE_COLUMNS])))
        cv[name] = {"cv_MAE_mean": float(np.mean(maes)), "cv_MAE_std": float(np.std(maes))}
        print(f"{name:18s} CV MAE {np.mean(maes):,.0f} +- {np.std(maes):,.0f}")

    preds = {}
    for name, pipe in models.items():
        pipe.fit(train[FEATURE_COLUMNS], train[TARGET])
        preds[name] = pipe.predict(test[FEATURE_COLUMNS])
        results[name] = metrics(test[TARGET], preds[name])
    res = pd.DataFrame(results).T.round(3)
    print(res)

    best = min(models, key=lambda n: results[n]["MAE"])
    print("Best model:", best)

    final = models[best].fit(data[FEATURE_COLUMNS], data[TARGET])      # refit on all labelled data
    joblib.dump({"model": final, "name": best}, MODEL_PATH)
    panel[["Branch_Name", "Medicine_Category", "Period_str", "Revenue", "Units", "Txns"]].to_csv(HISTORY_CSV, index=False)

    out = test[["Branch_Name", "Medicine_Category", "Period_str", TARGET]].copy()
    for n, p in preds.items():
        out[f"pred_{n}"] = p
    out.to_csv(METRICS_DIR / "test_predictions.csv", index=False)
    res.to_csv(METRICS_DIR / "model_comparison.csv")
    json.dump({"test": results, "cv": cv, "best": best}, open(METRICS_DIR / "metrics.json", "w"), indent=2)


if __name__ == "__main__":
    main()
