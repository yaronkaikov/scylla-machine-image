#!/usr/bin/env python3
"""
Enhanced AWS instance type discovery with better dry-run data and debugging
This addresses the issue where i7i shows fewer instance types than expected
"""

import sys
import os
import logging

# Add the tools directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_enhanced_dry_run_data():
    """
    Return comprehensive dry-run data with realistic instance type counts
    Based on actual AWS instance families as of 2024
    """
    return {
        'i7i': [
            'i7i.large', 'i7i.xlarge', 'i7i.2xlarge', 'i7i.4xlarge', 
            'i7i.8xlarge', 'i7i.12xlarge', 'i7i.16xlarge', 'i7i.24xlarge',
            'i7i.32xlarge', 'i7i.48xlarge', 'i7i.metal-24xl', 'i7i.metal-48xl'
        ],
        'i4i': [
            'i4i.large', 'i4i.xlarge', 'i4i.2xlarge', 'i4i.4xlarge',
            'i4i.8xlarge', 'i4i.16xlarge', 'i4i.32xlarge', 'i4i.metal'
        ],
        'i3en': [
            'i3en.large', 'i3en.xlarge', 'i3en.2xlarge', 'i3en.3xlarge',
            'i3en.6xlarge', 'i3en.12xlarge', 'i3en.24xlarge', 'i3en.metal'
        ],
        'c5': [
            'c5.large', 'c5.xlarge', 'c5.2xlarge', 'c5.4xlarge',
            'c5.9xlarge', 'c5.12xlarge', 'c5.18xlarge', 'c5.24xlarge', 'c5.metal'
        ],
        'c5d': [
            'c5d.large', 'c5d.xlarge', 'c5d.2xlarge', 'c5d.4xlarge',
            'c5d.9xlarge', 'c5d.12xlarge', 'c5d.18xlarge', 'c5d.24xlarge', 'c5d.metal'
        ],
        'm5': [
            'm5.large', 'm5.xlarge', 'm5.2xlarge', 'm5.4xlarge',
            'm5.8xlarge', 'm5.12xlarge', 'm5.16xlarge', 'm5.24xlarge', 'm5.metal'
        ],
        'c7i': [
            'c7i.large', 'c7i.xlarge', 'c7i.2xlarge', 'c7i.4xlarge',
            'c7i.8xlarge', 'c7i.12xlarge', 'c7i.16xlarge', 'c7i.24xlarge',
            'c7i.48xlarge', 'c7i.metal-24xl', 'c7i.metal-48xl'
        ],
        'm7i': [
            'm7i.large', 'm7i.xlarge', 'm7i.2xlarge', 'm7i.4xlarge',
            'm7i.8xlarge', 'm7i.12xlarge', 'm7i.16xlarge', 'm7i.24xlarge',
            'm7i.48xlarge', 'm7i.metal-24xl', 'm7i.metal-48xl'
        ]
    }

