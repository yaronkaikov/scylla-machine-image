#!/usr/bin/env python3
"""
Quick test to check actual i7i instance count from AWS API
"""

import sys
import os

# Add the tools directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def main():
    try:
        from cloud_io_benchmark import AWSProvider
        
        print("🔍 Testing i7i instance type discovery...")
        
        # Test 1: Dry-run mode
        print("\n1. DRY-RUN mode:")
        provider_dry = AWSProvider('us-east-1', dry_run=True)
        i7i_dry = provider_dry.get_instance_types_by_family('i7i')
        print(f"   Result: {len(i7i_dry)} types: {i7i_dry}")
        
        # Test 2: Real AWS API (but limit the region test)
        print("\n2. REAL AWS API (us-east-1):")
        provider_real = AWSProvider('us-east-1', dry_run=False)
        i7i_real = provider_real.get_instance_types_by_family('i7i')
        print(f"   Result: {len(i7i_real)} types")
        print(f"   Types: {i7i_real}")
        
        # Analysis
        print(f"\n📊 ANALYSIS:")
        print(f"   Dry-run: {len(i7i_dry)} types (hardcoded samples)")
        print(f"   Real API: {len(i7i_real)} types (actual AWS data)")
        
        if len(i7i_real) < 11:
            print(f"\n❓ Why Only {len(i7i_real)} Types Instead of 11?")
            print("   Possible reasons:")
            print("   • Region-specific availability (not all i7i types in us-east-1)")
            print("   • Instance types in limited/preview status")
            print("   • Account-specific restrictions")
            print("   • API filtering based on some criteria")
            
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
