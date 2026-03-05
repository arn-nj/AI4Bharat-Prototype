#!/usr/bin/env bash
# deploy.sh — Build and deploy the full stack (backend + frontend) to AWS
# Usage:  bash scripts/deploy.sh [dev|staging|prod]
#         ./scripts/deploy.sh  [dev|staging|prod]   (after chmod +x)

# Re-exec with bash if invoked via sh (pipefail is bash-only)
if [ -z "${BASH_VERSION:-}" ]; then
  exec bash "$0" "$@"
fi

set -euo pipefail

STAGE="${1:-dev}"
STACK_NAME="ewaste-optimizer-${STAGE}"
REGION="${AWS_REGION:-us-east-1}"
MODEL_ID="${BEDROCK_MODEL_ID:-qwen.qwen3-next-80b-a3b}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FRONTEND_DIR="${REPO_ROOT}/src/frontend"

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

# 3. Capture stack outputs
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

FRONTEND_BUCKET=$(aws cloudformation describe-stacks \
  --stack-name "${STACK_NAME}" \
  --region "${REGION}" \
  --query 'Stacks[0].Outputs[?OutputKey==`FrontendBucketName`].OutputValue' \
  --output text)

CF_DIST_ID=$(aws cloudformation describe-stacks \
  --stack-name "${STACK_NAME}" \
  --region "${REGION}" \
  --query 'Stacks[0].Outputs[?OutputKey==`FrontendDistributionId`].OutputValue' \
  --output text)

FRONTEND_URL=$(aws cloudformation describe-stacks \
  --stack-name "${STACK_NAME}" \
  --region "${REGION}" \
  --query 'Stacks[0].Outputs[?OutputKey==`FrontendUrl`].OutputValue' \
  --output text)

# 4. Upload model artifacts to S3
echo ""
echo "▶ Syncing model artifacts to S3..."
aws s3 sync src/model_training/models/ "s3://${BUCKET}/models/" \
  --exclude "plots/*" \
  --region "${REGION}"

# 5. Build React frontend
echo ""
echo "▶ Building React frontend..."
(cd "${FRONTEND_DIR}" && \
  npm ci --prefer-offline && \
  VITE_BACKEND_URL="${API_URL}" npm run build)

# 6. Deploy frontend to S3 + invalidate CloudFront
echo ""
echo "▶ Syncing React build to S3..."
aws s3 sync "${FRONTEND_DIR}/dist/" "s3://${FRONTEND_BUCKET}/" \
  --delete --region "${REGION}"

echo ""
echo "▶ Invalidating CloudFront cache..."
aws cloudfront create-invalidation \
  --distribution-id "${CF_DIST_ID}" \
  --paths "/*" \
  --region us-east-1 \
  --output text --query 'Invalidation.Id'

# 7. Smoke test
echo ""
echo "▶ Running smoke test..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "${API_URL}/health" --max-time 30)

if [ "$HTTP_CODE" -eq 200 ]; then
  echo "  ✅ Health check passed (HTTP ${HTTP_CODE})"
else
  echo "  ❌ Health check failed (HTTP ${HTTP_CODE})"
  exit 1
fi

# 8. Summary
echo ""
echo "═══════════════════════════════════════════════════════════"
echo "  ✅ Deployment complete!"
echo ""
echo "  Frontend:    ${FRONTEND_URL}"
echo "  API URL:     ${API_URL}"
echo "  Swagger UI:  ${API_URL}/docs"
echo "  S3 Bucket:   ${BUCKET}"
echo "═══════════════════════════════════════════════════════════"
