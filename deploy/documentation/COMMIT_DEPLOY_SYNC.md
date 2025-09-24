# Commit-to-Deployment Sync Guide

This guide documents how SmartBuild deployments stay in sync with the exact commit and version that were shipped.

## Build Metadata
Every deployment includes a `BUILD_INFO.json` placed on the server at `/opt/smartbuild/BUILD_INFO.json` containing:

- `version`: from `version_config.py`
- `branch`: git branch name used for the build
- `commit`: short SHA of the commit
- `built_at`: UTC timestamp

The deployment script `deploy_to_ec2.sh` now auto‑generates this file and uploads it alongside the app files.

## Daily Flow (EC2)
- Commit and push changes
  - `./git_commit/commit_and_push.sh "feat: <message>"`
- (Optional) Tag the release (recommended)
  - `ver=$(python -c 'import version_config as v;print(v.get_version())')`
  - `git tag -a "v${ver}" -m "Release ${ver} ($(git rev-parse --short HEAD))"`
  - `git push origin "v${ver}"`
- Deploy
  - `./deploy_to_ec2.sh`
- Verify
  - `./deploy/scripts/verify-deployment.sh`

## Automated Deployment After Commit

Goal: Deploy to EC2 automatically after pushing to a specific branch or tag.

Option A — GitHub Actions runs `deploy_to_ec2.sh`
- Create repository secrets:
  - `SMARTBUILD_PEM` — contents of the EC2 private key (.pem)
  - `EC2_HOST` — e.g., `ubuntu@98.83.207.85`
- Add the workflow `.github/workflows/deploy_ec2.yml` (sample below). It:
  - Checks out code
  - Writes `SMARTBUILD_PEM` to a temp file and chmod 600
  - Runs `deploy_to_ec2.sh` with `KEY_PATH` override
- Trigger: on push to `smartbuild_monitor_automation` (or your main/release branches), and manual dispatch.

Option B — Remote pull via SSH
- Use a GitHub Action (appleboy/ssh-action) to SSH into EC2 and run `git pull` + a small remote deploy script. This keeps the PEM only in Actions (not on the runner disk beyond the job).

Notes
- Keep `sessions/active/` data persisted on EC2; the script only rsyncs app files.
- The verify step checks all three CloudFront endpoints and prints HTTP codes.


## What To Check After Deploy
- SSH to the instance and check `/opt/smartbuild/BUILD_INFO.json`.
- Ensure the three CloudFront endpoints respond (HTTP 200):
  - Main App
  - Job Monitor
  - Control Center
- Confirm services are active: `smartbuild`, `smartmonitor`, `job-queue-control`, `job-queue-monitor`.

## ECS Deployments (Optional)
For ECS, use image tags (git SHA or version) and add the same metadata as image labels and/or a file in the container at the same path. Ensure `deploy/scripts/deploy.sh` uses a specific `IMAGE_TAG` corresponding to the commit.

## Rollback
- Roll back by redeploying a prior tag or commit, then verify `BUILD_INFO.json` matches the intended rollback version and SHA.
