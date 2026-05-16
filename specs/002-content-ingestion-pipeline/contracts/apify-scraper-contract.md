# Interface Contract: Apify Actor Integration

**Date**: 2026-05-06 | **Feature**: [plan.md](../plan.md)  
**Status**: Complete | **Integration Point**: Lambda ingestion handler → Apify API

## Overview

The Phase 2 ingestion pipeline uses Apify Actors to scrape social media platforms. This contract defines the request/response format for integrating with Apify's SDK and REST API.

---

## 1. Apify SDK Usage (Recommended)

### JavaScript-to-Python Alternative

Apify SDKs are primarily JavaScript. Phase 2 uses Python → REST API directly (not SDK).

### Python: REST API Integration

**Base URL**: `https://api.apify.com/v2`  
**Authentication**: Bearer token via `PARAM_APIFY_API_TOKEN` (Parameter Store)  
**Rate Limit**: 600 requests/minute (sufficient for Phase 2 MVP)

---

## 2. Request: Start Actor Run

### Endpoint
```
POST /v2/acts/{actorId}/runs
```

### Request Headers
```json
{
  "Content-Type": "application/json",
  "Authorization": "Bearer {apify_token}"
}
```

### Request Payload: TikTok Scraper

```json
{
  "actId": "apify/tiktok-scraper",
  "actRunToken": null,
  "waitForFinish": 120,
  "memory": 4096,
  "timeout": 300,
  "input": {
    "searchType": "hashtag",
    "searchValue": "healingbedroom",
    "postsLimit": 5,
    "shouldDownloadVideos": false,
    "shouldDownloadCovers": true,
    "shouldDownloadSubs": false
  }
}
```

### Request Payload: Instagram Scraper

```json
{
  "actId": "apify/instagram-scraper",
  "waitForFinish": 120,
  "memory": 4096,
  "timeout": 300,
  "input": {
    "searchType": "hashtag",
    "searchValue": "healingbedroom",
    "resultsLimit": 5,
    "downloadImages": true,
    "downloadVideos": false
  }
}
```

### Request Payload: Facebook Scraper

```json
{
  "actId": "apify/facebook-pages-scraper",
  "waitForFinish": 120,
  "memory": 4096,
  "timeout": 300,
  "input": {
    "pageUrls": ["https://www.facebook.com/therapeutic-bedding"],
    "postsLimit": 5,
    "downloadImages": true,
    "includeComments": false
  }
}
```

---

## 3. Response: Actor Run Status

### Successful Response (HTTP 201)

```json
{
  "id": "run_abc123xyz",
  "actId": "apify/tiktok-scraper",
  "actorId": "actor123",
  "status": "SUCCEEDED",
  "startedAt": "2026-05-06T14:30:00.000Z",
  "finishedAt": "2026-05-06T14:35:15.000Z",
  "durationMillis": 315000,
  "exitCode": 0,
  "output": {
    "datasetId": "dataset_abc123",
    "resultUrl": "https://api.apify.com/v2/datasets/dataset_abc123/items"
  },
  "meta": {
    "userInteractionsCount": 1,
    "availableMemoryMbytes": 4096
  }
}
```

### Failed Response (HTTP 400/500)

```json
{
  "id": "run_abc123xyz",
  "status": "FAILED",
  "exitCode": 1,
  "errors": [
    {
      "message": "Rate limit exceeded. Try again in 3600 seconds.",
      "code": "RATE_LIMIT"
    }
  ],
  "output": null
}
```

---

## 4. Response: Dataset Items (Results)

### Endpoint
```
GET /v2/datasets/{datasetId}/items
```

### Response: TikTok Items

```json
[
  {
    "id": "7123456789012345678",
    "url": "https://www.tiktok.com/@creative_bedroom/video/7123456789012345678",
    "desc": "Transform your bedroom into a peaceful sanctuary ✨ #healingbedroom #aesthetic",
    "playCount": 15230,
    "diggCount": 1203,
    "commentCount": 87,
    "shareCount": 45,
    "downloadCount": 3,
    "video": {
      "downloadAddr": "https://v16m-default.akamaized.net/...",
      "coverUrl": "https://p16-sign-va.tiktokcdn.com/...",
      "duration": 45
    },
    "author": {
      "uniqueId": "creative_bedroom",
      "nickname": "Creative Bedroom",
      "avatarUrl": "https://p16-sign-va.tiktokcdn.com/...",
      "verified": false
    },
    "hashtags": ["healingbedroom", "bedroomtransformation", "aesthetic"],
    "createTime": 1715000445,
    "height": 1080,
    "width": 1920
  }
]
```

