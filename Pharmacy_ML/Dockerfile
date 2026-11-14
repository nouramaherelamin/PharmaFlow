FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src ./src
COPY app ./app
COPY models ./models
COPY data/processed/monthly_history.csv data/processed/dashboard_data.json data/processed/medicines.json data/processed/medicine_history.csv ./data/processed/
ENV PORT=7860
EXPOSE 7860
CMD gunicorn app.app:app --bind 0.0.0.0:${PORT}
