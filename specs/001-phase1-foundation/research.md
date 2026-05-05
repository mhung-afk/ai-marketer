# Phase 0 Research: Phase 1 Foundation – AWS Infrastructure

**Date**: 2026-05-03  
**Status**: Complete  
**Completed by**: Planning workflow

---

## Research Findings

### Topic 1: AWS CDK Best Practices for Serverless IaC

**Research Question**: What are AWS CDK best practices for defining serverless infrastructure as code?

**Decision**: Use AWS CDK v2 with Python for infrastructure definition. Single stack (`HealingBedroomStack`) containing all Phase 1 resources. Leverage CDK constructs for DynamoDB, S3, CloudFront, IAM, CloudWatch.

**Rationale**: 
- CDK is easier to read and maintain than CloudFormation templates (Terraform alternative ruled out due to learning curve for solo developer)
- Python matches project language (Claude Haiku for LLMs, Python for orchestration)
- Single stack keeps deployment simple (single `cdk deploy` command deploys all resources)

**Alternatives Considered**:
- CloudFormation YAML/JSON (too verbose, harder to maintain)
- Terraform (requires HCL learning, adds operational overhead)
- Manual AWS Console setup (not reproducible, error-prone)

**Implementation Notes**:
- Use CDK context for environment-specific config (AWS region, budget amount)
- Export stack outputs (table name, bucket name, CloudFront URL) for Phase 2+ Lambda functions
- Add CDK assertions for testing (validate permissions, resource names)

---

### Topic 2: DynamoDB UUID v4 Generation & Partition Key Design

**Research Question**: How to generate and validate UUID v4 partition keys for DynamoDB items in Python?

**Decision**: Use Python `uuid.uuid4()` library to generate UUID v4 strings. Store as string type in DynamoDB (not binary). Partition key name: `item_id`.

**Rationale**:
- UUID v4 is stateless (no collision risk even with concurrent generation)
- String type simpler to debug and query than binary
- `uuid.uuid4()` is stdlib (no external dependency)
- Distributed generation: each Lambda can independently generate UUIDs without coordination

**Alternatives Considered**:
- ULID (newer, smaller, sortable) – overkill for Phase 1, added complexity
- Increment integers (simpler, but requires coordination/central counter)
- Timestamp-based IDs (simpler for some workloads, but less collision-safe)

**Implementation Notes**:
- Lambda layer or common utility function: `generate_item_id()` returns `str(uuid.uuid4())`
- DynamoDB key schema: `item_id` (Partition Key, String)
- Test for uniqueness: generate 10k UUIDs, verify no collisions

---

### Topic 3: S3 Lifecycle Policy Configuration & Cost Optimization

**Research Question**: How to configure S3 lifecycle policies to automatically delete objects after N days and minimize costs?

**Decision**: Enable S3 lifecycle rule to delete all objects after 7 days of creation. No versioning (increases cost). No MFA Delete (not needed for MVP). CloudFront TTL set to 1 day for images.

**Rationale**:
- 7-day lifecycle matches project's transient content model (images are temporary, consumed, then deleted)
- Prevents storage costs from accumulating over months
- Reduces average storage to < 1 GB (cost benefit substantial)
- Aligns with budget constraint ($40/month)

