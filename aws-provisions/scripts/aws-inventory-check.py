#!/usr/bin/env python3

"""
AWS Inventory Check

Cross-platform AWS inventory utility.

Usage:
    python3 aws-inventory-check.py --profile dev
    python aws-inventory-check.py --profile dev

Requirements:
    Python 3.9+
    boto3
"""

import argparse
import sys
import re

import boto3
from botocore.exceptions import BotoCoreError, ClientError, ProfileNotFound


# ============================================================
# CONFIGURATION
# ============================================================

DEFAULT_REGION = "us-east-1"
INVENTORY_ERRORS = 0


# ============================================================
# ARGUMENT PARSING
# ============================================================

def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Collect an AWS resource inventory for a selected profile."
    )

    parser.add_argument(
        "--profile",
        required=True,
        help="AWS CLI profile to use, e.g. dev",
    )

    return parser.parse_args()


# ============================================================
# OUTPUT / PROGRESS
# ============================================================

def progress(percent, message):
    """
    Send progress/status messages to stderr so they remain
    visible in the terminal when stdout is redirected to a file.
    """
    print(
        f"[{percent:3d}%] {message}",
        file=sys.stderr,
    )


def terminal_print(message=""):
    """
    Send informational messages to the terminal instead of
    the inventory output file.
    """
    print(message, file=sys.stderr)


def terminal_input(prompt):
    """
    Display an interactive prompt in the terminal instead of
    sending the prompt to stdout.
    """
    print(prompt, end="", flush=True, file=sys.stderr)
    return input().strip()


def print_section(title):
    print()
    print(f"=== {title} ===")


# ============================================================
# AWS HELPERS
# ============================================================

def call_aws(description, function, **kwargs):
    """
    Execute an AWS API call and track failures without
    terminating the entire inventory.
    """
    global INVENTORY_ERRORS

    try:
        response = function(**kwargs)
        return response

    except (ClientError, BotoCoreError) as error:
        INVENTORY_ERRORS = 1

        print(
            f"ERROR collecting {description}: {error}",
            file=sys.stderr,
        )

        return None


def print_values(response, key_path, empty_message="None"):
    """
    Print values from a nested AWS response.

    key_path is a list describing the response structure.
    """

    if not response:
        print(empty_message)
        return

    values = response

    for key in key_path:
        if isinstance(values, list):
            next_values = []

            for item in values:
                if isinstance(item, dict) and key in item:
                    next_values.append(item[key])

            values = next_values

        elif isinstance(values, dict):
            values = values.get(key, [])

        else:
            values = []

    if not values:
        print(empty_message)
        return

    if isinstance(values, list):
        for value in values:
            if isinstance(value, dict):
                print(value)
            else:
                print(value)
    else:
        print(values)


def print_objects(response, collection_key, fields):
    """
    Print selected fields from a collection of AWS objects.
    """

    if not response:
        print("None")
        return

    objects = response.get(collection_key, [])

    if not objects:
        print("None")
        return

    headers = list(fields.values())

    rows = []

    for obj in objects:
        row = []

        for source_key in fields:
            value = obj.get(source_key, "")

            if isinstance(value, dict):
                value = value.get("Name", value)

            row.append(str(value))

        rows.append(row)

    widths = [
        max(len(headers[index]), *(len(row[index]) for row in rows))
        for index in range(len(headers))
    ]

    print(
        "  ".join(
            headers[index].ljust(widths[index])
            for index in range(len(headers))
        )
    )

    print(
        "  ".join(
            "-" * widths[index]
            for index in range(len(headers))
        )
    )

    for row in rows:
        print(
            "  ".join(
                row[index].ljust(widths[index])
                for index in range(len(headers))
            )
        )


# ============================================================
# REGION DISCOVERY
# ============================================================

def get_available_regions(ec2_client):
    response = call_aws(
        "AWS regions",
        ec2_client.describe_regions,
        AllRegions=False,
    )

    if not response:
        return []

    return [
        region["RegionName"]
        for region in response.get("Regions", [])
        if "RegionName" in region
    ]


