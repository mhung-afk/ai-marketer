# Feature Specification: Phase 1 Foundation – AWS Infrastructure

**Feature Branch**: `001-phase1-foundation`  
**Created**: 2026-05-03  
**Status**: Draft  
**Project**: Phòng Ngủ Chữa Lành – AI Marketer MVP V3.1  
**Phase**: 1 (Foundation)  
**Duration**: Week 1 (3–5 days)

---

## Clarifications

### Session 2026-05-03

- Q: Should Lambda functions share a single IAM role or have separate dedicated roles? → A: Single shared `lambda-healing-bedroom-role` with fine-grained resource ARNs (simplicity for MVP; separate roles can be introduced in Phase 2+)
- Q: How to prevent DynamoDB runaway costs with on-demand billing? → A: On-demand mode + rely on existing AWS Budget alerts to catch overages (no DynamoDB-level caps; keeps Phase 1 lean)
- Q: Secrets Manager rotation strategy and naming convention? → A: Use AWS Systems Manager Parameter Store instead (simpler, no cost for standard parameters, no rotation needed for Phase 1)

---

## User Scenarios & Testing

### User Story 1 - Deploy Base Infrastructure Programmatically (Priority: P1)

**Scenario**: As a solo developer, I want to deploy all core AWS resources (DynamoDB, S3, CloudFront, IAM, Parameter Store) as code using AWS CDK, so that I can reproduce, version-control, and iterate on infrastructure quickly without manual AWS Console clicks.

**Why this priority**: Foundation is blocking - cannot proceed with any feature development (ingestion, processing, posting) until infrastructure is in place. Reproducibility and IaC are critical for consistency and disaster recovery.

**Independent Test**: Deploy CDK stack to AWS account, verify all resources exist (tables, buckets, roles, distributions) with correct configurations, and confirm they're accessible via the CDK app output.

**Acceptance Scenarios**:

1. **Given** the CDK stack is defined in Python, **When** developer runs `cdk deploy`, **Then** all AWS resources are created with correct names, permissions, and configurations (no manual steps required).
2. **Given** infrastructure is deployed, **When** developer inspects AWS console, **Then** DynamoDB table has correct partition key (UUID), GSI, and on-demand billing mode.
3. **Given** S3 bucket is created, **When** lifecycle policy executes, **Then** objects older than 7 days are automatically deleted.
4. **Given** CloudFront distribution is deployed, **When** a test image is uploaded to S3 and accessed via CloudFront URL, **Then** image is served publicly with caching headers.

---

### User Story 2 - Store and Access Secrets Securely (Priority: P1)

**Scenario**: As a solo developer managing multiple API keys (Anthropic, fal.ai, Apify, Telegram), I want all API keys stored in AWS Systems Manager Parameter Store and accessible to Lambda functions via IAM roles, so that I never hardcode credentials and keep setup lean without rotation overhead.

**Why this priority**: Security is non-negotiable. Hard-coding secrets risks exposing them in version control. Parameter Store is a lightweight, cost-effective solution for non-sensitive config and API keys.

**Independent Test**: Deploy Parameter Store parameters, create a test Lambda with appropriate IAM role, invoke Lambda to fetch a parameter, and verify it returns the correct plaintext value.

**Acceptance Scenarios**:

1. **Given** API keys are stored in Parameter Store, **When** Lambda function assumes the `lambda-healing-bedroom-role`, **Then** Lambda can read parameters without hardcoding credentials in environment variables.
2. **Given** developer needs to rotate a parameter value (e.g., new API key), **When** they update the parameter in AWS console, **Then** Lambda can immediately retrieve the new value on next invocation.
3. **Given** Telegram Bot Token is stored in Parameter Store, **When** the Notifier Lambda retrieves it, **Then** it can successfully send test messages to Telegram.

---

### User Story 3 - Monitor and Alert on Budget Overruns (Priority: P1)

**Scenario**: As a solo developer with a tight budget (~$30–40/month), I want AWS Budget Alerts configured to notify me on Telegram when spending reaches 50% and 80% of budget, so that I catch runaway costs immediately and can take corrective action before exceeding budget.

**Why this priority**: Cost control is critical for solo developer profitability. Without monitoring, a few runaway Lambda invocations or unexpected data transfer charges can quickly exceed budget.

