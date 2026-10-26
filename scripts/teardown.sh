#!/usr/bin/env bash
set -euo pipefail
# Preview is the default; no cloud mutation without the explicit --execute flag.
if [ "${1:-}" != '--execute' ]; then
  echo 'Preview: destroy the Resonance CloudFormation stack. Retained raw/evidence buckets, records and logs remain for explicit review.'
  exit 0
fi
aws cloudformation delete-stack --stack-name Resonance
aws cloudformation wait stack-delete-complete --stack-name Resonance
