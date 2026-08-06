# Lambda Cold Starts

This document defines how to measure and improve Lambda startup behavior for
the recommendation API. Read it during deployment measurement and performance
tuning. The authoritative phase order remains in
[`docs/deployment.md`](../deployment.md).

## Current Loading Behavior

Reference data is loaded lazily during the first recommendation request:

- `backend/api.py` calls cached loader functions from inside the endpoint.
- `backend/data_loader.py` reads JSON only when those functions are first
  called.
- later requests in the same execution environment reuse the cached objects.

Consequences:

- Lambda `Init Duration` measures runtime startup and module imports, not the
  reference-data load.
- the first handler `Duration` includes JSON loading and deserialization
- warm requests reuse loaded data and should be much faster
- SnapStart would capture empty reference-data caches in the current design

Keep lazy loading for the initial MVP deployment. Eager initialization is a
prerequisite only if SnapStart is reconsidered later.

## Measurement Plan

Instrument reference-data loading explicitly rather than inferring it from
Lambda's report line.

Record structured timing for:

- total handler duration
- name lookup load
- card database load
- commander list load
- whether each loader was a cache hit or miss

Do not log uploaded collection contents, card names, object keys, or full
reference records. Timing logs should identify the deployed code version and
reference-data manifest version.

### Initial Deployment Measurements

For each deployed memory setting, record multiple cold and warm requests:

| Measurement | Purpose |
| --- | --- |
| Lambda `Init Duration` | Runtime and import overhead |
| Explicit reference-load duration | JSON I/O and deserialization cost |
| Handler `Duration` | End-to-end Lambda execution |
| Browser/API latency | Network, API Gateway, and CloudFront overhead |
| Max memory used | Detect excessive memory pressure from loaded JSON |

Use a genuine large collection export for the main benchmark. Keep the
existing synthetic 20,000-row fixture as a repeatable comparison, not as a
substitute for real export size.

## Tuning Order

Apply changes in increasing order of complexity and remeasure after each one.

### 1. Lambda Memory

Lambda allocates CPU proportionally to memory. Start at 1,024 MB, then compare
representative settings using AWS Lambda Power Tuning. Higher memory can be
both faster and cheaper when reduced duration offsets the higher GB-second
rate.

Do not assume that 1,769 MB or any other setting is optimal without deployed
measurements.

### 2. JSON Deserialization

If explicit timing shows JSON deserialization is significant, evaluate
`orjson` against the standard library. This is a code and packaging change:

- update loaders to read bytes appropriately
- add the Linux arm64 wheel to Lambda runtime dependencies
- rerun loader validation and the complete test suite
- compare cold load duration and package size before adopting it

Do not replace `json` solely because `orjson` is generally faster.

### 3. Data Representation

If memory or deserialization remains problematic, evaluate a more compact
preprocessed representation before increasing architectural complexity.
Any new format must preserve deterministic builds, validation, and readable
failure modes.

## SnapStart Status

SnapStart is deferred and is not part of the initial deployment.

### Why It Does Not Help Reference Loading Today

SnapStart captures state after Lambda initialization. The current application
does not load reference data during initialization, so the snapshot would not
contain those objects. It could preserve imported runtime state, but it would
not remove the first-request reference-data cost that this project expects to
be the larger startup component.

Adopting SnapStart therefore requires eager module-level reference loading
before publishing a version.

### Cost

Python SnapStart charges for snapshot caching and restoration. At the
documented us-east-1 cache rate of `$0.0000015046` per GB-second, one
continuously active version costs approximately:

| Memory | Monthly cache cost per active version |
| --- | ---: |
| 512 MB | `$1.95` |
| 1,024 MB | `$3.90` |
| 1,769 MB | `$6.74` |
| 2,048 MB | `$7.80` |

Restore charges are small at MVP traffic levels, but stale published versions
can accumulate cache charges. If SnapStart is adopted, CI must delete
superseded versions that are no longer referenced by an alias.

### Constraints to Reconfirm

- Python 3.12 or later
- published versions and aliases, never `$LATEST`
- zip deployment package rather than a container image
- no provisioned concurrency
- no EFS
- no ephemeral storage above 512 MB
- confirmed compatibility between the selected Python runtime and arm64

Treat service availability, compatibility, and pricing as time-sensitive and
verify them against current AWS documentation before implementation.

### Re-Evaluation Criteria

Revisit SnapStart only when every condition is met:

1. Deployed cold-start measurements show user-visible latency worth fixing.
2. Memory tuning and any justified deserialization improvements have been
   applied and remeasured.
3. Python and arm64 compatibility is confirmed.
4. Eager reference-data initialization is implemented and tested.
5. The eager load still fits Lambda memory and initialization limits.
6. CI automatically removes superseded published versions.
7. The expected latency improvement justifies the recurring cost.

## Verification Checklist

- [ ] Reference-load timing is logged separately from `Init Duration`.
- [ ] Logs contain no user collection data.
- [ ] Cold and warm requests are measured independently.
- [ ] At least two memory configurations are compared.
- [ ] Changes are validated with both synthetic and genuine large exports.
- [ ] Package size and maximum memory usage are recorded.
- [ ] SnapStart remains disabled unless every re-evaluation criterion passes.
