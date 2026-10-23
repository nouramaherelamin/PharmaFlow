# Pharmacy Intelligence — Sales Analytics + Machine Learning

A portfolio-ready starter project built from the supplied 50,000-row pharmacy transaction dataset (January 2022–June 2023, Sri Lankan Rupees).

## Included
- `app.py`: interactive Streamlit dashboard with filters, KPIs, Plotly charts, a baseline monthly revenue forecast, and an interactive transaction revenue estimator.
- `api.py`: Flask REST API exposing the Random Forest transaction revenue prediction at `POST /predict`.
- `notebooks/Pharmacy_Sales_ML.ipynb`: data exploration, cleaning, feature engineering, time-series baseline, model training, evaluation, and plots.
- `data/pharmacy_sales.csv`: input data copy.

## Setup

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
```

## Run the Streamlit dashboard

```bash
streamlit run app.py
```

## Run the Flask prediction API

In a separate terminal:

```bash
python api.py
```

Test it:

```bash
curl -X POST http://127.0.0.1:5000/predict ^
  -H "Content-Type: application/json" ^
  -d "{\"Quantity\":2,\"Unit_Price_LKR\":1500,\"Discount_Rate\":0.05,\"Customer_Age\":35,\"Customer_Gender\":\"Female\",\"Medicine_Category\":\"Antibiotic\",\"Dosage_Form\":\"Capsule\",\"Branch_Name\":\"Pharmacy - Kandy City\",\"Month\":4}"
```

On PowerShell, curl quoting may differ. Use Postman if preferred. `Discount_Rate` is a decimal: `0.05` means 5%.

## Model scope and limitations
- Transaction prediction target: `Line_Total_LKR` (renamed to `Revenue` in code).
- Inputs: quantity, unit price, discount rate, customer age/gender, medicine category, dosage form, branch, and month.
- The Streamlit forecast is a simple linear-trend baseline over monthly totals. There are only 18 months of history, so forecast quality is limited and should not be presented as production-grade.
- The Random Forest demo currently trains on the full dataset for interactive predictions. The notebook includes a held-out evaluation workflow; use its test metrics and consider a time-aware split before publishing model performance.
- Predictions are estimates, not guaranteed revenue. No medical advice or patient-level decision-making is performed.

## Suggested next improvements
1. Use chronological train/test splits and compare against a naive baseline.
2. Add model persistence with `joblib` so Flask doesn't retrain on each startup.
3. Add unit tests and API validation for category values.
4. Add deployment configuration for Streamlit Community Cloud and a separate Flask host.
5. Consider a more suitable forecasting approach after collecting multiple years of monthly data.
