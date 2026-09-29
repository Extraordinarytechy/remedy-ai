#!/usr/bin/env bash
# Builds the Lambda package into .build/lambda for Python 3.13 on arm64 (Graviton).
# Wheels are downloaded for the Lambda platform explicitly, so the build does not depend on
# the host OS or host Python version (a Windows or x86 wheel can never end up in the zip).
set -euo pipefail
cd "$(dirname "$0")/.."

OUT=.build/lambda
rm -rf "$OUT"
mkdir -p "$OUT"

python3 -m pip install \
  --quiet \
  --target "$OUT" \
  --platform manylinux2014_aarch64 \
  --implementation cp \
  --python-version 3.13 \
  --only-binary=:all: \
  --upgrade \
  -r backend/requirements.txt

cp -r backend/src backend/knowledge "$OUT"/
find "$OUT" -name "__pycache__" -type d -prune -exec rm -rf {} +
echo "Built $OUT ($(du -sh "$OUT" | cut -f1))"
