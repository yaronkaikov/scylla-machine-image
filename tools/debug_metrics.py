#!/usr/bin/env python3

"""
Diagnostic script to test the metrics parsing fix.
This script will help debug why the YAML file reading isn't working.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add the current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

# Set up logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_yaml_parsing():
    """Test YAML parsing with sample data"""
    print("🧪 Testing YAML parsing logic...")
    
    # Sample YAML content from scylla_cloud_io_setup
    sample_yaml = """disks:
- mountpoint: /var/lib/scylla
  read_iops: 109954
  read_bandwidth: 763580096
  write_iops: 61008
  write_bandwidth: 561926784"""
    
    try:
        import yaml
        parsed = yaml.safe_load(sample_yaml)
        print(f"✅ YAML parsing works: {parsed}")
        
        if parsed and 'disks' in parsed and parsed['disks']:
            disk_props = parsed['disks'][0]
            read_iops = disk_props.get('read_iops')
            write_iops = disk_props.get('write_iops')
            print(f"✅ Extracted read_iops: {read_iops}")
            print(f"✅ Extracted write_iops: {write_iops}")
        else:
            print("❌ YAML structure unexpected")
            
    except ImportError:
        print("❌ PyYAML not available")
    except Exception as e:
        print(f"❌ YAML parsing failed: {e}")

def analyze_csv_result():
    """Analyze the CSV result from the benchmark"""
    print("\n📊 Analyzing your CSV result...")
    
    csv_data = """cloud,instance_type,instance_id,run_number,success,execution_time,read_iops,write_iops,read_bandwidth,write_bandwidth,error_message
aws,i4i.xlarge,i-04c1bab3d7f7188b5,1,True,185.86745691299438,,,,,"""
    
    lines = csv_data.strip().split('\n')
    headers = lines[0].split(',')
    data = lines[1].split(',')
    
    result = dict(zip(headers, data))
    
    print("📋 Parsed CSV data:")
    for key, value in result.items():
        status = "✅" if value and value != "" else "❌"
        print(f"   {status} {key}: '{value}'")
    
    print(f"\n🔍 Analysis:")
    print(f"   - Command succeeded: {result['success'] == 'True'}")
    print(f"   - Execution time: {result['execution_time']} seconds")
    print(f"   - Instance ID: {result['instance_id']}")
    print(f"   - Metrics missing: ALL IOPS and bandwidth values are empty")
    
def suggest_debugging_steps():
    """Suggest debugging steps"""
    print("\n🔧 Debugging Steps:")
    
    print("\n1. **Manual SSH Test** - Check if YAML file exists:")
    print("   ssh -i ~/.ssh/scylla-qa-ec2 scyllaadm@INSTANCE_IP")
    print("   sudo cat /etc/scylla.d/io_properties.yaml")
    print("   # Check if the file exists and has the expected format")
    
    print("\n2. **Check Script Output** - See what scylla_cloud_io_setup actually does:")
    print("   ssh -i ~/.ssh/scylla-qa-ec2 scyllaadm@INSTANCE_IP")
    print("   sudo /opt/scylladb/scylla-machine-image/scylla_cloud_io_setup")
    print("   echo 'Exit code:' $?")
    print("   sudo cat /etc/scylla.d/io_properties.yaml")
    
    print("\n3. **Check Instance Type Support**:")
    print("   # Verify i4i.xlarge is supported in aws_io_params.yaml")
    print("   ssh -i ~/.ssh/scylla-qa-ec2 scyllaadm@INSTANCE_IP")
    print("   sudo cat /opt/scylladb/scylla-machine-image/aws_io_params.yaml | grep -A5 -B5 i4i.xlarge")
    
    print("\n4. **Debug Benchmark Tool** - Add debug logging:")
    print("   python3 cloud_io_benchmark.py --cloud aws --region us-east-1 \\")
    print("     --image ami-12345678 --instance-types i4i.xlarge \\")
    print("     --aws-key-name scylla-qa-ec2 --runs 1 --debug")
    
    print("\n5. **Test with Different Instance Type**:")
    print("   # Try with a different AWS instance type that's definitely supported")
    print("   python3 cloud_io_benchmark.py --cloud aws --region us-east-1 \\")
    print("     --image ami-12345678 --instance-types i3.large \\")
    print("     --aws-key-name scylla-qa-ec2 --runs 1")

def check_aws_params():
    """Check if i4i.xlarge is in the AWS params file"""
    print("\n📋 Checking AWS I/O parameters...")
    
    aws_params_path = "/Users/yaronkaikov/git/scylla-machine-image/common/aws_io_params.yaml"
    
    try:
        with open(aws_params_path, 'r') as f:
            content = f.read()
            
        if 'i4i.xlarge:' in content:
            print("✅ i4i.xlarge found in aws_io_params.yaml")
            # Extract the parameters
            lines = content.split('\n')
            in_i4i_xlarge = False
            params = []
            
            for line in lines:
                if line.startswith('i4i.xlarge:'):
                    in_i4i_xlarge = True
                    params.append(line)
                elif in_i4i_xlarge and line.startswith('  '):
                    params.append(line)
                elif in_i4i_xlarge and not line.startswith('  '):
                    break
            
            print("📊 Expected metrics for i4i.xlarge:")
            for param in params:
                print(f"   {param}")
                
        else:
            print("❌ i4i.xlarge NOT found in aws_io_params.yaml")
            print("   This might explain why no metrics are generated!")
            
    except FileNotFoundError:
        print(f"❌ AWS params file not found: {aws_params_path}")
    except Exception as e:
        print(f"❌ Error reading AWS params: {e}")

if __name__ == "__main__":
    print("🔍 ScyllaDB I/O Benchmark Metrics Diagnostic")
    print("=" * 50)
    
    test_yaml_parsing()
    analyze_csv_result()
    check_aws_params()
    suggest_debugging_steps()
    
    print("\n🎯 **Most Likely Issues:**")
    print("1. YAML file doesn't exist (script failed silently)")
    print("2. Instance terminated before we could read the file")
    print("3. i4i.xlarge not in aws_io_params.yaml")
    print("4. SSH permission issue reading /etc/scylla.d/")
    print("\n💡 Start with the manual SSH test to see what's actually happening!")
