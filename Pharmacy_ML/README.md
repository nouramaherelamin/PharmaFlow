# Pharmacy Revenue Forecasting

End-to-end ML project: forecast next-month revenue (LKR) for every Branch x Medicine category from 50,000 pharmacy transactions (Jan 2022 – Jun 2023), served through an interactive dashboard.

**PharmaFlow app (dark theme):** Predict Sales (pick a medicine + branch → expected units, revenue, 80% range, stock check, branch comparison) · Forecast (category x branch revenue, backtest, sortable table) · Analytics (KPIs, trends, heatmap) · Model Info (honest evaluation of both models) · About.

## Results
**Category revenue model** (Forecast page). Time-based split (train to 2023-03, test 2023-04..06):

| Model | MAE (LKR) | R² | WAPE |
|---|---|---|---|
| Baseline: 3-month mean | 30,244 | 0.818 | 21.0% |
| **Ridge (selected)** | **28,899** | **0.832** | **20.1%** |
| RandomForest | 29,761 | 0.824 | 20.7% |
| GradientBoosting | 30,476 | 0.816 | 21.2% |

The data is very stable month to month, so the gain over a simple average is modest (~4% MAE); small categories have higher relative error.

**Medicine demand model** (Predict Sales page): units per medicine x branch x month. R² is about 0 on the test months and every model ties with the simple average (MAE ~4.36 units): in this dataset each medicine sells about the same amount each month and no feature explains the differences, so the app shows an honest 80% range rather than a falsely precise number.

## Structure
```
data/raw, data/processed   src/ (config, preprocess, eda, features, train, evaluate, medicine_model, dashboard_data)
models/                    app/ (app.py, templates/index.html)
reports/                   notebooks/   run_pipeline.py   Dockerfile   Procfile
```

## Run locally
```bash
pip install -r requirements.txt
python run_pipeline.py        # preprocess -> EDA -> train -> evaluate -> medicine model -> dashboard data
python -m app.app             # http://localhost:5000
```

## Deploy (free options)
- **Render / Railway:** push the repo to GitHub, create a Web Service, build `pip install -r requirements.txt`, start `gunicorn app.app:app` (a `Procfile` is included). Commit `models/` and `data/processed/` so the app can start.
- **Hugging Face Spaces (Docker):** create a Docker Space and push the repo; the included `Dockerfile` serves on port 7860.

## API
`GET /api/predict_medicine?medicine_id=..&branch=..&price=..&stock=..` · `GET /api/medicines` · `GET /api/forecast?branch=...&category=...` · `GET /api/forecast_all` · `GET /api/overview` · `GET /api/performance` · `POST /predict`
