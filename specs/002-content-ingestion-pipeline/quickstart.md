# Phase 2 Quickstart Guide: Content Ingestion Pipeline

**Date**: 2026-05-06 | **Estimated Setup Time**: 30–45 minutes  
**Status**: Complete | **Audience**: Developers implementing Phase 2

## Prerequisites

✅ Phase 1 infrastructure deployed and verified:
- DynamoDB table `HealingBedroomContent` exists
- S3 bucket `healing-bedroom-images-ai-marketer` exists with CloudFront distribution
- Parameter Store has Telegram bot credentials
- Lambda Layer `healing-bedroom-common` deployed
- Lambda IAM role `lambda-healing-bedroom-role` created

✅ AWS CLI configured with credentials for `ap-southeast-1`

✅ Python 3.9+ virtual environment activated

✅ Apify API token available (from console.apify.com)

✅ Anthropic Claude API key available (from console.anthropic.com)

---

## Step 1: Extend shared configuration

### Update `src/common/config.py`

Add Phase 2 specific configuration:

```python
# ============================================================================
# Phase 2: Content Ingestion Pipeline
# ============================================================================
INGESTION_SCHEDULE_CRON = os.getenv("INGESTION_SCHEDULE_CRON", "0 */6 * * ? *")  # Every 6 hours

SOURCES_CONFIG = {
    "tiktok": {
        "actor_id": "apify/tiktok-scraper",
        "hashtags": ["healingbedroom", "bedroomdecor", "asmr", "cozybedroom"],
        "max_items": 5,
    },
    "instagram": {
        "actor_id": "apify/instagram-scraper",
        "hashtags": ["healingbedroom", "bedroomdecor", "asmr", "cozyroom"],
        "max_items": 5,
    },
    "facebook": {
        "actor_id": "apify/facebook-pages-scraper",
        "page_ids": ["therapeutic-bedding", "bedroom-aesthetics"],
        "max_items": 5,
    }
}

SQS_DLQ_NAME = "healing-bedroom-ingestion-dlq"
DEAD_LETTER_QUEUE_URL = os.getenv("DEAD_LETTER_QUEUE_URL", "")

# Claude Prompt (hardcoded for Phase 2 MVP)
CLAUDE_SYSTEM_PROMPT = """You are a Vietnamese content creator specializing in calming, wellness-focused bedroom aesthetics. Your captions are natural, poetic, and optimized for Instagram/TikTok engagement.

Brand Guidelines:
- Tone: Peaceful, aspirational, wellness-focused, no hard selling
- Style: Poetic, minimalist descriptions of bedroom ambiance
- Hashtags: 3-5 relevant tags per caption
- Word count: 50-100 Vietnamese words max

Respond ONLY with:
1. Vietnamese caption (50-100 words)
2. Line break
3. Hashtags (e.g., #cozybedroom #aesthetic #sleep)

Do NOT include explanations, notes, or formatting beyond the caption and hashtags."""
```

---

## Step 2: Add Pydantic schemas to shared layer

### Update `src/common/schemas.py`

Add ContentItem and IngestionRun models (see [data-model.md](data-model.md) for complete schema):

```python
from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any
from enum import Enum
from datetime import datetime
from uuid import uuid4

class SourcePlatform(str, Enum):
    TIKTOK = "tiktok"
    INSTAGRAM = "instagram"
    FACEBOOK = "facebook"

class ContentStatus(str, Enum):
    RAW = "RAW"
    APPROVED = "APPROVED"
    PUBLISHED = "PUBLISHED"
    REJECTED = "REJECTED"
    ERROR = "ERROR"

class ContentItem(BaseModel):
    item_id: str = Field(default_factory=lambda: str(uuid4()))
    source_platform: SourcePlatform
    source_url: str
    original_caption: str
    ai_caption_vi: Optional[str] = None
    s3_image_key: Optional[str] = None
    cloudfront_url: Optional[str] = None
    content_hash: Optional[str] = None
    status: ContentStatus = ContentStatus.RAW
    created_at: datetime = Field(default_factory=datetime.utcnow)
    processed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        use_enum_values = True
```

---

## Step 3: Create ingestion Lambda handler structure

### Create `src/lambdas/ingestion/` directory

