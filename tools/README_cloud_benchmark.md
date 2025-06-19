# ScyllaDB Cloud I/O Benchmark Tool

This tool automates the process of spinning up cloud instances across AWS, GCP, and Azure, running the `scylla_cloud_io_setup` command multiple times on each instance type, and reporting the results in a tabular format.

## Features

- **Multi-Cloud Support**: Works with AWS EC2, Google Compute Engine, and Azure Virtual Machines
- **Automated Instance Management**: Creates, configures, and terminates instances automatically
- **Performance Metrics**: Extracts I/O performance metrics (IOPS, bandwidth) from `scylla_cloud_io_setup`
- **Comprehensive Reporting**: Generates CSV reports and summary tables
- **Concurrent Execution**: Supports parallel benchmarking for faster results
- **Error Handling**: Robust error handling and logging throughout the process

## Prerequisites

### 1. Install Dependencies

```bash
cd /Users/yaronkaikov/git/scylla-machine-image/tools
pip install -r requirements.txt
```

### 2. Cloud Provider Setup

#### AWS
```bash
# Install AWS CLI and configure credentials
aws configure
# Or set environment variables
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
export AWS_DEFAULT_REGION=us-east-1
```

#### Google Cloud Platform
```bash
# Install gcloud CLI and authenticate
gcloud auth login
gcloud config set project your-project-id
# Or set service account key
export GOOGLE_APPLICATION_CREDENTIALS=path/to/service-account-key.json
```

#### Azure
```bash
# Install Azure CLI and login
az login
# Or set service principal credentials
export AZURE_CLIENT_ID=your_client_id
export AZURE_CLIENT_SECRET=your_secret
export AZURE_TENANT_ID=your_tenant_id
```

### 3. SSH Key Setup

Ensure you have SSH keys configured for accessing the cloud instances:

```bash
# Generate SSH key if needed
ssh-keygen -t rsa -b 4096 -f ~/.ssh/scylla-benchmark-key

# Add public key to cloud providers
# AWS: Add to EC2 Key Pairs
# GCP: Add to Compute Engine metadata
# Azure: Configure during VM creation
```

## Usage

### Basic Usage

```bash
# Test AWS i4i instance family
python cloud_io_benchmark.py \
  --cloud aws \
  --region us-east-1 \
  --image ami-12345678 \
  --instance-family i4i \
  --runs 3

# Test GCP n2 instance family
python cloud_io_benchmark.py \
  --cloud gcp \
  --region us-central1 \
  --project-id my-project \
  --image projects/scylla-images/global/images/scylladb-5-2-1 \
  --instance-family n2 \
  --runs 3

# Test Azure L8s_v3 instance family
python cloud_io_benchmark.py \
  --cloud azure \
  --region eastus \
  --subscription-id 12345678-1234-1234-1234-123456789012 \
  --image /subscriptions/.../images/scylladb/versions/5.2.1 \
  --instance-family L8s_v3 \
  --runs 3
```

### Advanced Usage

```bash
# Test specific instance types
python cloud_io_benchmark.py \
  --cloud aws \
  --region us-east-1 \
  --image ami-12345678 \
  --instance-types i4i.large i4i.xlarge i4i.2xlarge \
  --runs 5 \
  --max-concurrent 2 \
  --output-csv my_benchmark_results.csv

# Dry run to see configuration
python cloud_io_benchmark.py \
  --cloud aws \
  --region us-east-1 \
  --image ami-12345678 \
  --instance-family i4i \
  --dry-run

# Enable debug logging
python cloud_io_benchmark.py \
  --cloud aws \
  --region us-east-1 \
  --image ami-12345678 \
  --instance-family i4i \
  --debug
```

## Supported Instance Types

### AWS
- **i3en**: i3en.large, i3en.xlarge, i3en.2xlarge, i3en.3xlarge, i3en.6xlarge, i3en.12xlarge, i3en.24xlarge, i3en.metal
- **i4i**: i4i.large, i4i.xlarge, i4i.2xlarge, i4i.4xlarge, i4i.8xlarge, i4i.16xlarge, i4i.32xlarge, i4i.metal
- **i3**: i3.large, i3.xlarge, i3.2xlarge, i3.4xlarge, i3.8xlarge, i3.16xlarge, i3.metal
- **c5d**: c5d.large, c5d.xlarge, c5d.2xlarge, c5d.4xlarge, c5d.9xlarge, c5d.18xlarge, c5d.metal
- **i7ie**: i7ie.large, i7ie.xlarge, i7ie.2xlarge, i7ie.3xlarge
- **im4gn**: im4gn.xlarge, im4gn.2xlarge, im4gn.4xlarge, im4gn.8xlarge, im4gn.16xlarge
- **is4gen**: is4gen.xlarge, is4gen.2xlarge, is4gen.4xlarge
- **i4g**: i4g.large, i4g.xlarge, i4g.2xlarge, i4g.4xlarge, i4g.8xlarge, i4g.16xlarge

