#!/usr/bin/env python3
"""
Test to investigate why i7i shows only 3 instance types instead of the expected 11.
Let's check both dry-run mode and real AWS API calls.
"""

import sys
import os
import logging

# Add the tools directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cloud_io_benchmark import AWSProvider

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_i7i_dry_run_vs_real():
    """Test i7i instance discovery in both dry-run and real modes"""
    print("=" * 80)
    print("🔍 INVESTIGATING: i7i Instance Type Count")
    print("Expected: 11 i7i instance types according to AWS documentation")
    print("Reported: Only 3 instance types discovered")
    print("=" * 80)
    
    # 1. Test dry-run mode first
    print("\n1. Testing DRY-RUN mode:")
    try:
        provider_dry = AWSProvider('us-east-1', dry_run=True)
        i7i_dry = provider_dry.get_instance_types_by_family('i7i')
        print(f"   Dry-run result: {len(i7i_dry)} types: {i7i_dry}")
        
        # Check the dry-run implementation
        expected_dry = ['i7i.large', 'i7i.xlarge']
        if i7i_dry == expected_dry:
            print("   ✅ Dry-run mode returns expected hardcoded sample (2 types)")
        else:
            print(f"   ❓ Dry-run mode returned unexpected result: {i7i_dry}")
            
    except Exception as e:
        print(f"   ❌ Dry-run test failed: {e}")
        return False
    
    # 2. Test real AWS API call
    print("\n2. Testing REAL AWS API call:")
    try:
        provider_real = AWSProvider('us-east-1', dry_run=False)
        i7i_real = provider_real.get_instance_types_by_family('i7i')
        print(f"   Real API result: {len(i7i_real)} types: {i7i_real}")
        
        if len(i7i_real) == 11:
            print("   ✅ Found expected 11 i7i instance types!")
        elif len(i7i_real) == 3:
            print("   ❓ Found only 3 i7i instance types - investigating why...")
            
            # Let's check what we actually got
            print(f"   Found types: {', '.join(i7i_real)}")
            
            # Check if there might be a region-specific limitation
            print(f"   Region: us-east-1")
            print("   Possible causes:")
            print("   - Some i7i types might not be available in us-east-1")
            print("   - AWS API might be filtering based on account limits")
            print("   - Instance types might be in preview/limited availability")
            
        else:
            print(f"   ❓ Found {len(i7i_real)} i7i instance types (neither 3 nor 11)")
            
    except Exception as e:
        print(f"   ❌ Real API test failed: {e}")
        print(f"   This might be due to:")
        print(f"   - Missing AWS credentials")
        print(f"   - Insufficient permissions (need ec2:DescribeInstanceTypes)")
        print(f"   - Network connectivity issues")
        return False
    
    # 3. Test with multiple regions to see if it's region-specific
    print("\n3. Testing different regions:")
    regions_to_test = ['us-east-1', 'us-west-2', 'eu-west-1']
    
    for region in regions_to_test:
        try:
            provider = AWSProvider(region, dry_run=False)
            i7i_types = provider.get_instance_types_by_family('i7i')
            print(f"   {region}: {len(i7i_types)} types: {i7i_types}")
        except Exception as e:
            print(f"   {region}: Error - {e}")
    
    # 4. Compare with other instance families
    print("\n4. Testing other instance families for comparison:")
    families_to_test = ['i4i', 'i3en', 'c5', 'm5']
    
    try:
        provider = AWSProvider('us-east-1', dry_run=False)
        for family in families_to_test:
            try:
                types = provider.get_instance_types_by_family(family)
                print(f"   {family}: {len(types)} types")
            except Exception as e:
                print(f"   {family}: Error - {e}")
    except Exception as e:
        print(f"   Failed to test other families: {e}")
    
    print("\n" + "=" * 80)
    print("📊 ANALYSIS:")
    print("If dry-run shows 2 types but you're seeing 3, there might be:")
    print("1. A bug in the dry-run logic")
    print("2. Mixed results from different test runs")
    print("3. The count includes some other source")
    print()
    print("If real API shows fewer than 11 types, it could be:")
    print("1. Region-specific availability")
    print("2. Account-specific limits or restrictions")
    print("3. Instance types in preview/beta status")
    print("4. API filtering based on some criteria")
    print("=" * 80)
    
    return True

def main():
    """Main test function"""
    success = test_i7i_dry_run_vs_real()
    
    if success:
        print("\n🎯 Investigation completed successfully!")
        print("Check the output above to understand the i7i instance type count.")
        return 0
    else:
        print("\n💥 Investigation failed!")
        return 1

if __name__ == '__main__':
    sys.exit(main())
