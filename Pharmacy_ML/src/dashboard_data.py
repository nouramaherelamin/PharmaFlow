"""Pre-compute the aggregates the dashboard needs.  Run:  python -m src.dashboard_data"""
import json

import numpy as np
import pandas as pd

from .config import CLEAN_CSV, DASHBOARD_JSON, METRICS_DIR, REVENUE_COL as REV, TARGET


def main():
    df = pd.read_csv(CLEAN_CSV, parse_dates=["Transaction_Date"])
    meta = json.load(open(METRICS_DIR / "metrics.json"))
    best = meta["best"]

    monthly = df.groupby("YearMonth").agg(revenue=(REV, "sum"), txns=("Transaction_ID", "count")).reset_index()
    by_cat = df.groupby("Medicine_Category")[REV].sum().sort_values(ascending=False)
    by_branch = df.groupby("Branch_Name")[REV].sum().sort_values(ascending=False)
    pay = df.groupby("Payment_Method")[REV].sum()
    pv = df.pivot_table(index="Medicine_Category", columns="Branch_Name", values=REV, aggfunc="sum").loc[by_cat.index]
    age = df.groupby("Age_Group", observed=True)[REV].sum()

    overview = {
        "kpis": {"revenue": float(df[REV].sum()), "transactions": int(len(df)),
                 "avg_basket": float(df[REV].mean()), "units": int(df.Quantity.sum()),
                 "rx_share": float(df[df.Prescription_Required == "Yes"][REV].sum() / df[REV].sum()),
                 "date_from": str(df.Transaction_Date.min().date()), "date_to": str(df.Transaction_Date.max().date()),
                 "branches": int(df.Branch_Name.nunique()), "medicines": int(df.Medicine_ID.nunique())},
        "monthly": {"labels": monthly.YearMonth.tolist(), "revenue": monthly.revenue.round(0).tolist(),
                    "txns": monthly.txns.tolist()},
        "by_category": {"labels": by_cat.index.tolist(), "values": by_cat.round(0).tolist()},
        "by_branch": {"labels": by_branch.index.tolist(), "values": by_branch.round(0).tolist()},
        "payment": {"labels": pay.index.tolist(), "values": pay.round(0).tolist()},
        "age_group": {"labels": [str(i) for i in age.index], "values": age.round(0).tolist()},
        "heatmap": {"rows": pv.index.tolist(), "cols": pv.columns.tolist(), "values": pv.round(0).values.tolist()},
    }

    t = pd.read_csv(METRICS_DIR / "test_predictions.csv")
    t["pred"] = t[f"pred_{best}"]
    resid = (t[TARGET] - t.pred)
    backtest = {}
    for (b, c), d in t.groupby(["Branch_Name", "Medicine_Category"]):
        backtest[f"{b}||{c}"] = [{"period": r.Period_str, "actual": round(float(r[TARGET]), 0),
                                  "pred": round(float(r.pred), 0)} for _, r in d.iterrows()]
    imp = pd.read_csv(METRICS_DIR / "feature_importance.csv", index_col=0).importance

    performance = {
        "best": best,
        "comparison": {k: {m: round(v, 3) for m, v in vals.items()} for k, vals in meta["test"].items()},
        "cv": meta["cv"],
        "scatter": [[round(float(a), 0), round(float(p), 0)] for a, p in zip(t[TARGET], t.pred)],
        "importance": {"labels": imp.index.tolist(), "values": imp.round(0).tolist()},
        "interval": {"q10": float(np.quantile(resid, 0.10)), "q90": float(np.quantile(resid, 0.90))},
        "n_test": int(len(t)),
    }
    med = json.load(open(METRICS_DIR / "medicine_metrics.json"))
    DASHBOARD_JSON.write_text(json.dumps({"overview": overview, "performance": performance, "backtest": backtest,
                                          "medicine_model": med}))
    print(f"Dashboard data -> {DASHBOARD_JSON}")


if __name__ == "__main__":
    main()