```bash
mkdir -p src/lambdas/ingestion
touch src/lambdas/ingestion/__init__.py
touch src/lambdas/ingestion/lambda_function.py
touch src/lambdas/ingestion/apify_client.py
touch src/lambdas/ingestion/claude_caption_generator.py
touch src/lambdas/ingestion/image_processor.py
touch src/lambdas/ingestion/deduplication.py
touch src/lambdas/ingestion/error_handlers.py
```

### Minimal `src/lambdas/ingestion/lambda_function.py`

```python
"""
AWS Lambda: Content Ingestion Pipeline

Scrapes images from social media via Apify, generates Vietnamese captions via Claude,
stores results in DynamoDB with CloudFront URLs for downstream approval workflows.

Trigger: EventBridge Scheduler (6–12 hour interval)
"""

import json
import logging
import sys
import os

# Lambda Layer import
sys.path.insert(0, "/var/task")
from src.common.config import SOURCES_CONFIG, AWS_REGION
from src.common.utils import generate_item_id
from src.lambdas.ingestion.apify_client import ApifyClient
from src.lambdas.ingestion.claude_caption_generator import CaptionGenerator
from src.lambdas.ingestion.image_processor import ImageProcessor
from src.lambdas.ingestion.error_handlers import ErrorHandler

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    """
    Main ingestion Lambda handler.
    
    Returns:
        {
            "statusCode": 200,
            "body": {
                "total_processed": int,
                "successful": int,
                "failed": int,
                "duplicates_skipped": int
            }
        }
    """
    logger.info(f"🚀 Ingestion pipeline started. Event: {json.dumps(event)}")
    
    stats = {
        "total_processed": 0,
        "successful": 0,
        "failed": 0,
        "duplicates_skipped": 0
    }
    
    try:
        apify = ApifyClient()
        claude = CaptionGenerator()
        image_proc = ImageProcessor()
        error_handler = ErrorHandler()
        
        # Process each configured source
        for platform, config in SOURCES_CONFIG.items():
            logger.info(f"📱 Processing platform: {platform}")
            
            try:
                # 1. Scrape via Apify
                items = apify.scrape(platform, config)
                logger.info(f"✅ Scraped {len(items)} items from {platform}")
                
                # 2. Process each item
                for item in items:
                    stats["total_processed"] += 1
                    
                    try:
                        # 3. Check for duplicates
                        is_dup, dup_id = image_proc.check_duplicate(item)
                        if is_dup:
                            stats["duplicates_skipped"] += 1
                            logger.info(f"⏭️  Skipped duplicate: {item['url']}")
                            continue
                        
                        # 4. Generate caption
                        caption_vi = claude.generate(item['caption'], platform)
                        
                        # 5. Upload image + generate CloudFront URL
                        image_data = image_proc.process_image(item['image_url'])
                        
                        # 6. Store in DynamoDB
                        # [Implementation in src/lambdas/ingestion/lambda_function.py]
                        
                        stats["successful"] += 1
                        logger.info(f"✅ Processed: {item['url']}")
                        
                    except Exception as e:
                        stats["failed"] += 1
                        logger.error(f"❌ Failed to process item: {str(e)}")
                        error_handler.move_to_dlq(item, str(e))
            
            except Exception as e:
                logger.error(f"❌ Platform {platform} failed: {str(e)}")
                error_handler.send_alert(f"Apify error on {platform}: {str(e)}")
        
        logger.info(f"✅ Ingestion complete. Stats: {json.dumps(stats)}")
        
        return {
            "statusCode": 200,
            "body": json.dumps(stats)
        }
    
    except Exception as e:
        logger.error(f"❌ Unexpected error in ingestion: {str(e)}", exc_info=True)
        error_handler.send_alert(f"Critical ingestion error: {str(e)}")
        
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }
```

---

## Step 4: Extend CDK Stack with Phase 2 resources

### Update `cdk/stack.py`

Add EventBridge Scheduler, Lambda ingestion, SQS dead-letter queue:

