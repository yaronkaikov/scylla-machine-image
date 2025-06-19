#!/usr/bin/env python3
"""
Quick diagnostic to understand why real i7i benchmark returns empty values
"""

import sys
import os
import asyncio

# Add the tools directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cloud_io_benchmark import AWSProvider, CloudBenchmarkRunner, InstanceConfig

async def diagnose_i7i_benchmark():
    """Diagnose why i7i benchmark returns empty values"""
    print("🔍 DIAGNOSING: i7i.xlarge benchmark empty values")
    print("=" * 60)
    
    try:
        # Create AWS provider (real mode, not dry-run)
        print("1. Creating AWS provider...")
        provider = AWSProvider('us-east-1', dry_run=False, key_name='scylla-qa-ec2')
        
        # Check if i7i.xlarge is available in any zones
        print("\n2. Checking i7i.xlarge availability across zones...")
        available_zones = provider._get_available_zones()
        print(f"   Available zones: {available_zones}")
        
        supported_zones = []
        for zone in available_zones:
            try:
                if provider._check_instance_type_support('i7i.xlarge', zone):
                    supported_zones.append(zone)
                    print(f"   ✅ i7i.xlarge supported in {zone}")
                else:
                    print(f"   ❌ i7i.xlarge NOT supported in {zone}")
            except Exception as e:
                print(f"   ❓ Error checking {zone}: {e}")
        
        print(f"\n   📊 Summary: i7i.xlarge supported in {len(supported_zones)}/{len(available_zones)} zones")
        print(f"   Supported zones: {supported_zones}")
        
        if not supported_zones:
            print("\n   🚨 PROBLEM: i7i.xlarge is not available in ANY zone in us-east-1!")
            print("   This could explain why the benchmark returns empty values.")
            return False
        
        # Test VPC configuration
        print("\n3. Testing VPC configuration...")
        try:
            config = InstanceConfig(
                instance_type='i7i.xlarge',
                image_id='ami-034fdf5e5bd47ceb0',
                instance_name='test-i7i-xlarge'
            )
            
            vpc_config = provider._get_vpc_configuration_with_zone_support(
                instance_type='i7i.xlarge'
            )
            print(f"   ✅ VPC config found: {vpc_config}")
            
        except Exception as e:
            print(f"   ❌ VPC configuration failed: {e}")
            return False
        
        # Test actual instance creation (but don't run the benchmark)
        print("\n4. Testing instance creation (will terminate immediately)...")
        try:
            instance_id = await provider.create_instance(config)
            print(f"   ✅ Instance created successfully: {instance_id}")
            
            # Immediately terminate to avoid costs
            print("   🧹 Terminating test instance...")
            await provider.terminate_instance(instance_id)
            print("   ✅ Test instance terminated")
            
        except Exception as e:
            print(f"   ❌ Instance creation failed: {e}")
            print(f"   This is likely the cause of empty benchmark values!")
            return False
        
        print("\n✅ All diagnostics passed!")
        print("The i7i.xlarge instance type should work for benchmarking.")
        return True
        
    except Exception as e:
        print(f"❌ Diagnostic failed: {e}")
        return False

async def main():
    """Main function"""
    print("🎯 DIAGNOSTIC: Why does i7i.xlarge benchmark return empty values?")
    print()
    
    success = await diagnose_i7i_benchmark()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 DIAGNOSIS COMPLETE: i7i.xlarge should work!")
        print()
        print("💡 If you're still getting empty values, the issue might be:")
        print("   • Network connectivity during SSH")
        print("   • ScyllaDB setup/installation issues")
        print("   • Timeout issues with the 3-minute limit")
        print("   • SSH key or security group problems")
    else:
        print("💥 DIAGNOSIS FAILED: Found issues with i7i.xlarge!")
        print()
        print("🔧 Possible solutions:")
        print("   • Try a different instance type (i4i.xlarge, i3en.xlarge)")
        print("   • Use a different region (us-west-2, eu-west-1)")
        print("   • Check AWS account limits for i7i instances")
    
    return 0 if success else 1

if __name__ == '__main__':
    sys.exit(asyncio.run(main()))
