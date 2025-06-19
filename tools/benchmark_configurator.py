#!/usr/bin/env python3

"""
ScyllaDB Cloud Benchmark Configuration Generator

This script helps generate benchmark configurations for different scenarios
and provides recommendations for optimal testing strategies.

Usage:
    python benchmark_configurator.py --scenario performance-comparison
    python benchmark_configurator.py --scenario cost-optimization --budget 100
    python benchmark_configurator.py --custom --clouds aws gcp --families i4i n2
"""

import argparse
import json
import logging
import sys
from typing import Dict, List, Optional

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Instance families by cloud provider with cost estimates (USD per hour, approximate)
INSTANCE_FAMILIES = {
    'aws': {
        'i4i': {
            'description': 'High-performance NVMe SSD storage',
            'types': ['i4i.large', 'i4i.xlarge', 'i4i.2xlarge', 'i4i.4xlarge', 'i4i.8xlarge', 'i4i.16xlarge', 'i4i.32xlarge', 'i4i.metal'],
            'cost_per_hour': [0.1536, 0.3072, 0.6144, 1.2288, 2.4576, 4.9152, 9.8304, 19.6608],
            'use_cases': ['High IOPS workloads', 'Real-time analytics', 'High-performance databases']
        },
        'i3en': {
            'description': 'High-performance SSD with enhanced networking',
            'types': ['i3en.large', 'i3en.xlarge', 'i3en.2xlarge', 'i3en.3xlarge', 'i3en.6xlarge', 'i3en.12xlarge', 'i3en.24xlarge'],
            'cost_per_hour': [0.1504, 0.3008, 0.6016, 0.9024, 1.8048, 3.6096, 7.2192],
            'use_cases': ['Distributed file systems', 'High-performance computing', 'Network-intensive applications']
        },
        'c5d': {
            'description': 'Compute optimized with local NVMe SSD',
            'types': ['c5d.large', 'c5d.xlarge', 'c5d.2xlarge', 'c5d.4xlarge', 'c5d.9xlarge', 'c5d.18xlarge'],
            'cost_per_hour': [0.096, 0.192, 0.384, 0.768, 1.728, 3.456],
            'use_cases': ['CPU-intensive applications', 'Scientific modeling', 'Batch processing']
        }
    },
    'gcp': {
        'n2': {
            'description': 'Balanced compute and memory',
            'types': ['n2-standard-2', 'n2-standard-4', 'n2-standard-8', 'n2-standard-16', 'n2-standard-32', 'n2-highmem-4', 'n2-highmem-8'],
            'cost_per_hour': [0.0776, 0.1552, 0.3104, 0.6208, 1.2416, 0.2074, 0.4148],
            'use_cases': ['General purpose workloads', 'Web serving', 'Enterprise applications']
        },
        'n2d': {
            'description': 'AMD-based balanced instances',
            'types': ['n2d-standard-2', 'n2d-standard-4', 'n2d-standard-8', 'n2d-standard-16', 'n2d-standard-32'],
            'cost_per_hour': [0.0698, 0.1396, 0.2792, 0.5584, 1.1168],
            'use_cases': ['Cost-effective computing', 'Development environments', 'Testing']
        },
        'c2': {
            'description': 'Compute-optimized instances',
            'types': ['c2-standard-4', 'c2-standard-8', 'c2-standard-16', 'c2-standard-30', 'c2-standard-60'],
            'cost_per_hour': [0.1342, 0.2684, 0.5368, 1.0065, 2.013],
            'use_cases': ['High-performance computing', 'Gaming', 'Scientific computing']
        }
    },
    'azure': {
        'L8s_v3': {
            'description': 'Storage optimized with NVMe',
            'types': ['Standard_L8s_v3', 'Standard_L16s_v3', 'Standard_L32s_v3', 'Standard_L48s_v3', 'Standard_L64s_v3'],
            'cost_per_hour': [0.624, 1.248, 2.496, 3.744, 4.992],
            'use_cases': ['High IOPS storage', 'NoSQL databases', 'Data analytics']
        },
        'Lsv2': {
            'description': 'Storage optimized with local SSD',
            'types': ['Standard_L8s_v2', 'Standard_L16s_v2', 'Standard_L32s_v2', 'Standard_L48s_v2', 'Standard_L64s_v2'],
            'cost_per_hour': [0.624, 1.248, 2.496, 3.744, 4.992],
            'use_cases': ['Distributed NoSQL databases', 'In-memory analytics', 'Caching layers']
        }
    }
}

