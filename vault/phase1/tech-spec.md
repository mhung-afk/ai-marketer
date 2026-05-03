**Technical Specification: Phòng Ngủ Chữa Lành – MVP V3.1**  
**Project:** Phòng Ngủ Chữa Lành  
**Version:** V3.1 (Post Gemini Review & Cost Optimization)  
**Date:** May 2026  
**Mục tiêu:** Xây dựng MVP lean, chi phí thấp (15-35 USD/tháng), dễ triển khai solo, tập trung vào chất lượng nội dung AIGC và compliance.

### 1. Executive Summary
Xây dựng hệ thống tự động hóa nội dung AI hỗ trợ Affiliate Marketing niche **Phòng ngủ chữa lành**. Hệ thống sẽ quét trending content từ Pinterest và Instagram, sử dụng LLM + AI Image Generation để tạo caption tiếng Việt và hình ảnh độc bản, sau đó đưa qua quy trình phê duyệt thủ công trước khi đăng lên Facebook Fanpage.

Phiên bản V3.1 tập trung mạnh vào việc **giản lược công nghệ**, **tối thiểu chi phí** và **tăng tốc độ triển khai** phù hợp với lịch trình cá nhân trong tháng 5.

### 2. Tech Stack (V3.1)

- **Orchestration:** AWS Lambda (Python) + EventBridge Cron
- **Ingestion:** Apify Actors (Pinterest Scraper & Instagram Scraper)
- **AI Engine:**
  - Text Generation: **Claude Haiku 4.5** (Anthropic API)
  - Image Generation: **Nano Banana 2** via fal.ai
- **Database:** DynamoDB (On-demand mode)
- **Storage:** Amazon S3 + CloudFront
- **Dashboard:** Streamlit (ưu tiên Streamlit Community Cloud)
- **Social Posting:** Facebook Graph API (Pages API)

**Không sử dụng:** SQS, Step Functions, DynamoDB Streams (giai đoạn đầu)

### 3. Data Lifecycle & State Machine

Mỗi item sẽ có các trạng thái sau trong DynamoDB:

1. **RAW** – Dữ liệu thô vừa crawl từ Apify
2. **PROCESSING** – Đang được AI xử lý
3. **DRAFT** – Nội dung AI đã sinh xong, chờ duyệt
4. **APPROVED** – Đã pass Hard Gate Compliance
5. **POSTED** – Đã đăng thành công lên Fanpage
6. **FAILED** – Xảy ra lỗi (lưu log)

### 4. Những gì cần làm (Implementation Tasks)

Dưới đây là danh sách công việc cụ thể cần hoàn thành cho V3.1:

#### Phase 1: Foundation (Tuần 1)
- Thiết kế và tạo DynamoDB table (Single Table Design) với các field cần thiết và GSI cho status
- Setup S3 bucket + CloudFront Distribution cho image hosting
- Tạo IAM roles cho Lambda
- Lưu secrets (Apify token, Anthropic API key, fal.ai key, FB Page Access Token) vào AWS Secrets Manager

#### Phase 2: Ingestion Layer
- Viết Lambda Ingestion: Gọi Apify Actors với danh sách keywords liên quan đến phòng ngủ chữa lành
- Xử lý deduplication cơ bản
- Lưu dữ liệu thô vào DynamoDB với status = RAW

#### Phase 3: AI Processing Pipeline
- Viết Lambda Processor (trigger bằng EventBridge Cron):
  - Query items có status = RAW
  - Gọi Claude Haiku 4.5 để phân tích và viết caption tiếng Việt chữa lành
  - Tạo prompt và gọi Nano Banana 2 để sinh ảnh
  - Upload ảnh lên S3 → lấy public URL qua CloudFront
  - Cập nhật status = DRAFT

#### Phase 4: Compliance Dashboard
- Xây dựng Streamlit Dashboard với các chức năng chính:
  - Hiển thị danh sách items ở trạng thái DRAFT (với preview ảnh + caption)
  - Checkbox Hard Gate: “Tôi xác nhận đã thêm nhãn AIGC và Disclaimer Affiliate”
  - Nút Approve / Reject
  - Tab xem Approved & Posted items
- Deploy Streamlit lên Community Cloud (hoặc Railway)

#### Phase 5: Posting Layer
- Viết Lambda Post (có thể trigger manual hoặc Cron):
  - Query items status = APPROVED
  - Post ảnh + caption lên Facebook Fanpage qua Graph API
  - Cập nhật status = POSTED và lưu post_id
- Xử lý Long-lived Page Access Token và error handling

#### Phase 6: Monitoring & Operations
- Setup CloudWatch Logs + Alarms cơ bản
- Thiết lập thông báo lỗi qua Telegram
- Viết script/utility để retry FAILED items

### 5. Key Principles cho V3.1
- Ưu tiên **simplicity** và **speed to market**
- Giữ chi phí thấp nhất có thể trong 3 tháng đầu
- Đảm bảo 100% bài đăng có nhãn AIGC + Disclaimer
- Dễ mở rộng sau này (thêm niche, thêm fanpage)
- Warm-up Fanpage thủ công ít nhất 7 ngày trước khi chạy pipeline tự động
