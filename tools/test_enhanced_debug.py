#!/usr/bin/env python3

"""
Enhanced test to run a single benchmark with detailed debugging
This will help us see exactly what's happening with the YAML file reading
"""

import asyncio
import logging
import sys
import os
from pathlib import Path

# Add the current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

# Set up detailed logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_test_config():
    """Create a minimal test configuration"""
    # You'll need to update these values for your AWS environment
    config = {
        'cloud': 'aws',
        'region': 'us-east-1',
        'instance_types': ['i4i.xlarge'],
        'image': 'ami-0abcdef1234567890',  # Replace with actual ScyllaDB AMI
        'runs': 1,
        'aws_key_name': 'scylla-qa-ec2',
        'max_concurrent': 1,
        'csv_file': 'test_enhanced_debug.csv',
        'debug': True,
        'debug_live': True  # Enable live output streaming!
    }
    
    # Check for required environment variables
    required_vars = ['AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY']
    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    
    if missing_vars:
        print(f"❌ Missing required environment variables: {missing_vars}")
        print("Please set your AWS credentials:")
        print("export AWS_ACCESS_KEY_ID=your_access_key")
        print("export AWS_SECRET_ACCESS_KEY=your_secret_key")
        return None
        
    return config

async def test_enhanced_debug():
    """Run a test with enhanced debugging"""
    print("🔧 Running enhanced debug test...")
    
    config = create_test_config()
    if not config:
        return
        
    try:
        from cloud_io_benchmark import CloudBenchmarkRunner
        
        print("✅ CloudBenchmarkRunner imported successfully")
        
        # Create runner with debug enabled
        runner = CloudBenchmarkRunner(config)
        
        print("📊 Starting benchmark...")
        await runner.run_benchmark()
        print("✅ Benchmark completed!")
        
        # Read the results
        csv_path = Path('test_enhanced_debug.csv')
        if csv_path.exists():
            print("\n📋 CSV Results:")
            content = csv_path.read_text()
            print(content)
            
            # Check if we got metrics this time
            lines = content.strip().split('\n')
            if len(lines) > 1:
                header = lines[0].split(',')
                data = lines[1].split(',')
                
                # Find metric columns
                metrics = ['read_iops', 'write_iops', 'read_bandwidth', 'write_bandwidth']
                for metric in metrics:
                    if metric in header:
                        idx = header.index(metric)
                        value = data[idx] if idx < len(data) else ''
                        if value and value != '':
                            print(f"✅ {metric}: {value}")
                        else:
                            print(f"❌ {metric}: empty")
        else:
            print("❌ No CSV file generated")
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🔍 ScyllaDB I/O Benchmark Enhanced Debug Test")
    print("=" * 50)
    
    # Check dependencies
    try:
        import yaml
        print("✅ PyYAML available")
    except ImportError:
        print("❌ PyYAML not available - installing...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "PyYAML"])
        print("✅ PyYAML installed")
    
    try:
        import boto3
        print("✅ boto3 available")
    except ImportError:
        print("❌ boto3 not available - installing...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "boto3"])
        print("✅ boto3 installed")
    
    # Run the test
    asyncio.run(test_enhanced_debug())
