---
description: "Task list for Phase 2 Content Ingestion Pipeline implementation"
---

# Tasks: Content Ingestion Pipeline (Phase 2)

**Input**: Design documents from `/specs/002-content-ingestion-pipeline/`  
**Prerequisites**: Phase 1 foundation complete; all AWS resources deployed  
**Status**: Ready for implementation  
**Estimated Effort**: 2–3 weeks (US1+US2+US3+US4)

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4, US5)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and dependencies

- [x] T001 Create directory structure per implementation plan: `src/lambdas/ingestion/`, `tests/unit/`, `tests/integration/`, `scripts/python/`
- [x] T002 [P] Update `requirements.txt` with anthropic==0.28.0 and apify-client SDK dependencies
- [x] T003 [P] Configure black, flake8, mypy for Python code formatting and linting

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST complete before ANY user story implementation

**⚠️ CRITICAL**: No user story work begins until this phase completes

### 2.1 DynamoDB Schema Extension

- [x] T004 Extend Phase 1 `HealingBedroomContent` DynamoDB table: add `content_hash`, `ai_caption_vi`, `s3_image_key`, `cloudfront_url`, `retry_count`, `error_reason` attributes in `cdk/stack.py`
- [x] T005 Create Global Secondary Index (GSI) on `content_hash` + `created_at` in `cdk/stack.py` for O(1) deduplication lookups per [data-model.md](data-model.md#global-secondary-index-gsi_contenthash)

### 2.2 Pydantic Schemas & Common Layer

- [x] T006 [P] Create Pydantic schemas in `src/common/schemas.py`: `SourcePlatform` enum, `ContentStatus` enum, `CaptureTone` enum, `ContentItem` model, `IngestionRun` model per [data-model.md](data-model.md#pydantic-models-python-type-safety)
- [x] T007 [P] Update Lambda Layer `cdk/stack.py` to include `src/common/schemas.py` in `python/common/` folder; ensure Pydantic is available in Lambda runtime
- [x] T008 [P] Add utility functions to `src/common/utils.py`: `send_ingestion_alert()` for Telegram error alerts; `get_dynamodb_gsi_by_hash()` for deduplication lookup; `generate_cloudfront_url()` for image URL generation

### 2.3 Configuration & Environment

- [x] T009 [P] Update `src/common/config.py` with new constants: `INGESTION_SCHEDULE_CRON` (default `"0 */6 * * ? *"`), `SOURCES_CONFIG` dict with TikTok/Instagram/Facebook Apify actor IDs and hashtags per [research.md](research.md#1-apify-actor-selection-for-social-media-scraping)
- [x] T010 [P] Add new Parameter Store key retrieval in `src/common/config.py`: `PARAM_APIFY_API_TOKEN`, `PARAM_ANTHROPIC_API_KEY`, `PARAM_INGESTION_ALERTS_TELEGRAM_CHAT_ID` (reuse Phase 1 Telegram bot token); validate at Lambda startup
- [x] T011 [P] Create `.env.example` with Phase 2 placeholders: `APIFY_API_TOKEN`, `ANTHROPIC_API_KEY`, `INGESTION_SCHEDULE_CRON`

### 2.4 SQS Dead-Letter Queue

- [x] T012 Create SQS dead-letter queue in `cdk/stack.py`: `healing-bedroom-ingestion-dlq` with 7-day retention, 5-minute visibility timeout per [research.md](research.md#4-dead-letter-queue-sqs-vs-dynamodb)

### 2.5 EventBridge Scheduler

- [x] T013 Create EventBridge Scheduler rule in `cdk/stack.py`: schedule Lambda ingestion handler with cron expression from `config.INGESTION_SCHEDULE_CRON`; attach Lambda execution role with sufficient permissions per [research.md](research.md#3-eventbridge-scheduler-configuration)

### 2.6 IAM & Permissions

- [x] T014 Extend Phase 1 Lambda IAM role in `cdk/stack.py` with permissions: SQS SendMessage (for dead-letter queue), SNS Publish (for Telegram alerts), EventBridge Scheduler invoke Lambda
- [x] T015 Verify S3 bucket policy allows Lambda role to GetObject (image URLs from source) and PutObject (to `raw/` folder)

### 2.7 Error Handling Infrastructure

- [x] T016 Create `src/common/error_handlers.py` with custom exceptions: `ApifyError`, `ClaudeError`, `ImageProcessingError`, `DeduplicationError`, `S3UploadError` and shared retry logic with exponential backoff (max 3 retries)

**Checkpoint**: Foundation complete. All user story implementation can now begin in parallel.

---

## Phase 3: User Story 1 – Scrape Social Media Content (Priority: P1) 🎯 MVP

**Goal**: Automated Lambda function discovers and collects images from TikTok, Instagram, and Facebook without manual intervention

**Independent Test**: Trigger Lambda manually with test hashtags; verify DynamoDB contains new entries with `source_url`, `source_platform` fields populated; images accessible via CloudFront URLs

### 3.1 Apify Client Implementation

- [x] T017 [P] [US1] Create `src/lambdas/ingestion/apify_client.py`: implement `ApifyClient` class with methods: `__init__(api_token)`, `start_actor_run(actor_id, input_params)`, `get_run_status(run_id)`, `retrieve_results(run_id, limit=100)` per [contracts/apify-scraper-contract.md](contracts/apify-scraper-contract.md)
- [x] T018 [P] [US1] Add error handling to ApifyClient: catch HTTP 403 (auth error), 429 (rate limit), 503 (service unavailable); raise `ApifyError` with descriptive message for Lambda error handler to catch
- [x] T019 [P] [US1] Implement config-driven actor orchestration: loop through `SOURCES_CONFIG` dict and trigger Apify actor runs for TikTok, Instagram, Facebook sequentially per [research.md](research.md#1-apify-actor-selection-for-social-media-scraping)

### 3.2 Deduplication Logic

- [x] T020 [US1] Create `src/lambdas/ingestion/deduplication.py`: implement `check_duplicate_by_hash(content_hash)` function that queries DynamoDB GSI `GSI_ContentHash`; return `(is_duplicate, existing_item_id)` per [data-model.md](data-model.md#global-secondary-index-gsi_contenthash)
- [x] T021 [US1] Add `check_duplicate_by_url(source_url)` function to handle edge case where image URL matches existing entry (same source reposted); return dedup result

### 3.3 Unit Tests for US1

- [x] T022 [P] [US1] Contract test in `tests/unit/test_apify_client.py`: mock Apify API responses; verify `start_actor_run()` constructs correct request payload for TikTok, Instagram, Facebook per contracts
- [x] T023 [P] [US1] Unit test in `tests/unit/test_apify_client.py`: verify error handling for HTTP 403, 429, 503; confirm `ApifyError` is raised
- [x] T024 [P] [US1] Unit test in `tests/unit/test_deduplication.py`: mock DynamoDB GSI query; verify `check_duplicate_by_hash()` returns True for existing hash, False for new hash (moto for DynamoDB mocking)
- [x] T025 [US1] Integration test in `tests/integration/test_ingestion_pipeline_e2e.py`: Scrape flow – verify DynamoDB has new items with `source_platform`, `source_url`, `original_caption` populated after Lambda execution

**Checkpoint**: User Story 1 complete. Social media scraping functional and tested.

---

## Phase 4: User Story 2 – Generate AI Captions in Vietnamese (Priority: P1)

**Goal**: For each scraped image, call Anthropic Claude to transform original caption into brand-aligned Vietnamese caption with hashtags

**Independent Test**: Process 10 sample images through Claude; review output captions for linguistic quality and brand alignment; verify all captions populate `ai_caption_vi` field in DynamoDB

### 4.1 Claude Caption Generator

- [x] T026 [P] [US2] Create `src/lambdas/ingestion/claude_caption_generator.py`: implement `ClaudeClient` class with `generate_caption(original_caption, source_platform, tone='aesthetic')` method that calls Claude API per [contracts/claude-caption-contract.md](contracts/claude-caption-contract.md)
- [x] T027 [P] [US2] Hardcode system prompt in `ClaudeClient.__init__()`: define "Healing Bedroom" brand tone (calming, aspirational, wellness-focused, no hard selling); include instruction to respond ONLY with Vietnamese caption + hashtags
- [x] T028 [P] [US2] Implement token budget enforcement: `max_tokens=300` per Claude request; verify response parsing extracts Vietnamese caption + hashtags correctly
- [x] T029 [US2] Add timeout handling: if Claude API call exceeds 30 seconds, raise `ClaudeError("timeout")` for retry logic to catch

### 4.2 Error Handling for Claude

- [x] T030 [US2] Implement exponential backoff retry logic in Claude client: max 3 retries with 2^n second delays (1s, 2s, 4s); log retry attempts to CloudWatch per [plan.md](plan.md#risks--mitigations)
- [x] T031 [US2] Handle Claude auth errors (invalid API key): catch HTTP 401, raise `ClaudeError("auth_failed")` for Telegram alert

### 4.3 Unit Tests for US2

- [x] T032 [P] [US2] Contract test in `tests/unit/test_claude_caption_generator.py`: mock Claude API responses; verify request payload includes correct system prompt and message format per contracts
- [x] T033 [P] [US2] Unit test in `tests/unit/test_claude_caption_generator.py`: verify `generate_caption()` correctly parses response and extracts Vietnamese text + hashtags
- [x] T034 [P] [US2] Unit test in `tests/unit/test_claude_caption_generator.py`: test timeout handling; confirm exponential backoff logic and max 3 retries
- [x] T035 [US2] Integration test in `tests/integration/test_ingestion_pipeline_e2e.py`: Caption generation flow – verify DynamoDB items updated with `ai_caption_vi` field populated after Claude processing

**Checkpoint**: User Story 2 complete. AI caption generation functional and tested.

---

## Phase 5: User Story 3 – Store Enriched Content (Priority: P1)

**Goal**: Processed content (images, captions, metadata) stored in DynamoDB with CloudFront URLs for public access

**Independent Test**: Query DynamoDB for items with `status = RAW`; verify all required fields populated; confirm CloudFront URLs return valid image content

### 5.1 Image Processing

- [x] T036 [P] [US3] Create `src/lambdas/ingestion/image_processor.py`: implement `ImageProcessor` class with `download_image(image_url)` method; handle timeouts and HTTP errors; return `(image_bytes, extension)` per [contracts/s3-cloudfront-contract.md](contracts/s3-cloudfront-contract.md)
- [x] T037 [P] [US3] Implement `compute_content_hash(image_bytes) -> str` function using hashlib.md5(); store hash for deduplication
- [x] T038 [P] [US3] Implement `upload_to_s3(image_bytes, extension) -> str` function: generate object key format `raw/YYYY-MM-DD/HH-MM-SS-{uuid}.{ext}`; upload to S3; return `s3_image_key`
- [x] T039 [P] [US3] Generate CloudFront URL in `upload_to_s3()`: retrieve CloudFront domain from Phase 1 stack output; construct public URL in format `https://d{distribution-id}.cloudfront.net/{s3_image_key}`

### 5.2 DynamoDB Storage

- [x] T040 [US3] Create `src/lambdas/ingestion/dynamodb_storage.py`: implement `save_content_item(content_item: ContentItem)` function that writes to DynamoDB table; set `status = RAW`, `processed_at = now`, `created_at = now`
- [x] T041 [US3] Implement update logic: `update_content_item_with_caption(item_id, ai_caption_vi, ai_caption_tone)` and `update_content_item_with_error(item_id, error_reason, retry_count)` functions

### 5.3 Main Lambda Handler

- [x] T042 [US3] Create `src/lambdas/ingestion/lambda_function.py`: implement main Lambda handler that orchestrates entire pipeline: scrape → dedup → download image → generate caption → upload to S3 → store in DynamoDB; handle errors at each step
- [x] T043 [US3] Implement individual item processing: loop through Apify results; for each item, attempt scrape → caption → storage; if error, move to SQS dead-letter queue; continue processing remaining items (no cascade failures)
- [x] T044 [US3] Add logging to Lambda handler: log `items_scraped`, `items_deduplicated`, `items_processed`, `items_failed` to CloudWatch per [plan.md](plan.md#key-design-decisions)

### 5.4 Unit Tests for US3

- [x] T045 [P] [US3] Unit test in `tests/unit/test_image_processor.py`: mock image download; verify `download_image()` returns correct bytes and extension
- [x] T046 [P] [US3] Unit test in `tests/unit/test_image_processor.py`: verify `compute_content_hash()` produces consistent MD5 hashes
- [x] T047 [P] [US3] Unit test in `tests/unit/test_image_processor.py`: mock S3 upload; verify `upload_to_s3()` returns correct CloudFront URL format
- [x] T048 [P] [US3] Unit test in `tests/unit/test_dynamodb_storage.py`: mock DynamoDB put_item; verify `save_content_item()` writes all required fields

### 5.5 Integration Tests for US3

- [x] T049 [US3] Integration test in `tests/integration/test_ingestion_pipeline_e2e.py`: End-to-end flow – trigger Lambda; verify DynamoDB contains complete ContentItem records with all fields (`source_platform`, `source_url`, `original_caption`, `ai_caption_vi`, `s3_image_key`, `cloudfront_url`, `status = RAW`); confirm CloudFront URL returns valid image

**Checkpoint**: User Story 3 complete. Content storage and CDN access functional and tested.

---

## Phase 6: User Story 4 – Monitor Pipeline Health (Priority: P2)

**Goal**: Operations staff receive real-time notifications when pipeline fails; metrics logged to CloudWatch

**Independent Test**: Simulate API failures (invalid Apify token, Claude rate limit); verify Telegram alerts delivered within 5 minutes with specific error details

### 6.1 Error Handling & Alerts

- [x] T050 [US4] Create `src/lambdas/ingestion/error_handlers.py`: implement `handle_pipeline_error(error_type, error_message, retry_count)` function that publishes to SNS topic for Telegram delivery per [research.md](research.md#7-telegram-alert-efficiency)
- [x] T051 [US4] Add Telegram alert helper to `src/common/utils.py`: `send_ingestion_alert(error_type, error_message, retry_count)` that constructs alert message with error details and recovery hints
- [x] T052 [US4] Implement dead-letter queue error handling: when max retries exhausted, serialize failed item to SQS `healing-bedroom-ingestion-dlq` with metadata: `error_code`, `last_error_message`, `retry_count`, `moved_to_dlq_at` per [data-model.md](data-model.md#sqs-dead-letter-queue-schema)

### 6.2 CloudWatch Metrics

- [x] T053 [US4] Add CloudWatch custom metrics to Lambda handler: `processed_items`, `successful_captions`, `failed_captions`, `duplicate_skipped`, `errors_total` per execution; emit via `cloudwatch.put_metric_data()`
- [x] T054 [US4] Create CloudWatch dashboard in `cdk/stack.py`: widgets showing items processed/failed, caption success rate, error frequency; set alarm thresholds for dead-letter queue size

### 6.3 Logging & Observability

- [x] T055 [US4] Implement structured logging in Lambda handler: use JSON format for all logs; include `request_id`, `platform`, `item_count`, `execution_time_ms` for easier analysis in CloudWatch Insights
- [x] T056 [US4] Add error context logging: when error occurs, log full traceback, API response body, and suggested remediation steps (e.g., "Check Apify token in Parameter Store")

### 6.4 Unit Tests for US4

- [x] T057 [P] [US4] Unit test in `tests/unit/test_error_handlers.py`: mock SNS publish; verify Telegram alert message includes error type, message, retry count
- [x] T058 [P] [US4] Unit test in `tests/unit/test_error_handlers.py`: mock SQS send_message; verify dead-letter queue message structure matches schema
- [x] T059 [US4] Unit test in `tests/unit/test_lambda_ingestion.py`: verify CloudWatch metrics emitted for `processed_items`, `successful_captions`, `failed_captions`

**Checkpoint**: User Story 4 complete. Pipeline monitoring and alerting functional.

---

## Phase 7: User Story 5 – Extend Content Sources (Priority: P3)

**Goal**: System architecture supports adding new social media platforms with minimal code changes

**Independent Test**: Add new mock source in `SOURCES_CONFIG`; verify Lambda processes it without core logic changes

### 7.1 Extensibility Design

- [x] T060 [US5] Refactor Apify orchestration in `src/lambdas/ingestion/apify_client.py`: implement generic `start_actor_run_for_source(source_config)` method that accepts arbitrary actor ID and input params; remove platform-specific logic from main handler
- [x] T061 [US5] Create plugin-style registration in `src/common/config.py`: `SOURCES_CONFIG` dict can be extended by adding new source entries without modifying core Lambda code; each source includes `actor_id`, `options`, `hashtags`
- [x] T062 [US5] Document extensibility pattern in `README.md` Phase 2 section: step-by-step guide for adding YouTube, Threads, or other platforms

### 7.2 Future Capabilities

- [x] T063 [US5] Design (document only, no code) support for platform-specific metadata extraction (e.g., TikTok engagement metrics, Instagram Reels duration); proposal for Phase 3+ — See [future-capabilities-design.md](future-capabilities-design.md#1-platform-specific-metadata-extraction-t063)
- [x] T064 [US5] Design (document only) support for dynamic prompt variations per platform (e.g., TikTok tone vs. Facebook tone); proposal for Phase 3+ — See [future-capabilities-design.md](future-capabilities-design.md#2-dynamic-prompt-variations-per-platform-t064)

**Checkpoint**: User Story 5 complete. Architecture supports future platform expansion.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Final integration, documentation, and production readiness

### 8.1 Manual Testing & Verification

- [x] T065 [P] Create manual test script in `scripts/python/test-ingestion-pipeline.py`: trigger Lambda directly with test hashtags, verify DynamoDB entries created, CloudFront URLs accessible, check CloudWatch logs for errors
- [x] T066 [P] Create health check script in `scripts/python/health-check-ingestion.py`: verify all Phase 2 resources exist (Lambda, EventBridge, SQS, DynamoDB GSI); check Parameter Store credentials; test Apify/Claude connectivity

### 8.2 Code Quality

- [ ] T071 [P] Run black formatter on all Phase 2 code: `black src/lambdas/ingestion/ src/common/ cdk/`
- [ ] T072 [P] Run flake8 linter: `flake8 src/lambdas/ingestion/ src/common/ cdk/`
- [ ] T073 [P] Run mypy type checker: `mypy src/lambdas/ingestion/ src/common/` (ensure all imports typed)
- [ ] T074 Generate code coverage report: `pytest tests/ --cov=src/lambdas/ingestion --cov-report=html`; target ≥80% coverage on critical paths (dedup, image processing, error handling)

### 8.3 CDK Deployment

- [ ] T075 Validate CDK synthesis: `cdk synth` generates valid CloudFormation template
- [ ] T076 [P] Run CDK diff: `cdk diff` vs. Phase 1 stack; verify only Phase 2 resources added (EventBridge, Lambda, SQS, DynamoDB GSI updates)
- [ ] T077 Deploy Phase 2 via CDK: `cdk deploy --require-approval never`; verify all resources created successfully

**Checkpoint**: Phase 2 production-ready. All integration tests pass; documentation complete; costs validated.

---

## Dependencies & Execution Order

### Critical Path (Blocking Dependencies)

```
Phase 1: Setup (T001-T003)
    ↓
Phase 2: Foundational (T004-T016)
    ↓
├─→ Phase 3: US1 Scrape (T017-T025) [US1] — Can run in parallel
├─→ Phase 4: US2 Captions (T026-T035) [US2] — Can run in parallel
├─→ Phase 5: US3 Storage (T036-T049) [US3] — Can run in parallel
├─→ Phase 6: US4 Monitoring (T050-T059) [US4] — Can run in parallel
└─→ Phase 7: US5 Extensibility (T060-T064) [US5] — Can run in parallel
    ↓
Phase 8: Polish (T065-T084)
```

### Parallel Execution Example

After Phase 2 completion, teams can work in parallel:

- **Team A** implements US1 (Apify scraping) — T017-T025
- **Team B** implements US2 (Claude captions) — T026-T035
- **Team C** implements US3 (DynamoDB + S3 storage) — T036-T049
- **Team D** implements US4 (monitoring) — T050-T059
- **Team E** designs US5 extensibility — T060-T064

All teams converge at Phase 8 for integration testing and production readiness.

---

## MVP Scope (Minimum Viable Product)

**Recommended Release 1**: US1 + US2 + US3 (Phases 3-5)

- Complete content ingestion pipeline from social media → Vietnamese captions → DynamoDB storage
- Independent verification via manual test script
- Estimated effort: 1.5–2 weeks
- Enables Phase 3 approval dashboard to function

**Optional for Release 1**: US4 (Phase 6)

- Add production monitoring and alerting
- Recommended: Include for ops visibility from day 1

**Defer to Release 2**: US5 (Phase 7)

- Platform extensibility is nice-to-have; full scraping from 3 platforms sufficient for MVP

---

## Success Criteria Verification

| Success Criterion | Verification Method | Task(s) |
|-------------------|---------------------|---------|
| SC-001: ≥10–20 items/day ingested | Manual test: trigger Lambda, check DynamoDB item count | T065 |
| SC-002: ≥95% caption success rate | Integration test: process 100 items, count successes | T049 |
| SC-003: ≥99% duplicate detection | Unit test: verify GSI query logic; manual spot-check | T024 |
| SC-004: ≥70% brand-aligned captions | Manual QA review: 10-item sample scored by brand team | Documentation |
| SC-005: CloudFront URLs load <10s | Integration test: measure CDN access time | T049 |
| SC-006: ≤2 auto-retries before alerting | Unit test: verify exponential backoff logic | T034 |
| SC-007: $8–15/month budget | Cost calculator: Apify + Claude + Lambda + storage | T078 |
| SC-008: CDK deployment no errors | Terminal: `cdk deploy` succeeds | T077 |
| SC-009: Alerts <5min to Telegram | Integration test: simulate error, measure time to alert | T081 |

---

## Post-Phase-2 Roadmap

**Phase 3**: Approval Dashboard  
- Streamlit UI for human approval/rejection
- Integration with DynamoDB `RAW` status query
- Batch approve/reject operations

**Phase 4**: Social Media Publishing  
- Post approved content to Telegram, Facebook, Instagram via platform APIs
- Engagement tracking (likes, comments, shares)

**Phase 5**: Advanced Analytics  
- Dashboard showing engagement metrics by source platform, tone, time of day
- A/B testing framework for caption variations
