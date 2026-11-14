"""Medicine-level demand model: expected units sold per Medicine x Branch next month.

Run:  python -m src.medicine_model
"""
import json

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from .config import (CLEAN_CSV, LAST_TRAIN_MONTH, METRICS_DIR, MED_CATALOG_JSON, MED_HISTORY_CSV, MED_MODEL_PATH)

NUM = ["Units_lag1", "Units_lag2", "Units_lag3", "Units_roll3", "Chain_lag1", "Pack_Size", "Strength_mg", "AvgPrice"]
CAT = ["Branch_Name", "Medicine_Category", "Dosage_Form", "Prescription_Required"]
COLS = NUM + CAT
KEY = ["Medicine_ID", "Branch_Name"]


def make_catalog(df):
    cat = (df.groupby("Medicine_ID")
             .agg(name=("Medicine_Name", "first"), generic=("Generic_Name", "first"),
                  Medicine_Category=("Medicine_Category", "first"), Dosage_Form=("Dosage_Form", "first"),
                  Strength_mg=("Strength_mg", "first"), Pack_Size=("Pack_Size", "first"),
                  Prescription_Required=("Prescription_Required", "first"), supplier=("Supplier_Name", "first"),
                  AvgPrice=("Unit_Price_LKR", "mean"), avg_discount=("Discount_Rate", "mean"))
             .reset_index())
    dup = cat.name.duplicated(keep=False)
    cat["label"] = np.where(dup, cat.name + " (#" + cat.Medicine_ID.astype(str) + ")", cat.name)
    return cat


def make_panel(df):
    df = df.copy()
    df["Period"] = pd.to_datetime(df.Transaction_Date).dt.to_period("M")
    g = df.groupby(KEY + ["Period"]).agg(Units=("Quantity", "sum"), Revenue=("Line_Total_LKR", "sum")).reset_index()
    periods = pd.period_range(df.Period.min(), df.Period.max(), freq="M")
    full = pd.MultiIndex.from_product([sorted(df.Medicine_ID.unique()), sorted(df.Branch_Name.unique()), periods],
                                      names=KEY + ["Period"])
    g = g.set_index(KEY + ["Period"]).reindex(full).fillna(0).reset_index()
    g["Period_str"] = g.Period.astype(str)
    return g.sort_values(KEY + ["Period"]).reset_index(drop=True)


def add_features(panel, catalog):
    g = panel.copy()
    grp = g.groupby(KEY)["Units"]
    for k in (1, 2, 3):
        g[f"Units_lag{k}"] = grp.shift(k)
    g["Units_roll3"] = grp.transform(lambda s: s.shift(1).rolling(3).mean())
    chain = g.groupby(["Medicine_ID", "Period"]).Units.sum().rename("Chain").reset_index()
    chain["Chain_lag1"] = chain.groupby("Medicine_ID").Chain.shift(1)
    g = g.merge(chain[["Medicine_ID", "Period", "Chain_lag1"]], on=["Medicine_ID", "Period"], how="left")
    g = g.merge(catalog[["Medicine_ID", "Medicine_Category", "Dosage_Form", "Prescription_Required",
                         "Pack_Size", "Strength_mg", "AvgPrice"]], on="Medicine_ID", how="left")
    return g.dropna(subset=["Units_lag3", "Units_roll3", "Chain_lag1"]).copy()


def next_rows(history, catalog, medicine_id, branches):
    """Feature rows for the month after the last month in `history` (one row per branch)."""
    nxt = str(pd.Period(history.Period_str.max(), freq="M") + 1)
    c = catalog[catalog.Medicine_ID == medicine_id].iloc[0]
    h = history[history.Medicine_ID == medicine_id]
    chain_last = float(h[h.Period_str == h.Period_str.max()].Units.sum())
    rows = []
    for b in branches:
        u = h[h.Branch_Name == b].sort_values("Period_str").Units.to_numpy()[::-1][:3]
        rows.append({"Units_lag1": u[0], "Units_lag2": u[1], "Units_lag3": u[2], "Units_roll3": u.mean(),
                     "Chain_lag1": chain_last, "Pack_Size": c.Pack_Size, "Strength_mg": c.Strength_mg,
                     "AvgPrice": c.AvgPrice, "Branch_Name": b, "Medicine_Category": c.Medicine_Category,
                     "Dosage_Form": c.Dosage_Form, "Prescription_Required": c.Prescription_Required})
    return pd.DataFrame(rows)[COLS], nxt


def pre(scale):
    return ColumnTransformer([("num", StandardScaler() if scale else "passthrough", NUM),
                              ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), CAT)])


def metrics(y, p):
    return {"MAE": float(mean_absolute_error(y, p)), "RMSE": float(np.sqrt(mean_squared_error(y, p))),
            "R2": float(r2_score(y, p)), "WAPE_%": float(np.abs(y - p).sum() / np.abs(y).sum() * 100)}


def main():
    df = pd.read_csv(CLEAN_CSV, parse_dates=["Transaction_Date"])
    catalog = make_catalog(df)
    panel = make_panel(df)
    data = add_features(panel, catalog)
    train, test = data[data.Period_str <= LAST_TRAIN_MONTH], data[data.Period_str > LAST_TRAIN_MONTH]
    print(f"Medicine panel {panel.shape} | train {len(train)} | test {len(test)}")

    results = {"Baseline: train average": metrics(test.Units, np.full(len(test), train.Units.mean())),
               "Baseline: last month": metrics(test.Units, test.Units_lag1),
               "Baseline: 3-month mean": metrics(test.Units, test.Units_roll3)}
    models = {
        "Ridge": Pipeline([("pre", pre(True)), ("m", Ridge(alpha=200))]),
        "HistGradientBoosting": Pipeline([("pre", pre(False)), ("m", HistGradientBoostingRegressor(
            loss="poisson", max_depth=3, learning_rate=0.04, max_iter=150, min_samples_leaf=150,
            l2_regularization=10, random_state=42))]),
        "RandomForest": Pipeline([("pre", pre(False)), ("m", RandomForestRegressor(
            n_estimators=200, min_samples_leaf=80, max_features=0.5, random_state=42, n_jobs=-1))]),
    }
    preds = {}
    for n, p in models.items():
        p.fit(train[COLS], train.Units)
        preds[n] = p.predict(test[COLS]); results[n] = metrics(test.Units, preds[n])
    res = pd.DataFrame(results).T.round(3); print(res)
    best = min(models, key=lambda n: results[n]["MAE"])
    best_overall_baseline = min((k for k in results if k.startswith("Baseline")), key=lambda k: results[k]["MAE"])
    print("Best model:", best, "| best baseline:", best_overall_baseline)

    resid = test.Units.to_numpy() - preds[best]
    final = models[best].fit(data[COLS], data.Units)
    joblib.dump({"model": final, "name": best}, MED_MODEL_PATH)
    catalog.to_json(MED_CATALOG_JSON, orient="records")
    panel[["Medicine_ID", "Branch_Name", "Period_str", "Units", "Revenue"]].to_csv(MED_HISTORY_CSV, index=False)
    json.dump({"test": results, "best": best, "best_baseline": best_overall_baseline,
               "interval": {"q10": float(np.quantile(resid, .10)), "q90": float(np.quantile(resid, .90))},
               "n_train": int(len(train)), "n_test": int(len(test)), "avg_units_cell": float(data.Units.mean()),
               "rows_total": int(len(df)), "n_medicines": int(len(catalog))},
              open(METRICS_DIR / "medicine_metrics.json", "w"), indent=2)


if __name__ == "__main__":
    main()
