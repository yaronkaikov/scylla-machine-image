#!/usr/bin/env python3
"""
Test script to verify the dynamic timeout fix for i7i.xlarge instances.

This script tests the new dynamic timeout functionality that should resolve
the empty values issue for larger instance types like i7i.xlarge.
"""

import sys
import os
import asyncio
import time
from unittest.mock import Mock, AsyncMock

# Add the tools directory to the path
sys.path.insert(0, '/Users/yaronkaikov/git/scylla-machine-image/tools')

from cloud_io_benchmark import CloudProviderInterface, AWSProvider

def test_dynamic_timeout_calculation():
    """Test the dynamic timeout calculation for various instance types"""
    print("🧪 Testing dynamic timeout calculation...")
    
    # Create test provider
    provider = CloudProviderInterface("us-east-1")
    
    # Test cases: instance_type -> expected_timeout_range
    test_cases = [
        ("i7i.large", (180, 300)),      # 1.5x = 270s
        ("i7i.xlarge", (300, 400)),     # 2.0x = 360s  
        ("i7i.2xlarge", (400, 500)),    # 2.5x = 450s
        ("i7i.4xlarge", (500, 600)),    # 3.0x = 540s
        ("i7i.8xlarge", (600, 700)),    # 3.5x = 630s
        ("i7i.16xlarge", (700, 900)),   # 4.5x = 810s
        ("i7i.metal", (1200, 1500)),    # 8.0x = 1440s
        ("c7i.medium", (180, 250)),     # 1.2x = 216s
        ("m5.nano", (180, 200)),        # 1.0x = 180s
        ("unknown.type", (300, 400)),   # default 2.0x = 360s
    ]
    
    results = []
    for instance_type, (min_expected, max_expected) in test_cases:
        timeout = provider.get_instance_readiness_timeout(instance_type)
        passed = min_expected <= timeout <= max_expected
        results.append(passed)
        
        status = "✅" if passed else "❌"
        print(f"{status} {instance_type}: {timeout}s (expected {min_expected}-{max_expected}s)")
    
    success_rate = sum(results) / len(results) * 100
    print(f"\n📊 Dynamic timeout calculation: {success_rate:.1f}% tests passed")
    return all(results)

def test_i7i_xlarge_timeout():
    """Test specifically that i7i.xlarge gets sufficient timeout"""
    print("\n🎯 Testing i7i.xlarge timeout fix...")
    
    provider = CloudProviderInterface("us-east-1")
    timeout = provider.get_instance_readiness_timeout("i7i.xlarge")
    
    # i7i.xlarge should get 360 seconds (6 minutes) which is double the old 180s
    expected_min = 300  # At least 5 minutes
    expected_max = 400  # At most 6.67 minutes
    
    if expected_min <= timeout <= expected_max:
        print(f"✅ i7i.xlarge timeout: {timeout}s (sufficient for large instance)")
        return True
    else:
        print(f"❌ i7i.xlarge timeout: {timeout}s (should be {expected_min}-{expected_max}s)")
        return False

def test_timeout_progression():
    """Test that timeout increases appropriately with instance size"""
    print("\n📈 Testing timeout progression by instance size...")
    
    provider = CloudProviderInterface("us-east-1")
    
    # Test progression within i7i family
    sizes = ["large", "xlarge", "2xlarge", "4xlarge", "8xlarge", "16xlarge"]
    timeouts = []
    
    for size in sizes:
        instance_type = f"i7i.{size}"
        timeout = provider.get_instance_readiness_timeout(instance_type)
        timeouts.append(timeout)
        print(f"  i7i.{size}: {timeout}s")
    
    # Check that timeouts are increasing
    increasing = all(timeouts[i] <= timeouts[i+1] for i in range(len(timeouts)-1))
    
    if increasing:
        print("✅ Timeouts increase appropriately with instance size")
        return True
    else:
        print("❌ Timeouts do not increase properly with instance size")
        return False

def simulate_i7i_xlarge_benchmark():
    """Simulate the benchmark process for i7i.xlarge"""
    print("\n🚀 Simulating i7i.xlarge benchmark with new timeout...")
    
    provider = CloudProviderInterface("us-east-1")
    instance_type = "i7i.xlarge"
    
    # Get the dynamic timeout
    timeout = provider.get_instance_readiness_timeout(instance_type)
    
    print(f"📋 Benchmark simulation:")
    print(f"   Instance type: {instance_type}")
    print(f"   Dynamic timeout: {timeout}s ({timeout/60:.1f} minutes)")
    print(f"   Old timeout was: 180s (3.0 minutes)")
    print(f"   Improvement: +{timeout-180}s (+{(timeout-180)/60:.1f} minutes)")
    
    # Simulate a scenario where instance takes 5 minutes to be ready
    instance_ready_time = 300  # 5 minutes
    
    if timeout >= instance_ready_time:
        print(f"✅ SUCCESS: Instance ready in {instance_ready_time}s, timeout is {timeout}s")
        print("   This should resolve the empty values issue!")
        return True
    else:
        print(f"❌ FAILURE: Instance needs {instance_ready_time}s, but timeout is only {timeout}s")
        return False

def main():
    """Run all timeout tests"""
    print("🔧 Testing Dynamic Timeout Fix for i7i.xlarge Empty Values Issue")
    print("=" * 70)
    
    tests = [
        ("Dynamic timeout calculation", test_dynamic_timeout_calculation),
        ("i7i.xlarge specific timeout", test_i7i_xlarge_timeout),
        ("Timeout progression", test_timeout_progression),
        ("i7i.xlarge benchmark simulation", simulate_i7i_xlarge_benchmark),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append(result)
        except Exception as e:
            print(f"❌ {test_name} failed with error: {e}")
            results.append(False)
    
    print("\n" + "=" * 70)
    print("📊 SUMMARY:")
    
    passed = sum(results)
    total = len(results)
    
    for i, (test_name, _) in enumerate(tests):
        status = "✅ PASS" if results[i] else "❌ FAIL"
        print(f"   {status}: {test_name}")
    
    print(f"\n🎯 Overall: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("\n🎉 SUCCESS: Dynamic timeout fix should resolve i7i.xlarge empty values!")
        print("💡 The issue was that i7i.xlarge instances need more than 3 minutes to initialize.")
        print("   Now they get 6 minutes, which should be sufficient.")
        return 0
    else:
        print("\n❌ ISSUES: Some tests failed. The fix may need adjustments.")
        return 1

if __name__ == '__main__':
    sys.exit(main())
