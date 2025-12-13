# src/api/main.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from llama_cpp import Llama
import time
from prometheus_client import start_http_server, generate_latest
from fastapi.responses import PlainTextResponse
import os
import mlflow
from dotenv import load_dotenv

# Import our custom metrics
from src.metrics.custom_exporter import (
    RequestTracker,
    track_quality,
    track_response_size,
    set_model_info,
    model_load_time,
    initialize_metrics
)
from src.monitoring.drift_detection import drift_detector

load_dotenv()

# Connect to MLflow
mlflow.set_tracking_uri("http://localhost:5000")
mlflow.set_experiment("ad-creative-experiment")

app = FastAPI(title="E-Commerce Ad Creative Generator")

# Initialize metrics
initialize_metrics()

# Load model and track load time
print("Loading Gemma model...")
model_start = time.time()
llm = Llama(
    model_path="models/gemma-2-2b-it-Q5_K_M.gguf",
    n_ctx=8192,
    n_threads=4,
    n_batch=512,
    verbose=False
)
load_duration = time.time() - model_start
model_load_time.set(load_duration)
print(f"✅ Model loaded in {load_duration:.2f}s")

# Set model info for Prometheus
set_model_info(
    model_name="gemma-2-2b-it",
    version="Q5_K_M",
    quantization="Q5"
)

class ProductInput(BaseModel):
    title: str
    description: str = ""

def estimate_quality(text: str) -> float:
    """Estimate ad quality score (0-1)"""
    # Base score from word count
    score = min(len(text.split()) / 80.0, 0.5)
    
    # Bonus for marketing keywords
    keywords = ["sale", "limited", "now", "free", "best", "save", "grab", "deal", "under"]
    score += sum(1 for kw in keywords if kw.lower() in text.lower()) * 0.08
    
    # Bonus for emojis
    emoji_bonus = sum(1 for c in text if c in "🎧🔥😎🚀💥🎉✨⭐") * 0.05
    
    # Penalty for very short ads
    if len(text.split()) < 20:
        score *= 0.7
    
    return min(1.0, max(0.0, score + emoji_bonus))

@app.post("/generate")
async def generate_ad(input: ProductInput):
    """Generate ad creative with full metric tracking"""
    
    with RequestTracker(endpoint="/generate") as tracker:
        try:
            prompt = f"""<bos><start_of_turn>user
Write a catchy, engaging Instagram/Facebook ad (max 80 words).

Product: {input.title}
Description: {input.description}

Make it compelling with emojis and call-to-action!
<end_of_turn>
<start_of_turn>model
"""

            output = llm(prompt, max_tokens=120, temperature=0.8, top_p=0.9)
            ad_text = output["choices"][0]["text"].strip()
            
            # Calculate metrics
            quality = estimate_quality(ad_text)
            response_size = len(ad_text.encode('utf-8'))
            
            # Track custom metrics
            track_quality(quality)
            track_response_size(response_size)
            
            # Drift detection
            drift_detector.add_prediction(quality, ad_text)
            
            # MLflow logging (lightweight)
            try:
                with mlflow.start_run(nested=True):
                    mlflow.log_metrics({
                        "inference_quality": quality,
                        "response_length": len(ad_text)
                    })
            except Exception as e:
                print(f"MLflow logging failed: {e}")
            
            return {
                "ad_creative": ad_text,
                "quality_score": round(quality, 3),
                "char_count": len(ad_text),
                "word_count": len(ad_text.split())
            }
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return PlainTextResponse(generate_latest())

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "model_loaded": True,
        "service": "ad-creative-api"
    }

@app.get("/drift-report")
async def drift_report():
    """Get model drift detection report"""
    return drift_detector.get_drift_report()

@app.get("/")
async def root():
    """Root endpoint with API info"""
    return {
        "service": "E-Commerce Ad Creative Generator",
        "version": "1.0.0",
        "endpoints": {
            "/generate": "POST - Generate ad creative",
            "/metrics": "GET - Prometheus metrics",
            "/health": "GET - Health check",
            "/docs": "GET - API documentation"
        }
    }

# Start Prometheus exporter on port 8001
start_http_server(8001)
print("✅ Prometheus metrics server started on :8001")