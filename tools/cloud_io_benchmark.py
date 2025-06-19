#!/usr/bin/env python3

"""
Cloud Instance I/O Benchmark Script for ScyllaDB

This script creates VMs across AWS, GCP, and Azure cloud providers, runs scylla_io_setup
on each instance type, and collects performance results in a tabular format.

Usage:
    python cloud_io_benchmark.py --cloud aws --image ami-12345678 --instance-family i4i
    python cloud_io_benchmark.py --cloud gcp --image projects/scylla-images/global/images/scylladb-5-2-1 --instance-family n2
    python cloud_io_benchmark.py --cloud azure --image /subscriptions/.../resourceGroups/.../providers/Microsoft.Compute/galleries/.../images/scylladb/versions/5.2.1 --instance-family L8s_v3
"""

import argparse
import asyncio
import csv
import json
import logging
import os
import re
import subprocess
import sys
import time
import yaml
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import statistics

# Optional cost estimation
try:
    from cost_estimator import CostEstimator
    COST_ESTIMATION_AVAILABLE = True
except ImportError:
    COST_ESTIMATION_AVAILABLE = False

# Cloud provider SDKs - import conditionally
boto3 = None
compute_v1 = None
DefaultAzureCredential = None

try:
    import boto3
    from botocore.exceptions import ClientError, NoCredentialsError
except ImportError:
    boto3 = None
    ClientError = Exception
    NoCredentialsError = Exception

try:
    from google.cloud import compute_v1
    from google.auth.exceptions import DefaultCredentialsError
except ImportError:
    compute_v1 = None
    DefaultCredentialsError = Exception

try:
    from azure.identity import DefaultAzureCredential
    from azure.mgmt.compute import ComputeManagementClient
    from azure.mgmt.network import NetworkManagementClient
    from azure.mgmt.resource import ResourceManagementClient
    from azure.core.exceptions import ClientAuthenticationError