def select_region(available_regions):
    terminal_print()
    terminal_print("=== AWS Region Selection ===")
    terminal_print()
    terminal_print("Option 1: Input the Region")
    terminal_print(f"Option 2: Use default ({DEFAULT_REGION})")
    terminal_print()

    while True:
        choice = terminal_input("Choose an option [1-2]: ")

        if choice == "1":
            attempts = 0

            while attempts < 3:
                region = terminal_input(
                    "Enter AWS Region (e.g. us-east-1): "
                )

                region_pattern = r"^[a-z]{2}(-gov)?-[a-z]+-[0-9]+$"

                if (
                    re.fullmatch(region_pattern, region)
                    and region in available_regions
                ):
                    terminal_print(f"Region accepted: {region}")
                    terminal_print()
                    return region

                attempts += 1

                terminal_print(
                    "Incorrect format or AWS region does not exist, "
                    "try again."
                )

                if attempts == 3:
                    terminal_print(
                        f"Maximum attempts reached. "
                        f"Using default region: {DEFAULT_REGION}"
                    )
                    terminal_print()
                    return DEFAULT_REGION

        elif choice == "2":
            terminal_print(
                f"Using default region: {DEFAULT_REGION}"
            )
            terminal_print()
            return DEFAULT_REGION

        else:
            terminal_print(
                "Invalid option. Please choose 1 or 2."
            )
            terminal_print()


# ============================================================
# AWS ACCOUNT INFORMATION
# ============================================================

def get_account_id(sts_client):
    response = call_aws(
        "AWS account identity",
        sts_client.get_caller_identity,
    )

    if not response:
        return "Unavailable"

    return response.get("Account", "Unavailable")


# ============================================================
# EC2 / VPC NETWORKING
# ============================================================

def collect_network_inventory(ec2_client):

    print_section("VPCs")

    response = call_aws(
        "VPCs",
        ec2_client.describe_vpcs,
    )

    print_values(response, ["Vpcs", "VpcId"])

    print_section("EC2 Instances")

    response = call_aws(
        "EC2 instances",
        ec2_client.describe_instances,
    )

    if response:
        instances = []

        for reservation in response.get("Reservations", []):
            instances.extend(
                reservation.get("Instances", [])
            )

        if instances:
            print_objects(
                {"Instances": instances},
                "Instances",
                {
                    "InstanceId": "ID",
                    "State": "STATE",
                },
            )
        else:
            print("None")
    else:
        print("None")

    print_section("VPC Endpoints")

    response = call_aws(
        "VPC endpoints",
        ec2_client.describe_vpc_endpoints,
    )

    print_objects(
        response,
        "VpcEndpoints",
        {
            "VpcEndpointId": "ID",
            "State": "STATE",
        },
    )

    print_section("Subnets")

    response = call_aws(
        "subnets",
        ec2_client.describe_subnets,
    )

    print_values(
        response,
        ["Subnets", "SubnetId"],
    )

    print_section("Route Tables")

    response = call_aws(
        "route tables",
        ec2_client.describe_route_tables,
    )

    print_values(
        response,
        ["RouteTables", "RouteTableId"],
    )

    print_section("Internet Gateways")

    response = call_aws(
        "internet gateways",
        ec2_client.describe_internet_gateways,
    )

    print_values(
        response,
        ["InternetGateways", "InternetGatewayId"],
    )

    print_section("Network ACLs (non-default)")

    response = call_aws(
        "network ACLs",
        ec2_client.describe_network_acls,
    )

    if response:
        non_default = [
            acl
            for acl in response.get("NetworkAcls", [])
            if not acl.get("IsDefault", True)
        ]

        if non_default:
            for acl in non_default:
                print(acl.get("NetworkAclId"))
        else:
            print("None")
    else:
        print("None")

    print_section("Security Groups (non-default)")

    response = call_aws(
        "security groups",
        ec2_client.describe_security_groups,
    )

    if response:
        groups = [
            group
            for group in response.get("SecurityGroups", [])
            if group.get("GroupName") != "default"
        ]

        print_objects(
            {"SecurityGroups": groups},
            "SecurityGroups",
            {
                "GroupId": "ID",
                "GroupName": "NAME",
            },
        )
    else:
        print("None")

    print_section("NAT Gateways")

    response = call_aws(
        "NAT gateways",
        ec2_client.describe_nat_gateways,
    )

    print_objects(
        response,
        "NatGateways",
        {
            "NatGatewayId": "ID",
            "State": "STATE",
        },
    )

    print_section("Elastic IPs")

    response = call_aws(
        "Elastic IPs",
        ec2_client.describe_addresses,
    )

    print_values(
        response,
        ["Addresses", "PublicIp"],
    )

    print_section("Network Interfaces")

    response = call_aws(
        "network interfaces",
        ec2_client.describe_network_interfaces,
    )

    print_objects(
        response,
        "NetworkInterfaces",
        {
            "NetworkInterfaceId": "ID",
            "Status": "STATUS",
        },
    )

    print_section("VPC Flow Logs")

    response = call_aws(
        "VPC flow logs",
        ec2_client.describe_flow_logs,
    )

    print_values(
        response,
        ["FlowLogs", "FlowLogId"],
    )

    print_section("EBS Volumes")

    response = call_aws(
        "EBS volumes",
        ec2_client.describe_volumes,
    )

    print_objects(
        response,
        "Volumes",
        {
            "VolumeId": "ID",
            "State": "STATE",
        },
    )

    print_section("Key Pairs")

    response = call_aws(
        "key pairs",
        ec2_client.describe_key_pairs,
    )

    print_values(
        response,
        ["KeyPairs", "KeyName"],
    )

    print_section("DHCP Options (non-default)")

    response = call_aws(
        "DHCP options",
        ec2_client.describe_dhcp_options,
    )

    print_values(
        response,
        ["DhcpOptions", "DhcpOptionsId"],
    )


