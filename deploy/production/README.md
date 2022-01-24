# Deploy to production automation

## Quick Start

- Set AWS_PROFILE: `export AWS_PROFILE=noq_dev`
- Authenticate: `aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin 259868150464.dkr.ecr.us-west-2.amazonaws.com`
- Deploy: `bazelisk run //deploy/production`

## Technical Debt

- Instead of using the genrule, build a bzl starlark rule