```python
# In HealingBedroomStack.__init__()

# 1. Create SQS dead-letter queue
self.ingestion_dlq = sqs.Queue(
    self, "IngestionDLQ",
    queue_name="healing-bedroom-ingestion-dlq",
    retention_period=Duration.days(4),
    visibility_timeout=Duration.seconds(300)
)

# 2. Create Lambda ingestion function
self.ingestion_lambda = lambda_.Function(
    self, "IngestionLambda",
    runtime=lambda_.Runtime.PYTHON_3_12,
    handler="src.lambdas.ingestion.lambda_function.lambda_handler",
    code=lambda_.Code.from_asset("."),
    timeout=Duration.minutes(15),
    memory_size=512,
    role=self.lambda_role,  # Reuse Phase 1 role
    layers=[self.shared_layer],
    environment={
        "AWS_REGION": self.region,
        "DEAD_LETTER_QUEUE_URL": self.ingestion_dlq.queue_url,
        "ENVIRONMENT_NAME": "phase2"
    }
)

# Grant DLQ permissions
self.ingestion_dlq.grant_send_messages(self.ingestion_lambda)

# 3. Create EventBridge Scheduler rule
from aws_cdk import aws_scheduler as scheduler

rule = scheduler.CfnScheduleGroup(
    self, "IngestionScheduleGroup",
    name="healing-bedroom-ingestion-group"
)

scheduler.CfnSchedule(
    self, "IngestionSchedule",
    schedule_expression=f"cron({config.INGESTION_SCHEDULE_CRON})",
    target=scheduler.CfnSchedule.Target(
        arn=self.ingestion_lambda.function_arn,
        role_arn=scheduler_role.role_arn  # Create minimal role for scheduler
    ),
    flexible_time_window=scheduler.CfnSchedule.FlexibleTimeWindowProperty(mode="OFF")
)

# Update Lambda role to include SQS + DynamoDB extended permissions
self.lambda_role.add_to_policy(iam.PolicyStatement(
    actions=["sqs:SendMessage"],
    resources=[self.ingestion_dlq.queue_arn]
))

self.lambda_role.add_to_policy(iam.PolicyStatement(
    actions=["dynamodb:Query"],
    resources=[f"{self.dynamodb_table.table_arn}/index/GSI_ContentHash"]
))
```

---

## Step 5: Install dependencies

### Update `requirements.txt`

```txt
aws-cdk-lib==2.139.0
boto3==1.28.0
apify-client==1.4.0
anthropic==0.7.8
pydantic==2.4.0
requests==2.31.0
Pillow==10.0.0
```

### Install

```bash
pip install -r requirements.txt
```

---

## Step 6: Update Parameter Store with Phase 2 secrets

### Create Apify API token parameter

```bash
aws ssm put-parameter \
  --name /healing-bedroom/apify-api-token \
  --value "YOUR_APIFY_API_TOKEN" \
  --type "SecureString" \
  --region ap-southeast-1 \
  --overwrite
```

### Create Anthropic API key parameter

```bash
aws ssm put-parameter \
  --name /healing-bedroom/anthropic-api-key \
  --value "YOUR_ANTHROPIC_API_KEY" \
  --type "SecureString" \
  --region ap-southeast-1 \
  --overwrite
```

### Verify parameters

```bash
aws ssm describe-parameters --region ap-southeast-1 | grep healing-bedroom
```

---

## Step 7: Deploy via CDK

### Validate

```bash
cd cdk
cdk synth
```

### Deploy

```bash
cdk deploy --require-approval never
```

✅ CloudFormation stack creates:
- Lambda ingestion function
- EventBridge Scheduler
- SQS dead-letter queue
- Updated DynamoDB GSI (content_hash)

---

## Step 8: Manual Testing

### Trigger Lambda Manually

```bash
aws lambda invoke \
  --function-name healing-bedroom-ingestion \
  --payload '{}' \
  --region ap-southeast-1 \
  /tmp/response.json

cat /tmp/response.json
```

### Verify DynamoDB

```bash
aws dynamodb query \
  --table-name HealingBedroomContent \
  --index-name GSI1_Status \
  --key-condition-expression "status = :status" \
  --expression-attribute-values '{":status":{"S":"RAW"}}' \
  --region ap-southeast-1
```

### Check CloudFront URLs

