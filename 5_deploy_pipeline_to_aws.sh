#!/bin/bash

# Determine the parent directory of the script
SCRIPT_DIR=$(dirname "$(realpath "$0")")
PARENT_DIR=$(dirname "$SCRIPT_DIR")

# Default parameter template file path in the parent directory
DEFAULT_PARAM_TEMPLATE="$PARENT_DIR/parameter-template.json"
read -p "Enter the name of the parameter template file (default: $DEFAULT_PARAM_TEMPLATE): " PARAMETER_TEMPLATE
PARAMETER_TEMPLATE=${PARAMETER_TEMPLATE:-$DEFAULT_PARAM_TEMPLATE}

# Prompt for ZIP file name
read -p "Enter the name of the ZIP file (without extension): " ZIP_FILE_NAME

# Prompt for pipeline name
read -p "Enter the name of the pipeline: " PIPELINE_NAME

# Prompt for S3 path, defaulting to a specific path if not provided
DEFAULT_S3_PATH="s3://jazzpharma-sonrai-pipelines/workflows/"
read -p "Enter the S3 path to upload the ZIP file (default: $DEFAULT_S3_PATH): " S3_PATH
S3_PATH=${S3_PATH:-$DEFAULT_S3_PATH}

# Ensure the S3 path ends with a slash
[[ "${S3_PATH: -1}" != "/" ]] && S3_PATH="${S3_PATH}/"

# Create a ZIP file of the parent directory, excluding healthomics_helper_tools and the .git
ZIP_FILE="$ZIP_FILE_NAME.zip"
echo "Creating ZIP file: $ZIP_FILE from the parent directory excluding healthomics_helper_tools"
cd "$PARENT_DIR" || { echo "Failed to navigate to the parent directory"; exit 1; }
zip -r "$ZIP_FILE" . -x "./$(basename "$SCRIPT_DIR")/healthomics_helper_tools/*" || { echo "Failed to create ZIP file"; exit 1; }
cd "$SCRIPT_DIR" || { echo "Failed to return to the original directory"; exit 1; }

# Upload the ZIP file to S3
S3_FULL_PATH="${S3_PATH}${ZIP_FILE}"
echo "Uploading ZIP file to S3: $S3_FULL_PATH"
aws s3 cp "$PARENT_DIR/$ZIP_FILE" "$S3_FULL_PATH" || { echo "Failed to upload ZIP file to S3"; exit 1; }

# Create the Omics workflow
echo "Creating Omics workflow: $PIPELINE_NAME"
aws omics create-workflow \
    --name "$PIPELINE_NAME" \
    --definition-uri "$S3_FULL_PATH" \
    --parameter-template "file://$PARAMETER_TEMPLATE" \
    --engine NEXTFLOW || { echo "Failed to create Omics workflow"; exit 1; }

echo "Workflow created successfully."

# Add "healthomics_helper_tools" to .gitignore in the parent directory if it doesn't already exist
GITIGNORE_FILE="$PARENT_DIR/.gitignore"
if ! grep -qx "healthomics_helper_tools" "$GITIGNORE_FILE"; then
    echo "healthomics_helper_tools" >> "$GITIGNORE_FILE"
    echo "healthomics_helper_tools added to the nf-core .gitignore"
else
    echo "healthomics_helper_tools already exists in the .gitignore"
fi
