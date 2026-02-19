#!/bin/bash
set -e

echo "================================================"
echo "AWS Secrets Manager IAM Policy Setup"
echo "================================================"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo -e "${RED}ERROR: AWS CLI is not installed${NC}"
    echo "Install with: pip install awscli"
    exit 1
fi

# Check AWS credentials
if ! aws sts get-caller-identity &> /dev/null; then
    echo -e "${RED}ERROR: AWS credentials not configured${NC}"
    echo "Run: aws configure"
    exit 1
fi

# Get AWS account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo -e "${GREEN}AWS Account ID: ${ACCOUNT_ID}${NC}"
echo ""

# Prompt for IAM role or instance profile
echo "This script will attach the Secrets Manager policy to an IAM role."
echo ""
read -p "Enter the IAM role name (e.g., purplex-ec2-role): " ROLE_NAME

if [ -z "$ROLE_NAME" ]; then
    echo -e "${RED}ERROR: Role name is required${NC}"
    exit 1
fi

# Check if role exists
if ! aws iam get-role --role-name "$ROLE_NAME" &> /dev/null; then
    echo -e "${YELLOW}Role '$ROLE_NAME' does not exist. Create it? (y/n)${NC}"
    read -p "> " CREATE_ROLE
    
    if [ "$CREATE_ROLE" = "y" ]; then
        echo "Creating IAM role..."
        
        # Create trust policy for EC2
        cat > /tmp/trust-policy.json << TRUST_EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "ec2.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
TRUST_EOF
        
        aws iam create-role \
            --role-name "$ROLE_NAME" \
            --assume-role-policy-document file:///tmp/trust-policy.json \
            --description "Purplex EC2 role with Secrets Manager access"
        
        # Create instance profile
        aws iam create-instance-profile --instance-profile-name "$ROLE_NAME"
        
        # Add role to instance profile
        aws iam add-role-to-instance-profile \
            --instance-profile-name "$ROLE_NAME" \
            --role-name "$ROLE_NAME"
        
        rm /tmp/trust-policy.json
        echo -e "${GREEN}Role created successfully${NC}"
    else
        echo "Exiting..."
        exit 1
    fi
fi

# Create or update the policy
POLICY_NAME="PurplexSecretsManagerAccess"
POLICY_FILE="scripts/aws-secrets-iam-policy.json"

echo ""
echo "Creating IAM policy: $POLICY_NAME"

# Check if policy already exists
EXISTING_POLICY=$(aws iam list-policies --query "Policies[?PolicyName=='$POLICY_NAME'].Arn" --output text)

if [ -n "$EXISTING_POLICY" ]; then
    echo -e "${YELLOW}Policy already exists: $EXISTING_POLICY${NC}"
    POLICY_ARN="$EXISTING_POLICY"
else
    # Create new policy
    POLICY_ARN=$(aws iam create-policy \
        --policy-name "$POLICY_NAME" \
        --policy-document file://"$POLICY_FILE" \
        --description "Allows Purplex EC2 instances to read secrets from AWS Secrets Manager" \
        --query 'Policy.Arn' \
        --output text)
    
    echo -e "${GREEN}Policy created: $POLICY_ARN${NC}"
fi

# Attach policy to role
echo ""
echo "Attaching policy to role..."

aws iam attach-role-policy \
    --role-name "$ROLE_NAME" \
    --policy-arn "$POLICY_ARN"

echo -e "${GREEN}✓ Policy attached successfully${NC}"

echo ""
echo "================================================"
echo "Next Steps:"
echo "================================================"
echo ""
echo "1. Attach this IAM role to your EC2 instance:"
echo "   - Go to EC2 Console"
echo "   - Select your instance"
echo "   - Actions → Security → Modify IAM role"
echo "   - Select: $ROLE_NAME"
echo ""
echo "2. Or use AWS CLI:"
echo "   aws ec2 associate-iam-instance-profile \\"
echo "       --instance-id i-xxxxx \\"
echo "       --iam-instance-profile Name=$ROLE_NAME"
echo ""
echo "3. Verify on EC2 instance:"
echo "   aws secretsmanager get-secret-value \\"
echo "       --secret-id purplex/production/credentials"
echo ""
