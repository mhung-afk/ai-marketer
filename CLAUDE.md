# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

**Healing Bedroom MVP** is a Vietnamese AI-powered content curation and repurposing pipeline. The project uses **AWS CDK** (Infrastructure-as-Code with Python 3.12) to deploy a serverless architecture with Lambda functions, DynamoDB, S3, CloudFront, and monitoring.

**Current Phase**: Phase 1 - Infrastructure Foundation (May 2026)

---

## High-Level Architecture

### Core Components

1. **Infrastructure-as-Code (CDK)**
   - `app.py` — CDK app entry point; initializes the stack and environment
   - `cdk/stack.py` — Main stack definition with all AWS resources (DynamoDB, S3, CloudFront, Lambda, SNS, Budget alarms)

2. **Shared Code Layer** (`src/common/`)
   - `config.py` — Centralized config constants (AWS region, Parameter Store paths, Lambda names, S3 bucket names, budget thresholds)
   - `utils.py` — Helper functions for AWS API calls (e.g., `get_parameter()` for SSM Parameter Store)
   - `schemas.py` — Pydantic/data models for validation

3. **Lambda Functions** (`src/lambdas/`)
   - `notifier/lambda_function.py` — Budget alert receiver; triggered by SNS, forwards alerts to Telegram

4. **Lambda Layer** (`src/layers/common/python/common/`)
   - Symlinked to `src/common/`; packaged and deployed as a Lambda layer so all Lambdas can import shared utilities
   - **Do not edit** `src/layers/common/python/common/` directly—only work on `src/common/`

5. **Tests** (`tests/`)
   - `unit/` — Unit tests (mocked AWS calls, no actual deployments)
   - `fixtures/` — Test data (JSON fixtures for SNS events, DynamoDB records, etc.)
   - `integration/` — Integration tests (may hit real AWS; see setup before running)

### Data Flow

1. AWS Budget triggers SNS topic → Lambda notifier receives event
2. Lambda retrieves Telegram credentials from Parameter Store
3. Lambda formats alert and posts to Telegram
4. DynamoDB stores content metadata; S3 stores images; CloudFront serves them globally

---

## Development Setup

### Prerequisites
- Python 3.12+ (required; CDK and Lambdas are Python 3.12)
- AWS CLI v2 configured with credentials (`aws configure`)
- Node.js 18+ (for AWS CDK CLI)
- Git

### Initial Setup
```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # macOS/Linux; Windows: venv\Scripts\activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Copy environment file and fill in required values
cp .env.example .env
# Edit .env: AWS_REGION, AWS_ACCOUNT_ID, BUDGET_LIMIT, API_KEY tokens
```

---

## Common Commands

### CDK Deployment
```bash
# Validate and synthesize CloudFormation template
cdk synth

# Deploy infrastructure (first time: run bootstrap first)
cdk bootstrap
cdk deploy --require-approval never

# Destroy all resources (will prompt for confirmation)
cdk destroy
```

### Testing
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/unit/test_lambda_notifier.py

# Run with coverage
pytest --cov=src

# Run single test function
pytest tests/unit/test_lambda_notifier.py::test_lambda_handler_success
```

### Code Quality
```bash
# Format code with black (line length: 100)
black . --line-length=100

# Lint with flake8 (excludes venv, cdk.out)
flake8 . --exclude=venv,cdk.out,.git --max-line-length=100

# Type check with mypy
mypy . --ignore-missing-imports --no-implicit-optional

# Check with pylint (linting)
pylint $(find . -path ./venv -prune -o -type f -name "*.py" -print | grep -E "(cdk|src|tests)")
```

Run all checks (as used in CI/CD):
```bash
black --check . --line-length=100 --extend-exclude="(venv|cdk\.out|cdk\.context\.json)"
flake8 . --exclude=venv,cdk.out,.git --max-line-length=100
mypy . --ignore-missing-imports --no-implicit-optional --exclude "(venv|cdk\.out)"
```

### Miscellaneous
```bash
# Activate virtual environment
source venv/bin/activate

# View CDK resources that would be created (without deploying)
cdk diff
```

---

## Key Files & Their Purpose

| File | Purpose |
|------|---------|
| `app.py` | CDK app entry point; instantiates the stack |
| `cdk/stack.py` | Main infrastructure stack (1000+ lines); all AWS resources defined here |
| `src/common/config.py` | Centralized config (S3 prefix, DynamoDB table name, Lambda names, etc.) |
| `src/common/utils.py` | Shared utilities (e.g., `get_parameter()` for Parameter Store) |
| `src/common/schemas.py` | Pydantic models/schemas for data validation |
| `src/lambdas/notifier/lambda_function.py` | Budget alert notifier Lambda |
| `tests/unit/test_lambda_notifier.py` | Unit tests for notifier Lambda |
| `requirements.txt` | Python dependencies (pytest, black, flake8, mypy, AWS CDK) |
| `.env.example` | Template for environment variables |

---

## Important Notes

- **src/common is the source of truth**: `src/layers/common/python/common/` is a symlink to `src/common/`. Always edit `src/common/` only; the symlink is automatically packaged into the Lambda layer during CDK synthesis.

- **Environment variables**: All AWS credentials and API keys must be in `.env`. The CDK reads from environment at deploy time.

- **Code style**: Black (100-char line length), flake8, mypy, and pylint are enforced in CI/CD. Run locally before committing.

- **Testing strategy**: Lambda tests mock AWS API calls (no actual deployments). Fixtures provide sample SNS events and DynamoDB records. Tests live in `tests/unit/` and `tests/integration/`.

- **Lambda layer packaging**: The layer is created from `src/layers/common/python/common/` and deployed with every stack update. It contains all imports from `src/common/`.

---

## Phases Overview

- **Phase 1** (Current): AWS infrastructure foundation (DynamoDB, S3, CloudFront, Lambda, SNS, budget alarms)
- **Phase 2**: Content ingestion pipeline (Apify web scraper + Claude API for Vietnamese captions)
- **Phase 3**: Image generation (fal.ai + Stable Diffusion)
- **Phase 4**: Dashboard (Streamlit) with compliance gates and human approval
- **Phase 5**: Content posting (Facebook, TikTok, Instagram via official APIs)
