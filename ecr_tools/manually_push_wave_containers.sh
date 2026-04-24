#!/bin/bash
set -euo pipefail

# Configuration
DEFAULT_REGION="eu-west-2"
DEFAULT_ACCOUNT_ID=""

# Container images to migrate
CONTAINERS=(
    "community.wave.seqera.io/library/coreutils:9.5--ae99c88a9b28c264"
    "community.wave.seqera.io/library/coreutils_grep_gzip_lbzip2_pruned:838ba80435a629f8"
    "community.wave.seqera.io/library/cutadapt_trim-galore_pigz:a98edd405b34582d"
    "community.wave.seqera.io/library/fastp:1.0.1--c8b87fe62dcc103c"
    "community.wave.seqera.io/library/htslib_samtools_star_gawk:311d422a50e6d829"
    "community.wave.seqera.io/library/multiqc:1.32--d58f60e4deb769bf"
    "community.wave.seqera.io/library/sortmerna:4.3.7--b730cad73fc42b8e"
)

# ECR policy document for Omics access
ECR_POLICY='{
  "Version": "2012-10-17",
  "Statement": [{
    "Sid": "omics workflow access",
    "Effect": "Allow",
    "Principal": {
      "Service": "omics.amazonaws.com"
    },
    "Action": [
      "ecr:GetDownloadUrlForLayer",
      "ecr:BatchGetImage",
      "ecr:BatchCheckLayerAvailability"
    ]
  }]
}'

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Helper functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Get AWS account ID and region
log_info "Getting AWS account information..."
read -p "Enter AWS region (default: $DEFAULT_REGION): " REGION
REGION=${REGION:-$DEFAULT_REGION}

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text 2>/dev/null || echo "")
if [ -z "$ACCOUNT_ID" ]; then
    log_error "Could not determine AWS account ID. Please check your AWS credentials."
    exit 1
fi

log_info "Using AWS Account: $ACCOUNT_ID"
log_info "Using Region: $REGION"

# Login to ECR
log_info "Logging into AWS ECR..."
aws ecr get-login-password --region "$REGION" | docker login --username AWS --password-stdin "$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com"

# Process each container
for CONTAINER in "${CONTAINERS[@]}"; do
    echo ""
    log_info "=========================================="
    log_info "Processing: $CONTAINER"
    log_info "=========================================="
    
    # Parse the container image
    # Format: community.wave.seqera.io/library/package:tag
    if [[ $CONTAINER =~ ^community\.wave\.seqera\.io/(.+):(.+)$ ]]; then
        PATH_WITH_NAME="${BASH_REMATCH[1]}"  # library/package
        TAG="${BASH_REMATCH[2]}"              # tag
        
        # Create ECR repository name by replacing community.wave.seqera.io with wave
        ECR_REPO="wave/$PATH_WITH_NAME"
        
        log_info "Source: $CONTAINER"
        log_info "Target ECR Repo: $ECR_REPO"
        log_info "Tag: $TAG"
    else
        log_error "Could not parse container image: $CONTAINER"
        continue
    fi
    
    # Pull the container from Wave
    log_info "Pulling container from Wave..."
    if ! docker pull "$CONTAINER"; then
        log_error "Failed to pull $CONTAINER"
        continue
    fi
    
    # Create ECR repository if it doesn't exist
    log_info "Creating ECR repository: $ECR_REPO"
    if aws ecr describe-repositories --repository-names "$ECR_REPO" --region "$REGION" >/dev/null 2>&1; then
        log_warn "Repository $ECR_REPO already exists"
    else
        if aws ecr create-repository --repository-name "$ECR_REPO" --region "$REGION" >/dev/null 2>&1; then
            log_info "Created repository: $ECR_REPO"
        else
            log_error "Failed to create repository: $ECR_REPO"
            continue
        fi
    fi
    
    # Set repository policy for Omics access
    log_info "Setting repository policy for Omics access..."
    if aws ecr set-repository-policy \
        --repository-name "$ECR_REPO" \
        --policy-text "$ECR_POLICY" \
        --region "$REGION" >/dev/null 2>&1; then
        log_info "Policy set successfully"
    else
        log_warn "Failed to set policy (may already exist or have permissions issue)"
    fi
    
    # Tag the image for ECR
    ECR_IMAGE="$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$ECR_REPO:$TAG"
    log_info "Tagging image as: $ECR_IMAGE"
    docker tag "$CONTAINER" "$ECR_IMAGE"
    
    # Push to ECR
    log_info "Pushing to ECR..."
    if docker push "$ECR_IMAGE"; then
        log_info "Successfully pushed: $ECR_IMAGE"
    else
        log_error "Failed to push $ECR_IMAGE"
        continue
    fi
    
    # Clean up local images to save space
    log_info "Cleaning up local images..."
    docker rmi "$CONTAINER" "$ECR_IMAGE" 2>/dev/null || true
    
    log_info "✓ Completed: $ECR_REPO:$TAG"
done

echo ""
log_info "=========================================="
log_info "Migration complete!"
log_info "=========================================="
log_info "All containers have been migrated to ECR in region: $REGION"
log_info "ECR registry: $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com"