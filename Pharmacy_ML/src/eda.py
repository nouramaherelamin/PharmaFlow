"""Step 2 - EDA figures.  Run:  python -m src.eda"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

from .config import CLEAN_CSV, FIG_DIR, REVENUE_COL as REV

sns.set_theme(style="whitegrid")


def save(name):
    plt.tight_layout(); plt.savefig(FIG_DIR / f"{name}.png", dpi=130); plt.close()


def main():
    df = pd.read_csv(CLEAN_CSV, parse_dates=["Transaction_Date", "Expiry_Date"])

    m = df.groupby("YearMonth").agg(Revenue=(REV, "sum"), Txns=("Transaction_ID", "count"))
    fig, ax = plt.subplots(1, 2, figsize=(13, 4))
    m.Revenue.plot(ax=ax[0], marker="o"); ax[0].set_title("Monthly revenue (LKR)")
    m.Txns.plot(ax=ax[1], marker="o", color="tab:green"); ax[1].set_title("Monthly transactions")
    for a in ax: a.tick_params(axis="x", rotation=60)
    save("01_monthly_trend")

    fig, ax = plt.subplots(1, 3, figsize=(15, 4))
    sns.histplot(df[REV], bins=50, ax=ax[0]); ax[0].set_title("Line total (LKR)")
    sns.histplot(df.Customer_Age, bins=30, ax=ax[1]); ax[1].set_title("Customer age")
    sns.countplot(x="Quantity", data=df, ax=ax[2]); ax[2].set_title("Quantity per line")
    save("02_distributions")

    fig, ax = plt.subplots(1, 3, figsize=(17, 5))
    df.groupby("Medicine_Category")[REV].sum().sort_values().plot.barh(ax=ax[0]); ax[0].set_title("Revenue by category")
    df.groupby("Branch_Name")[REV].sum().sort_values().plot.barh(ax=ax[1], color="tab:orange"); ax[1].set_title("Revenue by branch")
    df.groupby("Payment_Method")[REV].sum().plot.pie(ax=ax[2], autopct="%1.0f%%"); ax[2].set_ylabel(""); ax[2].set_title("Revenue by payment")
    save("03_revenue_breakdown")

    pv = df.pivot_table(index="Medicine_Category", columns="Branch_Name", values=REV, aggfunc="sum")
    plt.figure(figsize=(11, 7)); sns.heatmap(pv / 1e6, annot=True, fmt=".1f", cmap="YlGnBu")
    plt.title("Revenue (million LKR): category x branch"); save("04_category_branch_heatmap")

    fig, ax = plt.subplots(1, 2, figsize=(12, 4))
    df.groupby("Month")[REV].sum().plot.bar(ax=ax[0]); ax[0].set_title("Revenue by calendar month")
    df.groupby("DayOfWeek")[REV].sum().plot.bar(ax=ax[1], color="tab:purple"); ax[1].set_title("Revenue by day of week (0=Mon)")
    save("05_seasonality")

    num = ["Customer_Age", "Pack_Size", "Strength_mg", "Quantity", "Unit_Price_LKR", "Discount_Rate", "Days_To_Expiry", REV]
    plt.figure(figsize=(8, 6)); sns.heatmap(df[num].corr(), annot=True, fmt=".2f", cmap="coolwarm", center=0)
    plt.title("Correlation"); save("06_correlation")
    print(f"EDA figures saved to {FIG_DIR}")


if __name__ == "__main__":
    main()
