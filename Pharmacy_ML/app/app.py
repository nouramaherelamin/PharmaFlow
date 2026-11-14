"""Pharmacy Revenue Forecasting dashboard (Flask).

Run from the project root:   python -m app.app        -> http://localhost:5000
Production:                  gunicorn app.app:app
"""
import json
import os

import joblib
import numpy as np
import pandas as pd
from flask import Flask, jsonify, render_template, request

from src.config import (DASHBOARD_JSON, HISTORY_CSV, MED_CATALOG_JSON, MED_HISTORY_CSV, MED_MODEL_PATH, MODEL_PATH)
from src.features import FEATURE_COLUMNS, next_month_row
from src.medicine_model import COLS as MED_COLS, next_rows

MODEL = joblib.load(MODEL_PATH)["model"]
HIST = pd.read_csv(HISTORY_CSV)
DASH = json.load(open(DASHBOARD_JSON))
MED_MODEL = joblib.load(MED_MODEL_PATH)["model"]
MED_CAT = pd.DataFrame(json.load(open(MED_CATALOG_JSON)))
MED_HIST = pd.read_csv(MED_HISTORY_CSV)
MED_Q10, MED_Q90 = DASH["medicine_model"]["interval"]["q10"], DASH["medicine_model"]["interval"]["q90"]
MED_NEXT = str(pd.Period(MED_HIST.Period_str.max(), freq="M") + 1)
BRANCHES = sorted(HIST.Branch_Name.unique())
CATEGORIES = sorted(HIST.Medicine_Category.unique())
NEXT = str(pd.Period(HIST.Period_str.max(), freq="M") + 1)
Q10, Q90 = DASH["performance"]["interval"]["q10"], DASH["performance"]["interval"]["q90"]

app = Flask(__name__, template_folder="templates", static_folder="static")


def forecast(pairs):
    X = pd.DataFrame([next_month_row(HIST, b, c)[0] for b, c in pairs])
    return np.maximum(MODEL.predict(X[FEATURE_COLUMNS]), 0)


def interval(pred):
    """80% prediction interval from the empirical test-set residuals."""
    return max(pred + Q10, 0.0), pred + Q90


def valid(b, c):
    return b in BRANCHES and c in CATEGORIES


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/health")
def health():
    return jsonify(status="ok")


@app.route("/api/meta")
def meta():
    return jsonify(branches=BRANCHES, categories=CATEGORIES, next_month=NEXT,
                   last_month=HIST.Period_str.max(), model=DASH["performance"]["best"])


@app.route("/api/overview")
def overview():
    pairs = [(b, c) for b in BRANCHES for c in CATEGORIES]
    total_next = float(forecast(pairs).sum())
    last = float(HIST[HIST.Period_str == HIST.Period_str.max()].Revenue.sum())
    return jsonify(**DASH["overview"], next_total=total_next, last_total=last, next_month=NEXT)


@app.route("/api/forecast")
def api_forecast():
    b, c = request.args.get("branch"), request.args.get("category")
    if not valid(b, c):
        return jsonify(error="Unknown branch or category"), 400
    h = HIST[(HIST.Branch_Name == b) & (HIST.Medicine_Category == c)].sort_values("Period_str")
    pred = float(forecast([(b, c)])[0])
    lo, hi = interval(pred)
    last = float(h.Revenue.iloc[-1])
    return jsonify(branch=b, category=c, next_month=NEXT, forecast=round(pred, 2), low=round(lo, 2), high=round(hi, 2),
                   last_month=round(last, 2), change_pct=round((pred / last - 1) * 100, 1) if last else None,
                   avg_3m=round(float(h.Revenue.tail(3).mean()), 2),
                   history={"labels": h.Period_str.tolist(), "revenue": h.Revenue.round(0).tolist()},
                   backtest=DASH["backtest"].get(f"{b}||{c}", []))


@app.route("/api/forecast_all")
def api_forecast_all():
    pairs = [(b, c) for b in BRANCHES for c in CATEGORIES]
    preds = forecast(pairs)
    last_m = HIST.Period_str.max()
    last = HIST[HIST.Period_str == last_m].set_index(["Branch_Name", "Medicine_Category"]).Revenue
    rows = []
    for (b, c), p in zip(pairs, preds):
        lo, hi = interval(float(p))
        lm = float(last.get((b, c), 0))
        rows.append({"branch": b, "category": c, "forecast": round(float(p), 0), "low": round(lo, 0), "high": round(hi, 0),
                     "last_month": round(lm, 0), "change_pct": round((float(p) / lm - 1) * 100, 1) if lm else None})
    return jsonify(next_month=NEXT, rows=rows)