**Alternatives Considered**:
- No lifecycle policy (risky—storage costs grow unbounded)
- 30-day lifecycle (higher average cost, unclear benefit)
- S3 Intelligent-Tiering (added complexity, marginal savings for MVP)
- Archive to Glacier (overkill—we delete, don't archive)

**Implementation Notes**:
- CDK `s3.LifecycleRule`: `expiration.after_days(7)`
- Versioning disabled in CDK construct
- Document in README: "Images auto-delete after 7 days; for permanent storage, move to separate archive bucket in Phase 3+"

---

### Topic 4: CloudFront Origin Access Control (OAC) & HTTPS Configuration

**Research Question**: How to use CloudFront OAC to serve S3 objects publicly while keeping S3 private?

**Decision**: Use CloudFront Origin Access Control (OAC) instead of legacy Origin Access Identity (OAI). Configure CloudFront to serve HTTPS only (HTTP redirected to HTTPS). Cache policy: 1 day for images, 1 hour for metadata.

**Rationale**:
- OAC is AWS's newer approach (OAI deprecated); allows more granular permissions
- HTTPS-only prevents man-in-the-middle attacks
- Cache TTL reduces origin requests, lowering DynamoDB + S3 costs
- Images served via CloudFront URL (e.g., `https://d123abc.cloudfront.net/image.jpg`)

**Alternatives Considered**:
- Direct S3 public URLs (no security—anyone can list bucket)
- CloudFront with legacy OAI (still works but deprecated)
- Presigned S3 URLs (adds Lambda complexity for generating URLs)

**Implementation Notes**:
- CDK: `cloudfront.Distribution` with S3 origin + OAC
- Behavior: `/` → origin (S3), cache policy 1 day
- HTTPS viewer protocol policy (redirect HTTP → HTTPS)
- Custom domain optional (Phase 2+)

---

### Topic 5: IAM Role Least-Privilege Pattern for Lambda + DynamoDB + S3

**Research Question**: How to design IAM permissions for Lambda to access DynamoDB and S3 with minimum required privileges?

**Decision**: Single shared `lambda-healing-bedroom-role` with:
- DynamoDB: `dynamodb:GetItem`, `dynamodb:PutItem`, `dynamodb:UpdateItem`, `dynamodb:Query`, `dynamodb:Scan` on table ARN only (no wildcard)
- S3: `s3:GetObject`, `s3:PutObject`, `s3:ListBucket` on bucket ARN + objects under bucket (no delete, no bucket management)
- Parameter Store: `ssm:GetParameter`, `ssm:GetParameters` on path `/healing-bedroom/*` only
- CloudWatch Logs: `logs:CreateLogGroup`, `logs:CreateLogStream`, `logs:PutLogEvents` on log group `/aws/lambda/healing-bedroom-*`

**Rationale**:
- Explicit resource ARNs (no wildcards) prevent accidental permission escalation
- Single role simpler for MVP (per-function roles deferred to Phase 2+)
- Each permission scoped to only what that function needs
- Follows AWS best practices (least privilege principle)

**Alternatives Considered**:
- AmazonDynamoDBFullAccess + AmazonS3FullAccess (too broad, violates least privilege)
- Per-function roles (Phase 1 simplicity vs Phase 2+ security—deferred)
- Service-linked roles (not applicable for this use case)

**Implementation Notes**:
- CDK `iam.Role` with inline policies (not managed policies for fine-grained control)
- Document in README: "Each Lambda function must explicitly allow actions in their code"
- Test IAM policy: create test Lambda, attempt denied action, verify CloudWatch rejection

---

### Topic 6: Parameter Store vs AWS Secrets Manager Trade-off

**Research Question**: Should we use Parameter Store or Secrets Manager for storing API keys?

**Decision**: Use AWS Systems Manager Parameter Store (standard tier) instead of Secrets Manager.

**Rationale**:
- Standard Parameter Store: free (no per-secret cost)
- Secrets Manager: $0.40/secret/month (5 secrets × $0.40 = $2/month—acceptable but not needed for MVP)
- Standard tier sufficient for non-critical settings (API keys are semi-critical but not encryption-critical for Phase 1)
- Manual rotation (developer updates value in console) is acceptable for Phase 1 tempo
- Reduces infrastructure complexity (one fewer service to manage)

**Alternatives Considered**:
- Secrets Manager with auto-rotation Lambda (too complex, deferred to Phase 4+)
- Environment variables (not secure—risk of exposure in logs/source control)
- .env file (not centralized, hard to rotate across instances)

**Implementation Notes**:
- Parameter naming convention: `/healing-bedroom/[service-name]` (e.g., `/healing-bedroom/anthropic-api-key`)
- CDK: `ssm.StringParameter` for each key
- Update process: developer updates parameter in AWS console → Lambda picks up on next invocation
- Add to README: "To rotate a parameter: AWS Systems Manager → Parameter Store → Edit → update value"

---

### Topic 7: CloudWatch Logs Retention & Cost Optimization

**Research Question**: How to configure CloudWatch Logs retention to balance debugging needs with cost?

**Decision**: CloudWatch Logs retention set to 7 days (default). Lambda functions log to `/aws/lambda/healing-bedroom-*` log groups. No log aggregation service (e.g., Datadog, CloudWatch Insights queries) in Phase 1.

**Rationale**:
- 7 days retention sufficient for debugging Phase 1 Lambda invocations
- CloudWatch Logs free tier: 5 GB ingestion/month (more than enough for MVP Lambda traffic)
- Longer retention (30+ days) adds cost; not needed for Phase 1 iteration
- Queries via CloudWatch console or AWS CLI sufficient for MVP

**Alternatives Considered**:
- No retention (dangerous—can't debug past issues)
- 30-day retention (cost-effective if within free tier, but adds complexity)
- Central logging service (Phase 2+ improvement)

**Implementation Notes**:
- CDK: `logs.RetentionMode` set to `SEVEN_DAYS`
- Lambda functions use standard `print()` or `logging` library; CDK auto-creates log groups
- Test: invoke Lambda, verify logs appear in CloudWatch within 1–2 seconds

---

### Topic 8: AWS Budget Alarm Configuration & Telegram Integration

**Research Question**: How to configure AWS Budget alerts to trigger SNS → Lambda → Telegram notifications?

**Decision**: AWS Budget set to $40/month with thresholds at 50% ($20) and 80% ($32). Alerts publish to SNS topic. SNS triggers Notifier Lambda which sends formatted message to Telegram via Bot API.

**Rationale**:
- Budget alarm fires automatically when threshold is reached (no manual monitoring needed)
- SNS provides reliable, scalable message routing
- Telegram provides real-time, low-latency notifications (developer always aware of spending)
- Two thresholds (50%, 80%) give early warning + urgent alert

**Alternatives Considered**:
- CloudWatch alarms directly (less integrated with AWS Cost management)
- Email alerts (slower, can miss in inbox)
- Slack (alternative to Telegram; Telegram chosen for existing bot)

**Implementation Notes**:
- CDK: `budgets.CfnBudget` resource
- SNS topic: `healing-bedroom-budget-alerts`
- Notifier Lambda: parses SNS message, fetches Telegram Bot Token from Parameter Store, sends formatted alert
- Test: set budget to low value (e.g., $5), trigger alert, verify Telegram message received

---

## Resolved Clarifications

All 3 clarifications from the specification have been incorporated:

1. **IAM Role Strategy**: Single shared role with fine-grained resource ARNs (Research Topic 5 covers implementation)
2. **DynamoDB Cost Control**: On-demand billing monitored via Budget alerts (Research Topic 8 covers Telegram integration)
3. **Secret Management**: Parameter Store instead of Secrets Manager (Research Topic 6 provides rationale)

---

## Summary: Ready for Phase 1 Design

✅ All research questions have been answered with decisions and rationale.  
✅ All clarifications from specification incorporated.  
✅ All alternatives evaluated and documented.  
✅ Implementation notes provided for Phase 1 design + Phase 2+ development.

**Next Step**: Proceed to Phase 1 design (data-model.md, contracts/, quickstart.md).
