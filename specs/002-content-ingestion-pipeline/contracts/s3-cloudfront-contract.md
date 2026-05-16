# Interface Contract: S3 & CloudFront Image Distribution

**Date**: 2026-05-06 | **Feature**: [plan.md](../plan.md)  
**Status**: Complete | **Integration Point**: Lambda ingestion handler → S3 → CloudFront

## Overview

Phase 2 Lambda downloads images from social media, uploads to S3, and generates public CloudFront URLs for safe distribution without direct dependency on third-party platforms (which may remove/block content). This contract defines the S3 upload workflow and CloudFront URL generation.

---

## 1. S3 Bucket Configuration (Phase 1 Reuse)

### Bucket Details

| Property | Value | Notes |
|----------|-------|-------|
| **Bucket Name** | `healing-bedroom-images-ai-marketer` | From Phase 1; lowercase, no underscores |
| **Region** | `ap-southeast-1` | Consistent with Phase 1 |
| **Access** | Private (IAM-only) | Public access blocked at bucket level |
| **Versioning** | Disabled | Not needed for stateless ingestion |
| **Encryption** | AES-256 (SSE-S3) | Default; no KMS needed |
| **Lifecycle** | 7-day expiration | Auto-cleanup; images are ephemeral |

### Folder Structure

```
s3://healing-bedroom-images-ai-marketer/
├── raw/
│   └── 2026-05-06/
│       ├── 14-30-45-550e8400-e29b-41d4.jpg
│       ├── 14-31-02-550e8400-e29b-41d5.jpg
│       └── ...
└── approved/  # [Phase 3, not used in Phase 2]
    └── ...
```

**Object Key Format**: `raw/YYYY-MM-DD/HH-MM-SS-{uuid}.{ext}`

---

## 2. Upload Workflow

### Step 1: Download Image from Source

```python
def download_image(image_url: str, timeout: int = 10) -> tuple[bytes, str]:
    """
    Download image from social media platform.
    
    Args:
        image_url: Public image URL from Apify response
        timeout: Request timeout in seconds
    
    Returns:
        (image_bytes, image_extension)
    
    Raises:
        ImageDownloadError: If download fails
    """
    try:
        response = requests.get(image_url, timeout=timeout, stream=True)
        response.raise_for_status()
        
        # Infer extension from Content-Type
        content_type = response.headers.get('Content-Type', 'image/jpeg')
        ext_map = {
            'image/jpeg': 'jpg',
            'image/png': 'png',
            'image/webp': 'webp',
            'image/gif': 'gif'
        }
        extension = ext_map.get(content_type.split(';')[0], 'jpg')
        
        return response.content, extension
    
    except requests.exceptions.Timeout:
        raise ImageDownloadError(f"Timeout downloading {image_url}")
    except requests.exceptions.HTTPError as e:
        raise ImageDownloadError(f"HTTP {e.response.status_code}: {image_url}")
```

### Step 2: Compute Content Hash

```python
import hashlib

def compute_content_hash(image_bytes: bytes) -> str:
    """Compute MD5 hash of image for deduplication."""
    return hashlib.md5(image_bytes).hexdigest()
```

### Step 3: Upload to S3

```python
from datetime import datetime
import uuid
from src.common.utils import s3_client

def upload_to_s3(image_bytes: bytes, extension: str) -> str:
    """
    Upload image to S3 and return object key.
    
    Args:
        image_bytes: Downloaded image data
        extension: File extension (jpg, png, etc.)
    
    Returns:
        S3 object key (e.g., raw/2026-05-06/14-30-45-uuid.jpg)
    
    Raises:
        S3UploadError: If upload fails
    """
    now = datetime.utcnow()
    date_part = now.strftime('%Y-%m-%d')
    time_part = now.strftime('%H-%M-%S')
    uuid_part = str(uuid.uuid4())[:8]
    
    object_key = f"raw/{date_part}/{time_part}-{uuid_part}.{extension}"
    
    try:
        s3_client.put_object(
            Bucket='healing-bedroom-images-ai-marketer',
            Key=object_key,
            Body=image_bytes,
            ContentType=f'image/{extension}',
            CacheControl='max-age=604800',  # 7 days
            Metadata={
                'source': 'ingestion-pipeline',
                'uploaded-at': now.isoformat()
            }
        )
        return object_key
    except Exception as e:
        raise S3UploadError(f"Failed to upload {object_key}: {str(e)}")
```

---

## 3. CloudFront Distribution (Phase 1 Reuse)

### Distribution Configuration

| Property | Value | Notes |
|----------|-------|-------|
| **Domain** | `d{hash}.cloudfront.net` | From Phase 1 |
| **Origin** | S3 bucket | With Origin Access Control (OAC) |
| **TTL** | 86400 seconds (1 day) | Cache behavior for raw/ folder |
| **Compression** | gzip, brotli | Auto-enabled for image metadata requests |
| **Protocol** | HTTPS only | Enforce SSL/TLS |

### URL Generation

