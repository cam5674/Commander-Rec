# Commander Rec Infrastructure

This AWS CDK app defines the Phase 5 parallel deployment stack:

- Python 3.12 ARM64 Lambda and its IAM role
- HTTP API routes and stage throttling
- private S3 frontend bucket with CloudFront OAC
- CloudFront frontend and `/api/*` behaviors
- frontend asset deployment and cache headers
- API access logs and explicit 14-day CloudWatch log retention
- CloudWatch alarms with an SNS email subscription
- CloudFront managed security response headers

The stack is named `commander-rec-cdk`, so it does not modify the existing
manual SAM/CloudFormation deployment.

## Prepare

Build the frontend before synthesizing or deploying:

```powershell
cd frontend
npm ci
npm run build
cd ..\infra
```

Create and activate the infrastructure environment if needed:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt -r requirements-dev.txt
```

Docker Desktop must be running because CDK builds the Lambda's Linux ARM64
zip asset from `lambda.Dockerfile`.

## Validate

```powershell
python -m pytest
cdk synth --profile commander-rec
cdk diff --profile commander-rec
```

## Deploy

Review the diff before creating the parallel stack:

```powershell
$AlertEmail = "you@example.com"
cdk deploy --profile commander-rec --parameters AlertEmail=$AlertEmail
```

After deployment, confirm the AWS SNS subscription email before expecting
alarm notifications.

Do not remove the existing manual stack until the CDK deployment passes the
Phase 5 browser, API, caching, and rollback checks in `docs/deployment.md`.
