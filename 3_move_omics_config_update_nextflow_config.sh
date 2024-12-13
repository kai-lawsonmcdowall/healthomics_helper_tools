#!/bin/bash

# Get the directory of the current script
script_dir=$(dirname "$(readlink -f "$0")")
parent_dir=$(dirname "$script_dir")
conf_dir="$parent_dir/conf"

# Define the source and destination paths
omics_config_source="$parent_dir/omics.config"
omics_config_destination="$conf_dir/omics.config"
nextflow_config_file="$parent_dir/nextflow.config"

# Create the conf directory if it doesn't exist
if [ ! -d "$conf_dir" ]; then
    echo "Creating directory: $conf_dir"
    mkdir "$conf_dir"
fi

# Check if omics.config exists in the parent directory
if [ -f "$omics_config_source" ]; then
    echo "Moving $omics_config_source to $omics_config_destination"
    mv "$omics_config_source" "$omics_config_destination"
else
    echo "Error: $omics_config_source not found."
    exit 1
fi

if [ -f "$nextflow_config_file" ]; then
    # Check if the line already exists
    if grep -Fxq "includeConfig 'conf/omics.config'" "$nextflow_config_file"; then
        echo "The line 'includeConfig \"conf/omics.config\"' already exists in $nextflow_config_file."
    else
        # Append the line to nextflow.config
        echo "Appending includeConfig 'conf/omics.config' to $nextflow_config_file"
        echo "includeConfig 'conf/omics.config'" >> "$nextflow_config_file"
    fi
else
    echo "Error: $nextflow_config_file not found."
    exit 1
fi

echo "Script completed successfully."

