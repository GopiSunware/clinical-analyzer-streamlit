#!/bin/bash

# Create CloudFront Distribution for SmartDeploy
set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN} Creating CloudFront for SmartDeploy   ${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Configuration
STACK_NAME="SmartDeploy-CloudFront-Stack"
TEMPLATE_FILE="deploy/infrastructure/smartdeploy-cloudfront.yaml"
REGION="us-east-1"
EC2_IP="98.83.207.85"
APP_PORT="8506"

echo -e "${YELLOW}Deploying CloudFront distribution...${NC}"

# Deploy the CloudFormation stack
aws cloudformation deploy \
    --template-file $TEMPLATE_FILE \
    --stack-name $STACK_NAME \
    --parameter-overrides \
        EC2PublicIP=$EC2_IP \
        AppPort=$APP_PORT \
    --region $REGION \
    --no-fail-on-empty-changeset

echo -e "${YELLOW}Waiting for stack to complete...${NC}"

# Wait for stack to complete
aws cloudformation wait stack-create-complete \
    --stack-name $STACK_NAME \
    --region $REGION 2>/dev/null || \
aws cloudformation wait stack-update-complete \
    --stack-name $STACK_NAME \
    --region $REGION 2>/dev/null || true

# Get the CloudFront URL
CLOUDFRONT_URL=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --query 'Stacks[0].Outputs[?OutputKey==`CloudFrontURL`].OutputValue' \
    --output text \
    --region $REGION)

CLOUDFRONT_DOMAIN=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --query 'Stacks[0].Outputs[?OutputKey==`CloudFrontDomainName`].OutputValue' \
    --output text \
    --region $REGION)

DISTRIBUTION_ID=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --query 'Stacks[0].Outputs[?OutputKey==`CloudFrontDistributionId`].OutputValue' \
    --output text \
    --region $REGION)

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}    CloudFront Created Successfully!    ${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "CloudFront URL: ${GREEN}${CLOUDFRONT_URL}${NC}"
echo -e "Domain Name: ${GREEN}${CLOUDFRONT_DOMAIN}${NC}"
echo -e "Distribution ID: ${GREEN}${DISTRIBUTION_ID}${NC}"
echo ""
echo -e "${YELLOW}Note: It may take 15-20 minutes for the distribution to fully propagate.${NC}"
echo ""

# Save the CloudFront details to a file
echo "{
  \"cloudfront_url\": \"${CLOUDFRONT_URL}\",
  \"domain_name\": \"${CLOUDFRONT_DOMAIN}\",
  \"distribution_id\": \"${DISTRIBUTION_ID}\",
  \"ec2_ip\": \"${EC2_IP}\",
  \"app_port\": \"${APP_PORT}\",
  \"created_at\": \"$(date -Iseconds)\"
}" > deploy/smartdeploy_cloudfront.json

echo -e "${GREEN}CloudFront details saved to deploy/smartdeploy_cloudfront.json${NC}"