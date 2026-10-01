# CloudTrail: calls made with `aksilhoutte` since 2026-09-29

Exported 2026-10-01T18:31:51+00:00 from CloudTrail event history (`aws cloudtrail lookup-events`). All times are UTC (CloudTrail `eventTime`). Account IDs and IPs redacted.

- Total events: **4299**, of which **159** changed something (ReadOnly=false).
- Calls whose user agent carries the `app/kiro-ide` tag (set by the agent's deploy script with `AWS_SDK_UA_APP_ID`; a client-set value, recorded by AWS as sent): **29**, first at `2026-10-01T18:05:29Z`, e.g. request a804943a-5c79-469b-90d5-3f8daa68d496.

| Client (from userAgent) | Mutating calls |
| --- | ---: |
| CloudFormation (stack deployed by the agent) | 84 |
| SAM CLI (run by the agent) | 38 |
| AWS CLI (run by the agent) | 28 |
| other: spendlimit_member.budgets.amazonaws.com | 4 |
| other: dynamodb.amazonaws.com | 2 |
| other: organizations.amazonaws.com | 2 |
| other: apigateway.amazonaws.com | 1 |

| Service | Mutating calls |
| --- | ---: |
| lambda.amazonaws.com | 40 |
| cloudformation.amazonaws.com | 38 |
| cloudfront.amazonaws.com | 30 |
| iam.amazonaws.com | 16 |
| s3.amazonaws.com | 8 |
| notifications-contacts.amazonaws.com | 4 |
| logs.amazonaws.com | 4 |
| organizations.amazonaws.com | 4 |
| dynamodb.amazonaws.com | 3 |
| sns.amazonaws.com | 3 |
| monitoring.amazonaws.com | 3 |
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
- `2026-10-01T18:06:41Z` CreateChangeSet (cloudformation.amazonaws.com) request 1728fd77-e6b1-4225-b607-3c86149dff85
- `2026-10-01T18:07:00Z` ExecuteChangeSet (cloudformation.amazonaws.com) request 0364960b-6468-402f-b738-a1a923df6391
- `2026-10-01T18:07:07Z` UpdateFunctionCode20150331v2 (lambda.amazonaws.com) request 18734187-e5cd-472b-8823-0eb95df65443
- `2026-10-01T18:07:07Z` UpdateFunctionCode20150331v2 (lambda.amazonaws.com) request ba34a43e-d1bf-44a9-a1a5-33001cf84974
- `2026-10-01T18:08:11Z` CreateInvalidation (cloudfront.amazonaws.com) request 364099ff-2e1c-48ad-9c47-0b22b520cd7d
