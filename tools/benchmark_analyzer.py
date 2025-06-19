#!/usr/bin/env python3

"""
ScyllaDB Cloud Benchmark Results Analyzer

This script analyzes CSV results from the cloud_io_benchmark.py tool to provide 
detailed comparisons, visualizations, and recommendations.

Usage:
    python benchmark_analyzer.py results.csv
    python benchmark_analyzer.py --compare file1.csv file2.csv file3.csv
    python benchmark_analyzer.py --top-n 5 --metric read_iops results.csv
"""

import argparse
import csv
import json
import logging
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import statistics

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class BenchmarkResult:
    """Represents a single benchmark result"""
    def __init__(self, row: Dict[str, str]):
        self.cloud = row.get('cloud', '')
        self.instance_type = row.get('instance_type', '')
        self.instance_id = row.get('instance_id', '')
        self.run_number = int(row.get('run_number', 0))
        self.success = row.get('success', '').lower() == 'true'
        self.execution_time = float(row.get('execution_time', 0))
        self.read_iops = float(row.get('read_iops', 0)) if row.get('read_iops') else None
        self.write_iops = float(row.get('write_iops', 0)) if row.get('write_iops') else None
        self.read_bandwidth = float(row.get('read_bandwidth', 0)) if row.get('read_bandwidth') else None
        self.write_bandwidth = float(row.get('write_bandwidth', 0)) if row.get('write_bandwidth') else None
        self.error_message = row.get('error_message', '')

