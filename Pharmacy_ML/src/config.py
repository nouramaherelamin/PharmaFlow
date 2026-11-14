"""Central paths and constants shared by every step."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW_CSV = ROOT / "data" / "raw" / "Pharmacy_OLTP_SLStyle_18Months.csv"
CLEAN_CSV = ROOT / "data" / "processed" / "pharmacy_clean.csv"
HISTORY_CSV = ROOT / "data" / "processed" / "monthly_history.csv"
MED_CATALOG_JSON = ROOT / "data" / "processed" / "medicines.json"
MED_HISTORY_CSV = ROOT / "data" / "processed" / "medicine_history.csv"
MED_MODEL_PATH = ROOT / "models" / "medicine_model.joblib"
DASHBOARD_JSON = ROOT / "data" / "processed" / "dashboard_data.json"
MODEL_PATH = ROOT / "models" / "model.joblib"
FIG_DIR = ROOT / "reports" / "figures"
METRICS_DIR = ROOT / "reports" / "metrics"

REVENUE_COL = "Line_Total_LKR"
TARGET = "Revenue"
NUM_FEATURES = ["Rev_lag1", "Rev_lag2", "Rev_lag3", "Rev_roll3_mean", "Rev_roll3_std", "Rev_trend",
                "Units_lag1", "Txns_lag1", "Month_sin", "Month_cos"]
CAT_FEATURES = ["Branch_Name", "Medicine_Category"]
LAST_TRAIN_MONTH = "2023-03"   # time-based split: train <= this month, test after it

for d in (CLEAN_CSV.parent, MODEL_PATH.parent, FIG_DIR, METRICS_DIR):
    d.mkdir(parents=True, exist_ok=True)
