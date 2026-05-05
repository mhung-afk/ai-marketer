"""
AWS Lambda: Budget Alert Notifier

This Lambda function receives AWS Budget alerts via SNS and forwards them
to Telegram for real-time cost monitoring notifications.

Trigger: SNS topic `healing-bedroom-budget-alerts`
"""

import json
import logging
import os
import urllib.request
from datetime import datetime, timezone
from typing import Optional

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS Systems Manager client
ssm_client = boto3.client("ssm")

# Parameter Store parameter names
PARAM_TELEGRAM_BOT_TOKEN = "/healing-bedroom/telegram-bot-token"
PARAM_TELEGRAM_CHAT_ID = "/healing-bedroom/telegram-chat-id"

# AWS Region (set by Lambda runtime)
AWS_REGION = os.environ.get("AWS_REGION", "ap-southeast-1")

def get_parameter(parameter_name: str, with_decryption: bool = False) -> Optional[str]:
    try:
        response = ssm_client.get_parameter(
            Name=parameter_name,
            WithDecryption=with_decryption
        )
        value = response["Parameter"]["Value"]
        cleaned = str(value).strip()   # Aggressive strip
        
        logger.info(f"✅ Retrieved: {parameter_name}")
        
        return cleaned

    except Exception as e:
        logger.error(f"Failed to get parameter {parameter_name}: {e}")
        raise


def lambda_handler(event, context):
    """
    Handle SNS Budget alert and send Telegram notification.

    Args:
        event: Lambda event from SNS
        context: Lambda context

    Returns:
        Response with notification status
    """
    try:
        logger.info("Budget alert notification handler invoked")
        logger.info(f"Event: {json.dumps(event)}")

        # Extract SNS message
        sns_message = json.loads(event["Records"][0]["Sns"]["Message"])
        logger.info(f"SNS Message: {json.dumps(sns_message)}")

        # Retrieve Telegram credentials from Parameter Store
        try:
            telegram_token = get_parameter(PARAM_TELEGRAM_BOT_TOKEN, with_decryption=True)
            telegram_chat_id = get_parameter(PARAM_TELEGRAM_CHAT_ID)

            if not telegram_token or not telegram_chat_id:
                logger.error("❌ Telegram credentials not found in Parameter Store")
                return {
                    "statusCode": 500,
                    "body": json.dumps({
                        "error": "Telegram credentials not configured"
                    })
                }

        except Exception as e:
            logger.error(f"❌ Failed to retrieve Telegram credentials: {e}")
            return {
                "statusCode": 500,
                "body": json.dumps({
                    "error": f"Failed to retrieve credentials: {str(e)}"
                })
            }

        # Parse budget alert data
        notification_type = sns_message.get("notificationType", "UNKNOWN")
        subscriptionName = sns_message.get("budgetName", "HealingBedroom Budget")
        threshold = sns_message.get("trigger", {}).get("threshold", "UNKNOWN")
        threshold_type = sns_message.get("trigger", {}).get("thresholdType", "UNKNOWN")
        actual_amount = sns_message.get("current", {}).get("amount", "UNKNOWN")
        max_amount = sns_message.get("max", {}).get("amount", "UNKNOWN")
        unit = sns_message.get("current", {}).get("unit", "USD")

        # Format message for Telegram
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

        message = f"""
🚨 **Budget Alert**

📊 Budget: {subscriptionName}
💰 Current Spend: {actual_amount} {unit}
📈 Budget Limit: {max_amount} {unit}
⚠️  Alert Threshold: {threshold}% ({threshold_type})

🕐 Timestamp: {timestamp}
🌍 Region: {AWS_REGION}

Actions:
1. Review AWS Cost Explorer: https://console.aws.amazon.com/cost-management/
2. Check CloudWatch Logs: /aws/lambda/healing-bedroom
3. View detailed budget info: https://console.aws.amazon.com/budgets/

Please investigate and take action if spending is unexpected.
"""

        # Send to Telegram
        try:
            send_telegram_message(
                token=telegram_token,
                chat_id=telegram_chat_id,
                message=message.strip()
            )

            logger.info("✅ Budget alert sent to Telegram successfully")

            return {
                "statusCode": 200,
                "body": json.dumps({
                    "message": "Budget alert notification sent to Telegram",
                    "threshold": threshold,
                    "actual_amount": actual_amount,
                })
            }

        except Exception as e:
            logger.error(f"❌ Failed to send Telegram message: {e}")
            return {
                "statusCode": 500,
                "body": json.dumps({
                    "error": f"Failed to send Telegram message: {str(e)}"
                })
            }

    except Exception as e:
        logger.error(f"❌ Unexpected error in budget notifier: {e}", exc_info=True)
        return {
            "statusCode": 500,
            "body": json.dumps({
                "error": f"Unexpected error: {str(e)}"
            })
        }

def send_telegram_message(token, chat_id, message):
    """Final robust version"""
    # Aggressive cleaning
    token = str(token).strip()
    chat_id = str(chat_id).strip()
    
    # Remove any invisible characters
    import re
    token = re.sub(r'[\s\n\r\t]+', '', token)

    url = f"https://api.telegram.org/bot{token}/sendMessage"

    payload = {
        "chat_id": chat_id,
        "text": message.strip()
    }

    logger.info(f"📤 Sending to chat_id: {chat_id}")
    data = json.dumps(payload).encode("utf-8")

    try:
        req = urllib.request.Request(
            url=url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        with urllib.request.urlopen(req, timeout=15) as response:
            result = json.loads(response.read().decode("utf-8"))
            logger.info(f"✅ Telegram Success: {result}")
            return result

    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        logger.error(f"❌ Telegram HTTP Error {e.code}: {error_body}")
        raise Exception(f"Telegram HTTP error: {e.code} - {error_body}")
        
    except Exception as e:
        logger.error(f"❌ Telegram request failed: {e}", exc_info=True)
        raise
