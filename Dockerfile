FROM python:3.12-slim AS builder
WORKDIR /app

# Install build deps for llama-cpp-python
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Install ALL dependencies into /install
RUN pip install --prefix=/install -r requirements.txt --no-cache-dir


# -----------------------------
FROM python:3.12-slim
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*
# Copy installed Python packages from builder stage
COPY --from=builder /install /usr/local

# Your app files
COPY src/ src/
COPY models/gemma-2-2b-it-Q5_K_M.gguf models/

EXPOSE 8000
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