except ImportError:
    DefaultAzureCredential = None
    ComputeManagementClient = None
    NetworkManagementClient = None
    ResourceManagementClient = None
    ClientAuthenticationError = Exception

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('cloud_io_benchmark.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Global flag for live debug output streaming
DEBUG_LIVE_MODE = False

@dataclass
class IoSetupResult:
    """Represents the result of running scylla_io_setup on an instance"""
    cloud: str
    instance_type: str
    instance_id: str
    run_number: int
    success: bool
    execution_time: float
    read_iops: Optional[int] = None
    write_iops: Optional[int] = None
    read_bandwidth: Optional[float] = None  # MB/s
    write_bandwidth: Optional[float] = None  # MB/s
    error_message: Optional[str] = None

@dataclass 
class InstanceConfig:
    """Configuration for creating a cloud instance"""
    instance_type: str
    image_id: str
    key_name: Optional[str] = None
    security_group: Optional[str] = None
    subnet_id: Optional[str] = None
    vpc_id: Optional[str] = None
    user_data: Optional[str] = None

class CloudProviderInterface:
    """Base interface for cloud provider operations"""
    
    def __init__(self, region: str):
        self.region = region
        
    async def create_instance(self, config: InstanceConfig) -> str:
        """Create an instance and return its ID"""
        raise NotImplementedError
        
    async def wait_for_instance_ready(self, instance_id: str, timeout: int = 600) -> bool:
        """Wait for instance to be ready and return True if successful"""
        raise NotImplementedError
        
    async def get_instance_ip(self, instance_id: str) -> str:
        """Get the public IP address of the instance"""
        raise NotImplementedError
        
    async def run_command_on_instance(self, instance_id: str, command: str) -> Tuple[int, str, str]:
        """Run a command on the instance and return (return_code, stdout, stderr)"""
        raise NotImplementedError
        
    async def terminate_instance(self, instance_id: str) -> None:
        """Terminate the instance"""
        raise NotImplementedError

class AWSProvider(CloudProviderInterface):
    """AWS EC2 provider implementation"""
    
    def __init__(self, region: str, dry_run: bool = False, key_name: str = None):
        super().__init__(region)
        if not boto3:
            raise ImportError("boto3 is required for AWS operations")
        
        self.dry_run = dry_run
        self.key_name = key_name  # Store key name for SSH connections
        if not dry_run:
            try:
                self.ec2_client = boto3.client('ec2', region_name=region)
                self.ec2_resource = boto3.resource('ec2', region_name=region)
                # Test credentials
                self.ec2_client.describe_regions()
            except (NoCredentialsError, ClientError) as e:
                raise RuntimeError(f"AWS credentials not configured: {e}")
        else:
            # For dry runs, create placeholder clients
            self.ec2_client = None
            self.ec2_resource = None
            
    def _get_vpc_configuration(self, user_vpc_id=None, user_subnet_id=None):
        """Get or create VPC configuration for instances"""
        try:
            # Use user-provided VPC and subnet if available
            if user_vpc_id and user_subnet_id:
                logger.info(f"Using user-specified VPC: {user_vpc_id}, subnet: {user_subnet_id}")
                return user_vpc_id, user_subnet_id
            
            # If only VPC is specified, find a suitable subnet
            if user_vpc_id:
                logger.info(f"Using user-specified VPC: {user_vpc_id}")
                subnets_response = self.ec2_client.describe_subnets(
                    Filters=[
                        {'Name': 'vpc-id', 'Values': [user_vpc_id]},
                        {'Name': 'map-public-ip-on-launch', 'Values': ['true']}
                    ]
                )
                
                if subnets_response['Subnets']:
                    subnet_id = subnets_response['Subnets'][0]['SubnetId']
                    logger.info(f"Using public subnet: {subnet_id}")
                    return user_vpc_id, subnet_id
                
                # Fall back to any subnet in the VPC
                subnets_response = self.ec2_client.describe_subnets(
                    Filters=[{'Name': 'vpc-id', 'Values': [user_vpc_id]}]
                )
                
                if subnets_response['Subnets']:
                    subnet_id = subnets_response['Subnets'][0]['SubnetId']
                    logger.info(f"Using subnet: {subnet_id}")
                    return user_vpc_id, subnet_id
                
                raise RuntimeError(f"No subnets found in user-specified VPC {user_vpc_id}")
            
            # Auto-detect VPC configuration
            # Try to find default VPC first
            vpcs_response = self.ec2_client.describe_vpcs(
                Filters=[{'Name': 'is-default', 'Values': ['true']}]
            )
            
            if vpcs_response['Vpcs']:
                default_vpc = vpcs_response['Vpcs'][0]
                vpc_id = default_vpc['VpcId']
                logger.info(f"Using default VPC: {vpc_id}")
                
                # Get a subnet from the default VPC
                subnets_response = self.ec2_client.describe_subnets(
                    Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}]
                )
                if subnets_response['Subnets']:
                    subnet_id = subnets_response['Subnets'][0]['SubnetId']
                    logger.info(f"Using subnet: {subnet_id}")
                    return vpc_id, subnet_id
            
            # No default VPC, find any available VPC
            vpcs_response = self.ec2_client.describe_vpcs()
            if not vpcs_response['Vpcs']:
                raise RuntimeError("No VPCs found in this AWS account")
            
            # Use the first available VPC
            vpc_id = vpcs_response['Vpcs'][0]['VpcId']
            logger.info(f"No default VPC found, using VPC: {vpc_id}")
            
            # Get a public subnet from this VPC
            subnets_response = self.ec2_client.describe_subnets(
                Filters=[
                    {'Name': 'vpc-id', 'Values': [vpc_id]},
                    {'Name': 'map-public-ip-on-launch', 'Values': ['true']}
                ]
            )
            
            if subnets_response['Subnets']:
                subnet_id = subnets_response['Subnets'][0]['SubnetId']
                logger.info(f"Using public subnet: {subnet_id}")
                return vpc_id, subnet_id
            
            # If no public subnet, use any subnet
            subnets_response = self.ec2_client.describe_subnets(
                Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}]
            )
            
            if subnets_response['Subnets']:
                subnet_id = subnets_response['Subnets'][0]['SubnetId']
                logger.info(f"Using subnet: {subnet_id}")
                return vpc_id, subnet_id
            
            raise RuntimeError(f"No subnets found in VPC {vpc_id}")
            
        except ClientError as e:
            raise RuntimeError(f"Failed to get VPC configuration: {e}")
    
    def _get_or_create_security_group(self, vpc_id):
        """Get or create a security group for SSH access"""
        sg_name = 'scylla-benchmark-sg'
        
        try:
            # Try to find existing security group
            response = self.ec2_client.describe_security_groups(
                Filters=[
                    {'Name': 'group-name', 'Values': [sg_name]},
                    {'Name': 'vpc-id', 'Values': [vpc_id]}
                ]
            )
            
            if response['SecurityGroups']:
                sg_id = response['SecurityGroups'][0]['GroupId']
                logger.info(f"Using existing security group: {sg_id}")
                return sg_id
            
            # Create new security group
            response = self.ec2_client.create_security_group(
                GroupName=sg_name,
                Description='Security group for ScyllaDB benchmark instances',
                VpcId=vpc_id
            )
            sg_id = response['GroupId']
            
            # Add SSH access rule
            self.ec2_client.authorize_security_group_ingress(
                GroupId=sg_id,
                IpPermissions=[
                    {
                        'IpProtocol': 'tcp',
                        'FromPort': 22,
                        'ToPort': 22,
                        'IpRanges': [{'CidrIp': '0.0.0.0/0', 'Description': 'SSH access for benchmark'}]
                    }
                ]
            )
            
            logger.info(f"Created security group: {sg_id}")
            return sg_id
            
        except ClientError as e:
            logger.warning(f"Failed to create security group: {e}")
            return None
    
    def _get_available_zones(self):
        """Get list of available availability zones in the region"""
        try:
            response = self.ec2_client.describe_availability_zones(
                Filters=[{'Name': 'state', 'Values': ['available']}]
            )
            zones = [zone['ZoneName'] for zone in response['AvailabilityZones']]
            logger.debug(f"Available zones in {self.region}: {zones}")
            return zones
        except ClientError as e:
            logger.warning(f"Failed to get availability zones: {e}")
            return []
    
    def _check_instance_type_support(self, instance_type: str, zone: str):
        """Check if an instance type is supported in a specific availability zone"""
        try:
            # Try to get instance type offerings for the zone
            response = self.ec2_client.describe_instance_type_offerings(
                Filters=[
                    {'Name': 'instance-type', 'Values': [instance_type]},
                    {'Name': 'location', 'Values': [zone]}
                ],
                LocationType='availability-zone'
            )
            return len(response['InstanceTypeOfferings']) > 0
        except ClientError as e:
            logger.debug(f"Failed to check instance type support for {instance_type} in {zone}: {e}")
            return False
    
    def _find_supported_subnet(self, vpc_id: str, instance_type: str):
        """Find a subnet in an availability zone that supports the instance type"""
        try:
            # Get all subnets in the VPC
            subnets_response = self.ec2_client.describe_subnets(
                Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}]
            )
            
            # Get available zones
            available_zones = self._get_available_zones()
            
            # Try to find a subnet in a zone that supports the instance type
            # Prefer public subnets first
            public_subnets = [s for s in subnets_response['Subnets'] 
                            if s.get('MapPublicIpOnLaunch', False)]
            all_subnets = subnets_response['Subnets']
            
            # Try public subnets first, then all subnets
            for subnet_list in [public_subnets, all_subnets]:
                for subnet in subnet_list:
                    zone = subnet['AvailabilityZone']
                    if zone in available_zones:
                        if self._check_instance_type_support(instance_type, zone):
                            logger.info(f"Found supported subnet {subnet['SubnetId']} in zone {zone} for instance type {instance_type}")
                            return subnet['SubnetId'], zone
                        else:
                            logger.debug(f"Instance type {instance_type} not supported in zone {zone}")
            
            # If no existing subnet works, return the first available one and let AWS handle the error
            if subnets_response['Subnets']:
                subnet = subnets_response['Subnets'][0]
                logger.warning(f"No subnet found with confirmed support for {instance_type}, trying {subnet['SubnetId']} in {subnet['AvailabilityZone']}")
                return subnet['SubnetId'], subnet['AvailabilityZone']
            
            raise RuntimeError(f"No subnets found in VPC {vpc_id}")
            
        except ClientError as e:
            raise RuntimeError(f"Failed to find supported subnet: {e}")

    def _get_vpc_configuration_with_zone_support(self, user_vpc_id=None, user_subnet_id=None, instance_type=None):
        """Get VPC configuration that supports the instance type in an available zone"""
        try:
            # Use user-provided VPC and subnet if available
            if user_vpc_id and user_subnet_id:
                # Verify the subnet supports the instance type
                if instance_type:
                    subnet_response = self.ec2_client.describe_subnets(SubnetIds=[user_subnet_id])
                    if subnet_response['Subnets']:
                        zone = subnet_response['Subnets'][0]['AvailabilityZone']
                        if self._check_instance_type_support(instance_type, zone):
                            logger.info(f"Using user-specified VPC: {user_vpc_id}, subnet: {user_subnet_id} (zone: {zone})")
                            return user_vpc_id, user_subnet_id
                        else:
                            logger.warning(f"User-specified subnet {user_subnet_id} in zone {zone} doesn't support {instance_type}, searching for alternative...")
                            return self._find_vpc_with_instance_support(user_vpc_id, instance_type)
                
                logger.info(f"Using user-specified VPC: {user_vpc_id}, subnet: {user_subnet_id}")
                return user_vpc_id, user_subnet_id
            
            # If only VPC is specified, find a suitable subnet that supports the instance type
            if user_vpc_id:
                if instance_type:
                    subnet_id, zone = self._find_supported_subnet(user_vpc_id, instance_type)
                    return user_vpc_id, subnet_id
                
                # Fallback to original logic if no instance type specified
                return self._get_vpc_configuration(user_vpc_id, user_subnet_id)
            
            # Auto-detect VPC configuration with instance type support
            return self._find_vpc_with_instance_support(None, instance_type)
            
        except Exception as e:
            logger.warning(f"Failed to find VPC configuration with zone support: {e}")
            # Fallback to original method
            return self._get_vpc_configuration(user_vpc_id, user_subnet_id)
    
    def _find_vpc_with_instance_support(self, preferred_vpc_id=None, instance_type=None):
        """Find a VPC and subnet that supports the instance type"""
        try:
            # Get VPCs to search
            if preferred_vpc_id:
                vpcs_to_try = [preferred_vpc_id]
            else:
                # Try default VPC first, then others
                vpcs_response = self.ec2_client.describe_vpcs()
                default_vpcs = [vpc['VpcId'] for vpc in vpcs_response['Vpcs'] if vpc.get('IsDefault', False)]
                other_vpcs = [vpc['VpcId'] for vpc in vpcs_response['Vpcs'] if not vpc.get('IsDefault', False)]
                vpcs_to_try = default_vpcs + other_vpcs
            
            for vpc_id in vpcs_to_try:
                try:
                    if instance_type:
                        subnet_id, zone = self._find_supported_subnet(vpc_id, instance_type)
                        logger.info(f"Using VPC {vpc_id} with subnet {subnet_id} in zone {zone}")
                        return vpc_id, subnet_id
                    else:
                        # Use original logic if no instance type
                        return self._get_vpc_configuration(vpc_id, None)
                except Exception as e:
                    logger.debug(f"VPC {vpc_id} doesn't work for instance type {instance_type}: {e}")
                    continue
            
            # If no VPC works, fall back to original method
            logger.warning(f"No VPC found with confirmed support for {instance_type}, using default configuration")
            return self._get_vpc_configuration()
            
        except Exception as e:
            logger.error(f"Failed to find VPC with instance support: {e}")
            # Final fallback
            return self._get_vpc_configuration()

    async def create_instance(self, config: InstanceConfig) -> str:
        """Create EC2 instance"""
        # Get VPC configuration - check config first, then auto-detect
        user_vpc_id = config.vpc_id
        user_subnet_id = config.subnet_id
        vpc_id, subnet_id = self._get_vpc_configuration_with_zone_support(user_vpc_id, user_subnet_id, config.instance_type)
        
        # Get or create security group
        user_security_group_id = config.security_group
        if user_security_group_id:
            security_group_id = user_security_group_id
            logger.info(f"Using user-specified security group: {security_group_id}")
        else:
            security_group_id = self._get_or_create_security_group(vpc_id)
        
        run_instances_params = {
            'ImageId': config.image_id,
            'MinCount': 1,
            'MaxCount': 1,
            'InstanceType': config.instance_type,
            'SubnetId': subnet_id,
            'TagSpecifications': [
                {
                    'ResourceType': 'instance',
                    'Tags': [
                        {'Key': 'Name', 'Value': f'scylla-io-benchmark-{config.instance_type}'},
                        {'Key': 'Purpose', 'Value': 'scylla-io-benchmark'},
                        {'Key': 'AutoTerminate', 'Value': 'true'}
                    ]
                }
            ]
        }
        
        if config.key_name:
            run_instances_params['KeyName'] = config.key_name
        
        if security_group_id:
            run_instances_params['SecurityGroupIds'] = [security_group_id]
            
        if config.user_data:
            run_instances_params['UserData'] = config.user_data
            
        try:
            response = self.ec2_client.run_instances(**run_instances_params)
            instance_id = response['Instances'][0]['InstanceId']
            logger.info(f"Created AWS instance {instance_id} of type {config.instance_type}")
            return instance_id
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            error_message = str(e)
            
            # Handle specific AWS errors with helpful messages
            if error_code == 'Unsupported' and 'Availability Zone' in error_message:
                # Extract zone information from error message
                logger.error(f"Instance type {config.instance_type} not supported in the selected availability zone")
                logger.info("Attempting to find an alternative availability zone...")
                
                # Try to find another zone automatically
                try:
                    # Get the current subnet's zone
                    subnet_response = self.ec2_client.describe_subnets(SubnetIds=[subnet_id])
                    current_zone = subnet_response['Subnets'][0]['AvailabilityZone']
                    logger.debug(f"Current zone {current_zone} doesn't support {config.instance_type}")
                    
                    # Try to find a supported zone and corresponding subnet
                    if hasattr(config, 'vpc_id') or hasattr(self, '_get_vpc_configuration_with_zone_support'):
                        logger.info(f"Retrying with automatic zone selection for {config.instance_type}")
                        # The zone selection should have already been done in _get_vpc_configuration_with_zone_support
                        # If we still get this error, it means no zone supports this instance type
                        available_zones = self._get_available_zones()
                        supported_zones = []
                        for zone in available_zones:
                            if self._check_instance_type_support(config.instance_type, zone):
                                supported_zones.append(zone)
                        
                        if supported_zones:
                            raise RuntimeError(f"Instance type {config.instance_type} is supported in zones {supported_zones} but not in the selected subnet's zone {current_zone}. Please specify a different --aws-subnet-id in one of the supported zones, or remove --aws-subnet-id to allow automatic selection.")
                        else:
                            raise RuntimeError(f"Instance type {config.instance_type} is not supported in any availability zone in region {self.region}. Please choose a different instance type or region.")
                    
                except Exception as retry_error:
                    logger.debug(f"Failed to find alternative zone: {retry_error}")
                    raise RuntimeError(f"Instance type {config.instance_type} not supported in the selected availability zone. {error_message}")
            
            elif error_code == 'InsufficientInstanceCapacity':
                raise RuntimeError(f"Insufficient capacity for instance type {config.instance_type} in the selected availability zone. Try again later or choose a different instance type.")
            
            elif error_code == 'InvalidInstanceType':
                raise RuntimeError(f"Invalid instance type {config.instance_type}. Please check the instance type name and ensure it's available in region {self.region}.")
            
            else:
                raise RuntimeError(f"Failed to create AWS instance: {error_message}")
            
    async def wait_for_instance_ready(self, instance_id: str, timeout: int = 600) -> bool:
        """Wait for EC2 instance to be ready"""
        waiter = self.ec2_client.get_waiter('instance_status_ok')
        try:
            waiter.wait(
                InstanceIds=[instance_id],
                WaiterConfig={'Delay': 15, 'MaxAttempts': timeout // 15}
            )
            logger.info(f"AWS instance {instance_id} is ready")
            return True
        except Exception as e:
            logger.error(f"AWS instance {instance_id} failed to become ready: {e}")
            return False
            
    async def get_instance_ip(self, instance_id: str) -> str:
        """Get EC2 instance public IP"""
        response = self.ec2_client.describe_instances(InstanceIds=[instance_id])
        instance = response['Reservations'][0]['Instances'][0]
        return instance.get('PublicIpAddress', instance.get('PrivateIpAddress'))
        
    async def run_command_on_instance(self, instance_id: str, command: str) -> Tuple[int, str, str]:
        """Run command via SSH"""
        try:
            # Get instance IP
            ip_address = await self.get_instance_ip(instance_id)
            
            # Try different SSH users for ScyllaDB images
            ssh_users = ['scyllaadm', 'centos', 'ubuntu', 'ec2-user', 'admin']
            
            for user in ssh_users:
                # SSH command with error handling
                ssh_cmd = [
                    'ssh', '-o', 'StrictHostKeyChecking=no', 
                    '-o', 'UserKnownHostsFile=/dev/null',
                    '-o', 'ConnectTimeout=30',
                    '-o', 'ServerAliveInterval=60',
                    '-o', 'ServerAliveCountMax=3',
                    '-o', 'BatchMode=yes',  # Don't prompt for passwords
                    '-o', 'PasswordAuthentication=no'
                ]
                
                # Add SSH key if available
                key_added = False
                if self.key_name:
                    # Try different key file formats
                    key_paths = [
                        os.path.expanduser(f'~/.ssh/{self.key_name}.pem'),
                        os.path.expanduser(f'~/.ssh/{self.key_name}'),
                        os.path.expanduser(f'~/.ssh/{self.key_name}.key')
                    ]
                    
                    for key_path in key_paths:
                        if os.path.exists(key_path):
                            ssh_cmd.extend(['-i', key_path])
                            key_added = True
                            logger.debug(f"Using SSH key: {key_path}")
                            break
                
                if not key_added:
                    # Try default SSH keys
                    default_keys = [
                        os.path.expanduser('~/.ssh/id_rsa'),
                        os.path.expanduser('~/.ssh/id_ed25519'),
                        os.path.expanduser('~/.ssh/id_ecdsa')
                    ]
                    
                    for key_path in default_keys:
                        if os.path.exists(key_path):
                            ssh_cmd.extend(['-i', key_path])
                            logger.debug(f"Using default SSH key: {key_path}")
                            break
                
                # Add user and target
                ssh_cmd.extend([f'{user}@{ip_address}', command])
                
                logger.info(f"Trying SSH connection to AWS instance {instance_id} ({ip_address}) as user '{user}'")
                logger.debug(f"SSH command: {' '.join(ssh_cmd[:ssh_cmd.index(f'{user}@{ip_address}')])}")
                
                # Run SSH command with optional live output streaming
                if DEBUG_LIVE_MODE:
                    # Stream output live for debug mode
                    logger.info(f"🔴 LIVE OUTPUT from {instance_id} ({user}@{ip_address}):")
                    logger.info("=" * 60)
                    
                    process = await asyncio.create_subprocess_exec(
                        *ssh_cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.STDOUT  # Merge stderr into stdout for live streaming
                    )
                    
                    stdout_lines = []
                    
                    # Stream output line by line
                    async for line in process.stdout:
                        line_str = line.decode('utf-8', errors='replace').rstrip('\n\r')
                        if line_str:  # Only print non-empty lines
                            print(f"📟 {line_str}")
                            stdout_lines.append(line_str)
                    
                    await process.wait()
                    return_code = process.returncode
                    stdout_str = '\n'.join(stdout_lines)
                    stderr_str = ""  # Merged with stdout in live mode
                    
                    logger.info("=" * 60)
                    logger.info(f"🔴 LIVE OUTPUT COMPLETE (return code: {return_code})")
                    
                else:
                    # Normal execution without live streaming
                    process = await asyncio.create_subprocess_exec(
                        *ssh_cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    
                    stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=600)
                    return_code = process.returncode
                    
                    stdout_str = stdout.decode('utf-8', errors='replace')
                    stderr_str = stderr.decode('utf-8', errors='replace')
                
                if return_code == 0 or 'Permission denied' not in stderr_str:
                    logger.info(f"Successfully connected as user '{user}'")
                    logger.debug(f"Command completed with return code {return_code}")
                    return return_code, stdout_str, stderr_str
                else:
                    logger.debug(f"SSH connection failed for user '{user}': {stderr_str}")
                    continue
            
            # If all users failed, return the last error
            logger.error(f"SSH connection failed for all attempted users: {ssh_users}")
            return 1, "", f"SSH connection failed for all users: {ssh_users}. " + \
                          f"Make sure your SSH key is properly configured and accessible."
            
        except asyncio.TimeoutError:
            logger.error(f"Command timeout on AWS instance {instance_id}")
            return 1, "", "Command timed out"
        except Exception as e:
            logger.error(f"SSH command failed on AWS instance {instance_id}: {e}")
            return 1, "", str(e)
        
    def get_instance_types_by_family(self, instance_family: str) -> List[str]:
        """Get available instance types for a given family by querying AWS API"""
        try:
            if self.dry_run:
                # For dry runs, return some sample types for testing
                return [f"{instance_family}.large", f"{instance_family}.xlarge"]
            
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
                return []
                
            # Sort instance types for consistent ordering
            instance_types.sort()
            logger.info(f"Found {len(instance_types)} instance types for family '{instance_family}': {', '.join(instance_types)}")
            
            return instance_types
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            if error_code == 'UnauthorizedOperation':
                raise RuntimeError(f"Insufficient permissions to describe instance types. Please ensure your AWS credentials have 'ec2:DescribeInstanceTypes' permission.")
            else:
                raise RuntimeError(f"Failed to discover instance types for family '{instance_family}': {e}")
        except Exception as e:
            raise RuntimeError(f"Failed to discover instance types for family '{instance_family}': {e}")

    async def terminate_instance(self, instance_id: str) -> None:
        """Terminate EC2 instance"""
        try:
            self.ec2_client.terminate_instances(InstanceIds=[instance_id])
            logger.info(f"Terminated AWS instance {instance_id}")
        except ClientError as e:
            logger.error(f"Failed to terminate AWS instance {instance_id}: {e}")

class GCPProvider(CloudProviderInterface):
    """Google Cloud Platform provider implementation"""
    
    def __init__(self, region: str, project_id: str, zone: str, dry_run: bool = False):
        super().__init__(region)
        if not compute_v1:
            raise ImportError("google-cloud-compute is required for GCP operations")
        self.project_id = project_id
        self.zone = zone
        self.dry_run = dry_run
        
        if not dry_run:
            try:
                self.compute_client = compute_v1.InstancesClient()
                # Test credentials by making a simple API call
                request = compute_v1.ListInstancesRequest(project=project_id, zone=zone)
                list(self.compute_client.list(request=request))
            except DefaultCredentialsError as e:
                raise RuntimeError(f"GCP credentials not configured: {e}")
        else:
            # For dry runs, create placeholder client
            self.compute_client = None
            
    async def create_instance(self, config: InstanceConfig) -> str:
        """Create GCE instance"""
        instance_body = {
            'name': f'scylla-io-benchmark-{config.instance_type.replace(".", "-").replace("_", "-").lower()}',
            'machine_type': f'zones/{self.zone}/machineTypes/{config.instance_type}',
            'disks': [
                {
                    'boot': True,
                    'auto_delete': True,
                    'initialize_params': {
                        'source_image': config.image_id,
                        'disk_type': f'zones/{self.zone}/diskTypes/pd-ssd',
                        'disk_size_gb': '20'
                    }
                }
            ],
            'network_interfaces': [
                {
                    'network': 'global/networks/default',
                    'access_configs': [
                        {
                            'type': 'ONE_TO_ONE_NAT',
                            'name': 'External NAT'
                        }
                    ]
                }
            ],
            'labels': {
                'purpose': 'scylla-io-benchmark',
                'auto-terminate': 'true'
            }
        }
        
        # Add local SSDs for supported instance types
        if any(family in config.instance_type for family in ['n1', 'n2', 'n2d', 'c2']):
            instance_body['disks'].append({
                'auto_delete': True,
                'interface': 'NVME',
                'type': 'SCRATCH',
                'initialize_params': {
                    'disk_type': f'zones/{self.zone}/diskTypes/local-ssd'
                }
            })
        
        if config.user_data:
            instance_body['metadata'] = {
                'items': [
                    {
                        'key': 'startup-script',
                        'value': config.user_data
                    }
                ]
            }
            
        request = compute_v1.InsertInstanceRequest(
            project=self.project_id,
            zone=self.zone,
            instance_resource=instance_body
        )
        
        try:
            operation = self.compute_client.insert(request=request)
            instance_name = instance_body['name']
            logger.info(f"Created GCP instance {instance_name} of type {config.instance_type}")
            return instance_name
        except Exception as e:
            raise RuntimeError(f"Failed to create GCP instance: {e}")
            
    async def wait_for_instance_ready(self, instance_id: str, timeout: int = 600) -> bool:
        """Wait for GCE instance to be ready"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                request = compute_v1.GetInstanceRequest(
                    project=self.project_id,
                    zone=self.zone,
                    instance=instance_id
                )
                instance = self.compute_client.get(request=request)
                if instance.status == 'RUNNING':
                    logger.info(f"GCP instance {instance_id} is ready")
                    return True
            except Exception as e:
                logger.debug(f"Waiting for GCE instance {instance_id}: {e}")
            await asyncio.sleep(15)
        
        logger.error(f"GCP instance {instance_id} failed to become ready within {timeout}s")
        return False
        
    async def get_instance_ip(self, instance_id: str) -> str:
        """Get GCE instance external IP"""
        request = compute_v1.GetInstanceRequest(
            project=self.project_id,
            zone=self.zone,
            instance=instance_id
        )
        instance = self.compute_client.get(request=request)
        
        for interface in instance.network_interfaces:
            for access_config in interface.access_configs:
                if access_config.nat_i_p:
                    return access_config.nat_i_p
        
        # Fallback to internal IP
        return instance.network_interfaces[0].network_i_p
        
    async def run_command_on_instance(self, instance_id: str, command: str) -> Tuple[int, str, str]:
        """Run command via gcloud SSH"""
        try:
            # Use gcloud SSH to connect to the instance
            gcloud_cmd = [
                'gcloud', 'compute', 'ssh', instance_id,
                '--project', self.project_id,
                '--zone', self.zone,
                '--ssh-flag=-o StrictHostKeyChecking=no',
                '--ssh-flag=-o UserKnownHostsFile=/dev/null',
                '--ssh-flag=-o ConnectTimeout=30',
                '--command', command
            ]
            
            logger.info(f"Running command on GCP instance {instance_id}: {command}")
            
            # Run gcloud SSH command with optional live output streaming
            if DEBUG_LIVE_MODE:
                # Stream output live for debug mode
                logger.info(f"🔴 LIVE OUTPUT from GCP {instance_id}:")
                logger.info("=" * 60)
                
                process = await asyncio.create_subprocess_exec(
                    *gcloud_cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.STDOUT  # Merge stderr into stdout for live streaming
                )
                
                stdout_lines = []
                
                # Stream output line by line
                async for line in process.stdout:
                    line_str = line.decode('utf-8', errors='replace').rstrip('\n\r')
                    if line_str:  # Only print non-empty lines
                        print(f"📟 {line_str}")
                        stdout_lines.append(line_str)
                
                await process.wait()
                return_code = process.returncode
                stdout_str = '\n'.join(stdout_lines)
                stderr_str = ""  # Merged with stdout in live mode
                
                logger.info("=" * 60)
                logger.info(f"🔴 LIVE OUTPUT COMPLETE (return code: {return_code})")
                
            else:
                # Normal execution without live streaming
                process = await asyncio.create_subprocess_exec(
                    *gcloud_cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=600)
                return_code = process.returncode
                
                stdout_str = stdout.decode('utf-8', errors='replace')
                stderr_str = stderr.decode('utf-8', errors='replace')
            
            logger.debug(f"Command completed with return code {return_code}")
            return return_code, stdout_str, stderr_str
            
        except asyncio.TimeoutError:
            logger.error(f"Command timeout on GCP instance {instance_id}")
            return 1, "", "Command timed out"
        except Exception as e:
            logger.error(f"gcloud SSH command failed on GCP instance {instance_id}: {e}")
            return 1, "", str(e)
        
    async def terminate_instance(self, instance_id: str) -> None:
        """Delete GCE instance"""
        try:
            request = compute_v1.DeleteInstanceRequest(
                project=self.project_id,
                zone=self.zone,
                instance=instance_id
            )
            self.compute_client.delete(request=request)
            logger.info(f"Terminated GCE instance {instance_id}")
        except Exception as e:
            logger.error(f"Failed to terminate GCE instance {instance_id}: {e}")

class AzureProvider(CloudProviderInterface):
    """Microsoft Azure provider implementation"""
    
    def __init__(self, region: str, subscription_id: str, resource_group: str, dry_run: bool = False):
        super().__init__(region)
        if not DefaultAzureCredential:
            raise ImportError("azure-mgmt-compute and azure-identity are required for Azure operations")
        self.subscription_id = subscription_id
        self.resource_group = resource_group
        self.dry_run = dry_run
        
        if not dry_run:
            try:
                credential = DefaultAzureCredential()
                self.compute_client = ComputeManagementClient(credential, subscription_id)
                self.network_client = NetworkManagementClient(credential, subscription_id)
                self.resource_client = ResourceManagementClient(credential, subscription_id)
                # Test credentials
                list(self.resource_client.resource_groups.list())
            except ClientAuthenticationError as e:
                raise RuntimeError(f"Azure credentials not configured: {e}")
        else:
            # For dry runs, create placeholder clients
            self.compute_client = None
            self.network_client = None
            self.resource_client = None
            
    async def create_instance(self, config: InstanceConfig) -> str:
        """Create Azure VM"""
        vm_name = f'scylla-io-benchmark-{config.instance_type.replace("_", "-").lower()}'
        
        # Create VM parameters
        vm_parameters = {
            'location': self.region,
            'os_profile': {
                'computer_name': vm_name,
                'admin_username': 'scylla',
                'disable_password_authentication': True,
                'linux_configuration': {
                    'disable_password_authentication': True,
                    'ssh': {
                        'public_keys': [
                            {
                                'path': '/home/scylla/.ssh/authorized_keys',
                                'key_data': config.key_name or 'ssh-rsa AAAAB3NzaC1yc2EAAAA...'  # Placeholder
                            }
                        ]
                    }
                }
            },
            'hardware_profile': {
                'vm_size': config.instance_type
            },
            'storage_profile': {
                'image_reference': {
                    'id': config.image_id
                },
                'os_disk': {
                    'create_option': 'FromImage',
                    'managed_disk': {
                        'storage_account_type': 'Premium_LRS'
                    }
                }
            },
            'network_profile': {
                'network_interfaces': [
                    {
                        'id': f'/subscriptions/{self.subscription_id}/resourceGroups/{self.resource_group}/providers/Microsoft.Network/networkInterfaces/{vm_name}-nic'
                    }
                ]
            },
            'tags': {
                'Purpose': 'scylla-io-benchmark',
                'AutoTerminate': 'true'
            }
        }
        
        if config.user_data:
            vm_parameters['os_profile']['custom_data'] = config.user_data
            
        try:
            # Create network interface first (simplified - assumes existing vnet/subnet)
            # In practice, you'd need to create these resources
            
            operation = self.compute_client.virtual_machines.begin_create_or_update(
                self.resource_group,
                vm_name,
                vm_parameters
            )
            
            logger.info(f"Created Azure VM {vm_name} of type {config.instance_type}")
            return vm_name
        except Exception as e:
            raise RuntimeError(f"Failed to create Azure VM: {e}")
            
    async def wait_for_instance_ready(self, instance_id: str, timeout: int = 600) -> bool:
        """Wait for Azure VM to be ready"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                vm = self.compute_client.virtual_machines.get(
                    self.resource_group,
                    instance_id,
                    expand='instanceView'
                )
                if vm.instance_view and any(
                    status.code == 'PowerState/running' 
                    for status in vm.instance_view.statuses
                ):
                    logger.info(f"Azure VM {instance_id} is ready")
                    return True
            except Exception as e:
                logger.debug(f"Waiting for Azure VM {instance_id}: {e}")
            await asyncio.sleep(15)
        
        logger.error(f"Azure VM {instance_id} failed to become ready within {timeout}s")
        return False
        
    async def get_instance_ip(self, instance_id: str) -> str:
        """Get Azure VM public IP"""
        try:
            # Get VM network interface
            vm = self.compute_client.virtual_machines.get(
                self.resource_group,
                instance_id
            )
            
            if vm.network_profile and vm.network_profile.network_interfaces:
                nic_id = vm.network_profile.network_interfaces[0].id
                nic_name = nic_id.split('/')[-1]
                
                # Get network interface details
                nic = self.network_client.network_interfaces.get(
                    self.resource_group,
                    nic_name
                )
                
                # Get public IP if available
                if nic.ip_configurations:
                    ip_config = nic.ip_configurations[0]
                    if ip_config.public_ip_address:
                        public_ip_name = ip_config.public_ip_address.id.split('/')[-1]
                        public_ip = self.network_client.public_ip_addresses.get(
                            self.resource_group,
                            public_ip_name
                        )
                        return public_ip.ip_address
                    
                    # Fallback to private IP
                    if ip_config.private_ip_address:
                        return ip_config.private_ip_address
                        
            return "unknown.azure.ip"
            
        except Exception as e:
            logger.error(f"Failed to get Azure VM IP for {instance_id}: {e}")
            return "unknown.azure.ip"
        
    async def run_command_on_instance(self, instance_id: str, command: str) -> Tuple[int, str, str]:
        """Run command via Azure SSH"""
        try:
            # Get instance IP first
            ip_address = await self.get_instance_ip(instance_id)
            
            # SSH command with error handling  
            ssh_cmd = [
                'ssh', '-o', 'StrictHostKeyChecking=no', 
                '-o', 'UserKnownHostsFile=/dev/null',
                '-o', 'ConnectTimeout=30',
                f'scyllaadm@{ip_address}', 
                command
            ]
            
            logger.info(f"Running command on Azure instance {instance_id} ({ip_address}): {command}")
            
            # Run SSH command with optional live output streaming
            if DEBUG_LIVE_MODE:
                # Stream output live for debug mode
                logger.info(f"🔴 LIVE OUTPUT from Azure {instance_id} ({ip_address}):")
                logger.info("=" * 60)
                
                process = await asyncio.create_subprocess_exec(
                    *ssh_cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.STDOUT  # Merge stderr into stdout for live streaming
                )
                
                stdout_lines = []
                
                # Stream output line by line
                async for line in process.stdout:
                    line_str = line.decode('utf-8', errors='replace').rstrip('\n\r')
                    if line_str:  # Only print non-empty lines
                        print(f"📟 {line_str}")
                        stdout_lines.append(line_str)
                
                await process.wait()
                return_code = process.returncode
                stdout_str = '\n'.join(stdout_lines)
                stderr_str = ""  # Merged with stdout in live mode
                
                logger.info("=" * 60)
                logger.info(f"🔴 LIVE OUTPUT COMPLETE (return code: {return_code})")
                
            else:
                # Normal execution without live streaming
                process = await asyncio.create_subprocess_exec(
                    *ssh_cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=600)
                return_code = process.returncode
                
                stdout_str = stdout.decode('utf-8', errors='replace')
                stderr_str = stderr.decode('utf-8', errors='replace')
            
            logger.debug(f"Command completed with return code {return_code}")
            return return_code, stdout_str, stderr_str
            
        except asyncio.TimeoutError:
            logger.error(f"Command timeout on Azure instance {instance_id}")
            return 1, "", "Command timed out"
        except Exception as e:
            logger.error(f"SSH command failed on Azure instance {instance_id}: {e}")
            return 1, "", str(e)
        
    async def terminate_instance(self, instance_id: str) -> None:
        """Delete Azure VM"""
        try:
            operation = self.compute_client.virtual_machines.begin_delete(
                self.resource_group,
                instance_id
            )
            operation.wait()
            logger.info(f"Terminated Azure VM {instance_id}")
        except Exception as e:
            logger.error(f"Failed to terminate Azure VM {instance_id}: {e}")

