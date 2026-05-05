# Implementation Plan: Phase 1 Foundation – AWS Infrastructure

**Branch**: `001-phase1-foundation` | **Date**: 2026-05-03 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/001-phase1-foundation/spec.md`

## Summary

**Primary Requirement**: Deploy core AWS infrastructure (DynamoDB, S3, CloudFront, IAM, Parameter Store, Budget Alarms) as code using AWS CDK (Python) to support the Phase 2+ feature pipeline. Enable solo developer to reproduce, version-control, and iterate on infrastructure without manual AWS Console steps.

**Technical Approach**: 
- Infrastructure-as-Code using AWS CDK (Python) with single `HealingBedroomStack` construct
- Data persistence: DynamoDB on-demand (with UUID v4 partition key, GSI for status-based queries)
- Image storage & delivery: S3 bucket (private, lifecycle deletes after 7 days) + CloudFront (public HTTPS URL via OAC)
- Secrets management: AWS Systems Manager Parameter Store (standard tier, manual rotation)
- Cost monitoring: AWS Budget ($40/month cap) with SNS → Lambda Notifier → Telegram alerts
- IAM security: Single shared `lambda-healing-bedroom-role` with fine-grained resource ARNs (least privilege)
- Observability: CloudWatch Logs capturing all Lambda executions; 7-day retention

**Outcome**: Fully functional infrastructure deployed via `cdk deploy`, ready for Phase 2 ingestion layer to begin populating DynamoDB with scraped content.

## Technical Context

**Language/Version**: Python 3.9+  
**Primary Dependencies**: AWS CDK (v2.x), boto3, aws-cdk-lib, constructs  
**Storage**: DynamoDB (on-demand mode, single table `HealingBedroomContent`), S3 bucket for images  
**Testing**: pytest for infrastructure validation; manual AWS resource verification during Phase 1  
**Target Platform**: AWS Lambda (runtime Python 3.11), serverless architecture  
**Project Type**: Infrastructure-as-Code (IaC) backend; serverless application foundation  
**Performance Goals**: 
- Lambda cold start < 3 seconds
- DynamoDB query latency < 100ms (on-demand)
- CloudFront edge latency < 50ms for image delivery
- CDK deployment completion < 10 minutes

**Constraints**: 
- Monthly budget hard-capped at $40 USD
- Single region deployment (us-east-1)
- No multi-region replication
- No reserved capacity or provisioned throughput (on-demand only)
- Parameter Store standard tier only (no advanced tier)

**Scale/Scope**: 
- Solo developer team (1 person)
- 1 DynamoDB table with 1 GSI
- 1 S3 bucket with lifecycle policy
- 1 CloudFront distribution
- 1 shared Lambda IAM role
- 5 Parameter Store parameters
- Expected initial data volume: < 1000 items/month → scales to Phase 2+

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

✅ **Compliance-First**: Infrastructure includes Parameter Store for storing compliance-related settings (AIGC labels, affiliate disclaimers) that Phase 2+ will enforce via Streamlit dashboard hard gate. Phase 1 foundation supports compliance enforcement layer.

✅ **Simplicity Over Perfection**: CDK stack is minimal and focused (no SQS, Step Functions, DynamoDB Streams, or other "nice-to-have" services). YAGNI discipline applied—only core resources deployed. Single shared IAM role (not per-function) keeps complexity low for MVP.

✅ **Cost Discipline**: Infrastructure designed for < $40/month:
- DynamoDB on-demand (no reserved capacity)
- S3 lifecycle policy deletes after 7 days (low average storage)
- Parameter Store standard tier (free)
- CloudFront edge caching reduces origin requests
- Single region (no replication cost)
- Budget alarms enforce hard cap via Telegram notifications

✅ **Documentation & Decisions**: Spec, plan, and constitution all documented. Clarifications recorded (3 questions resolved). All design decisions justified in plan.md and spec.md.

✅ **Automation with Human Oversight**: Phase 1 is infrastructure automation (IaC); no autonomous posting or content generation in Phase 1. Phase 2+ will introduce Lambda-based automation with mandatory human approval gates in Streamlit dashboard.

✅ **Lean Iteration & Pivot Readiness**: Phase 1 is foundation-only (3–5 day timeline). Phase 2+ will introduce feature layers (ingestion, processing, posting). Clear checkpoint structure: deploy infrastructure (Week 1) → test infrastructure (Week 1–2) → begin Phase 2 ingestion layer.

**GATE RESULT**: ✅ **PASS** – All constitution principles satisfied. Proceed to Phase 0 research.

## Project Structure

### Documentation (this feature)

```text
specs/001-phase1-foundation/
├── plan.md              # This file (/speckit.plan command output)
├── spec.md              # Feature specification
├── research.md          # Phase 0 research findings
├── data-model.md        # DynamoDB schema design
├── quickstart.md        # Deployment guide
├── contracts/           # External interface contracts
│   ├── parameter-store-interface.md
│   └── budget-alert-telegram-pipeline.md
├── checklists/
│   └── requirements.md   # Specification quality checklist
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
healing-bedroom-mvp/
├── cdk/                    # AWS CDK infrastructure-as-code
│   ├── stack.py            # HealingBedroomStack construct
│   ├── config.py           # Configuration (region, budget, names)
│   └── requirements.txt    # CDK Python dependencies
├── src/
│   ├── lambdas/
│   │   ├── notifier/       # Telegram budget alert notifier
│   │   │   └── lambda_function.py
│   │   ├── ingestion/      # Phase 2+
│   │   ├── processor/      # Phase 3+
│   │   └── poster/         # Phase 5+
│   ├── dashboard/          # Phase 4+ (Streamlit)
│   └── common/
│       ├── utils.py        # Shared utilities (UUID generation, Parameter Store access)
│       ├── schemas.py      # Data schemas (validation, serialization)
│       └── config.py       # Shared config
├── prompts/                # AI prompts
│   ├── caption-prompt.md
│   └── image-prompt.md
├── tests/
│   ├── unit/              # Unit tests (pytest)
│   ├── integration/       # Integration tests
│   └── fixtures/          # Test data
├── scripts/
│   ├── bash/
│   │   ├── deploy.sh
│   │   ├── test.sh
│   │   └── cleanup.sh
│   └── python/
│       ├── seed-data.py   # Phase 2+
│       └── audit.py       # Cost/compliance audit
├── .github/
│   ├── workflows/         # GitHub Actions
│   │   ├── deploy.yml
│   │   ├── test.yml
│   │   └── security-scan.yml
│   ├── copilot-instructions.md
│   └── prompts/
├── .specify/              # Spec Kit configuration
│   ├── extensions.yml
│   ├── templates/
│   └── scripts/
├── vault/                 # Decision & operational logs
│   ├── plan.md           # Business plan
│   ├── phase1/
│   │   ├── week1.md
│   │   ├── Niche-selected.md
│   │   └── tech-spec/
│   └── secret.txt        # Sensitive notes (git-ignored)
├── requirements.txt       # Python runtime dependencies
├── app.py                # CDK entry point
├── .env.example          # Environment variable template
├── README.md             # Setup and deployment guide
├── .gitignore
└── cdk.json             # CDK configuration
```

**Structure Decision**: 
- Single monolithic repository (not microservices)
- CDK for infrastructure
- Lambda functions organized by pipeline stage (ingestion → processing → posting)
- Spec Kit stores specs, plans, research in `specs/` directory
- Decision history in `vault/` directory
- Python 3.9+ shared across all services

---

## Complexity Tracking

> **Post-Design Constitution Re-Check**

All Phase 1 design decisions have been validated against the constitution:

✅ **Compliance-First**: Parameter Store and Telegram alerts ready for Phase 2+ compliance gate integration  
✅ **Simplicity Over Perfection**: Minimal CDK stack, no over-engineering, single shared IAM role  
✅ **Cost Discipline**: Budget cap enforced, all components designed for < $40/month  
✅ **Documentation & Decisions**: Spec, plan, research, data model, contracts all documented  
✅ **Automation with Human Oversight**: IaC automation in Phase 1; human gates introduced in Phase 2+  
✅ **Lean Iteration & Pivot Readiness**: 3–5 day Phase 1 timeline, clear Phase 2+ path  

**GATE RESULT (Post-Design)**: ✅ **PASS** – All principles revalidated. Ready for Phase 2 task generation.

---

## Deliverables Checklist (Phase 1)

- [x] Specification complete (spec.md)
- [x] Research phase complete (research.md) – 8 research topics investigated
- [x] Data model defined (data-model.md) – DynamoDB schema, GSI, lifecycle, billing
- [x] Interface contracts defined (contracts/) – Parameter Store, budget alerts, Telegram pipeline
- [x] Quickstart guide complete (quickstart.md) – 10-step deployment procedure
- [x] CDK stack designed (cdk/stack.py structure outlined)
- [x] IAM role strategy finalized (single shared role with fine-grained ARNs)
- [x] Repository structure defined (root directory layout)
- [x] Agent context updated (.github/copilot-instructions.md points to plan)
- [x] Constitution re-checked and validated

---

## Timeline & Milestones

| Phase | Timeline | Deliverable | Status |
|-------|----------|-------------|--------|
| **Phase 0: Research** | Day 1 | research.md | ✅ Complete |
| **Phase 1: Design** | Day 1–2 | data-model.md, contracts/, quickstart.md | ✅ Complete |
| **Phase 1: CDK Implementation** | Day 3–5 | AWS resources deployed via `cdk deploy` | 📋 Pending (task generation) |
| **Phase 1: Testing & Acceptance** | Day 5 | All acceptance criteria verified | 📋 Pending (implementation) |
| **Phase 2: Task Generation** | Day 5+ | tasks.md generated via `/speckit.tasks` | 📋 Pending |

---

## Success Metrics (Phase 1 Completion)

| Metric | Target | Acceptance Criteria |
|--------|--------|-------------------|
| Infrastructure deployment time | < 15 minutes | CDK stack deployed successfully |
| CloudFront activation | 15–20 minutes | Public HTTPS URL accessible for images |
| DynamoDB operational | Immediate | Query/put operations succeed |
| Budget alerts | < 2 minutes latency | Telegram message received within threshold |
| Parameter Store access | < 100ms latency | Lambda retrieves API keys without errors |
| Infrastructure cost | < $5/day | AWS Cost Explorer confirms spend |
| Documentation completeness | 100% | All spec, plan, research, quickstart complete |
| Constitution alignment | 100% | All 6 principles validated |

---

## Next Actions

1. **Commit Phase 1 planning** → `/speckit.git.commit` (optional)
2. **Generate implementation tasks** → `/speckit.tasks` (required for Phase 1 implementation)
3. **Review quickstart.md** → Follow deployment procedure to bring infrastructure online
4. **Begin Phase 2 design** → After Phase 1 infrastructure operational
