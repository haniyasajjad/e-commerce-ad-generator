# src/api/main.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from llama_cpp import Llama
import time
from prometheus_client import Counter, Histogram, start_http_server, generate_latest
from fastapi.responses import PlainTextResponse
import os
import mlflow
from dotenv import load_dotenv

load_dotenv()

# Connect to MLflow inside docker-compose
mlflow.set_tracking_uri("http://localhost:5000")
mlflow.set_experiment("ad-creative-experiment")

app = FastAPI(title="E-Commerce Ad Creative Generator")

# Prometheus metrics
REQUEST_COUNT = Counter("ad_requests_total", "Total requests", ["status"])
REQUEST_LATENCY = Histogram("ad_latency_seconds", "Latency of ad generation")
THROUGHPUT = Counter("ad_throughput_total", "Total generated ads")
QUALITY_SCORE = Histogram("ad_quality_score", "Estimated quality (0-1)")

print("Loading Gemma model...")
llm = Llama(
    model_path="models/gemma-2-2b-it-Q5_K_M.gguf",
    n_ctx=8192,
    n_threads=4,
    n_batch=512,
    verbose=False
)

class ProductInput(BaseModel):
    title: str
    description: str = ""

def estimate_quality(text: str) -> float:
    score = len(text.split()) / 80.0
    keywords = ["sale", "limited", "now", "free", "best", "save", "grab", "deal", "under"]
    score += sum(1 for kw in keywords if kw in text.lower()) * 0.08
    emoji_bonus = sum(1 for c in text if c in "🎧🔥😎🚀💥") * 0.05
    return min(1.0, max(0.0, score + emoji_bonus))

@app.post("/generate")
async def generate_ad(input: ProductInput):
    start_time = time.time()
    try:
        prompt = f"""
<bos><start_of_turn>user
Write a catchy, engaging Instagram/Facebook ad (max 80 words).

Product: {input.title}
Description: {input.description}
<end_of_turn>
<start_of_turn>model
        """

        output = llm(prompt, max_tokens=120, temperature=0.8, top_p=0.9)
        ad_text = output["choices"][0]["text"].strip()

        latency = time.time() - start_time
        quality = estimate_quality(ad_text)

        # Prometheus
        REQUEST_COUNT.labels(status="success").inc()
        REQUEST_LATENCY.observe(latency)
        THROUGHPUT.inc()
        QUALITY_SCORE.observe(quality)

        # MLflow inference logging – lightweight
        mlflow.log_metrics({
            "latency_sec": latency,
            "quality_score": quality,
        })

        return {
            "ad_creative": ad_text,
            "latency_sec": round(latency, 2),
            "quality_score": round(quality, 3)
        }

    except Exception as e:
        REQUEST_COUNT.labels(status="error").inc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/metrics")
async def metrics():
    return PlainTextResponse(generate_latest())

# Prometheus exporter
start_http_server(8001)
