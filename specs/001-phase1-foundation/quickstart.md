# Quickstart: Phase 1 Foundation – AWS Infrastructure Deployment

**Date**: 2026-05-03  
**Target**: Solo developer deploying Phase 1 CDK stack  
**Estimated Time**: 30–45 minutes (including AWS account setup and testing)  
**Prerequisites**: AWS CLI configured, Python 3.9+, AWS CDK installed

---

## Prerequisites Checklist

Before starting, ensure you have:

- [ ] AWS account created and CLI credentials configured (`aws configure`)
- [ ] Python 3.9+ installed (`python3 --version`)
- [ ] Node.js 14+ installed (required for AWS CDK)
- [ ] AWS CDK v2 installed (`npm install -g aws-cdk`)
- [ ] Git and repository cloned (`git clone ...`)
- [ ] API keys obtained (Anthropic, fal.ai, Telegram Bot token)
- [ ] Telegram bot created via @BotFather (save token and chat ID)

**Verify AWS credentials**:
```bash
aws sts get-caller-identity
# Should output: Account ID, ARN, UserId
```

---

## Step 1: Repository Setup (5 minutes)

### 1.1 Clone the repository
```bash
git clone https://github.com/{your-org}/healing-bedroom-mvp.git
cd healing-bedroom-mvp
git checkout 001-phase1-foundation
```

### 1.2 Create Python virtual environment
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 1.3 Install dependencies
```bash
pip install -r requirements.txt
# Key dependencies: aws-cdk-lib, constructs, boto3
```

### 1.4 Verify CDK installation
```bash
cdk --version
# Should output: X.X.X
```

---

## Step 2: Configure Environment (5 minutes)

### 2.1 Copy environment template
```bash
cp .env.example .env
```

### 2.2 Edit `.env` with your AWS region and budget
```bash
# .env
AWS_REGION=us-east-1
AWS_ACCOUNT_ID=123456789012  # Your AWS account ID (from Step 1)
BUDGET_LIMIT_USD=40
S3_BUCKET_SUFFIX=${USER}  # Use your username for unique bucket name
```

### 2.3 Load environment variables
```bash
source .env
```

### 2.4 Verify AWS CDK can bootstrap (first-time setup)
```bash
cdk bootstrap aws://${AWS_ACCOUNT_ID}/${AWS_REGION}
# This creates CDKToolkit resources in your AWS account (one-time)
```

---

## Step 3: Deploy Infrastructure (10 minutes)

### 3.1 Synthesize CDK stack
```bash
cdk synth
# Generates CloudFormation template; verify no errors
```

### 3.2 Review planned changes
```bash
cdk diff
# Shows what will be created/modified; review carefully
```

### 3.3 Deploy stack
```bash
cdk deploy
# Prompts for confirmation; type 'y' and press Enter
# Deployment takes ~5–10 minutes
```

**Expected output**:
```
HealingBedroomStack: deploying... [1/1]
HealingBedroomStack: creating CloudFormation changeset...
[████████████████████] (X/X) Progress

 ✓ HealingBedroomStack

Stack ARN: arn:aws:cloudformation:us-east-1:123456789012:stack/HealingBedroomStack/...

Outputs:
  HealingBedroomStack.DynamoDBTableName = HealingBedroomContent
  HealingBedroomStack.S3BucketName = healing-bedroom-images-{user}
  HealingBedroomStack.CloudFrontDomain = d123abc.cloudfront.net
  HealingBedroomStack.ParameterStorePrefix = /healing-bedroom
```

### 3.4 Verify deployment
```bash
# Check DynamoDB table
aws dynamodb describe-table --table-name HealingBedroomContent --region ${AWS_REGION}

# Check S3 bucket
aws s3 ls s3://healing-bedroom-images-${USER}/ --region ${AWS_REGION}

# Check CloudFront distribution (takes ~15–20 minutes to fully activate)
aws cloudfront list-distributions --region ${AWS_REGION}
```

---

## Step 4: Store API Keys in Parameter Store (5 minutes)

### 4.1 Store Anthropic API key
```bash
aws ssm put-parameter \
  --name "/healing-bedroom/anthropic-api-key" \
  --value "sk-ant-..." \
  --type "String" \
  --overwrite \
  --region ${AWS_REGION}
```

### 4.2 Store fal.ai key
```bash
aws ssm put-parameter \
  --name "/healing-bedroom/fal-ai-key" \
  --value "fal_..." \
  --type "String" \
  --overwrite \
  --region ${AWS_REGION}
```

### 4.3 Store Telegram Bot Token
```bash
aws ssm put-parameter \
  --name "/healing-bedroom/telegram-bot-token" \
  --value "123456789:ABCdefGHIjklMNOpqrsTUVwxyz" \
  --type "String" \
  --overwrite \
  --region ${AWS_REGION}
```

### 4.4 Store Telegram Chat ID
```bash
aws ssm put-parameter \
  --name "/healing-bedroom/telegram-chat-id" \
  --value "-1001234567890" \
  --type "String" \
  --overwrite \
  --region ${AWS_REGION}
```

