import boto3
import requests
import pandas as pd
import os
from urllib.parse import urlparse


def parse_s3_url(s3_url):
    """Parse S3 URL to bucket and key."""
    parsed_url = urlparse(s3_url)
    bucket = parsed_url.netloc
    key = parsed_url.path.lstrip("/")
    return bucket, key


def download_file(url, local_path):
    """Download file from HTTP URL."""
    response = requests.get(url, stream=True)
    response.raise_for_status()  # Raise an exception for HTTP errors
    with open(local_path, "wb") as file:
        for chunk in response.iter_content(chunk_size=8192):
            file.write(chunk)


def upload_to_s3(local_file, bucket_name, s3_path):
    """Upload local file to S3."""
    s3 = boto3.client("s3")
    s3.upload_file(local_file, bucket_name, s3_path)


def copy_s3_file(src_url, dst_url):
    """Copy file from one S3 location to another."""
    s3 = boto3.client("s3")
    src_bucket, src_key = parse_s3_url(src_url)
    dst_bucket, dst_key = parse_s3_url(dst_url)

    copy_source = {"Bucket": src_bucket, "Key": src_key}
    s3.copy(CopySource=copy_source, Bucket=dst_bucket, Key=dst_key)
    print(f"Copied {src_url} to {dst_url}")


def copy_files(samplesheet_path, string1, string2):
    # Load the samplesheet into a DataFrame
    df = pd.read_csv(samplesheet_path)

    # Collect all valid file URLs into a list
    file_urls = []

    for col in ["fastq_1", "fastq_2"]:
        col_files = df[col].dropna().tolist()  # Drop NaN values and convert to list
        file_urls.extend(
            [file for file in col_files if file.strip()]
        )  # Append only non-empty strings

    # Function to determine if a URL is an HTTP URL
    def is_http_url(url):
        return isinstance(url, str) and (
            url.startswith("http://") or url.startswith("https://")
        )

    # Function to process file URLs
    def process_file(file_url, string1, string2):
        if file_url.startswith(string1):
            # Destination path
            dst_path = file_url.replace(string1, string2, 1)

            if is_http_url(file_url):
                # Download the file locally
                local_filename = os.path.basename(urlparse(file_url).path)
                download_file(file_url, local_filename)

                # Upload the file to S3
                dst_bucket, dst_key = parse_s3_url(dst_path)
                upload_to_s3(local_filename, dst_bucket, dst_key)

                # Remove the local file
                os.remove(local_filename)
                print(f"Uploaded {local_filename} to s3://{dst_bucket}/{dst_key}")
            else:
                # Copy the file within S3
                copy_s3_file(file_url, dst_path)

    # Process each file in the list
    for file_url in file_urls:
        process_file(file_url, string1, string2)


def upload_samplesheets(local_file_path, s3_url):
    """
    Upload a local file to an S3 bucket.

    :param local_file_path: The path to the local file to be uploaded.
    :param s3_url: The S3 URL where the file should be uploaded (e.g., s3://bucket-name/path/to/file).
    """
    # Parse the S3 URL to get the bucket name and key
    parsed_url = urlparse(s3_url)
    bucket_name = parsed_url.netloc
    s3_key = parsed_url.path.lstrip("/")  # Remove leading slash

    # Initialize the S3 client
    s3_client = boto3.client("s3")

    try:
        # Upload the file
        s3_client.upload_file(local_file_path, bucket_name, s3_key)
        print(f"File uploaded successfully to {s3_url}")
    except Exception as e:
        print(f"Error uploading file: {e}")
