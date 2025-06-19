#!/usr/bin/env python3

"""
End-to-end test to verify all fixes work together.
This creates a mock CSV with various edge cases and tests the analyzer.
"""

import csv
import tempfile
import os
from datetime import datetime

def create_test_csv():
    """Create a test CSV with various edge cases"""
    
    # Create a temporary CSV file
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False)
    
    # Write headers (same as the real benchmark tool)
    headers = [
        'timestamp', 'cloud', 'region', 'instance_type', 'image', 'run_number',
        'execution_time', 'success', 'error_message', 'read_iops', 'write_iops',
        'read_bandwidth', 'write_bandwidth', 'instance_cost_per_hour'
    ]
    
    writer = csv.writer(temp_file)
    writer.writerow(headers)
    
    # Test data with various edge cases
    test_data = [
        # Normal successful run
        ['2025-06-18T14:15:00', 'aws', 'us-east-1', 't3.medium', 'ami-12345678', '1',
         '120.5', 'True', '', '1000.0', '800.0', '50.0', '40.0', '0.042'],
        
        # Successful run with some None values (this was causing the statistics error)
        ['2025-06-18T14:16:00', 'aws', 'us-east-1', 't3.medium', 'ami-12345678', '2',
         '125.0', 'True', '', '', '850.0', '', '42.0', '0.042'],
        
        # Another run with different None pattern
        ['2025-06-18T14:17:00', 'aws', 'us-east-1', 't3.medium', 'ami-12345678', '3', 
         '118.0', 'True', '', '1100.0', '', '55.0', '', '0.042'],
        
        # Failed run
        ['2025-06-18T14:18:00', 'aws', 'us-east-1', 't3.large', 'ami-12345678', '1',
         '0', 'False', 'SSH connection failed', '', '', '', '', '0.084'],
        
        # Successful run for t3.large with all values
        ['2025-06-18T14:19:00', 'aws', 'us-east-1', 't3.large', 'ami-12345678', '2',
         '110.0', 'True', '', '1500.0', '1200.0', '75.0', '60.0', '0.084'],
        
        # Another t3.large run with mixed None values
        ['2025-06-18T14:20:00', 'aws', 'us-east-1', 't3.large', 'ami-12345678', '3',
         '115.0', 'True', '', '', '1100.0', '', '58.0', '0.084']
    ]
    
    for row in test_data:
        writer.writerow(row)
    
    temp_file.close()
    return temp_file.name

def test_analyzer():
    """Test the benchmark analyzer with edge case data"""
    print("🧪 Creating test CSV with edge cases...")
    csv_file = create_test_csv()
    print(f"📄 Created test file: {csv_file}")
    
    try:
        # Test the analyzer (this would previously fail with statistics errors)
        print("\n📊 Testing benchmark analyzer...")
        import subprocess
        result = subprocess.run([
            'python3', 'benchmark_analyzer.py', csv_file
        ], capture_output=True, text=True, cwd='/Users/yaronkaikov/git/scylla-machine-image/tools')
        
        if result.returncode == 0:
            print("✅ Benchmark analyzer completed successfully!")
            print("\n--- Analyzer Output ---")
            print(result.stdout)
        else:
            print("❌ Benchmark analyzer failed!")
            print("STDERR:", result.stderr)
            print("STDOUT:", result.stdout)
            
    finally:
        # Clean up
        os.unlink(csv_file)
        print(f"\n🧹 Cleaned up test file: {csv_file}")

if __name__ == "__main__":
    print("🚀 Running end-to-end test of all fixes...")
    test_analyzer()
    print("\n🎉 End-to-end test completed!")
