# Deployment Reference Data

This document defines how processed Scryfall reference data is measured,
packaged, refreshed, and supplied to CI. Read it when implementing Lambda
packaging or the deployment pipeline. The authoritative phase order remains
in [`docs/deployment.md`](../deployment.md).

## Runtime Data Set

The Lambda package requires the generated files from `data/processed`:

| File | Current size | Runtime purpose |
| --- | ---: | --- |
| `cards_by_id.json` | Approximately 27,000 KB | Card records keyed by Oracle ID |
| `name_to_id.json` | Approximately 2,340 KB | Normalized name lookup |
| `theme_to_card_ids.json` | Approximately 972 KB | Reverse theme index |
| `commanders.json` | Approximately 128 KB | Commander-eligible Oracle IDs |
| **Total** | **31,469,912 bytes / 30.01 MiB** | |

The raw `data/raw/oracle_cards.jsonl.gz` file is a processing input and must
not be included in the Lambda package.

## Packaging Decision

Use a Lambda zip deployment artifact and bake the processed JSON into it.
This avoids runtime S3 reads, keeps reference data versioned with application
code, and preserves the option to evaluate SnapStart later.

The 30.01 MiB reference-data portion fits comfortably under Lambda's 250 MB
unzipped package limit. Complete package viability is not yet confirmed:

- measure the final compressed artifact against the 50 MB direct-upload limit
- measure the final uncompressed artifact against the 250 MB hard limit
- include application code and every Lambda runtime dependency in both
  measurements

CDK can stage a zip larger than 50 MB through its bootstrap S3 bucket, but it
cannot bypass the 250 MB uncompressed limit.

## Lambda Runtime Dependencies

Do not package the complete development `requirements.txt`. Create a focused
Lambda dependency definition such as `requirements-lambda.txt`.

Include:

- FastAPI and its runtime dependencies
- `python-multipart` on the synchronous-upload branch
- Mangum

Exclude dependencies used only for local serving, tests, downloads, or data
generation, including `uvicorn[standard]`, `httpx`, and `requests` unless a
later runtime change makes one necessary.

The package is not pure Python because `pydantic-core` is compiled. Build
Linux arm64 wheels explicitly:

```powershell
pip install `
  --platform manylinux2014_aarch64 `
  --target ./package `
  --implementation cp `
  --python-version 3.12 `
  --only-binary=:all: `
  -r requirements-lambda.txt
```

Installing dependencies directly from the Windows host environment can
produce binaries that fail on Lambda.

## CI Acquisition Decision

`data/` is gitignored, so CI obtains processed reference data from a private,
versioned S3 staging bucket. Do not regenerate from the latest Scryfall bulk
data during each application build; doing so would make the same commit
produce different deployment artifacts over time.

### Archive and Manifest

1. Run the local Scryfall processing pipeline.
2. Archive only the four processed JSON files.
3. Upload the archive to a versioned key such as
   `reference-data/2026-08-05/reference-data.zip`.
4. Generate a SHA-256 checksum.
5. Commit a small manifest containing:
   - schema version
   - reference-data version or date
   - S3 bucket and key
   - archive SHA-256
   - expected uncompressed file names
6. CI downloads the exact object named by the manifest and rejects a checksum
   mismatch before packaging.

The manifest is the reproducibility boundary: a code commit always identifies
the exact reference data used to build it.

### Bucket Controls

- Keep the staging bucket private.
- Enable versioning.
- Scope the CI OIDC role to read only the reference-data prefix.
- Use a separate controlled identity or workflow for archive uploads.
- Treat versioned keys as immutable; never overwrite an existing version.
- Add retention rules later if obsolete archives begin accumulating
  meaningful storage.

## Refresh Workflow

Reference refresh remains manual for the MVP:

```powershell
python scripts/download_scryfall.py
python scripts/process_scryfall.py
```

After reviewing the generated classification changes:

1. archive the processed files
2. upload a new versioned object
3. update and commit the manifest
4. run CI tests and package validation
5. deploy the code and reference-data version atomically

The application must never download a changing Scryfall data set during a
request or Lambda cold start.

## CI Pipeline

The backend GitHub Actions job should:

1. authenticate to AWS through GitHub OIDC
2. read the committed manifest
3. download the reference-data archive
4. verify its SHA-256 and expected contents
5. install platform-targeted Lambda dependencies
6. assemble application code, dependencies, and processed JSON
7. record compressed and uncompressed artifact sizes
8. run backend tests against the staged data where appropriate
9. run `cdk deploy`

The frontend job remains separate:

1. run frontend tests and `npm run build`
2. synchronize the build to the private frontend bucket
3. invalidate `/index.html` in CloudFront

## Lambda Layer Decision

A dedicated reference-data layer is optional and cadence-motivated, not
size-motivated. A layer can prevent a small code change from re-uploading the
data set, but code plus all attached layers still share the 250 MB unzipped
limit.

Do not introduce a layer until deployment frequency demonstrates that the
separation is worth the additional version-management complexity.

## Verification Checklist

- [ ] The archive contains exactly the four processed JSON files.
- [ ] The manifest checksum is verified before packaging.
- [ ] CI can reproduce the same artifact from the same commit.
- [ ] Runtime-only dependencies are used.
- [ ] Linux arm64 wheels are installed successfully.
- [ ] Compressed and uncompressed package sizes are recorded.
- [ ] The Lambda can load the packaged data through `REFERENCE_DATA_DIR`.
- [ ] Updating reference data requires a reviewed manifest commit.
