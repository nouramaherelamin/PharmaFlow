from pathlib import Path
import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="Pharmacy Intelligence", page_icon="💊", layout="wide")
DATA_PATH = Path(__file__).parent / "data" / "pharmacy_sales.csv"

NAVY = "#102A56"
BLUE = "#3977C3"
LIGHT_BLUE = "#DCE8F7"
BG = "#F4F7FB"

@st.cache_data
def load_data():
    df = pd.read_csv(DATA_PATH)
    df["Transaction_Date"] = pd.to_datetime(df["Transaction_Date"], errors="coerce")
    df["Expiry_Date"] = pd.to_datetime(df["Expiry_Date"], errors="coerce")
    df["Revenue"] = pd.to_numeric(df["Line_Total_LKR"], errors="coerce")
    df["Quantity"] = pd.to_numeric(df["Quantity"], errors="coerce")
    df["Discount_Rate"] = pd.to_numeric(df["Discount_Rate"], errors="coerce")
    df = df.dropna(subset=["Transaction_Date", "Revenue"])
    df["YearMonth"] = df["Transaction_Date"].dt.to_period("M").astype(str)
    return df

df = load_data()
st.markdown("""
<style>
.stApp {background: #F4F7FB;}
[data-testid="stSidebar"] {background: #102A56;}
[data-testid="stSidebar"] * {color: white !important;}
h1,h2,h3 {color: #102A56;}
div[data-testid="stMetric"] {background:white;border:1px solid #DCE5F1;padding:16px;border-radius:14px;box-shadow:0 3px 12px #102a5610;}
</style>
""", unsafe_allow_html=True)

st.title("💊 Pharmacy Intelligence")
st.caption("Interactive sales analytics • Machine Learning • Revenue prediction")
st.markdown("A modern, filterable view of the 50,000-transaction pharmacy dataset.")

with st.sidebar:
    st.header("Filters")
    date_min, date_max = df["Transaction_Date"].min().date(), df["Transaction_Date"].max().date()
    dates = st.date_input("Transaction date range", value=(date_min, date_max), min_value=date_min, max_value=date_max)
    branches = sorted(df["Branch_Name"].dropna().unique())
    chosen_branches = st.multiselect("Branch", branches, default=branches)
    categories = sorted(df["Medicine_Category"].dropna().unique())
    chosen_categories = st.multiselect("Medicine category", categories, default=categories)
    provinces = sorted(df["Province"].dropna().unique())
    chosen_provinces = st.multiselect("Province", provinces, default=provinces)
    genders = sorted(df["Customer_Gender"].dropna().unique())
    chosen_genders = st.multiselect("Customer gender", genders, default=genders)
    st.caption("Filters apply to the analytics charts below.")

if isinstance(dates, tuple) and len(dates) == 2:
    start, end = pd.Timestamp(dates[0]), pd.Timestamp(dates[1]) + pd.Timedelta(days=1)
    view = df[(df.Transaction_Date >= start) & (df.Transaction_Date < end)]
else:
    view = df.copy()
view = view[view.Branch_Name.isin(chosen_branches) & view.Medicine_Category.isin(chosen_categories) &
            view.Province.isin(chosen_provinces) & view.Customer_Gender.isin(chosen_genders)]

if view.empty:
    st.warning("No rows match these filters. Widen the filters to see results.")
    st.stop()

revenue = view["Revenue"].sum()
transactions = view["Transaction_ID"].nunique()
qty = view["Quantity"].sum()
avg_discount = view["Discount_Rate"].mean() * 100

m1,m2,m3,m4 = st.columns(4)
m1.metric("Total Revenue", f"LKR {revenue:,.0f}")
m2.metric("Transactions", f"{transactions:,.0f}")
m3.metric("Units Sold", f"{qty:,.0f}")
m4.metric("Avg. Discount", f"{avg_discount:.2f}%")

tab1, tab2, tab3 = st.tabs(["📊 Sales overview", "🤖 ML & forecast", "🔮 Revenue predictor"])

