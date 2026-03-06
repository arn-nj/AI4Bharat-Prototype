# AWS Lambda container image — E-Waste Asset Lifecycle Optimizer
# Base: official AWS Python 3.12 Lambda image (Amazon Linux 2023, x86_64)
FROM amazon/aws-lambda-python:3.12

# --------------------------------------------------------------------------
# Upgrade pip
# --------------------------------------------------------------------------
RUN pip install --no-cache-dir --upgrade pip

# --------------------------------------------------------------------------
# Install dependencies in two layers for better Docker cache reuse:
#   Layer 1 — heavy ML/data packages (rarely change → cached across builds)
#   Layer 2 — app packages (change each release)
# --------------------------------------------------------------------------

# Layer 1: large ML packages
RUN pip install --no-cache-dir \
    "scikit-learn>=1.3.0" \
    "pandas>=2.0.0" \
    "numpy>=1.24.0" \
    "joblib>=1.3.0"

# Layer 2: remaining app, DB and AWS packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# --------------------------------------------------------------------------
# Copy application source (includes src/model_training/models/*.joblib)
# --------------------------------------------------------------------------
COPY src/ ${LAMBDA_TASK_ROOT}/src/

# --------------------------------------------------------------------------
# Lambda handler — Mangum wraps FastAPI for the Lambda invocation protocol
# --------------------------------------------------------------------------
CMD ["src.backend.main.handler"]

