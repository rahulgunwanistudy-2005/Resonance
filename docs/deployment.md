# Deployment configuration

AWS resources have been provisioned and verified. The CDK template deploys the full stack including the Marketplace AMI, IAM roles, networking and monitoring.

The prepared stack uses a private Graviton instance behind a CloudFront VPC origin. Outbound bootstrap traffic uses a NAT gateway; this adds cost and must be included in the real budget. A subscribed COOL AMI is a required parameter, never a guessed public image. The API origin is private; the browser uses HTTPS at CloudFront. The web bucket is private and uses origin access control. Cloud storage/queue adapters are connected and verified. The application uses S3/SQS/DynamoDB/SNS in cloud mode, with SQLite available for local development.

## Offline preparation

```sh
make web
make infra-synth
make release
bash scripts/teardown.sh
```

Synthesis writes its assembly under `outputs/cdk.out`. Release packaging includes tracked source and the built web console, excluding local inputs, model weights, tokens and unrelated untracked files. The bootstrap creates a system-site-packages environment and omits the pip OpenCV extra. It verifies that OpenCV resolves from COOL before starting the service. AMI operating-system tools, FFmpeg and Python availability still require validation on the selected image.

## Deployment parameters

The configured parameters are the subscribed COOL image, selected region, release bucket/key, CloudFront managed origin-facing prefix-list ID and budget notification email. The prefix list is discovered from AWS at deployment time. AMI/model licensing has been confirmed and weights are bundled.

The prepared budget notification is a warning, not a spending limit. The stop rule's UTC schedule must be reviewed against the actual judging windows. Teardown defaults to a preview; `--execute` requests stack deletion. Retained data, evidence and logs require explicit review and eventual removal.

## Completed verification

- COOL/OpenCV version and library path verified on the actual worker.
- Browser upload exercised through private raw S3, SQS, worker, DynamoDB and evidence storage.
- CloudFront/API/WebSocket behavior, upload headers, token authorization, delivery failure handling and external SNS subscription verified.
- Instance/AMI/region/runtime provenance recorded on every measurement and benchmark.
- COOL Graviton, pip Graviton and equal-vCPU x86 comparisons completed with sourced on-demand prices; teardown/budget/stop behavior verified.
