# Utility scripts for AWS HealthOmics

**_This is a significant evolution a previous repo - [healthomics_parameter_creator](https://github.com/kai-lawsonmcdowall/healthomics_parameter_creator)_**

This is a workflow designed to streamline the process of preparing, uploading and testing NF-core workflows onto AWS HealthOmics. It is based off of this [Workshop](https://catalog.us-east-1.prod.workshops.aws/workshops/76d4a4ff-fe6f-436a-a1c2-f7ce44bc5d17/en-US/workshop/project-setup) provided by AWS.

Prior to running this, please make sure that you have the correct aws credentials to do this (for example, aws_access_key_id and aws_secret_access_key) and that it is in the correct location (usually home dir under .aws/credentials) as well as the correct region set. I generally recommend changing as few of the defaults values as possible. There are several default values that are not defined as empty in the scripts:

- `default_region` (currently eu-west-2) in 1_create_docker_manifest_and_omics_config.sh
- `DEFAULT_S3_PATH` in script 5_deploy_pipeline_to_aws_images.png

That you will likely be better off setting yourself if you are frequently uploading your pipeline .zip files to a particular S3 bucket/folder and region.

# Custom helper functions

The healthomics_helper_tools is a collection of AWS Omics and custom functions that streamlines the preparation of nf-core pipelines onto healthomics. The scripts below should prompt you for values, but will often specify defaults as is. **Place the healthomics_helper_functions in the parent directory of the nf-core pipeline, then cd into it, and execute the scripts in order (1 to 5)**

## 1_create_docker_manifest_and_omics_config.sh

<br>
This creates a custom nextflow config called omics.config, which defines the containers that need to be used for the different processes. The docker manifest further defines the set of docker containers. Please make sure the public_registry_properties.json is present in the healthomics_helper_tools.
<br><br>
This will create the above files, update the nextflow version in the omics.config (to 23.1 for now), and comment out specific lines in the nextflow.config pertaining to other registries. 
<br>
<br>

![The prompts expected by 1_create_docker_manifest_and_omics_config_inputs](/images/1_create_docker_manifest_and_omics_config_inputs.png)

## 2_stepfunction.sh

<br>
This the needed to privatize the containers by by pulling public containers and registering them to privatize Amazon Elastic Container Registry (AWS ECR). We use the images_manifest.json and an amazon helper function *omx-ecr-helper* app, which helps automate preparing containers for use with AWS HealthOmics Workflows that performs two key functions: <br><br>

1. **container-puller**: Retrieves container images from public registries like (Amazon ECR Public, Quay.io, DockerHub) and stages them in Amazon ECR Private image repositories in your AWS account
   <br>

2. **container-builder**: Builds ECR Private container images from source bundles staged in S3
   <br>

![The prompts expected by 2_stepfunction.sh](/images/2_stepfunction_inputs.png)

## 3_move_omics_config_update_nextflow_config.sh

<br>
This script is some what of an intermediary, moving the omics.config from the nf-core parent directory to the conf directory. As well as making sure the omics.config file is include/read in by the nextflow.config. This doesn't require any additional inputs and can simply be run.

<br>

## 4_parameter_extractor_command_line.py

<br>
creates the paramter_template.json file which has to be supplied to healthomics for it to understand which parameters it can use. This leverages the nextflow_schema.json, and the nf-core page for the pipeline in question. It also filters out general parameters which will not work in the context of HealthOmics. It shoud output a parameter_template.json file. Please ensure that only the absolutely necessary parameters in are set to optional=false, in this file, as otherwise HealthOmics will prevent the pipeline running without them even if they are not strictly needed. 
<br>
<br>

![The prompts expected by 4_parameter_extractor_command_line_inputs](/images/4_parameter_extractor_command_line_inputs.png)

## 5_deploy_pipeline_to_aws.sh

<br>
This is the final stage in the process. This involves zipping the workflow, uploading to s3, and then pointing HealthOmics at this zipped workflow to create the omics workflow. There are several smaller intermediate steps which are detailed in the script itself. 
<br>
<br>

![The prompts expected by 5_deploy_pipeline_to_aws_images](/images/5_deploy_pipeline_to_aws_images.png)

## 6_pull_test_data

Most NF-core pipelines have test and test_full profiles, and within these links to sample sheets which themselves contain links to filepaths for samples. The purpose of this script is firstly, to identify the link to the sample sheets within the test.config files (i.e. the --input value), for example:

```
# extracted from the nf-core rnaseq pipeline in conf/test.config
 input              = 'https://raw.githubusercontent.com/nf-core/test-datasets/626c8fab639062eade4b10747e919341cbf9b41a/samplesheet/v3.10/samplesheet_test.csv'
```

Which looks like so:

```
sample,fastq_1,fastq_2,strandedness
WT_REP1,https://raw.githubusercontent.com/nf-core/test-datasets/rnaseq/testdata/GSE110004/SRR6357070_1.fastq.gz,https://raw.githubusercontent.com/nf-core/test-datasets/rnaseq/testdata/GSE110004/SRR6357070_2.fastq.gz,auto
WT_REP1,https://raw.githubusercontent.com/nf-core/test-datasets/rnaseq/testdata/GSE110004/SRR6357071_1.fastq.gz,https://raw.githubusercontent.com/nf-core/test-datasets/rnaseq/testdata/GSE110004/SRR6357071_2.fastq.gz,auto
WT_REP2,https://raw.githubusercontent.com/nf-core/test-datasets/rnaseq/testdata/GSE110004/SRR6357072_1.fastq.gz,https://raw.githubusercontent.com/nf-core/test-datasets/rnaseq/testdata/GSE110004/SRR6357072_2.fastq.gz,reverse
RAP1_UNINDUCED_REP1,https://raw.githubusercontent.com/nf-core/test-datasets/rnaseq/testdata/GSE110004/SRR6357073_1.fastq.gz,,reverse
RAP1_UNINDUCED_REP2,https://raw.githubusercontent.com/nf-core/test-datasets/rnaseq/testdata/GSE110004/SRR6357074_1.fastq.gz,,reverse
RAP1_UNINDUCED_REP2,https://raw.githubusercontent.com/nf-core/test-datasets/rnaseq/testdata/GSE110004/SRR6357075_1.fastq.gz,,reverse
RAP1_IAA_30M_REP1,https://raw.githubusercontent.com/nf-core/test-datasets/rnaseq/testdata/GSE110004/SRR6357076_1.fastq.gz,https://raw.githubusercontent.com/nf-core/test-datasets/rnaseq/testdata/GSE110004/SRR6357076_2.fastq.gz,reverse
```

Secondly, download the sample sheet locally, then download it's corresponding files. From here, you can then specify your new s3 folder that you would like the sample sheet and files (will be the same folder for now) to be uploaded to. The script will then change the filepaths in the sample sheet, and then uploaded the samples and the sample sheets to the folder. All in all, this means you should now have a sample sheet and the corresponding files on your s3 ready to be passed to the pipeline for testing. (for the moment, the choice to have the sample sheet and samples end up in the same place was for simplicities sake).

It will then repeat the above process for the test_full.config, if you wish to have a larger test available.

The general workflow might look like this:

```
# How it will appear on the command line (6_pull_test_data.py)

# Using the above example, executing this for RNAseq (For test.config)

Enter the filepath of the samples in the sample sheet you want to change:
https://raw.githubusercontent.com/nf-core/test-datasets/rnaseq/testdata/GSE110004/ #check sample sheet above

Enter the string you want to replace it with:
s3://path/where/I/want/my/fastqs/and/samplesheet.

*repeat for test_full.config*

```

# AWS Specific functions

These are scripts that support using AWS HealthOmics

## [inspect_nf](./inspect_nf.py)

Python script that inspects a Nextflow workflow definition and generates resources to help migrate it to run on AWS HealthOmics.

Specifically designed to handle NF-Core based workflows, but in theory could handle any Nextflow workflow definition.

Prerequisites:

- Python 3

What it does:

- look through all \*.nf files
- find `container` directives
- extract container uris to:
  - build an image uri manifest
  - create a custom nextflow.config file

Usage:

```text
usage: inspect_nf.py [-h] [-s CONTAINER_SUBSTITUTIONS] [-n NAMESPACE_CONFIG] [--output-manifest-file OUTPUT_MANIFEST_FILE] [--output-config-file OUTPUT_CONFIG_FILE]
                     [--region REGION] [--profile PROFILE]
                     project

positional arguments:
  project               Top level directory of Nextflow workflow project

optional arguments:
  -h, --help            show this help message and exit
  -s CONTAINER_SUBSTITUTIONS, --container-substitutions CONTAINER_SUBSTITUTIONS
                        JSON file of container image substitutions.
  -n NAMESPACE_CONFIG, --namespace-config NAMESPACE_CONFIG
                        JSON file with public registry to ecr repository namespace mappings. This should be the same as what is used by omx-ecr-helper.
  --output-manifest-file OUTPUT_MANIFEST_FILE
                        Filename to use for generated container image manifest
  --output-config-file OUTPUT_CONFIG_FILE
                        Filename to use for generated nextflow config file
  --region REGION       AWS region name
  --profile PROFILE     AWS CLI profile to use. (See `aws configure help` for more info)
```

## [compute_pricing.py](./compute_pricing.py)

Python script that computes the cost of a workflow run breaking out details for individual tasks and run storage.

Prerequisites:

- Python 3
- Python packages
  - boto3
  - requests

What it does:

- retrieves regional AWS HealthOmics pricing using the [AWS Price List bulk API](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/using-ppslong.html)
- retrieves workflow run details from AWS HealthOmics
- matches reported run task `omics.*` instance types to pricing SKUs
- prints a JSON summary of the run's costs

Usage:

```text
usage: compute_pricing.py [-h] [--profile PROFILE] [--region REGION] [--offering OFFERING] run_id

positional arguments:
  run_id               HealthOmics workflow run-id to analyze

optional arguments:
  -h, --help           show this help message and exit
  --profile PROFILE    AWS profile to use
  --region REGION      AWS region to use
  --offering OFFERING  path to pricing offer JSON
```

## [timeline.py](./timeline.py)

Python script that generates a timeline plot of a workflow run

Prerequisites:

- Python 3
- Python packages
  - boto3
  - bokeh == 2.4.3
  - pandas
  - requests
- Other scripts
  - compute_pricing.py

What it does:

- retrieves workflow run details from AWS HealthOmics
- creates a csv file with task details
- creates an html document with an interactive Bokeh plot that shows task timing with instance cpu and memory allocated per task

Usage:

```text
usage: timeline.py [-h] [--profile PROFILE] [--region REGION] [-u {sec,min,hr,day}] [-o OUTPUT_DIR] [--no-show] runid

positional arguments:
  runid                 HealthOmics workflow run-id to plot

optional arguments:
  -h, --help            show this help message and exit
  --profile PROFILE     AWS profile to use (default: None)
  --region REGION       AWS region to use (default: None)
  -u {sec,min,hr,day}, --time-units {sec,min,hr,day}
                        Time units to use for plot (default: min)
  -o OUTPUT_DIR, --output-dir OUTPUT_DIR
                        Directory to save output files (default: .)
  --no-show             Do not show plot (default: False)
```
