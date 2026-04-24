# ecr_tools

Utility scripts for managing container images in Amazon ECR for use with **nf-core (Nextflow) pipelines** running on **AWS HealthOmics**.

## Background

AWS HealthOmics requires every container image referenced by a workflow to exist in a **private ECR repository in the same region** before a run can start. The usual process — described in the [AWS HealthOmics nf-core workshop](https://catalog.us-east-1.prod.workshops.aws/workshops/76d4a4ff-fe6f-436a-a1c2-f7ce44bc5d17/en-US/workshop/project-setup) — is to submit a `container_image_manifest.json` to the `omx-container-puller` Step Functions state machine (from the [amazon-ecr-helper-for-aws-healthomics](https://github.com/aws-samples/amazon-ecr-helper-for-aws-healthomics) CDK app), which pulls each public image and stages it into ECR with the correct HealthOmics access policy.

In practice the state machine occasionally misses images (e.g. `community.wave.seqera.io` / Seqera Wave containers, or images whose source registry prefix doesn't match what's in the manifest), and empty repositories tend to accumulate after experimentation. The scripts in this folder fill those gaps.

## Scripts

### `find_containers_stepfunction_missed.py`
Audits which containers referenced in a pipeline's `omics.config` are actually present in ECR. It parses every `container = '...'` line out of the config, reads the `ecr_registry` value, and calls `ecr:DescribeImages` for each `repository:tag`. Prints an `EXISTS` / `MISSING` line per container and exits non-zero with a list of missing ones — useful for confirming the `omx-container-puller` state machine did its job, or generating a shortlist to re-push manually.

```bash
python find_containers_stepfunction_missed.py --config ../conf/omics.config --region eu-west-2
```

### `sync_containers_to_ecr.py`
The main remediation script. For every container in `omics.config` it:
1. Checks whether a matching image already exists locally (tolerating registry-prefix differences, e.g. `biocontainers/fq:...` vs `quay.io/biocontainers/fq:...`).
2. If not, looks the image up in `container_image_manifest.json` and `docker pull`s it, with automatic `quay.io/` fallback for `biocontainers/` and `nf-core/` namespaces.
3. Creates the ECR repository if needed and applies the HealthOmics repository policy (`omics.amazonaws.com` → `BatchGetImage`, `GetDownloadUrlForLayer`, `BatchCheckLayerAvailability`).
4. Tags the image for the target ECR registry and pushes it.

Supports `--dry-run` to preview everything without pulling, tagging, or pushing.

```bash
python sync_containers_to_ecr.py \
    --config ../conf/omics.config \
    --manifest ../container_image_manifest.json \
    --region eu-west-2 \
    [--dry-run]
```

### `manually_push_wave_containers.sh`
A focused variant of the sync script for **Seqera Wave** containers (`community.wave.seqera.io/library/...`), which the `omx-container-puller` state machine doesn't handle well. The list of containers is hardcoded at the top of the script. For each one it pulls from Wave, creates an ECR repo named `wave/library/<package>`, applies the HealthOmics access policy, pushes the image, and cleans up the local copies. Interactive — prompts for region at start and uses the current `aws sts` identity for the account ID.

```bash
./manually_push_wave_containers.sh
```

To add or remove images, edit the `CONTAINERS=(...)` array at the top of the file.

### `list_empty_ECR_repositories.sh`
Lists ECR repositories in the configured region that contain zero images. Read-only, useful as a preview before running the delete script or for general housekeeping. Region is set via the `AWS_REGION` variable at the top of the file.

```bash
./list_empty_ECR_repostories.sh
```

### `delete_empty_ECR_repositories.sh`
Deletes every ECR repository in the region that has no images in it. Supports `--dry-run` to print which repositories *would* be deleted without acting. Region is set via the `AWS_REGION` variable at the top of the file.

```bash
./delete_empty_ECR_repositories.sh --dry-run   # preview
./delete_empty_ECR_repositories.sh             # actually delete
```

> This is Destructive. Always run with `--dry-run` first, or check output of `list_empty_ECR_repostories.sh`, before deleting.

## Typical workflow

1. Run the `omx-container-puller` Step Function with your `container_image_manifest.json` as per the AWS workshop.
2. Run `find_containers_stepfunction_missed.py` to see which images, if any, it missed.
3. Run `sync_containers_to_ecr.py` (and/or `manually_push_wave_containers.sh` for Wave images) to push the stragglers.
4. Re-run `find_containers_stepfunction_missed.py` to confirm everything resolves.
5. Periodically use the `list` / `delete` empty-repo scripts for cleanup.

## Requirements

- AWS CLI v2, authenticated with permissions for `ecr:*` and `sts:GetCallerIdentity`
- Docker daemon running and logged in to any public registries your images come from (most Biocontainers / quay.io images are anonymous-pullable)
- Python 3.8+ with `boto3` (for the `.py` scripts)
- `bash` 4+ (for the `.sh` scripts)

All scripts default to region `eu-west-2`; override via `--region` (Python) or by editing the `AWS_REGION` / prompt value (shell).