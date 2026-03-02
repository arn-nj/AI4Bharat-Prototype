#!/usr/bin/env bash
# deploy.sh — Deploy the E-Waste Asset Lifecycle Optimizer to AWS
# Usage:  ./scripts/deploy.sh [dev|staging|prod]
set -euo pipefail

STAGE="${1:-dev}"
STACK_NAME="ewaste-optimizer-${STAGE}"
REGION="${AWS_REGION:-us-east-1}"
MODEL_ID="${BEDROCK_MODEL_ID:-qwen.qwen3-30b-a3b}"

echo "═══════════════════════════════════════════════════════════"
echo "  Deploying E-Waste Asset Lifecycle Optimizer"
echo "  Stage:    ${STAGE}"
echo "  Stack:    ${STACK_NAME}"
echo "  Region:   ${REGION}"
echo "  Model:    ${MODEL_ID}"
echo "═══════════════════════════════════════════════════════════"

# 1. Build
echo ""
echo "▶ Building SAM application..."
sam build --use-container

# 2. Deploy
echo ""
echo "▶ Deploying to AWS..."
sam deploy \
  --stack-name "${STACK_NAME}" \
  --no-confirm-changeset \
  --no-fail-on-empty-changeset \
  --capabilities CAPABILITY_IAM \
  --region "${REGION}" \
  --parameter-overrides \
    "StageName=${STAGE}" \
    "BedrockModelId=${MODEL_ID}" \
    "BedrockRegion=${REGION}"

# 3. Capture outputs
API_URL=$(aws cloudformation describe-stacks \
  --stack-name "${STACK_NAME}" \
  --region "${REGION}" \
  --query 'Stacks[0].Outputs[?OutputKey==`ApiUrl`].OutputValue' \
  --output text)

BUCKET=$(aws cloudformation describe-stacks \
  --stack-name "${STACK_NAME}" \
  --region "${REGION}" \
  --query 'Stacks[0].Outputs[?OutputKey==`StorageBucketName`].OutputValue' \
  --output text)

# 4. Upload model artifacts to S3
echo ""
echo "▶ Syncing model artifacts to S3..."
aws s3 sync src/model_training/models/ "s3://${BUCKET}/models/" \
  --exclude "plots/*" \
  --region "${REGION}"

# 5. Smoke test
echo ""
echo "▶ Running smoke test..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "${API_URL}/health" --max-time 30)

if [ "$HTTP_CODE" -eq 200 ]; then
  echo "  ✅ Health check passed (HTTP ${HTTP_CODE})"
else
  echo "  ❌ Health check failed (HTTP ${HTTP_CODE})"
  exit 1
fi

# 6. Summary
echo ""
echo "═══════════════════════════════════════════════════════════"
echo "  ✅ Deployment complete!"
echo ""
echo "  API URL:     ${API_URL}"
echo "  Swagger UI:  ${API_URL}/docs"
echo "  S3 Bucket:   ${BUCKET}"
echo "═══════════════════════════════════════════════════════════"
