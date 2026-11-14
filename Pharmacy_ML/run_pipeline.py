"""Run the whole pipeline: python run_pipeline.py"""
from src import preprocess, eda, train, evaluate, medicine_model, dashboard_data

for step in (preprocess, eda, train, evaluate, medicine_model, dashboard_data):
    print(f"\n=== {step.__name__} ===")
    step.main()