class BenchmarkAnalyzer:
    """Analyzes benchmark results from CSV files"""
    
    def __init__(self):
        self.results: List[BenchmarkResult] = []
        self.by_instance_type: Dict[str, List[BenchmarkResult]] = defaultdict(list)
        self.by_cloud: Dict[str, List[BenchmarkResult]] = defaultdict(list)
    
    def load_csv(self, csv_file: str) -> None:
        """Load benchmark results from CSV file"""
        try:
            with open(csv_file, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    result = BenchmarkResult(row)
                    self.results.append(result)
                    self.by_instance_type[result.instance_type].append(result)
                    self.by_cloud[result.cloud].append(result)
            
            logger.info(f"Loaded {len(self.results)} results from {csv_file}")
        except Exception as e:
            logger.error(f"Failed to load {csv_file}: {e}")
            sys.exit(1)
    
    def get_instance_stats(self, instance_type: str) -> Dict:
        """Get statistics for a specific instance type"""
        results = [r for r in self.by_instance_type[instance_type] if r.success]
        
        if not results:
            return {"success_rate": 0, "total_runs": len(self.by_instance_type[instance_type])}
        
        # Safe data extraction with empty list checks
        read_iops_values = [r.read_iops for r in results if r.read_iops is not None]
        write_iops_values = [r.write_iops for r in results if r.write_iops is not None]
        read_bw_values = [r.read_bandwidth for r in results if r.read_bandwidth is not None]
        write_bw_values = [r.write_bandwidth for r in results if r.write_bandwidth is not None]
        
        return {
            "success_rate": len(results) / len(self.by_instance_type[instance_type]) * 100,
            "total_runs": len(self.by_instance_type[instance_type]),
            "successful_runs": len(results),
            "avg_execution_time": statistics.mean([r.execution_time for r in results]),
            "std_execution_time": statistics.stdev([r.execution_time for r in results]) if len(results) > 1 else 0,
            "avg_read_iops": statistics.mean(read_iops_values) if read_iops_values else 0,
            "std_read_iops": statistics.stdev(read_iops_values) if len(read_iops_values) > 1 else 0,
            "avg_write_iops": statistics.mean(write_iops_values) if write_iops_values else 0,
            "std_write_iops": statistics.stdev(write_iops_values) if len(write_iops_values) > 1 else 0,
            "avg_read_bw": statistics.mean(read_bw_values) if read_bw_values else 0,
            "avg_write_bw": statistics.mean(write_bw_values) if write_bw_values else 0,
            "min_read_iops": min(read_iops_values, default=0),
            "max_read_iops": max(read_iops_values, default=0),
            "min_write_iops": min(write_iops_values, default=0),
            "max_write_iops": max(write_iops_values, default=0),
        }
    
    def print_detailed_analysis(self) -> None:
        """Print detailed analysis of all results"""
        print("\n" + "="*100)
        print("DETAILED BENCHMARK ANALYSIS")
        print("="*100)
        
        # Overall statistics
        total_results = len(self.results)
        successful_results = len([r for r in self.results if r.success])
        print(f"\n📊 Overall Statistics:")
        print(f"   Total test runs: {total_results}")
        print(f"   Successful runs: {successful_results} ({successful_results/total_results*100:.1f}%)")
        print(f"   Clouds tested: {len(self.by_cloud.keys())}")
        print(f"   Instance types tested: {len(self.by_instance_type.keys())}")
        
        # Cloud breakdown
        print(f"\n☁️ Results by Cloud Provider:")
        for cloud, results in self.by_cloud.items():
            successful = len([r for r in results if r.success])
            print(f"   {cloud.upper()}: {successful}/{len(results)} successful ({successful/len(results)*100:.1f}%)")
        
        # Instance type analysis
        print(f"\n🔧 Instance Type Analysis:")
        print(f"{'Instance Type':<25} {'Success Rate':<12} {'Avg Time':<10} {'Read IOPS':<12} {'Write IOPS':<12} {'Read BW':<10} {'Write BW':<10}")
        print("-" * 110)
        
        for instance_type in sorted(self.by_instance_type.keys()):
            stats = self.get_instance_stats(instance_type)
            if stats['successful_runs'] > 0:
                print(f"{instance_type:<25} {stats['success_rate']:>8.1f}%    {stats['avg_execution_time']:>8.1f}s   {stats['avg_read_iops']:>10.0f}   {stats['avg_write_iops']:>10.0f}   {stats['avg_read_bw']:>8.1f}   {stats['avg_write_bw']:>8.1f}")
            else:
                print(f"{instance_type:<25} {stats['success_rate']:>8.1f}%    {'N/A':<8}   {'N/A':<10}   {'N/A':<10}   {'N/A':<8}   {'N/A':<8}")
        
        print("\n" + "="*100)
    
    def print_rankings(self, top_n: int = 5) -> None:
        """Print performance rankings"""
        # Get all instance types with successful runs
        instance_stats = {}
        for instance_type in self.by_instance_type.keys():
            stats = self.get_instance_stats(instance_type)
            if stats['successful_runs'] > 0:
                instance_stats[instance_type] = stats
        
        if not instance_stats:
            print("No successful runs to rank")
            return
        
        print(f"\n🏆 TOP {top_n} PERFORMANCE RANKINGS")
        print("="*60)
        
        # Top by Read IOPS
        print(f"\n📈 Top {top_n} by Read IOPS:")
        top_read = sorted(instance_stats.items(), key=lambda x: x[1]['avg_read_iops'], reverse=True)[:top_n]
        for i, (instance_type, stats) in enumerate(top_read, 1):
            print(f"   {i}. {instance_type:<20} - {stats['avg_read_iops']:>10.0f} IOPS (±{stats['std_read_iops']:>6.0f})")
        
        # Top by Write IOPS
        print(f"\n📈 Top {top_n} by Write IOPS:")
        top_write = sorted(instance_stats.items(), key=lambda x: x[1]['avg_write_iops'], reverse=True)[:top_n]
        for i, (instance_type, stats) in enumerate(top_write, 1):
            print(f"   {i}. {instance_type:<20} - {stats['avg_write_iops']:>10.0f} IOPS (±{stats['std_write_iops']:>6.0f})")
        
        # Fastest execution
        print(f"\n⚡ Top {top_n} by Execution Speed:")
        fastest = sorted(instance_stats.items(), key=lambda x: x[1]['avg_execution_time'])[:top_n]
        for i, (instance_type, stats) in enumerate(fastest, 1):
            print(f"   {i}. {instance_type:<20} - {stats['avg_execution_time']:>8.2f}s (±{stats['std_execution_time']:>5.2f}s)")
        
        # Most reliable
        print(f"\n✅ Top {top_n} by Reliability:")
        most_reliable = sorted(instance_stats.items(), key=lambda x: x[1]['success_rate'], reverse=True)[:top_n]
        for i, (instance_type, stats) in enumerate(most_reliable, 1):
            print(f"   {i}. {instance_type:<20} - {stats['success_rate']:>6.1f}% success rate ({stats['successful_runs']}/{stats['total_runs']} runs)")
        
        print("\n" + "="*60)
    
    def compare_instance_types(self, instance_types: List[str]) -> None:
        """Compare specific instance types"""
        print(f"\n🔍 INSTANCE TYPE COMPARISON")
        print("="*80)
        
        valid_types = [t for t in instance_types if t in self.by_instance_type]
        if not valid_types:
            print("No valid instance types found for comparison")
            return
        
        print(f"\nComparing: {', '.join(valid_types)}")
        print("-" * 80)
        
        comparison_data = []
        for instance_type in valid_types:
            stats = self.get_instance_stats(instance_type)
            if stats['successful_runs'] > 0:
                comparison_data.append((instance_type, stats))
        
        if not comparison_data:
            print("No successful runs found for comparison")
            return
        
        # Print comparison table
        print(f"{'Metric':<20}", end='')
        for instance_type, _ in comparison_data:
            print(f"{instance_type:<15}", end='')
        print()
        print("-" * (20 + 15 * len(comparison_data)))
        
        metrics = [
            ('Success Rate (%)', 'success_rate', '.1f'),
            ('Avg Time (s)', 'avg_execution_time', '.2f'),
            ('Read IOPS', 'avg_read_iops', '.0f'),
            ('Write IOPS', 'avg_write_iops', '.0f'),
            ('Read BW (MB/s)', 'avg_read_bw', '.1f'),
            ('Write BW (MB/s)', 'avg_write_bw', '.1f'),
        ]
        
        for metric_name, metric_key, fmt in metrics:
            print(f"{metric_name:<20}", end='')
            for _, stats in comparison_data:
                value = stats.get(metric_key, 0)
                formatted_value = f"{value:{fmt}}"
                print(f"{formatted_value:>15}", end='')
            print()
        
        print("\n" + "="*80)
    
    def export_summary(self, output_file: str) -> None:
        """Export summary statistics to JSON"""
        summary = {
            "analysis_metadata": {
                "total_results": len(self.results),
                "successful_results": len([r for r in self.results if r.success]),
                "clouds_tested": list(self.by_cloud.keys()),
                "instance_types_tested": list(self.by_instance_type.keys())
            },
            "cloud_summary": {},
            "instance_type_summary": {}
        }
        
        # Cloud summary
        for cloud, results in self.by_cloud.items():
            successful = len([r for r in results if r.success])
            summary["cloud_summary"][cloud] = {
                "total_runs": len(results),
                "successful_runs": successful,
                "success_rate": successful / len(results) * 100 if results else 0
            }
        
        # Instance type summary
        for instance_type in self.by_instance_type.keys():
            stats = self.get_instance_stats(instance_type)
            summary["instance_type_summary"][instance_type] = stats
        
        with open(output_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        logger.info(f"Exported summary to {output_file}")

def main():
    parser = argparse.ArgumentParser(description='Analyze ScyllaDB cloud benchmark results')
    parser.add_argument('files', nargs='+', help='CSV result files to analyze')
    parser.add_argument('--compare', action='store_true', 
                       help='Compare multiple CSV files')
    parser.add_argument('--top-n', type=int, default=5,
                       help='Number of top performers to show (default: 5)')
    parser.add_argument('--metric', choices=['read_iops', 'write_iops', 'execution_time', 'success_rate'],
                       help='Primary metric for ranking')
    parser.add_argument('--instance-types', nargs='+',
                       help='Specific instance types to compare')
    parser.add_argument('--export-json', help='Export summary to JSON file')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    
    args = parser.parse_args()
    
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    if args.compare and len(args.files) < 2:
        logger.error("--compare requires at least 2 files")
        sys.exit(1)
    
    # Analyze single file
    if len(args.files) == 1 and not args.compare:
        analyzer = BenchmarkAnalyzer()
        analyzer.load_csv(args.files[0])
        
        analyzer.print_detailed_analysis()
        analyzer.print_rankings(args.top_n)
        
        if args.instance_types:
            analyzer.compare_instance_types(args.instance_types)
        
        if args.export_json:
            analyzer.export_summary(args.export_json)
    
    # Compare multiple files
    elif args.compare:
        print("🔍 MULTI-FILE COMPARISON")
        print("="*60)
        
        file_analyzers = {}
        for file_path in args.files:
            analyzer = BenchmarkAnalyzer()
            analyzer.load_csv(file_path)
            file_analyzers[Path(file_path).stem] = analyzer
        
        # Print summary for each file
        for file_name, analyzer in file_analyzers.items():
            print(f"\n📁 Results from {file_name}:")
            total = len(analyzer.results)
            successful = len([r for r in analyzer.results if r.success])
            print(f"   Total runs: {total}, Successful: {successful} ({successful/total*100:.1f}%)")
            print(f"   Instance types: {len(analyzer.by_instance_type.keys())}")
        
        # Find common instance types
        common_types = set.intersection(*[set(analyzer.by_instance_type.keys()) for analyzer in file_analyzers.values()])
        
        if common_types:
            print(f"\n🔗 Common instance types across all files: {len(common_types)}")
            for instance_type in sorted(common_types):
                print(f"\n   {instance_type}:")
                for file_name, analyzer in file_analyzers.items():
                    stats = analyzer.get_instance_stats(instance_type)
                    if stats['successful_runs'] > 0:
                        print(f"     {file_name}: {stats['avg_read_iops']:.0f} read IOPS, {stats['avg_write_iops']:.0f} write IOPS")
                    else:
                        print(f"     {file_name}: No successful runs")
        else:
            print("\n⚠️ No common instance types found across all files")
    
    else:
        # Multiple files but not comparison mode
        for file_path in args.files:
            print(f"\n" + "="*100)
            print(f"ANALYZING: {file_path}")
            print("="*100)
            
            analyzer = BenchmarkAnalyzer()
            analyzer.load_csv(file_path)
            analyzer.print_detailed_analysis()
            analyzer.print_rankings(args.top_n)

if __name__ == '__main__':
    main()
