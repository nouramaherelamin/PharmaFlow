"""Step 4 - evaluation plots and importance.  Run:  python -m src.evaluate"""
import json

import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from sklearn.inspection import permutation_importance

from .config import CLEAN_CSV, FIG_DIR, METRICS_DIR, MODEL_PATH, TARGET
from .features import FEATURE_COLUMNS, add_features, build_panel, train_test_split_time

sns.set_theme(style="whitegrid")


def main():
    meta = json.load(open(METRICS_DIR / "metrics.json"))
    best = meta["best"]
    t = pd.read_csv(METRICS_DIR / "test_predictions.csv")
    t["pred"] = t[f"pred_{best}"]
    t["err"] = t[TARGET] - t.pred

    fig, ax = plt.subplots(1, 3, figsize=(17, 4.8))
    ax[0].scatter(t[TARGET] / 1e3, t.pred / 1e3, alpha=.5, s=14)
    lim = [0, t[TARGET].max() / 1e3 * 1.05]; ax[0].plot(lim, lim, "r--")
    ax[0].set_xlabel("Actual (k LKR)"); ax[0].set_ylabel("Predicted (k LKR)"); ax[0].set_title(f"Actual vs predicted - {best}")
    sns.histplot(t.err / 1e3, bins=40, ax=ax[1]); ax[1].set_title("Residuals (k LKR)")
    pd.DataFrame(meta["test"]).T["MAE"].sort_values().plot.barh(ax=ax[2], color="tab:green"); ax[2].set_title("Test MAE (lower = better)")
    plt.tight_layout(); plt.savefig(FIG_DIR / "07_evaluation.png", dpi=130); plt.close()

    for col, fn in [("Medicine_Category", "08_error_by_category"), ("Branch_Name", "09_error_by_branch")]:
        e = t.groupby(col).apply(lambda d: d.err.abs().sum() / d[TARGET].sum() * 100).sort_values()
        e.plot.barh(figsize=(8, 5)); plt.title(f"WAPE % by {col}"); plt.tight_layout()
        plt.savefig(FIG_DIR / f"{fn}.png", dpi=130); plt.close()
        print(e.round(1))

    # permutation importance (final model is refit on all data, so this is indicative)
    model = joblib.load(MODEL_PATH)["model"]
    data = add_features(build_panel(pd.read_csv(CLEAN_CSV, parse_dates=["Transaction_Date"])))
    _, test = train_test_split_time(data)
    pi = permutation_importance(model, test[FEATURE_COLUMNS], test[TARGET],
                                scoring="neg_mean_absolute_error", n_repeats=15, random_state=0)
    imp = pd.Series(pi.importances_mean, index=FEATURE_COLUMNS).sort_values()
    imp.sort_values(ascending=False).rename("importance").to_csv(METRICS_DIR / "feature_importance.csv")
    imp.plot.barh(figsize=(8, 5)); plt.title("Permutation importance (increase in MAE)"); plt.tight_layout()
    plt.savefig(FIG_DIR / "10_feature_importance.png", dpi=130); plt.close()
    print(imp.sort_values(ascending=False).head(6).round(0))


if __name__ == "__main__":
    main()
