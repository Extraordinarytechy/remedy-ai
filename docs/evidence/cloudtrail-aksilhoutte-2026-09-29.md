# CloudTrail: calls made with `aksilhoutte` since 2026-09-29

Exported 2026-10-01T14:05:57+00:00 from CloudTrail event history (`aws cloudtrail lookup-events`). All times are UTC (CloudTrail `eventTime`). Account IDs and IPs redacted.

- Total events: **2951**, of which **132** changed something (ReadOnly=false).

| Client (from userAgent) | Mutating calls |
| --- | ---: |
| CloudFormation (stack deployed by the agent) | 73 |
| AWS SDK for Python (SAM CLI internals, run by the agent) | 28 |
| AWS CLI (run by the agent) | 22 |
| other: spendlimit_member.budgets.amazonaws.com | 4 |
| other: dynamodb.amazonaws.com | 2 |
| other: organizations.amazonaws.com | 2 |
| other: apigateway.amazonaws.com | 1 |

| Service | Mutating calls |
| --- | ---: |
| lambda.amazonaws.com | 30 |
| cloudformation.amazonaws.com | 28 |
| cloudfront.amazonaws.com | 24 |
| iam.amazonaws.com | 16 |
| s3.amazonaws.com | 8 |
| notifications-contacts.amazonaws.com | 4 |
| logs.amazonaws.com | 4 |
| organizations.amazonaws.com | 4 |
| dynamodb.amazonaws.com | 3 |
| sns.amazonaws.com | 3 |
| kms.amazonaws.com | 2 |
| apigateway.amazonaws.com | 2 |
| monitoring.amazonaws.com | 2 |
| budgets.amazonaws.com | 1 |
| scheduler.amazonaws.com | 1 |

First and last mutating calls:

- `2026-09-29T18:36:09Z` CreateChangeSet (cloudformation.amazonaws.com) request fcc42498-969e-4b0c-9549-a7b18fe5b2d4
- `2026-09-29T18:36:22Z` ExecuteChangeSet (cloudformation.amazonaws.com) request 987ad5e9-0a00-4fa2-8830-3665db2cfc7c
- `2026-09-29T18:36:25Z` CreateResponseHeadersPolicy (cloudfront.amazonaws.com) request af414b68-11fc-450d-831b-3862120ed6e7
- `2026-09-29T18:36:25Z` CreateOriginAccessControl (cloudfront.amazonaws.com) request daf7d2bd-9938-4514-be55-7f2588e1855d
- `2026-09-29T18:36:25Z` CreateEmailContact (notifications-contacts.amazonaws.com) request 84207501-32e0-4792-abcd-f024415d9151
- `2026-10-01T14:00:56Z` UpdateFunctionCode20150331v2 (lambda.amazonaws.com) request f67baa14-1188-47a8-beac-4569da7a4720
- `2026-10-01T14:00:59Z` Subscribe (sns.amazonaws.com) request 51a67e91-ae71-5ac2-98c3-1da9c7aab765
- `2026-10-01T14:01:01Z` SetTopicAttributes (sns.amazonaws.com) request d8c41b20-9732-5ca9-9078-7818feef35cc
- `2026-10-01T14:01:02Z` PutMetricAlarm (monitoring.amazonaws.com) request c5697fb2-abb4-4e60-89f3-fd485a1e03c0
- `2026-10-01T14:01:02Z` PutMetricAlarm (monitoring.amazonaws.com) request 9803eedd-0c3c-48a3-98cb-5e24026f5df0
