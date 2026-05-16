**Content Ingestion Pipeline**

**Project**: Healing Bedroom MVP – AI Marketer  
**Phase**: 2 – Content Ingestion  
**Status**: Draft → Ready for Implementation  
**Timeframe**: May 2026  
**Owner**: Solo Developer  
**Budget estimate**: +$8–15/tháng (Apify + Anthropic + Lambda)

---

## 🎯 **Mục tiêu Phase 2**

Xây dựng pipeline tự động thu thập nội dung (hình ảnh + caption) từ các nguồn TikTok / Instagram / Facebook, sau đó dùng **Anthropic Claude** để generate **caption tiếng Việt** tối ưu, hấp dẫn, phù hợp phong cách “Healing Bedroom” (thoải mái, chữa lành, thẩm mỹ, ASMR, bedroom decor…).

Kết quả: Các record được lưu vào DynamoDB với `status = RAW`, sẵn sàng cho Phase 3 (Image Generation / Enhancement).

---

## 📋 **Prerequisites** (trước khi implement Phase 2)

1. **Phase 1 đã deploy thành công** (DynamoDB, S3 + CloudFront, Parameter Store, IAM Role cho Lambda, Layer).
2. Có **Apify API Token** (tạo tại console.apify.com).
3. Có **Anthropic API Key** (sonnet hoặc haiku).
4. Đã config Parameter Store:
   - `/healing-bedroom/apify-api-token`
   - `/healing-bedroom/anthropic-api-key`
5. AWS Region thống nhất (`ap-southeast-1`).
6. Telegram Bot đã hoạt động (để nhận thông báo lỗi ingestion).

---

## ✅ **Functional Requirements**

### 1. Ingestion Sources
- Hỗ trợ scrape từ **TikTok**, **Instagram**, **Facebook** (ưu tiên TikTok & Instagram).
- Sử dụng **Apify Actors** phù hợp (ví dụ: `apify/instagram-scraper`, `apify/tiktok-scraper`, hoặc custom actor).
- Hỗ trợ scrape theo **keyword/hashtag** (ví dụ: `#healingbedroom`, `#bedroomdecor`, `#asmr`, `#cozyroom`...) và **user profile**.

### 2. Data Processing Flow
1. Lambda `ingestion-handler` được trigger bởi **EventBridge Schedule** (mỗi 6–12h).
2. Gọi Apify Actor → lấy posts (image/video URL, original caption, metadata).
3. Tải ảnh về tạm thời → upload lên **S3** (`/raw/YYYY-MM-DD/`) → sinh CloudFront public URL.
4. Gọi **Anthropic Claude** để:
   - Rewrite caption sang **tiếng Việt tự nhiên**, phong cách Healing Bedroom.
   - Thêm hashtag phù hợp.
   - Gợi ý tone (chill, motivational, aesthetic…).
5. Lưu record vào **DynamoDB** (`HealingBedroomContent`):
   - `status`: `RAW`
   - Các field: `source_platform`, `source_url`, `original_caption`, `ai_caption_vi`, `original_image_url`, `s3_image_key`, `cloudfront_url`, `scraped_at`, `processed_at`, `metadata` (JSON).

### 3. Deduplication
- Kiểm tra duplicate dựa trên `source_url` hoặc hash của ảnh trước khi lưu.

### 4. Error Handling & Monitoring
- Retry logic (Apify & Claude).
- Log đầy đủ vào CloudWatch.
- Gửi thông báo Telegram khi có lỗi nghiêm trọng (rate limit, quota, v.v.).
- Dead Letter Queue (nếu cần).

---

## **Acceptance Criteria (ACs)**

- [ ] Lambda `ingestion` deploy thành công, dùng shared Layer và IAM role từ Phase 1.
- [ ] Pipeline chạy theo lịch → ingest được ít nhất **10–20 items/ngày**.
- [ ] Mỗi item trong DynamoDB có đầy đủ fields, `cloudfront_url` public và hoạt động.
- [ ] Caption AI tiếng Việt chất lượng cao, phù hợp brand (có thể kiểm tra manual 10 samples).
- [ ] Không lưu duplicate (kiểm tra bằng query GSI).
- [ ] Error handling hoạt động: thông báo Telegram khi scrape hoặc Claude fail.
- [ ] Cost monitoring: Budget alert vẫn hoạt động.
- [ ] `cdk synth` & `cdk deploy` sạch, không lỗi.
- [ ] README Phase 2 cập nhật + hướng dẫn manual trigger Lambda.

---

## **Non-Functional Requirements**

- **Serverless** 100%.
- **Idempotent** & **Scalable**.
- **Secure**: Không hardcode secret (dùng Parameter Store).
- **Cost effective**: Sử dụng Claude Haiku khi có thể, giới hạn số items/batch.
- **Extensible**: Dễ thêm source mới hoặc prompt mới.

---

## **Implementation Tasks (Checklist)**

1. Tạo folder `src/lambdas/ingestion/`
2. Viết Lambda handler + Apify client + Claude client.
3. Thêm EventBridge Rule + Target trong CDK Stack.
4. Cập nhật IAM Policy cho Lambda (Apify HTTP calls, Anthropic).
5. Viết unit tests + manual test script.
6. Cập nhật README & Tech Spec.
7. Deploy & Verify.

---

## **Success Metrics**

- Pipeline chạy ổn định ≥ 3 ngày liên tục.
- ≥ 70% items có caption AI chất lượng (đánh giá subjective).
- Chi phí Phase 2 < $15/tháng.
