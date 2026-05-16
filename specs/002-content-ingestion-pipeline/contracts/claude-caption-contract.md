# Interface Contract: Anthropic Claude Caption Generation

**Date**: 2026-05-06 | **Feature**: [plan.md](../plan.md)  
**Status**: Complete | **Integration Point**: Lambda ingestion handler → Claude API

## Overview

Phase 2 uses Anthropic Claude Haiku to transform English social media captions into brand-aligned Vietnamese captions for the "Healing Bedroom" brand. This contract defines the request/response format.

---

## 1. API Endpoint & Authentication

### Endpoint
```
POST https://api.anthropic.com/v1/messages
```

### Request Headers
```json
{
  "Content-Type": "application/json",
  "x-api-key": "{anthropic_api_key}",
  "anthropic-version": "2023-06-01"
}
```

**API Key Source**: `PARAM_ANTHROPIC_API_KEY` (AWS Parameter Store, Phase 1)

---

## 2. Request Payload

### Request: Basic Caption Rewrite

```json
{
  "model": "claude-3-5-haiku-20241022",
  "max_tokens": 300,
  "system": "You are a Vietnamese content creator specializing in calming, wellness-focused bedroom aesthetics. Your captions are natural, poetic, and optimized for Instagram/TikTok engagement. Tone: peaceful, aspirational, no hard selling. Include 3-5 relevant hashtags at the end.",
  "messages": [
    {
      "role": "user",
      "content": "Rewrite this English caption into Vietnamese for the \"Healing Bedroom\" brand. Respond ONLY with the Vietnamese caption + hashtags. No explanations.\n\nOriginal: Transform your bedroom into a peaceful sanctuary ✨\nPlatform: tiktok"
    }
  ]
}
```

### Request Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `model` | string | Yes | `claude-3-5-haiku-20241022` (Phase 2 default; per Constitution cost discipline) |
| `max_tokens` | integer | Yes | 300 (sufficient for caption + hashtags) |
| `system` | string | Yes | System prompt defining brand tone + output format |
| `messages` | array | Yes | Array of message objects (user/assistant turns) |
| `temperature` | float | No | Default 1.0 (natural variation); can lower to 0.7 for consistency |

### System Prompt Template

```
You are a Vietnamese content creator specializing in calming, wellness-focused bedroom aesthetics. Your captions are natural, poetic, and optimized for Instagram/TikTok engagement.

Brand Guidelines:
- Tone: Peaceful, aspirational, wellness-focused, no hard selling
- Style: Poetic, minimalist descriptions of bedroom ambiance
- Hashtags: 3-5 relevant tags per caption
- Word count: 50-100 Vietnamese words max

Respond ONLY with:
1. Vietnamese caption (50-100 words)
2. Line break
3. Hashtags (e.g., #cozybedroom #aesthetic #sleep)

Do NOT include explanations, notes, or formatting beyond the caption and hashtags.
```

---

## 3. Response Payload

### Success Response (HTTP 200)

```json
{
  "id": "msg_01ARZ3NdrlSZN57fNLZy5G1Oy2e4GZY",
  "type": "message",
  "role": "assistant",
  "content": [
    {
      "type": "text",
      "text": "Biến phòng ngủ của bạn thành một thiên đường bình yên. Ánh sáng nhẹ, không gian thoải mái, mọi thứ lẫn trong màu sắc dịu dàng.\n\n#healingbedroom #aesthetic #cozybedroom #sleepmode #interiordesign"
    }
  ],
  "model": "claude-3-5-haiku-20241022",
  "stop_reason": "end_turn",
  "stop_sequence": null,
  "usage": {
    "input_tokens": 185,
    "output_tokens": 68
  }
}
```

### Error Response: Rate Limit (HTTP 429)

```json
{
  "type": "error",
  "error": {
    "type": "rate_limit_error",
    "message": "Rate limit exceeded. Please try again later."
  }
}
```

### Error Response: Invalid API Key (HTTP 401)

```json
{
  "type": "error",
  "error": {
    "type": "authentication_error",
    "message": "Invalid API Key provided."
  }
}
```

### Error Response: Timeout (HTTP 504)

```json
{
  "type": "error",
  "error": {
    "type": "timeout_error",
    "message": "Request timed out."
  }
}
```

---

## 4. Retry & Error Handling

### Error Codes & Strategies

| HTTP | Error Type | Cause | Retry |
|------|-----------|-------|-------|
| 200 | (success) | Request succeeded | No |
| 400 | `invalid_request_error` | Malformed request (e.g., invalid JSON) | No – fix input |
| 401 | `authentication_error` | Invalid/expired API key | No – alert ops to rotate key |
| 429 | `rate_limit_error` | API rate limit hit | Yes – exponential backoff |
| 500 | `internal_server_error` | Anthropic server error | Yes – exponential backoff (max 3x) |
| 504 | `timeout_error` | Request timeout | Yes – retry with 30s timeout |

### Retry Policy