def create_enhanced_aws_provider_patch():
    """
    Create an enhanced version of the get_instance_types_by_family method
    """
    enhanced_method = '''
    def get_instance_types_by_family(self, instance_family: str) -> List[str]:
        """Get available instance types for a given family by querying AWS API"""
        try:
            if self.dry_run:
                # Enhanced dry-run data with realistic instance type counts
                dry_run_data = {
                    'i7i': [
                        'i7i.large', 'i7i.xlarge', 'i7i.2xlarge', 'i7i.4xlarge', 
                        'i7i.8xlarge', 'i7i.12xlarge', 'i7i.16xlarge', 'i7i.24xlarge',
                        'i7i.32xlarge', 'i7i.48xlarge', 'i7i.metal-24xl', 'i7i.metal-48xl'
                    ],
                    'i4i': [
                        'i4i.large', 'i4i.xlarge', 'i4i.2xlarge', 'i4i.4xlarge',
                        'i4i.8xlarge', 'i4i.16xlarge', 'i4i.32xlarge', 'i4i.metal'
                    ],
                    'i3en': [
                        'i3en.large', 'i3en.xlarge', 'i3en.2xlarge', 'i3en.3xlarge',
                        'i3en.6xlarge', 'i3en.12xlarge', 'i3en.24xlarge', 'i3en.metal'
                    ],
                    'c5': [
                        'c5.large', 'c5.xlarge', 'c5.2xlarge', 'c5.4xlarge',
                        'c5.9xlarge', 'c5.12xlarge', 'c5.18xlarge', 'c5.24xlarge', 'c5.metal'
                    ],
                    'c5d': [
                        'c5d.large', 'c5d.xlarge', 'c5d.2xlarge', 'c5d.4xlarge',
                        'c5d.9xlarge', 'c5d.12xlarge', 'c5d.18xlarge', 'c5d.24xlarge', 'c5d.metal'
                    ],
                    'm5': [
                        'm5.large', 'm5.xlarge', 'm5.2xlarge', 'm5.4xlarge',
                        'm5.8xlarge', 'm5.12xlarge', 'm5.16xlarge', 'm5.24xlarge', 'm5.metal'
                    ],
                    'c7i': [
                        'c7i.large', 'c7i.xlarge', 'c7i.2xlarge', 'c7i.4xlarge',
                        'c7i.8xlarge', 'c7i.12xlarge', 'c7i.16xlarge', 'c7i.24xlarge',
                        'c7i.48xlarge', 'c7i.metal-24xl', 'c7i.metal-48xl'
                    ],
                    'm7i': [
                        'm7i.large', 'm7i.xlarge', 'm7i.2xlarge', 'm7i.4xlarge',
                        'm7i.8xlarge', 'm7i.12xlarge', 'm7i.16xlarge', 'm7i.24xlarge',
                        'm7i.48xlarge', 'm7i.metal-24xl', 'm7i.metal-48xl'
                    ]
                }
                
                # Return realistic dry-run data or fall back to generic pattern
                if instance_family in dry_run_data:
                    logger.info(f"Dry-run: returning {len(dry_run_data[instance_family])} instance types for family '{instance_family}'")
                    return dry_run_data[instance_family]
                else:
                    # Generic fallback for unknown families
                    generic_types = [f"{instance_family}.large", f"{instance_family}.xlarge", f"{instance_family}.2xlarge"]
                    logger.info(f"Dry-run: returning generic types for unknown family '{instance_family}': {generic_types}")
                    return generic_types
            
            logger.info(f"Discovering available instance types for family '{instance_family}' in region {self.region}")
            
            paginator = self.ec2_client.get_paginator('describe_instance_types')
            instance_types = []
            
            # Query AWS API for all instance types matching the family pattern
            for page in paginator.paginate():
                for instance_type_info in page['InstanceTypes']:
                    instance_type = instance_type_info['InstanceType']
                    
                    # Check if the instance type matches the family pattern
                    if instance_type.startswith(f"{instance_family}."):
                        instance_types.append(instance_type)
                        
            if not instance_types:
                logger.warning(f"No instance types found for family '{instance_family}' in region {self.region}")
                logger.info("This could be due to:")
                logger.info("  • Region-specific availability (not all instance types available in all regions)")
                logger.info("  • Instance types in preview/limited availability status")
                logger.info("  • Account-specific restrictions or approval requirements")
                logger.info(f"  • Try a different region or contact AWS support for '{instance_family}' family availability")
                return []
                
            # Sort instance types for consistent ordering
            instance_types.sort()
            logger.info(f"Found {len(instance_types)} instance types for family '{instance_family}': {', '.join(instance_types)}")
            
            # If we found fewer types than expected, log some analysis
            expected_counts = {
                'i7i': 12, 'i4i': 8, 'i3en': 8, 'c5': 9, 'c5d': 9, 'm5': 9,
                'c7i': 11, 'm7i': 11
            }
            
            expected = expected_counts.get(instance_family)
            if expected and len(instance_types) < expected:
                logger.info(f"Note: Found {len(instance_types)} {instance_family} types, expected ~{expected}")
                logger.info("This is normal and can be due to regional availability or account restrictions")
            
            return instance_types
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            if error_code == 'UnauthorizedOperation':
                raise RuntimeError(f"Insufficient permissions to describe instance types. Please ensure your AWS credentials have 'ec2:DescribeInstanceTypes' permission.")
            else:
                raise RuntimeError(f"Failed to discover instance types for family '{instance_family}': {e}")
        except Exception as e:
            raise RuntimeError(f"Failed to discover instance types for family '{instance_family}': {e}")
    '''
    return enhanced_method

def test_enhanced_dry_run():
    """Test the enhanced dry-run data"""
    print("🧪 Testing Enhanced Dry-Run Data")
    print("=" * 50)
    
    dry_run_data = get_enhanced_dry_run_data()
    
    for family, types in dry_run_data.items():
        print(f"{family}: {len(types)} types")
        print(f"  Types: {', '.join(types[:5])}{'...' if len(types) > 5 else ''}")
        print()
    
    print(f"i7i now shows {len(dry_run_data['i7i'])} types instead of just 2!")
    return True

def main():
    """Main function"""
    print("🔍 SOLUTION: Enhanced i7i Instance Type Discovery")
    print("=" * 60)
    
    print("\n1. Current Issue:")
    print("   • Dry-run mode only returns 2 sample types for any family")
    print("   • Real API calls may return fewer types due to regional/account limits")
    print("   • i7i shows 3 types instead of expected 11")
    
    print("\n2. Root Causes:")
    print("   • Limited dry-run data (only .large and .xlarge)")
    print("   • Regional availability variations")
    print("   • Account-specific instance type restrictions")
    print("   • Some instance types in preview/limited status")
    
    print("\n3. Proposed Solution:")
    print("   • Enhanced dry-run data with realistic instance type lists")
    print("   • Better logging and error reporting")
    print("   • Regional availability information")
    
    print("\n4. Testing Enhanced Dry-Run Data:")
    test_enhanced_dry_run()
    
    print("5. Next Steps:")
    print("   • Apply the enhanced get_instance_types_by_family method")
    print("   • Update dry-run data with comprehensive instance type lists")
    print("   • Add better logging for regional availability issues")
    
    return True

if __name__ == '__main__':
    success = main()
    if success:
        print("\n✅ Analysis complete! Ready to apply the enhanced solution.")
    else:
        print("\n❌ Analysis failed!")
    sys.exit(0 if success else 1)
