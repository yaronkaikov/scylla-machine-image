#!/usr/bin/env python3
"""
Test to reproduce and diagnose the i7i.xlarge empty values issue
"""

import sys
import os
import logging

# Add the tools directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_i7i_empty_values_issue():
    """Reproduce and diagnose the empty values issue with i7i.xlarge"""
    print("🔍 INVESTIGATING: i7i.xlarge Empty Values Issue")
    print("=" * 60)
    
    # Check current CSV results
    print("\n1. Checking current benchmark results...")
    try:
        with open('scylla_io_benchmark_results.csv', 'r') as f:
            content = f.read()
            print("   Current CSV content:")
            print("   " + "-" * 40)
            for line in content.strip().split('\n'):
                print(f"   {line}")
            print("   " + "-" * 40)
            
            # Check if values are actually empty
            lines = content.strip().split('\n')
            if len(lines) > 1:  # Has header + data
                data_line = lines[-1]  # Get last data line
                fields = data_line.split(',')
                
                print(f"\n   Analysis of last result:")
                print(f"   - Instance Type: {fields[1] if len(fields) > 1 else 'MISSING'}")
                print(f"   - Success: {fields[4] if len(fields) > 4 else 'MISSING'}")
                print(f"   - Read IOPS: {fields[6] if len(fields) > 6 else 'MISSING'}")
                print(f"   - Write IOPS: {fields[7] if len(fields) > 7 else 'MISSING'}")
                print(f"   - Read Bandwidth: {fields[8] if len(fields) > 8 else 'MISSING'}")
                print(f"   - Write Bandwidth: {fields[9] if len(fields) > 9 else 'MISSING'}")
                
                # Check for empty values
                empty_fields = []
                if len(fields) > 6 and (not fields[6] or fields[6].strip() == ''):
                    empty_fields.append('read_iops')
                if len(fields) > 7 and (not fields[7] or fields[7].strip() == ''):
                    empty_fields.append('write_iops')
                if len(fields) > 8 and (not fields[8] or fields[8].strip() == ''):
                    empty_fields.append('read_bandwidth')
                if len(fields) > 9 and (not fields[9] or fields[9].strip() == ''):
                    empty_fields.append('write_bandwidth')
                
                if empty_fields:
                    print(f"   ❌ FOUND EMPTY VALUES: {', '.join(empty_fields)}")
                    return True
                else:
                    print(f"   ✅ NO EMPTY VALUES FOUND - values look good!")
                    return False
            else:
                print("   ❌ No data rows found in CSV")
                return True
                
    except FileNotFoundError:
        print("   ❌ No results file found")
        return True
    except Exception as e:
        print(f"   ❌ Error reading results: {e}")
        return True

def test_dry_run_vs_real_benchmark():
    """Test if the issue is with dry-run vs real benchmark"""
    print("\n2. Testing dry-run vs real benchmark...")
    
    # Test dry-run
    print("   Testing dry-run mode:")
    try:
        result = os.system("python3 cloud_io_benchmark.py --cloud aws --instance-types i7i.xlarge --region us-east-1 --image ami-034fdf5e5bd47ceb0 --runs 1 --aws-key-name scylla-qa-ec2 --dry-run")
        if result == 0:
            print("   ✅ Dry-run completed successfully")
        else:
            print(f"   ❌ Dry-run failed with exit code {result}")
    except Exception as e:
        print(f"   ❌ Dry-run error: {e}")

def check_instance_availability():
    """Check if i7i.xlarge is available in the region"""
    print("\n3. Checking i7i.xlarge availability...")
    
    try:
        from cloud_io_benchmark import AWSProvider
        
        provider = AWSProvider('us-east-1', dry_run=False)
        
        # Check all i7i types
        i7i_types = provider.get_instance_types_by_family('i7i')
        print(f"   Available i7i types: {len(i7i_types)}")
        print(f"   Types: {i7i_types}")
        
        if 'i7i.xlarge' in i7i_types:
            print("   ✅ i7i.xlarge is available in the region")
        else:
            print("   ❌ i7i.xlarge is NOT available in us-east-1")
            
        # Check zone availability
        zones = provider._get_available_zones()
        print(f"   Available zones: {zones}")
        
        supported_zones = []
        for zone in zones[:3]:  # Test first 3 zones
            try:
                if provider._check_instance_type_support('i7i.xlarge', zone):
                    supported_zones.append(zone)
            except:
                pass
        
        print(f"   i7i.xlarge supported in zones: {supported_zones}")
        
    except Exception as e:
        print(f"   ❌ Error checking availability: {e}")

def main():
    """Main test function"""
    print("🎯 REPRODUCING: i7i.xlarge Empty Values Issue")
    print()
    
    # Test 1: Check if values are actually empty
    has_empty_values = test_i7i_empty_values_issue()
    
    # Test 2: Check instance availability
    check_instance_availability()
    
    # Test 3: Dry-run test
    test_dry_run_vs_real_benchmark()
    
    print("\n" + "=" * 60)
    if has_empty_values:
        print("🚨 CONFIRMED: Empty values issue found!")
        print()
        print("💡 Possible causes:")
        print("   • Instance creation/connection issues")
        print("   • ScyllaDB setup/configuration problems")
        print("   • I/O benchmark execution failures")
        print("   • YAML parsing/reading issues")
        print("   • SSH connectivity problems")
        print()
        print("🔧 Suggested next steps:")
        print("   • Run with --debug flag to see detailed logs")
        print("   • Check if instance actually gets created")
        print("   • Verify SSH connectivity and ScyllaDB status")
        print("   • Try a different instance type (i4i.xlarge)")
    else:
        print("✅ NO EMPTY VALUES FOUND")
        print("The benchmark appears to be working correctly.")
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
