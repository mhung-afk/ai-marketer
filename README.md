# Healing Bedroom MVP – AWS Infrastructure

> **Phase 1 Foundation**: Deploy core AWS infrastructure (DynamoDB, S3, CloudFront, Parameter Store, Budget Alarms) as code using AWS CDK to support the content pipeline.

**Status**: Phase 1 - Infrastructure Foundation (May 3–10, 2026)  
**Team**: Solo Developer  
**Budget**: $20/month  
**Deployed To**: AWS (ap-southeast-1)

---

## 🎯 Project Overview

The **Healing Bedroom MVP** is a Vietnamese AI-powered content curation and repurposing pipeline. Phase 1 foundation deploys all core AWS infrastructure required for phases 2–5:

- **Phase 1**: AWS infrastructure (DynamoDB, S3, CloudFront, Parameter Store, Budget Alarms) ← **YOU ARE HERE**
- **Phase 2**: Content ingestion pipeline (Apify web scraper + Anthropic Claude for Vietnamese captions)
- **Phase 3**: Image generation (fal.ai + Stable Diffusion)
- **Phase 4**: Dashboard (Streamlit) with compliance gates and human approval workflow
- **Phase 5**: Content posting (Facebook, TikTok, Instagram via official APIs)

**Key Principles**:
- ✅ **Infrastructure-as-Code**: All AWS resources defined in CDK (Python), version-controlled and reproducible
- ✅ **Cost-Conscious**: < $40/month with automatic budget alerts
- ✅ **Serverless**: No long-running servers; Lambda + managed services only
- ✅ **Secure**: API keys in Parameter Store, IAM least-privilege roles
- ✅ **Documented**: Every design decision justified; deployment fully automated

---

## 📋 Prerequisites

Before starting, ensure you have:

- **AWS Account** with credentials configured (`aws configure`)
- **Python 3.9+** installed locally
- **Node.js 18+** (for AWS CDK CLI)
- **Git** for version control
- **Telegram Bot Token** (create via [@BotFather](https://t.me/botfather))

### Verify Installation

```bash
# Check Python version
python --version     # Should be 3.9+

# Check AWS CLI
aws --version        # Should be AWS CLI 2.x

# Check Node.js
node --version       # Should be 18+

# Check Git
git --version        # Should be 2.x+
```

---

## 🚀 Quick Start (5 minutes)

### 1. Clone Repository

```bash
git clone https://github.com/mhung/healing-bedroom-mvp.git
cd healing-bedroom-mvp
```

### 2. Set Up Python Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate it
source venv/bin/activate    # macOS/Linux
# or
venv\Scripts\activate       # Windows

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Environment Variables

```bash
# Copy example to .env
cp .env.example .env

# Edit .env and fill in values
nano .env  # or use your preferred editor
```

**Required values**:
- `AWS_REGION`: us-east-1 (Phase 1)
- `AWS_ACCOUNT_ID`: Your 12-digit AWS account number
- `BUCKET_NAME_SUFFIX`: Unique suffix for S3 bucket (e.g., your username)
- `TELEGRAM_BOT_TOKEN`: From [@BotFather](https://t.me/botfather)
- `TELEGRAM_CHAT_ID`: Your Telegram user ID (send `/start` to [@userinfobot](https://t.me/userinfobot))

### 4. Deploy Infrastructure

```bash
# Validate CDK stack
cdk synth

# Deploy to AWS
cdk deploy --require-approval never

# Bootstrap for first run
cdk bootstrap

# Highly recommend
eval $(aws configure export-credentials --profile default --format env) && cdk deploy --require-approval never

# ✅ Infrastructure deployed! Check AWS console for new resources
```

### 5. Destroy Stack (when needed)

To safely remove all AWS resources:

```bash
# WARNING: This will delete all Phase 1 resources!
# - DynamoDB: HealingBedroomContent table
# - S3: healing-bedroom-images-* bucket (will be RETAINED due to data protection)
# - CloudFront distribution
# - IAM role, CloudWatch logs, SNS topic, Budget alarms

cdk destroy

# You will be prompted for confirmation before proceeding
```