```python
def generate_cloudfront_url(s3_object_key: str) -> str:
    """
    Generate public CloudFront URL for S3 object.
    
    Args:
        s3_object_key: S3 object key (e.g., raw/2026-05-06/14-30-45-uuid.jpg)
    
    Returns:
        HTTPS CloudFront URL
    """
    cloudfront_domain = "d123abc456.cloudfront.net"  # From Phase 1
    return f"https://{cloudfront_domain}/{s3_object_key}"
```

### Example URLs

```
https://d123abc456.cloudfront.net/raw/2026-05-06/14-30-45-abc12345.jpg
https://d123abc456.cloudfront.net/raw/2026-05-06/14-31-02-def67890.png
```

---

## 4. IAM Permissions (Phase 1 Role)

### Required S3 Permissions

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:DeleteObject"
      ],
      "Resource": "arn:aws:s3:::healing-bedroom-images-ai-marketer/raw/*"
    },
    {
      "Effect": "Allow",
      "Action": "s3:ListBucket",
      "Resource": "arn:aws:s3:::healing-bedroom-images-ai-marketer"
    }
  ]
}
```

**Status**: Permissions already included in Phase 1 Lambda Role. No changes needed.

---

## 5. Lifecycle Policy (Phase 1 Reuse)

### Expiration Rule

```json
{
  "Rules": [
    {
      "Id": "ExpireRawImages",
      "Status": "Enabled",
      "Prefix": "raw/",
      "Expiration": {
        "Days": 7
      }
    }
  ]
}
```

**Effect**: Images automatically deleted 7 days after upload. Cost-effective cleanup.

---

## 6. Integration with DynamoDB

### Image Reference Fields

```python
# DynamoDB ContentItem
{
    "item_id": "550e8400-e29b-41d4-a716-446655440000",
    "s3_image_key": "raw/2026-05-06/14-30-45-abc12345.jpg",
    "cloudfront_url": "https://d123abc456.cloudfront.net/raw/2026-05-06/14-30-45-abc12345.jpg",
    "image_size_bytes": 245000,
    "image_width": 1080,
    "image_height": 1920,
    ...
}
```

### Full Integration Example

```python
# src/lambdas/ingestion/image_processor.py

class ImageProcessor:
    def __init__(self):
        self.s3_client = boto3.client('s3')
        self.cloudfront_domain = "d123abc456.cloudfront.net"
    
    def process_image(self, source_url: str) -> dict:
        """
        Download, hash, upload, and generate URL.
        
        Returns:
            {
                "s3_image_key": "raw/2026-05-06/14-30-45-uuid.jpg",
                "cloudfront_url": "https://...",
                "content_hash": "a1b2c3d4...",
                "image_size_bytes": 245000,
                "image_width": 1080,
                "image_height": 1920
            }
        """
        # 1. Download
        image_bytes, ext = download_image(source_url)
        
        # 2. Hash
        content_hash = compute_content_hash(image_bytes)
        
        # 3. Check for duplicate
        if is_duplicate(content_hash):
            raise DuplicateImageError(f"Image hash {content_hash} already processed")
        
        # 4. Upload to S3
        s3_object_key = upload_to_s3(image_bytes, ext)
        
        # 5. Generate CloudFront URL
        cloudfront_url = f"https://{self.cloudfront_domain}/{s3_object_key}"
        
        # 6. Get image dimensions
        image = Image.open(BytesIO(image_bytes))
        width, height = image.size
        
        return {
            "s3_image_key": s3_object_key,
            "cloudfront_url": cloudfront_url,
            "content_hash": content_hash,
            "image_size_bytes": len(image_bytes),
            "image_width": width,
            "image_height": height
        }
```

---

## 7. Error Handling

### Failure Scenarios

| Scenario | HTTP | Retry | Action |
|----------|------|-------|--------|
| Image URL 404 | 404 | No | Log error; move to DLQ |
| S3 permission denied | 403 | No | Alert ops; check IAM role |
| S3 quota exceeded | 503 | Yes | Exponential backoff; escalate if persistent |
| CloudFront delay | N/A | N/A | Wait up to 60s for URL to become live |
| Image too large (>100MB) | N/A | No | Skip; log warning |
| Corrupted image file | N/A | No | Skip; move to DLQ |

### Retry Logic

```python
def upload_with_retry(image_bytes: bytes, extension: str, max_retries: int = 3) -> str:
    """Upload to S3 with exponential backoff."""
    for attempt in range(max_retries):
        try:
            return upload_to_s3(image_bytes, extension)
        except S3UploadError as e:
            if attempt < max_retries - 1 and '503' in str(e):
                wait_time = 2 ** attempt  # 1s, 2s, 4s
                time.sleep(wait_time)
            else:
                raise
```

---

## 8. Contract Compliance Checklist

- [x] S3 bucket configuration documented (Phase 1 reuse)
- [x] Object key naming convention defined
- [x] Upload workflow (download → hash → upload) specified
- [x] CloudFront URL generation documented
- [x] IAM permissions confirmed (Phase 1 role includes S3 access)
- [x] Lifecycle policy (7-day expiration) confirmed
- [x] Integration with DynamoDB ContentItem schema
- [x] Error handling and retry logic defined
- [x] Python implementation provided

---

**Contract Approved**: 2026-05-06  
**Status**: Ready for implementation  
**Next**: Quickstart guide