### 4.5 Verify parameters stored
```bash
aws ssm get-parameters \
  --names /healing-bedroom/anthropic-api-key /healing-bedroom/telegram-bot-token \
  --region ${AWS_REGION}
```

---

## Step 5: Create and Test Budget Alarm (5 minutes)

### 5.1 Create AWS Budget (if not already created by CDK)
```bash
aws budgets create-budget \
  --account-id ${AWS_ACCOUNT_ID} \
  --budget file://budget-config.json \
  --notifications-with-subscribers file://budget-notifications.json

# See budget-config.json and budget-notifications.json templates in /scripts/
```

### 5.2 Verify Budget created
```bash
aws budgets describe-budgets --account-id ${AWS_ACCOUNT_ID}
```

### 5.3 Test budget alert (optional, manual)
- Go to AWS Console → AWS Budgets → Select budget
- Manually trigger alert (or set budget to $5 to trigger organically)
- Verify Telegram message received

---

## Step 6: Test Infrastructure Components (10 minutes)

### 6.1 Test DynamoDB (Create & Query)
```bash
# Create test item
aws dynamodb put-item \
  --table-name HealingBedroomContent \
  --item '{
    "item_id": {"S": "550e8400-e29b-41d4-a716-446655440000"},
    "status": {"S": "RAW"},
    "created_at": {"S": "2026-05-03T14:30:00Z"},
    "niche": {"S": "healing-bedroom"}
  }' \
  --region ${AWS_REGION}

# Query table
aws dynamodb get-item \
  --table-name HealingBedroomContent \
  --key '{"item_id": {"S": "550e8400-e29b-41d4-a716-446655440000"}}' \
  --region ${AWS_REGION}
```

### 6.2 Test S3 (Upload & Verify)
```bash
# Create test file
echo "test image content" > test.jpg

# Upload to S3
aws s3 cp test.jpg s3://healing-bedroom-images-${USER}/test.jpg --region ${AWS_REGION}

# List S3 objects
aws s3 ls s3://healing-bedroom-images-${USER}/ --region ${AWS_REGION}
```

### 6.3 Test CloudFront (Access image via public URL)
**Note**: CloudFront takes 15–20 minutes to activate. After activation:

```bash
# Get CloudFront domain from CDK outputs
CLOUDFRONT_DOMAIN=$(cdk list --outputs | grep CloudFrontDomain | cut -d'=' -f2)

# Access image via CloudFront (replace domain)
curl -I https://${CLOUDFRONT_DOMAIN}/test.jpg

# Should return: HTTP/1.1 200 OK with cache headers
```

### 6.4 Test Lambda IAM Role
```bash
# Create test Lambda function (optional, for verification)
# Lambda should be able to:
# - Read/write DynamoDB
# - Read/write S3
# - Read Parameter Store
# - Write to CloudWatch Logs

# See Step 7 for test Lambda code
```

### 6.5 Test Parameter Store Access
```bash
# Create test Lambda that retrieves a parameter
# See contracts/parameter-store-interface.md for Lambda code example
```

---

## Step 7: Deploy Test Lambda (Optional, for Notifier Verification)

### 7.1 Create test Lambda function
Create `src/lambdas/notifier/lambda_function.py`:

```python
import json
import boto3

ssm_client = boto3.client('ssm')

def lambda_handler(event, context):
    try:
        # Test retrieving from Parameter Store
        response = ssm_client.get_parameter(
            Name='/healing-bedroom/telegram-bot-token'
        )
        token = response['Parameter']['Value']
        
        print(f"✓ Successfully retrieved Parameter Store value")
        
        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'Parameter Store access verified'})
        }
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
```

### 7.2 Deploy test Lambda
```bash
# Package Lambda
zip -j notifier.zip src/lambdas/notifier/lambda_function.py

# Create function (if not created by CDK)
aws lambda create-function \
  --function-name healing-bedroom-notifier \
  --runtime python3.11 \
  --role arn:aws:iam::${AWS_ACCOUNT_ID}:role/lambda-healing-bedroom-role \
  --handler lambda_function.lambda_handler \
  --zip-file fileb://notifier.zip \
  --region ${AWS_REGION}
```

### 7.3 Invoke test Lambda
```bash
aws lambda invoke \
  --function-name healing-bedroom-notifier \
  --region ${AWS_REGION} \
  response.json

cat response.json
# Should show: {"statusCode": 200, "body": "{\"message\": \"Parameter Store access verified\"}"}
```

### 7.4 Check Lambda logs
```bash
aws logs tail /aws/lambda/healing-bedroom-notifier --follow --region ${AWS_REGION}
```

---

## Step 8: Verify Budget Alerts & Telegram Integration (5 minutes)

