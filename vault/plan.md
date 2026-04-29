# KẾ HOẠCH XÂY DỰNG DOANH NGHIỆP AI-FIRST E-COMMERCE (Fanpage → Affiliate/Shopee/TikTok Shop)
**Phiên bản tinh chỉnh cuối – Ready for a Constrained Pilot**  
**Ngày cập nhật:** 27/04/2026  
**Mục tiêu:** Xây dựng dòng tiền ổn định với chi phí tối thiểu, rủi ro thấp nhất cho developer solo tại Việt Nam.

## 1. Chiến lược cốt lõi
- **Audience-First + Iterative Learning**: Xây dựng khán giả trước (Fanpage Facebook + TikTok) bằng nội dung quote + trend organic.  
- Dùng dữ liệu thực tế (reach, like, view, saves) để tinh chỉnh prompt AI trước khi chuyển sang bán hàng.  
- **Constrained Pilot**: Chỉ chạy **1 ngách, 1 fanpage, 1–2 format content** trong 2 tuần manual trước khi semi-auto.

## 2. Tech Stack MVP 2026 (Tinh gọn – Serverless)
- **Orchestration**: Python scripts + cron job hoặc **AWS Lambda + Function URLs**.  
- **LLM**: Claude Haiku 4.5 (default + prompt caching) + Claude Sonnet 4.6 chỉ khi cần ($1/$5 và $3/$15).  
- **Hình ảnh**: **Nano Banana 2** (fal.ai) ưu tiên (text tiếng Việt xuất sắc).  
- **Video**: Tùy chọn (Seedream V4 / Luma Dream Machine).  
- **Database**: **DynamoDB on-demand** (metadata: `source_url`, `captured_at`, `prompt_version`, `human_approved_at`, `format_type`, `niche_tag`).  
- **Storage**: **S3 + Lifecycle Policy** (xóa sau 30 ngày).  
- **Logging & Monitoring**: **CloudWatch Logs + Alarms** (Telegram/Zalo alert) + Lambda định kỳ check affiliate link health.  
- **Scraping**: Crawlee + Playwright.  
- **Dashboard**: Streamlit/Gradio (có **hard gate "Verify Compliance"** + AIGC label bắt buộc).  
- **Hạ tầng**: AWS Lambda + DynamoDB + S3 + CloudWatch (free tier + buffer 20–30%).

**Nguyên tắc**: Chỉ code những gì phục vụ trực tiếp ra đơn. Không over-engineer.

## 3. Timeline 12 tuần (Constrained Pilot)
- **Tuần 1–2**: Niche Validation + scraper + script caption + vận hành thủ công.  
- **Tuần 3–4**: Tích hợp ảnh + tinh chỉnh prompt + 2 format test.  
- **Tuần 5–8**: Deploy cron + scheduling + Shopee Affiliate.  
- **Tuần 9–12**: Scale (nếu đạt checkpoint) hoặc pivot.

**Checkpoint**:
- Tuần 4: ≥2–3 bài reach >500 organic + 1 format thắng (sau ít nhất 20 bài).  
- Tuần 8: CTR ≥1.5% + ≥1–2 đơn hàng.  
- Tuần 12: Doanh thu ≥5–10 triệu VNĐ/tháng **hoặc** pivot.

## 4. Ngân sách thực tế (1 fanpage)
- LLM + caching: $5–12/tháng  
- Hình ảnh: $2–8/tháng  
- **Tổng**: **$15–35/tháng** + **buffer 20–30%** (retry, logs, storage).  
- **Chi phí công của bạn**: 15–30 phút duyệt/ngày (ghi nhận để tính ROI thực).

## 5. Niche Selection Framework (Tuần 1 – Bắt buộc)
**Bước 1 – Hard Filter Compliance**: Pass/Fail (loại ngay nếu nhạy cảm).  
**Bước 2 – Chấm điểm** (chỉ ngách Pass mới chấm, cần ≥85 điểm):

| Tiêu chí              | Trọng số | Cách chấm (1–10) |
|-----------------------|----------|------------------|
| Affiliate Margin      | 25%      | ≥10–15%          |
| Viral Potential       | 20%      | Dễ chia sẻ       |
| AI Content Fit        | 15%      | Dễ quote/trend   |
| Catalog Depth         | 10%      | >500 sản phẩm    |
| Seasonality           | 10%      | Ổn định hoặc tận dụng mùa |

**Gợi ý ngách hot**: Làm đẹp Gen Z, Gia dụng thông minh, Phụ kiện công nghệ.

## 6. Ngưỡng Pivot (có volume tối thiểu)
- Sau **4 tuần VÀ ít nhất 20 bài đăng**: Reach trung bình <200/bài dù thử 3 format → **Đổi format**.  
- Sau **8 tuần**: Click affiliate <50/tuần → **Đổi ngách**.

## 7. Risk Register & Compliance (Hard Gate)
**Compliance bắt buộc**:
- TikTok: Toggle **AI-generated** hoặc watermark rõ ràng.  
- Meta: Disclose “Ảnh minh họa bằng AI”.  
- Affiliate: “Link affiliate, mình nhận hoa hồng nhỏ”.

## 8. Quy trình vận hành (Human-in-the-loop)
1. AI quét trend → sinh nháp.  
2. Duyệt Dashboard (**Verify Compliance** bắt buộc).  
3. Schedule đăng.  
4. Theo dõi & tinh chỉnh.

**Monitoring**: Insights + UTM + CloudWatch + Obsidian (“Winning Prompts”, “Failed Content”, format thắng = reach/CTR cao hơn median của 3 bài gần nhất cùng niche/CTA/nền tảng).

## 9. SOP Xử lý sự cố
| Sự cố                              | Hành động ngay + Sau sự cố |
|------------------------------------|-----------------------------|
| Account bị bóp tương tác           | Nội dung thật 7 ngày + ngâm lại + root cause |
| AI hallucination / nội dung nhạy cảm | Dừng auto + cập nhật prompt + root cause |
| Nội dung bị từ chối                | Flag + regenerate |
| Bạn bận                            | Auto-pilot top content |
