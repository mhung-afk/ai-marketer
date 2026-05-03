**✅ TUẦN 1 ĐÃ TỐI ƯU – PHIÊN BẢN 2.0 (Tích hợp Feedback Gemini 100%)**  
**Ngày:** 28/04/2026  
**Mục tiêu vẫn giữ nguyên:** Chọn xong **1 ngách duy nhất** + setup fanpage + scraper/caption chạy + 5–7 bài đăng thử + thu thập data thực tế.

Tôi đã đọc kỹ feedback của Gemini → rất sát và thực tế. Tôi **tích hợp toàn bộ** 3 điểm tinh chỉnh + cảnh báo AIGC vào checklist này để kế hoạch của chúng ta “vận hành mượt” hơn ngay từ ngày đầu.

### 1. Niche Selection Framework (Cập nhật – Thêm “AI Content Moat”)
**Bước 1A: Hard Filter Compliance** (giữ nguyên)  
**Bước 1B: Bảng chấm điểm MỚI (đã điều chỉnh trọng số)**

| Tiêu chí                  | Trọng số | Cách chấm (1–10)                  | Ghi chú thực tế (tuần 1) |
|---------------------------|----------|-----------------------------------|--------------------------|
| **Affiliate Margin**      | 25%      | ≥10–15%                           | Check Shopee Affiliate   |
| **Viral Potential**       | 20%      | Dễ chia sẻ                        | Trend TikTok/FB          |
| **AI Content Fit**        | 15%      | Dễ quote/trend                    | Quote + hình Nano Banana |
| **AI Content Moat** *(mới)* | **15%**  | AI tạo hình **độc bản**, ít cạnh tranh trực tiếp | Phong thủy hiện đại, Decor Việt tối giản, Phụ kiện GenZ độc lạ… |
| **Catalog Depth**         | 10%      | >500 sản phẩm                     | Shopee search            |
| **Seasonality**           | 10%      | Ổn định hoặc tận dụng mùa         | -                        |
| **Tổng**                  | **100%** | **≥85 điểm** mới pass             | -                        |

**Lý do thêm AI Content Moat**: Gemini đúng – một số ngách “dễ” như Gia dụng thông minh lại cạnh tranh cực cao và hình AI dễ bị “trông giống nhau”. Chúng ta muốn ngách mà **Nano Banana 2** tạo ra hình ảnh độc, đẹp, mang dấu ấn Việt Nam → dễ viral organic hơn.

**Bước 1C:** So sánh top 3 ngách → chọn **1 ngách DUY NHẤT**. Ghi file `Niche_Selected.md`.

**Chốt:** Decor Phòng Ngủ Chill & Phong Thủy Hiện Đại (tập trung chữa lành, năng lượng, cảm xúc)

### 2. Warm-up Tài khoản (Tinh chỉnh mới – Bắt buộc)
- Trước khi đăng bài đầu tiên: Dùng **điện thoại thật** lướt TikTok/Facebook **15–20 phút/ngày** trong ngách đã chọn.
- Hành động: Like 20–30 bài, comment 5–7 comment tự nhiên, follow 10–15 tài khoản cùng ngách.
- Mục tiêu: Tạo tín hiệu “người dùng thật” → giảm nguy cơ shadowban ngay tuần đầu.

**Chốt:** 
- Tên Fanpage Facebook: Phòng Ngủ Chữa Lành, Hoãn triển khai Tiktok
- Đổi tên Fanpage thành “Phòng Ngủ Chữa Lành”
- Đổi Avatar + Banner
- Đăng bài Rebranding
- Đã và đang warm-up thường xuyên

### 3. Tech Stack MVP – Scraper (Tinh chỉnh theo Gemini + tình hình 2026)
**Chiến lược mới (rất quan trọng):**

| Giai đoạn          | Công cụ chính                  | Lý do / Fallback |
|--------------------|--------------------------------|------------------|
| Ngày 1–2           | **Crawlee + Playwright** (như plan gốc) | Miễn phí, full control |
| Nếu block >2 lần   | **TikAPI** (tikapi.io) hoặc Apify TikTok Scraper (free tier) | Nhanh, ổn định, ít bảo trì |
| Shopee sản phẩm    | Crawlee trước → Apify Shopee Scraper nếu cần | Hỗ trợ VN tốt |

**Hành động tuần 1:**
- Ưu tiên code scraper **trend TikTok** (hashtag + từ khóa ngách).
- Nếu mất >4 giờ fix anti-bot → **chuyển ngay sang TikAPI** (có free trial, sau đó ~$49/tháng nhưng chỉ dùng ít).
- Script caption vẫn dùng Claude Haiku + prompt caching.

### 4. Quy trình Vận hành Thủ Công + Compliance (Cập nhật)
Mỗi bài **BẮT BUỘC**:
- Caption có dòng: “Ảnh minh họa bằng AI • Link affiliate, mình nhận hoa hồng nhỏ”
- TikTok: Bật **AI-generated content** label + watermark nếu có
- Fanpage: Bật **AI-generated content** label + Thêm disclaimer rõ ràng

**Format tuần 1:** Vẫn chỉ **2 format**:
1. Quote + hình đẹp + CTA
2. Before/After hoặc “Mẹo hay” (nếu ngách phù hợp)

### 5. Checklist Ngày-by-Ngày (Tuần 1 – Đã tinh chỉnh)
- **Ngày 1**: Hoàn tất Niche Selection (bảng chấm điểm mới + AI Content Moat) → Quyết định ngách.
- **Ngày 2**: Tạo Fanpage + TikTok + Warm-up 15 phút + setup scraper + caption script.
- **Ngày 3–6**: Đăng **1–2 bài/ngày** + warm-up + ghi log (Google Sheet).
- **Ngày 7**: 
  - Review data
  - **Phân tích lý do format thất bại** (mới – theo Gemini)
  - Tinh chỉnh prompt
  - Viết “Week 1 Report” trong Obsidian/Notion

**Google Sheet template theo dõi** (cột mới):
- Bài | Ngày | Format | Reach | Like | Save | Comment | Lý do nghi ngờ thất bại (nếu <200 reach) | Ghi chú prompt

### 6. Checklist bổ sung Ngày 7 (theo Gemini)
- Phân tích **tại sao format X fail** (ví dụ: hình không hấp dẫn, caption không trigger cảm xúc, CTA yếu…).
- So sánh median reach của 2 format.
- Cập nhật “Winning Prompts” và “Failed Content” folder.

### 7. Ngân sách & Rủi ro (Giữ nguyên + nhắc)
- Tuần 1 dự kiến: **< $3** (Claude Haiku + Nano Banana).
- **Cảnh báo đỏ**: Thiếu nhãn AIGC → tài khoản bay màu sau 3 bài (2026 rất nghiêm).