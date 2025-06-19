#!/usr/bin/env python3

"""
Debug test to run a minimal benchmark and get detailed logging
This will help us understand what's happening with the YAML file reading
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add the current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from cloud_io_benchmark import CloudBenchmarkRunner

# Set up debug logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def run_debug_benchmark():
    """Run a minimal benchmark with full debug logging"""
    print("🔧 Running debug benchmark with full logging...")
    
    # Create minimal config for benchmark
    config = {
        'cloud': 'aws',
        'region': 'us-east-1',
        'instance_types': ['i4i.xlarge'],
        'image': 'ami-12345678',  # You'll need to replace this with a real AMI
        'runs': 1,
        'aws_key_name': 'scylla-qa-ec2',
        'max_concurrent': 1,
        'csv_file': 'debug_benchmark_results.csv',
        'debug': True
    }
    
    try:
        runner = CloudBenchmarkRunner(config)
        
        # Run just one instance to see what happens
        print("📊 Starting benchmark...")
        await runner.run_benchmark()
        print("✅ Benchmark completed!")
        
        # Read the results
        csv_path = Path('debug_benchmark_results.csv')
        if csv_path.exists():
            print("\n📋 CSV Results:")
            print(csv_path.read_text())
        else:
            print("❌ No CSV file generated")
            
    except Exception as e:
        print(f"❌ Benchmark failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🔍 ScyllaDB I/O Benchmark Debug Test")
    print("=" * 50)
    
    # Check if we can import everything needed
    try:
        import yaml
        print("✅ PyYAML available")
    except ImportError:
        print("❌ PyYAML not available - installing...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "PyYAML"])
        print("✅ PyYAML installed")
    
    # Run the debug test
    asyncio.run(run_debug_benchmark())
