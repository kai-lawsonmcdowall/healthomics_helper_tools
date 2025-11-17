import json
from pathlib import Path

# Set default paths
script_dir = Path(__file__).parent
default_input_path = script_dir.parent / "nextflow_schema.json"
default_output_path = script_dir.parent / "parameter-template.json"

# Parameters to exclude (set for faster lookups)
EXCLUDE_PARAMETERS = {
    "outdir",
    "email",
    "custom_config_version",
    "custom_config_base",
    "config_profile_name",
    "config_profile_description",
    "config_profile_contact",
    "config_profile_url",
    "max_cpus",
    "max_memory",
    "max_time",
    "max_multiqc_email_size",
    "help",
    "version",
    "publish_dir_mode",
    "email_on_fail",
    "plaintext_email",
    "monochrome_logs",
    "hook_url",
    "validate_params",
    "validationShowHiddenParams",
    "validationFailUnrecognisedParams",
    "validationLenientMode",
    "pipelines_testdata_base_path",
    "genome",
    "igenomes_base",
    "igenomes_ignore",
}

# Get input path with default handling
input_path = input(
    f"Enter path to nextflow_schema.json [default: {default_input_path}]: "
).strip()
input_path = Path(input_path) if input_path else default_input_path

# Read and parse the input JSON file
with open(input_path, "r") as f:
    schema = json.load(f)

processed_params = {}

# Iterate through each definition in the $defs section
for def_name, def_content in schema.get("$defs", {}).items():
    if isinstance(def_content, dict) and "properties" in def_content:
        required_params = def_content.get("required", [])
        properties = def_content["properties"]

        # Process each parameter in the properties
        for param, details in properties.items():
            # Skip excluded and deprecated parameters
            if param in EXCLUDE_PARAMETERS:
                continue
            if details.get("deprecated", False):
                continue

            description = details.get("description", "")
            optional = param not in required_params

            processed_params[param] = {
                "description": description.strip(),
                "optional": optional,
            }

# Write to default output path
with open(default_output_path, "w") as f:
    json.dump(processed_params, f, indent=4)

print(f"\nProcessed {len(processed_params)} parameters")
print(f"Excluded {len(EXCLUDE_PARAMETERS)} specified parameters")
print(f"Output saved to: {default_output_path}")