# ============================================================
# RDS
# ============================================================

def collect_rds_inventory(rds_client):

    progress(
        30,
        "Collecting RDS resources..."
    )

    print_section("RDS Instances")

    response = call_aws(
        "RDS instances",
        rds_client.describe_db_instances,
    )

    print_values(
        response,
        ["DBInstances", "DBInstanceIdentifier"],
    )

    print_section("RDS Clusters")

    response = call_aws(
        "RDS clusters",
        rds_client.describe_db_clusters,
    )

    print_values(
        response,
        ["DBClusters", "DBClusterIdentifier"],
    )


# ============================================================
# LOAD BALANCERS
# ============================================================

def collect_load_balancer_inventory(elbv2_client):

    progress(
        40,
        "Collecting Load Balancer resources..."
    )

    print_section("Load Balancers")

    response = call_aws(
        "load balancers",
        elbv2_client.describe_load_balancers,
    )

    print_values(
        response,
        ["LoadBalancers", "LoadBalancerName"],
    )

    print_section("Target Groups")

    response = call_aws(
        "target groups",
        elbv2_client.describe_target_groups,
    )

    print_values(
        response,
        ["TargetGroups", "TargetGroupName"],
    )


# ============================================================
# LAMBDA
# ============================================================

def collect_lambda_inventory(lambda_client):

    progress(
        50,
        "Collecting Lambda resources..."
    )

    print_section("Lambda Functions")

    response = call_aws(
        "Lambda functions",
        lambda_client.list_functions,
    )

    print_values(
        response,
        ["Functions", "FunctionName"],
    )


# ============================================================
# SECRETS MANAGER
# ============================================================

def collect_secrets_inventory(secrets_client):

    progress(
        60,
        "Collecting Secrets Manager resources..."
    )

    print_section("Secrets")

    response = call_aws(
        "Secrets Manager secrets",
        secrets_client.list_secrets,
    )

    print_values(
        response,
        ["SecretList", "Name"],
    )


# ============================================================
# SAGEMAKER / S3
# ============================================================

def collect_sagemaker_s3_inventory(
    sagemaker_client,
    s3_client,
):

    progress(
        70,
        "Collecting SageMaker and S3 resources..."
    )

    print_section("SageMaker Domains")

    response = call_aws(
        "SageMaker domains",
        sagemaker_client.list_domains,
    )

    print_values(
        response,
        ["Domains", "DomainId"],
    )

    print_section("S3 Buckets")

    response = call_aws(
        "S3 buckets",
        s3_client.list_buckets,
    )

    print_values(
        response,
        ["Buckets", "Name"],
    )


# ============================================================
# CLOUDWATCH / WAF
# ============================================================

def collect_monitoring_inventory(
    cloudwatch_client,
    logs_client,
    waf_client,
):

    progress(
        80,
        "Collecting CloudWatch and WAF resources..."
    )

    print_section("CloudWatch Alarms")

    response = call_aws(
        "CloudWatch alarms",
        cloudwatch_client.describe_alarms,
    )

    print_values(
        response,
        ["MetricAlarms", "AlarmName"],
    )

    print_section("CloudWatch Log Groups")

    response = call_aws(
        "CloudWatch log groups",
        logs_client.describe_log_groups,
    )

    print_values(
        response,
        ["logGroups", "logGroupName"],
    )

    print_section("WAF IP Sets")

    response = call_aws(
        "WAF IP sets",
        waf_client.list_ip_sets,
        Scope="REGIONAL",
    )

    print_values(
        response,
        ["IPSets", "Name"],
    )


