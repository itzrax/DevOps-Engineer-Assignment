# Required tags every resource must have
REQUIRED_TAGS = ["Project", "Environment", "Owner", "ManagedBy"]

# Number of days a stopped instance is considered orphaned
DEFAULT_STOPPED_DAYS = 14

# LocalStack endpoint
LOCALSTACK_ENDPOINT = "http://localhost:4566"

# AWS region
DEFAULT_REGION = "us-east-1"

# Pricing estimates (USD per month) for cost reporting
# Sources: https://aws.amazon.com/ebs/pricing/
#          https://aws.amazon.com/ec2/pricing/on-demand/
PRICING = {
    "ebs_gp3_per_gb": 0.08,    # EBS gp3: $0.08/GB-month (us-east-1)
    "elastic_ip": 3.60,         # Unattached EIP: $0.005/hour = ~$3.60/month
    "ec2_t3_micro": 8.35,       # t3.micro on-demand: $0.0116/hour = ~$8.35/month
}

# Fake AWS account ID used by LocalStack
ACCOUNT_ID = "000000000000"