# dags/data_ingestion.py
from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime
import pandas as pd
from azure.storage.blob import BlobServiceClient
import os

def ingest_products():
    connect_str = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    
    # Mock data
    df = pd.DataFrame({
        "title": ["Wireless Earbuds", "Smart Watch", "Coffee Maker", "Laptop Stand", "USB-C Hub"],
        "description": [
            "Noise-cancelling, 30h battery",
            "Fitness tracking with heart rate",
            "12-cup programmable",
            "Ergonomic aluminum design",
            "7-in-1 multiport adapter"
        ]
    })
    
    if not connect_str:
        print("⚠️ AZURE_STORAGE_CONNECTION_STRING not set — running in LOCAL mode")
        # Save locally for batch_inference to use
        os.makedirs("/opt/airflow/data", exist_ok=True)
        local_path = "/opt/airflow/data/products.csv"
        df.to_csv(local_path, index=False)
        print(f"✅ Saved products to {local_path}")
        return

    # Azure mode
    try:
        blob_service = BlobServiceClient.from_connection_string(connect_str)
        container = blob_service.get_container_client("products")
        
        csv_data = df.to_csv(index=False)
        blob_client = container.get_blob_client("latest_products.csv")
        blob_client.upload_blob(csv_data, overwrite=True)
        
        print("✅ Uploaded latest_products.csv to Azure Blob Storage")
    except Exception as e:
        print(f"❌ Azure upload failed: {e}")
        # Fallback to local
        os.makedirs("/opt/airflow/data", exist_ok=True)
        df.to_csv("/opt/airflow/data/products.csv", index=False)
        print("✅ Saved locally as fallback")

with DAG(
    dag_id="data_ingestion",
    schedule="@daily",
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=["mlops", "data"]
) as dag:

    ingest = PythonOperator(
        task_id="ingest_products",
        python_callable=ingest_products
    )