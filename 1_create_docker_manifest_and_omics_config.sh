#!/bin/bash

# Get the directory of the current script
script_dir=$(dirname "$(readlink -f "$0")")
parent_dir=$(dirname "$script_dir")

# Default filenames and paths
default_manifest_file="container_image_manifest.json"
public_registry_file="$script_dir/public_registry_properties.json"
config_file="$parent_dir/omics.config"
nextflow_config_file="$parent_dir/nextflow.config"
default_region="eu-west-2"

# Prompt the user for the manifest file name
read -p "Enter the name for the output manifest file (default: $default_manifest_file): " manifest_file
manifest_file=${manifest_file:-$default_manifest_file}

# Prompt the user for the region
read -p "Enter the AWS region (default: $default_region): " region
region=${region:-$default_region}

echo "inspect_nf.py in $script_dir/inspect_nf.py"
echo "docker manifest file will be $manifest_file"
echo "the public registry file is $public_registry_file"
echo "the omics.config is $config_file"

# Run the Python script with the specified and default paths
python3 "$script_dir/inspect_nf.py" \
    --output-manifest-file "$manifest_file" \
    -n "$public_registry_file" \
    --output-config-file "$config_file" \
    --region "$region" \
    $parent_dir

# Check if the omics.config file exists and update the nextflowVersion
if [ -f "$config_file" ]; then
    echo "Updating the omics.config to use nextflow version 23.10.0"
    sed -i 's/nextflowVersion = '\''!>=22.04.0'\''/nextflowVersion = '\''!>=23.10.0'\''/' "$config_file"

    # Replace container registry in omics.config
    echo "Replacing container registry in omics.config"
    sed -i "s|container = 'biocontainers/|container = 'quay/biocontainers/|g" "$config_file"

    # Replace specific container registry reference
    echo "Replacing nf-core/ubuntu:20.04 container in omics.config"
    sed -i "s|container = 'nf-core/ubuntu:20.04'|container = 'quay/nf-core/ubuntu:20.04'|g" "$config_file"
else
    echo "Warning: $config_file not found. Skipping nextflow version update and container registry replacement."
fi

# Move the manifest file to the parent directory
mv "$manifest_file" "$parent_dir/"
if [ $? -eq 0 ]; then
    echo "Moved $manifest_file to $parent_dir"
else
    echo "Failed to move $manifest_file to $parent_dir"
fi

# Modify the container_image_manifest.json to update container registry references
if [ -f "$parent_dir/$manifest_file" ]; then
    echo "Replacing container registry in container_image_manifest.json"
    sed -i "s|biocontainers/|quay/biocontainers/|g" "$parent_dir/$manifest_file"

    # Replace specific container registry reference
    echo "Replacing nf-core/ubuntu:20.04 in container_image_manifest.json"
    sed -i "s|nf-core/ubuntu:20.04|quay/nf-core/ubuntu:20.04|g" "$parent_dir/$manifest_file"

    # Replace redundant quay.io/quay.io/ with quay/
    echo "Replacing redundant quay.io/quay.io/ with quay/ in container_image_manifest.json"
    sed -i "s|quay.io/quay.io/|quay/|g" "$parent_dir/$manifest_file"

    # Replace "ubuntu:20.04" with "quay/nf-core/ubuntu:20.04"
    echo "Replacing ubuntu:20.04 with quay/nf-core/ubuntu:20.04 in container_image_manifest.json"
    sed -i "s|ubuntu:20.04|quay/nf-core/ubuntu:20.04|g" "$parent_dir/$manifest_file"
else
    echo "Warning: $manifest_file not found in $parent_dir. Skipping container registry replacement."
fi

# Comment out specific lines in nextflow.config if they exist
if [ -f "$nextflow_config_file" ]; then
    echo "Processing nextflow.config to comment out registry lines"

    # Use sed to comment out each registry line
    sed -i 's/^\(apptainer\.registry[[:space:]]*=[[:space:]]*'\''quay'\''\)/\/\/ \1/' "$nextflow_config_file" && echo "Commenting out apptainer.registry in nextflow.config"
    sed -i 's/^\(docker\.registry[[:space:]]*=[[:space:]]*'\''quay'\''\)/\/\/ \1/' "$nextflow_config_file" && echo "Commenting out docker.registry in nextflow.config"
    sed -i 's/^\(podman\.registry[[:space:]]*=[[:space:]]*'\''quay'\''\)/\/\/ \1/' "$nextflow_config_file" && echo "Commenting out podman.registry in nextflow.config"
    sed -i 's/^\(singularity\.registry[[:space:]]*=[[:space:]]*'\''quay'\''\)/\/\/ \1/' "$nextflow_config_file" && echo "Commenting out singularity.registry in nextflow.config"
else
    echo "Warning: $nextflow_config_file not found. Skipping registry updates."
fi