# ============================================================
# SNS / EVENTBRIDGE / BUDGETS
# ============================================================

def collect_messaging_inventory(
    sns_client,
    events_client,
    budgets_client,
    account_id,
):

    progress(
        90,
        "Collecting SNS, EventBridge, and Budgets resources..."
    )

    print_section("SNS Topics")

    response = call_aws(
        "SNS topics",
        sns_client.list_topics,
    )

    print_values(
        response,
        ["Topics", "TopicArn"],
    )

    print_section("EventBridge Rules")

    response = call_aws(
        "EventBridge rules",
        events_client.list_rules,
    )

    print_values(
        response,
        ["Rules", "Name"],
    )

    print_section("Budgets")

    if account_id == "Unavailable":
        print(
            "Unavailable because AWS account ID could not be determined."
        )
        return

    response = call_aws(
        "AWS Budgets",
        budgets_client.describe_budgets,
        AccountId=account_id,
    )

    print_values(
        response,
        ["Budgets", "BudgetName"],
    )


# ============================================================
# MAIN
# ============================================================

def main():

    global INVENTORY_ERRORS

    args = parse_arguments()

    try:
        session = boto3.Session(
            profile_name=args.profile
        )

        sts_client = session.client("sts")

        # Keep execution metadata in the terminal.
        terminal_print(
            "=== AWS INVENTORY CHECK ==="
        )
        terminal_print(
            f"Profile: {args.profile}"
        )

        account_id = get_account_id(
            sts_client
        )

        terminal_print(
            f"Account: {account_id}"
        )

        ec2_client = session.client(
            "ec2",
            region_name=DEFAULT_REGION,
        )

        available_regions = get_available_regions(
            ec2_client
        )

        if not available_regions:
            terminal_print(
                "ERROR: Unable to retrieve AWS regions."
            )
            terminal_print(
                "Check your AWS credentials, permissions, "
                "and default region."
            )
            return 1

        region = select_region(
            available_regions
        )

        # Create regional clients after region selection.
        ec2_client = session.client(
            "ec2",
            region_name=region,
        )

        rds_client = session.client(
            "rds",
            region_name=region,
        )

        elbv2_client = session.client(
            "elbv2",
            region_name=region,
        )

        lambda_client = session.client(
            "lambda",
            region_name=region,
        )

        secrets_client = session.client(
            "secretsmanager",
            region_name=region,
        )

        sagemaker_client = session.client(
            "sagemaker",
            region_name=region,
        )

        s3_client = session.client("s3")

        cloudwatch_client = session.client(
            "cloudwatch",
            region_name=region,
        )

        logs_client = session.client(
            "logs",
            region_name=region,
        )

        waf_client = session.client(
            "wafv2",
            region_name=region,
        )

        sns_client = session.client(
            "sns",
            region_name=region,
        )

        events_client = session.client(
            "events",
            region_name=region,
        )

        budgets_client = session.client(
            "budgets",
            region_name=region,
        )

        progress(
            0,
            "Starting AWS inventory..."
        )

        # Inventory output remains stdout.
        print(
            f"=== REGION: {region} ==="
        )

        collect_network_inventory(
            ec2_client
        )

        collect_rds_inventory(
            rds_client
        )

        collect_load_balancer_inventory(
            elbv2_client
        )

        collect_lambda_inventory(
            lambda_client
        )

        collect_secrets_inventory(
            secrets_client
        )

        collect_sagemaker_s3_inventory(
            sagemaker_client,
            s3_client,
        )

        collect_monitoring_inventory(
            cloudwatch_client,
            logs_client,
            waf_client,
        )

        collect_messaging_inventory(
            sns_client,
            events_client,
            budgets_client,
            account_id,
        )

        print()

        if INVENTORY_ERRORS == 0:
            progress(
                100,
                "AWS inventory complete."
            )
            return 0

        progress(
            100,
            "AWS inventory completed with errors."
        )
        return 1

    except ProfileNotFound:
        print(
            f"ERROR: AWS profile '{args.profile}' was not found.",
            file=sys.stderr,
        )

        print(
            "Check your configured AWS profiles.",
            file=sys.stderr,
        )

        return 1

    except KeyboardInterrupt:
        print(
            "\nScript interrupted by user. Exiting...",
            file=sys.stderr,
        )

        return 130

    except Exception as error:
        print(
            f"ERROR: Unexpected failure: {error}",
            file=sys.stderr,
        )

        return 1


if __name__ == "__main__":
    sys.exit(main())
