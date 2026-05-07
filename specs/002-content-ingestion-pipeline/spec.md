# Feature Specification: Content Ingestion Pipeline

**Feature Branch**: `002-content-ingestion-pipeline`  
**Created**: May 6, 2026  
**Status**: Draft  
**Input**: Implement phase 2 – automated content ingestion with AI caption generation

## Overview

Phase 2 establishes an automated content ingestion pipeline that scrapes images and metadata from social media platforms (TikTok, Instagram, Facebook), processes them through AI to generate compelling Vietnamese captions aligned with the "Healing Bedroom" brand aesthetic, and stores results in DynamoDB for downstream approval and publishing workflows.

## Clarifications

### Session 2026-05-06

- Q: Should Phase 2 ingestion Lambda strictly follow Phase 1 patterns (shared config, utils, Layer)? → A: Yes – strictly follow Phase 1 patterns. Lambda ingestion handler MUST import from `src/common/` (config.py, utils.py) and use shared Lambda Layer, exactly as Phase 1 notifier does.
- Q: Which deduplication strategy for detecting duplicate content? → A: Content hash (image MD5/SHA256) + source_url comparison. Catches stolen/reposted images even from different URLs; store hash in DynamoDB GSI for fast lookup.
- Q: How should caption generation prompt be configured? → A: Hardcode prompt template in Lambda source code for Phase 2 MVP. Enables fastest development iteration. Plan to move to Parameter Store in Phase 3 if brand tone changes become frequent.
- Q: How should EventBridge scheduling be configured? → A: Use AWS EventBridge Scheduler with cron expression stored in `config.py` (e.g., `INGESTION_SCHEDULE_CRON = "0 */6 * * ? *"`). CDK creates rule dynamically. Allows easy reschedule by config change without code redeploy.
- Q: Should items be batch-processed or individually processed? → A: Process items individually with error isolation. Failed item goes to dead-letter queue; successful items commit. Enables per-item retry and prevents cascading failures.

## User Scenarios & Testing

### User Story 1 – Scrape Social Media Content (Priority: P1)

An automated Lambda function runs on a scheduled interval to discover and collect images from TikTok, Instagram, and Facebook using relevant hashtags (e.g., `#healingbedroom`, `#bedroomdecor`, `#asmr`). The function retrieves image URLs, original captions, and platform-specific metadata without any manual intervention.

**Why this priority**: Core requirement; without content acquisition, the entire pipeline fails. This is the entry point for all content flowing through the system.

**Independent Test**: Can be fully tested by triggering the Lambda manually with a test hashtag list and verifying DynamoDB contains new entries with `source_url` and `source_platform` fields populated, and images accessible via CloudFront URLs.

**Acceptance Scenarios**:

1. **Given** Apify Actor API is configured with valid credentials in Parameter Store, **When** Lambda ingestion trigger fires, **Then** system retrieves ≥ 10 items per execution from at least 2 social platforms
2. **Given** items already exist in DynamoDB, **When** Lambda runs again, **Then** system detects and skips duplicates based on `source_url` hash
3. **Given** Apify API rate limit is exceeded, **When** Lambda processes next batch, **Then** system retries with exponential backoff and logs error to CloudWatch

---

### User Story 2 – Generate AI Captions in Vietnamese (Priority: P1)

For each scraped image, the system calls Anthropic Claude to transform the original (often English or platform-specific) caption into a natural, brand-aligned Vietnamese caption with appropriate hashtags. The AI respects the "Healing Bedroom" tone: calming, aesthetic, aspirational, wellness-focused.

**Why this priority**: Core value delivery; brand differentiation depends on high-quality Vietnamese captions optimized for engagement and platform algorithms.

**Independent Test**: Can be fully tested by processing 10 sample images through Claude, reviewing the output captions for linguistic quality and brand alignment, and verifying all captions populate the `ai_caption_vi` field in DynamoDB.

**Acceptance Scenarios**:

