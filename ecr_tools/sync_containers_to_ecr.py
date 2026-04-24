#!/usr/bin/env python3
"""
Script to sync container images from omics.config to ECR.
Checks local Docker images, pulls missing ones, tags them, and pushes to ECR.
"""

import re
import sys
import json
import argparse
import subprocess
import boto3
from pathlib import Path
from botocore.exceptions import ClientError


def parse_omics_config(config_path):
    """Parse omics.config and extract ECR registry and containers."""
    with open(config_path, "r") as f:
        content = f.read()

    ecr_match = re.search(r"ecr_registry\s*=\s*'([^']+)'", content)
    ecr_registry = ecr_match.group(1) if ecr_match else None

    container_pattern = r"container\s*=\s*'([^']+)'"
    containers = re.findall(container_pattern, content)

    return ecr_registry, list(set(containers))  # Remove duplicates


def load_manifest(manifest_path):
    """Load container image manifest JSON."""
    with open(manifest_path, "r") as f:
        data = json.load(f)
    return data["manifest"]


def get_local_docker_images():
    """Get list of local Docker images."""
    try:
        result = subprocess.run(
            ["docker", "images", "--format", "{{.Repository}}:{{.Tag}}"],
            capture_output=True,
            text=True,
            check=True,
        )
        return [img.strip() for img in result.stdout.split("\n") if img.strip()]
    except subprocess.CalledProcessError as e:
        print(f"Error getting Docker images: {e}")
        return []


def strip_known_registry_prefix(image_spec):
    """
    Strip known registry prefixes from image spec.

    Known prefixes:
    - community.wave.seqera.io/library/
    - quay.io/
    - docker.io/

    E.g., 'quay.io/biocontainers/fq:0.12.0' -> 'biocontainers/fq:0.12.0'
    """
    known_prefixes = [
        "community.wave.seqera.io/library/",
        "quay.io/",
        "docker.io/",
    ]

    for prefix in known_prefixes:
        if image_spec.startswith(prefix):
            return image_spec[len(prefix) :]

    return image_spec


def extract_image_suffix(image_spec):
    """
    Extract the part after the first '/' for comparison with manifest.
    E.g., 'biocontainers/ribotish:0.2.7' -> 'ribotish:0.2.7'
         'quay.io/biocontainers/ribotish:0.2.7' -> 'biocontainers/ribotish:0.2.7'
    """
    if "/" in image_spec:
        parts = image_spec.split("/", 1)
        return parts[1]
    return image_spec


def find_matching_local_image(target_spec, local_images):
    """
    Find a local image that matches the target_spec after stripping known registry prefixes.
    Returns the full local image name if found, None otherwise.

    If multiple matches found, prefer the one with fewer slashes (shorter prefix).

    E.g., target: 'biocontainers/fq:0.12.0--h9ee0642_0'
          Local: 'quay.io/biocontainers/fq:0.12.0--h9ee0642_0'
          After stripping: 'biocontainers/fq:0.12.0--h9ee0642_0'
          Match! Returns: 'quay.io/biocontainers/fq:0.12.0--h9ee0642_0'
    """
    matches = []

    for local_img in local_images:
        # Strip known registry prefix from local image
        stripped_local = strip_known_registry_prefix(local_img)

        # Compare with target spec
        if stripped_local == target_spec:
            matches.append(local_img)

    if not matches:
        return None

    # If multiple matches, prefer the one with fewer path components (shorter prefix)
    # This will prefer 'biocontainers/samtools:tag' over 'quay.io/biocontainers/samtools:tag'
    matches.sort(key=lambda x: x.count("/"))
    return matches[0]


def match_manifest_image(target_spec, manifest_images):
    """
    Find matching image in manifest by comparing after first '/'.
    """
    target_suffix = extract_image_suffix(target_spec)

    for manifest_img in manifest_images:
        manifest_suffix = extract_image_suffix(manifest_img)
        if manifest_suffix == target_suffix:
            return manifest_img
    return None


