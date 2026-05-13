#!/bin/bash
set -euo pipefail

# ---------------------------------------
# Defaults
# ---------------------------------------

DEFAULT_ROLE_ARN="arn:aws:iam::512620729442:role/dev-omicsWorkflowRun-role"
DEFAULT_REGION="eu-west-2"
DEFAULT_OUTPUT_URI="s3://dev-sonrai-pipelines/omics-output/"
DEFAULT_STORAGE_CAPACITY="1200"
DEFAULT_LOG_LEVEL="ALL"

# ---------------------------------------
# Prompt User for Required Inputs
# ---------------------------------------

echo "========================================"
echo "AWS HealthOmics Workflow Launcher"
echo "========================================"
echo ""

# Workflow ID (required)
read -rp "Enter Workflow ID (required): " WORKFLOW_ID
if [[ -z "$WORKFLOW_ID" ]]; then
    echo "ERROR: Workflow ID is required."
    exit 1
fi

# Run name prefix (required)
read -rp "Enter run name prefix (required): " RUN_NAME_PREFIX
if [[ -z "$RUN_NAME_PREFIX" ]]; then
    echo "ERROR: Run name prefix is required."
    exit 1
fi

RUN_NAME="${RUN_NAME_PREFIX}-test-run-$(date +%Y%m%d-%H%M%S)"

# Parameters JSON S3 URI (required)
read -rp "Enter parameters JSON S3 URI (required): " PARAMS_URI
if [[ -z "$PARAMS_URI" ]]; then
    echo "ERROR: Parameters URI is required."
    exit 1
fi

# ---------------------------------------
# Prompt User for Optional Inputs (with defaults)
# ---------------------------------------

read -rp "IAM Role ARN [$DEFAULT_ROLE_ARN]: " ROLE_ARN
ROLE_ARN="${ROLE_ARN:-$DEFAULT_ROLE_ARN}"

read -rp "AWS Region [$DEFAULT_REGION]: " REGION
REGION="${REGION:-$DEFAULT_REGION}"

read -rp "Output S3 URI [$DEFAULT_OUTPUT_URI]: " OUTPUT_URI
OUTPUT_URI="${OUTPUT_URI:-$DEFAULT_OUTPUT_URI}"

read -rp "Storage Capacity (GiB) [$DEFAULT_STORAGE_CAPACITY]: " STORAGE_CAPACITY
STORAGE_CAPACITY="${STORAGE_CAPACITY:-$DEFAULT_STORAGE_CAPACITY}"

read -rp "Log Level (ALL|OFF) [$DEFAULT_LOG_LEVEL]: " LOG_LEVEL
LOG_LEVEL="${LOG_LEVEL:-$DEFAULT_LOG_LEVEL}"

# ---------------------------------------
# Display Final Configuration
# ---------------------------------------

echo ""
echo "========================================"
echo "Workflow Configuration"
echo "========================================"
echo "Workflow ID      : $WORKFLOW_ID"
echo "Run Name         : $RUN_NAME"
echo "Role ARN         : $ROLE_ARN"
echo "Parameters       : $PARAMS_URI"
echo "Output URI       : $OUTPUT_URI"
echo "Region           : $REGION"
echo "Storage Capacity : ${STORAGE_CAPACITY} GiB"
echo "Log Level        : $LOG_LEVEL"
echo "========================================"
echo ""

# ---------------------------------------
# Validate AWS CLI
# ---------------------------------------

if ! command -v aws &> /dev/null; then
    echo "ERROR: AWS CLI not found. Please install it first."
    exit 1
fi

# ---------------------------------------
# Download params.json temporarily
# ---------------------------------------

TEMP_PARAMS=$(mktemp)
trap "rm -f $TEMP_PARAMS" EXIT

echo "Downloading parameters file..."
aws s3 cp "$PARAMS_URI" "$TEMP_PARAMS" --region "$REGION"
echo ""

# ---------------------------------------
# Start Workflow Run
# ---------------------------------------

echo "Starting HealthOmics workflow run..."
echo ""

RUN_ID=$(aws omics start-run \
    --workflow-id "$WORKFLOW_ID" \
    --role-arn "$ROLE_ARN" \
    --name "$RUN_NAME" \
    --parameters "file://$TEMP_PARAMS" \
    --output-uri "$OUTPUT_URI" \
    --storage-capacity "$STORAGE_CAPACITY" \
    --log-level "$LOG_LEVEL" \
    --region "$REGION" \
    --query 'id' \
    --output text)

echo "========================================"
echo "Workflow run started successfully!"
echo "========================================"
echo "Run ID   : $RUN_ID"
echo "Run Name : $RUN_NAME"
echo ""
echo "Monitor your run with:"
echo "  aws omics get-run --id $RUN_ID --region $REGION"
echo ""
echo "AWS Console:"
echo "  https://${REGION}.console.aws.amazon.com/omics/home?region=${REGION}#/runs/${RUN_ID}"
echo "========================================"