1. **Given** a raw content item with `original_caption`, **When** Claude processes it, **Then** `ai_caption` field contains natural Vietnamese text with embedded hashtags
2. **Given** Claude API fails (rate limit, timeout), **When** Lambda receives error, **Then** system retries with exponential backoff up to 3 times before moving item to dead-letter state
3. **Given** multiple tone preferences exist (e.g., chill vs. motivational), **When** Lambda processes caption, **Then** AI applies consistent tone matching stored preference in `metadata`

---

### User Story 3 – Store Enriched Content (Priority: P1)

Processed content (images, captions, metadata) is stored in DynamoDB with all required fields populated and CloudFront URLs generated for public image access. This allows downstream workflows (approval, publishing) to reference and retrieve content.

**Why this priority**: Data persistence is prerequisite for all downstream phases; without reliable storage, approval and publishing workflows cannot function.

**Independent Test**: Can be fully tested by querying DynamoDB for items with `status = RAW`, verifying all required fields are populated (source_url, s3_image_key, cloudfront_url, ai_caption_vi), and confirming CloudFront URLs return valid image content.

**Acceptance Scenarios**:

1. **Given** a processed item, **When** Lambda commits to DynamoDB, **Then** all fields are populated: `source_platform`, `source_url`, `original_caption`, `ai_caption`, `s3_image_key`, `cloudfront_url`, `processed_at`, `status = RAW`
2. **Given** storage succeeds, **When** querying DynamoDB, **Then** item is immediately queryable by `source_platform` and `processed_at` (via GSI if applicable)
3. **Given** CloudFront URL is generated, **When** accessing URL in browser, **Then** image loads successfully with correct content type

---

### User Story 4 – Monitor Pipeline Health (Priority: P2)

Operations staff receives real-time notifications when ingestion or caption generation fails, including error details and suggested remediation steps. Metrics on items processed, success/failure rates are logged to CloudWatch.

**Why this priority**: Operational visibility; enables rapid response to pipeline issues before they impact content availability or brand reputation.

**Independent Test**: Can be tested by simulating API failures (invalid Apify token, Claude rate limit) and verifying Telegram alerts are delivered within 5 minutes with specific error details.

**Acceptance Scenarios**:

1. **Given** Apify API returns 403 (auth error), **When** Lambda catches exception, **Then** Telegram notification is sent to ops channel with error code and recovery hint
2. **Given** Lambda completes execution, **When** metrics are logged, **Then** CloudWatch shows count of `processed_items`, `successful_captions`, `failed_captions`, `duplicate_skipped` for the period
3. **Given** dead-letter storage reaches threshold, **When** Lambda completes, **Then** metric alarms trigger and escalate to on-call engineer

---

### User Story 5 – Extend Content Sources (Priority: P3)

System architecture is designed to support adding new social media platforms or scraping strategies with minimal code changes. New platforms can be registered in configuration and integrated into the pipeline without modifying core Lambda logic.

**Why this priority**: Future extensibility; allows team to expand to YouTube, Threads, or other platforms as strategy evolves without rearchitecting.

**Independent Test**: Can be tested by adding a new mock source in configuration and verifying Lambda processes it without requiring core logic changes.

**Acceptance Scenarios**:

1. **Given** a new Apify Actor for platform X is registered, **When** configuration is updated and Lambda redeploys, **Then** system scrapes from platform X without code changes to handler
2. **Given** existing Lambda processes TikTok, Instagram, Facebook, **When** YouTube scraper is added, **Then** all platforms continue working with no disruption

---

### Edge Cases

- What happens when Apify returns 0 items (no content matching hashtags found)?
- How does system handle duplicate detection when image hash is identical but source_url differs?
- What happens when Claude timeout exceeds 30 seconds – does Lambda retry or move to dead letter?
- How does system behave if S3 upload fails (bucket full, permissions)? Do we retry or skip image storage?
- What if Parameter Store secret expires or is rotated mid-execution?
- How does system handle corrupted or invalid image files from source platforms?

## Requirements

### Functional Requirements