def pull_with_registry_fallback(image_name):
    """
    Attempt to pull image.
    If it fails and image starts with known namespaces,
    retry with quay.io prefix.

    Supported fallbacks:
      - biocontainers/*  -> quay.io/biocontainers/*
      - nf-core/*        -> quay.io/nf-core/*
    """
    print(f"  Pulling {image_name}...")
    try:
        subprocess.run(
            ["docker", "pull", image_name],
            check=True,
            capture_output=True,
        )
        print("  ✓ Pulled successfully")
        return image_name
    except subprocess.CalledProcessError:
        fallback_prefixes = ("biocontainers/", "nf-core/")

        for prefix in fallback_prefixes:
            if image_name.startswith(prefix):
                fallback_image = f"quay.io/{image_name}"
                print(f"  ⚠ Pull failed, retrying with {fallback_image}...")
                try:
                    subprocess.run(
                        ["docker", "pull", fallback_image],
                        check=True,
                        capture_output=True,
                    )
                    print("  ✓ Pulled successfully via quay.io")
                    return fallback_image
                except subprocess.CalledProcessError as e:
                    print(f"  ✗ Failed to pull fallback image: {e}")
                break

        print("  ✗ Failed to pull image (no valid fallback succeeded)")
        return None


def pull_image(image_name):
    """Pull a Docker image."""
    print(f"  Pulling {image_name}...")
    try:
        subprocess.run(["docker", "pull", image_name], check=True, capture_output=True)
        print(f"  ✓ Pulled successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"  ✗ Failed to pull: {e}")
        return False


def tag_image(source_tag, target_tag):
    """Tag a Docker image."""
    try:
        subprocess.run(
            ["docker", "tag", source_tag, target_tag], check=True, capture_output=True
        )
        return True
    except subprocess.CalledProcessError as e:
        print(f"  ✗ Failed to tag: {e}")
        return False


def ecr_login(ecr_registry, region):
    """Login to ECR."""
    print(f"\nLogging into ECR...")
    try:
        # Extract account ID from registry
        account_id = ecr_registry.split(".")[0]

        # Get ECR login password
        ecr_client = boto3.client("ecr", region_name=region)
        response = ecr_client.get_authorization_token(registryIds=[account_id])

        auth_data = response["authorizationData"][0]
        auth_token = auth_data["authorizationToken"]

        # Decode token and login
        import base64

        decoded = base64.b64decode(auth_token).decode("utf-8")
        username, password = decoded.split(":")

        subprocess.run(
            [
                "docker",
                "login",
                "--username",
                username,
                "--password-stdin",
                ecr_registry,
            ],
            input=password.encode(),
            check=True,
            capture_output=True,
        )
        print("✓ Logged into ECR successfully")
        return True
    except Exception as e:
        print(f"✗ Failed to login to ECR: {e}")
        return False


def ensure_ecr_repository(ecr_client, repository_name):
    """Create ECR repository if it doesn't exist."""
    try:
        ecr_client.describe_repositories(repositoryNames=[repository_name])
        return True
    except ClientError as e:
        if e.response["Error"]["Code"] == "RepositoryNotFoundException":
            try:
                ecr_client.create_repository(repositoryName=repository_name)
                print(f"  Created ECR repository: {repository_name}")
                return True
            except Exception as create_error:
                print(f"  ✗ Failed to create repository: {create_error}")
                return False
        else:
            print(f"  ✗ Error checking repository: {e}")
            return False


def set_ecr_repository_policy(ecr_client, repository_name):
    """Set ECR repository policy for HealthOmics access."""
    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "omics workflow access",
                "Effect": "Allow",
                "Principal": {"Service": "omics.amazonaws.com"},
                "Action": [
                    "ecr:GetDownloadUrlForLayer",
                    "ecr:BatchGetImage",
                    "ecr:BatchCheckLayerAvailability",
                ],
            }
        ],
    }

    try:
        ecr_client.set_repository_policy(
            repositoryName=repository_name, policyText=json.dumps(policy)
        )
        return True
    except Exception as e:
        print(f"  ⚠ Warning: Failed to set policy: {e}")
        return False


