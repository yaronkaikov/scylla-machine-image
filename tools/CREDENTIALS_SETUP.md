# Cloud Credentials Setup Guide

## Overview
The ScyllaDB Cloud I/O Benchmark tool requires proper authentication with cloud providers to create and manage instances. This guide shows you how to set up credentials for each supported cloud provider.

## AWS Credentials Setup

### Method 1: AWS CLI (Recommended)
```bash
# Install AWS CLI if not already installed
pip install awscli

# Run AWS configure and enter your credentials
aws configure
```

You'll be prompted to enter:
- AWS Access Key ID
- AWS Secret Access Key  
- Default region name (e.g., us-east-1)
- Default output format (json)

### Method 2: Environment Variables
```bash
export AWS_ACCESS_KEY_ID=your_access_key_here
export AWS_SECRET_ACCESS_KEY=your_secret_key_here
export AWS_DEFAULT_REGION=us-east-1
```

### Method 3: IAM Roles (For EC2 instances)
If running on an EC2 instance, attach an IAM role with the following permissions:
- `ec2:*` (EC2 full access)
- `iam:PassRole` (if needed for instance profiles)

### Required AWS Permissions
Your AWS credentials need the following permissions:
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "ec2:RunInstances",
                "ec2:TerminateInstances",
                "ec2:DescribeInstances",
                "ec2:DescribeInstanceStatus",
                "ec2:DescribeRegions",
                "ec2:CreateTags",
                "ec2:DescribeImages",
                "ec2:DescribeSecurityGroups",
                "ec2:DescribeSubnets",
                "ec2:DescribeKeyPairs"
            ],
            "Resource": "*"
        }
    ]
}
```

## GCP Credentials Setup

### Method 1: gcloud CLI (Recommended)
```bash
# Install Google Cloud SDK
# Visit: https://cloud.google.com/sdk/docs/install

# Authenticate with Google Cloud
gcloud auth login

# Set your project ID
gcloud config set project YOUR_PROJECT_ID

# Enable required APIs
gcloud services enable compute.googleapis.com
```

### Method 2: Service Account Key
```bash
# Create a service account key file
# Download the JSON key file from GCP Console
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/your/service-account-key.json"
```

### Required GCP Permissions
Your GCP credentials need the following roles:
- `Compute Engine Admin` (compute.admin)
- Or custom role with these permissions:
  - `compute.instances.create`
  - `compute.instances.delete`
  - `compute.instances.get`
  - `compute.instances.list`
  - `compute.instances.setMetadata`
  - `compute.disks.create`
  - `compute.disks.delete`

## Azure Credentials Setup

### Method 1: Azure CLI (Recommended)
```bash
# Install Azure CLI
# Visit: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli

# Login to Azure
az login

# Set your subscription (if you have multiple)
az account set --subscription "your-subscription-id"
```

### Method 2: Service Principal
```bash
# Create a service principal
az ad sp create-for-rbac --name "scylla-benchmark-sp" --role Contributor

# Set environment variables with the output
export AZURE_CLIENT_ID=your_client_id
export AZURE_CLIENT_SECRET=your_client_secret
export AZURE_TENANT_ID=your_tenant_id
export AZURE_SUBSCRIPTION_ID=your_subscription_id
```

### Required Azure Permissions
Your Azure credentials need the following permissions:
- `Virtual Machine Contributor` role
- `Network Contributor` role (for network operations)
- Or custom role with these permissions:
  - `Microsoft.Compute/virtualMachines/*`
  - `Microsoft.Network/networkInterfaces/*`
  - `Microsoft.Network/publicIPAddresses/*`

## Testing Your Credentials

### Test with Dry Run
Before running actual benchmarks, test your credentials with dry-run mode:

```bash
# Test AWS credentials
python cloud_io_benchmark.py --cloud aws --region us-east-1 --image ami-12345678 --instance-family i4i --dry-run

# Test GCP credentials
python cloud_io_benchmark.py --cloud gcp --region us-central1 --project-id YOUR_PROJECT --image projects/scylla-images/global/images/scylladb-5-2-1 --instance-family n2 --dry-run

# Test Azure credentials
python cloud_io_benchmark.py --cloud azure --region eastus --subscription-id YOUR_SUBSCRIPTION --image /subscriptions/.../images/scylladb --instance-family L8s_v3 --dry-run
```

### Test with Minimal Run
Once dry-run works, test with a minimal actual run:

```bash
# Test with just one instance type and one run
python cloud_io_benchmark.py --cloud aws --region us-east-1 --image ami-12345678 --instance-types i4i.large --runs 1
```

## SSH Key Setup

The benchmark tool requires SSH access to instances. Make sure you have SSH keys configured:

### AWS
```bash
# Create or import an EC2 key pair
aws ec2 create-key-pair --key-name scylla-benchmark-key --query 'KeyMaterial' --output text > ~/.ssh/scylla-benchmark-key.pem
chmod 400 ~/.ssh/scylla-benchmark-key.pem

# Add to SSH config
echo "Host *.amazonaws.com
    IdentityFile ~/.ssh/scylla-benchmark-key.pem
    User ec2-user" >> ~/.ssh/config
```

### GCP
```bash
# GCP uses gcloud SSH which handles keys automatically
# Ensure you have the gcloud SDK installed and configured
gcloud compute config-ssh
```

### Azure
```bash
# Create SSH key pair
ssh-keygen -t rsa -b 4096 -f ~/.ssh/scylla-azure-key

# The public key will be used when creating VMs
# Private key will be used for SSH access
```

## Troubleshooting

### Common Issues

1. **"AWS credentials not configured"**
   - Check if `aws configure` was run successfully
   - Verify environment variables are set correctly
   - Test with `aws sts get-caller-identity`

2. **"GCP credentials not configured"**
   - Check if `gcloud auth login` was run
   - Verify project ID is set: `gcloud config get-value project`
   - Test with `gcloud compute instances list`

3. **"Azure credentials not configured"**
   - Check if `az login` was run
   - Verify subscription: `az account show`
   - Test with `az vm list`

4. **"Permission denied" errors**
   - Check if your credentials have the required permissions
   - For AWS, try `aws ec2 describe-regions`
   - For GCP, try `gcloud compute instances list`
   - For Azure, try `az vm list`

### Getting Help

If you continue to have credential issues:

1. Use `--debug` flag for detailed logging
2. Check the log file `cloud_io_benchmark.log`
3. Verify your cloud provider's documentation for authentication
4. Test credentials with cloud provider's CLI tools first

## Security Best Practices

1. **Use minimal required permissions** - Don't use admin accounts
2. **Rotate credentials regularly** - Especially for programmatic access
3. **Use temporary credentials** when possible (IAM roles, service accounts)
4. **Never commit credentials** to version control
5. **Monitor usage** with cloud provider billing and activity logs
