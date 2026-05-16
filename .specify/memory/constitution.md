<!-- Sync Impact Report
  Version: 1.0.0 → 1.1.0 (MINOR: added technical governance & architecture principles)
  Status: Constitution amended to honor CLAUDE.md technical standards
  Changed Principles: None renamed/removed; All prior principles preserved
  Added Sections: II. Infrastructure-as-Code Discipline, III. Code Quality & Testing Standards
  Removed Sections: None
  Templates Updated: constitution.md aligned with CLAUDE.md architecture guidance
  Follow-up TODOs: None - amendment ratified May 9, 2026
-->

# AI-Marketer Constitution
**Building an AI-first e-commerce venture with compliance-first discipline, lean engineering, and human oversight**

## Core Principles

### I. Compliance-First (NON-NEGOTIABLE)
Every piece of AIGC content MUST carry explicit AIGC labels and affiliate disclaimers before publication. Hard gates in the dashboard enforce this with no exceptions. Compliance violations block posting immediately and trigger incident review. This protects audience trust and ensures sustainable affiliate operations.

### II. Simplicity Over Perfection
Build only what directly generates revenue or supports compliance. No over-engineering infrastructure, no speculative features, no organizational-only tooling. YAGNI (You Aren't Gonna Need It) discipline. Target: Deploy MVP in 12 weeks, iterate on data.

### III. Cost Discipline
Every tool choice and API call must justify its cost. Default to lowest-cost options: Claude Haiku (not Sonnet), DynamoDB on-demand (not provisioned), Lambda (not EC2). Monthly budget hard-capped at $50 USD. Trade cost constraints for feature scope—always.

### V. Automation with Human Oversight
AI generates content at scale; humans verify every item before posting. The Streamlit dashboard with "Verify Compliance" checkbox is the mandatory gate. No fully autonomous posting. Human judgment remains the trust boundary.

### VI. Lean Iteration & Pivot Readiness
Define clear checkpoints (Weeks 4, 8, 12) and metrics (organic reach, CTR, affiliate clicks). Pivot format or niche without hesitation if metrics miss thresholds. Treat first 12 weeks as a constrained pilot; do not scale until proof-of-concept metrics are achieved.

### VII. Infrastructure-as-Code Discipline
All AWS infrastructure MUST be defined in AWS CDK (Python 3.12). Infrastructure is versioned and reproducible; all resource definitions live in code, never manual console operations. The shared layer (`src/common/`) is the source of truth—it is symlinked to Lambda layers but only edited in source form. Configuration is centralized in `src/common/config.py`; no hardcoded values in Lambda functions or CDK code.

### VIII. Code Quality & Testing Standards
All Python code MUST pass black (100-char line length), flake8, mypy, and pylint checks before merge. Tests are mandatory: Lambda functions have unit tests with mocked AWS calls; integration tests verify end-to-end flows. Code reviews verify compliance with style and testing discipline.

## Technology & Operations Standards

**Tech Stack Constraints**:
- LLM: Claude Haiku 4.5 by default; Sonnet 4.6 only when unavoidable
- Image Generation: Nano Banana 2 (fal.ai) for Vietnamese text handling
- Infrastructure: AWS Lambda + DynamoDB + S3 + CloudWatch (serverless only, no EC2)
- Monitoring: CloudWatch Logs + Telegram alerts; no complex observability infrastructure

**Compliance Enforcement**:
- Every social post MUST include: AIGC disclosure tag, affiliate link disclaimer, niche category tag
- Dashboard hard gate: "Verify Compliance" checkbox required before approval (no bypassing)
- Content review SOP: Dashboard review + manual audit before first publication of new niche/format

## Governance

This Constitution is the supreme law of the AI-Marketer project. All engineering decisions, deployment practices, and operational procedures MUST comply with these principles.

**Compliance Verification**:
- All code reviews MUST verify adherence to Cost Discipline and Simplicity principles
- Monthly cost audits against the $50 USD hard cap
- Weekly compliance spot-checks: Sample 5 recent posts for AIGC labels and disclaimers
- Checkpoint reviews at Weeks 4, 8, 12 against defined success metrics

---

**Version**: 1.1.0 | **Ratified**: 2026-05-03 | **Last Amended**: 2026-05-09
