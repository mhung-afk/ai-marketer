# Implementation Plan: Content Ingestion Pipeline

**Branch**: `002-content-ingestion-pipeline` | **Date**: 2026-05-06 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification - Phase 2 automated content ingestion with AI caption generation for Vietnamese captions

## Summary

Phase 2 establishes an automated Lambda-based pipeline that scrapes images and metadata from TikTok, Instagram, and Facebook using Apify Actors on a configurable 6–12 hour schedule, processes them through Anthropic Claude to generate brand-aligned Vietnamese captions with hashtags, and stores enriched content in DynamoDB with `status = RAW` for downstream approval workflows. The pipeline implements individual item processing with per-item error isolation, dead-letter queue handling for failures, and Telegram alerts for critical errors. Cost target: $8–15/month (Apify + Claude + Lambda + storage). All infrastructure deployed via AWS CDK, reusing Phase 1 patterns (shared config, utilities, IAM role, Lambda Layer).

## Technical Context

**Language/Version**: Python 3.9+ (aligned with Phase 1)  
**Primary Dependencies**: boto3 (DynamoDB, S3, Parameter Store, SNS), requests (Apify API), anthropic SDK, aws-cdk-lib v2  
**Storage**: DynamoDB (HealingBedroomContent table with GSI on content_hash for deduplication), S3 (image staging with 7-day lifecycle), Parameter Store (API credentials)  
**Testing**: pytest (unit tests), moto (DynamoDB/S3 mocking), manual integration tests with test Apify tokens  
**Target Platform**: AWS Lambda (Python 3.12 runtime), EventBridge Scheduler, ap-southeast-1 region  
**Project Type**: Serverless pipeline (Lambda + infrastructure-as-code via CDK)  
**Performance Goals**: Process ≥ 10–20 items per day; ≥ 95% caption success rate; CloudFront image access within 10 seconds  
**Constraints**: Lambda 15-min timeout per item; exponential backoff retry (max 3 attempts); $8–15/month cost; Claude Haiku only (not Sonnet per Constitution)  
**Scale/Scope**: Phase 2 MVP scope – 3 platforms (TikTok, Instagram, Facebook), hardcoded prompts, individual item processing, basic dead-letter queue

## Constitution Check

✅ **Compliance-First**: N/A at pipeline layer; compliance gates enforced in Phase 3 approval dashboard  
✅ **Simplicity Over Perfection**: Hardcoded prompts, config-driven scheduling, no perceptual hashing – MVP approach  
✅ **Cost Discipline**: Apify Actor quotas pre-negotiated; Claude Haiku only; DynamoDB on-demand (Phase 1 model); S3 lifecycle 7-day auto-cleanup; $8–15/month budget  
✅ **Documentation & Decisions**: Phase 0 research.md captures all API choices; tech-spec in vault/ with rationale  
✅ **Automation with Human Oversight**: Pipeline is fully automated; human approval happens downstream in Phase 3  
✅ **Lean Iteration & Pivot Readiness**: Success metrics defined (SC-001 through SC-009); can pivot prompt strategy or add platforms without architectural rework

**No Constitution violations detected.** All decisions align with project principles.

## Project Structure

### Documentation (this feature)

```text
specs/002-content-ingestion-pipeline/
├── spec.md              # Feature specification (COMPLETE)
├── plan.md              # This file (implementation plan)
├── research.md          # Phase 0 research (DELIVERABLE)
├── data-model.md        # Phase 1 data model (DELIVERABLE)
├── quickstart.md        # Phase 1 quickstart guide (DELIVERABLE)
├── contracts/           # Phase 1 API contracts (DELIVERABLE)
└── checklists/
    └── requirements.md  # Specification validation (COMPLETE)
```

### Source Code (repository root)

```text
src/
├── common/                    # [REUSED FROM PHASE 1]
│   ├── __init__.py
│   ├── config.py            # Add INGESTION_SCHEDULE_CRON, SOURCES_CONFIG
│   ├── utils.py             # [Existing: get_parameter, generate_item_id, etc.]
│   └── schemas.py           # Add ContentItem, IngestionRun Pydantic models
│
├── lambdas/
│   ├── notifier/            # [EXISTING PHASE 1]
│   │   └── lambda_function.py
│   │
│   └── ingestion/           # [NEW PHASE 2]
│       ├── lambda_function.py       # Main handler
│       ├── apify_client.py          # Apify Actor orchestration
│       ├── claude_caption_generator.py  # Claude caption prompt + API calls
│       ├── image_processor.py       # Download, hash, S3 upload
│       ├── deduplication.py         # Content hash lookup in DynamoDB GSI
│       ├── error_handlers.py        # Retry logic, dead-letter queue
│       └── __init__.py
│
└── layers/
    └── common/              # [REUSED FROM PHASE 1]
        └── python/common/
            ├── __init__.py
            ├── config.py
            ├── utils.py
            └── schemas.py

cdk/
├── stack.py                 # [EXTEND PHASE 1]
│   # Add: EventBridge Scheduler, Lambda ingestion, SQS dead-letter queue, DynamoDB GSI
└── config.py                # [EXTEND PHASE 1]
    # Add: INGESTION_SCHEDULE_CRON, SOURCES_CONFIG, DEAD_LETTER_QUEUE_NAME

tests/
├── unit/
│   ├── test_apify_client.py
│   ├── test_claude_caption_generator.py
│   ├── test_deduplication.py
│   ├── test_image_processor.py
│   └── test_lambda_ingestion.py
│
└── integration/
    ├── test_ingestion_pipeline_e2e.py
    └── test_dynamodb_queries.py

scripts/
└── python/
    └── test-ingestion-pipeline.py  # Manual trigger + verification script
```