- **FR-001**: System MUST scrape social media platforms (TikTok, Instagram, Facebook) using Apify Actors on a schedule configured via AWS EventBridge Scheduler with cron expression in `config.py` (default 6–12 hour intervals)
- **FR-002**: System MUST retrieve image URLs, original captions, and platform metadata from each source
- **FR-003**: System MUST detect and skip duplicate content using MD5/SHA256 hash of downloaded image plus `source_url` comparison; store content hash in DynamoDB GSI for O(1) lookup performance
- **FR-004**: System MUST upload images to S3 with lifecycle policy for automatic cleanup (7 days)
- **FR-005**: System MUST generate public CloudFront URLs for all uploaded images
- **FR-006**: System MUST call Anthropic Claude with hardcoded prompt template to rewrite original captions into natural Vietnamese matching "Healing Bedroom" brand tone (calming, aesthetic, aspirational, wellness-focused)
- **FR-007**: System MUST include relevant hashtags in AI-generated captions (auto-generated or per stored preference)
- **FR-008**: System MUST store enriched content in DynamoDB with status `RAW` and all fields populated
- **FR-009**: System MUST implement retry logic with exponential backoff for Apify and Claude API failures; items with persistent failures are moved out DynamoDB table
- **FR-010**: System MUST process items individually to enable error isolation; failed item does not block processing of subsequent items
- **FR-011**: System MUST retrieve API secrets (Apify token, Claude API key, Telegram token) from AWS Parameter Store at runtime
- **FR-012**: System MUST log all operations (success/failure/retry count) to CloudWatch Logs
- **FR-013**: System MUST send Telegram alerts when pipeline encounters critical errors (auth failure, rate limit, service unavailable)
- **FR-014**: System MUST be deployable via AWS CDK without manual steps
- **FR-015**: System MUST reuse shared IAM role and Lambda Layer from Phase 1

### Key Entities

- **ContentItem**: Represents a processed piece of content with fields: `id` (PK), `source_platform` (TikTok/Instagram/Facebook), `source_url`, `original_caption`, `ai_caption`, `s3_image_key`, `cloudfront_url`, `status` (RAW/APPROVED/PUBLISHED), `processed_at`, `metadata` (JSON for tone, source profile, engagement metrics)
- **IngestionRun**: Represents a single execution of the pipeline with fields: `run_id` (PK), `start_time`, `end_time`, `platform`, `items_scraped`, `items_deduplicated`, `items_processed`, `items_failed`, `errors` (list)

## Success Criteria

### Measurable Outcomes

- **SC-001**: Pipeline ingests ≥ 10–20 items per day from combined sources (TikTok, Instagram, Facebook)
- **SC-002**: ≥ 95% of scraped items successfully generate Vietnamese captions without errors
- **SC-003**: Duplicate detection accuracy ≥ 99% (no more than 1 duplicate per 100 items processed)
- **SC-004**: ≥ 70% of AI-generated captions receive positive subjective brand-alignment rating in manual QA review (10-item sample)
- **SC-005**: All images are publicly accessible via CloudFront within 10 seconds of processing
- **SC-006**: Pipeline recovers from transient API failures (rate limits, timeouts) with ≤ 2 automatic retries before alerting ops
- **SC-007**: Cost of Phase 2 operations (Apify + Claude + Lambda + storage) stays within $8–15/month budget
- **SC-008**: CDK deployment completes without errors; infrastructure is reproducible across environments
- **SC-009**: Ops team receives error alerts within 5 minutes of failure via Telegram

## Assumptions

- Phase 1 infrastructure (DynamoDB, S3, CloudFront, Parameter Store, IAM Role, Lambda Layer) is deployed and functional
- Apify API tokens for TikTok, Instagram, Facebook scrapers are available and not rate-limited
- Anthropic Claude API is accessible with sufficient quota for ≥ 100 requests per day
- AWS region is `ap-southeast-1` (consistent with Phase 1)
- Telegram Bot token and chat ID are configured in Parameter Store for alert delivery
- Social media platforms' Terms of Service permit automated scraping via Apify (existing legal review assumed)
- Network connectivity and API availability are 99%+ (transient failures are acceptable and handled by retry logic)
- Initial hashtag/keyword targets are known; no dynamic user-driven search required
- Images from source platforms do not require rights verification in Phase 2 (curation approval happens downstream)