**Independent Test**: Set AWS Budget to a low test value (e.g., $5), trigger a test alert notification via SNS → Telegram Notifier Lambda, and verify the message arrives on Telegram with cost details.

**Acceptance Scenarios**:

1. **Given** AWS Budget is set to $40/month with alert thresholds at 50% ($20) and 80% ($32), **When** spending triggers a threshold, **Then** SNS publishes a notification.
2. **Given** SNS notification is published, **When** Notifier Lambda is triggered, **Then** it formats the alert and sends it to Telegram chat via Bot Token from Parameter Store.
3. **Given** developer receives Telegram alert, **When** they click on the message, **Then** it includes useful context (current spend, threshold, remaining budget).

---

### User Story 4 - Initialize GitHub Repository with Proper Structure (Priority: P2)

**Scenario**: As a solo developer, I want the GitHub repository to have a well-organized folder structure (cdk/, src/, prompts/, tests/, etc.) and clear documentation (README), so that future code contributions and handoffs are straightforward.

**Why this priority**: Good structure reduces friction for future phases and makes the codebase more maintainable. Not blocking Phase 1 but should be done during setup.

**Independent Test**: Clone the repository, verify folder structure matches expected layout, and confirm README provides clear setup/deployment instructions.

**Acceptance Scenarios**:

1. **Given** the repository is cloned, **When** developer lists top-level directories, **Then** they see: cdk/, src/, prompts/, tests/, .github/, requirements.txt, app.py, README.md, .env.example.
2. **Given** developer follows README setup steps, **When** they run `cdk deploy`, **Then** they successfully deploy the stack without errors.

---

### Edge Cases

- **What if** AWS CDK is not installed or Python environment is misconfigured? → Setup guide in README must include environment setup commands.
- **What if** an S3 bucket name is already taken globally? → Bucket naming should include a unique suffix (username or timestamp).
- **What if** CloudFront distribution takes 15–20 minutes to deploy? → Documentation should warn about deployment time and confirm status via CloudFront console.
- **What if** a developer accidentally deploys a stack with DynamoDB OnDemand billing but forgets to set reserved capacity limits? → CDK should enforce reasonable defaults (e.g., max 100 RCUs).
- **What if** Telegram Notifier Lambda fails silently? → CloudWatch Logs must capture all Lambda execution details for debugging.

---

## Requirements

### Functional Requirements

- **FR-001**: CDK stack MUST deploy all required AWS resources (DynamoDB table, S3 bucket, CloudFront distribution, IAM Role, Parameter Store parameters, CloudWatch Budget Alarms) in a single `cdk deploy` command.
- **FR-002**: DynamoDB table MUST have:
  - Table name: `HealingBedroomContent`
  - Partition Key: `item_id` (String – UUID v4)
  - Global Secondary Index (GSI1_Status): Partition Key `status` (String), Sort Key `created_at` (String – ISO 8601)
  - Billing mode: On-demand (monitored via AWS Budget alerts; no DynamoDB-level throughput caps in Phase 1)
  - All required attributes: item_id, status, niche, source_platform, source_url, original_caption, original_image_url, ai_caption, image_s3_key, image_cloudfront_url, post_id, post_url, scraped_at, processed_at, approved_at, posted_at, error_log, retry_count, approved_by

- **FR-003**: S3 bucket MUST:
  - Have a globally unique name (e.g., `healing-bedroom-images-[username]`)
  - Block all public access by default (all ACLs and policies set to private)
  - Have versioning disabled (to save costs)
  - Have a lifecycle policy that automatically deletes objects after 7 days

- **FR-004**: CloudFront distribution MUST:
  - Use S3 bucket as origin with Origin Access Control (OAC) to prevent public S3 access
  - Serve content over HTTPS only
  - Cache images with appropriate TTL (default 1 day for images, 1 hour for metadata)
  - Support custom cache headers

