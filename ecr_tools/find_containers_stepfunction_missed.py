#!/usr/bin/env python3
"""
Script to check if container images specified in omics.config exist in AWS ECR.
"""

import re
import sys
import argparse
import boto3
from pathlib import Path
from botocore.exceptions import ClientError


def parse_omics_config(config_path):
    """
    Parse the omics.config file and extract container specifications.

    Args:
        config_path: Path to the omics.config file

    Returns:
        tuple: (ecr_registry, list of container specs)
    """
    with open(config_path, "r") as f:
        content = f.read()

    # Extract ECR registry
    ecr_match = re.search(r"ecr_registry\s*=\s*'([^']+)'", content)
    ecr_registry = ecr_match.group(1) if ecr_match else None

    # Extract all container specifications
    container_pattern = r"container\s*=\s*'([^']+)'"
    containers = re.findall(container_pattern, content)

    return ecr_registry, containers


def parse_container_spec(container_spec):
    """
    Parse a container specification into registry, repository, and tag.

    Args:
        container_spec: Container string (e.g., 'biocontainers/kallisto:0.51.1--heb0cbe2_0')

    Returns:
        tuple: (repository, tag) or None if not parseable
    """
    # Handle different container spec formats
    if ":" in container_spec:
        repo_tag = container_spec.split(":")
        repository = repo_tag[0]
        tag = repo_tag[1] if len(repo_tag) > 1 else "latest"
        return repository, tag
    else:
        return container_spec, "latest"


def check_ecr_image_exists(ecr_client, registry, repository, tag):
    """
    Check if an image with a specific tag exists in an ECR repository.

    Args:
        ecr_client: boto3 ECR client
        registry: ECR registry URL
        repository: Repository name
        tag: Image tag

    Returns:
        bool: True if image exists, False otherwise
    """
    try:
        response = ecr_client.describe_images(
            repositoryName=repository, imageIds=[{"imageTag": tag}]
        )
        return len(response["imageDetails"]) > 0
    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        if error_code == "RepositoryNotFoundException":
            return False
        elif error_code == "ImageNotFoundException":
            return False
        else:
            print(f"Error checking {repository}:{tag}: {e}")
            return False


def main():
    parser = argparse.ArgumentParser(
        description="Check if containers from omics.config exist in ECR"
    )
    parser.add_argument(
        "--config",
        type=str,
        default="../conf/omics.config",
        help="Path to omics.config file (default: ../conf/omics.config)",
    )
    parser.add_argument(
        "--region",
        type=str,
        default="eu-west-2",
        help="AWS region (default: eu-west-2)",
    )

    args = parser.parse_args()

    # Resolve config path
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Error: Config file not found at {config_path}")
        sys.exit(1)

    print(f"Reading config from: {config_path}")

    # Parse the config file
    ecr_registry, containers = parse_omics_config(config_path)

    if not ecr_registry:
        print("Error: Could not find ecr_registry in config file")
        sys.exit(1)

    print(f"ECR Registry: {ecr_registry}")
    print(f"Found {len(containers)} container specifications\n")

    # Extract region from registry if not provided
    if "ecr" in ecr_registry:
        region_match = re.search(r"\.([a-z0-9-]+)\.amazonaws\.com", ecr_registry)
        if region_match:
            region = region_match.group(1)
            print(f"Detected AWS region: {region}\n")
    else:
        region = args.region

    # Initialize ECR client
    ecr_client = boto3.client("ecr", region_name=region)

    # Check each container
    missing_containers = []
    existing_containers = []

    print("Checking containers in ECR...\n")

    for container in set(containers):  # Use set to avoid duplicates
        repository, tag = parse_container_spec(container)

        print(f"Checking: {repository}:{tag}...", end=" ")

        exists = check_ecr_image_exists(ecr_client, ecr_registry, repository, tag)

        if exists:
            print("✓ EXISTS")
            existing_containers.append(container)
        else:
            print("✗ MISSING")
            missing_containers.append(container)

    # Print summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Total containers checked: {len(set(containers))}")
    print(f"Existing: {len(existing_containers)}")
    print(f"Missing: {len(missing_containers)}")

    if missing_containers:
        print("\n" + "=" * 70)
        print("MISSING CONTAINERS:")
        print("=" * 70)
        for container in missing_containers:
            print(f"  - {container}")
        sys.exit(1)
    else:
        print("\n✓ All containers exist in ECR!")
        sys.exit(0)


if __name__ == "__main__":
    main()