with tab1:
    c1,c2 = st.columns(2)
    monthly = view.groupby("YearMonth", as_index=False)["Revenue"].sum().sort_values("YearMonth")
    with c1:
        fig = px.line(monthly, x="YearMonth", y="Revenue", markers=True, title="Monthly revenue trend",
                      labels={"YearMonth":"Month","Revenue":"Revenue (LKR)"})
        fig.update_traces(line_color=BLUE, line_width=3)
        fig.update_layout(plot_bgcolor="white", paper_bgcolor="white")
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        cat = view.groupby("Medicine_Category", as_index=False)["Revenue"].sum().sort_values("Revenue", ascending=True)
        fig = px.bar(cat, x="Revenue", y="Medicine_Category", orientation="h", title="Revenue by medicine category",
                     labels={"Revenue":"Revenue (LKR)","Medicine_Category":"Category"}, color_discrete_sequence=[BLUE])
        fig.update_layout(plot_bgcolor="white", paper_bgcolor="white")
        st.plotly_chart(fig, use_container_width=True)

    c3,c4 = st.columns(2)
    with c3:
        branch = view.groupby("Branch_Name", as_index=False)["Revenue"].sum().sort_values("Revenue", ascending=False)
        fig = px.bar(branch, x="Branch_Name", y="Revenue", title="Branch performance",
                     labels={"Revenue":"Revenue (LKR)","Branch_Name":"Branch"}, color_discrete_sequence=[NAVY])
        fig.update_layout(plot_bgcolor="white", paper_bgcolor="white", xaxis_tickangle=-25)
        st.plotly_chart(fig, use_container_width=True)
    with c4:
        age_bins = [0,18,35,60,120]
        age_labels = ["0–18","19–35","36–60","60+"]
        age = view.copy()
        age["Age_Group"] = pd.cut(age.Customer_Age, bins=age_bins, labels=age_labels, include_lowest=True)
        ag = age.groupby("Age_Group", observed=False, as_index=False)["Revenue"].sum()
        fig = px.bar(ag, x="Age_Group", y="Revenue", title="Revenue by customer age group",
                     labels={"Revenue":"Revenue (LKR)","Age_Group":"Age group"}, color_discrete_sequence=[BLUE])
        fig.update_layout(plot_bgcolor="white", paper_bgcolor="white")
        st.plotly_chart(fig, use_container_width=True)

    c5,c6 = st.columns(2)
    with c5:
        gender = view.groupby("Customer_Gender", as_index=False)["Revenue"].sum()
        fig = px.pie(gender, names="Customer_Gender", values="Revenue", hole=.58, title="Revenue by gender")
        fig.update_layout(paper_bgcolor="white")
        st.plotly_chart(fig, use_container_width=True)
    with c6:
        top = view.groupby("Medicine_Name", as_index=False)["Revenue"].sum().nlargest(10,"Revenue").sort_values("Revenue")
        fig = px.bar(top, x="Revenue", y="Medicine_Name", orientation="h", title="Top 10 medicines by revenue",
                     labels={"Revenue":"Revenue (LKR)","Medicine_Name":"Medicine"}, color_discrete_sequence=[BLUE])
        fig.update_layout(plot_bgcolor="white", paper_bgcolor="white")
        st.plotly_chart(fig, use_container_width=True)

    with st.expander("Explore filtered transaction data"):
        st.dataframe(view.drop(columns=["Expiry_Date"], errors="ignore"), use_container_width=True, hide_index=True)
        st.download_button("Download filtered CSV", view.to_csv(index=False).encode("utf-8"),
                           "filtered_pharmacy_sales.csv", "text/csv")

with tab2:
    st.subheader("Monthly revenue forecast")
    st.info("The dataset covers only 18 months. This is a baseline forecast for exploration, not a reliable long-term business forecast. Validate with more history before operational use.")
    from sklearn.linear_model import LinearRegression
    monthly_all = df.groupby(pd.Grouper(key="Transaction_Date", freq="MS"))["Revenue"].sum().reset_index()
    monthly_all = monthly_all.rename(columns={"Transaction_Date":"MonthStart"})
    monthly_all["t"] = np.arange(len(monthly_all))
    model = LinearRegression().fit(monthly_all[["t"]], monthly_all["Revenue"])
    horizon = st.slider("Months to forecast", 1, 6, 3)
    future = pd.DataFrame({"t": np.arange(len(monthly_all), len(monthly_all)+horizon)})
    future["MonthStart"] = pd.date_range(monthly_all["MonthStart"].max()+pd.offsets.MonthBegin(1), periods=horizon, freq="MS")
    future["Predicted_Revenue_LKR"] = np.maximum(0, model.predict(future[["t"]]))
    hist = monthly_all[["MonthStart","Revenue"]].rename(columns={"Revenue":"Value"})
    hist["Type"] = "Historical"
    fut = future[["MonthStart","Predicted_Revenue_LKR"]].rename(columns={"Predicted_Revenue_LKR":"Value"})
    fut["Type"] = "Forecast"
    both = pd.concat([hist, fut], ignore_index=True)
    fig = px.line(both, x="MonthStart", y="Value", color="Type", markers=True, title="Historical vs baseline forecast",
                  labels={"MonthStart":"Month","Value":"Revenue (LKR)"})
    fig.update_layout(plot_bgcolor="white", paper_bgcolor="white")
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(future[["MonthStart","Predicted_Revenue_LKR"]].assign(MonthStart=lambda x: x.MonthStart.dt.strftime("%Y-%m")),
                 use_container_width=True, hide_index=True)
    st.caption("Forecast is based on a simple linear trend. It does not account for holidays, stockouts, promotions, or economic changes.")

