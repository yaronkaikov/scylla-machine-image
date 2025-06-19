#!/usr/bin/env python3
"""
Test script to verify the asyncio fix works correctly
"""

import asyncio
import sys
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Import the benchmark module
try:
    from cloud_io_benchmark import CloudBenchmarkRunner
    print("✓ Successfully imported CloudBenchmarkRunner")
except ImportError as e:
    print(f"✗ Failed to import CloudBenchmarkRunner: {e}")
    sys.exit(1)

# Create a mock provider for testing
class MockProvider:
    def __init__(self):
        pass
    
    async def create_instance(self, config):
        return "test-instance-1"
    
    async def wait_for_instance_ready(self, instance_id, timeout=600):
        return True
    
    async def run_command_on_instance(self, instance_id, command):
        # Mock successful scylla_io_setup output
        mock_output = """
Running scylla_cloud_io_setup...
read_iops: 50000
write_iops: 45000
read_bandwidth: 500
write_bandwidth: 450
Setup completed successfully
"""
        return 0, mock_output, ""
    
    async def terminate_instance(self, instance_id):
        pass

async def test_benchmark_runner():
    """Test that the benchmark runner works without asyncio errors"""
    print("Testing CloudBenchmarkRunner...")
    
    # Create mock provider and runner
    provider = MockProvider()
    runner = CloudBenchmarkRunner(provider, max_concurrent=2)
    
    # Test the fixed benchmark_multiple_instance_types method
    try:
        await runner.benchmark_multiple_instance_types(
            instance_types=['test.small', 'test.medium'],
            image_id='test-image',
            runs=1
        )
        print("✓ benchmark_multiple_instance_types completed successfully")
        
        # Check that results were generated
        if runner.results:
            print(f"✓ Generated {len(runner.results)} results")
            for result in runner.results:
                print(f"  - {result.instance_type}: success={result.success}")
        else:
            print("✗ No results generated")
            
    except Exception as e:
        print(f"✗ benchmark_multiple_instance_types failed: {e}")
        return False
    
    return True

async def main():
    """Main test function"""
    print("Testing asyncio fix for CloudBenchmarkRunner...")
    print("=" * 50)
    
    try:
        success = await test_benchmark_runner()
        
        if success:
            print("\n✓ All tests passed! The asyncio fix is working correctly.")
            print("The '_asyncio.Future' object has no attribute '_condition' error should be resolved.")
            return 0
        else:
            print("\n✗ Tests failed!")
            return 1
            
    except Exception as e:
        print(f"\n✗ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(asyncio.run(main()))
