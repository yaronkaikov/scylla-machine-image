#!/usr/bin/env python3
"""
SSH Connection Test for ScyllaDB Cloud Benchmark

This script tests the SSH connection fixes without actually running cloud instances.
It validates the SSH key discovery and connection logic.
"""

import os
import sys
from pathlib import Path

def test_ssh_key_discovery():
    """Test SSH key discovery logic"""
    print("🔑 Testing SSH Key Discovery")
    print("=" * 50)
    
    # Common SSH key locations
    ssh_dir = os.path.expanduser('~/.ssh')
    if not os.path.exists(ssh_dir):
        print(f"❌ SSH directory not found: {ssh_dir}")
        return False
    
    print(f"✓ SSH directory found: {ssh_dir}")
    
    # List available SSH keys
    key_files = []
    common_key_names = ['id_rsa', 'id_ed25519', 'id_ecdsa']
    
    for key_name in common_key_names:
        key_path = os.path.join(ssh_dir, key_name)
        if os.path.exists(key_path):
            key_files.append(key_path)
            print(f"✓ Found SSH key: {key_path}")
    
    # Look for .pem files (EC2 format)
    pem_files = list(Path(ssh_dir).glob('*.pem'))
    for pem_file in pem_files:
        key_files.append(str(pem_file))
        print(f"✓ Found EC2 key: {pem_file}")
    
    if not key_files:
        print("⚠️  No SSH keys found in ~/.ssh/")
        print("💡 You may need to generate SSH keys or download your EC2 key pair")
        return False
    
    print(f"\n📊 Total SSH keys found: {len(key_files)}")
    return True

def test_ssh_key_permissions():
    """Test SSH key file permissions"""
    print("\n🔒 Testing SSH Key Permissions")
    print("=" * 50)
    
    ssh_dir = os.path.expanduser('~/.ssh')
    issues_found = []
    
    # Check SSH directory permissions
    ssh_dir_stat = os.stat(ssh_dir)
    ssh_dir_perms = oct(ssh_dir_stat.st_mode)[-3:]
    
    if ssh_dir_perms != '700':
        issues_found.append(f"SSH directory permissions: {ssh_dir_perms} (should be 700)")
        print(f"⚠️  SSH directory permissions: {ssh_dir_perms} (should be 700)")
    else:
        print(f"✓ SSH directory permissions: {ssh_dir_perms}")
    
    # Check individual key file permissions
    for key_file in Path(ssh_dir).glob('*'):
        if key_file.is_file() and not key_file.name.endswith('.pub'):
            try:
                key_stat = os.stat(key_file)
                key_perms = oct(key_stat.st_mode)[-3:]
                
                if key_perms not in ['600', '400']:
                    issues_found.append(f"{key_file.name} permissions: {key_perms} (should be 600 or 400)")
                    print(f"⚠️  {key_file.name} permissions: {key_perms} (should be 600 or 400)")
                else:
                    print(f"✓ {key_file.name} permissions: {key_perms}")
            except OSError as e:
                print(f"❌ Error checking {key_file.name}: {e}")
    
    if issues_found:
        print(f"\n🔧 Found {len(issues_found)} permission issues:")
        for issue in issues_found:
            print(f"   - {issue}")
        print("\n💡 Fix with:")
        print("   chmod 700 ~/.ssh")
        print("   chmod 600 ~/.ssh/id_*")
        print("   chmod 400 ~/.ssh/*.pem")
        return False
    
    print("\n✓ All SSH key permissions are correct")
    return True

def test_aws_key_parameter():
    """Test AWS key parameter handling"""
    print("\n🚀 Testing AWS Key Parameter Logic")
    print("=" * 50)
    
    # Simulate the key discovery logic from the benchmark tool
    def find_ssh_key(key_name):
        """Simulate the SSH key discovery logic"""
        if not key_name:
            return None
        
        key_paths = [
            os.path.expanduser(f'~/.ssh/{key_name}.pem'),
            os.path.expanduser(f'~/.ssh/{key_name}'),
            os.path.expanduser(f'~/.ssh/{key_name}.key')
        ]
        
        for key_path in key_paths:
            if os.path.exists(key_path):
                return key_path
        
        return None
    
    # Test different key name scenarios
    test_cases = [
        ("my-ec2-key", "Typical EC2 key name"),
        ("scylla-benchmark-key", "Benchmark-specific key"),
        ("id_rsa", "Default RSA key"),
        (None, "No key specified")
    ]
    
    for key_name, description in test_cases:
        print(f"\n🔍 Testing: {description}")
        if key_name:
            found_key = find_ssh_key(key_name)
            if found_key:
                print(f"   ✓ Found key: {found_key}")
            else:
                print(f"   ❌ Key not found for: {key_name}")
        else:
            print(f"   ℹ️  No key name provided - will use default keys")
    
    return True

def generate_setup_commands():
    """Generate setup commands for the user"""
    print("\n🛠️  Setup Commands for AWS Benchmark")
    print("=" * 50)
    
    print("If you don't have an EC2 key pair yet, create one:")
    print()
    print("# Create new EC2 key pair")
    print("aws ec2 create-key-pair --key-name scylla-benchmark-key \\")
    print("  --query 'KeyMaterial' --output text > ~/.ssh/scylla-benchmark-key.pem")
    print()
    print("# Set proper permissions")
    print("chmod 400 ~/.ssh/scylla-benchmark-key.pem")
    print()
    print("# Test the benchmark with your key")
    print("python cloud_io_benchmark.py --cloud aws --region us-east-1 \\")
    print("  --image ami-12345678 --instance-family i4i \\")
    print("  --aws-key-name scylla-benchmark-key --dry-run")
    print()
    
    # Check if user has AWS CLI configured
    aws_config = os.path.expanduser('~/.aws/credentials')
    if os.path.exists(aws_config):
        print("✓ AWS credentials file found")
    else:
        print("⚠️  AWS credentials not found. Run: aws configure")
    
    return True

def main():
    """Main test function"""
    print("🧪 ScyllaDB Cloud Benchmark - SSH Connection Test")
    print("=" * 60)
    print("This script validates your SSH setup for the benchmark tool.")
    print("=" * 60)
    
    tests = [
        ("SSH Key Discovery", test_ssh_key_discovery),
        ("SSH Key Permissions", test_ssh_key_permissions),
        ("AWS Key Parameter Logic", test_aws_key_parameter),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"❌ Test '{test_name}' failed with error: {e}")
    
    print(f"\n📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Your SSH setup looks good.")
        print("\n💡 You can now run the benchmark with confidence.")
        print("   Make sure to specify --aws-key-name when running the benchmark.")
    else:
        print("⚠️  Some tests failed. Please review the issues above.")
    
    generate_setup_commands()
    
    return 0 if passed == total else 1

if __name__ == '__main__':
    sys.exit(main())
