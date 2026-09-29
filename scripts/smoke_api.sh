#!/usr/bin/env bash
# Smoke-tests a deployed RemedyAI API. Usage: ./scripts/smoke_api.sh [base-url]
set -uo pipefail
cd "$(dirname "$0")/.."
BASE=${1:-}
if [ -z "$BASE" ]; then
  API_ID=$(aws cloudformation describe-stack-resource --stack-name remedy-ai --logical-resource-id HttpApi --query StackResourceDetail.PhysicalResourceId --output text)
  BASE="https://${API_ID}.execute-api.${AWS_REGION:-us-east-1}.amazonaws.com"
fi
echo "BASE $BASE"
curl -sS "$BASE/health"; echo
FIX=$(curl -sS "$BASE/api/fixtures")
echo "$FIX" | python3 -c "import sys,json; d=json.load(sys.stdin); print('fixtures', list(d))"
for k in case1_apple_iphone14plus case2_visa_infinite_sony case3_uk_samsung_tv case4_unknown_unsupported; do
  echo "$FIX" | python3 -c "import sys,json; print(json.dumps(json.load(sys.stdin)['$k']))" \
    | curl -sS -X POST "$BASE/api/evaluate" -H 'content-type: application/json' --data @- \
    | python3 -c "import sys,json; d=json.load(sys.stdin); print('$k', d['has_coverage'], [(r['route_id'], r['status']) for r in d['matched_routes']], d.get('evaluation_date'))"
done
curl -sS "$BASE/api/sources" | python3 -c "import sys,json; d=json.load(sys.stdin); [print(' ', s['id'], s['watch'].get('http_status'), s['watch'].get('listed_on_apple_index')) for s in d['sources']]; print('apple index titles', len((d.get('apple_index') or {}).get('titles', [])))"
echo SMOKE_DONE
