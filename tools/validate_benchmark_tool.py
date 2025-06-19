#!/usr/bin/env python3

"""
Validation script for the Cloud I/O Benchmark tool
Tests key functionality without requiring actual cloud resources
"""

import sys
import os
import subprocess
import json
from pathlib import Path

def test_help_output():
    """Test that the tool shows help correctly"""
    print("🧪 Testing help output...")
    try:
        result = subprocess.run([
            sys.executable, "cloud_io_benchmark.py", "--help"
        ], capture_output=True, text=True, cwd=Path(__file__).parent)
        
        if result.returncode == 0:
            # Check for key features
            help_text = result.stdout
            checks = [
                ("--debug-live", "Live debug parameter"),
                ("--dry-run", "Dry run parameter"),
                ("--debug", "Debug parameter"),
                ("--cloud {aws,gcp,azure}", "Cloud provider options"),
                ("shows live output from instances", "Live debug description")
            ]
            
            for check, desc in checks:
                if check in help_text:
                    print(f"  ✅ {desc} found")
                else:
                    print(f"  ❌ {desc} missing")
                    return False
            return True
        else:
            print(f"  ❌ Help command failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"  ❌ Error running help: {e}")
        return False

def test_dry_run():
    """Test dry run functionality"""
    print("🧪 Testing dry run functionality...")
    try:
        result = subprocess.run([
            sys.executable, "cloud_io_benchmark.py",
            "--cloud", "aws",
            "--region", "us-east-1", 
            "--image", "ami-test123",
            "--instance-types", "i4i.xlarge",
            "--dry-run"
        ], capture_output=True, text=True, cwd=Path(__file__).parent)
        
        if result.returncode == 0:
            output = result.stdout + result.stderr
            checks = [
                ("Dry run - configuration:", "Dry run header"),
                ("Cloud: aws", "Cloud configuration"),
                ("Instance types: ['i4i.xlarge']", "Instance types"),
                ("Will test 1 instance types", "Instance count")
            ]
            
            for check, desc in checks:
                if check in output:
                    print(f"  ✅ {desc} found")
                else:
                    print(f"  ❌ {desc} missing in output: {output}")
                    return False
            return True
        else:
            print(f"  ❌ Dry run failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"  ❌ Error running dry run: {e}")
        return False

def test_debug_live_flag():
    """Test that the debug-live flag is accepted"""
    print("🧪 Testing debug-live flag...")
    try:
        result = subprocess.run([
            sys.executable, "cloud_io_benchmark.py",
            "--cloud", "aws",
            "--region", "us-east-1", 
            "--image", "ami-test123",
            "--instance-types", "i4i.xlarge",
            "--debug-live",
            "--dry-run"
        ], capture_output=True, text=True, cwd=Path(__file__).parent)
        
        if result.returncode == 0:
            print(f"  ✅ Debug-live flag accepted")
            return True
        else:
            print(f"  ❌ Debug-live flag rejected: {result.stderr}")
            return False
    except Exception as e:
        print(f"  ❌ Error testing debug-live flag: {e}")
        return False

def check_requirements():
    """Check if requirements.txt exists and contains expected dependencies"""
    print("🧪 Checking requirements.txt...")
    req_file = Path(__file__).parent / "requirements.txt"
    if not req_file.exists():
        print("  ❌ requirements.txt not found")
        return False
    
    requirements = req_file.read_text()
    expected_deps = ["boto3", "google-cloud-compute", "azure-identity", "PyYAML"]
    
    for dep in expected_deps:
        if dep in requirements:
            print(f"  ✅ {dep} found in requirements")
        else:
            print(f"  ❌ {dep} missing from requirements")
            return False
    
    return True

def check_code_structure():
    """Check key code structure elements"""
    print("🧪 Checking code structure...")
    
    benchmark_file = Path(__file__).parent / "cloud_io_benchmark.py"
    if not benchmark_file.exists():
        print("  ❌ cloud_io_benchmark.py not found")
        return False
    
    code = benchmark_file.read_text()
    
    checks = [
        ("DEBUG_LIVE_MODE", "Live debug mode variable"),
        ("_read_io_properties_file", "YAML file reading method"),
        ("asyncio.Semaphore", "Async concurrency fix"),
        ("io_properties.yaml", "YAML metrics parsing"),
        ("ssh_users = [", "Multi-user SSH authentication")
    ]
    
    for check, desc in checks:
        if check in code:
            print(f"  ✅ {desc} implemented")
        else:
            print(f"  ❌ {desc} missing")
            return False
    
    return True

def main():
    """Run all validation tests"""
    print("🚀 Validating ScyllaDB Cloud I/O Benchmark Tool")
    print("=" * 60)
    
    tests = [
        ("Requirements file", check_requirements),
        ("Code structure", check_code_structure),
        ("Help output", test_help_output),
        ("Dry run", test_dry_run),
        ("Debug-live flag", test_debug_live_flag)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}")
        if test_func():
            passed += 1
            print(f"  🎉 PASSED")
        else:
            print(f"  💥 FAILED")
    
    print("\n" + "=" * 60)
    print(f"📊 SUMMARY: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The benchmark tool is ready for use.")
        print("\n🚀 NEXT STEPS:")
        print("1. Install dependencies: pip install -r requirements.txt")
        print("2. Configure cloud credentials (AWS, GCP, or Azure)")
        print("3. Run with --debug-live to see real-time output")
        print("4. Try: python3 cloud_io_benchmark.py --cloud aws --region us-east-1 --image <ami-id> --instance-types i4i.xlarge --debug-live")
        return 0
    else:
        print("❌ Some tests failed. Please review the issues above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
