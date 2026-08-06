# Deployment Security and Cost Controls

This document contains the detailed security, abuse-prevention, and cost
controls for the deployment plan. Read it when implementing conditional S3
uploads, API throttling, alarms, or deployment budgets. The authoritative
phase order remains in [`docs/deployment.md`](../deployment.md).

## Threat Model

The main API Lambda is invoked synchronously through API Gateway. It has no
recursive event source that can reinvoke it by writing to S3, SNS, or SQS.
The separate remediation Lambda described below is alarm-driven, but it does
not invoke the API Lambda.

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

Set these controls on the first manual deployment:

| Control | Setting | Effect |
| --- | --- | --- |
| Lambda reserved concurrency | 5 | Caps simultaneous API executions; excess requests are rejected |
| Lambda timeout | 10 seconds | Bounds duration cost for a pathological invocation |
| API Gateway route throttle | 10 requests/second, burst 20 | Bounds arrival rate, though rejected requests can still incur gateway charges |
| Account concurrency quota | Deliberately lowered | Limits blast radius across the learning account |

Reserved concurrency can also serve as the emergency kill switch when set to
zero.

## Layer 2: Detection

| Alarm | Metric | Purpose |
| --- | --- | --- |
| Invocation spike | Lambda `Invocations`, five-minute sum | Detect accepted volume before concurrency saturates |
| Lambda throttling | Lambda `Throttles` | Detect traffic rejected after concurrency saturates |
| Errors | Lambda `Errors` | Surface handler failures |
| Latency | Lambda p95 `Duration` | Detect performance regressions |
| Gateway volume | API Gateway `Count` | Measure attempted traffic even when Lambda rejects it |
| Gateway client failures | API Gateway 4xx | Detect route throttling, malformed traffic, and abuse |
| Gateway failures | API Gateway 5xx | Detect integration failures |

Send alarm notifications through SNS to email or SMS. Metrics generally
publish at roughly one-minute granularity, so detection should occur within
minutes rather than on the next invoice.

## Layer 3: Automated Kill Switch

Do not rely on Lambda `Invocations` alone because concurrency-throttled
requests are not counted as successful invocations. Route a high-confidence
alarm path to a separate remediation Lambda when either of these conditions
persists across consecutive evaluation periods:

- accepted invocation volume is far above the expected peak
- Lambda throttles or API Gateway request volume indicate a sustained loop

The remediation function sets the API function's reserved concurrency to
zero. Keep enough unreserved account concurrency for the remediation function
itself to run during an incident.

This deliberately trades availability for bounded cost. Restore service only
after identifying the traffic source.

## Layer 4: Financial Backstop

- Create an AWS Budget at `$20/month` with alerts at 50%, 80%, and 100%.
- Attach a budget action that applies the selected deny policy at the final
  threshold.
- Enable AWS Cost Anomaly Detection.

Budgets are not a real-time kill switch. Billing data can lag by many hours,
so Layers 1 through 3 provide the actual operational protection.

## Layer 5: Housekeeping

- Set CloudWatch log retention to 14 days instead of the default indefinite
  retention.
- If SnapStart is ever adopted, delete superseded published Lambda versions
  in CI because each active version can retain a billed snapshot.
- Retain only the intended reference-data archives and deployment artifacts in
  S3; add lifecycle policies when accumulation is no longer useful.

## Manual Kill Switch

```powershell
aws lambda put-function-concurrency `
  --function-name mtg-recommender-api `
  --reserved-concurrent-executions 0
```

Restore service by setting reserved concurrency back to 5.

## Worst-Case Synchronous-Upload Exposure

Assumptions:

- five concurrent executions
- 1,024 MB Lambda memory
- ten-second timeout
- arm64 duration rate of `$0.0000133334` per GB-second
- ten API requests per second
- a file near the 4 MiB synchronous limit

| Component | Calculation | Approximate rate |
| --- | --- | --- |
| Lambda duration | `5 x 1 GB x 3,600 seconds` = 18,000 GB-seconds/hour | `$0.24/hour` |
| API Gateway | 36,000 requests/hour at 8–9 billable 512 KiB units each | `$0.29–0.32/hour` |
| Lambda requests | At most 1,800 admitted invocations/hour | Less than `$0.001/hour` |
| **Total** | Sustained and unnoticed | **`$0.53–0.56/hour`, or `$12.70–13.45/day`** |

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
| AWS Budgets | One action-enabled budget | `$0` |

Expected MVP steady state is approximately `$0–1/month`, excluding optional
SnapStart and a custom domain.

## Account Plan

For an AWS account created under the post-July-2025 account model, use the
Paid plan rather than the six-month Free plan. Both begin with promotional
credits, but the Paid plan is suitable for a project intended to remain
available after the introductory period. Confirm the actual account creation
date and selected plan before provisioning resources.

## Verification Checklist

- [ ] Main Lambda concurrency and timeout are configured.
- [ ] API Gateway route throttling is configured.
- [ ] All seven alarms publish to the intended SNS topic.
- [ ] High-confidence traffic alarms can invoke the remediation Lambda.
- [ ] The manual concurrency-zero command has been tested.
- [ ] Budget and anomaly notifications reach the owner.
- [ ] Log retention is 14 days.
- [ ] Conditional scratch uploads enforce key, size, CORS, deletion, and IAM
      restrictions.
