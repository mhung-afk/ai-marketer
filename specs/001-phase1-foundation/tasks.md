---
description: "Task list for Phase 1 Foundation - AWS Infrastructure implementation"
---

# Tasks: Phase 1 Foundation – AWS Infrastructure

**Input**: Design documents from `/specs/001-phase1-foundation/`
**Prerequisites**: plan.md ✅, spec.md ✅, data-model.md ✅, contracts/ ✅
**Duration**: 3–5 days
**Team**: 1 solo developer
**Tests**: Manual acceptance testing (no automated tests in Phase 1; Phase 2+ will add pytest)

---

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Project Initialization)

**Purpose**: Repository structure, dependencies, and configuration framework

- [x] T001 Create repository folder structure per plan.md in `/home/mhung/workspace/AI-marketer/` (cdk/, src/lambdas/, src/common/, tests/, .github/, prompts/, scripts/)
- [x] T002 [P] Initialize Python virtual environment and create requirements.txt at `/home/mhung/workspace/AI-marketer/requirements.txt` with AWS CDK v2, boto3, pytest dependencies
- [x] T003 [P] Create `.env.example` template at `/home/mhung/workspace/AI-marketer/.env.example` with placeholder values for all Phase 1 parameters (AWS_REGION, BUDGET_LIMIT, TELEGRAM_BOT_TOKEN, etc.)
- [x] T004 [P] Configure Python linting and formatting (black, flake8) in `/.github/workflows/lint.yml`
- [x] T005 Create README.md at `/home/mhung/workspace/AI-marketer/README.md` with quickstart instructions from quickstart.md
- [x] T006 [P] Create .gitignore at `/home/mhung/workspace/AI-marketer/.gitignore` to exclude .env, __pycache__, .venv, cdk.context.json

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: CDK infrastructure base, IAM role, and common utilities that ALL user stories depend on

**⚠️ CRITICAL**: All Phase 3+ work cannot begin until this phase completes

- [x] T007 [P] Create CDK stack entry point at `/home/mhung/workspace/AI-marketer/app.py` with instantiation of HealingBedroomStack and CDK App initialization
- [x] T008 [P] Create CDK configuration file at `/home/mhung/workspace/AI-marketer/cdk.json` with context values (region: us-east-1, budget_limit: 40, environment_name: phase1)
- [x] T009 [P] Create CDK stack base class at `/home/mhung/workspace/AI-marketer/cdk/stack.py` with HealingBedroomStack construct and necessary imports
- [x] T010 [P] Create CDK config module at `/home/mhung/workspace/AI-marketer/cdk/config.py` with constants for resource names, AWS region, budget, and naming conventions
- [x] T011 Create IAM role `lambda-healing-bedroom-role` in CDK stack with least-privilege permissions in `/home/mhung/workspace/AI-marketer/cdk/stack.py`:
  - DynamoDB actions: GetItem, PutItem, UpdateItem, Query, Scan (scoped to table ARN)
  - S3 actions: GetObject, PutObject, ListBucket (scoped to bucket ARN + objects)
  - Parameter Store actions: GetParameter, GetParameters (scoped to `/healing-bedroom/*` path)
  - CloudWatch Logs actions: CreateLogGroup, CreateLogStream, PutLogEvents (scoped to `/aws/lambda/healing-bedroom-*`)
- [x] T012 [P] Create common utilities module at `/home/mhung/workspace/AI-marketer/src/common/utils.py` with:
  - `generate_item_id()` function for UUID v4 generation
  - `get_parameter()` function for Parameter Store retrieval
  - `get_parameters()` function for batch Parameter Store retrieval
  - ISO 8601 timestamp helpers
- [x] T013 [P] Create shared config module at `/home/mhung/workspace/AI-marketer/src/common/config.py` with:
  - Parameter Store path constants
  - Environment variable loading
  - CloudWatch log group name constants
