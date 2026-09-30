# Evidence

These files show that the coding agent (Kiro) was connected to this AWS account and built and
deployed RemedyAI. Account IDs, email addresses and IP addresses are masked; everything else
is as AWS and the scripts produced it.

## Start here

| File | What it proves |
| --- | --- |
| [`cloudtrail-aksilhoutte-2026-09-29.md`](cloudtrail-aksilhoutte-2026-09-29.md) | AWS's own record (CloudTrail) of every API call made with the agent's IAM user: totals, which clients made them (SAM CLI, AWS CLI, CloudFormation) and the first and last changes, each with its AWS request ID. |
| [`e2e-live.txt`](e2e-live.txt) | The latest end-to-end run against the live site: the four examples, a real Amazon Textract and Bedrock read, the receipt-country check blocking and then releasing a claim PDF, the removed endpoint, iPhone 18 Pro, the Mac mini program and the Source Watch gap alert. |
| Latest `deploy-*.log` | A complete deploy by the agent: caller identity, arm64 Lambda package, `sam validate --lint`, the CloudFormation change set, site upload, a Source Watch run and a smoke test of the live URL. |

## All files

| File | Contents |
| --- | --- |
| `cloudtrail-aksilhoutte-2026-09-29.json` | The full CloudTrail export behind the summary (one row per event, with request IDs). |
| `deploy-20260929T183512Z.log` | First deploy: the stack is created from nothing. |
| `deploy-20260929T184745Z.log` to `deploy-20260929T190504Z.log` | Same-day fixes and redeploys (Source Watch, upload flow, spend guard, writeup links). `185404Z` shows a failed run from a shell syntax error in the deploy script, fixed in the next run; it is kept on purpose. |
| `deploy-20260930T*.log` | Deploys for the claim-integrity checks, security hardening, the redesign, new Apple sources and Source Watch changes. |

Regenerate the CloudTrail export with `python3 scripts/export_cloudtrail.py --user <iam-user> --since YYYY-MM-DD`, then mask it with `python3 scripts/redact_evidence.py`.
