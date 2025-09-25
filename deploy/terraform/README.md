# Terraform Infrastructure

This directory contains Terraform configurations for provisioning Purplex infrastructure.

## Structure

- `main.tf` - Main configuration
- `variables.tf` - Input variables
- `outputs.tf` - Output values
- `providers.tf` - Provider configuration
- `modules/` - Reusable modules

## Usage

```bash
# Initialize Terraform
terraform init

# Plan changes
terraform plan -var-file="production.tfvars"

# Apply changes
terraform apply -var-file="production.tfvars"

# Destroy infrastructure
terraform destroy -var-file="production.tfvars"
```

## Resources Managed

- VPC and networking
- RDS PostgreSQL database
- ElastiCache Redis cluster
- ECS/EKS cluster
- Load balancers
- S3 buckets for static files
- CloudFront distribution
- Route53 DNS records
- IAM roles and policies

## Notes

- State files should be stored in S3 with state locking via DynamoDB
- Use workspaces for different environments (dev, staging, prod)
- Keep sensitive variables in `.tfvars` files (gitignored)