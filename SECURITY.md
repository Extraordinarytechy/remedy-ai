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
| Data | What a user enters and uploads is not saved. No accounts, cookies or third-party analytics. Logs keep only error types and anonymous totals (checks run, checks with an option, claim PDFs), for 14 days. |
| Uploads | Optional. Re-encoded in the browser (EXIF/GPS removed), 4 MB limit. The server accepts only JPEG, PNG or WebP, judged by the file's own first bytes, before anything is counted or sent to AWS. Sent only on an explicit action after a privacy prompt; what was read is shown to the user, who can leave it out. |
| Claim PDF | Built only from the server's own evaluation of the case; any evaluation sent by the client is ignored. All text is escaped before it reaches the PDF engine. Refused for dates that were refused as invalid input and while a hard consistency check is unconfirmed, and options whose source must be re-checked are never used in the claim letter. |
| Claim date | Every window is measured against the claim date, which the server sets: it accepts only the visitor's own calendar date (its UTC date ±1 day). |
| Abuse and cost | API Gateway throttling (10 req/s, burst 20). This limit is shared by all visitors, so one busy client can slow the site for others; there is no per-IP firewall rule. Paid AI calls and claim PDFs are each capped per UTC day overall and per visitor; visitors are counted by an HMAC of the IP with a random daily key (expires 2 days after last use), never the raw IP. The caps fail closed. AWS Budgets alert. |
| Source checks | If the latest Source Watch result can't be read, every option is shown as "check it first" rather than as verified. |
| Input | Length limits on every free-text field, including each photo observation and receipt field; dates must be YYYY-MM-DD; strict schema validation (Pydantic); generic error messages. Purchase dates more than 30 years before the claim date, and dates before a model's on-sale date, are refused as invalid input. |
| Transport and browser | HTTPS only, HSTS, a strict Content Security Policy (`default-src 'self'`, no third-party scripts, fonts or images), `X-Frame-Options: DENY`, `nosniff`. |
| Infrastructure | Private S3 buckets behind CloudFront Origin Access Control, encryption at rest, one least-privilege IAM role per function (DynamoDB access scoped to the item keys each function uses), one SAM template. The API only answers requests that carry CloudFront's secret origin header (a random 256-bit value, passed as a NoEcho parameter and masked in deploy logs), so the API Gateway URL can't be used to skip the security headers or forge the visitor address used by the per-visitor limit. |
| AI data use | The AWS account has an AI services opt-out policy (AWS Organizations), so Textract content is not stored or used by AWS to improve its services. Every deploy log prints the account's effective opt-out policy ([`docs/evidence/`](docs/evidence)). Bedrock does not use prompts or images for training. |
| Dependencies | Direct runtime dependencies pinned; `pip-audit` and `npm audit` run in CI on every push to `main` and on pull requests. |

## Data protection notes

RemedyAI is run from India and doesn't target EU residents. It processes UK visitors' data only briefly
(photos are read and discarded; the per-visitor code expires within days), so it relies on the UK GDPR
Article 27(2) exemption for occasional, low-risk processing and has no UK representative. This is
reviewed if the service starts storing user data.