- [x] T014 [P] Create CloudWatch Logs setup in CDK stack at `/home/mhung/workspace/AI-marketer/cdk/stack.py` with:
  - Log group `/aws/lambda/healing-bedroom-*` with 7-day retention
  - Log stream naming convention per Lambda function

**Checkpoint**: Foundation ready - user story implementation can begin in parallel

---

## Phase 3: User Story 1 – Deploy Base Infrastructure Programmatically (Priority: P1) 🎯 MVP

**Goal**: Deploy all core AWS resources (DynamoDB, S3, CloudFront, IAM, Parameter Store, CloudWatch Budget Alarms) as code using AWS CDK so infrastructure is reproducible, version-controlled, and deployable via single `cdk deploy` command

**Independent Test**: Deploy CDK stack to AWS account, verify all resources exist (tables, buckets, distributions, roles) with correct configurations, and confirm they're accessible via CDK output. Verify infrastructure costs < $5/day.

### Implementation for User Story 1

- [x] T015 [P] [US1] Create DynamoDB table in CDK stack at `/home/mhung/workspace/AI-marketer/cdk/stack.py`:
  - Table name: `HealingBedroomContent`
  - Partition key: `item_id` (String)
  - Billing mode: ON_DEMAND
  - Global Secondary Index `GSI1_Status`: partition key `status`, sort key `created_at`, projection ALL
  - TTL: disabled
  - Point-in-time recovery: disabled
  - Encryption: default AWS-managed keys

- [x] T016 [P] [US1] Create S3 bucket in CDK stack at `/home/mhung/workspace/AI-marketer/cdk/stack.py`:
  - Bucket naming: `healing-bedroom-images-${username}` (unique suffix)
  - Block all public access: enabled
  - Versioning: disabled
  - Lifecycle policy: delete objects after 7 days
  - Default encryption: enabled (SSE-S3)

- [x] T017 [P] [US1] Create CloudFront distribution in CDK stack at `/home/mhung/workspace/AI-marketer/cdk/stack.py`:
  - Origin: S3 bucket with Origin Access Control (OAC)
  - Default behavior: cache images 1 day, metadata 1 hour
  - Viewer protocol policy: redirect HTTP to HTTPS
  - Default root object: disabled (API-driven, not website)
  - Export CloudFront URL as stack output

- [x] T018 [P] [US1] Create S3 bucket policy in CDK stack allowing CloudFront OAC access in `/home/mhung/workspace/AI-marketer/cdk/stack.py`:
  - Restrict bucket access to CloudFront distribution only
  - Deny direct S3 public access

- [x] T019 [US1] Create DynamoDB table attributes in data schema at `/home/mhung/workspace/AI-marketer/src/common/schemas.py`:
  - Core attributes: item_id, status, created_at, niche, source_platform, source_url
  - Ingestion attributes: original_caption, original_image_url, scraped_at
  - Processing attributes: ai_caption, image_s3_key, image_cloudfront_url, processed_at
  - Approval attributes: approved_by, approved_at
  - Posting attributes: post_id, post_url, posted_at
  - Error attributes: error_log, retry_count
  - Status enum: RAW, PROCESSING, DRAFT, APPROVED, POSTED, FAILED

- [x] T020 [US1] Export CDK stack outputs in `/home/mhung/workspace/AI-marketer/cdk/stack.py`:
  - DynamoDB table name
  - S3 bucket name
  - CloudFront distribution domain name
  - Lambda IAM role ARN
  - CloudWatch log group name

- [x] T021 [US1] Create CDK assertion tests at `/home/mhung/workspace/AI-marketer/tests/unit/test_cdk_stack.py`:
  - Verify DynamoDB table exists with correct schema
  - Verify S3 bucket has lifecycle policy
  - Verify CloudFront distribution has correct origin
  - Verify IAM role has required permissions

- [x] T022 [US1] Document deployment process in README.md with step-by-step CDK deploy instructions

**Checkpoint**: User Story 1 complete – infrastructure deployable via `cdk deploy`

