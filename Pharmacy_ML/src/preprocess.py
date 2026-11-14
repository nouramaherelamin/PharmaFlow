"""Step 1 - preprocessing.  Run:  python -m src.preprocess"""
import pandas as pd

from .config import RAW_CSV, CLEAN_CSV, METRICS_DIR


def main():
    report = []
    def log(msg):
        print(msg); report.append(msg)

    df = pd.read_csv(RAW_CSV)
    log(f"Raw shape: {df.shape}")
    df["Transaction_Date"] = pd.to_datetime(df["Transaction_Date"], format="%m/%d/%Y")
    df["Expiry_Date"] = pd.to_datetime(df["Expiry_Date"], format="%m/%d/%Y")

    log(f"Duplicate rows: {df.duplicated().sum()} | duplicate Transaction_ID: {df.Transaction_ID.duplicated().sum()}")
    miss = df.isna().sum()
    log("Missing values:\n" + miss[miss > 0].to_string())
    # Strength_mg is empty for forms where mg is not meaningful (cream, syrup, ...)
    df["Has_Strength"] = df["Strength_mg"].notna().astype(int)
    df["Strength_mg"] = df["Strength_mg"].fillna(0)

    calc = (df.Quantity * df.Unit_Price_LKR * (1 - df.Discount_Rate)).round(2)
    log(f"Line_Total mismatches: {(abs(calc - df.Line_Total_LKR) > 0.02).sum()}")
    log(f"Rows sold after expiry: {(df.Expiry_Date < df.Transaction_Date).sum()}")

    q1, q3 = df.Line_Total_LKR.quantile([.25, .75])
    df["Is_High_Value"] = (df.Line_Total_LKR > q3 + 1.5 * (q3 - q1)).astype(int)   # flagged, not removed
    log(f"High-value rows flagged: {df.Is_High_Value.sum()}")

    df["Days_To_Expiry"] = (df.Expiry_Date - df.Transaction_Date).dt.days
    df["YearMonth"] = df.Transaction_Date.dt.to_period("M").astype(str)
    df["DayOfWeek"] = df.Transaction_Date.dt.dayofweek
    df["Quarter"] = df.Transaction_Date.dt.quarter
    df["Age_Group"] = pd.cut(df.Customer_Age, [17, 30, 45, 60, 80], labels=["18-30", "31-45", "46-60", "61-80"])
    df = df.sort_values("Transaction_Date").reset_index(drop=True)

    df.to_csv(CLEAN_CSV, index=False)
    log(f"Clean shape: {df.shape} -> {CLEAN_CSV}")
    (METRICS_DIR / "preprocessing_report.txt").write_text("\n".join(report))


if __name__ == "__main__":
    main()
