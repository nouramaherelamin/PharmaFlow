"""Feature engineering shared by training and the deployed app (single source of truth)."""
import numpy as np
import pandas as pd

from .config import NUM_FEATURES, CAT_FEATURES, LAST_TRAIN_MONTH

KEY = ["Branch_Name", "Medicine_Category"]


def build_panel(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate transactions to Branch x Category x Month (empty months = 0)."""
    df = df.copy()
    df["Period"] = pd.to_datetime(df["Transaction_Date"]).dt.to_period("M")
    g = (df.groupby(KEY + ["Period"])
           .agg(Revenue=("Line_Total_LKR", "sum"), Units=("Quantity", "sum"), Txns=("Transaction_ID", "count"))
           .reset_index())
    periods = pd.period_range(df.Period.min(), df.Period.max(), freq="M")
    full = pd.MultiIndex.from_product([df.Branch_Name.unique(), df.Medicine_Category.unique(), periods],
                                      names=KEY + ["Period"])
    g = g.set_index(KEY + ["Period"]).reindex(full).fillna(0).reset_index()
    g["Period_str"] = g.Period.astype(str)
    return g.sort_values(KEY + ["Period"]).reset_index(drop=True)


def add_features(g: pd.DataFrame) -> pd.DataFrame:
    """Lag / rolling / calendar features. Everything is shifted so only past data is used."""
    g = g.copy()
    grp = g.groupby(KEY)["Revenue"]
    for k in (1, 2, 3):
        g[f"Rev_lag{k}"] = grp.shift(k)
    g["Rev_roll3_mean"] = grp.transform(lambda s: s.shift(1).rolling(3).mean())
    g["Rev_roll3_std"] = grp.transform(lambda s: s.shift(1).rolling(3).std())
    g["Units_lag1"] = g.groupby(KEY)["Units"].shift(1)
    g["Txns_lag1"] = g.groupby(KEY)["Txns"].shift(1)
    g["Rev_trend"] = g.Rev_lag1 - g.Rev_lag2
    month = g.Period.dt.month
    g["Month_sin"] = np.sin(2 * np.pi * month / 12)
    g["Month_cos"] = np.cos(2 * np.pi * month / 12)
    return g.dropna(subset=["Rev_lag3", "Rev_roll3_mean", "Rev_roll3_std"]).copy()


def train_test_split_time(data: pd.DataFrame):
    return data[data.Period_str <= LAST_TRAIN_MONTH], data[data.Period_str > LAST_TRAIN_MONTH]


def next_month_row(hist: pd.DataFrame, branch: str, category: str):
    """Build the feature row for the month after the last one in `hist`."""
    nxt = pd.Period(hist.Period_str.max(), freq="M") + 1
    h = hist[(hist.Branch_Name == branch) & (hist.Medicine_Category == category)].sort_values("Period_str").tail(3)
    if len(h) < 3:
        raise ValueError("Not enough history (need 3 months).")
    rev = h.Revenue.to_numpy()[::-1]          # rev[0] = last month
    m = nxt.month
    row = {"Branch_Name": branch, "Medicine_Category": category,
           "Rev_lag1": rev[0], "Rev_lag2": rev[1], "Rev_lag3": rev[2],
           "Rev_roll3_mean": rev.mean(), "Rev_roll3_std": rev.std(ddof=1), "Rev_trend": rev[0] - rev[1],
           "Units_lag1": h.Units.iloc[-1], "Txns_lag1": h.Txns.iloc[-1],
           "Month_sin": np.sin(2 * np.pi * m / 12), "Month_cos": np.cos(2 * np.pi * m / 12)}
    return row, str(nxt)


FEATURE_COLUMNS = NUM_FEATURES + CAT_FEATURES
