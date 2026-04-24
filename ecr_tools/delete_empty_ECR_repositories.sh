#!/usr/bin/env bash

set -euo pipefail

AWS_REGION=eu-west-2   # change if needed
DRY_RUN=false

# Parse arguments
for arg in "$@"; do
  case "$arg" in
    --dry-run)
      DRY_RUN=true
      shift
      ;;
    *)
      echo "Unknown option: $arg"
      echo "Usage: $0 [--dry-run]"
      exit 1
      ;;
  esac
done

for repo in $(aws ecr describe-repositories \
  --region "$AWS_REGION" \
  --query 'repositories[].repositoryName' \
  --output text); do

  image_count=$(aws ecr list-images \
    --region "$AWS_REGION" \
    --repository-name "$repo" \
    --query 'length(imageIds)' \
    --output text)

  if [ "$image_count" -eq 0 ]; then
    if [ "$DRY_RUN" = true ]; then
      echo "[DRY-RUN] Would delete empty repository: $repo"
    else
      echo "Deleting empty repository: $repo"
      aws ecr delete-repository \
        --region "$AWS_REGION" \
        --repository-name "$repo"
    fi
  fi
done