### 8.1 Manually test Telegram notification
```bash
# Get Telegram credentials from Parameter Store
BOT_TOKEN=$(aws ssm get-parameter --name /healing-bedroom/telegram-bot-token --query 'Parameter.Value' --output text --region ${AWS_REGION})
CHAT_ID=$(aws ssm get-parameter --name /healing-bedroom/telegram-chat-id --query 'Parameter.Value' --output text --region ${AWS_REGION})

# Send test message via curl
curl -X POST "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" \
  -d "chat_id=${CHAT_ID}" \
  -d "text=✓ Phase 1 infrastructure deployed successfully!"

# Verify message received in Telegram
```

### 8.2 Monitor CloudWatch Logs
```bash
# Watch all Lambda logs
aws logs tail /aws/lambda/healing-bedroom-notifier --follow --region ${AWS_REGION}

# Watch SNS notifications
# (visible in AWS console → SNS → Topics → healing-bedroom-budget-alerts)
```

---

## Step 9: Verify Cost (5 minutes)

### 9.1 Check AWS Cost Explorer
```bash
# Go to AWS Console → Cost Management → Cost Explorer
# Filter: Service = "DynamoDB" + "S3" + "CloudFront"
# Time: Last 7 days
# Should show: < $5 for Phase 1 setup
```

### 9.2 Check budget status
```bash
aws budgets describe-budgets --account-id ${AWS_ACCOUNT_ID}
```

### 9.3 Review CloudWatch metrics
```bash
# DynamoDB consumed read/write units
aws cloudwatch get-metric-statistics \
  --namespace AWS/DynamoDB \
  --metric-name ConsumedReadCapacityUnits \
  --dimensions Name=TableName,Value=HealingBedroomContent \
  --start-time 2026-05-03T00:00:00Z \
  --end-time 2026-05-03T23:59:59Z \
  --period 3600 \
  --statistics Sum \
  --region ${AWS_REGION}
```

---

## Step 10: Cleanup & Next Steps (Optional)

### 10.1 To destroy all resources (and stop incurring costs)
```bash
cdk destroy
# Prompts for confirmation; type 'y'
# Warning: This deletes all Phase 1 infrastructure
```

### 10.2 Next steps after Phase 1
1. Proceed to Phase 2: Ingestion layer (Apify scrapers, DynamoDB ingestion Lambda)
2. Set up GitHub Actions for automated deployments
3. Begin Phase 3: AI processor (Claude Haiku, image generation)
4. Monitor costs weekly via AWS Cost Explorer

---

## Troubleshooting

### Issue: `cdk bootstrap` fails
**Solution**: Ensure AWS credentials are configured and account ID is correct
```bash
aws sts get-caller-identity
# Copy Account ID and verify in .env
```

### Issue: CloudFront takes > 20 minutes to activate
**Solution**: This is normal for AWS CloudFront. Check status via AWS console.

### Issue: Parameter Store put-parameter fails with "AccessDenied"
**Solution**: Ensure your AWS user/role has `ssm:PutParameter` permission

### Issue: DynamoDB query returns no items
**Solution**: Verify item was created successfully; check table name and region

### Issue: Telegram message not received
**Solution**: 
1. Verify bot token and chat ID are correct
2. Check Lambda logs: `aws logs tail /aws/lambda/healing-bedroom-notifier`
3. Manually test Telegram API with curl (see Step 8.1)

### Issue: S3 bucket creation fails - bucket name already exists
**Solution**: Bucket names are globally unique; use different suffix (BUCKET_SUFFIX env var)
```bash
export S3_BUCKET_SUFFIX=myname-2
cdk deploy
```

---

## Success Criteria Verification Checklist

- [ ] CDK deployed successfully without errors
- [ ] DynamoDB table created with correct schema (item_id, status, created_at)
- [ ] S3 bucket created with lifecycle policy (delete after 7 days)
- [ ] CloudFront distribution active (can access test image via HTTPS)
- [ ] Parameter Store contains 4 parameters (`/healing-bedroom/*`)
- [ ] Lambda can read Parameter Store without errors
- [ ] AWS Budget created with $40 limit and thresholds at 50% and 80%
- [ ] Budget alert triggered → SNS → Lambda → Telegram message received
- [ ] CloudWatch Logs capture all Lambda executions
- [ ] Infrastructure cost < $5 for Phase 1 setup period

---

## Performance Targets (Phase 1)

| Metric | Target | Actual |
|--------|--------|--------|
| CDK deployment time | < 10 minutes | ___ |
| CloudFront activation time | 15–20 minutes | ___ |
| DynamoDB query latency | < 100ms | ___ |
| Parameter Store retrieval | < 100ms | ___ |
| Telegram notification delivery | < 2 minutes | ___ |
| Infrastructure cost (24h) | < $1 | ___ |

---

## Documentation & Decision Tracking

All major decisions are documented in:
- **spec.md** – Feature specification
- **plan.md** – Implementation plan
- **research.md** – Technical research & rationale
- **data-model.md** – DynamoDB schema
- **contracts/** – External interface contracts

For Phase 2+ enhancements or questions, refer to these documents first.