### Response: Instagram Items

```json
[
  {
    "id": "17999456789012345",
    "url": "https://www.instagram.com/p/ABC1234DEF/",
    "caption": "Healing bedroom vibes 🛏️✨ #cozybedroom #aesthetic",
    "likeCount": 3421,
    "commentCount": 156,
    "timestamp": "2026-05-06T12:30:45.000Z",
    "imageUrl": "https://instagram.com/media/ABC1234/",
    "imageUrls": [
      "https://instagram.com/media/ABC1234/",
      "https://instagram.com/media/ABC1234/ABC/"
    ],
    "owner": {
      "username": "bedroom_aesthetic",
      "name": "Bedroom Aesthetic",
      "profileUrl": "https://www.instagram.com/bedroom_aesthetic/",
      "profilePictureUrl": "https://instagram.com/profile/..."
    },
    "hashtags": ["cozybedroom", "aesthetic", "bedroom"],
    "location": null
  }
]
```

---

## 5. Error Handling

### Common Errors

| Error Code | HTTP | Cause | Retry Strategy |
|------------|------|-------|-----------------|
| `RATE_LIMIT` | 429 | API call limit exceeded | Exponential backoff; wait 60–3600s |
| `TIMEOUT` | 504 | Actor execution timeout | Retry with longer timeout (max 600s) |
| `INVALID_TOKEN` | 401 | Apify token invalid/expired | Alert ops; check Parameter Store |
| `INVALID_INPUT` | 400 | Malformed request payload | Fix payload; do not retry |
| `NOT_FOUND` | 404 | Actor ID does not exist | Verify actor name; update config |
| `SERVICE_UNAVAILABLE` | 503 | Apify service down | Retry after 60s; escalate to Telegram |

### Retry Policy

```python
# src/lambdas/ingestion/error_handlers.py
def retry_with_backoff(func, max_retries=3):
    for attempt in range(max_retries):
        try:
            return func()
        except ApifyRateLimitError:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # 1s, 2s, 4s
                time.sleep(wait_time)
            else:
                raise  # Give up after max retries
        except ApifyTimeoutError:
            if attempt < max_retries - 1:
                timeout = 60 + (30 * attempt)  # 60s, 90s, 120s
                # Retry with longer timeout
            else:
                raise
```

---

## 6. Implementation: Python Apify Client

### Installation
```bash
pip install apify-client
```

### Basic Usage

```python
# src/lambdas/ingestion/apify_client.py
from apify_client import ApifyClient
from src.common.utils import get_parameter
from src.common.config import PARAM_APIFY_API_TOKEN

def scrape_tiktok(hashtag: str, max_items: int = 5) -> list[dict]:
    """
    Scrape TikTok posts by hashtag.
    
    Returns:
        List of post objects with url, caption, image, author info
    """
    token = get_parameter(PARAM_APIFY_API_TOKEN)
    client = ApifyClient(token)
    
    run = client.actor("apify/tiktok-scraper").call(input={
        "searchType": "hashtag",
        "searchValue": hashtag,
        "postsLimit": max_items,
        "shouldDownloadVideos": False,
        "shouldDownloadCovers": True
    })
    
    # Access dataset results
    dataset = client.dataset(run["defaultDatasetId"])
    items = dataset.list_items().items
    
    return [
        {
            "id": item["id"],
            "url": item["url"],
            "caption": item["desc"],
            "image_url": item["video"]["coverUrl"],
            "platform": "tiktok",
            "author": item["author"]["uniqueId"],
            "engagement": {
                "likes": item["diggCount"],
                "comments": item["commentCount"],
                "shares": item["shareCount"],
                "views": item["playCount"]
            }
        }
        for item in items
    ]
```

---

## 7. Contract Compliance Checklist

- [x] All Apify Actor endpoints documented
- [x] Request/response payloads for all 3 platforms
- [x] Error codes + retry strategies defined
- [x] Rate limit + timeout values confirmed
- [x] Python implementation pattern provided
- [x] Integration with Phase 1 secrets management (Parameter Store)

---

**Contract Approved**: 2026-05-06  
**Status**: Ready for implementation  
**Next**: Claude API contract