class CloudBenchmarkRunner:
    """Main orchestrator for cloud I/O benchmarking"""
    
    def __init__(self, provider: CloudProviderInterface, max_concurrent: int = 3, aws_config: dict = None):
        self.provider = provider
        self.max_concurrent = max_concurrent
        self.results: List[IoSetupResult] = []
        self.aws_config = aws_config or {}
        
    async def run_io_setup_on_instance(self, instance_id: str, instance_type: str, 
                                     run_number: int) -> IoSetupResult:
        """Read I/O metrics from io_properties.yaml, waiting for scylla-server if needed"""
        start_time = time.time()
        max_wait_time = 1200  # 20 minutes in seconds
        
        try:
            # Wait for instance to be ready
            if not await self.provider.wait_for_instance_ready(instance_id):
                return IoSetupResult(
                    cloud=self.provider.__class__.__name__.replace('Provider', '').lower(),
                    instance_type=instance_type,
                    instance_id=instance_id,
                    run_number=run_number,
                    success=False,
                    execution_time=time.time() - start_time,
                    error_message="Instance failed to become ready"
                )
            
            # Try to read I/O metrics from YAML file directly, with service checking
            read_iops, write_iops, read_bandwidth, write_bandwidth = await self._wait_and_read_io_metrics(
                instance_id, max_wait_time, start_time
            )
            
            execution_time = time.time() - start_time
            
            # Check if we got valid metrics
            if any(metric is not None for metric in [read_iops, write_iops, read_bandwidth, write_bandwidth]):
                logger.info(f"Successfully read metrics from YAML file: read_iops={read_iops}, write_iops={write_iops}, read_bw={read_bandwidth}, write_bw={write_bandwidth}")
                
                result = IoSetupResult(
                    cloud=self.provider.__class__.__name__.replace('Provider', '').lower(),
                    instance_type=instance_type,
                    instance_id=instance_id,
                    run_number=run_number,
                    success=True,
                    execution_time=execution_time,
                    read_iops=read_iops,
                    write_iops=write_iops,
                    read_bandwidth=read_bandwidth,
                    write_bandwidth=write_bandwidth
                )
            else:
                result = IoSetupResult(
                    cloud=self.provider.__class__.__name__.replace('Provider', '').lower(),
                    instance_type=instance_type,
                    instance_id=instance_id,
                    run_number=run_number,
                    success=False,
                    execution_time=execution_time,
                    error_message="Could not read I/O metrics from YAML file within 20 minutes"
                )
                
            logger.info(f"Completed run {run_number} on {instance_type} instance {instance_id}")
            return result
            
        except Exception as e:
            return IoSetupResult(
                cloud=self.provider.__class__.__name__.replace('Provider', '').lower(),
                instance_type=instance_type,
                instance_id=instance_id,
                run_number=run_number,
                success=False,
                execution_time=time.time() - start_time,
                error_message=str(e)
            )
            
    async def _wait_and_read_io_metrics(self, instance_id: str, max_wait_time: int, start_time: float) -> Tuple[Optional[float], Optional[float], Optional[float], Optional[float]]:
        """Wait for scylla-server to be up and read I/O metrics from YAML file"""
        check_interval = 10  # Check every 10 seconds
        
        logger.info(f"Attempting to read I/O metrics from /etc/scylla.d/io_properties.yaml")
        
        while (time.time() - start_time) < max_wait_time:
            # First, try to read the YAML file directly
            read_iops = await self._read_io_properties_file(instance_id, 'read_iops')
            write_iops = await self._read_io_properties_file(instance_id, 'write_iops')
            read_bandwidth = await self._read_io_properties_file(instance_id, 'read_bandwidth')
            write_bandwidth = await self._read_io_properties_file(instance_id, 'write_bandwidth')
            
            # If we got any metrics, return them
            if any(metric is not None for metric in [read_iops, write_iops, read_bandwidth, write_bandwidth]):
                logger.info(f"✅ Successfully read I/O metrics from YAML file")
                return read_iops, write_iops, read_bandwidth, write_bandwidth
            
            # If no metrics available, check if scylla-server is running
            elapsed_time = time.time() - start_time
            remaining_time = max_wait_time - elapsed_time
            
            logger.info(f"⏳ YAML file not ready yet, checking scylla-server status... ({remaining_time:.0f}s remaining)")
            
            # Check scylla-server service status
            service_status = await self._check_scylla_service_status(instance_id)
            
            if service_status == "active":
                logger.info("📊 scylla-server is active, waiting for I/O properties to be generated...")
                # Give scylla some time to generate the I/O properties file
                await asyncio.sleep(min(30, remaining_time/4))  # Wait up to 30 seconds or 1/4 of remaining time
            elif service_status == "inactive":
                logger.info("🔄 scylla-server is not active, waiting for service to start...")
                await asyncio.sleep(min(check_interval, remaining_time/10))
            else:
                logger.info(f"❓ scylla-server status: {service_status}, continuing to wait...")
                await asyncio.sleep(min(check_interval, remaining_time/10))
            
            # Check if we're running out of time
            if (time.time() - start_time) >= max_wait_time:
                break
        
        logger.warning(f"❌ Could not read I/O metrics within {max_wait_time/60:.1f} minutes")
        return None, None, None, None
    
    async def _check_scylla_service_status(self, instance_id: str) -> str:
        """Check the status of scylla-server service"""
        try:
            return_code, stdout, stderr = await self.provider.run_command_on_instance(
                instance_id, 
                "systemctl is-active scylla-server"
            )
            
            if return_code == 0:
                status = stdout.strip()
                logger.debug(f"scylla-server status: {status}")
                return status
            else:
                logger.debug(f"Failed to check scylla-server status: {stderr}")
                return "unknown"
                
        except Exception as e:
            logger.debug(f"Error checking scylla-server status: {e}")
            return "error"

    def _parse_metric(self, output: str, metric_name: str) -> Optional[float]:
        """Parse performance metrics from scylla_cloud_io_setup output"""
        try:
            # The scylla_cloud_io_setup script generates io_properties.yaml file
            # We look for specific patterns in output or try to read the generated file
            
            import re
            import yaml
            
            # First, try to parse direct output for metrics
            patterns = {
                'read_iops': r'read_iops[:\s]+(\d+)',
                'write_iops': r'write_iops[:\s]+(\d+)', 
                'read_bandwidth': r'read_bandwidth[:\s]+(\d+)',
                'write_bandwidth': r'write_bandwidth[:\s]+(\d+)'
            }
            
            if metric_name in patterns:
                match = re.search(patterns[metric_name], output, re.IGNORECASE)
                if match:
                    return float(match.group(1))
            
            # If direct parsing fails, look for YAML content in output
            yaml_pattern = r'disks:\s*\n\s*-\s*(.*?)(?=\n\S|\Z)'
            yaml_match = re.search(yaml_pattern, output, re.DOTALL)
            if yaml_match:
                try:
                    # Try to parse as YAML
                    yaml_content = f"disks:\n  - {yaml_match.group(1)}"
                    parsed = yaml.safe_load(yaml_content)
                    if 'disks' in parsed and parsed['disks']:
                        disk_props = parsed['disks'][0]
                        return disk_props.get(metric_name)
                except:
                    pass
            
            # Look for numeric values after metric names in a more flexible way
            flexible_pattern = rf'{metric_name}[^\d]*(\d+(?:\.\d+)?)'
            flex_match = re.search(flexible_pattern, output, re.IGNORECASE)
            if flex_match:
                return float(flex_match.group(1))
                
            return None
            
        except Exception as e:
            logger.debug(f"Failed to parse {metric_name} from output: {e}")
            return None
    
    async def _read_io_properties_file(self, instance_id: str, metric_name: str) -> Optional[float]:
        """Read metrics from the generated io_properties.yaml file on the instance"""
        try:
            # The scylla_cloud_io_setup script writes metrics to /etc/scylla.d/io_properties.yaml
            # We need to read this file from the instance
            # Use multiple commands to debug the file state
            debug_cmd = "ls -la /etc/scylla.d/ 2>/dev/null || echo 'directory not found'"
            read_cmd = "cat /etc/scylla.d/io_properties.yaml 2>/dev/null || echo 'file not found'"
            
            logger.debug(f"Reading YAML file for {metric_name} from instance {instance_id}")
            
            # First check if directory and file exist
            debug_code, debug_out, debug_err = await self.provider.run_command_on_instance(instance_id, debug_cmd)
            logger.debug(f"Directory listing: {debug_out}")
            
            # Then read the file
            return_code, stdout, stderr = await self.provider.run_command_on_instance(instance_id, read_cmd)
            logger.debug(f"YAML read command return_code={return_code}, stdout length={len(stdout)}")
            
            if return_code == 0 and 'file not found' not in stdout:
                logger.debug(f"YAML file content: {stdout[:200]}...")  # Log first 200 chars
                # Parse the YAML content
                import yaml
                try:
                    parsed = yaml.safe_load(stdout)
                    logger.debug(f"Parsed YAML structure: {parsed}")
                    if parsed and 'disks' in parsed and parsed['disks']:
                        disk_props = parsed['disks'][0]
                        value = disk_props.get(metric_name)
                        if value is not None:
                            logger.info(f"✅ Found {metric_name}={value} in io_properties.yaml")
                            return float(value)
                        else:
                            logger.warning(f"❌ {metric_name} not found in disk properties: {list(disk_props.keys())}")
                    else:
                        logger.warning(f"❌ Unexpected YAML structure: {parsed}")
                except yaml.YAMLError as e:
                    logger.error(f"❌ Error parsing YAML from io_properties.yaml: {e}")
            else:
                logger.warning(f"❌ YAML file not found or command failed: return_code={return_code}, stdout='{stdout[:100]}'")
            
        except Exception as e:
            logger.error(f"❌ Error reading io_properties.yaml: {e}")
            
        return None
        
    async def benchmark_instance_type(self, instance_type: str, image_id: str, 
                                    runs: int = 3) -> List[IoSetupResult]:
        """Run benchmark on a single instance type with multiple runs"""
        logger.info(f"Starting benchmark for {instance_type} with {runs} runs")
        
        # Create instance configuration
        config = InstanceConfig(
            instance_type=instance_type,
            image_id=image_id,
            key_name=self.aws_config.get('key_name'),
            security_group=self.aws_config.get('security_group_id'),
            subnet_id=self.aws_config.get('subnet_id'),
            user_data=self._get_user_data()
        )
        
        instance_results = []
        
        for run_number in range(1, runs + 1):
            try:
                # Create instance
                instance_id = await self.provider.create_instance(config)
                
                # Run benchmark
                result = await self.run_io_setup_on_instance(instance_id, instance_type, run_number)
                instance_results.append(result)
                self.results.append(result)
                
                # Clean up instance
                await self.provider.terminate_instance(instance_id)
                
                # Brief pause between runs
                await asyncio.sleep(10)
                
            except Exception as e:
                logger.error(f"Failed run {run_number} for {instance_type}: {e}")
                error_result = IoSetupResult(
                    cloud=self.provider.__class__.__name__.replace('Provider', '').lower(),
                    instance_type=instance_type,
                    instance_id="unknown",
                    run_number=run_number,
                    success=False,
                    execution_time=0,
                    error_message=str(e)
                )
                instance_results.append(error_result)
                self.results.append(error_result)
                
        return instance_results
        
    def _get_user_data(self) -> str:
        """Get cloud-init user data for instance setup"""
        return """#!/bin/bash
# Ensure ScyllaDB is properly installed and configured
systemctl enable scylla-server
systemctl start scylla-server

# Wait for system to be ready
sleep 30
"""
        
    async def benchmark_multiple_instance_types(self, instance_types: List[str], 
                                              image_id: str, runs: int = 3) -> None:
        """Run benchmarks across multiple instance types"""
        logger.info(f"Starting benchmarks for {len(instance_types)} instance types")
        
        # Create semaphore to limit concurrency
        semaphore = asyncio.Semaphore(self.max_concurrent)
        
        async def run_benchmark_with_semaphore(instance_type: str):
            """Run benchmark with concurrency limiting"""
            async with semaphore:
                try:
                    return await self.benchmark_instance_type(instance_type, image_id, runs)
                except Exception as e:
                    logger.error(f"Benchmark task failed for {instance_type}: {e}")
                    return []
        
        # Submit all benchmark tasks
        tasks = [
            run_benchmark_with_semaphore(instance_type)
            for instance_type in instance_types
        ]
        
        # Wait for all to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Log any exceptions
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Benchmark failed for {instance_types[i]}: {result}")
                    
    def export_results_to_csv(self, filename: str) -> None:
        """Export benchmark results to CSV file"""
        if not self.results:
            logger.warning("No results to export")
            return
            
        with open(filename, 'w', newline='') as csvfile:
            fieldnames = list(asdict(self.results[0]).keys())
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for result in self.results:
                writer.writerow(asdict(result))
                
        logger.info(f"Exported {len(self.results)} results to {filename}")
        
    def print_summary_table(self) -> None:
        """Print a summary table of benchmark results"""
        if not self.results:
            logger.warning("No results to display")
            return
            
        # Group results by instance type
        by_instance_type = {}
        for result in self.results:
            if result.instance_type not in by_instance_type:
                by_instance_type[result.instance_type] = []
            by_instance_type[result.instance_type].append(result)
            
        # Print summary table
        print("\n" + "="*100)
        print("SCYLLA I/O SETUP BENCHMARK RESULTS")
        print("="*100)
        print(f"{'Instance Type':<20} {'Success Rate':<12} {'Avg Time (s)':<12} {'Avg Read IOPS':<15} {'Avg Write IOPS':<15} {'Avg Read BW (MB/s)':<20} {'Avg Write BW (MB/s)':<20}")
        print("-"*100)
        
        for instance_type, results in sorted(by_instance_type.items()):
            successful_results = [r for r in results if r.success]
            success_rate = len(successful_results) / len(results) * 100
            
            if successful_results:
                avg_time = sum(r.execution_time for r in successful_results) / len(successful_results)
                avg_read_iops = sum(r.read_iops or 0 for r in successful_results) / len(successful_results)
                avg_write_iops = sum(r.write_iops or 0 for r in successful_results) / len(successful_results)
                avg_read_bw = sum(r.read_bandwidth or 0 for r in successful_results) / len(successful_results)
                avg_write_bw = sum(r.write_bandwidth or 0 for r in successful_results) / len(successful_results)
                
                print(f"{instance_type:<20} {success_rate:>8.1f}%    {avg_time:>8.1f}      {avg_read_iops:>11.0f}      {avg_write_iops:>11.0f}      {avg_read_bw:>15.1f}         {avg_write_bw:>15.1f}")
            else:
                print(f"{instance_type:<20} {success_rate:>8.1f}%    {'N/A':<8}      {'N/A':<11}      {'N/A':<11}      {'N/A':<15}         {'N/A':<15}")
                
        print("-"*100)
        print(f"Total instances tested: {len(self.results)}")
        overall_success_rate = len([r for r in self.results if r.success]) / len(self.results) * 100
        print(f"Overall success rate: {overall_success_rate:.1f}%")
        print("="*100)
        
    def analyze_results(self) -> None:
        """Analyze benchmark results and print detailed statistics"""
        if not self.results:
            logger.warning("No results to analyze")
            return
            
        # Group results by instance type
        by_instance_type = {}
        for result in self.results:
            if result.instance_type not in by_instance_type:
                by_instance_type[result.instance_type] = []
            by_instance_type[result.instance_type].append(result)
        
        print("\n" + "="*100)
        print("SCYLLA I/O SETUP BENCHMARK ANALYSIS")
        print("="*100)
        
        # Collect all metrics for ranking
        all_metrics = []
        
        for instance_type, results in sorted(by_instance_type.items()):
            successful_results = [r for r in results if r.success]
            
            if successful_results:
                # Calculate averages and standard deviations
                avg_time = statistics.mean([r.execution_time for r in successful_results])
                
                # Safe mean calculation with empty list checks
                read_iops_values = [r.read_iops for r in successful_results if r.read_iops is not None]
                write_iops_values = [r.write_iops for r in successful_results if r.write_iops is not None]
                read_bw_values = [r.read_bandwidth for r in successful_results if r.read_bandwidth is not None]
                write_bw_values = [r.write_bandwidth for r in successful_results if r.write_bandwidth is not None]
                
                avg_read_iops = statistics.mean(read_iops_values) if read_iops_values else 0
                avg_write_iops = statistics.mean(write_iops_values) if write_iops_values else 0
                avg_read_bw = statistics.mean(read_bw_values) if read_bw_values else 0
                avg_write_bw = statistics.mean(write_bw_values) if write_bw_values else 0
                
                # Calculate standard deviations (safe with empty list checks)
                stddev_time = statistics.stdev([r.execution_time for r in successful_results]) if len(successful_results) > 1 else 0
                stddev_read_iops = statistics.stdev(read_iops_values) if len(read_iops_values) > 1 else 0
                stddev_write_iops = statistics.stdev(write_iops_values) if len(write_iops_values) > 1 else 0
                
                # Calculate min/max values (safe with empty list checks)
                min_read_iops = min(read_iops_values, default=0)
                max_read_iops = max(read_iops_values, default=0)
                min_write_iops = min(write_iops_values, default=0)
                max_write_iops = max(write_iops_values, default=0)
                
                print(f"\nInstance Type: {instance_type}")
                print(f"  Success Rate: {len(successful_results)}/{len(results)} ({len(successful_results) / len(results) * 100:.1f}%)")
                print(f"  Execution Time: {avg_time:.2f}s ±{stddev_time:.2f}s")
                print(f"  Read IOPS: {avg_read_iops:.0f} ±{stddev_read_iops:.0f} (range: {min_read_iops:.0f}-{max_read_iops:.0f})")
                print(f"  Write IOPS: {avg_write_iops:.0f} ±{stddev_write_iops:.0f} (range: {min_write_iops:.0f}-{max_write_iops:.0f})")
                print(f"  Read Bandwidth: {avg_read_bw:.1f} MB/s")
                print(f"  Write Bandwidth: {avg_write_bw:.1f} MB/s")
                
                # Store for ranking
                all_metrics.append({
                    'instance_type': instance_type,
                    'avg_read_iops': avg_read_iops,
                    'avg_write_iops': avg_write_iops,
                    'avg_read_bw': avg_read_bw,
                    'avg_write_bw': avg_write_bw,
                    'avg_time': avg_time,
                    'success_rate': len(successful_results) / len(results) * 100
                })
            else:
                print(f"\nInstance Type: {instance_type}")
                print(f"  Success Rate: 0/{len(results)} (0.0%)")
                print("  All benchmark runs failed")
        
        # Performance rankings
        if all_metrics:
            print("\n" + "="*100)
            print("PERFORMANCE RANKINGS")
            print("="*100)
            
            # Top performers by Read IOPS
            print("\n🏆 Top 5 by Read IOPS:")
            top_read_iops = sorted(all_metrics, key=lambda x: x['avg_read_iops'], reverse=True)[:5]
            for i, metric in enumerate(top_read_iops, 1):
                print(f"  {i}. {metric['instance_type']:<20} - {metric['avg_read_iops']:>10.0f} IOPS")
                
            # Top performers by Write IOPS
            print("\n🏆 Top 5 by Write IOPS:")
            top_write_iops = sorted(all_metrics, key=lambda x: x['avg_write_iops'], reverse=True)[:5]
            for i, metric in enumerate(top_write_iops, 1):
                print(f"  {i}. {metric['instance_type']:<20} - {metric['avg_write_iops']:>10.0f} IOPS")
                
            # Best price/performance (would need cost data)
            print("\n⚡ Fastest Execution Time:")
            fastest = sorted(all_metrics, key=lambda x: x['avg_time'])[:5]
            for i, metric in enumerate(fastest, 1):
                print(f"  {i}. {metric['instance_type']:<20} - {metric['avg_time']:>8.2f}s")
                
            # Most reliable (highest success rate)
            print("\n✅ Most Reliable (Highest Success Rate):")
            most_reliable = sorted(all_metrics, key=lambda x: x['success_rate'], reverse=True)[:5]
            for i, metric in enumerate(most_reliable, 1):
                print(f"  {i}. {metric['instance_type']:<20} - {metric['success_rate']:>6.1f}%")
        
        print("\n" + "="*100)
        print("END OF ANALYSIS")
        print("="*100)