- **FR-005**: Single shared IAM Role (`lambda-healing-bedroom-role`) MUST:
  - Have permissions to read/write DynamoDB table and GSI (specific table ARN)
  - Have permissions to read/write S3 bucket and list objects (specific bucket ARN)
  - Have permissions to read parameters from AWS Systems Manager Parameter Store (path-scoped to `/healing-bedroom/*`)
  - Have permissions to write logs to CloudWatch Logs (log group scoped to `/aws/lambda/healing-bedroom-*`)
  - Follow principle of least privilege (no wildcard actions; all resource ARNs explicitly specified)
  - Applied to all Lambda functions deployed in Phase 1+ (Ingestion, Processor, Poster, Notifier); dedicated per-function roles can be introduced in Phase 2+ if needed

- **FR-006**: AWS Systems Manager Parameter Store MUST store the following API keys:
  - `/healing-bedroom/anthropic-api-key`
  - `/healing-bedroom/fal-ai-key`
  - `/healing-bedroom/telegram-bot-token`
  - `/healing-bedroom/apify-api-token` (placeholder for Phase 2)
  - `/healing-bedroom/facebook-page-access-token` (placeholder for Phase 5)
  - All parameters use standard tier (no encryption cost); manual rotation (no automated rotation Lambda in Phase 1)

- **FR-007**: AWS Budget MUST:
  - Be set to $40/month (reflecting the cost target)
  - Trigger alerts at 50% ($20) and 80% ($32) spending thresholds
  - Publish alerts to SNS topic
  - SNS topic MUST trigger Notifier Lambda to forward alerts to Telegram
  - DynamoDB on-demand mode will be monitored via Budget alerts; no DynamoDB-level throughput caps required for Phase 1

- **FR-008**: GitHub repository structure MUST include:
  - `/cdk/` – AWS CDK stack code (Python)
  - `/src/lambdas/` – Lambda functions (ingestion, processor, poster, notifier)
  - `/src/dashboard/` – Streamlit dashboard code
  - `/src/common/` – Shared utilities, schemas, configs
  - `/prompts/` – AI prompts (Claude, image generation)
  - `/tests/` – Unit and integration tests
  - `/.github/` – GitHub Actions workflows, issue templates
  - `/requirements.txt` – Python dependencies
  - `/app.py` – CDK entry point
  - `/.env.example` – Environment variable template
  - `/README.md` – Setup and deployment instructions

- **FR-009**: Lambda Notifier function MUST:
  - Receive CloudWatch Budget alerts via SNS
  - Retrieve Telegram Bot Token from AWS Systems Manager Parameter Store
  - Format alert message with: current spend, threshold, remaining budget, timestamp
  - Send formatted message to Telegram chat
  - Log all attempts (success/failure) to CloudWatch Logs

- **FR-010**: CloudWatch Logs MUST:
  - Capture all Lambda function executions (start, end, errors, duration)
  - Retain logs for minimum 7 days
  - Allow real-time log streaming and historical queries

### Key Entities

- **Content Item** (DynamoDB):
  - Represents a single piece of AI-generated content (image + caption pair)
  - Lifecycle: RAW → PROCESSING → DRAFT → APPROVED → POSTED or FAILED
  - Attributes track source, AI processing, approval, and posting status

- **S3 Image Object**:
  - AI-generated or scraped image uploaded to S3
  - Served publicly via CloudFront URL
  - Automatically cleaned up after 7 days if not moved to persistent storage

- **API Parameter** (Parameter Store):
  - API credentials for third-party services (Anthropic, fal.ai, Apify, Telegram)
  - Stored centrally in AWS Systems Manager Parameter Store (standard tier, no encryption cost)
  - Accessed by Lambda functions via IAM role
  - Manually rotated by developer updating parameter value in AWS console (no automated rotation in Phase 1)

- **AWS Budget Alert**:
  - Monitors cumulative spending against monthly budget
  - Triggers SNS notification when threshold is reached
  - Forwarded to Telegram for real-time visibility

---

## Success Criteria

### Measurable Outcomes

- **SC-001**: CDK stack deploys successfully to AWS account without manual intervention; all resources exist and are correctly configured as verified by AWS CLI or console.

- **SC-002**: DynamoDB table is operational and can accept test writes and reads; `item_id` UUID primary key generates without collisions.

- **SC-003**: S3 bucket is created with correct name, permissions, and lifecycle policy; test image upload succeeds and is automatically deleted after 7 days.

- **SC-004**: CloudFront distribution serves images via public HTTPS URL within 20 minutes of distribution creation; images are cached and subsequent requests return from cache (verified via HTTP headers).

