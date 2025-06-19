#!/usr/bin/env python3

"""
Demo script showing the new --debug-live feature
"""

import sys
from pathlib import Path

def main():
    print("🔍 ScyllaDB Cloud I/O Benchmark - Live Debug Feature Demo")
    print("=" * 60)
    
    print("\n📚 USAGE EXAMPLES:")
    
    print("\n1️⃣  Basic debug mode (shows logs after completion):")
    print("   python3 cloud_io_benchmark.py \\")
    print("     --cloud aws \\")
    print("     --region us-east-1 \\")
    print("     --image ami-12345678 \\")
    print("     --instance-types i4i.xlarge \\")
    print("     --aws-key-name my-key \\")
    print("     --debug")
    
    print("\n2️⃣  NEW: Live debug mode (shows real-time output):")
    print("   python3 cloud_io_benchmark.py \\")
    print("     --cloud aws \\")
    print("     --region us-east-1 \\")
    print("     --image ami-12345678 \\")
    print("     --instance-types i4i.xlarge \\")
    print("     --aws-key-name my-key \\")
    print("     --debug-live")
    
    print("\n🔴 WHAT YOU'LL SEE WITH --debug-live:")
    print("   🔴 LIVE OUTPUT from i-04c1bab3d7f7188b5 (scyllaadm@1.2.3.4):")
    print("   " + "=" * 60)
    print("   📟 Starting ScyllaDB Cloud I/O Setup...")
    print("   📟 Checking instance type: i4i.xlarge")
    print("   📟 Found 1 NVMe devices")
    print("   📟 Reading AWS I/O parameters...")
    print("   📟 Instance type i4i.xlarge found in parameters")
    print("   📟 Calculating metrics for 1 disk(s)")
    print("   📟   read_iops: 109954")
    print("   📟   read_bandwidth: 763580096")
    print("   📟   write_iops: 61008")
    print("   📟   write_bandwidth: 561926784")
    print("   📟 Writing metrics to /etc/scylla.d/io_properties.yaml")
    print("   📟 Setup completed successfully")
    print("   " + "=" * 60)
    print("   🔴 LIVE OUTPUT COMPLETE (return code: 0)")
    
    print("\n💡 TIPS:")
    print("   • Use --max-concurrent 1 with --debug-live to avoid mixed output")
    print("   • Perfect for troubleshooting when metrics come back empty")
    print("   • Great for understanding what the I/O setup script actually does")
    print("   • Works with all cloud providers (AWS, GCP, Azure)")
    
    print("\n🚀 Try it now to see your ScyllaDB instances come to life!")

if __name__ == "__main__":
    main()
