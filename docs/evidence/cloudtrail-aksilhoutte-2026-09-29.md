# CloudTrail: calls made with `aksilhoutte` since 2026-09-29

Exported 2026-10-01T20:04:35+00:00 from CloudTrail event history (`aws cloudtrail lookup-events`). All times are UTC (CloudTrail `eventTime`). Account IDs and IPs redacted.

- Total events: **4714**, of which **168** changed something (ReadOnly=false).
- Calls whose user agent carries the `app/kiro-ide` tag (set by the agent's deploy script with `AWS_SDK_UA_APP_ID`; a client-set value, recorded by AWS as sent): **70**, first at `2026-10-01T18:05:29Z`, e.g. request a804943a-5c79-469b-90d5-3f8daa68d496.

| Client (from userAgent) | Mutating calls |
| --- | ---: |
| CloudFormation (stack deployed by the agent) | 89 |
| SAM CLI (run by the agent) | 40 |
| AWS CLI (run by the agent) | 30 |
| other: budgets.amazonaws.com | 4 |
| other: dynamodb.amazonaws.com | 2 |
| other: organizations.amazonaws.com | 2 |
| other: apigateway.amazonaws.com | 1 |

| Service | Mutating calls |
| --- | ---: |
| lambda.amazonaws.com | 42 |
| cloudformation.amazonaws.com | 40 |
| cloudfront.amazonaws.com | 32 |
| iam.amazonaws.com | 16 |
| s3.amazonaws.com | 8 |
| notifications-contacts.amazonaws.com | 4 |
| dynamodb.amazonaws.com | 4 |
| logs.amazonaws.com | 4 |
| organizations.amazonaws.com | 4 |
| sns.amazonaws.com | 4 |
| monitoring.amazonaws.com | 4 |
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
- `2026-10-01T19:49:33Z` UpdateContinuousBackups (dynamodb.amazonaws.com) request AGPILA2QLQ2F1RTFNLL369QQ3BVV4KQNSO5AEMVJF66Q9ASUAAJG
- `2026-10-01T19:49:39Z` UpdateFunctionCode20150331v2 (lambda.amazonaws.com) request 5e8939cd-767b-49d8-8a72-60baacb89890
- `2026-10-01T19:49:39Z` UpdateFunctionCode20150331v2 (lambda.amazonaws.com) request 0e4519e9-0629-4597-bdb6-d067faeab1fe
- `2026-10-01T19:50:48Z` CreateInvalidation (cloudfront.amazonaws.com) request 527dc3e2-c79f-4de6-8b0c-2c982911b5e9
- `2026-10-01T19:55:06Z` SetAlarmState (monitoring.amazonaws.com) request 8eeeeb0f-cf16-421e-83ac-6d4f19f33686