```bash
# Get a processed item
ITEM_ID=$(aws dynamodb query \
  --table-name HealingBedroomContent \
  --key-condition-expression "item_id = :id" \
  --expression-attribute-values '{":id":{"S":"<item_id>"}}' \
  --region ap-southeast-1 \
  --query 'Items[0].cloudfront_url' \
  --output text)

# Verify URL is accessible
curl -I $ITEM_ID
```

### Monitor CloudWatch Logs

```bash
aws logs tail /aws/lambda/healing-bedroom-ingestion --follow --region ap-southeast-1
```

---

## Step 9: Verify Success Metrics

### Checklist

- [ ] Lambda function deployed and triggered
- [ ] ≥ 1 item in DynamoDB with `status = RAW`
- [ ] CloudFront URLs are publicly accessible (HTTP 200)
- [ ] Vietnamese captions populated in `ai_caption_vi`
- [ ] `content_hash` populated for deduplication
- [ ] Telegram alert on first successful run
- [ ] No items in SQS dead-letter queue (on first successful run)

### Expected Output

```
✅ Scraped 5 TikTok items
✅ Scraped 5 Instagram items
✅ Scraped 3 Facebook items
✅ 13 items processed
✅ 0 duplicates
✅ 0 failures
✅ All CloudFront URLs accessible
✅ All Vietnamese captions generated
```

---

## Step 10: Operational Monitoring

### View Ingestion Metrics

```bash
aws cloudwatch get-metric-statistics \
  --namespace "AWS/Lambda" \
  --metric-name Duration \
  --dimensions Name=FunctionName,Value=healing-bedroom-ingestion \
  --start-time 2026-05-06T00:00:00Z \
  --end-time 2026-05-07T00:00:00Z \
  --period 3600 \
  --statistics Average,Maximum \
  --region ap-southeast-1
```

### Check Dead-Letter Queue

```bash
aws sqs receive-message \
  --queue-url $(aws sqs get-queue-url --queue-name healing-bedroom-ingestion-dlq \
    --region ap-southeast-1 --query QueueUrl --output text) \
  --max-number-of-messages 10 \
  --region ap-southeast-1
```

### Telegram Alerts

- **On Success**: "✅ Ingestion complete: X items processed, Y duplicates, Z failures"
- **On Failure**: "❌ Ingestion failed: [error detail]"

---

## Troubleshooting

### Issue: Lambda timeout

**Symptom**: `Task timed out after 900 seconds`

**Solution**:
1. Increase Lambda timeout (currently 15 min)
2. Reduce max_items per source in SOURCES_CONFIG
3. Check Apify/Claude API latency

### Issue: Apify rate limit

**Symptom**: `403 Rate limit exceeded`

**Solution**:
1. Wait 60+ seconds; Lambda will retry
2. Pre-negotiate higher quota with Apify
3. Reduce hashtag targets per source

### Issue: Claude API failures

**Symptom**: `anthropic.RateLimitError` or `anthropic.AuthenticationError`

**Solution**:
1. If auth error: rotate PARAM_ANTHROPIC_API_KEY in Parameter Store
2. If rate limit: exponential backoff will retry (up to 3x)
3. Check Anthropic console for quota status

### Issue: S3 upload fails

**Symptom**: `NoSuchBucket` or `AccessDenied`

**Solution**:
1. Verify bucket exists: `aws s3 ls healing-bedroom-images-ai-marketer`
2. Check IAM role has S3 permissions
3. Verify bucket policy allows CloudFront OAC

### Issue: No Telegram alerts

**Symptom**: No alerts in Telegram despite errors

**Solution**:
1. Verify Telegram credentials: `aws ssm get-parameter --name /healing-bedroom/telegram-bot-token`
2. Test Telegram connectivity: `python scripts/python/test-telegram-alert.py`
3. Check SNS topic permissions

---

## Next Steps

1. Run Phase 2 Lambda manually 3+ times over 24 hours
2. Verify ≥ 70% caption quality subjectively (10-item sample)
3. Proceed to Phase 3 (Approval Dashboard + Publishing)

---

**Quickstart Completed**: 2026-05-06  
**Estimated Setup Time**: 30–45 minutes  
**Status**: Ready for Phase 2 implementation  
**Support**: See [plan.md](plan.md) for architecture; see [research.md](research.md) for API details