def create_cloud_provider(cloud: str, region: str, **kwargs) -> CloudProviderInterface:
    """Factory function to create cloud provider instances"""
    dry_run = kwargs.get('dry_run', False)
    
    if cloud.lower() == 'aws':
        key_name = kwargs.get('key_name')
        return AWSProvider(region, dry_run=dry_run, key_name=key_name)
    elif cloud.lower() == 'gcp':
        project_id = kwargs.get('project_id')
        zone = kwargs.get('zone', f'{region}-a')
        if not project_id:
            raise ValueError("project_id is required for GCP")
        return GCPProvider(region, project_id, zone, dry_run=dry_run)
    elif cloud.lower() == 'azure':
        subscription_id = kwargs.get('subscription_id')
        resource_group = kwargs.get('resource_group', 'scylla-benchmark')
        if not subscription_id:
            raise ValueError("subscription_id is required for Azure")
        return AzureProvider(region, subscription_id, resource_group, dry_run=dry_run)
    else:
        raise ValueError(f"Unsupported cloud provider: {cloud}")

def main():
    parser = argparse.ArgumentParser(
        description="Cloud I/O Benchmark for ScyllaDB instances",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --cloud aws --region us-east-1 --image ami-12345678 --instance-family i4i --runs 3
  %(prog)s --cloud gcp --region us-central1 --project-id my-project --image projects/scylla-images/global/images/scylladb-5-2-1 --instance-family n2
  %(prog)s --cloud azure --region eastus --subscription-id 12345 --image /subscriptions/.../images/scylladb/versions/5.2.1 --instance-family L8s_v3
        """
    )
    
    parser.add_argument('--cloud', required=True, choices=['aws', 'gcp', 'azure'],
                       help='Cloud provider to use')
    parser.add_argument('--region', required=True,
                       help='Cloud region to use')
    parser.add_argument('--image', required=True,
                       help='ScyllaDB image ID/name to use')
    parser.add_argument('--instance-family',
                       help='Instance family to benchmark (e.g., i4i, n2, L8s_v3)')
    parser.add_argument('--instance-types', nargs='+',
                       help='Specific instance types to test (overrides --instance-family)')
    parser.add_argument('--runs', type=int, default=3,
                       help='Number of runs per instance type (default: 3)')
    parser.add_argument('--max-concurrent', type=int, default=3,
                       help='Maximum concurrent instances (default: 3)')
    parser.add_argument('--output-csv', default='scylla_io_benchmark_results.csv',
                       help='Output CSV file for results')
    
    # Cloud-specific arguments
    parser.add_argument('--project-id', help='GCP project ID (required for GCP)')
    parser.add_argument('--zone', help='GCP zone (default: {region}-a)')
    parser.add_argument('--subscription-id', help='Azure subscription ID (required for Azure)')
    parser.add_argument('--resource-group', default='scylla-benchmark',
                       help='Azure resource group (default: scylla-benchmark)')
    
    # AWS-specific arguments
    parser.add_argument('--aws-vpc-id', help='AWS VPC ID to use (auto-detected if not specified)')
    parser.add_argument('--aws-subnet-id', help='AWS subnet ID to use (auto-detected if not specified)')
    parser.add_argument('--aws-security-group-id', help='AWS security group ID to use (auto-created if not specified)')
    parser.add_argument('--aws-key-name', help='AWS EC2 key pair name for SSH access')
    
    parser.add_argument('--dry-run', action='store_true',
                       help='Print configuration and exit without running tests')
    parser.add_argument('--show-costs', action='store_true',
                       help='Show cost estimation for benchmark run')
    parser.add_argument('--debug', action='store_true',
                       help='Enable debug logging')
    parser.add_argument('--debug-live', action='store_true',
                       help='Enable debug logging with real-time command output streaming (shows live output from instances)')
    
    args = parser.parse_args()
    
    if args.debug or args.debug_live:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Set global debug live mode flag
    global DEBUG_LIVE_MODE
    DEBUG_LIVE_MODE = args.debug_live
    
    # Validate that either instance-family or instance-types is provided
    if not args.instance_types and not args.instance_family:
        parser.error("Either --instance-family or --instance-types must be specified")
        
    # Determine instance types to test
    if args.instance_types:
        instance_types = args.instance_types
    else:
        # Use dynamic instance type discovery for AWS
        if args.cloud.lower() == 'aws':
            # Create a temporary AWS provider to discover instance types
            temp_provider = create_cloud_provider(
                args.cloud,
                args.region,
                project_id=args.project_id,
                zone=args.zone,
                subscription_id=args.subscription_id,
                resource_group=args.resource_group,
                dry_run=args.dry_run,
                key_name=args.aws_key_name
            )
            instance_types = temp_provider.get_instance_types_by_family(args.instance_family)
        else:
            # For non-AWS providers, use fallback hardcoded mapping
            # TODO: Implement dynamic discovery for GCP and Azure
            fallback_types = {
                'gcp': {
                    'n1': ['n1-standard-2', 'n1-standard-4', 'n1-standard-8', 'n1-standard-16', 'n1-standard-32', 'n1-highmem-8', 'n1-highmem-16'],
                    'n2': ['n2-standard-2', 'n2-standard-4', 'n2-standard-8', 'n2-standard-16', 'n2-standard-32', 'n2-highmem-4', 'n2-highmem-8'],
                    'n2d': ['n2d-standard-2', 'n2d-standard-4', 'n2d-standard-8', 'n2d-standard-16', 'n2d-standard-32', 'n2d-highmem-4', 'n2d-highmem-8'],
                    'c2': ['c2-standard-4', 'c2-standard-8', 'c2-standard-16', 'c2-standard-30'],
                    'm1': ['m1-megamem-96'],
                },
                'azure': {
                    'L8s_v3': ['Standard_L8s_v3'],
                    'L16s_v3': ['Standard_L16s_v3'],
                    'L32s_v3': ['Standard_L32s_v3'],
                    'L48s_v3': ['Standard_L48s_v3'], 
                    'L64s_v3': ['Standard_L64s_v3'],
                    'L80s_v3': ['Standard_L80s_v3'],
                    'Lsv2': ['Standard_L8s_v2', 'Standard_L16s_v2', 'Standard_L32s_v2'],
                }
            }
            instance_types = fallback_types.get(args.cloud, {}).get(args.instance_family, [])
            
        if not instance_types:
            logger.error(f"No supported instance types found for {args.cloud}/{args.instance_family}")
            if args.cloud.lower() == 'aws':
                logger.error(f"Possible solutions:")
                logger.error(f"  1. Check that the instance family '{args.instance_family}' exists in AWS")
                logger.error(f"  2. Verify that the instance family is available in region '{args.region}'")
                logger.error(f"  3. Try a different instance family (e.g., 'i4i', 'i3en', 'c5d')")
                logger.error(f"  4. Ensure your AWS credentials have 'ec2:DescribeInstanceTypes' permission")
            sys.exit(1)
            
    logger.info(f"Will test {len(instance_types)} instance types: {', '.join(instance_types)}")
    
    if args.dry_run:
        print("Dry run - configuration:")
        print(f"  Cloud: {args.cloud}")
        print(f"  Region: {args.region}")
        print(f"  Image: {args.image}")
        print(f"  Instance types: {instance_types}")
        print(f"  Runs per type: {args.runs}")
        print(f"  Max concurrent: {args.max_concurrent}")
        print(f"  Output file: {args.output_csv}")
        
        # Show cost estimation if available
        if COST_ESTIMATION_AVAILABLE:
            try:
                estimator = CostEstimator()
                estimator.print_cost_estimate(args.cloud, instance_types, args.runs, args.region)
            except Exception as e:
                print(f"\n⚠️  Cost estimation failed: {e}")
        else:
            print("\n💡 Install cost_estimator.py for cost estimation features")
        
        return
        
    try:
        # Create cloud provider
        provider = create_cloud_provider(
            args.cloud,
            args.region,
            project_id=args.project_id,
            zone=args.zone,
            subscription_id=args.subscription_id,
            resource_group=args.resource_group,
            dry_run=args.dry_run,
            key_name=args.aws_key_name  # Pass key name for AWS SSH connections
        )
        
        # Prepare AWS configuration if using AWS
        aws_config = {}
        if args.cloud.lower() == 'aws':
            aws_config = {
                'key_name': args.aws_key_name,
                'security_group_id': args.aws_security_group_id,
                'subnet_id': args.aws_subnet_id,
                'vpc_id': args.aws_vpc_id
            }
        
        # Create benchmark runner
        runner = CloudBenchmarkRunner(provider, args.max_concurrent, aws_config)
        
        # Run benchmarks
        asyncio.run(
            runner.benchmark_multiple_instance_types(
                instance_types, 
                args.image, 
                args.runs
            )
        )
        
        # Export and display results
        runner.export_results_to_csv(args.output_csv)
        runner.print_summary_table()
        runner.analyze_results()
        
    except Exception as e:
        error_msg = str(e)
        if "credentials not configured" in error_msg.lower():
            logger.error(f"❌ {error_msg}")
            logger.error("")
            logger.error("💡 To fix this issue:")
            logger.error("   1. Run with --dry-run to test configuration without credentials")
            logger.error("   2. Configure your cloud credentials:")
            logger.error("      • AWS: run 'aws configure' or set AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY")
            logger.error("      • GCP: run 'gcloud auth login' and 'gcloud config set project PROJECT_ID'")
            logger.error("      • Azure: run 'az login'")
            logger.error("   3. See CREDENTIALS_SETUP.md for detailed setup instructions")
            logger.error("")
        else:
            logger.error(f"❌ Benchmark failed: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
