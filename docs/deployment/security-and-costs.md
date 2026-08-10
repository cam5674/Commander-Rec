# Deployment Security and Cost Controls

This document contains the detailed security, abuse-prevention, and cost
controls for the deployment plan. Read it when implementing conditional S3
uploads, API throttling, alarms, or deployment budgets. The authoritative
phase order remains in [`docs/deployment.md`](../deployment.md).

## Threat Model

The main API Lambda is invoked synchronously through API Gateway. It has no
recursive event source that can reinvoke it by writing to S3, SNS, or SQS.

An infinite loop inside the handler is bounded by the Lambda timeout. The more
likely exposure is repeated public traffic:

- a frontend request loop caused by application code
- a malicious or accidental client repeatedly submitting uploads
- abuse of the conditional presign endpoint

The endpoint is intentionally public and unauthenticated for the MVP, so cost
controls must not depend on identifying a user.

## Conditional Scratch-Upload Security

These controls apply only if Phase 0 selects the presigned-S3 upload branch.

### Upload Flow

1. The frontend requests a presigned POST form from the API.
2. The backend creates a cryptographically random key under `uploads/` and
   returns a short-lived form with a content-length policy.
3. The frontend uploads the CSV directly to the private scratch bucket.
4. The frontend submits the server-issued key to `POST /recommendations`.
5. The backend validates, reads, processes, and deletes the object.

### Required Controls

- Keep the scratch bucket private with S3 Block Public Access enabled.
- Permit browser POST requests only from the deployed CloudFront origin.
- Generate keys server-side using the exact
  `uploads/<generated-id>.csv` shape; reject arbitrary buckets, prefixes, or
  client-selected keys.
- Expire presigned forms within minutes.
- Include `content-length-range` in the presigned POST policy.
- Run `HeadObject` before download and reject objects whose size or content
  type violates `GET /config`.
- Rate-limit the public presign route independently from recommendations.
- Delete the object in a `finally` block after every processing attempt,
  including parsing and scoring failures.
- Apply a one-day lifecycle rule only as a fallback for uploads abandoned
  before the recommendation request.
- Scope Lambda IAM to `s3:PutObject`, `s3:GetObject`, and `s3:DeleteObject`
  on the scratch prefix only.

Immediate deletion preserves the MVP requirement that uploaded collections
are discarded after the request. Lifecycle expiration alone does not satisfy
that requirement.

## Layer 1: Hard Caps

Keep these controls on the CDK deployment:

| Control | Setting | Effect |
| --- | --- | --- |
| Account concurrency quota | 10 | Caps concurrent Lambda executions across the learning account and Region |
| API positive reserved concurrency | Not configured | Avoids raising the account quota solely to satisfy Lambda's unreserved-capacity requirement |
| Lambda timeout | 10 seconds | Bounds duration cost for a pathological invocation |
| API Gateway route throttle | 10 requests/second, burst 20 | Bounds arrival rate, though rejected requests can still incur gateway charges |

The API uses the account's unreserved pool and can consume at most the available
10 executions. Reserved concurrency zero remains available as the emergency
kill switch even though no positive reservation is configured. Do not request a
quota increase solely to add an automated remediation Lambda for the showcase
deployment.

## Layer 2: Detection

| Alarm | Metric | Initial threshold | Purpose |
| --- | --- | --- | --- |
| Invocation spike | Lambda `Invocations`, five-minute sum | More than 300 for two periods | Detect accepted volume before concurrency saturates |
| Lambda throttling | Lambda `Throttles`, five-minute sum | At least 5 | Detect traffic rejected after concurrency saturates |
| Errors | Lambda `Errors`, five-minute sum | At least 5 | Surface handler failures |
| Latency | Lambda p95 `Duration` | More than 8 seconds | Detect performance regressions |
| Gateway volume | API Gateway `Count`, five-minute sum | More than 600 for two periods | Measure attempted traffic even when Lambda rejects it |
| Gateway client failures | API Gateway 4xx, five-minute sum | More than 50 | Detect route throttling, malformed traffic, and abuse |
| Gateway failures | API Gateway 5xx, five-minute sum | At least 5 | Detect integration failures |

Send all alarm notifications through one SNS topic with a confirmed email
subscription. Treat missing data as non-breaching because normal showcase
traffic is sparse, and ignore low-sample percentile evaluation for the p95
duration alarm. Use stage-level API Gateway metrics rather than enabling paid
detailed route metrics. Metrics generally publish at roughly one-minute
granularity, so detection should occur within minutes rather than on the next
invoice. Tune the initial thresholds after observing real traffic.

## Layer 3: Manual Incident Response

Do not rely on Lambda `Invocations` alone because concurrency-throttled
requests are not counted as successful invocations. Review Lambda alarms and
API Gateway `Count`, 4xx, and 5xx together when evaluating a suspected loop.
When sustained abnormal traffic is confirmed, manually set the API function's
reserved concurrency to zero. Restore service only after identifying the
traffic source.

The automated remediation Lambda is deferred. With the current account quota
of 10, a remediation Lambda would share the same saturated pool. Guaranteeing
its execution would require increasing the quota enough to leave 100 units
unreserved, which is unnecessary for expected showcase traffic and increases
operational complexity.

