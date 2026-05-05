<!-- SPECKIT START -->
For additional context about technologies to be used, project structure,
shell commands, and other important information, read the current plan:

**Current Plan**: [Phase 1 Foundation – AWS Infrastructure](../specs/001-phase1-foundation/plan.md)

**Related Specs**:
- [Phase 1 Specification](../specs/001-phase1-foundation/spec.md) – Features, requirements, acceptance criteria
- [Phase 1 Research](../specs/001-phase1-foundation/research.md) – Technical decisions & rationale
- [Data Model](../specs/001-phase1-foundation/data-model.md) – DynamoDB schema
- [Quickstart Guide](../specs/001-phase1-foundation/quickstart.md) – Deployment instructions
- [Interface Contracts](../specs/001-phase1-foundation/contracts/) – External integration specs

For information on project principles and decision-making, read: [Constitution](../.specify/memory/constitution.md)
<!-- SPECKIT END -->

## Phase 1 Implementation (✅ COMPLETE)

### Project Overview

**Healing Bedroom MVP** – An AI-powered content curation platform deployed on AWS serverless infrastructure. Phase 1 establishes foundational AWS infrastructure (DynamoDB, S3, CloudFront, Parameter Store, Budget Alarms) via AWS CDK in Python.

**Repository**: `AI-marketer` on `001-phase1-foundation` branch  
**Status**: Phase 1 COMPLETE; Phase 2 (Ingestion Pipeline) READY  
**Tech Stack**: Python 3.9+, AWS CDK v2, boto3, DynamoDB, S3, CloudFront, Lambda

### Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **On-Demand DynamoDB** | Unpredictable ingestion patterns; pay per request vs. reserved capacity |
| **S3 + CloudFront** | Cost-effective image delivery; 7-day lifecycle for automatic cleanup |
| **Parameter Store (Standard Tier)** | Free secrets storage for Phase 1; plan SecureString for Phase 2+ |
| **Single IAM Role** | All Lambdas share least-privilege role (DynamoDB, S3, Parameter Store, CloudWatch) |
| **CloudFront OAC** | Modern origin access control; replaces deprecated OAI bucket policies |
| **Telegram Bot Alerts** | Simple, free, immediate budget notifications without webhook overhead |

### Directory Structure

```
cdk/                     # Infrastructure-as-code
├── stack.py           # Main CDK stack with all Phase 1 resources
├── config.py          # Configuration constants, env var loading
└── requirements.txt   # aws-cdk-lib==2.139.0, boto3

src/                     # Application code
├── lambdas/notifier/  # SNS → Telegram budget alerts
├── common/            # Shared utilities: Parameter Store, schemas, config
└── dashboard/         # Phase 2+ placeholder

tests/                   # Testing & fixtures
├── unit/test_cdk_stack.py  # CDK assertions (20+ tests)
└── fixtures/sample_data.json  # Sample DynamoDB items, SNS messages

docs/                    # Comprehensive guides
├── architecture.md       # System design, data flows, scaling
├── deployment-guide.md   # Step-by-step deployment (15 steps)
├── parameter-store-guide.md  # Secrets management & rotation
└── budget-alerts-guide.md    # Budget monitoring & Telegram setup

scripts/                 # Utility scripts
├── bash/cleanup.sh     # `cdk destroy` with warnings
└── python/
    ├── health-check.py      # Verify all Phase 1 resources exist
    ├── verify-param-store.py  # Test Parameter Store access
    ├── test-telegram-alert.py  # Send test budget alert
    └── audit-costs.py       # AWS Cost Explorer analysis
```

### Deployment Quick Reference

```bash
# Setup
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # Edit with AWS credentials & secrets

# Validate
cdk synth  # Generate CloudFormation template

# Deploy
cdk deploy --require-approval never

# Verify
python scripts/python/health-check.py
python scripts/python/test-telegram-alert.py

# Cost check
python scripts/python/audit-costs.py
```

**Estimated Time**: 10–15 minutes  
**Budget**: $40/month with 50% & 80% alerts

### AWS Resources Created

| Resource | Purpose | Phase |
|----------|---------|-------|
| **DynamoDB**: HealingBedroomContent | Content items pipeline storage (20+ attributes) | 1 |
| **S3**: healing-bedroom-images-* | Image storage with 7-day lifecycle | 1 |
| **CloudFront**: healing-bedroom-dist | Image CDN with 1-day cache | 1 |
| **Parameter Store**: /healing-bedroom/* | 6 parameters (Anthropic, fal.ai, Telegram, Apify) | 1 |
| **Lambda**: notifier | SNS → Telegram budget alerts | 1 |
| **IAM Role**: lambda-healing-bedroom-role | Least-privilege for all Lambdas | 1 |
| **CloudWatch**: /aws/lambda/healing-bedroom | 7-day log retention | 1 |
| **SNS**: healing-bedroom-budget-alerts | Budget alert distribution | 1 |
| **AWS Budget**: HealingBedroom-Monthly | $40/month with 50% & 80% thresholds | 1 |

### Phase 2 Preview

**User Story 1**: Content Ingestion (Apify web scraper)  
**User Story 2**: Image Processing (Anthropic Claude + fal.ai)  
**User Story 3**: Approval Dashboard (Streamlit)  
**User Story 4**: Social Media Posting (Telegram, Facebook)

Estimated: 2–3 weeks  
Budget: ~$390/month (vs. $40 Phase 1)

### Critical Files for Phase 2+

- [Phase 1 Data Model](../specs/001-phase1-foundation/data-model.md) – DynamoDB schema reference
- [Budget Alerts Guide](docs/budget-alerts-guide.md) – Cost monitoring pattern
- [Parameter Store Guide](docs/parameter-store-guide.md) – Secrets management
- [Architecture](docs/architecture.md) – System design & scaling
- [Implementation Report](IMPLEMENTATION_REPORT.md) – Complete Phase 1 summary

### Common Commands

```bash
# Development
black src/ cdk/  # Format code
flake8 src/ cdk/  # Lint
mypy src/ cdk/  # Type check
pytest tests/  # Run tests

# CDK
cdk list  # Show stacks
cdk diff  # Compare with deployed
cdk destroy  # Delete infrastructure

# Verification
python scripts/python/health-check.py
python scripts/python/verify-param-store.py
python scripts/python/audit-costs.py

# Cleanup
bash scripts/bash/cleanup.sh  # WARNING: Deletes all resources
```

### Troubleshooting

**Issue**: CDK deploy fails with credential error  
**Solution**: Run `aws configure` with valid AWS credentials

**Issue**: Parameter Store retrieval fails  
**Solution**: Check `/healing-bedroom/` parameters in AWS Systems Manager console

**Issue**: Telegram alerts not received  
**Solution**: Run `python scripts/python/test-telegram-alert.py` to diagnose

**Issue**: S3 bucket already exists  
**Solution**: Modify `BUCKET_NAME_SUFFIX` in `.env` to use unique name

For complete troubleshooting, see [deployment-guide.md](docs/deployment-guide.md).