---

## Phase 4: User Story 2 – Store and Access Secrets Securely (Priority: P1)

**Goal**: Store all API keys (Anthropic, fal.ai, Telegram, Apify, Facebook) in AWS Systems Manager Parameter Store and ensure Lambda functions can retrieve them securely via IAM roles without hardcoding credentials

**Independent Test**: Deploy Parameter Store parameters, create test Lambda with IAM role, invoke Lambda to fetch parameters, verify correct values returned without errors

### Implementation for User Story 2

- [x] T023 [P] [US2] Create Parameter Store parameters in CDK stack at `/home/mhung/workspace/AI-marketer/cdk/stack.py`:
  - `/healing-bedroom/anthropic-api-key` (Phase 1)
  - `/healing-bedroom/fal-ai-key` (Phase 1)
  - `/healing-bedroom/telegram-bot-token` (Phase 1)
  - `/healing-bedroom/telegram-chat-id` (Phase 1)
  - `/healing-bedroom/apify-api-token` (Phase 2+ placeholder)
  - `/healing-bedroom/facebook-page-access-token` (Phase 5+ placeholder)
  - All as String type, standard tier, no encryption

- [x] T024 [US2] Create Parameter Store access utility at `/home/mhung/workspace/AI-marketer/src/common/param_store.py`:
  - Implement `get_parameter(name)` with error handling and retries
  - Implement `get_parameters(names)` for batch retrieval
  - Add CloudWatch logging for retrieval failures
  - Handle ParameterNotFound, AccessDeniedException, timeout exceptions

- [x] T025 [US2] Update IAM role policy in CDK stack `/home/mhung/workspace/AI-marketer/cdk/stack.py` to:
  - Grant `ssm:GetParameter` and `ssm:GetParameters` on path `/healing-bedroom/*`
  - Scope to Parameter Store actions only (no Secrets Manager)

- [x] T026 [P] [US2] Create test Lambda function at `/home/mhung/workspace/AI-marketer/src/lambdas/test-param-store/lambda_function.py`:
  - Retrieves a test parameter from Parameter Store
  - Returns parameter value for validation
  - Used for Phase 1 acceptance testing only

- [x] T027 [US2] Create Parameter Store documentation at `/home/mhung/workspace/AI-marketer/docs/parameter-store-guide.md`:
  - Naming convention and list of all parameters
  - Manual rotation process (update via AWS console)
  - Error handling patterns for Lambda functions
  - Reference to contract: contracts/parameter-store-interface.md

- [x] T028 [US2] Create Parameter Store verification script at `/home/mhung/workspace/AI-marketer/scripts/python/verify-param-store.py`:
  - Test connection to Parameter Store
  - Verify all Phase 1 parameters exist
  - Test retrieval of each parameter
  - Report any missing or inaccessible parameters

**Checkpoint**: User Story 2 complete – all API keys stored securely in Parameter Store

---

## Phase 5: User Story 3 – Monitor and Alert on Budget Overruns (Priority: P1)

**Goal**: Configure AWS Budget alerts to notify developer on Telegram when spending reaches 50% and 80% of monthly $40 budget so runaway costs are caught immediately

**Independent Test**: Set Budget to low test value ($5), trigger test alert, verify Telegram message received with correct cost data within 2 minutes

### Implementation for User Story 3

- [x] T029 [P] [US3] Create AWS Budget in CDK stack at `/home/mhung/workspace/AI-marketer/cdk/stack.py`:
  - Budget name: `HealingBedroom-Monthly-Budget`
  - Budget limit: $40/month
  - Budget type: COST
  - Time unit: MONTHLY

- [x] T030 [P] [US3] Create SNS topic for budget alerts in CDK stack at `/home/mhung/workspace/AI-marketer/cdk/stack.py`:
  - Topic name: `healing-bedroom-budget-alerts`
  - Enable delivery status logging to CloudWatch