### Google Cloud Platform
- **n1**: n1-standard-2, n1-standard-4, n1-standard-8, n1-standard-16, n1-standard-32, n1-highmem-8, n1-highmem-16
- **n2**: n2-standard-2, n2-standard-4, n2-standard-8, n2-standard-16, n2-standard-32, n2-highmem-4, n2-highmem-8
- **n2d**: n2d-standard-2, n2d-standard-4, n2d-standard-8, n2d-standard-16, n2d-standard-32, n2d-highmem-4, n2d-highmem-8
- **c2**: c2-standard-4, c2-standard-8, c2-standard-16, c2-standard-30
- **m1**: m1-megamem-96

### Microsoft Azure
- **L8s_v3**: Standard_L8s_v3
- **L16s_v3**: Standard_L16s_v3
- **L32s_v3**: Standard_L32s_v3
- **L48s_v3**: Standard_L48s_v3
- **L64s_v3**: Standard_L64s_v3
- **L80s_v3**: Standard_L80s_v3
- **Lsv2**: Standard_L8s_v2, Standard_L16s_v2, Standard_L32s_v2

## Output

The tool generates two types of output:

### 1. CSV Report
A detailed CSV file containing all benchmark results with columns:
- cloud, instance_type, instance_id, run_number, success, execution_time
- read_iops, write_iops, read_bandwidth, write_bandwidth, error_message

### 2. Summary Table
A formatted console table showing averages per instance type:
```
====================================================================================================
SCYLLA I/O SETUP BENCHMARK RESULTS
====================================================================================================
Instance Type        Success Rate Avg Time (s) Avg Read IOPS  Avg Write IOPS Avg Read BW (MB/s)   Avg Write BW (MB/s)  
----------------------------------------------------------------------------------------------------
i4i.large                100.0%       45.2           58000           52000              1400.5              1250.3
i4i.xlarge               100.0%       48.1           95000           88000              2200.8              2100.1
----------------------------------------------------------------------------------------------------
Total instances tested: 6
Overall success rate: 100.0%
====================================================================================================
```

## Testing

Run the test suite to verify your setup:

```bash
python test_cloud_benchmark.py
```

This will test:
- Import functionality
- Instance type mappings
- Metric parsing
- Configuration handling

## Troubleshooting

### Common Issues

1. **Import Errors**: Install missing dependencies with `pip install -r requirements.txt`
2. **Authentication Errors**: Verify cloud provider credentials are properly configured
3. **SSH Connection Issues**: Ensure SSH keys are properly set up and security groups allow SSH access
4. **Instance Creation Failures**: Check quotas, limits, and permissions in your cloud account
5. **Metric Parsing Issues**: Verify that `scylla_cloud_io_setup` is installed and working on your instances

### Debug Mode

Enable debug logging to get detailed information about what the tool is doing:

```bash
python cloud_io_benchmark.py --debug [other options]
```

### Logs

Check the log file for detailed execution information:
```bash
tail -f cloud_io_benchmark.log
```

## Cost Considerations

- **Instance Costs**: You will be charged for the compute time of instances created during benchmarking
- **Storage Costs**: Minimal storage costs for OS disks during instance lifetime
- **Network Costs**: Minimal network costs for SSH connections and data transfer

To minimize costs:
- Use smaller instance types for initial testing
- Limit the number of concurrent instances with `--max-concurrent`
- Ensure instances are properly terminated (the tool does this automatically)

## Security Considerations

- Instances are created with security groups allowing SSH access
- SSH keys should be properly secured
- Instances are tagged for identification and automatic cleanup
- All instances are terminated automatically after benchmarking

## Contributing

To add support for new instance types:
1. Update the `get_supported_instance_types()` function
2. Test with the new instance types
3. Update this documentation

To add support for new cloud providers:
1. Implement the `CloudProviderInterface` 
2. Add the provider to `create_cloud_provider()` function
3. Update documentation and tests
