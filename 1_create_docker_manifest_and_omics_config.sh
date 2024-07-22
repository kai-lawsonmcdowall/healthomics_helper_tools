#!/bin/bash

# Get the directory of the current script
script_dir=$(dirname "$(readlink -f "$0")")
parent_dir=$(dirname "$script_dir")

# Default filenames and paths
default_manifest_file="images_manifest.json"
public_registry_file="$script_dir/public_registry_properties.json"
config_file="$parent_dir/omics.config"
nextflow_config_file="$parent_dir/nextflow.config"
default_region="us-west-2"

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
    echo "Updating the omics config to use nextflow version 23.10.0"
    sed -i 's/nextflowVersion = '\''!>=22.04.0'\''/nextflowVersion = '\''!>=23.10.0'\''/' "$config_file"
else
    echo "Warning: $config_file not found. Skipping nextflow version update."
fi

# Move the manifest file to the parent directory
mv "$manifest_file" "$parent_dir/"
if [ $? -eq 0 ]; then
    echo "Moved $manifest_file to $parent_dir"
else
    echo "Failed to move $manifest_file to $parent_dir"
fi

# Comment out specific lines in nextflow.config if they exist
if [ -f "$nextflow_config_file" ]; then
    echo "Processing nextflow.config to comment out registry lines"

    # Use sed to comment out each registry line
    sed -i 's/^\(apptainer\.registry[[:space:]]*=[[:space:]]*'\''quay\.io'\''\)/\/\/ \1/' "$nextflow_config_file" && echo "Commenting out apptainer.registry in nextflow.config"
    sed -i 's/^\(docker\.registry[[:space:]]*=[[:space:]]*'\''quay\.io'\''\)/\/\/ \1/' "$nextflow_config_file" && echo "Commenting out docker.registry in nextflow.config"
    sed -i 's/^\(podman\.registry[[:space:]]*=[[:space:]]*'\''quay\.io'\''\)/\/\/ \1/' "$nextflow_config_file" && echo "Commenting out podman.registry in nextflow.config"
    sed -i 's/^\(singularity\.registry[[:space:]]*=[[:space:]]*'\''quay\.io'\''\)/\/\/ \1/' "$nextflow_config_file" && echo "Commenting out singularity.registry in nextflow.config"
else
    echo "Warning: $nextflow_config_file not found. Skipping registry updates."
fi