- [x] T031 [P] [US3] Create budget alert thresholds in CDK stack at `/home/mhung/workspace/AI-marketer/cdk/stack.py`:
  - 50% threshold ($20): notification type ACTUAL
  - 80% threshold ($32): notification type ACTUAL
  - Both publish to SNS topic

- [x] T032 [US3] Create Lambda Notifier function at `/home/mhung/workspace/AI-marketer/src/lambdas/notifier/lambda_function.py`:
  - Triggered by SNS from Budget alerts
  - Parse SNS message for budget alert data
  - Retrieve Telegram Bot Token from Parameter Store
  - Format alert message with: current spend, budget limit, percentage, threshold, timestamp
  - Send formatted message to Telegram via Bot API
  - Log success/failure to CloudWatch

- [x] T033 [US3] Create Notifier Lambda execution role in CDK stack at `/home/mhung/workspace/AI-marketer/cdk/stack.py`:
  - Grant IAM permissions: Parameter Store read, CloudWatch Logs write
  - Use the shared `lambda-healing-bedroom-role` from Phase 2

- [x] T034 [P] [US3] Create Notifier Lambda testing utility at `/home/mhung/workspace/AI-marketer/scripts/python/test-telegram-alert.py`:
  - Simulate SNS budget alert message
  - Invoke Notifier Lambda locally or in AWS
  - Verify Telegram message delivery
  - Display received message for verification

- [x] T035 [US3] Create budget alert documentation at `/home/mhung/workspace/AI-marketer/docs/budget-alerts-guide.md`:
  - AWS Budget setup and thresholds
  - Telegram Bot integration steps
  - Message format reference
  - Troubleshooting guide for failed alerts
  - Reference to contract: contracts/budget-alert-telegram-pipeline.md

- [x] T036 [US3] Wire SNS topic to Lambda Notifier in CDK stack at `/home/mhung/workspace/AI-marketer/cdk/stack.py`:
  - Create SNS subscription: topic → Lambda Notifier
  - Grant Lambda permission to be invoked by SNS

**Checkpoint**: User Story 3 complete – budget alerts configured and tested on Telegram

---

## Phase 6: User Story 4 – Initialize GitHub Repository with Proper Structure (Priority: P2)

**Goal**: Ensure GitHub repository has well-organized folder structure and clear documentation so future code contributions and handoffs are straightforward

**Independent Test**: Clone repository, verify folder structure matches plan.md layout, follow README setup steps, and successfully run `cdk deploy` without errors

### Implementation for User Story 4

- [x] T037 [P] [US4] Create cdk/ subdirectory structure at `/home/mhung/workspace/AI-marketer/cdk/`:
  - stack.py (CDK stack definition)
  - config.py (configuration constants)
  - requirements.txt (CDK Python dependencies)

- [x] T038 [P] [US4] Create src/ subdirectory structure at `/home/mhung/workspace/AI-marketer/src/`:
  - lambdas/notifier/ (Phase 1 Notifier Lambda)
  - lambdas/ingestion/ (Phase 2+ placeholder)
  - lambdas/processor/ (Phase 3+ placeholder)
  - lambdas/poster/ (Phase 5+ placeholder)
  - common/ (shared utilities)
  - dashboard/ (Phase 4+ placeholder)

- [x] T039 [P] [US4] Create tests/ subdirectory structure at `/home/mhung/workspace/AI-marketer/tests/`:
  - unit/ (unit tests)
  - integration/ (integration tests)
  - fixtures/ (test data)

- [x] T040 [P] [US4] Create .github/ subdirectory structure at `/home/mhung/workspace/AI-marketer/.github/`:
  - workflows/ (GitHub Actions)
  - copilot-instructions.md (agent context)
  - prompts/ (PR templates, issue templates)

- [x] T041 [P] [US4] Create prompts/ subdirectory at `/home/mhung/workspace/AI-marketer/prompts/`:
  - caption-prompt.md (Claude prompt for Vietnamese captions)
  - image-prompt.md (fal.ai image generation prompt)

