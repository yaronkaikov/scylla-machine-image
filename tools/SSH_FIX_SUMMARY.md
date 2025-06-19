# SSH Authentication Fix Summary

## Issue Resolved
Fixed SSH "Permission denied (publickey)" error when connecting to AWS instances for ScyllaDB benchmarking.

## Root Cause
The original code was trying to connect via SSH without proper key authentication and only attempting one user (`scyllaadm`).

## Changes Made

### 1. Enhanced SSH Key Discovery
- Automatically searches for SSH keys in multiple standard locations
- Supports different key file formats (.pem, .key, standard)
- Falls back to default SSH keys if no specific key is provided

### 2. Multiple User Authentication
- Tries connecting with common ScyllaDB/AWS users in sequence:
  - `scyllaadm` (ScyllaDB default)
  - `centos` (CentOS/RHEL images)  
  - `ubuntu` (Ubuntu images)
  - `ec2-user` (Amazon Linux)
  - `admin` (custom images)

### 3. Improved AWS Provider
- Added `key_name` parameter to AWS provider constructor
- Pass SSH key name through to connection logic
- Better error handling and logging

### 4. Enhanced Connection Logic
- Added connection timeout and keepalive settings
- Disabled password authentication for security
- Better error reporting for troubleshooting

## Files Modified
- `/Users/yaronkaikov/git/scylla-machine-image/tools/cloud_io_benchmark.py`
  - Updated `AWSProvider.__init__()` to accept key_name
  - Enhanced `run_command_on_instance()` with multi-user SSH attempts  
  - Updated `create_cloud_provider()` factory function
  - Modified main() to pass key_name to provider

## Usage Instructions

### Quick Fix - Specify Your Key
```bash
python cloud_io_benchmark.py --cloud aws --region us-east-1 \
  --image ami-12345678 --instance-family i4i \
  --aws-key-name YOUR_EC2_KEY_NAME
```

### If You Don't Have a Key
```bash
# Create one first:
aws ec2 create-key-pair --key-name scylla-benchmark-key \
  --query 'KeyMaterial' --output text > ~/.ssh/scylla-benchmark-key.pem
chmod 400 ~/.ssh/scylla-benchmark-key.pem

# Then use it:
python cloud_io_benchmark.py --cloud aws --region us-east-1 \
  --image ami-12345678 --instance-family i4i \
  --aws-key-name scylla-benchmark-key
```

## Benefits
- ✅ **Multiple user fallback** - Automatically tries different SSH users
- ✅ **Flexible key discovery** - Finds SSH keys in standard locations  
- ✅ **Better error messages** - Clear feedback on connection issues
- ✅ **Backwards compatible** - Works with existing setups
- ✅ **Secure connections** - Proper SSH configuration with timeouts

The benchmark should now successfully connect to AWS instances and generate CSV reports without SSH authentication errors.