def push_image(image_tag):
    """Push a Docker image to ECR."""
    print(f"  Pushing {image_tag}...")
    try:
        subprocess.run(["docker", "push", image_tag], check=True, capture_output=True)
        print(f"  ✓ Pushed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"  ✗ Failed to push: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Sync containers from omics.config to ECR"
    )
    parser.add_argument(
        "--config",
        type=str,
        default="../conf/omics.config",
        help="Path to omics.config file (default: ../conf/omics.config)",
    )
    parser.add_argument(
        "--manifest",
        type=str,
        default="../container_image_manifest.json",
        help="Path to container_image_manifest.json (default: ../container_image_manifest.json)",
    )
    parser.add_argument(
        "--region",
        type=str,
        default="eu-west-2",
        help="AWS region (default: eu-west-2)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without actually doing it",
    )

    args = parser.parse_args()

    # Validate paths
    config_path = Path(args.config)
    manifest_path = Path(args.manifest)

    if not config_path.exists():
        print(f"Error: Config file not found at {config_path}")
        sys.exit(1)

    if not manifest_path.exists():
        print(f"Error: Manifest file not found at {manifest_path}")
        sys.exit(1)

    print("=" * 70)
    print("Container Sync to ECR")
    print("=" * 70)
    print(f"Config: {config_path}")
    print(f"Manifest: {manifest_path}")
    print(f"Dry run: {args.dry_run}")
    print("=" * 70 + "\n")

    # Parse config and manifest
    ecr_registry, target_containers = parse_omics_config(config_path)
    manifest_images = load_manifest(manifest_path)

    if not ecr_registry:
        print("Error: Could not find ecr_registry in config file")
        sys.exit(1)

    print(f"ECR Registry: {ecr_registry}")
    print(f"Target containers: {len(target_containers)}")
    print(f"Manifest images: {len(manifest_images)}\n")

    # Extract region from registry
    region_match = re.search(r"\.([a-z0-9-]+)\.amazonaws\.com", ecr_registry)
    region = region_match.group(1) if region_match else args.region
    print(f"AWS Region: {region}\n")

    # Get local Docker images
    print("Checking local Docker images...")
    local_images = get_local_docker_images()
    print(f"Found {len(local_images)} local images\n")

    # Initialize ECR client
    ecr_client = boto3.client("ecr", region_name=region)

    # Login to ECR
    if not args.dry_run:
        if not ecr_login(ecr_registry, region):
            print("Failed to login to ECR. Exiting.")
            sys.exit(1)

    # Process each target container
    print("\n" + "=" * 70)
    print("Processing Containers")
    print("=" * 70 + "\n")

    success_count = 0
    failed_count = 0

    for target_spec in target_containers:
        print(f"Processing: {target_spec}")

        # Search for matching local image (ignoring prefix before first "/")
        local_match = find_matching_local_image(target_spec, local_images)

        if local_match:
            print(f"  ✓ Found locally as: {local_match}")
            source_image = local_match
        else:
            print(f"  ✗ Not found locally")

            # Find in manifest
            manifest_match = match_manifest_image(target_spec, manifest_images)

            if not manifest_match:
                print(f"  ✗ Not found in manifest either. Skipping.")
                failed_count += 1
                continue

            print(f"  Found in manifest as: {manifest_match}")

            # Pull image
            if args.dry_run:
                print(f"  [DRY RUN] Would pull: {manifest_match}")
                source_image = manifest_match
            else:
                pulled_image = pull_with_registry_fallback(manifest_match)

                if not pulled_image:
                    failed_count += 1
                    continue

                source_image = pulled_image

        # Prepare ECR tag (use the target_spec format for ECR)
        repository = target_spec.split(":")[0]
        tag = target_spec.split(":")[1] if ":" in target_spec else "latest"

        # Tag as target_spec format for local intermediate step
        intermediate_tag = target_spec
        ecr_image = f"{ecr_registry}/{target_spec}"

        # Ensure repository exists and has correct policy
        if args.dry_run:
            print(f"  [DRY RUN] Would ensure repository exists: {repository}")
            print(f"  [DRY RUN] Would set HealthOmics policy on: {repository}")
        else:
            if ensure_ecr_repository(ecr_client, repository):
                set_ecr_repository_policy(ecr_client, repository)

        # Tag image to intermediate format (if needed)
        if source_image != intermediate_tag:
            if args.dry_run:
                print(f"  [DRY RUN] Would retag: {source_image} -> {intermediate_tag}")
            else:
                print(f"  Retagging: {source_image} -> {intermediate_tag}")
                if not tag_image(source_image, intermediate_tag):
                    failed_count += 1
                    continue

        # Tag image for ECR
        if args.dry_run:
            print(f"  [DRY RUN] Would tag for ECR: {intermediate_tag} -> {ecr_image}")
        else:
            print(f"  Tagging for ECR: {ecr_image}")
            if not tag_image(intermediate_tag, ecr_image):
                failed_count += 1
                continue

        # Push to ECR
        if args.dry_run:
            print(f"  [DRY RUN] Would push: {ecr_image}")
        else:
            if not push_image(ecr_image):
                failed_count += 1
                continue

        success_count += 1
        print()

    # Summary
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Total containers: {len(target_containers)}")
    print(f"Successfully processed: {success_count}")
    print(f"Failed: {failed_count}")

    if args.dry_run:
        print("\nThis was a dry run. No changes were made.")

    if failed_count > 0:
        sys.exit(1)
    else:
        print("\n✓ All containers synced successfully!")
        sys.exit(0)


if __name__ == "__main__":
    main()
