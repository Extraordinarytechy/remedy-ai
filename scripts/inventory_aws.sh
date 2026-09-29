#!/usr/bin/env bash
# Writes an inventory of every AWS resource RemedyAI created to local/aws-inventory/ (git-ignored).
set -uo pipefail
cd "$(dirname "$0")/.."
REGION=${AWS_REGION:-us-east-1}
OUT=local/aws-inventory
mkdir -p "$OUT"
ts=$(date -u +%Y-%m-%dT%H:%M:%SZ)

aws sts get-caller-identity --output json > "$OUT/caller-identity.json"
for s in remedy-ai aws-sam-cli-managed-default; do
  aws cloudformation describe-stacks --stack-name "$s" --region "$REGION" --output json > "$OUT/stack-$s.json" 2>&1
  aws cloudformation list-stack-resources --stack-name "$s" --region "$REGION" --output json > "$OUT/resources-$s.json" 2>&1
done
ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
aws budgets describe-budgets --account-id "$ACCOUNT" --output json > "$OUT/budgets.json" 2>&1
aws notificationscontacts list-email-contacts --region us-east-1 --output json > "$OUT/notification-email-contacts.json" 2>&1
aws logs describe-log-groups --log-group-name-prefix /aws/lambda/remedy-ai --region "$REGION" --output json > "$OUT/log-groups.json" 2>&1
echo "$ts" > "$OUT/captured_at.txt"
echo INVENTORY_DONE
