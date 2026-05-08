# Healing Bedroom MVP - AI Content Pipeline

A Vietnamese AI-powered content curation and repurposing pipeline built with AWS CDK and Python. The project focuses on cost-conscious, serverless infrastructure to automate content ingestion, processing, and posting.

## 🏗️ Architecture Overview

The system is built on a serverless architecture using **AWS CDK (Python)**:
- **Database:** DynamoDB (`HealingBedroomContent`) for metadata and state tracking.
- **Storage:** S3 for image assets, served via **CloudFront** CDN.
- **Compute:** AWS Lambda (Python 3.12) for ingestion, processing, and notifications.
- **Configuration:** AWS Systems Manager Parameter Store for secrets and API keys.
- **Monitoring:** AWS Budgets with SNS-triggered Lambda alerts to Telegram.
- **Deployment:** Infrastructure-as-Code via CDK.

## 📁 Project Structure

```text
/
├── app.py              # CDK App entry point
├── cdk/                # Infrastructure definitions
│   └── stack.py        # Main CDK Stack (DynamoDB, S3, Lambda, etc.)
├── src/
│   ├── common/         # Shared utilities, config, and schemas
│   ├── lambdas/        # AWS Lambda function source code
│   │   └── notifier/   # Telegram notification service
│   └── layers/         # Shared Lambda layers (common utilities)
├── specs/              # Phase-based specifications and tasks
├── vault/              # Technical research and detailed specs
├── tests/              # pytest suite (unit and integration)
├── scripts/            # Utility scripts (python/bash)
├── .specify/           # Speckit framework configuration
└── .github/            # GitHub Actions and AI agent instructions
```

## 🚀 Building and Running

### Prerequisites
- Python 3.9+
- Node.js 18+ (for CDK CLI)
- AWS CLI configured with credentials

### Setup
```bash
# Initialize virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Infrastructure Commands
```bash
# Synthesize CloudFormation template
cdk synth

# Deploy infrastructure to AWS
cdk deploy

# Run unit tests (CDK assertions)
pytest tests/unit/test_cdk_stack.py
```

## 🛠️ Development Conventions

### Infrastructure-as-Code (CDK)
- Use **least-privilege** IAM roles for all Lambda functions.
- All core resources (DynamoDB, S3, etc.) should be tagged using `config.get_tags()`.
- Removal policies are set to `RETAIN` for data-bearing resources (DynamoDB, S3) and `DESTROY` for logs.

### Coding Standards
- **Python Version:** 3.12 for Lambda runtimes, 3.9+ for local development.
- **Formatting:** Use `black` for formatting and `flake8` for linting.
- **Type Hinting:** Use `mypy` for static type checking.
- **Configuration:** Centralized in `src/common/config.py`. Environment-specific values should be retrieved from environment variables or Parameter Store.

### Secrets Management
- **NEVER** hardcode API keys or secrets.
- Use **AWS SSM Parameter Store** (path: `/healing-bedroom/*`).
- Use `src.common.utils.get_parameter()` for secure retrieval in Lambda functions.

### Workflow & Documentation
- This project uses the **Speckit** framework for planning and task management.
- Check `specs/` for phase-specific `tasks.md` and `spec.md` before starting work.
- Research and design decisions are documented in the `vault/` directory.

## 📊 Current Status
- **Phase 1 (Infrastructure Foundation):** COMPLETE ✅
- **Phase 2 (Content Ingestion):** NEXT ⏳ (Apify scraper + Claude captioning)

<!-- SPECKIT START -->
For additional context about technologies to be used, project structure,
shell commands, and other important information, read the current plan
<!-- SPECKIT END -->
