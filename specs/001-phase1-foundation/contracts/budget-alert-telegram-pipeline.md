# Contract: CloudWatch Budget Alert to Telegram Message Pipeline

**Version**: 1.0  
**Date**: 2026-05-03  
**Scope**: Message schema and transformation pipeline from AWS Budget alerts → SNS → Lambda Notifier → Telegram

---

## Overview

Phase 1 cost monitoring pipeline:
1. AWS Budget triggers threshold breach (50% or 80%)
2. Budget publishes alert to SNS topic
3. SNS invokes Notifier Lambda
4. Notifier Lambda formats message and sends to Telegram via Bot API

This contract defines message schemas at each stage.

---

## Stage 1: AWS Budget Alert to SNS

**SNS Topic**: `arn:aws:sns:us-east-1:{account-id}:healing-bedroom-budget-alerts`

**Message Format** (SNS publish payload):

```json
{
  "MessageId": "a1b2c3d4-e5f6-4789-0123-456789abcdef",
  "TopicArn": "arn:aws:sns:us-east-1:123456789012:healing-bedroom-budget-alerts",
  "Message": "{\"budgetName\":\"HealingBedroom-Monthly-Budget\",\"budgetLimit\":40,\"budgetType\":\"COST\",\"timeUnit\":\"MONTHLY\",\"calculatedSpend\":20.45,\"calculatedSpendPercent\":51.125,\"thresholdLimit\":20,\"thresholdPercent\":50,\"notificationType\":\"ACTUAL\",\"status\":\"ALARM\",\"action\":[],\"actualSpend\":20.45,\"forecastedSpend\":null}",
  "Subject": "Alert: AWS Budgets Notification",
  "Timestamp": "2026-05-03T14:30:00Z",
  "SignatureVersion": "1",
  "Signature": "...(AWS SNS signature)..."
}
```

**Key Fields**:
- `budgetName`: Name of the AWS Budget ("HealingBedroom-Monthly-Budget")
- `budgetLimit`: Monthly budget cap (40 USD)
- `calculatedSpend`: Current month's cumulative spend (float, USD)
- `calculatedSpendPercent`: Percentage of budget spent (50–100)
- `thresholdPercent`: Threshold that triggered alert (50 or 80)
- `status`: "ALARM" (threshold breached) or "OK" (below threshold)
- `Timestamp`: ISO 8601 timestamp when alert was published

---

## Stage 2: SNS Message to Lambda Payload

**Lambda Event Payload** (after SNS deserialization):

```python
event = {
    "Records": [
        {
            "Sns": {
                "Message": "{...JSON string (see Stage 1)...}",
                "MessageAttributes": {
                    "Test": {"Type": "String", "Value": "False"},
                    "TokenId": {"Type": "Token", "Value": "d58c2694-712d-4423-b842-6bae87ed58db"}
                },
                "Subject": "Alert: AWS Budgets Notification",
                "TopicArn": "arn:aws:sns:us-east-1:123456789012:healing-bedroom-budget-alerts",
                "Timestamp": "2026-05-03T14:30:00.123Z",
                "Type": "Notification",
                "UnsubscribeURL": "..."
            }
        }
    ]
}
```

**Lambda Extraction Pattern**:

```python
import json
import boto3

def lambda_handler(event, context):
    """
    Receive SNS notification from AWS Budget alert.
    Parse alert details and send to Telegram.
    """
    try:
        # Extract SNS message
        sns_message_str = event['Records'][0]['Sns']['Message']
        alert_data = json.loads(sns_message_str)
        
        # Extract key fields
        budget_name = alert_data['budgetName']
        budget_limit = alert_data['budgetLimit']
        current_spend = alert_data['calculatedSpend']
        spend_percent = alert_data['calculatedSpendPercent']
        threshold_percent = alert_data['thresholdPercent']
        status = alert_data['status']
        
        print(f"Budget Alert: {budget_name} at {spend_percent}% of ${budget_limit}")
        
        # Send to Telegram (see Stage 3)
        send_telegram_alert(budget_name, budget_limit, current_spend, spend_percent, threshold_percent)
        
        return {"statusCode": 200, "body": "Alert sent to Telegram"}
    
    except Exception as e:
        print(f"Error processing budget alert: {str(e)}")
        return {"statusCode": 500, "body": str(e)}
```

---

## Stage 3: Lambda to Telegram Message

**Telegram Bot API Endpoint**: `https://api.telegram.org/bot{BOT_TOKEN}/sendMessage`

**HTTP Request**:

```
POST /bot{TELEGRAM_BOT_TOKEN}/sendMessage HTTP/1.1
Host: api.telegram.org
Content-Type: application/json
Content-Length: 437

{
  "chat_id": "-1001234567890",
  "text": "⚠️ AWS BUDGET ALERT\n\n💰 Budget: HealingBedroom-Monthly-Budget\n📊 Spent: $20.45 / $40.00 (51%)\n🚨 Threshold: 50% triggered\n⏰ Alert Time: 2026-05-03 14:30 UTC\n\nAction: Review cost-driving services and reduce if needed.",
  "parse_mode": "HTML"
}
```

**Response** (success):

```json
{
  "ok": true,
  "result": {
    "message_id": 12345,
    "date": 1714754400,
    "chat": {
      "id": -1001234567890,
      "type": "private"
    },
    "text": "⚠️ AWS BUDGET ALERT\n..."
  }
}
```

**Response** (error):

