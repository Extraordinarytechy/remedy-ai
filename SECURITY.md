# Security

## Reporting a vulnerability

Please report security issues privately through GitHub's
[private vulnerability reporting](https://github.com/Extraordinarytechy/remedy-ai/security/advisories/new)
rather than a public issue. Include the steps to reproduce and the impact you expect.
Reports are usually acknowledged within a few days.

Please don't test against the live site in ways that could affect other visitors
(load testing, or trying to use up the daily photo-reading limit).

## What is in place

| Area | Measure |
| --- | --- |
| Data | Nothing a user enters is stored. No accounts, cookies or analytics. Error logs keep only the error type, for 14 days. |
| Uploads | Optional. Re-encoded in the browser (EXIF/GPS removed), 4 MB limit, type checked by magic bytes, sent only on an explicit action after a privacy prompt. |
| Claim PDF | Built only from the server's own evaluation of the case; any evaluation sent by the client is ignored. All text is escaped before it reaches the PDF engine. Refused while a hard consistency check is unconfirmed. |
| Abuse and cost | API Gateway throttling (10 req/s, burst 20). Paid AI calls capped per UTC day overall and per visitor; visitors are counted by an HMAC of the IP with a random daily key (2-day TTL), never the raw IP. The cap fails closed. AWS Budgets alert. |
| Input | Length limits on every free-text field; strict schema validation (Pydantic); generic error messages. |
| Transport and browser | HTTPS only, HSTS, a strict Content Security Policy (`default-src 'self'`, no third-party scripts, fonts or images), `X-Frame-Options: DENY`, `nosniff`. |
| Infrastructure | Private S3 buckets behind CloudFront Origin Access Control, encryption at rest, one least-privilege IAM role per function, one SAM template. The API only answers requests that carry CloudFront's secret origin header (a random 256-bit value, passed as a NoEcho parameter and masked in deploy logs), so the API Gateway URL can't be used to skip the security headers or forge the visitor address used by the per-visitor limit. |
| AI data use | The AWS account has an AI services opt-out policy (AWS Organizations), so Textract content is not stored or used by AWS to improve its services. Bedrock does not use prompts or images for training. |
| Dependencies | Pinned runtime versions; `pip-audit` and `npm audit` run in CI on every push. |
