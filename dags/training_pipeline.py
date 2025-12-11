# dags/training_pipeline.py
from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime
import mlflow
import os
import shutil

MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5000")
mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
mlflow.set_experiment("ad-creative-training")

MODEL_SOURCE = "/opt/airflow/models/gemma-2-2b-it-Q5_K_M.gguf"

def mock_training():

    with mlflow.start_run(run_name="gemma-finetune-v1") as run:

        mlflow.log_param("model", "gemma-2-2b-it-Q5")
        mlflow.log_metric("mock_perplexity", 12.5)

        # Ensure model exists inside container
        if os.path.exists(MODEL_SOURCE):
            mlflow.log_artifact(MODEL_SOURCE)
        else:
            print("Model file missing inside Airflow container!")

        # Register the model
        mlflow.register_model(
            f"runs:/{run.info.run_id}/artifacts/gemma-2-2b-it-Q5_K_M.gguf",
            "AdCreativeModel"
        )

with DAG(
    dag_id='weekly_training',
    schedule='@weekly',
    start_date=datetime(2025,1,1),
    catchup=False
) as dag:

    train = PythonOperator(
        task_id='train_model',
        python_callable=mock_training
    )
