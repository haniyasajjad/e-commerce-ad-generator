# dags/batch_inference.py
from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import pandas as pd
import requests
import mlflow
from azure.storage.blob import BlobServiceClient
import os
import io

# Local API endpoint
API_ENDPOINT = "http://ad-creative-api:8001/generate"

def batch_generate_ads():
    # 1. Pull latest products (Azure or local fallback)
    connect_str = os.getenv("AZURE_STORAGE_CONNECTION_STRING", "")
    
    if not connect_str:
        print("⚠️ No Azure connection — loading from local file")
        # Try local file first
        local_path = "/opt/airflow/data/products.csv"
        if os.path.exists(local_path):
            df = pd.read_csv(local_path)
        else:
            print("⚠️ No local file found — using mock data")
            df = pd.DataFrame({
                "title": ["Wireless Earbuds", "Smart Watch", "Coffee Maker"],
                "description": [
                    "Noise-cancelling, 30h battery",
                    "Fitness tracking with heart rate",
                    "12-cup programmable"
                ]
            })
    else:
        try:
            blob_service = BlobServiceClient.from_connection_string(connect_str)
            container = blob_service.get_container_client("products")
            blob = container.get_blob_client("latest_products.csv")
            csv_content = blob.download_blob().readall()
            df = pd.read_csv(io.StringIO(csv_content.decode("utf-8")))
            print(f"✅ Loaded {len(df)} products from Azure")
        except Exception as e:
            print(f"❌ Azure read failed: {e}")
            # Fallback to mock
            df = pd.DataFrame({
                "title": ["Wireless Earbuds", "Smart Watch"],
                "description": ["Premium audio", "Health tracking"]
            })

    # 2. MLflow tracking
    mlflow.set_tracking_uri("http://mlflow:5000")

    with mlflow.start_run(run_name=f"batch_{datetime.now().strftime('%Y%m%d-%H%M')}"):
        total = 0
        failed = 0
        
        for idx, row in df.iterrows():
            payload = {
                "title": row["title"],
                "description": row.get("description", "")
            }
            try:
                r = requests.post(API_ENDPOINT, json=payload, timeout=30)
                if r.status_code == 200:
                    ad = r.json()["ad_creative"]
                    mlflow.log_text(ad, f"ads/ad_{idx}.txt")
                    total += 1
                else:
                    print(f"API error {r.status_code} for product {idx}")
                    failed += 1
            except Exception as e:
                print(f"Error processing product {idx}: {e}")
                failed += 1

        mlflow.log_metric("total_ads_generated", total)
        mlflow.log_metric("failed_generations", failed)
        mlflow.log_metric("success_rate", total / len(df) if len(df) > 0 else 0)
        
        print(f"✅ Batch complete: {total} ads generated, {failed} failed")

# ----------------------------------------------------------------

default_args = {
    "owner": "airflow",
    "start_date": datetime(2024, 1, 1),
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    dag_id="batch_inference",
    default_args=default_args,
    schedule_interval=None,   # run manually
    catchup=False,
    tags=["mlops", "inference"]
) as dag:
    
    run_batch = PythonOperator(
        task_id="run_batch",
        python_callable=batch_generate_ads
    )