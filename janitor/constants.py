# Required tags every resource must have
REQUIRED_TAGS = ["Project", "Environment", "Owner", "ManagedBy"]

# Number of days a stopped instance is considered orphaned
DEFAULT_STOPPED_DAYS = 14

# LocalStack endpoint
LOCALSTACK_ENDPOINT = "http://localhost:4566"

# AWS region
DEFAULT_REGION = "us-east-1"

# Pricing estimates (USD per month) for cost reporting
PRICING = {
    "ebs_gp3_per_gb": 0.08,
    "elastic_ip": 3.60,
    "ec2_t3_micro": 8.35,
}

ACCOUNT_ID = "000000000000"