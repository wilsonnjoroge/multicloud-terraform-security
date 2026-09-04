#!/bin/bash

# ============================================================
# CONFIGURATION
# ============================================================

export AWS_DEFAULT_REGION="${AWS_DEFAULT_REGION:-us-east-1}"

INVENTORY_ERRORS=0


# ============================================================
# CLEAN EXIT / CTRL+C
# ============================================================

trap '
    echo >&2
    echo "Script interrupted by user. Exiting..." >&2
    exit 130
' INT TERM


# ============================================================
# PROGRESS FUNCTION
# Sends progress to terminal (stderr)
# so it remains visible when stdout is redirected to a file.
# ============================================================

progress() {
    printf '[%3d%%] %s\n' "$1" "$2" >&2
}


# ============================================================
# AWS COMMAND WRAPPER
# Tracks failed AWS commands.
# ============================================================

run_aws() {
    "$@"

    local status=$?

    if (( status != 0 )); then
        INVENTORY_ERRORS=1
    fi

    return "$status"
}


# ============================================================
# GET AVAILABLE AWS REGIONS
# Stored in memory only.
# Nothing is written to disk.
# ============================================================

AVAILABLE_REGIONS=$(aws ec2 describe-regions \
    --region "$AWS_DEFAULT_REGION" \
    --query 'Regions[].RegionName' \
    --output text 2>/dev/null)

if [[ -z "$AVAILABLE_REGIONS" ]]; then
    echo >&2
    echo "ERROR: Unable to retrieve AWS regions." >&2
    echo "Check your AWS credentials, permissions, and default region." >&2
    exit 1
fi

#============================================================
# To see all the valid regions, uncomment the following:
# echo "=== Available AWS Regions ===" >&2
# printf '%s\n' "$AVAILABLE_REGIONS" | tr '\t' '\n' >&2
# echo >&2
#=============================================================


# ============================================================
# AWS REGION SELECTION
# ============================================================

while true; do

    read -rp $'\n=== AWS Region Selection ===\n\nOption 1: Input the Region\nOption 2: Use default ('"$AWS_DEFAULT_REGION"$')\n\nChoose an option [1-2]: ' choice

    case "$choice" in

        1)
            attempts=0

            while (( attempts < 3 )); do

                read -rp "Enter AWS Region (e.g. us-east-1): " REGION

                # Remove leading/trailing whitespace
                REGION="$(printf '%s' "$REGION" | xargs)"

                # ------------------------------------------------
                # Validate:
                # 1. AWS region format
                # 2. Region actually exists
                # ------------------------------------------------

                if [[ "$REGION" =~ ^[a-z]{2}(-gov)?-[a-z]+-[0-9]+$ ]] &&
                   printf '%s\n' "$AVAILABLE_REGIONS" |
                   tr '\t' '\n' |
                   grep -Fxq "$REGION"; then

                    export AWS_DEFAULT_REGION="$REGION"

                    echo "Region accepted: $AWS_DEFAULT_REGION" >&2
                    echo >&2

                    break 2
                fi

                ((attempts++))

                echo "Incorrect format or AWS region does not exist, try again." >&2

                if (( attempts == 3 )); then

                    echo "Maximum attempts reached." >&2
                    echo "Using default region: $AWS_DEFAULT_REGION" >&2
                    echo >&2

                    break 2
                fi

            done
            ;;

        2)
            echo "Using default region: $AWS_DEFAULT_REGION" >&2
            echo >&2

            break
            ;;

        *)
            echo "Invalid option. Please choose 1 or 2." >&2
            echo >&2
            ;;

    esac

done


# ============================================================
# AWS INVENTORY
# ============================================================

progress 0 "Starting AWS inventory..."

echo "=== REGION: $AWS_DEFAULT_REGION ==="


# ============================================================
# VPC / NETWORKING
# ============================================================

echo
echo "=== VPCs ==="
progress 10 "Collecting VPC resources..."

run_aws aws ec2 describe-vpcs \
    --region "$AWS_DEFAULT_REGION" \
    --query 'Vpcs[].VpcId' \
    --output table

echo
echo "=== EC2 Instances ==="

run_aws aws ec2 describe-instances \
    --region "$AWS_DEFAULT_REGION" \
    --query 'Reservations[].Instances[].{Id:InstanceId,State:State.Name}' \
    --output table

echo
echo "=== VPC Endpoints ==="

run_aws aws ec2 describe-vpc-endpoints \
    --region "$AWS_DEFAULT_REGION" \
    --query 'VpcEndpoints[].{Id:VpcEndpointId,State:State}' \
    --output table

echo
echo "=== Subnets ==="

run_aws aws ec2 describe-subnets \
    --region "$AWS_DEFAULT_REGION" \
    --query 'Subnets[].SubnetId' \
    --output table

echo
echo "=== Route Tables ==="

run_aws aws ec2 describe-route-tables \
    --region "$AWS_DEFAULT_REGION" \
    --query 'RouteTables[].RouteTableId' \
    --output table

echo
echo "=== Internet Gateways ==="

run_aws aws ec2 describe-internet-gateways \
    --region "$AWS_DEFAULT_REGION" \
    --query 'InternetGateways[].InternetGatewayId' \
    --output table

echo
echo "=== Network ACLs (non-default) ==="

run_aws aws ec2 describe-network-acls \
    --region "$AWS_DEFAULT_REGION" \
    --query 'NetworkAcls[?IsDefault==`false`].NetworkAclId' \
    --output table

echo
echo "=== Security Groups (non-default) ==="

