# Clinical Analyzer Cloud Deployment

This guide documents the minimal-cost AWS pipeline that now publishes the Streamlit Clinical Analyzer through CloudFront + EC2 with assets hosted in S3.

## 1. Package & Upload Artifacts

1. From the repo root, build the ZIP bundle (excludes secrets):
   ```bash
   mkdir -p dist
   zip -r dist/clinical-analyser.zip . \
     -x 'dist/*' '.git/*' '*.pyc' '__pycache__/*' 'env' 'env/*' 'key.json' \
        'deploy/keys/*' 'git_commit/PRIVATE_GITHUB_PAT.txt'
   ```
2. Upload to the artifacts bucket created for this project:
   ```bash
   aws s3 cp dist/clinical-analyser.zip \
     s3://clinical-analyser-artifacts-057669459602/artifacts/clinical-analyser.zip
   ```

## 2. Launch / Update the Stack

Template: `deploy/infrastructure/clinical-analyzer-minimal.yaml` (uses Ubuntu 22.04 + Nginx proxy).

```bash
aws cloudformation create-stack \
  --stack-name clinical-analyzer-minimal \
  --template-body file://deploy/infrastructure/clinical-analyzer-minimal.yaml \
  --parameters \
    ParameterKey=KeyPairName,ParameterValue=smartbuild-20250824180036 \
    ParameterKey=VpcId,ParameterValue=vpc-0bc30631a28503c95 \
    ParameterKey=PublicSubnetId,ParameterValue=subnet-0bee8301325571ebf \
    ParameterKey=ArtifactBucket,ParameterValue=clinical-analyser-artifacts-057669459602 \
    ParameterKey=ArtifactObjectKey,ParameterValue=artifacts/clinical-analyser.zip \
    ParameterKey=InstanceType,ParameterValue=t3a.micro \
  --capabilities CAPABILITY_NAMED_IAM
```

Re-deploy after code changes by re-uploading the ZIP and running `aws cloudformation update-stack` with the same parameters.

## 3. What the Stack Creates

- **EC2**: t3a.micro running Streamlit behind systemd (`clinical-analyzer.service`).
- **Security Group**: SSH (22) + HTTP (80) only.
- **IAM**: Instance profile scoped to the S3 artifact object.
- **CloudFront**: Public CDN edge serving the EC2 origin via HTTPS.

## 4. Verification

- Stack outputs: `aws cloudformation describe-stacks --stack-name clinical-analyzer-minimal --query 'Stacks[0].Outputs'` for current IP / URLs.
- Reach the app: `https://d1kmcm08kwn7a6.cloudfront.net`
- Direct instance check: `curl http://18.206.218.43` (update if the IP changes).
- SSH if needed: `ssh -i smartbuild-20250824180036.pem ubuntu@18.206.218.43`
- Service health: `sudo systemctl status clinical-analyzer` on the instance.

## 5. Cost & Cleanup

- Instance: `t3a.micro` (~$8/month in us-east-1 when running 24/7).
- CloudFront + S3: pay-per-use; current bucket versioning disabled.
- Tear-down when finished:
  ```bash
  aws cloudformation delete-stack --stack-name clinical-analyzer-minimal
  aws s3 rm s3://clinical-analyser-artifacts-057669459602/artifacts/clinical-analyser.zip
  aws s3 rb s3://clinical-analyser-artifacts-057669459602
  ```