```python
# src/lambdas/ingestion/claude_caption_generator.py
import anthropic
import time

def generate_caption_with_retry(original_caption: str, platform: str, max_retries: int = 3) -> str:
    """
    Generate Vietnamese caption using Claude Haiku with exponential backoff retry.
    
    Args:
        original_caption: English caption to rewrite
        platform: Source platform (tiktok, instagram, facebook)
        max_retries: Max retry attempts before raising exception
    
    Returns:
        Vietnamese caption + hashtags
        
    Raises:
        anthropic.APIError: If max retries exceeded
    """
    client = anthropic.Anthropic(api_key=get_parameter(PARAM_ANTHROPIC_API_KEY))
    
    for attempt in range(max_retries):
        try:
            response = client.messages.create(
                model="claude-3-5-haiku-20241022",
                max_tokens=300,
                system=CLAUDE_SYSTEM_PROMPT,  # Defined in config.py
                messages=[{
                    "role": "user",
                    "content": f"Rewrite into Vietnamese for {platform}:\n\n{original_caption}"
                }]
            )
            
            vietnamese_caption = response.content[0].text.strip()
            logger.info(f"✅ Claude caption generated (attempt {attempt + 1}): {vietnamese_caption[:50]}...")
            return vietnamese_caption
            
        except anthropic.RateLimitError as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** (attempt + 1)  # 2s, 4s, 8s
                logger.warning(f"⚠️ Rate limit (attempt {attempt + 1}/{max_retries}). Retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                logger.error(f"❌ Rate limit exceeded after {max_retries} retries")
                raise
                
        except anthropic.APITimeoutError as e:
            if attempt < max_retries - 1:
                logger.warning(f"⚠️ Timeout (attempt {attempt + 1}/{max_retries}). Retrying...")
                time.sleep(2 ** attempt)
            else:
                logger.error(f"❌ Timeout after {max_retries} retries")
                raise
                
        except anthropic.AuthenticationError as e:
            logger.error(f"❌ Authentication failed: Invalid API key or expired")
            raise  # Don't retry auth errors
```

---

## 5. Cost Estimation

### Token Pricing

**Anthropic Claude Haiku 3.5** (as of May 2026):
- Input: $0.80 per 1M tokens
- Output: $4.00 per 1M tokens

### Per-Caption Cost

| Metric | Tokens | Cost |
|--------|--------|------|
| System prompt | 150 | $0.00012 |
| User message (caption) | 50 | $0.00004 |
| **Input total** | 200 | **$0.00016** |
| Output (Vietnamese caption) | 80 | **$0.00032** |
| **Per-caption total** | 280 | **$0.00048** |

### Monthly Cost (10–20 captions/day)

- 15 captions/day × 30 days = 450 captions/month
- 450 × $0.00048 = **$0.22/month**

✅ **Well within $8–15 Phase 2 budget.**

---

## 6. Implementation: Python Client

### Installation
```bash
pip install anthropic
```

### Full Example

```python
# src/lambdas/ingestion/claude_caption_generator.py

import anthropic
from src.common.utils import get_parameter
from src.common.config import PARAM_ANTHROPIC_API_KEY, CLAUDE_SYSTEM_PROMPT

class CaptionGenerator:
    def __init__(self):
        self.client = anthropic.Anthropic(
            api_key=get_parameter(PARAM_ANTHROPIC_API_KEY)
        )
        self.model = "claude-3-5-haiku-20241022"
        self.max_tokens = 300
    
    def generate(self, original_caption: str, platform: str, max_retries: int = 3) -> str:
        """Generate Vietnamese caption with retry logic."""
        for attempt in range(max_retries):
            try:
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=self.max_tokens,
                    system=CLAUDE_SYSTEM_PROMPT,
                    messages=[{
                        "role": "user",
                        "content": f"Platform: {platform}\n\nOriginal: {original_caption}"
                    }]
                )
                return response.content[0].text.strip()
            except anthropic.RateLimitError:
                if attempt < max_retries - 1:
                    import time
                    time.sleep(2 ** (attempt + 1))
                else:
                    raise
    
    def batch_generate(self, captions: list[dict]) -> list[str]:
        """Generate multiple captions (placeholder for Phase 3 batching)."""
        results = []
        for item in captions:
            results.append(self.generate(item['original'], item['platform']))
        return results
```

---

## 7. Constraints & Limits

### Rate Limits

- **Default tier**: 1000 requests/minute, 10 million input tokens/day
- **Phase 2 expected**: ~100 requests/day, ~50K tokens/day → well under limit
- **Safeguard**: Implement 1-second min delay between requests to stay below tier limit

### Timeout Handling

- **Read timeout**: 30 seconds per request (hardcoded in Lambda)
- **If timeout**: Move item to SQS DLQ; alert ops via Telegram

### Model Stability

- **Model name**: `claude-3-5-haiku-20241022` (specific version for reproducibility)
- **Backup**: If Haiku unavailable, use `claude-3-5-sonnet-20241022` (higher cost, only if needed)

---

## 8. Contract Compliance Checklist

- [x] API endpoint and authentication documented
- [x] Request/response payloads for all scenarios (success, rate limit, auth error, timeout)
- [x] Error codes and retry strategies defined
- [x] Rate limit + timeout values confirmed
- [x] Cost estimation validated (<$1/month for MVP)
- [x] Python client implementation provided
- [x] System prompt template defined
- [x] Integration with Phase 1 secrets (Parameter Store)

---

**Contract Approved**: 2026-05-06  
**Status**: Ready for implementation  
**Next**: S3 Pre-signed URLs contract
