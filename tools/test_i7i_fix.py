#!/usr/bin/env python3
"""
Test script to verify that i7i instance family is now supported
"""

import sys
import os

# Add the tools directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cloud_io_benchmark import AWSProvider

def test_i7i_support():
    """Test that i7i instance family is now supported"""
    print("🔍 Testing i7i instance family support...")
    
    try:
        # Create AWS provider in dry-run mode to test instance discovery
        provider = AWSProvider('us-east-1', dry_run=True)
        
        # Test i7i family - should return sample data in dry-run mode
        i7i_instances = provider.get_instance_types_by_family('i7i')
        print(f"📋 Supported i7i instances (dry-run): {i7i_instances}")
        
        if i7i_instances:
            print(f"✅ SUCCESS: Found {len(i7i_instances)} i7i instance types")
            for instance in i7i_instances:
                print(f"  - {instance}")
                
            # In dry-run mode, should return sample types
            expected_sample = ['i7i.large', 'i7i.xlarge']
            if set(i7i_instances) == set(expected_sample):
                print("✅ Dry-run mode returns expected sample instance types")
            else:
                print("❌ Instance types don't match expected dry-run values")
                return False
                
        else:
            print("❌ FAILED: No i7i instance types found")
            return False
        
        # Test that the method exists and works
        print(f"\n✅ SUCCESS: AWSProvider.get_instance_types_by_family() method is working")
        
        # Test with another family
        i4i_instances = provider.get_instance_types_by_family('i4i')
        print(f"📋 Supported i4i instances (dry-run): {i4i_instances}")
        
        if i4i_instances:
            print(f"✅ SUCCESS: i4i family also works with {len(i4i_instances)} instance types")
        else:
            print("❌ FAILED: i4i family support is broken")
            return False
            
        return True
        
    except Exception as e:
        print(f"❌ FAILED: Error testing instance type discovery: {e}")
        return False

if __name__ == '__main__':
    success = test_i7i_support()
    if success:
        print("\n🎉 All tests passed! i7i instance family is now supported.")
        sys.exit(0)
    else:
        print("\n💥 Tests failed!")
        sys.exit(1)
