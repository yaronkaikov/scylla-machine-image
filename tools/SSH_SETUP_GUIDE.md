# SSH Configuration Guide for ScyllaDB Cloud I/O Benchmark

## Problem Resolution: SSH Permission Denied

The error you encountered indicates that SSH public key authentication is failing. Here's how to fix it:

### 1. AWS EC2 Key Pair Setup

**Option A: Use existing EC2 Key Pair**
```bash
# If you have an existing EC2 key pair, specify it when running the benchmark:
python cloud_io_benchmark.py --cloud aws --region us-east-1 \
  --image ami-12345678 --instance-family i4i \
  --aws-key-name YOUR_KEY_PAIR_NAME
```

**Option B: Create new EC2 Key Pair**
```bash
# Create a new key pair via AWS CLI
aws ec2 create-key-pair --key-name scylla-benchmark-key \
  --query 'KeyMaterial' --output text > ~/.ssh/scylla-benchmark-key.pem

# Set proper permissions
chmod 400 ~/.ssh/scylla-benchmark-key.pem

# Use the new key pair
python cloud_io_benchmark.py --cloud aws --region us-east-1 \
  --image ami-12345678 --instance-family i4i \
  --aws-key-name scylla-benchmark-key
```

### 2. SSH Key Location Options

The benchmark tool will automatically look for SSH keys in these locations (in order):

1. `~/.ssh/{key_name}.pem` (EC2 format)
2. `~/.ssh/{key_name}` (standard format)  
3. `~/.ssh/{key_name}.key` (alternative format)
4. `~/.ssh/id_rsa` (default RSA key)
5. `~/.ssh/id_ed25519` (default Ed25519 key)
6. `~/.ssh/id_ecdsa` (default ECDSA key)

### 3. User Authentication Attempt Order

The tool will try connecting with these users (in order):
1. `scyllaadm` (ScyllaDB default)
2. `centos` (CentOS/RHEL images)
3. `ubuntu` (Ubuntu images)
4. `ec2-user` (Amazon Linux)
5. `admin` (Some custom images)

### 4. Common SSH Key Issues & Solutions

**Issue: Key file permissions too open**
```bash
# Fix permissions
chmod 400 ~/.ssh/your-key.pem
```

**Issue: Key not found**
```bash
# Verify key exists
ls -la ~/.ssh/your-key.pem

# Check key permissions
ls -la ~/.ssh/your-key.pem
# Should show: -r-------- (400 permissions)
```

**Issue: Wrong key format**
```bash
# If you have a .pub file, you need the private key (without .pub extension)
# Make sure you're using the private key, not the public key
```

### 5. Testing SSH Connection Manually

Before running the benchmark, test SSH connection manually:

```bash
# Test connection (replace with your values)
ssh -i ~/.ssh/your-key.pem -o StrictHostKeyChecking=no scyllaadm@YOUR_INSTANCE_IP

# If that fails, try other users:
ssh -i ~/.ssh/your-key.pem -o StrictHostKeyChecking=no centos@YOUR_INSTANCE_IP
ssh -i ~/.ssh/your-key.pem -o StrictHostKeyChecking=no ubuntu@YOUR_INSTANCE_IP
ssh -i ~/.ssh/your-key.pem -o StrictHostKeyChecking=no ec2-user@YOUR_INSTANCE_IP
```

### 6. Enhanced Benchmark Command Example

```bash
# Complete example with all SSH-related parameters
python cloud_io_benchmark.py \
  --cloud aws \
  --region us-east-1 \
  --image ami-0abcd1234 \
  --instance-types i4i.large i4i.xlarge \
  --aws-key-name my-ec2-key \
  --runs 3 \
  --debug
```

### 7. Troubleshooting Tips

1. **Enable debug logging**: Add `--debug` to see detailed SSH connection attempts
2. **Check AWS Console**: Verify the instance is running and has a public IP
3. **Security Groups**: Ensure port 22 (SSH) is open in your security group
4. **VPC Settings**: Make sure the instance is in a public subnet with internet gateway access

### 8. Alternative: Use AWS Session Manager

If SSH continues to fail, you can use AWS Systems Manager Session Manager:

```bash
# Install Session Manager plugin
# Then connect without SSH keys:
aws ssm start-session --target YOUR_INSTANCE_ID
```

### What the Fix Does

The updated benchmark tool now:

✅ **Tries multiple SSH users** - Automatically attempts connection with different common users  
✅ **Finds SSH keys automatically** - Looks for keys in multiple standard locations  
✅ **Better error messages** - Provides clear feedback on connection failures  
✅ **Robust authentication** - Uses multiple fallback strategies for SSH access  

This should resolve the "Permission denied (publickey)" error you encountered.
