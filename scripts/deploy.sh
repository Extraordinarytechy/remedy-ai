#!/usr/bin/env bash
# Build and deploy RemedyAI (backend stack + frontend) from WSL/Linux with the AWS CLI and SAM CLI.
# Usage: ALERT_EMAIL=you@example.com ./scripts/deploy.sh
# Every run is logged to docs/evidence/ so the deployment history is part of the repository.
set -euo pipefail
cd "$(dirname "$0")/.."

STACK=${STACK:-remedy-ai}
REGION=${AWS_REGION:-us-east-1}
: "${ALERT_EMAIL:?Set ALERT_EMAIL for the AWS Budgets alert}"
mkdir -p docs/evidence
LOG="docs/evidence/deploy-$(date -u +%Y%m%dT%H%M%SZ).log"
exec > >(tee "$LOG") 2>&1

echo "== caller identity (the credentials the coding agent deploys with)"
aws sts get-caller-identity --output json | sed -E 's/\b([0-9]{4})[0-9]{4}([0-9]{4})\b/\1****\2/g'

echo "== lambda package"
[ -d .build/lambda ] || ./scripts/build_lambda.sh
file .build/lambda/pydantic_core/*.so | sed 's#.*/##'

echo "== validate"
sam validate --lint --region "$REGION"

echo "== deploy stack $STACK"
sam deploy \
  --template-file template.yaml \
  --stack-name "$STACK" \
  --region "$REGION" \
  --capabilities CAPABILITY_IAM \
  --resolve-s3 \
  --no-confirm-changeset \
  --no-fail-on-empty-changeset \
  --parameter-overrides "AlertEmail=$ALERT_EMAIL"

out() { aws cloudformation describe-stacks --stack-name "$STACK" --region "$REGION" --query "Stacks[0].Outputs[?OutputKey=='$1'].OutputValue" --output text; }
SITE_URL=$(out SiteUrl)
BUCKET=$(out SiteBucketName)
DIST=$(out DistributionId)
WATCH_FN=$(out SourceWatchFunctionName)

echo "== frontend -> s3://$BUCKET"
[ -f frontend/dist/index.html ] || { echo "Build the frontend first (npm run build in frontend/)"; exit 1; }
# Hashed assets are immutable; index.html and the un-hashed theme script must stay fresh.
aws s3 sync frontend/dist "s3://$BUCKET" --delete --region "$REGION" \
  --cache-control "public,max-age=31536000,immutable" --exclude index.html --exclude theme-init.js
aws s3 cp frontend/dist/index.html "s3://$BUCKET/index.html" --region "$REGION" \
  --cache-control "no-cache" --content-type "text/html; charset=utf-8"
aws s3 cp frontend/dist/theme-init.js "s3://$BUCKET/theme-init.js" --region "$REGION" \
  --cache-control "public,max-age=300" --content-type "text/javascript; charset=utf-8"
aws cloudfront create-invalidation --distribution-id "$DIST" --paths "/index.html" "/" "/theme-init.js" --query "Invalidation.Id" --output text

echo "== first Source Watch run"
aws lambda invoke --function-name "$WATCH_FN" --region "$REGION" /tmp/sourcewatch.json --query "StatusCode" --output text
cat /tmp/sourcewatch.json; echo

echo "== smoke test $SITE_URL"
curl -sS -o /dev/null -w "site %{http_code}\n" "$SITE_URL/"
curl -sS "$SITE_URL/health"; echo
curl -sS -o /dev/null -w "sources %{http_code}\n" "$SITE_URL/api/sources"

echo "DEPLOYED $SITE_URL"
