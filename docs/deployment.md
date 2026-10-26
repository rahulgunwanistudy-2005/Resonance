# Deployment preparation and deferred cloud gate

AWS access is deferred at Rahul's request. No resource was created and no credentials were requested again. The CDK template synthesizes locally; that does not verify a Marketplace AMI, live IAM, networking or a deployment.

The prepared stack uses a private Graviton instance behind a CloudFront VPC origin. Outbound bootstrap traffic uses a NAT gateway; this adds cost and must be included in the real budget. A subscribed COOL AMI is a required parameter, never a guessed public image. The API origin is private; the browser uses HTTPS at CloudFront. The web bucket is private and uses origin access control. Cloud storage/queue adapters are prepared independently; the running application still uses the local SQLite transport. Connecting and verifying those adapters is part of the deferred AWS phase.

## Offline preparation

```sh
make web
make infra-synth
make release
bash scripts/teardown.sh
```

Synthesis writes its assembly under `outputs/cdk.out`. Release packaging includes tracked source and the built web console, excluding local inputs, model weights, tokens and unrelated untracked files. The bootstrap creates a system-site-packages environment and omits the pip OpenCV extra. It verifies that OpenCV resolves from COOL before starting the service. AMI operating-system tools, FFmpeg and Python availability still require validation on the selected image.

## Later deployment inputs

The required parameters are the subscribed COOL image, selected region, release bucket/key, CloudFront managed origin-facing prefix-list ID and budget notification email. The prefix list can be discovered from AWS at deployment time; it is not hardcoded. The local stack requires no account lookup for synthesis. Confirm all AMI/model licensing before bundling weights.

The prepared budget notification is a warning, not a spending limit. The stop rule's UTC schedule must be reviewed against the actual judging windows. Teardown defaults to a preview; `--execute` requests stack deletion. Retained data, evidence and logs require explicit review and eventual removal.

## Required live verification

- Verify COOL/OpenCV version and library path on the actual worker; stop if the image supplies an incompatible runtime.
- Exercise browser upload through private raw S3, SQS, worker, DynamoDB and evidence storage; the local SQLite demonstration is not evidence of this integration.
- Verify CloudFront/API/WebSocket behavior, upload headers, token authorization, delivery failure handling and external SNS subscription.
- Record actual instance/AMI/region/runtime provenance on every measurement and benchmark.
- Run COOL Graviton, pip Graviton and equal-vCPU x86 comparisons, obtain sourced on-demand prices and verify teardown/budget/stop behavior.
