#!/bin/bash

# ScyllaDB Cloud I/O Benchmark - Example Usage Script
# This script demonstrates various ways to use the cloud benchmark tool

set -e

echo "🚀 ScyllaDB Cloud I/O Benchmark - Example Usage"
echo "================================================"
echo

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BENCHMARK_SCRIPT="$SCRIPT_DIR/cloud_io_benchmark.py"

# Check if the benchmark script exists
if [[ ! -f "$BENCHMARK_SCRIPT" ]]; then
    echo "❌ Error: cloud_io_benchmark.py not found in $SCRIPT_DIR"
    exit 1
fi

echo "📋 Available examples:"
echo "  1. Test configuration (dry-run)"
echo "  2. Quick single instance test"
echo "  3. Instance family comparison"
echo "  4. Multi-cloud comparison"
echo "  5. Custom instance selection"
echo

# Example 1: Test Configuration (Dry Run)
echo "1️⃣  Testing Configuration (Dry Run)"
echo "-----------------------------------"
echo "This tests your configuration without creating any instances or requiring credentials."
echo

echo "🔹 AWS i4i family dry-run:"
python3 "$BENCHMARK_SCRIPT" \
  --cloud aws \
  --region us-east-1 \
  --image ami-0a123456789abcdef \
  --instance-family i4i \
  --dry-run
echo

echo "🔹 GCP n2 family dry-run:"
python3 "$BENCHMARK_SCRIPT" \
  --cloud gcp \
  --region us-central1 \
  --project-id my-scylla-project \
  --image projects/scylla-images/global/images/scylladb-5-4-0 \
  --instance-family n2 \
  --dry-run
echo

echo "🔹 Azure L8s_v3 family dry-run:"
python3 "$BENCHMARK_SCRIPT" \
  --cloud azure \
  --region eastus \
  --subscription-id 12345678-1234-1234-1234-123456789012 \
  --image /subscriptions/12345678-1234-1234-1234-123456789012/resourceGroups/scylla-images/providers/Microsoft.Compute/galleries/scylla/images/scylladb/versions/5.4.0 \
  --instance-family L8s_v3 \
  --dry-run
echo

# Show help for reference
echo "📖 For more options, see the help:"
echo "python3 $BENCHMARK_SCRIPT --help"
echo

# Example usage commands (commented out since they require credentials)
cat << 'EOF'
2️⃣  Quick Single Instance Test
------------------------------
# Test a single instance type with minimal runs (requires credentials)

# AWS example:
# python3 cloud_io_benchmark.py \
#   --cloud aws \
#   --region us-east-1 \
#   --image ami-0a123456789abcdef \
#   --instance-types i4i.large \
#   --runs 1 \
#   --output-csv aws_quick_test.csv

3️⃣  Instance Family Comparison
-------------------------------
# Compare all instances in a family (requires credentials)

# AWS i4i family benchmark:
# python3 cloud_io_benchmark.py \
#   --cloud aws \
#   --region us-east-1 \
#   --image ami-0a123456789abcdef \
#   --instance-family i4i \
#   --runs 3 \
#   --max-concurrent 2 \
#   --output-csv aws_i4i_benchmark.csv

# GCP n2 family benchmark:
# python3 cloud_io_benchmark.py \
#   --cloud gcp \
#   --region us-central1 \
#   --project-id my-scylla-project \
#   --image projects/scylla-images/global/images/scylladb-5-4-0 \
#   --instance-family n2 \
#   --runs 3 \
#   --output-csv gcp_n2_benchmark.csv

4️⃣  Multi-Cloud Comparison
--------------------------
# Compare similar instances across cloud providers (requires credentials for all)

# Run these commands in parallel or sequence to compare:
# AWS:
# python3 cloud_io_benchmark.py --cloud aws --region us-east-1 --image ami-xxx --instance-types i4i.large i4i.xlarge --runs 3 --output-csv aws_comparison.csv

# GCP:
# python3 cloud_io_benchmark.py --cloud gcp --region us-central1 --project-id xxx --image projects/scylla-images/global/images/xxx --instance-types n2-standard-4 n2-standard-8 --runs 3 --output-csv gcp_comparison.csv

# Azure:
# python3 cloud_io_benchmark.py --cloud azure --region eastus --subscription-id xxx --image /subscriptions/xxx --instance-types Standard_L8s_v3 --runs 3 --output-csv azure_comparison.csv

5️⃣  Custom Instance Selection
-----------------------------
# Test specific instance types for detailed analysis (requires credentials)

# Mixed AWS instance types:
# python3 cloud_io_benchmark.py \
#   --cloud aws \
#   --region us-east-1 \
#   --image ami-0a123456789abcdef \
#   --instance-types i4i.large i4i.xlarge i3en.large i3en.xlarge \
#   --runs 3 \
#   --max-concurrent 2 \
#   --output-csv aws_mixed_instances.csv

📊 Analysis Examples
-------------------
# After running benchmarks, you can analyze the CSV results:

# View results in a spreadsheet application:
# open aws_i4i_benchmark.csv

# Quick command-line analysis:
# echo "Top performing instances by Read IOPS:"
# sort -t',' -k7 -nr aws_i4i_benchmark.csv | head -5

# echo "Average execution time by instance type:"
# awk -F',' 'NR>1 {sum[$2]+=$6; count[$2]++} END {for(i in sum) print i": "sum[i]/count[i]"s"}' aws_i4i_benchmark.csv

🔧 Troubleshooting
------------------
# If you get credential errors:
# 1. Run with --dry-run first to test configuration
# 2. Set up credentials:
#    - AWS: aws configure
#    - GCP: gcloud auth login && gcloud config set project PROJECT_ID
#    - Azure: az login
# 3. See CREDENTIALS_SETUP.md for detailed instructions

# If you get permission errors:
# - Ensure your credentials have the required permissions (see CREDENTIALS_SETUP.md)
# - Test with cloud provider CLI tools first

# For debugging:
# - Add --debug flag for detailed logging
# - Check cloud_io_benchmark.log file
# - Start with smaller runs (--runs 1, single instance type)

🎯 Best Practices
-----------------
# 1. Start with dry-run to validate configuration
# 2. Test with single instance first
# 3. Use appropriate regions (closer to your location)
# 4. Limit concurrent instances to avoid quotas (--max-concurrent 2)
# 5. Clean up is automatic, but monitor cloud console
# 6. Consider costs - use smaller instances for testing
EOF

echo
echo "✅ Example script completed!"
echo "💡 Uncomment and modify the examples above to run actual benchmarks"
echo "📚 See README_cloud_benchmark.md and CREDENTIALS_SETUP.md for more information"
