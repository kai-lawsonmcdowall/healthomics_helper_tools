import os
import re
import json
import requests
from bs4 import BeautifulSoup


def extract_substrings(input_string, keyword):
    """
    Extracts substrings enclosed between <code>--{keyword}</code> and <code>--</code> tags
    from the given input_string. These substrings and their contents are unique to each nf-core parameter listed on the nf-core
    page, therefore, we can use them to determine if a parameter is required or optional.

    Args:
        input_string (str): The HTML content of the workflow nf-core params page, as a giant string
        keyword (str): The keyword to identify substrings between <code>--{keyword}</code> tags.

    Returns:
        list: A list of extracted substrings, each of which will contain the optional or required statement of each parameter
        listed in the nf-core workflow params page.
    """
    substrings = []
    start_pattern = re.escape(f"<code>--{keyword}</code>")
    end_pattern = re.escape("<code>--")
    pattern = re.compile(r"{}(.*?){}".format(start_pattern, end_pattern), re.DOTALL)
    matches = pattern.findall(input_string)
    for match in matches:
        substrings.append(match.strip())
    return substrings


def process_json(input_string, json_data):
    """
    Process the input string to update the 'optional' status in the eventual parameter-description.json
    based on the presence of specific substrings associated with each keyword. This function modifies the
    'optional' status in the 'json_data' dictionary in place.

    Args:
        input_string (str): The input string to search for substrings.
        json_data (dict): A dictionary containing keyword-substring mappings.

    Returns:
        None
    """
    for keyword in json_data.keys():
        print(f"Getting required status for {keyword}")
        substrings = extract_substrings(input_string, keyword)
        for idx, substring in enumerate(substrings, 1):
            if (
                'class="badge text-bg-warning mb-1" data-svelte-h="svelte-1t99nzu">required</span>'
                in substring
            ):
                json_data[keyword]["optional"] = False
            else:
                json_data[keyword]["optional"] = True


def create_parameters_json(nextflow_schema, nf_core_params_url, json_output_path):
    """
    Create a JSON file containing parameters extracted from a Nextflow schema and nf-core parameters URL.

    Parameters:
        nextflow_schema (str): Path to the Nextflow schema JSON file.
        nf_core_params_url (str): URL of the nf-core parameters page of the workflow.
        json_output_path (str): Path to write the output JSON file containing extracted parameters.

    Returns:
        None

    This function loads the original Nextflow schema JSON file and fetches the HTML content of the nf-core parameters
    page. It extracts parameter titles and descriptions from the Nextflow schema and determines if each parameter is
    required or optional based on the HTML content. The extracted data is written to a new JSON file.
    """

    # Set default nextflow_schema path to nextflow_schema.json in parent directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(script_dir)
    default_nextflow_schema = os.path.join(parent_dir, "nextflow_schema.json")

    # Use default path if nextflow_schema is not provided
    if not nextflow_schema:
        nextflow_schema = default_nextflow_schema

    # Load the original JSON file
    with open(nextflow_schema, "r") as f:
        original_data = json.load(f)

    # Fetch the HTML content of the workflow's nf-core params page
    response = requests.get(nf_core_params_url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, "html.parser")
        html_string = str(soup)

    # Initialize an empty dictionary to store extracted data
    extracted_data = {}

    # Iterate over each definition in the Nextflow Schema
    for definition_key, definition_value in original_data.get(
        "definitions", {}
    ).items():
        # Check if the definition has properties
        if "properties" in definition_value:
            # Iterate over each property in the definition
            for property_key, property_value in definition_value["properties"].items():
                # Extract title and description
                title = property_key
                description = property_value.get("description", "")

                # Set optional field to an empty string
                extracted_data[title] = {"optional": "", "description": description}

    # Determine if the parameter is required or optional
    process_json(html_string, extracted_data)

    # Convert "optional": "" to "optional": true if empty
    for key, value in extracted_data.items():
        if value["optional"] == "":
            extracted_data[key]["optional"] = True

    # List of parameters to exclude from the final JSON
    exclude_parameters = [
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
    ]

    # Filter out excluded parameters
    final_data = {
        key: value
        for key, value in extracted_data.items()
        if key not in exclude_parameters
    }

    # Use default output path if json_output_path is not provided
    if not json_output_path:
        json_output_path = os.path.join(parent_dir, "parameter-template.json")

    # Write the filtered data to a new JSON file
    with open(json_output_path, "w") as f:
        json.dump(final_data, f, indent=4)

    print(
        "This is the penultimate step. Prior to deploying the workflow, ensure that only absolutely necessary parameters in the parameters template JSON are set to optional as false. If they are set to optional false and not provided, they will break healthomics."
    )


def main():
    print("Please provide the required inputs:")

    nextflow_schema = input(
        f"Path to the Nextflow schema JSON file (default: nextflow_schema.py in parent directory): "
    ).strip()
    nf_core_params_url = input(
        "URL of the nf-core parameters page of the workflow: "
    ).strip()
    json_output_path = input(
        "Path to write the output JSON file containing extracted parameters (default: parent directory of script with filename parameter-template.json): "
    ).strip()

    create_parameters_json(nextflow_schema, nf_core_params_url, json_output_path)


if __name__ == "__main__":
    main()
