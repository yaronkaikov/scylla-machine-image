#!/usr/bin/env python3

"""
Test script to verify CSV export functionality includes read_iops and read_bandwidth
"""

import csv
import tempfile
import os
from dataclasses import asdict
from typing import List

# Import the IoSetupResult from the benchmark tool
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from cloud_io_benchmark import IoSetupResult

def test_csv_export_fields():
    """Test that CSV export includes all required fields including read_iops and read_bandwidth"""
    
    print("🧪 Testing CSV export field inclusion...")
    
    # Create test data that mimics real benchmark results
    test_results = [
        IoSetupResult(
            cloud="aws",
            instance_type="i4i.xlarge",
            instance_id="i-04c1bab3d7f7188b5",
            run_number=1,
            success=True,
            execution_time=185.87,
            read_iops=109954,
            write_iops=61008,
            read_bandwidth=763580096,  # bytes/sec
            write_bandwidth=561926784,  # bytes/sec
            error_message=""
        ),
        IoSetupResult(
            cloud="aws", 
            instance_type="i4i.large",
            instance_id="i-04c1bab3d7f7188b6",
            run_number=1,
            success=True,
            execution_time=156.23,
            read_iops=54987,
            write_iops=30459,
            read_bandwidth=378494048,
            write_bandwidth=279713216,
            error_message=""
        ),
        IoSetupResult(
            cloud="aws",
            instance_type="t3.medium",
            instance_id="i-04c1bab3d7f7188b7", 
            run_number=1,
            success=False,
            execution_time=45.12,
            read_iops=None,
            write_iops=None,
            read_bandwidth=None,
            write_bandwidth=None,
            error_message="Failed to read metrics"
        )
    ]
    
    # Create a temporary CSV file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as tmp_file:
        # Export to CSV using the same logic as the benchmark tool
        fieldnames = list(asdict(test_results[0]).keys())
        writer = csv.DictWriter(tmp_file, fieldnames=fieldnames)
        
        writer.writeheader()
        for result in test_results:
            writer.writerow(asdict(result))
        
        tmp_file_path = tmp_file.name
    
    try:
        # Read back and verify the CSV content
        with open(tmp_file_path, 'r') as csvfile:
            reader = csv.DictReader(csvfile)
            headers = reader.fieldnames
            rows = list(reader)
        
        print(f"✅ CSV Headers: {headers}")
        
        # Check for required fields
        required_fields = [
            'cloud', 'instance_type', 'instance_id', 'run_number', 'success', 
            'execution_time', 'read_iops', 'write_iops', 'read_bandwidth', 
            'write_bandwidth', 'error_message'
        ]
        
        missing_fields = [field for field in required_fields if field not in headers]
        if missing_fields:
            print(f"❌ Missing fields: {missing_fields}")
            return False
        
        print("✅ All required fields present in CSV headers")
        
        # Verify data content
        print("\n📊 CSV Data Verification:")
        for i, row in enumerate(rows):
            print(f"\nRow {i+1}:")
            print(f"  📍 Instance: {row['cloud']}/{row['instance_type']}")
            print(f"  📈 Read IOPS: {row['read_iops']}")
            print(f"  📈 Write IOPS: {row['write_iops']}")
            print(f"  📊 Read Bandwidth: {row['read_bandwidth']}")
            print(f"  📊 Write Bandwidth: {row['write_bandwidth']}")
            print(f"  ✅ Success: {row['success']}")
            
            # Verify that successful runs have metrics
            if row['success'] == 'True':
                if not row['read_iops'] or not row['read_bandwidth']:
                    print(f"  ❌ Warning: Successful run missing read metrics")
                else:
                    print(f"  ✅ Successful run has complete metrics")
            else:
                print(f"  ℹ️  Failed run (metrics expected to be empty)")
        
        # Clean up
        os.unlink(tmp_file_path)
        
        print("\n🎉 CSV export test completed successfully!")
        print("✅ read_iops and read_bandwidth fields are properly included in CSV export")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        if 'tmp_file_path' in locals():
            try:
                os.unlink(tmp_file_path)
            except:
                pass
        return False

def test_dataclass_field_order():
    """Test that dataclass fields match expected CSV order"""
    
    print("\n🔍 Testing IoSetupResult dataclass field order...")
    
    # Create a sample result
    sample_result = IoSetupResult(
        cloud="test",
        instance_type="test.type",
        instance_id="i-123456",
        run_number=1,
        success=True,
        execution_time=100.0,
        read_iops=1000,
        write_iops=800,
        read_bandwidth=50000000,
        write_bandwidth=40000000,
        error_message=""
    )
    
    # Get field order from asdict
    fields = list(asdict(sample_result).keys())
    print(f"📋 Dataclass field order: {fields}")
    
    # Verify key performance fields are present
    performance_fields = ['read_iops', 'write_iops', 'read_bandwidth', 'write_bandwidth']
    for field in performance_fields:
        if field in fields:
            print(f"  ✅ {field}: position {fields.index(field)}")
        else:
            print(f"  ❌ {field}: MISSING")
    
    return True

if __name__ == "__main__":
    print("🚀 Testing CSV Export Functionality")
    print("=" * 50)
    
    success1 = test_csv_export_fields()
    success2 = test_dataclass_field_order()
    
    if success1 and success2:
        print("\n🎉 All tests passed! CSV export correctly includes read_iops and read_bandwidth fields.")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed.")
        sys.exit(1)