```json
{
  "ok": false,
  "error_code": 403,
  "description": "Bot was blocked by the user"
}
```

---

## Telegram Message Format

**Template**:

```
⚠️ AWS BUDGET ALERT

💰 Budget: {budget_name}
📊 Spent: ${current_spend:.2f} / ${budget_limit:.2f} ({spend_percent:.1f}%)
🚨 Threshold: {threshold_percent}% triggered
⏰ Alert Time: {timestamp}

Action: Review AWS Cost Explorer and identify cost-driving services.
```

**Example Output**:

```
⚠️ AWS BUDGET ALERT

💰 Budget: HealingBedroom-Monthly-Budget
📊 Spent: $20.45 / $40.00 (51.1%)
🚨 Threshold: 50% triggered
⏰ Alert Time: 2026-05-03 14:30 UTC

Action: Review AWS Cost Explorer and identify cost-driving services.
```

---

## Lambda Implementation Pattern

```python
import json
import boto3
import requests
from datetime import datetime

ssm_client = boto3.client('ssm')

def get_telegram_credentials():
    """Retrieve Telegram credentials from Parameter Store."""
    params = ssm_client.get_parameters(
        Names=[
            '/healing-bedroom/telegram-bot-token',
            '/healing-bedroom/telegram-chat-id'
        ]
    )
    params_dict = {p['Name'].split('/')[-1]: p['Value'] for p in params['Parameters']}
    return params_dict['telegram-bot-token'], params_dict['telegram-chat-id']

def send_telegram_message(bot_token, chat_id, message_text):
    """Send formatted message to Telegram."""
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message_text,
        "parse_mode": "HTML"
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        result = response.json()
        
        if result['ok']:
            print(f"✓ Message sent to Telegram (message_id: {result['result']['message_id']})")
            return True
        else:
            print(f"✗ Telegram API error: {result['description']}")
            return False
    except Exception as e:
        print(f"✗ Failed to send Telegram message: {str(e)}")
        return False

def lambda_handler(event, context):
    """Main handler for budget alert processing."""
    try:
        # Parse SNS event
        sns_message_str = event['Records'][0]['Sns']['Message']
        alert_data = json.loads(sns_message_str)
        
        # Extract budget details
        budget_name = alert_data.get('budgetName', 'Unknown')
        budget_limit = alert_data.get('budgetLimit', 0)
        current_spend = alert_data.get('calculatedSpend', 0)
        spend_percent = alert_data.get('calculatedSpendPercent', 0)
        threshold_percent = alert_data.get('thresholdPercent', 0)
        
        # Format timestamp
        timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')
        
        # Create message
        message = f"""⚠️ AWS BUDGET ALERT

💰 Budget: {budget_name}
📊 Spent: ${current_spend:.2f} / ${budget_limit:.2f} ({spend_percent:.1f}%)
🚨 Threshold: {threshold_percent}% triggered
⏰ Alert Time: {timestamp}

Action: Review AWS Cost Explorer and identify cost-driving services."""
        
        # Send to Telegram
        bot_token, chat_id = get_telegram_credentials()
        success = send_telegram_message(bot_token, chat_id, message)
        
        return {
            "statusCode": 200 if success else 500,
            "body": json.dumps({
                "success": success,
                "message": f"Budget alert: {spend_percent:.1f}% of ${budget_limit}"
            })
        }
    
    except Exception as e:
        print(f"Error in budget alert handler: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }
```

---

## Phase 1 Acceptance Testing

- [ ] Manually trigger AWS Budget alert in AWS console (set budget to low value like $5)
- [ ] Verify SNS publishes message to topic
- [ ] Verify Notifier Lambda is invoked
- [ ] Verify Telegram message received within 2 minutes with correct format and data
- [ ] Test error handling: block Telegram bot, verify error logged in CloudWatch
- [ ] Test 50% and 80% thresholds separately; verify both trigger alerts

---

## Error Handling & Retry Strategy

| Error | Cause | Lambda Behavior | Retry? |
|-------|-------|-----------------|--------|
| `ParameterNotFound` | Credentials missing | Log error, fail gracefully, alert to developer manually | No (manual intervention needed) |
| `Telegram API error 403` | Bot blocked by user or invalid chat ID | Log error, fail gracefully | No (manual intervention needed) |
| `Telegram API timeout` | Network latency | Retry up to 3 times with exponential backoff | Yes (1s, 2s, 4s) |
| `SNS message malformed` | Invalid JSON from Budget | Log error, fail gracefully | No (data issue, not transient) |

---

## Monitoring & Metrics

**CloudWatch Metrics**:
- `BudgetAlertNotificationsSent` (count): Successful Telegram messages sent
- `BudgetAlertNotificationFailures` (count): Failed Telegram sends
- `TelegramAPILatency` (ms): Time to send message to Telegram

**Alarms**:
- Alert if `BudgetAlertNotificationFailures > 0` in any 5-minute window (indicates credential or Telegram issue)
- Alert if `TelegramAPILatency > 5000ms` (indicates Telegram API degradation)

---

## Future Enhancements (Phase 2+)

- **Multi-Channel Alerts**: Send to Slack + email + SMS in addition to Telegram
- **Alert Aggregation**: If multiple thresholds breached, consolidate into single message
- **Budget Forecasting**: Include projected end-of-month spend in alert message
- **Remediation Actions**: Suggest cost-cutting actions based on high-cost services (Lambda, DynamoDB, etc.)
