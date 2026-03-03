# AWS Lambda container image for the E-Waste Asset Lifecycle Optimizer backend
# Using the official AWS Python 3.12 Lambda base image (supports up to 10 GB)
FROM amazon/aws-lambda-python:3.12

# --------------------------------------------------------------------------
# Install Python dependencies into the Lambda task root
# --------------------------------------------------------------------------
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# --------------------------------------------------------------------------
# Copy application source
# --------------------------------------------------------------------------
COPY src/ ${LAMBDA_TASK_ROOT}/src/

# --------------------------------------------------------------------------
# Lambda handler entry-point
# Mangum wraps the FastAPI app so it satisfies the Lambda handler protocol.
# --------------------------------------------------------------------------
CMD ["src.backend.main.handler"]
