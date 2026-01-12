#!/bin/bash
set -euo pipefail

# ---------------------------------------
# Paths
# ---------------------------------------
script_dir=$(dirname "$(readlink -f "$0")")
parent_dir=$(dirname "$script_dir")

default_manifest_file="container_image_manifest.json"
public_registry_file="$script_dir/public_registry_properties.json"
config_file="$parent_dir/omics.config"
nextflow_config_file="$parent_dir/nextflow.config"
default_region="eu-west-2"

# ---------------------------------------
# User input
# ---------------------------------------
read -p "Enter the name for the output manifest file (default: $default_manifest_file): " manifest_file
manifest_file=${manifest_file:-$default_manifest_file}

read -p "Enter the AWS region (default: $default_region): " region
region=${region:-$default_region}

read -p "Enter a container substitutions JSON file (optional, default: none): " substitutions_file
substitutions_file=${substitutions_file:-none}

echo "inspect_nf.py       : $script_dir/inspect_nf.py"
echo "Manifest file       : $manifest_file"
echo "Registry properties : $public_registry_file"
echo "Omics config        : $config_file"
echo "Substitutions file  : $substitutions_file"

# ---------------------------------------
# Build inspect_nf.py command
# ---------------------------------------
cmd=(python "$script_dir/inspect_nf.py"
    --output-manifest-file "$manifest_file"
    -n "$public_registry_file"
    --output-config-file "$config_file"
    --region "$region"
    "$parent_dir"
)

# Add substitutions argument only if file is provided
if [[ "$substitutions_file" != "none" ]]; then
    cmd+=(--container-substitutions "$substitutions_file")
fi

# ---------------------------------------
# Run inspect_nf.py
# ---------------------------------------
echo "Running inspect_nf.py..."
"${cmd[@]}"

# ---------------------------------------
# Update Nextflow minimum version in omics.config
# ---------------------------------------
if [[ -f "$config_file" ]]; then
    echo "Updating omics.config to require Nextflow >= 24.10.8"
    sed -i \
        "s/nextflowVersion = '!*>=22\.04\.0'/nextflowVersion = '!>=24.10.8'/" \
        "$config_file"
else
    echo "WARNING: $config_file not found! Skipping update."
fi

# ---------------------------------------
# Move manifest file to project root
# ---------------------------------------
mv "$manifest_file" "$parent_dir/"
echo "Moved manifest to $parent_dir"

# ---------------------------------------
# Comment out registry declarations in nextflow.config
# ---------------------------------------
if [[ -f "$nextflow_config_file" ]]; then
    echo "Commenting out registry lines in nextflow.config"
    sed -i "s/^\(apptainer\.registry\s*=\s*'.*'\)/\/\/ \1/" "$nextflow_config_file"
    sed -i "s/^\(docker\.registry\s*=\s*'.*'\)/\/\/ \1/" "$nextflow_config_file"
    sed -i "s/^\(podman\.registry\s*=\s*'.*'\)/\/\/ \1/" "$nextflow_config_file"
    sed -i "s/^\(singularity\.registry\s*=\s*'.*'\)/\/\/ \1/" "$nextflow_config_file"
    sed -i "s/^\(charliecloud\.registry\s*=\s*'.*'\)/\/\/ \1/" "$nextflow_config_file"
    
    
    
else
    echo "WARNING: $nextflow_config_file not found!"
fi

echo "Done."
