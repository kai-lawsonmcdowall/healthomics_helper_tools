#!/usr/bin/env bash

AWS_REGION=eu-west-2   # change if needed

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
    echo "$repo"
  fi
done
