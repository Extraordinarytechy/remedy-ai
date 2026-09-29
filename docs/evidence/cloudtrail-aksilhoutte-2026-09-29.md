# CloudTrail: calls made with `aksilhoutte` since 2026-09-29

Exported 2026-09-29T18:56:18+00:00 from CloudTrail event history (`aws cloudtrail lookup-events`). Account IDs and IPs redacted.

- Total events: **539**, of which **52** changed something (ReadOnly=false).

| Client (from userAgent) | Mutating calls |
| --- | ---: |
| AWS CloudFormation | 37 |
| other | 12 |
| AWS CLI | 3 |

| Service | Mutating calls |
| --- | ---: |
| iam.amazonaws.com | 11 |
| s3.amazonaws.com | 8 |
| cloudfront.amazonaws.com | 6 |
| cloudformation.amazonaws.com | 5 |
| lambda.amazonaws.com | 5 |
| notifications-contacts.amazonaws.com | 4 |
| logs.amazonaws.com | 4 |
| dynamodb.amazonaws.com | 3 |
| kms.amazonaws.com | 2 |
| apigateway.amazonaws.com | 2 |
| budgets.amazonaws.com | 1 |
| scheduler.amazonaws.com | 1 |

First and last mutating calls:

- `2026-09-30T00:06:09+05:30` CreateChangeSet (cloudformation.amazonaws.com) request fcc42498-969e-4b0c-9549-a7b18fe5b2d4
- `2026-09-30T00:06:22+05:30` ExecuteChangeSet (cloudformation.amazonaws.com) request 987ad5e9-0a00-4fa2-8830-3665db2cfc7c
- `2026-09-30T00:06:25+05:30` CreateResponseHeadersPolicy (cloudfront.amazonaws.com) request af414b68-11fc-450d-831b-3862120ed6e7
- `2026-09-30T00:06:25+05:30` CreateOriginAccessControl (cloudfront.amazonaws.com) request daf7d2bd-9938-4514-be55-7f2588e1855d
- `2026-09-30T00:06:25+05:30` CreateEmailContact (notifications-contacts.amazonaws.com) request 84207501-32e0-4792-abcd-f024415d9151
- `2026-09-30T00:18:56+05:30` UpdateFunctionCode20150331v2 (lambda.amazonaws.com) request 6ad97ae3-90e9-4d88-8ca2-ee9017e88949
- `2026-09-30T00:18:56+05:30` UpdateFunctionCode20150331v2 (lambda.amazonaws.com) request 4a681162-ab87-446f-a1fc-1b0b9fbb2519
- `2026-09-30T00:19:33+05:30` CreateInvalidation (cloudfront.amazonaws.com) request 0e73df12-d5a5-4358-a3b1-8f9ca0941b63
- `2026-09-30T00:22:34+05:30` CreateChangeSet (cloudformation.amazonaws.com) request 387b805e-dd26-419f-bec5-17c264f15944
- `2026-09-30T00:23:01+05:30` CreateInvalidation (cloudfront.amazonaws.com) request 6a372a6f-4bda-44b1-ae7f-890697e5edf0
