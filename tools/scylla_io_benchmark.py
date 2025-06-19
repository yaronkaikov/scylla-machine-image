#!/usr/bin/env python3
"""
scylla_io_benchmark.py

Launches cloud instances for I/O benchmarking with ScyllaDB images.
Supports AWS (AMI) initially. Extendable for GCP/Azure.

Usage:
    python scylla_io_benchmark.py --region <region> --image-type <ami|gcp|azure> --image-name <image-id> [--instance-types <type1,type2,...> | --family <family>]

Example:
    python scylla_io_benchmark.py --region us-east-1 --image-type ami --image-name ami-12345678 --instance-types i3.large,i3.xlarge
    python scylla_io_benchmark.py --region us-east-1 --image-type ami --image-name ami-12345678 --family i3
"""
import argparse
import sys

# ...existing code for imports and argument parsing...

def main():
    parser = argparse.ArgumentParser(description="ScyllaDB I/O Benchmark Launcher")
    parser.add_argument('--region', required=True, help='Cloud region (e.g., us-east-1)')
    parser.add_argument('--image-type', required=True, choices=['ami', 'gcp', 'azure'], help='Image type (ami/gcp/azure)')
    parser.add_argument('--image-name', required=True, help='Image name or ID (e.g., AMI ID)')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--instance-types', help='Comma-separated list of instance types')
    group.add_argument('--family', help='Instance family (e.g., i3, i4g, i7i)')
    args = parser.parse_args()

    # ...existing code for launching instances, running scylla_io_setup, and reporting results...

if __name__ == "__main__":
    main()
