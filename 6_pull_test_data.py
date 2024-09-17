import os
import re
import requests
from pathlib import Path
from file_uploader import *


def get_file_from_config(config_file):
    """Retrieve and download file from URL specified in config file."""
    url_pattern = re.compile(
        r"'(https://raw.githubusercontent.com/nf-core/test-datasets/.*samplesheet.*)'"
    )
    with open(config_file, "r") as file:
        content = file.read()
    match = url_pattern.search(content)
    if match:
        url = match.group(1)
        filename = url.split("/")[-1]
        response = requests.get(url)
        if response.status_code == 200:
            full_path = os.path.join(
                os.getcwd(), filename
            )  # Full path of the downloaded file
            with open(full_path, "wb") as f:
                f.write(response.content)
            return full_path  # Return the full path
        else:
            print(f"Failed to download file from {url}")
    else:
        print(f"No valid URL found in {config_file}")
    return None


def prompt_and_replace(file_path, default_replacement):
    """Prompt user for strings to replace in the given file."""
    print(f"Processing file: {file_path}")
    search_string = input(
        "Enter the filepath of the samples in the samplesheet you want to change: "
    )
    replace_string = (
        input(
            f"Enter the string you want to replace it with (default (initially empty): {default_replacement}): "
        )
        or default_replacement
    )
    return search_string, replace_string


def replace_in_file(file_path, search_string, replace_string):
    """Replace all occurrences of search_string with replace_string in the given file."""
    with open(file_path, "r") as file:
        file_content = file.read()

    new_content = file_content.replace(search_string, replace_string)

    with open(file_path, "w") as file:
        file.write(new_content)


def main():
    script_dir = Path(os.getcwd()).resolve()
    parent_dir = script_dir.parent
    config_dir = parent_dir / "conf"
    test_config = config_dir / "test.config"
    test_full_config = config_dir / "test_full.config"

    default_replacement = ""
    first_file = None
    second_file = None
    search_string_1 = ""
    search_string_2 = ""
    replace_string = ""

    # Intake user inputs without modifying the samplesheets
    if test_config.exists():
        first_file = get_file_from_config(test_config)
        if first_file:
            search_string_1, default_replacement = prompt_and_replace(first_file, "")
        else:
            print(f"Failed to get the file from {test_config}")
    else:
        print(f"{test_config} not found!")

    if test_full_config.exists():
        second_file = get_file_from_config(test_full_config)
        if second_file:
            search_string_2, replace_string = prompt_and_replace(
                second_file, default_replacement
            )
        else:
            print(f"Failed to get the file from {test_full_config}")
    else:
        print(f"{test_full_config} not found!")

    # Run the copy_files functions with the user inputs
    if first_file and search_string_1:
        print(
            f'Calling copy_files with:\nfirst_file: "{first_file}"\nsearch_string_1: "{search_string_1}"\ndefault_replacement: "{default_replacement}"'
        )
        copy_files(first_file, search_string_1, default_replacement)

    if second_file and search_string_2:
        print(
            f'Calling copy_files with:\nsecond_file: "{second_file}"\nsearch_string_2: "{search_string_2}"\nreplace_string: "{replace_string}"'
        )
        copy_files(second_file, search_string_2, replace_string)

    # Replace the search strings in the files before uploading
    if first_file and search_string_1:
        replace_in_file(first_file, search_string_1, default_replacement)
        first_samplesheet_s3_path = default_replacement + os.path.basename(first_file)
        print(f"Uploading {first_file} to {first_samplesheet_s3_path}")
        upload_samplesheets(first_file, first_samplesheet_s3_path)

    if second_file and search_string_2:
        replace_in_file(second_file, search_string_2, replace_string)
        second_samplesheet_s3_path = replace_string + os.path.basename(second_file)
        print(f"Uploading {second_file} to {second_samplesheet_s3_path}")
        upload_samplesheets(second_file, second_samplesheet_s3_path)

    print("Finished executing all tasks.")


if __name__ == "__main__":
    main()
