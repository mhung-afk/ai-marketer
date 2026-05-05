**Technical Specification – Phase 1: Foundation**  
**Project:** Phòng Ngủ Chữa Lành  
**Version:** MVP V3.1  
**Phase:** 1 – Foundation  
**Mục tiêu:** Xây dựng nền tảng hạ tầng vững chắc, tối ưu chi phí, dễ quản lý và phù hợp phát triển solo.

### 1. Key Decisions (V3.1)

| Hạng mục                  | Quyết định                          | Lý do |
|---------------------------|-------------------------------------|------|
| Database Partition Key    | UUID v4 (String)                    | Tránh collision, dễ generate và debug |
| S3 Versioning             | Tắt                                 | Không cần thiết cho MVP |
| S3 Lifecycle              | Xóa tự động sau **7 ngày**          | Tiết kiệm chi phí tối đa |
| IaC Tool                  | **AWS CDK (Python)**                | Thống nhất ngôn ngữ với toàn bộ dự án |
| Ngôn ngữ chính            | **Python**                          | Phù hợp Lambda, Streamlit, AI SDK |
| Cost Control              | AWS Budget + Alarm                  | Kiểm soát chặt chẽ chi phí |
| Notifications             | **Tất cả thông báo gom về Telegram** | Tập trung, dễ theo dõi cho solo developer |

### 2. Objectives của Phase 1
- Thiết lập toàn bộ infrastructure cốt lõi trên AWS.
- Đảm bảo bảo mật, logging, monitoring chi phí và thông báo tập trung.
- Chuẩn bị sẵn sàng cho các Phase sau triển khai nhanh.
- Hoàn thành trong **3–5 ngày**.

### 3. Deliverables
- AWS CDK Stack deploy thành công.
- DynamoDB table + GSI.
- S3 Bucket + CloudFront Distribution.
- IAM Role và Secrets Manager.
- GitHub Repository có cấu trúc chuẩn.
- AWS Budget Alarm + thông báo Telegram.

### 4. Chi Tiết Triển Khai

#### 4.1. DynamoDB Table
- **Table Name:** `HealingBedroomContent`
- **Partition Key:** `item_id` (String – **UUID v4**)
- **Global Secondary Index:**
  - **GSI1_Status**:
    - Partition Key: `status` (String)
    - Sort Key: `created_at` (String – ISO 8601)

**Các trường chính:**
- `item_id`
- `status` (RAW | PROCESSING | DRAFT | APPROVED | POSTED | FAILED)
- `niche`
- `source_platform`
- `source_url`
- `original_caption`
- `original_image_url`
- `ai_caption`
- `image_s3_key`
- `image_cloudfront_url`
- `post_id`
- `post_url`
- `scraped_at`
- `processed_at`
- `approved_at`
- `posted_at`
- `error_log`
- `retry_count`
- `approved_by`

#### 4.2. Storage
- **S3 Bucket**: `healing-bedroom-images-[yourname]` (private)
  - Versioning: **Tắt**
  - Lifecycle Rule: **Xóa sau 7 ngày**
- **CloudFront Distribution**:
  - Origin: S3 Bucket (dùng Origin Access Control - OAC)
  - HTTPS Only, cache tối ưu cho hình ảnh

#### 4.3. Infrastructure as Code
- Sử dụng **AWS CDK Python**
- Tạo Stack: `HealingBedroomStack`
- Bao gồm: DynamoDB, S3, CloudFront, IAM Role, Secrets Manager

#### 4.4. IAM & Security
- IAM Role: `lambda-healing-bedroom-role`
- Áp dụng Principle of Least Privilege
- Permissions: DynamoDB, S3, Secrets Manager, CloudWatch Logs

#### 4.5. Secrets Management
Lưu trong **AWS Secrets Manager**:
- `apify_api_token` (hoãn cho phase 2)
- `anthropic_api_key` (đã có)
- `fal_ai_key` (đã có)
- `facebook_page_access_token` (Long-lived) (hoãn cho phase 5)
- `telegram_bot_token` (đã có)

#### 4.6. Monitoring & Notifications
- **AWS Budget**:
  - Monthly budget: **40 USD**
  - Alert tại **50% (20 USD)** và **80% (32 USD)**
- **Tất cả thông báo** (Budget Alert, Lambda Error, Pipeline Failure…) sẽ được gom về **Telegram** qua SNS Topic + Lambda Notifier.

#### 4.7. GitHub Repository Structure
```
healing-bedroom-mvp/
├── cdk/                    # AWS CDK stacks
├── src/
│   ├── lambdas/
│   │   ├── ingestion/
│   │   ├── processor/
│   │   ├── poster/
│   │   └── notifier/       # Telegram notifier
│   ├── dashboard/          # Streamlit
│   └── common/             # utils, schemas, config
├── prompts/
├── tests/
├── requirements.txt
├── app.py                  # CDK entry point
├── .env.example
└── README.md
```

### 5. Acceptance Criteria
- [ ] CDK stack deploy thành công tất cả resources
- [ ] DynamoDB table + GSI1_Status hoạt động
- [ ] Upload test image → truy cập được qua CloudFront URL
- [ ] AWS Budget + Alarm thiết lập và test thành công
- [ ] Tất cả secrets được lưu trong Secrets Manager
- [ ] Telegram Notifier hoạt động (test gửi thông báo từ SNS)
- [ ] Repository có cấu trúc rõ ràng