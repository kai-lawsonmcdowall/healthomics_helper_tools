#!/bin/bash

# Prompt for ZIP file name
read -p "Enter the name of the ZIP file (without extension): " ZIP_FILE_NAME

# Prompt for pipeline name
read -p "Enter the name of the pipeline: " PIPELINE_NAME

# Default parameter template file path
DEFAULT_PARAM_TEMPLATE="parameter_template.json"
read -p "Enter the name of the parameter template file (default: $DEFAULT_PARAM_TEMPLATE): " PARAMETER_TEMPLATE
PARAMETER_TEMPLATE=${PARAMETER_TEMPLATE:-$DEFAULT_PARAM_TEMPLATE}

# Prompt for S3 path, defaulting to a specific path if not provided
DEFAULT_S3_PATH="s3://jazzpharma-sonrai-pipelines/workflows/"
read -p "Enter the S3 path to upload the ZIP file (default: $DEFAULT_S3_PATH): " S3_PATH
S3_PATH=${S3_PATH:-$DEFAULT_S3_PATH}

# Ensure the S3 path ends with a slash
[[ "${S3_PATH: -1}" != "/" ]] && S3_PATH="${S3_PATH}/"

# Determine the parent directory of the current directory
CURRENT_DIR=$(pwd)
PARENT_DIR=$(dirname "$CURRENT_DIR")

# Create a ZIP file of the parent directory, excluding healthomics_helper_tools and the .git
ZIP_FILE="$ZIP_FILE_NAME.zip"
echo "Creating ZIP file: $ZIP_FILE from the parent directory excluding healthomics_helper_tools"
cd "$PARENT_DIR" || { echo "Failed to navigate to the parent directory"; exit 1; }
zip -r "$ZIP_FILE" . -x "./$(basename "$CURRENT_DIR")/healthomics_helper_tools/*" || { echo "Failed to create ZIP file"; exit 1; }
cd "$CURRENT_DIR" || { echo "Failed to return to the original directory"; exit 1; }

# Upload the ZIP file to S3
S3_FULL_PATH="${S3_PATH}${ZIP_FILE}"
echo "Uploading ZIP file to S3: $S3_FULL_PATH"
aws s3 cp "$PARENT_DIR/$ZIP_FILE" "$S3_FULL_PATH" || { echo "Failed to upload ZIP file to S3"; exit 1; }

# Create the Omics workflow
echo "Creating Omics workflow: $PIPELINE_NAME"
aws omics create-workflow \
    --name "$PIPELINE_NAME" \
    --definition-uri "$S3_FULL_PATH" \
    --parameter-template "file://$PARENT_DIR/$PARAMETER_TEMPLATE" \
    --engine NEXTFLOW || { echo "Failed to create Omics workflow"; exit 1; }

echo "Workflow created successfully."
