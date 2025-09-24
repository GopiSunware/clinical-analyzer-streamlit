#!/bin/bash

# SmartBuild SPA AWS Deployment Script
# This script deploys the application to AWS using ECS Fargate

set -e

echo "========================================="
echo "SmartBuild SPA - AWS Deployment Script"
echo "========================================="

# Configuration
AWS_REGION=${AWS_REGION:-"us-east-1"}
STACK_NAME="smartbuild-spa-stack"
ECR_REPO_NAME="smartbuild-spa"
IMAGE_TAG="latest"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check AWS CLI is configured
echo -e "${YELLOW}Checking AWS configuration...${NC}"
aws sts get-caller-identity > /dev/null 2>&1 || {
    echo -e "${RED}Error: AWS CLI not configured. Please run 'aws configure'${NC}"
    exit 1
}

AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo -e "${GREEN}✓ AWS Account: $AWS_ACCOUNT_ID${NC}"
echo -e "${GREEN}✓ Region: $AWS_REGION${NC}"

# Step 1: Create ECR Repository
echo -e "\n${YELLOW}Step 1: Creating ECR Repository...${NC}"
aws ecr describe-repositories --repository-names $ECR_REPO_NAME --region $AWS_REGION 2>/dev/null || \
aws ecr create-repository --repository-name $ECR_REPO_NAME --region $AWS_REGION

ECR_URI="$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPO_NAME"
echo -e "${GREEN}✓ ECR Repository: $ECR_URI${NC}"

# Step 2: Build and Push Docker Image
echo -e "\n${YELLOW}Step 2: Building Docker image...${NC}"
cd ..
docker build -t $ECR_REPO_NAME:$IMAGE_TAG .

echo -e "\n${YELLOW}Step 3: Pushing to ECR...${NC}"
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_URI
docker tag $ECR_REPO_NAME:$IMAGE_TAG $ECR_URI:$IMAGE_TAG
docker push $ECR_URI:$IMAGE_TAG
echo -e "${GREEN}✓ Image pushed to ECR${NC}"

# Step 4: Deploy CloudFormation Stack
echo -e "\n${YELLOW}Step 4: Deploying CloudFormation stack...${NC}"
cd deploy

# Check if certificate ARN is provided
read -p "Do you have an ACM certificate ARN for HTTPS? (y/n): " has_cert
if [[ $has_cert == "y" ]]; then
    read -p "Enter ACM Certificate ARN: " CERT_ARN
    CERT_PARAM="CertificateArn=$CERT_ARN"
else
    CERT_PARAM=""
fi

# Deploy the stack
aws cloudformation deploy \
    --template-file cloudformation-template.yaml \
    --stack-name $STACK_NAME \
    --parameter-overrides \
        ImageUri=$ECR_URI:$IMAGE_TAG \
        $CERT_PARAM \
    --capabilities CAPABILITY_IAM \
    --region $AWS_REGION

echo -e "${GREEN}✓ CloudFormation stack deployed${NC}"

# Step 5: Get the application URL
echo -e "\n${YELLOW}Step 5: Getting application URL...${NC}"
APP_URL=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --query 'Stacks[0].Outputs[?OutputKey==`ApplicationURL`].OutputValue' \
    --output text \
    --region $AWS_REGION)

echo -e "\n========================================="
echo -e "${GREEN}Deployment Complete!${NC}"
echo -e "========================================="
echo -e "Application URL: ${GREEN}$APP_URL${NC}"
echo -e "\nNote: It may take 2-3 minutes for the application to be fully available."
echo -e "You can check the ECS service status in the AWS Console."
echo -e "\nTo delete the stack later, run:"
echo -e "  aws cloudformation delete-stack --stack-name $STACK_NAME --region $AWS_REGION"