with tab3:
    st.subheader("Estimate revenue for a hypothetical transaction")
    st.write("This baseline model estimates transaction-line revenue from quantity, unit price, discount, and basic context. It is not a clinical tool.")
    from sklearn.compose import ColumnTransformer
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import OneHotEncoder
    from sklearn.impute import SimpleImputer
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.metrics import mean_absolute_error
    @st.cache_resource
    def train_transaction_model(data):
        features = ["Quantity","Unit_Price_LKR","Discount_Rate","Customer_Age","Customer_Gender",
                    "Medicine_Category","Dosage_Form","Branch_Name","Month"]
        data = data.dropna(subset=["Revenue"]).copy()
        X, y = data[features], data["Revenue"]
        numeric = ["Quantity","Unit_Price_LKR","Discount_Rate","Customer_Age","Month"]
        categorical = ["Customer_Gender","Medicine_Category","Dosage_Form","Branch_Name"]
        pre = ColumnTransformer([
            ("num", SimpleImputer(strategy="median"), numeric),
            ("cat", Pipeline([("imputer", SimpleImputer(strategy="most_frequent")),
                              ("onehot", OneHotEncoder(handle_unknown="ignore"))]), categorical)
        ])
        pipe = Pipeline([("preprocess", pre), ("model", RandomForestRegressor(n_estimators=100, max_depth=14,
                           min_samples_leaf=3, random_state=42, n_jobs=-1))])
        pipe.fit(X, y)
        return pipe
    model = train_transaction_model(df)
    left, right = st.columns([1,1])
    with left:
        q = st.number_input("Quantity", min_value=1, max_value=100, value=2)
        price = st.number_input("Unit price (LKR)", min_value=0.0, value=1500.0, step=100.0)
        discount = st.slider("Discount", 0, 30, 5) / 100
        age = st.slider("Customer age", 1, 100, 35)
        gender = st.selectbox("Gender", sorted(df.Customer_Gender.dropna().unique()))
        category = st.selectbox("Medicine category", sorted(df.Medicine_Category.dropna().unique()))
        dosage = st.selectbox("Dosage form", sorted(df.Dosage_Form.dropna().unique()))
        branch = st.selectbox("Branch", sorted(df.Branch_Name.dropna().unique()))
        month = st.selectbox("Month", list(range(1,13)), index=0)
    with right:
        if st.button("Predict transaction revenue", type="primary"):
            sample = pd.DataFrame([{"Quantity":q,"Unit_Price_LKR":price,"Discount_Rate":discount,
                "Customer_Age":age,"Customer_Gender":gender,"Medicine_Category":category,
                "Dosage_Form":dosage,"Branch_Name":branch,"Month":month}])
            pred = max(0, float(model.predict(sample)[0]))
            st.metric("Estimated line revenue", f"LKR {pred:,.2f}")
            st.caption("Model estimate based on historical transaction patterns. Actual revenue can differ.")
        st.markdown("**Model notes**")
        st.write("- Algorithm: Random Forest Regressor")
        st.write("- Features: price, quantity, discount, age, category, dosage form, branch, month")
        st.write("- Evaluation on a held-out test set should be added before production use.")

st.divider()
st.caption("Portfolio prototype • Sri Lankan Rupees (LKR) • Built with Streamlit, Plotly and scikit-learn")
