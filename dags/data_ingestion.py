# dags/data_ingestion.py
from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime
import pandas as pd
from azure.storage.blob import BlobServiceClient
import os

def ingest_products():
    connect_str = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    if not connect_str:
        raise ValueError("AZURE_STORAGE_CONNECTION_STRING is missing!")

    blob_service = BlobServiceClient.from_connection_string(connect_str)
    container = blob_service.get_container_client("products")

    df = pd.DataFrame({
        "title": ["Wireless Earbuds", "Smart Watch", "Coffee Maker"],
        "description": [
            "Noise-cancelling, 30h battery",
            "Fitness tracking",
            "12-cup programmable"
        ]
    })

    csv_data = df.to_csv(index=False)
    blob_client = container.get_blob_client("latest_products.csv")
    blob_client.upload_blob(csv_data, overwrite=True)

    print("Uploaded latest_products.csv to Azure Blob Storage.")

with DAG(
    dag_id="data_ingestion",
    schedule="@daily",
    start_date=datetime(2025,1,1),
    catchup=False
) as dag:

    ingest = PythonOperator(
        task_id="ingest_products",
        python_callable=ingest_products
    )