- **SC-005**: IAM role grants Lambda functions the minimum required permissions; Lambda can read/write DynamoDB, S3, and Parameter Store without permission errors.

- **SC-006**: All API keys stored in AWS Systems Manager Parameter Store are accessible to Lambda functions; a test Lambda retrieves a parameter and returns the correct plaintext value.

- **SC-007**: AWS Budget alert fires correctly when spending reaches test thresholds; SNS notification triggers within 5 minutes of threshold breach.

- **SC-008**: Telegram Notifier Lambda successfully forwards budget alerts to Telegram chat; message is received within 2 minutes of SNS publish and includes correct cost data.

- **SC-009**: GitHub repository is initialized with correct folder structure and contains a functioning README with step-by-step setup and deployment instructions.

- **SC-010**: CloudWatch Logs capture all Lambda executions with timestamps, duration, and any errors; logs are accessible and queryable within AWS console.

- **SC-011**: Entire Phase 1 setup (from git clone to `cdk deploy` success) can be completed by a developer new to the project in under 30 minutes following README instructions.

- **SC-012**: Infrastructure costs remain under $40/month for the first month (verified by AWS Cost Explorer after 1 week of deployment).

---

## Assumptions

- **Developer Environment**: Developer has AWS CLI configured with valid credentials and an AWS account with sufficient permissions to create resources (DynamoDB, S3, CloudFront, IAM, Parameter Store, CloudWatch).

- **Python Version**: Python 3.9+ is available in the development environment.

- **AWS CDK**: AWS CDK is installed globally or available in a virtual environment.

- **Repository Access**: Developer has push access to the GitHub repository and can create feature branches.

- **API Keys Already Available**: For Phase 1, `anthropic_api_key`, `fal_ai_key`, and `telegram_bot_token` are already available (created in previous phases or locally). Phase 1 focuses on storing them in Parameter Store, not generating them.

- **Telegram Bot Exists**: A Telegram Bot token is already created via BotFather; developer has the chat ID for the recipient channel/group.

- **Cost Assumptions**: Monthly cost estimates ($15–35) are based on:
  - DynamoDB: On-demand pricing with < 1M reads/writes per month
  - S3: < 10 GB storage (lifecycle deletes after 7 days, so low average)
  - CloudFront: < 100 GB data transfer per month
  - Lambda: < 10K invocations per month at 128 MB memory
  - Parameter Store: Free tier (standard parameters, no advanced tier)

- **Scope Out of Phase 1**: Actual Lambda function implementations (ingestion, processing, posting, notifier) are out of scope. Phase 1 focuses on infrastructure and a placeholder Notifier Lambda for testing.

- **No Multi-Region**: All resources deployed to a single AWS region (us-east-1 recommended for cost optimization).

- **Error Handling**: Phase 1 focuses on happy-path deployments. Cleanup procedures (e.g., `cdk destroy`) will be documented but tested separately.

- **API Key Management**: API keys are manually stored in Parameter Store; no automated key generation or rotation Lambda in Phase 1. Rotation is manual developer process (update value in AWS console).

- **IAM Design Decision**: Single shared role approach (Option A clarification) balances MVP simplicity with security; per-function roles can be introduced post-Phase 1 as architecture scales and audit requirements increase.

- **DynamoDB Cost Control**: On-demand billing monitored via AWS Budget alerts (Option C clarification); no DynamoDB-level throughput caps or reserved capacity in Phase 1. Budget alerts serve as primary cost safeguard.

---

## Notes for Implementation

- **CDK Entry Point**: `app.py` in project root will instantiate and configure the `HealingBedroomStack`.
- **Environment Variables**: Terraform-like approach – use `.env.example` for developers to populate locally; CDK will read from `os.environ`.
- **Secrets Injection**: CDK will use AWS SecretsManager constructs; Lambda IAM role will grant read permissions but not manage policy inline (better for auditability).
- **Cost Alerts**: Set up SNS topic for Budget Alerts early; Notifier Lambda can be tested standalone before wiring to other phases.
- **Testing**: Phase 1 acceptance testing is manual (AWS console + boto3 CLI scripts); Phase 2+ will add unit/integration tests.