run_aws aws ec2 describe-security-groups \
    --region "$AWS_DEFAULT_REGION" \
    --query 'SecurityGroups[?GroupName!=`default`].{Id:GroupId,Name:GroupName}' \
    --output table

echo
echo "=== NAT Gateways ==="

run_aws aws ec2 describe-nat-gateways \
    --region "$AWS_DEFAULT_REGION" \
    --query 'NatGateways[].{Id:NatGatewayId,State:State}' \
    --output table

echo
echo "=== Elastic IPs ==="

run_aws aws ec2 describe-addresses \
    --region "$AWS_DEFAULT_REGION" \
    --query 'Addresses[].PublicIp' \
    --output table

echo
echo "=== Network Interfaces ==="

run_aws aws ec2 describe-network-interfaces \
    --region "$AWS_DEFAULT_REGION" \
    --query 'NetworkInterfaces[].{Id:NetworkInterfaceId,Status:Status}' \
    --output table

echo
echo "=== VPC Flow Logs ==="

run_aws aws ec2 describe-flow-logs \
    --region "$AWS_DEFAULT_REGION" \
    --query 'FlowLogs[].FlowLogId' \
    --output table

echo
echo "=== EBS Volumes ==="

run_aws aws ec2 describe-volumes \
    --region "$AWS_DEFAULT_REGION" \
    --query 'Volumes[].{Id:VolumeId,State:State}' \
    --output table

echo
echo "=== Key Pairs ==="

run_aws aws ec2 describe-key-pairs \
    --region "$AWS_DEFAULT_REGION" \
    --query 'KeyPairs[].KeyName' \
    --output table

echo
echo "=== DHCP Options (non-default) ==="

run_aws aws ec2 describe-dhcp-options \
    --region "$AWS_DEFAULT_REGION" \
    --query 'DhcpOptions[].DhcpOptionsId' \
    --output table


# ============================================================
# RDS
# ============================================================

progress 30 "Collecting RDS resources..."

echo
echo "=== RDS Instances ==="

run_aws aws rds describe-db-instances \
    --region "$AWS_DEFAULT_REGION" \
    --query 'DBInstances[].DBInstanceIdentifier' \
    --output table

echo
echo "=== RDS Clusters ==="

run_aws aws rds describe-db-clusters \
    --region "$AWS_DEFAULT_REGION" \
    --query 'DBClusters[].DBClusterIdentifier' \
    --output table


# ============================================================
# LOAD BALANCERS
# ============================================================

progress 40 "Collecting Load Balancer resources..."

echo
echo "=== Load Balancers ==="

run_aws aws elbv2 describe-load-balancers \
    --region "$AWS_DEFAULT_REGION" \
    --query 'LoadBalancers[].LoadBalancerName' \
    --output table

echo
echo "=== Target Groups ==="

run_aws aws elbv2 describe-target-groups \
    --region "$AWS_DEFAULT_REGION" \
    --query 'TargetGroups[].TargetGroupName' \
    --output table


# ============================================================
# LAMBDA
# ============================================================

progress 50 "Collecting Lambda resources..."

echo
echo "=== Lambda Functions ==="

run_aws aws lambda list-functions \
    --region "$AWS_DEFAULT_REGION" \
    --query 'Functions[].FunctionName' \
    --output table


# ============================================================
# SECRETS MANAGER
# ============================================================

progress 60 "Collecting Secrets Manager resources..."

echo
echo "=== Secrets ==="

run_aws aws secretsmanager list-secrets \
    --region "$AWS_DEFAULT_REGION" \
    --query 'SecretList[].Name' \
    --output table


# ============================================================
# SAGEMAKER / S3
# ============================================================

progress 70 "Collecting SageMaker and S3 resources..."

echo
echo "=== SageMaker Domains ==="

run_aws aws sagemaker list-domains \
    --region "$AWS_DEFAULT_REGION" \
    --query 'Domains[].DomainId' \
    --output table

echo
echo "=== S3 Buckets ==="

run_aws aws s3 ls


# ============================================================
# CLOUDWATCH / WAF
# ============================================================

progress 80 "Collecting CloudWatch and WAF resources..."

echo
echo "=== CloudWatch Alarms ==="

run_aws aws cloudwatch describe-alarms \
    --region "$AWS_DEFAULT_REGION" \
    --query 'MetricAlarms[].AlarmName' \
    --output table

echo
echo "=== CloudWatch Log Groups ==="

run_aws aws logs describe-log-groups \
    --region "$AWS_DEFAULT_REGION" \
    --query 'logGroups[].logGroupName' \
    --output table

echo
echo "=== WAF IP Sets ==="

run_aws aws wafv2 list-ip-sets \
    --region "$AWS_DEFAULT_REGION" \
    --scope REGIONAL \
    --query 'IPSets[].Name' \
    --output table


# ============================================================
# SNS / EVENTBRIDGE / BUDGETS
# ============================================================

progress 90 "Collecting SNS, EventBridge, and Budgets resources..."

echo
echo "=== SNS Topics ==="

run_aws aws sns list-topics \
    --region "$AWS_DEFAULT_REGION" \
    --query 'Topics[].TopicArn' \
    --output table

echo
echo "=== EventBridge Rules ==="

run_aws aws events list-rules \
    --region "$AWS_DEFAULT_REGION" \
    --query 'Rules[].Name' \
    --output table

echo
echo "=== Budgets ==="

run_aws aws budgets describe-budgets \
    --account-id 025066283316 \
    --query 'Budgets[].BudgetName' \
    --output table


# ============================================================
# COMPLETE
# ============================================================

if (( INVENTORY_ERRORS == 0 )); then
    progress 100 "AWS inventory complete."
else
    progress 100 "AWS inventory completed with errors."
fi