- [x] T042 [P] [US4] Create scripts/ subdirectory structure at `/home/mhung/workspace/AI-marketer/scripts/`:
  - bash/ (deployment, test, cleanup scripts)
  - python/ (data seeding, audit scripts)

- [x] T043 [US4] Create deployment guide at `/home/mhung/workspace/AI-marketer/docs/deployment-guide.md`:
  - Step-by-step instructions for `cdk deploy`
  - Expected outputs and verification steps
  - Troubleshooting common deployment issues
  - Post-deployment validation checklist

- [x] T044 [US4] Create architecture documentation at `/home/mhung/workspace/AI-marketer/docs/architecture.md`:
  - High-level overview of Phase 1 infrastructure
  - DynamoDB schema and access patterns
  - CloudFront caching strategy
  - Budget monitoring architecture
  - IAM role and permissions design

- [x] T045 [US4] Verify repository structure matches plan.md in `/home/mhung/workspace/AI-marketer/README.md` with visual folder tree

**Checkpoint**: User Story 4 complete – repository structure finalized and documented

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Final validation, documentation, testing, and cleanup

- [x] T046 [P] Manual acceptance testing checklist:
  - [x] CDK stack deploys without errors
  - [x] DynamoDB table created with correct schema
  - [x] S3 bucket created with correct policies
  - [x] CloudFront distribution serving images
  - [x] Parameter Store parameters accessible
  - [x] Lambda IAM role has correct permissions
  - [x] Budget alerts fire at thresholds
  - [x] Telegram Notifier receives alerts
  - [x] CloudWatch Logs capture Lambda executions
  - [x] Infrastructure cost < $5/day

- [x] T047 [P] Create cost audit script at `/home/mhung/workspace/AI-marketer/scripts/python/audit-costs.py`:
  - Query AWS Cost Explorer API
  - Report spending by service
  - Warn if spending exceeds $5/day threshold
  - Display cost breakdown for Phase 1 resources

- [x] T048 [P] Create cleanup script at `/home/mhung/workspace/AI-marketer/scripts/bash/cleanup.sh`:
  - `cdk destroy` with confirmation
  - Delete associated S3 buckets and DynamoDB tables
  - Document data loss warning

- [x] T049 [P] Create health check script at `/home/mhung/workspace/AI-marketer/scripts/python/health-check.py`:
  - Verify all Phase 1 AWS resources exist
  - Test DynamoDB connectivity
  - Test S3 bucket access
  - Test Parameter Store access
  - Report health status with recommendations

- [x] T050 Update .github/copilot-instructions.md with:
  - Link to plan.md and spec.md
  - Project structure overview
  - Key design decisions (CDK, on-demand billing, single IAM role)
  - Deployment quick reference

- [x] T051 Create CONTRIBUTING.md at `/home/mhung/workspace/AI-marketer/CONTRIBUTING.md` with:
  - Development environment setup
  - CDK local testing
  - Code style guidelines
  - PR review checklist for Phase 2+

- [x] T052 [P] Create test fixtures at `/home/mhung/workspace/AI-marketer/tests/fixtures/`:
  - Sample DynamoDB item JSON
  - Sample Parameter Store parameters
  - Sample Budget alert SNS message

- [x] T053 Generate final implementation report:
  - Total tasks completed (53)
  - Phase 1 deliverables checklist
  - Infrastructure deployment time
  - Monthly cost estimate
  - Phase 2 readiness assessment

**Checkpoint**: Phase 1 complete – infrastructure deployed, tested, and documented. Ready for Phase 2 ingestion layer.

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1: Setup (T001–T006)
    ↓
Phase 2: Foundational (T007–T014) ← BLOCKS all user stories
    ↓
Phase 3, 4, 5: User Stories 1, 2, 3 (T015–T036) ← Can run in parallel
    ↓
Phase 6: User Story 4 (T037–T045) ← Can start after Foundational or in parallel
    ↓
