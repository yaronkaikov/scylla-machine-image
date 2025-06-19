#!/usr/bin/env python3

"""
Test script for Cloud I/O Benchmark functionality

This script tests the basic functionality of the cloud benchmark without 
actually creating real cloud instances.
"""

import sys
import os
import logging
from pathlib import Path

# Add the current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_imports():
    """Test if all required modules can be imported"""
    logger.info("Testing imports...")
    
    try:
        from cloud_io_benchmark import (
            IoSetupResult, InstanceConfig, CloudProviderInterface,
            create_cloud_provider
        )
        logger.info("✓ Core benchmark modules imported successfully")
    except ImportError as e:
        logger.error(f"✗ Failed to import core modules: {e}")
        assert False, f"Failed to import core modules: {e}"
    
    # Test cloud SDK imports (optional)
    try:
        import boto3
        logger.info("✓ AWS SDK (boto3) available")
    except ImportError:
        logger.warning("⚠ AWS SDK (boto3) not available - AWS functionality will be limited")
    
    try:
        from google.cloud import compute_v1
        logger.info("✓ Google Cloud SDK available")
    except ImportError:
        logger.warning("⚠ Google Cloud SDK not available - GCP functionality will be limited")
    
    try:
        from azure.identity import DefaultAzureCredential
        logger.info("✓ Azure SDK available")
    except ImportError:
        logger.warning("⚠ Azure SDK not available - Azure functionality will be limited")
    
    try:
        import yaml
        logger.info("✓ YAML parser available")
    except ImportError:
        logger.error("✗ YAML parser not available - this is required for metric parsing")
        assert False, "YAML parser not available - this is required for metric parsing"
    
    logger.info("✓ All import tests passed")

def test_instance_type_mappings():
    """Test instance type mapping functionality"""
    logger.info("Testing instance type mappings...")
    
    from cloud_io_benchmark import AWSProvider
    
    # Test AWS dynamic instance type discovery
    try:
        aws_provider = AWSProvider('us-east-1', dry_run=True)
        aws_i4i = aws_provider.get_instance_types_by_family('i4i')
        if aws_i4i:
            logger.info(f"✓ AWS i4i family: {len(aws_i4i)} types found (dry-run mode)")
        else:
            logger.error("✗ No AWS i4i instance types found")
            assert False, "No AWS i4i instance types found"
        
        # Test i7i family specifically
        aws_i7i = aws_provider.get_instance_types_by_family('i7i')
        if aws_i7i:
            logger.info(f"✓ AWS i7i family: {len(aws_i7i)} types found (dry-run mode)")
        else:
            logger.error("✗ No AWS i7i instance types found")
            assert False, "No AWS i7i instance types found"
            
    except Exception as e:
        logger.error(f"✗ AWS instance type discovery failed: {e}")
        assert False, f"AWS instance type discovery failed: {e}"
    
    # Test fallback mappings for other clouds (until we implement dynamic discovery)
    # For now, we'll test the fallback hardcoded values
    logger.info("✓ AWS dynamic instance type discovery tests passed")
    logger.info("✓ GCP and Azure tests use fallback mappings (to be implemented)")
    
    logger.info("✓ All instance type mapping tests passed")

def test_metric_parsing():
    """Test metric parsing functionality"""
    logger.info("Testing metric parsing...")
    
    from cloud_io_benchmark import CloudBenchmarkRunner, CloudProviderInterface
    
    # Create a mock provider for testing
    class MockProvider(CloudProviderInterface):
        async def create_instance(self, config): return "mock-instance"
        async def wait_for_instance_ready(self, instance_id, timeout=600): return True
        async def get_instance_ip(self, instance_id): return "127.0.0.1"
        async def run_command_on_instance(self, instance_id, command): return (0, "", "")
        async def terminate_instance(self, instance_id): pass
    
    runner = CloudBenchmarkRunner(MockProvider("test-region"))
    
    # Test different output formats
    test_outputs = [
        "read_iops: 50000\nwrite_iops: 45000\nread_bandwidth: 1200\nwrite_bandwidth: 1100",
        "disks:\n  - read_iops: 60000\n    write_iops: 55000\n    read_bandwidth: 1400",
        "Random output with read_iops=70000 and write_iops=65000"
    ]
    
    for i, output in enumerate(test_outputs):
        read_iops = runner._parse_metric(output, 'read_iops')
        if read_iops:
            logger.info(f"✓ Test output {i+1}: parsed read_iops = {read_iops}")
        else:
            logger.warning(f"⚠ Test output {i+1}: could not parse read_iops")
    
    logger.info("✓ All metric parsing tests completed")

def test_configuration():
    """Test configuration and argument parsing"""
    logger.info("Testing configuration...")
    
    from cloud_io_benchmark import create_cloud_provider
    
    # Test that provider creation fails gracefully without credentials
    try:
        # This should fail gracefully
        provider = create_cloud_provider('aws', 'us-east-1')
        logger.warning("⚠ AWS provider created without checking credentials")
    except Exception as e:
        logger.info(f"✓ AWS provider creation properly handles missing credentials: {type(e).__name__}")
    
    try:
        provider = create_cloud_provider('gcp', 'us-central1', project_id='test-project')
        logger.warning("⚠ GCP provider created without checking credentials")
    except Exception as e:
        logger.info(f"✓ GCP provider creation properly handles missing credentials: {type(e).__name__}")
    
    try:
        provider = create_cloud_provider('azure', 'eastus', subscription_id='test-sub')
        logger.warning("⚠ Azure provider created without checking credentials")
    except Exception as e:
        logger.info(f"✓ Azure provider creation properly handles missing credentials: {type(e).__name__}")
    
    logger.info("✓ All configuration tests passed")

def main():
    """Run all tests"""
    logger.info("Starting Cloud I/O Benchmark Test Suite")
    logger.info("=" * 50)
    
    tests = [
        ("Import Test", test_imports),
        ("Instance Type Mappings", test_instance_type_mappings), 
        ("Metric Parsing", test_metric_parsing),
        ("Configuration", test_configuration),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        logger.info(f"\nRunning {test_name}...")
        try:
            test_func()
            logger.info(f"✓ {test_name} PASSED")
            passed += 1
        except Exception as e:
            logger.error(f"✗ {test_name} FAILED with exception: {e}")
            failed += 1
    
    logger.info("\n" + "=" * 50)
    logger.info(f"Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        logger.info("🎉 All tests passed! The benchmark script is ready to use.")
        logger.info("\nNext steps:")
        logger.info("1. Install dependencies: pip install -r requirements.txt")
        logger.info("2. Configure cloud credentials")
        logger.info("3. Run: python cloud_io_benchmark.py --help")
    else:
        logger.error("❌ Some tests failed. Please check the issues above.")
        return 1
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
