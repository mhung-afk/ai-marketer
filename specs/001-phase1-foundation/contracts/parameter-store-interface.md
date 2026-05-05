# Contract: Parameter Store Interface

**Version**: 1.0  
**Date**: 2026-05-03  
**Scope**: How Lambda functions retrieve API keys and configuration from AWS Systems Manager Parameter Store

---

## Overview

Phase 1 infrastructure stores all API keys and configuration in AWS Systems Manager Parameter Store (standard tier). This contract defines:
- Parameter naming conventions
- Data types and formats
- Lambda retrieval patterns
- Error handling

---

## Parameter Naming Convention

All parameters reside under path `/healing-bedroom/` with the following structure:

```
/healing-bedroom/{service-name}
```

**Examples**:
- `/healing-bedroom/anthropic-api-key`
- `/healing-bedroom/fal-ai-key`
- `/healing-bedroom/telegram-bot-token`
- `/healing-bedroom/apify-api-token`
- `/healing-bedroom/facebook-page-access-token`

---

## Parameter Specifications

| Parameter | Type | Format | Description | Phase |
|-----------|------|--------|-------------|-------|
| `/healing-bedroom/anthropic-api-key` | String | `sk-ant-...` | Anthropic API key for Claude Haiku 4.5 | 1 |
| `/healing-bedroom/fal-ai-key` | String | `fal_...` or token format | fal.ai API key for Nano Banana 2 image generation | 1 |
| `/healing-bedroom/telegram-bot-token` | String | `123456789:ABCdefGHIjklMNOpqrsTUVwxyz` | Telegram Bot token (from BotFather) | 1 |
| `/healing-bedroom/telegram-chat-id` | String | Chat ID or group ID | Recipient chat ID for Telegram alerts | 1 |
| `/healing-bedroom/apify-api-token` | String | `apify_api_...` | Apify API token for Pinterest/Instagram scrapers | 2+ |
| `/healing-bedroom/facebook-page-access-token` | String | Long-lived page token | Facebook page access token (must be long-lived) | 5+ |

---

## Lambda Retrieval Pattern

**IAM Permission Required**:
```
ssm:GetParameter
ssm:GetParameters
```

**Python SDK Example**:
```python
import boto3
import json

ssm_client = boto3.client('ssm')

def get_parameter(parameter_name: str) -> str:
    """Retrieve parameter from Parameter Store."""
    try:
        response = ssm_client.get_parameter(
            Name=parameter_name,
            WithDecryption=False  # Standard tier doesn't support encryption
        )
        return response['Parameter']['Value']
    except ssm_client.exceptions.ParameterNotFound:
        raise ValueError(f"Parameter {parameter_name} not found")
    except Exception as e:
        raise RuntimeError(f"Failed to retrieve parameter {parameter_name}: {str(e)}")

# Usage
api_key = get_parameter('/healing-bedroom/anthropic-api-key')
```

---

## Batch Retrieval Pattern

For efficiency, retrieve multiple parameters in a single call:

```python
def get_parameters(parameter_names: list) -> dict:
    """Retrieve multiple parameters from Parameter Store."""
    try:
        response = ssm_client.get_parameters(
            Names=parameter_names,
            WithDecryption=False
        )
        params = {param['Name']: param['Value'] for param in response['Parameters']}
        
        # Log any missing parameters
        if response['InvalidParameters']:
            print(f"Missing parameters: {response['InvalidParameters']}")
        
        return params
    except Exception as e:
        raise RuntimeError(f"Failed to retrieve parameters: {str(e)}")

# Usage
keys = get_parameters([
    '/healing-bedroom/anthropic-api-key',
    '/healing-bedroom/fal-ai-key',
    '/healing-bedroom/telegram-bot-token'
])
```

---

## Error Handling Contract

| Scenario | Error Type | Lambda Behavior | CloudWatch Log Entry |
|----------|-----------|-----------------|----------------------|
| Parameter not found | `ParameterNotFound` | Catch exception, log error, raise with context | `ERROR: Parameter {name} not found in Parameter Store` |
| IAM permission denied | `AccessDeniedException` | Catch exception, log error, raise with context | `ERROR: Access denied to Parameter {name}; check IAM role permissions` |
| Parameter retrieval timeout | Timeout exception | Retry up to 3 times with exponential backoff (1s, 2s, 4s) | `WARN: Timeout retrieving {name}; retrying (attempt {N}/3)` |
| Network failure | `ConnectionError` | Retry up to 3 times with exponential backoff | `ERROR: Network failure retrieving {name}; check VPC/networking` |

---

## Monitoring & Alerts

**CloudWatch Metrics**:
- `ParameterRetrievalLatency` (ms): How long it takes to fetch a parameter
- `ParameterRetrievalFailures` (count): Failed retrieval attempts per parameter

**Alarms**:
- Alert if `ParameterRetrievalFailures > 5` in 5 minutes (indicates IAM issue or Parameter Store outage)
- Alert if retrieval latency > 500ms for > 3 consecutive calls (indicates Parameter Store performance degradation)

---

## Rotation & Updates

**Manual Rotation Process**:
1. Developer navigates to AWS Systems Manager → Parameter Store
2. Selects parameter (e.g., `/healing-bedroom/anthropic-api-key`)
3. Clicks "Edit" and pastes new API key value
4. Clicks "Save"
5. Lambda picks up new value on next invocation (no restart needed)

**Zero-Downtime Update**:
- Old Lambda invocations in flight continue using cached parameter value (if cached)
- New invocations after update retrieve new parameter value
- No Lambda redeployment required

---

## Phase 1 Acceptance Testing

- [ ] Retrieve each parameter via Lambda; verify correct value returned
- [ ] Test parameter not found error; verify exception logged correctly
- [ ] Test IAM permission denied (remove ssm:GetParameter from role); verify access denied error logged
- [ ] Measure retrieval latency; confirm < 100ms
- [ ] Update parameter value; verify Lambda retrieves new value on next invocation without restart

---

## Future Enhancements

- **Caching Layer** (Phase 3+): Cache parameter values in Lambda with 1-hour TTL to reduce Parameter Store calls (cost optimization)
- **Secrets Manager Migration** (Phase 4+): Migrate to Secrets Manager if automated rotation becomes requirement
- **Audit Trail** (Phase 3+): Enable CloudTrail logging for all parameter access (compliance tracking)
- **Parameter Versioning** (Phase 3+): Track parameter history for rollback capability