REGIONS = {
    'aws': ['us-east-1', 'us-west-2', 'eu-west-1', 'ap-southeast-1'],
    'gcp': ['us-central1', 'us-west1', 'europe-west1', 'asia-southeast1'],
    'azure': ['eastus', 'westus2', 'westeurope', 'southeastasia']
}

class BenchmarkConfigurator:
    """Generates benchmark configurations for different scenarios"""
    
    def __init__(self):
        self.configurations = []
    
    def generate_performance_comparison(self, clouds: Optional[List[str]] = None) -> Dict:
        """Generate configuration for cross-cloud performance comparison"""
        clouds = clouds or ['aws', 'gcp', 'azure']
        
        config = {
            'scenario': 'performance-comparison',
            'description': 'Compare performance across cloud providers and instance types',
            'recommended_runs': 5,
            'max_concurrent': 3,
            'commands': []
        }
        
        for cloud in clouds:
            if cloud not in INSTANCE_FAMILIES:
                continue
                
            # Select high-performance families for each cloud
            if cloud == 'aws':
                families = ['i4i', 'i3en']
            elif cloud == 'gcp':
                families = ['n2', 'c2']
            elif cloud == 'azure':
                families = ['L8s_v3']
            
            for family in families:
                if family in INSTANCE_FAMILIES[cloud]:
                    # Select medium-sized instances for comparison
                    instance_types = INSTANCE_FAMILIES[cloud][family]['types']
                    selected_types = [t for t in instance_types if any(size in t for size in ['large', 'xlarge', 'standard-4', 'standard-8'])][:3]
                    
                    cmd = {
                        'cloud': cloud,
                        'region': REGIONS[cloud][0],
                        'instance_family': family,
                        'instance_types': selected_types,
                        'runs': 5,
                        'estimated_cost_per_hour': sum(INSTANCE_FAMILIES[cloud][family]['cost_per_hour'][:len(selected_types)]),
                        'estimated_total_time': '45-60 minutes',
                        'use_case': INSTANCE_FAMILIES[cloud][family]['use_cases'][0]
                    }
                    config['commands'].append(cmd)
        
        return config
    
    def generate_cost_optimization(self, budget: float, clouds: Optional[List[str]] = None) -> Dict:
        """Generate configuration optimized for budget constraints"""
        clouds = clouds or ['aws', 'gcp', 'azure']
        
        config = {
            'scenario': 'cost-optimization',
            'description': f'Optimize performance within ${budget} budget',
            'budget_limit': budget,
            'recommended_runs': 3,
            'max_concurrent': 2,
            'commands': []
        }
        
        # Calculate cost-effective instance selections
        cost_effective_instances = []
        
        for cloud in clouds:
            if cloud not in INSTANCE_FAMILIES:
                continue
                
            for family, details in INSTANCE_FAMILIES[cloud].items():
                for i, instance_type in enumerate(details['types']):
                    if i < len(details['cost_per_hour']):
                        cost_per_hour = details['cost_per_hour'][i]
                        # Estimate 20 minutes runtime for 3 runs
                        estimated_cost = cost_per_hour * (20/60)
                        
                        if estimated_cost <= budget / 5:  # Leave room for multiple instances
                            cost_effective_instances.append({
                                'cloud': cloud,
                                'family': family,
                                'instance_type': instance_type,
                                'cost_per_test': estimated_cost,
                                'cost_per_hour': cost_per_hour
                            })
        
        # Sort by cost and select best options within budget
        cost_effective_instances.sort(key=lambda x: x['cost_per_test'])
        
        total_cost = 0
        for instance in cost_effective_instances:
            if total_cost + instance['cost_per_test'] <= budget:
                cmd = {
                    'cloud': instance['cloud'],
                    'region': REGIONS[instance['cloud']][0],
                    'instance_types': [instance['instance_type']],
                    'runs': 3,
                    'estimated_cost': instance['cost_per_test'],
                    'cost_per_hour': instance['cost_per_hour']
                }
                config['commands'].append(cmd)
                total_cost += instance['cost_per_test']
        
        config['total_estimated_cost'] = total_cost
        return config
    
    def generate_comprehensive_test(self, clouds: Optional[List[str]] = None, 
                                  families: Optional[List[str]] = None) -> Dict:
        """Generate comprehensive test across all available instance types"""
        clouds = clouds or ['aws', 'gcp', 'azure']
        
        config = {
            'scenario': 'comprehensive-test',
            'description': 'Comprehensive performance testing across all instance types',
            'recommended_runs': 3,
            'max_concurrent': 3,
            'estimated_duration': '2-4 hours',
            'commands': []
        }
        
        total_cost = 0
        
        for cloud in clouds:
            if cloud not in INSTANCE_FAMILIES:
                continue
                
            cloud_families = families or list(INSTANCE_FAMILIES[cloud].keys())
            
            for family in cloud_families:
                if family in INSTANCE_FAMILIES[cloud]:
                    details = INSTANCE_FAMILIES[cloud][family]
                    
                    # For comprehensive test, include all instance types
                    cmd = {
                        'cloud': cloud,
                        'region': REGIONS[cloud][0],
                        'instance_family': family,
                        'runs': 3,
                        'description': details['description'],
                        'use_cases': details['use_cases'],
                        'estimated_cost_per_hour': sum(details['cost_per_hour']),
                        'instance_count': len(details['types'])
                    }
                    config['commands'].append(cmd)
                    total_cost += sum(details['cost_per_hour']) * 0.5  # 30 minutes estimate
        
        config['total_estimated_cost'] = total_cost
        return config
    
    def generate_quick_test(self, clouds: Optional[List[str]] = None) -> Dict:
        """Generate quick test configuration for rapid feedback"""
        clouds = clouds or ['aws']
        
        config = {
            'scenario': 'quick-test',
            'description': 'Quick performance test for rapid feedback',
            'recommended_runs': 1,
            'max_concurrent': 2,
            'estimated_duration': '10-15 minutes',
            'commands': []
        }
        
        for cloud in clouds[:1]:  # Only test one cloud for quick test
            if cloud not in INSTANCE_FAMILIES:
                continue
                
            # Select one high-performance family and a few instance types
            if cloud == 'aws':
                family = 'i4i'
                selected_types = ['i4i.large', 'i4i.xlarge']
            elif cloud == 'gcp':
                family = 'n2'
                selected_types = ['n2-standard-4', 'n2-standard-8']
            elif cloud == 'azure':
                family = 'L8s_v3'
                selected_types = ['Standard_L8s_v3']
            
            cmd = {
                'cloud': cloud,
                'region': REGIONS[cloud][0],
                'instance_types': selected_types,
                'runs': 1,
                'estimated_duration': '10-15 minutes',
                'estimated_cost': 2.0  # Low cost estimate
            }
            config['commands'].append(cmd)
        
        return config
    
    def print_configuration(self, config: Dict) -> None:
        """Pretty print a configuration"""
        print(f"\n🔧 BENCHMARK CONFIGURATION: {config['scenario'].upper()}")
        print("="*80)
        print(f"Description: {config['description']}")
        
        if 'budget_limit' in config:
            print(f"Budget Limit: ${config['budget_limit']:.2f}")
        
        if 'total_estimated_cost' in config:
            print(f"Estimated Total Cost: ${config['total_estimated_cost']:.2f}")
        
        if 'estimated_duration' in config:
            print(f"Estimated Duration: {config['estimated_duration']}")
        
        print(f"Recommended Runs: {config['recommended_runs']}")
        print(f"Max Concurrent: {config['max_concurrent']}")
        
        print(f"\n📋 Commands to run ({len(config['commands'])} total):")
        print("-"*80)
        
        for i, cmd in enumerate(config['commands'], 1):
            print(f"\n{i}. {cmd['cloud'].upper()} - {cmd.get('instance_family', 'Custom Selection')}")
            
            # Build command line
            cmd_line = f"python cloud_io_benchmark.py --cloud {cmd['cloud']} --region {cmd['region']}"
            
            if 'instance_family' in cmd:
                cmd_line += f" --instance-family {cmd['instance_family']}"
            elif 'instance_types' in cmd:
                cmd_line += f" --instance-types {' '.join(cmd['instance_types'])}"
            
            cmd_line += f" --runs {cmd.get('runs', config['recommended_runs'])}"
            cmd_line += f" --max-concurrent {config['max_concurrent']}"
            cmd_line += f" --output-csv {config['scenario']}_{cmd['cloud']}_results.csv"
            cmd_line += " --image YOUR_SCYLLA_IMAGE_ID"
            
            print(f"   {cmd_line}")
            
            if 'estimated_cost' in cmd:
                print(f"   Estimated cost: ${cmd['estimated_cost']:.2f}")
            elif 'estimated_cost_per_hour' in cmd:
                print(f"   Estimated cost: ${cmd['estimated_cost_per_hour'] * 0.5:.2f} (30 min estimate)")
        
        print(f"\n💡 Tips:")
        print(f"   • Replace YOUR_SCYLLA_IMAGE_ID with actual ScyllaDB image IDs for each cloud")
        print(f"   • Set up cloud credentials before running")
        print(f"   • Use --dry-run flag first to validate configuration")
        print(f"   • Consider running commands in parallel for faster results")
        
        if config['scenario'] == 'performance-comparison':
            print(f"   • After completion, use: python benchmark_analyzer.py --compare *.csv")
        
        print("="*80)
    
    def export_configuration(self, config: Dict, filename: str) -> None:
        """Export configuration to JSON file"""
        with open(filename, 'w') as f:
            json.dump(config, f, indent=2)
        logger.info(f"Configuration exported to {filename}")

