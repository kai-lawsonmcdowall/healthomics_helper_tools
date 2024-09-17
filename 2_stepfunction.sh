#!/bin/bash

# Get the directory of the current script
script_dir=$(dirname "$(readlink -f "$0")")
parent_dir=$(dirname "$script_dir")
omics_config_file="$parent_dir/omics.config"
default_input_file="$parent_dir/container_image_manifest.json"

# Extract the AWS account ID and region from omics.config
if [ -f "$omics_config_file" ]; then
    # Extract the ecr_registry value
    ecr_registry=$(grep -Po "(?<=ecr_registry = ').*(?=')" "$omics_config_file")
    if [[ $ecr_registry =~ ^([0-9]+)\.dkr\.ecr\.([^.]+)\.amazonaws\.com$ ]]; then
        default_account_id="${BASH_REMATCH[1]}"
        default_region="${BASH_REMATCH[2]}"
    else
        echo "Error: Could not parse ecr_registry value from $omics_config_file."
        exit 1
    fi
else
    echo "Error: $omics_config_file not found."
    exit 1
fi

# Verify that default_account_id and default_region are extracted
if [ -z "$default_account_id" ] || [ -z "$default_region" ]; then
    echo "Error: Could not parse account ID or region from $omics_config_file."
    exit 1
fi

# Prompt the user for the input file name, defaulting to the parent directory
read -p "Enter the input file for the Step Functions execution (default: container_image_manifest.json): " input_file_name
input_file_name=${input_file_name:-"container_image_manifest.json"}
input_file="$parent_dir/$input_file_name"

# Check if the input file exists
if [ ! -f "$input_file" ]; then
    echo "Error: $input_file not found in the parent directory."
    exit 1
fi

# Prompt the user for the account ID, defaulting to the extracted value
read -p "Enter the AWS account ID (default: $default_account_id): " account_id
account_id=${account_id:-$default_account_id}

# Prompt the user for the region, defaulting to the extracted value
read -p "Enter the AWS region (default: $default_region): " region
region=${region:-$default_region}

# Construct the ARN for the Step Functions state machine
state_machine_arn="arn:aws:states:$region:$account_id:stateMachine:omx-container-puller"

# Run the AWS Step Functions execution command
aws stepfunctions start-execution \
    --state-machine-arn "$state_machine_arn" \
    --input "file://$input_file"
