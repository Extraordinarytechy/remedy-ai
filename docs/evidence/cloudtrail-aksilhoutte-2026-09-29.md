# CloudTrail: calls made with `aksilhoutte` since 2026-09-29

Exported 2026-09-30T17:16:59+00:00 from CloudTrail event history (`aws cloudtrail lookup-events`). All times are UTC (CloudTrail `eventTime`). Account IDs and IPs redacted.

- Total events: **1311**, of which **73** changed something (ReadOnly=false).

| Client (from userAgent) | Mutating calls |
| --- | ---: |
| CloudFormation (stack deployed by the agent) | 48 |
| AWS SDK for Python (SAM CLI internals, run by the agent) | 12 |
| AWS CLI (run by the agent) | 6 |
| other: spendlimit_member.budgets.amazonaws.com | 4 |
| other: dynamodb.amazonaws.com | 2 |
| other: apigateway.amazonaws.com | 1 |

| Service | Mutating calls |
| --- | ---: |
| lambda.amazonaws.com | 13 |
| cloudformation.amazonaws.com | 12 |
| iam.amazonaws.com | 12 |
| cloudfront.amazonaws.com | 11 |
| s3.amazonaws.com | 8 |
| notifications-contacts.amazonaws.com | 4 |
| logs.amazonaws.com | 4 |
| dynamodb.amazonaws.com | 3 |
| kms.amazonaws.com | 2 |
| apigateway.amazonaws.com | 2 |
| budgets.amazonaws.com | 1 |
| scheduler.amazonaws.com | 1 |

First and last mutating calls:

- `2026-09-29T18:36:09Z` CreateChangeSet (cloudformation.amazonaws.com) request fcc42498-969e-4b0c-9549-a7b18fe5b2d4
- `2026-09-29T18:36:22Z` ExecuteChangeSet (cloudformation.amazonaws.com) request 987ad5e9-0a00-4fa2-8830-3665db2cfc7c
- `2026-09-29T18:36:25Z` CreateResponseHeadersPolicy (cloudfront.amazonaws.com) request af414b68-11fc-450d-831b-3862120ed6e7
- `2026-09-29T18:36:25Z` CreateOriginAccessControl (cloudfront.amazonaws.com) request daf7d2bd-9938-4514-be55-7f2588e1855d
- `2026-09-29T18:36:25Z` CreateEmailContact (notifications-contacts.amazonaws.com) request 84207501-32e0-4792-abcd-f024415d9151
- `2026-09-30T17:04:49Z` UpdateFunctionCode20150331v2 (lambda.amazonaws.com) request ca6ce252-b1a7-4f7e-93be-6c3fb582d719
- `2026-09-30T17:05:00Z` UpdateFunctionConfiguration20150331v2 (lambda.amazonaws.com) request 943d4eae-cd73-4d71-a41d-56894517c012
- `2026-09-30T17:05:07Z` UpdateFunctionCode20150331v2 (lambda.amazonaws.com) request f0186f29-c9a2-4bbb-bf2a-4d371b2bfcd8
- `2026-09-30T17:05:17Z` UpdateDistribution (cloudfront.amazonaws.com) request ead690ef-1605-41ee-a06f-740fe9f06867
- `2026-09-30T17:06:52Z` CreateInvalidation (cloudfront.amazonaws.com) request 4112ac51-0d54-4ea0-a8d5-e292ac8cf1a2