@app.route("/api/performance")
def performance():
    return jsonify(DASH["performance"])


@app.route("/predict", methods=["POST"])          # kept for simple API clients
def predict():
    d = request.get_json(force=True, silent=True) or {}
    b, c = d.get("branch"), d.get("category")
    if not valid(b, c):
        return jsonify(error="Unknown branch or category", branches=BRANCHES, categories=CATEGORIES), 400
    p = float(forecast([(b, c)])[0]); lo, hi = interval(p)
    return jsonify(branch=b, category=c, month=NEXT, forecast_revenue_lkr=round(p, 2),
                   low_80=round(lo, 2), high_80=round(hi, 2))


@app.route("/api/medicines")
def medicines():
    m = MED_CAT.sort_values("label")
    return jsonify(next_month=MED_NEXT, medicines=[
        {"id": int(r.Medicine_ID), "label": r.label, "category": r.Medicine_Category, "form": r.Dosage_Form,
         "strength": float(r.Strength_mg), "pack": int(r.Pack_Size), "rx": r.Prescription_Required,
         "supplier": r.supplier, "price": round(float(r.AvgPrice), 2), "discount": round(float(r.avg_discount), 4)}
        for r in m.itertuples()])


@app.route("/api/predict_medicine")
def predict_medicine():
    try:
        mid = int(request.args.get("medicine_id"))
    except (TypeError, ValueError):
        return jsonify(error="medicine_id is required"), 400
    branch = request.args.get("branch")
    row = MED_CAT[MED_CAT.Medicine_ID == mid]
    if row.empty or branch not in BRANCHES:
        return jsonify(error="Unknown medicine or branch"), 400
    c = row.iloc[0]

    def num(name, default):
        try:
            v = float(request.args.get(name, default))
            return v if v >= 0 else default
        except (TypeError, ValueError):
            return default
    price = num("price", float(c.AvgPrice)) or float(c.AvgPrice)
    stock = request.args.get("stock")
    stock = num("stock", None) if stock not in (None, "") else None

    X, nxt = next_rows(MED_HIST, MED_CAT, mid, BRANCHES)
    preds = np.maximum(MED_MODEL.predict(X[MED_COLS]), 0)
    by_branch = [{"branch": b, "units": round(float(p), 1)} for b, p in zip(BRANCHES, preds)]
    units = float(preds[BRANCHES.index(branch)])
    low, high = max(units + MED_Q10, 0.0), units + MED_Q90
    net = price * (1 - float(c.avg_discount))
    hist = MED_HIST[(MED_HIST.Medicine_ID == mid)].sort_values("Period_str")
    hb = hist[hist.Branch_Name == branch]
    avg_branch = float(MED_HIST[MED_HIST.Branch_Name == branch].Units.mean())

    out = {"medicine": c.label, "category": c.Medicine_Category, "branch": branch, "month": nxt,
           "units": round(units, 1), "units_low": round(low, 1), "units_high": round(high, 1),
           "price": round(price, 2), "discount": round(float(c.avg_discount), 4),
           "revenue": round(units * net, 0), "revenue_low": round(low * net, 0), "revenue_high": round(high * net, 0),
           "avg_units_branch": round(avg_branch, 1), "last_month_units": float(hb.Units.iloc[-1]),
           "history": {"labels": hb.Period_str.tolist(), "units": hb.Units.tolist()},
           "chain_history": hist.groupby("Period_str").Units.sum().tolist(), "by_branch": by_branch,
           "stock": stock}
    if stock is not None:
        out["stock_status"] = ("comfortable" if stock >= high else "adequate" if stock >= units else "shortage")
        out["stock_coverage_pct"] = round(stock / units * 100, 0) if units else None
        out["suggested_reorder"] = max(int(np.ceil(high - stock)), 0)
    return jsonify(out)


@app.route("/api/medicine_performance")
def medicine_performance():
    return jsonify(DASH["medicine_model"])


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