Phase 7: Polish (T046–T053)
```

### Parallel Opportunities

**Setup Phase (T001–T006)**: All [P] marked tasks can run in parallel
- T002, T003, T004, T006 are independent (different files)

**Foundational Phase (T007–T014)**: Tasks T007–T010, T012–T013 marked [P] can run in parallel
- T011 can start after T010 (depends on stack.py structure)
- T014 can run after T011

**User Story Phases (T015–T036)**: Can run in parallel if team has capacity
- US1 (DynamoDB, S3, CloudFront): T015–T022
- US2 (Parameter Store): T023–T028
- US3 (Budget Alerts): T029–T036
- All three stories independent; can be implemented by same developer sequentially or different developers in parallel

**Polish Phase (T046–T053)**: All [P] marked tasks can run in parallel
- T047, T048, T049 are independent testing/automation scripts

### Solo Developer Timeline

For a single developer working sequentially:

1. **Day 1 morning**: Phase 1 Setup (T001–T006) – ~1–2 hours
2. **Day 1 afternoon**: Phase 2 Foundational (T007–T014) – ~2–3 hours
3. **Day 2**: User Story 1 (T015–T022) – ~4–5 hours (includes CDK stack and DynamoDB testing)
4. **Day 2 afternoon**: User Story 2 (T023–T028) – ~2–3 hours
5. **Day 3 morning**: User Story 3 (T029–T036) – ~3–4 hours (includes Lambda Notifier + Telegram testing)
6. **Day 3 afternoon**: User Story 4 (T037–T045) – ~1–2 hours (mostly documentation)
7. **Day 4**: Polish & Testing (T046–T053) – ~2–3 hours (acceptance testing, scripts, cleanup)

**Total estimated time**: 16–22 hours over 3–5 days

### Parallel Example: User Stories in Parallel (if team available)

If two developers were available:

```
Day 1:
  Developer 1: Phase 1 Setup (T001–T006) + Phase 2 Foundational (T007–T014)
  
Day 2–3:
  Developer 1: User Story 1 (T015–T022) + Polish (T046–T053)
  Developer 2: User Story 2 (T023–T028) + User Story 3 (T029–T036)
  
Day 3–4:
  Either: User Story 4 (T037–T045) + final validation
```

With two developers, could compress to 2–3 days total.

---

## Success Criteria (Phase 1 Completion)

| Task | Success Indicator | Verification |
|------|------------------|--------------|
| T001–T006 | Repository structure created | `ls -la` shows expected directories |
| T007–T014 | CDK foundation ready | `cdk diff` shows resources to create |
| T015–T022 | Infrastructure deployable | `cdk deploy` succeeds, AWS resources visible in console |
| T023–T028 | Secrets accessible | Test Lambda retrieves parameter successfully |
| T029–T036 | Budget alerts working | Telegram message received within 2 minutes of alert |
| T037–T045 | Repository structure complete | README structure matches directory layout |
| T046–T053 | Phase 1 validated | All acceptance criteria met, cost < $5/day |

---

## Notes for Implementation

- **CDK Synthesize**: Run `cdk synth` before `cdk deploy` to validate CloudFormation template
- **Environment Setup**: Developer must have AWS CLI configured with valid credentials before `cdk deploy`
- **Parameter Store Initial Values**: Developer manually populates Parameter Store values via AWS console after initial `cdk deploy` (CDK cannot fetch secrets from outside AWS)
- **Telegram Bot Setup**: Developer must create Telegram Bot via BotFather and obtain Bot Token before deploying Notifier Lambda
- **Cost Alerts**: After deployment, set up AWS Budget in AWS console (CDK creates budget but alerts publish to SNS only after manual configuration)
- **Git Commits**: After each phase completes, run `git commit` to checkpoint progress (recommended: after T006, T014, T022, T028, T036, T045)
- **Cleanup on Failure**: If deployment fails, run `cdk destroy` to clean up partial resources before retrying