## Key Design Decisions

| Decision | Rationale | Alternative |
|----------|-----------|-------------|
| **Individual item processing** | Per-item error isolation; failed items don't block others; simpler retry logic; aligns with Lambda timeout model (15 min max) | Batch processing adds complexity; if 1 item fails, whole batch retried; cascading failures risk |
| **EventBridge Scheduler (config-driven cron)** | Serverless, no additional infra; cron in config.py allows schedule change without code redeploy; flexible for 6–12 hr intervals | Hard-wire in CDK (requires redeploy); Parameter Store (adds runtime overhead) |
| **Hardcoded Claude prompt (Phase 2 MVP)** | Fastest development iteration; no external dependencies; sufficient for MVP validation | Parameter Store (adds operational complexity too early); deferring to Phase 3 if needed |
| **Content hash (MD5) + URL deduplication** | Catches image theft/reposts even from different URLs; O(1) GSI lookup; cost-effective for MVP budget | URL-only (misses reposts); pHash (too expensive for budget) |
| **Dead-letter queue (SQS or DynamoDB)** | Persistent storage for investigation; enables manual retry or investigation; not lost on Lambda timeout | Log-only (harder to debug; retry requires manual intervention) |
| **Reuse Phase 1 patterns (config, utils, Layer)** | Single source of truth; consistent error handling; shared maintenance; proven in notifier Lambda | Self-contained modules (duplicate code; harder to maintain) |

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Apify API rate limit hit mid-batch | Pipeline stalls; items queue up; ingestion delays | Implement exponential backoff (max 3 retries); pre-negotiate Apify quotas; monitor via CloudWatch |
| Claude timeout (>30 sec) on complex captions | Item hangs; Lambda timeout; potential cost overrun | 30-sec timeout per Claude call; move to dead-letter after 3 retries; log and alert via Telegram |
| S3 upload fails (permissions, quota, connectivity) | Image lost; CloudFront URL generation skipped; item corrupted in DynamoDB | Retry S3 upload up to 3x; if persistent, move to dead-letter; verify bucket policy allows Lambda role |
| Duplicate detection misses reposted image | Content duplicates in DynamoDB; manual cleanup required | MD5 hash + URL provides 99%+ accuracy per SC-003; spot-check monthly |
| Parameter Store credential rotation mid-execution | Auth failures; Telegram alerts delayed; manual investigation needed | Implement try-catch around get_parameter calls; document rotation procedure in Phase 1 guide |
| Lambda Layer size exceeds 250 MB limit | Deployment fails; blocking issue for adding dependencies | Monitor Layer size; keep common/ module lean; defer heavy deps to Lambda zip if needed |
| Telegram alerts not received (bot token invalid) | Silent failures; ops unaware of pipeline errors | Test Telegram connectivity at Phase 1 completion; verify token in Parameter Store; manual test script provided |

## Success Checkpoints

### Phase 0 Completion (Research)
- [ ] All "NEEDS CLARIFICATION" items resolved
- [ ] API choice decisions documented (Apify, Claude, EventBridge, SQS/DynamoDB for DLQ)
- [ ] Research artifacts created: research.md (TO BE CREATED)

### Phase 1 Completion (Design & Contracts)
- [ ] Data model finalized: ContentItem, IngestionRun schemas with field validation
- [ ] DynamoDB schema designed: GSI on content_hash for O(1) dedup lookup
- [ ] API contracts defined: Apify request/response, Claude prompt/response, S3 pre-signed URLs
- [ ] Quickstart guide: Step-by-step deployment instructions
- [ ] Artifacts: data-model.md, contracts/*.md, quickstart.md (TO BE CREATED)

### Pre-Implementation (Phase 2 Tasks)
- [ ] CDK Stack extended with EventBridge, Lambda ingestion, SQS dead-letter queue
- [ ] Shared Layer updated with Pydantic schemas
- [ ] config.py extended with INGESTION_SCHEDULE_CRON, SOURCES_CONFIG
- [ ] Lambda handlers implemented: apify_client, claude_caption_generator, image_processor, deduplication, error_handlers
- [ ] Unit tests: 80%+ code coverage on critical paths (dedup, image processing, retry logic)
- [ ] Integration tests: E2E pipeline with test Apify tokens and mock Claude responses
- [ ] Manual test script: Trigger ingestion, verify DynamoDB + S3 + CloudFront + Telegram
- [ ] Documentation: README Phase 2 updates, troubleshooting guide

## Next Steps

1. **Proceed to Phase 0 (Research)**: Research will document all technical decisions for:
   - Apify Actor selection (TikTok, Instagram, Facebook scrapers)
   - Claude prompt design (brand tone, hashtag strategy)
   - EventBridge cron expression validation
   - SQS vs. DynamoDB for dead-letter queue selection
   - Cost estimation for Phase 2 monthly run rate

2. **After Phase 0**: Execute Phase 1 (Design) to generate data-model.md, contracts/, quickstart.md

3. **After Phase 1**: Run `/speckit.tasks` to generate actionable tasks.md with sprint planning

4. **Implementation**: Execute tasks in priority order (P1 user stories first, P2/P3 deferred if needed)

---

**Prepared by**: Copilot Planning Workflow  
**Status**: Ready for Phase 0 Research  
**Estimated Duration**: 2–3 weeks (research + design + implementation)  
**Budget Impact**: +$8–15/month (Apify, Claude, Lambda, S3 storage)
