# CloudTrail: calls made with `aksilhoutte` since 2026-09-29

Exported 2026-09-29T18:58:30+00:00 from CloudTrail event history (`aws cloudtrail lookup-events`). All times are UTC (CloudTrail `eventTime`). Account IDs and IPs redacted.

- Total events: **748**, of which **56** changed something (ReadOnly=false).

| Client (from userAgent) | Mutating calls |
| --- | ---: |
| CloudFormation (stack deployed by the agent) | 39 |
| SDK (boto3) | 7 |
| other: spendlimit_member.budgets.amazonaws.com | 4 |
| AWS CLI (run by the agent) | 3 |
| other: dynamodb.amazonaws.com | 2 |
| other: apigateway.amazonaws.com | 1 |

| Service | Mutating calls |
| --- | ---: |
| iam.amazonaws.com | 11 |
| s3.amazonaws.com | 8 |
| cloudformation.amazonaws.com | 7 |
| lambda.amazonaws.com | 7 |
| cloudfront.amazonaws.com | 6 |
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
- `2026-09-29T18:53:01Z` CreateInvalidation (cloudfront.amazonaws.com) request 6a372a6f-4bda-44b1-ae7f-890697e5edf0
- `2026-09-29T18:54:53Z` CreateChangeSet (cloudformation.amazonaws.com) request 3dc874a2-3649-4cd0-94e6-9d4ba071667f
- `2026-09-29T18:55:12Z` ExecuteChangeSet (cloudformation.amazonaws.com) request 3565f597-57bc-473b-aa1d-82f173a90651
- `2026-09-29T18:55:18Z` UpdateFunctionCode20150331v2 (lambda.amazonaws.com) request 2d546777-237b-4d21-b3d5-e78a144df405
- `2026-09-29T18:55:18Z` UpdateFunctionCode20150331v2 (lambda.amazonaws.com) request 4130c865-d0dc-4c9f-9a5e-ab7d62ff819a