def main():
    parser = argparse.ArgumentParser(description='Generate ScyllaDB cloud benchmark configurations')
    parser.add_argument('--scenario', choices=['performance-comparison', 'cost-optimization', 'comprehensive-test', 'quick-test'],
                       help='Predefined benchmark scenario')
    parser.add_argument('--custom', action='store_true', help='Create custom configuration')
    parser.add_argument('--clouds', nargs='+', choices=['aws', 'gcp', 'azure'],
                       help='Cloud providers to include')
    parser.add_argument('--families', nargs='+', help='Instance families to include')
    parser.add_argument('--budget', type=float, help='Budget limit in USD (for cost-optimization)')
    parser.add_argument('--export', help='Export configuration to JSON file')
    parser.add_argument('--list-families', action='store_true', help='List available instance families')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    
    args = parser.parse_args()
    
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    configurator = BenchmarkConfigurator()
    
    if args.list_families:
        print("Available Instance Families:")
        print("="*50)
        for cloud, families in INSTANCE_FAMILIES.items():
            print(f"\n{cloud.upper()}:")
            for family, details in families.items():
                print(f"  {family}: {details['description']}")
                print(f"    Types: {len(details['types'])} instances")
                print(f"    Use cases: {', '.join(details['use_cases'])}")
        return
    
    if not args.scenario and not args.custom:
        parser.error("Either --scenario or --custom must be specified")
    
    config = None
    
    if args.scenario == 'performance-comparison':
        config = configurator.generate_performance_comparison(args.clouds)
    elif args.scenario == 'cost-optimization':
        if not args.budget:
            parser.error("--budget is required for cost-optimization scenario")
        config = configurator.generate_cost_optimization(args.budget, args.clouds)
    elif args.scenario == 'comprehensive-test':
        config = configurator.generate_comprehensive_test(args.clouds, args.families)
    elif args.scenario == 'quick-test':
        config = configurator.generate_quick_test(args.clouds)
    elif args.custom:
        # For custom, generate comprehensive but allow filtering
        config = configurator.generate_comprehensive_test(args.clouds, args.families)
        config['scenario'] = 'custom'
        config['description'] = 'Custom benchmark configuration'
    
    if config:
        configurator.print_configuration(config)
        
        if args.export:
            configurator.export_configuration(config, args.export)

if __name__ == '__main__':
    main()