## Layer 4: Request and Browser Hardening

- Enable structured API Gateway access logs with request ID, source IP, route,
  status, response length, and latency fields.
- Retain access logs for 14 days and never log request bodies, CSV contents,
  uploaded filenames, or response payloads.
- Attach CloudFront's managed security-headers response policy to the frontend
  behavior.
- Keep FastAPI `/docs` and `/openapi.json` available locally but disable them in
  the deployed Lambda through environment-driven configuration.
- Keep WAF and Shield Advanced deferred unless observed traffic justifies their
  additional configuration or cost; Shield Standard remains automatic.

## Layer 5: Financial Backstop

- Verify the existing `$1` and `$10` monthly budgets and their actual and
  forecast notifications.
- Use the `$1` budget as an early warning and the `$10` budget as the final
  financial backstop; configure any final action deliberately and test its
  notification path.
- Enable AWS Cost Anomaly Detection.

Budgets are not a real-time kill switch. Billing data can lag by many hours,
so Layers 1 through 3 provide the actual operational protection.

## Layer 6: Housekeeping

- Set CloudWatch log retention to 14 days instead of the default indefinite
  retention.
- If SnapStart is ever adopted, delete superseded published Lambda versions
  in CI because each active version can retain a billed snapshot.
- Retain only the intended reference-data archives and deployment artifacts in
  S3; add lifecycle policies when accumulation is no longer useful.

## Manual Kill Switch

```powershell
aws lambda put-function-concurrency `
  --function-name commander-rec-cdk-api `
  --reserved-concurrent-executions 0 `
  --profile commander-rec `
  --region us-west-1
```

After identifying the traffic source, restore normal use of the account's
unreserved pool:

```powershell
aws lambda delete-function-concurrency `
  --function-name commander-rec-cdk-api `
  --profile commander-rec `
  --region us-west-1
```

Test both commands during a planned window, verify the API is unavailable while
disabled, and confirm `/api/config` and a CSV upload succeed after restoration.

## Worst-Case Synchronous-Upload Exposure

Assumptions:

- ten concurrent executions
- 1,024 MB Lambda memory
- ten-second timeout
- arm64 duration rate of `$0.0000133334` per GB-second
- ten API requests per second
- a file near the 4 MiB synchronous limit

| Component | Calculation | Approximate rate |
| --- | --- | --- |
| Lambda duration | `10 x 1 GB x 3,600 seconds` = 36,000 GB-seconds/hour | `$0.48/hour` |
| API Gateway | 36,000 requests/hour at 8–9 billable 512 KiB units each | `$0.29–0.32/hour` |
| Lambda requests | At most 3,600 admitted ten-second invocations/hour | Less than `$0.001/hour` |
| **Total** | Sustained and unnoticed | **`$0.77–0.80/hour`, or `$18.48–19.20/day`** |

The remaining integration attempts are rejected by Lambda but can still incur
API Gateway request charges. They do not incur Lambda request or duration
charges.

This calculation applies only to the synchronous branch. With presigned S3
uploads, only small presign and object-key requests pass through API Gateway;
that branch needs a separate exposure estimate that includes scratch-bucket
abuse.

## Expected Steady-State Cost

| Service | Expected MVP usage | Expected cost |
| --- | --- | --- |
| Lambda | Within 1M requests and 400,000 GB-seconds/month | `$0` |
| API Gateway HTTP API | A few thousand development requests | Approximately `$0` |
| CloudFront | Within free data, request, and function allowances | `$0` |
| S3 | Reference archive, frontend build, and deployment artifacts | Approximately `$0` |
| CloudWatch Logs | Within 5 GB monthly ingestion | `$0` |
| CloudWatch alarms | Seven alarms, within the allowance of ten | `$0` |
| AWS Budgets | Existing `$1` and `$10` budgets | Approximately `$0` |

Expected MVP steady state is approximately `$0–1/month`, excluding optional
SnapStart and a custom domain.

## Account Plan

For an AWS account created under the post-July-2025 account model, use the
Paid plan rather than the six-month Free plan. Both begin with promotional
credits, but the Paid plan is suitable for a project intended to remain
available after the introductory period. Confirm the actual account creation
date and selected plan before provisioning resources.

## Verification Checklist

- [ ] The account concurrency quota remains 10 and the Lambda timeout is configured.
- [ ] API Gateway route throttling is configured.
- [ ] All seven alarms publish to the intended SNS topic.
- [ ] The SNS email subscription is confirmed and a test notification arrives.
- [ ] API Gateway access logs omit request and response bodies and expire after 14 days.
- [ ] CloudFront security headers are present and production API docs are disabled.
- [ ] The manual concurrency-zero command has been tested.
- [ ] The API has been restored by deleting its concurrency configuration.
- [ ] Budget and anomaly notifications reach the owner.
- [ ] Log retention is 14 days.
- [ ] If Phase 0b is adopted, conditional scratch uploads enforce key, size,
      CORS, deletion, and IAM restrictions.
