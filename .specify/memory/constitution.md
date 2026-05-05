<!-- Sync Impact Report
  Version: 1.0.0 (initial)
  Status: Constitution established for AI-marketer project
  Changed Principles: None (inaugural constitution)
  Added Sections: Core Principles, Operations, Governance
  Removed Sections: None
  Templates Updated: All dependent templates reviewed for alignment
  Follow-up TODOs: None - constitution ratified May 3, 2026
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

### IV. Documentation & Decisions as First-Class Artifacts
All major decisions, design choices, and lessons learned must be captured in `/vault/` with clear timestamps. Plan, tech-spec, and phase notes are living documents updated before implementation. This repo stores both code and decision history—they are equally important.

### V. Automation with Human Oversight
AI generates content at scale; humans verify every item before posting. The Streamlit dashboard with "Verify Compliance" checkbox is the mandatory gate. No fully autonomous posting. Human judgment remains the trust boundary.

### VI. Lean Iteration & Pivot Readiness
Define clear checkpoints (Weeks 4, 8, 12) and metrics (organic reach, CTR, affiliate clicks). Pivot format or niche without hesitation if metrics miss thresholds. Treat first 12 weeks as a constrained pilot; do not scale until proof-of-concept metrics are achieved.

## Technology & Operations Standards

**Tech Stack Constraints**:
- LLM: Claude Haiku 4.5 by default; Sonnet 4.6 only when unavoidable
- Image Generation: Nano Banana 2 (fal.ai) for Vietnamese text handling
- Infrastructure: AWS Lambda + DynamoDB + S3 + CloudWatch (serverless only, no EC2)
- Monitoring: CloudWatch Logs + Telegram alerts; no complex observability infrastructure

**Development Environment**:
- Repository structure: `/vault/` for plans and decisions, `/src/` for code
- Source of truth: Specify workflow (plan.md → tech-spec.md → implementation)
- Change tracking: Git commits tied to Spec Kit tasks; all PRs reference decisions in `/vault/`

**Compliance Enforcement**:
- Every social post MUST include: AIGC disclosure tag, affiliate link disclaimer, niche category tag
- Dashboard hard gate: "Verify Compliance" checkbox required before approval (no bypassing)
- Content review SOP: Dashboard review + manual audit before first publication of new niche/format

## Governance

This Constitution is the supreme law of the AI-Marketer project. All engineering decisions, deployment practices, and operational procedures MUST comply with these principles.

**Amendment Procedure**:
1. Proposed amendment MUST be documented in `/vault/amendment-proposal.md` with rationale
2. Changes to Core Principles require manual review and approval before committing
3. Version bumps follow semantic versioning:
   - MAJOR: Principle removed or redefined (backward-incompatible governance shift)
   - MINOR: New principle or section added; existing guidance expanded
   - PATCH: Clarifications, wording improvements, typo fixes
4. Each amendment updates LAST_AMENDED_DATE and increments version

**Compliance Verification**:
- All code reviews MUST verify adherence to Cost Discipline and Simplicity principles
- Monthly cost audits against the $50 USD hard cap
- Weekly compliance spot-checks: Sample 5 recent posts for AIGC labels and disclaimers
- Checkpoint reviews at Weeks 4, 8, 12 against defined success metrics

**Guidance Runtime Documents**:
- See [.github/copilot-instructions.md](.github/copilot-instructions.md) for development environment setup
- See `vault/plan.md` for timeline, budget, and checkpoint metrics
- See `vault/phase1/tech-spec.md` for implementation details and architecture

---

**Version**: 1.0.0 | **Ratified**: 2026-05-03 | **Last Amended**: 2026-05-03
