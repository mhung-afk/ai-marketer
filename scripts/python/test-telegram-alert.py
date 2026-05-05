#!/usr/bin/env python3
"""
Telegram Budget Alert Test Script

This script simulates a budget alert and invokes the Lambda Notifier
to test Telegram integration without waiting for real budget threshold.

Usage:
    python scripts/python/test-telegram-alert.py
"""

import json
import boto3
import sys

# Initialize AWS Lambda client
lambda_client = boto3.client("lambda", region_name="ap-southeast-1")

# Simulated SNS budget alert message (as received from AWS Budgets)
MOCK_SNS_BUDGET_ALERT = {
    "Records": [
        {
            "Sns": {
                "Message": json.dumps({
                    "version": "1.0",
                    "notificationType": "ACTUAL",
                    "subscriptionName": "Healing Bedroom Monthly Budget",
                    "budgetName": "HealingBedroom-Monthly-Budget",
                    "trigger": {
                        "thresholdType": "ABSOLUTE_VALUE",
                        "threshold": "10",
                        "notificationFrequency": "Immediate"
                    },
                    "current": {
                        "amount": "10.50",
                        "unit": "USD"
                    },
                    "max": {
                        "amount": "20.00",
                        "unit": "USD"
                    },
                    "accountId": "637423194193",
                    "timeStamp": "2026-05-05T10:30:00Z"
                }),
                "TopicArn": "arn:aws:sns:ap-southeast-1:637423194193:healing-bedroom-budget-alerts"
            }
        }
    ]
}


def test_telegram_alert():
    """Test Telegram budget alert notification."""
    print("\n" + "="*70)
    print("Telegram Budget Alert Test")
    print("="*70 + "\n")

    print("📤 Invoking Lambda Notifier with test budget alert...")
    print("-" * 70)

    try:
        response = lambda_client.invoke(
            FunctionName="HealingBedroomStackCDK-LambdaNotifier47F67CB9-vIsNK6Ce9Gx7",
            InvocationType="RequestResponse",
            Payload=json.dumps(MOCK_SNS_BUDGET_ALERT)
        )

        # Parse response
        status_code = response["StatusCode"]
        response_payload = json.loads(response["Payload"].read())

        print(f"\n✅ Lambda invocation completed (Status: {status_code})")
        print(f"\n📋 Response:")
        print(json.dumps(response_payload, indent=2))

        # Extract result
        if status_code == 200:
            print("\n" + "="*70)
            print("✅ TEST PASSED")
            print("="*70)
            print("\n📬 Expected behavior:")
            print("   1. Lambda retrieved Telegram credentials from Parameter Store")
            print("   2. Parsed budget alert data from SNS message")
            print("   3. Formatted alert message with spend/threshold info")
            print("   4. Sent message to Telegram Bot API")
            print("\n📱 Check your Telegram chat for the alert message!")
            print("   If you don't receive it within 2 minutes:")
            print("   - Verify /healing-bedroom/telegram-bot-token in Parameter Store")
            print("   - Verify /healing-bedroom/telegram-chat-id in Parameter Store")
            print("   - Check Lambda execution logs for errors")
            return 0

        else:
            print("\n" + "="*70)
            print("❌ TEST FAILED")
            print("="*70)
            print(f"\nStatus Code: {status_code}")
            print(f"Error: {response_payload.get('error', 'Unknown error')}")
            return 1

    except lambda_client.exceptions.ResourceNotFoundException:
        print("\n❌ ERROR: Lambda function 'healing-bedroom-notifier' not found")
        print("\nPlease ensure:")
        print("  1. CDK stack has been deployed: cdk deploy")
        print("  2. Lambda Notifier function is created")
        print("  3. Function name is exactly 'healing-bedroom-notifier'")
        return 1

    except Exception as e:
        print(f"\n❌ ERROR: Failed to invoke Lambda: {e}")
        print("\nPlease check:")
        print("  1. AWS credentials are configured")
        print("  2. You have permission to invoke Lambda functions")
        print("  3. Lambda function exists in ap-southeast-1")
        return 1


if __name__ == "__main__":
    sys.exit(test_telegram_alert())
