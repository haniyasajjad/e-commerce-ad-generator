# dags/training_pipeline.py
from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime
import mlflow
import os
import shutil
import tempfile

MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5000")
mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
mlflow.set_experiment("ad-creative-training")

MODEL_SOURCE = "/opt/airflow/models/gemma-2-2b-it-Q5_K_M.gguf"

def mock_training():
    with mlflow.start_run(run_name="gemma-finetune-v1") as run:
        mlflow.log_param("model", "gemma-2-2b-it-Q5")
        mlflow.log_param("quantization", "Q5_K_M")
        mlflow.log_param("training_type", "mock")
        
        mlflow.log_metric("mock_perplexity", 12.5)
        mlflow.log_metric("mock_loss", 0.85)
        mlflow.log_metric("training_time_sec", 120)

        if not os.path.exists(MODEL_SOURCE):
            print(f"⚠️ Model file not found: {MODEL_SOURCE}")
            print("Creating placeholder model for testing...")
            # Create a tiny placeholder file for testing
            os.makedirs(os.path.dirname(MODEL_SOURCE), exist_ok=True)
            with open(MODEL_SOURCE, "w") as f:
                f.write("MOCK_MODEL_FILE")

        # Create a proper MLflow Model folder
        with tempfile.TemporaryDirectory() as tmpdir:
            model_dir = os.path.join(tmpdir, "model")
            os.makedirs(model_dir, exist_ok=True)

            # Copy the GGUF file - FIXED: using shutil.copy2 instead of os.copy
            dest_path = os.path.join(model_dir, "gemma.gguf")
            shutil.copy2(MODEL_SOURCE, dest_path)
            print(f"✅ Copied model to {dest_path}")

            # Minimal MLmodel file so mlflow.register_model accepts it
            mlmodel_yaml = f"""\
artifact_path: model
flavors:
  python_function:
    loader_module: mlflow.pyfunc
    python_version: 3.12
run_id: {run.info.run_id}
utc_time_created: "{datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')}"
model_uuid: {run.info.run_id}
"""
            with open(os.path.join(tmpdir, "MLmodel"), "w") as f:
                f.write(mlmodel_yaml)

            # Log the whole folder
            mlflow.log_artifacts(tmpdir, artifact_path="model")
            print("✅ Artifacts logged to MLflow")

        # Register — this now works perfectly
        model_uri = f"runs:/{run.info.run_id}/model"
        result = mlflow.register_model(model_uri, "AdCreativeModel")
        print(f"✅ SUCCESS — AdCreativeModel version {result.version} registered")
        
        # Log the version as metric
        mlflow.log_param("registered_version", result.version)

with DAG(
    dag_id="weekly_training",
    schedule="@weekly",
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=["mlops", "training"],
) as dag:
    train = PythonOperator(
        task_id="train_model",
        python_callable=mock_training,
    )