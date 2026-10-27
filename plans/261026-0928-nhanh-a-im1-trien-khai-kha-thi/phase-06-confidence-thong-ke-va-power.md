---
phase: 6
title: "Confidence theo registry, bootstrap group_id, quy ước đọc CI, MDE/power"
status: planned
owner_skills: [nckh-statistics]
---

# Giai đoạn 06: Confidence, thống kê, power

## Yêu cầu

- Confidence: chỉ các nguồn trong registry `src/rca/confidence.py`, từ chính lời gọi của ô. `token_prob` và độ tin cậy tự khai giữ trạng thái chưa xác thực, không vào bảng headline. Không thêm nguồn từ lời gọi LLM thứ hai.
- D10: thêm bootstrap theo `group_id` của split làm **phân tích độ nhạy**, giữ lặp trong nhóm; phân tích chính không đổi.
- Quy ước đọc CI cho mọi bảng R-a và IM1: CI chứa 0 là chưa đủ bằng chứng; CI nằm dưới 0 là bằng chứng tác hại; CI nằm trong ±SESOI là bằng chứng loại trừ hiệu ứng có ý nghĩa thực tiễn. Không viết "bác bỏ" khi CI chứa 0.
- Tính lại MDE/power cho H1 với mẫu số đã kiểm ở phase 02 (CPU). IM1 là thăm dò, không có cam kết confirmatory.

## Tệp

- Đọc: `src/rca/confidence.py`, `selective.py`, `contrasts.py`, `analyze.py`, `reproduce.py`, `tests/test_confidence.py`, `tests/test_contrasts.py`.
- Sửa có test: `contrasts.py`, `analyze.py`, `selective.py`, `cost.py` (bootstrap nhóm, nhãn diễn giải CI, khóa theo `arm`).
- Tạo trong thư mục kế hoạch: `work/h1-mde-recheck.md` kèm receipt.

## Các bước

1. Test trước cho bootstrap nhóm (fixture có lặp tương quan trong nhóm) và cho nhãn diễn giải CI ở ba trường hợp.
2. Sửa code; chạy test; tính MDE.

## Kiểm tra

- ~~Bootstrap nhóm không coi ba lần lặp là độc lập (trên fixture tương quan, CI theo nhóm không hẹp hơn CI theo injection).~~ Thay 2026-10-26 (D10-a): resample theo `group_id`, giữ lặp cùng nhóm; hai arm của contrast ghép cặp dùng cùng nhóm; fixture đối chiếu với một tham chiếu độc lập; phân tích chính không đổi, `group_id` là độ nhạy. Không đổi thuật toán hay seed để ép CI rộng hơn.
- `analyze.py`, `contrasts.py`, `selective.py`, `cost.py`: `arm` vào strata, khóa fit, pool và KEYS; dòng thiếu `arm` đọc là `l0` (retrieval none) hoặc arm retrieval hiện có (hybrid); test chứng minh không trộn arm và `l0`/retrieval không đổi.
- Không bảng headline nào dùng `token_prob`.
- `pytest` toàn bộ exit 0.

## Rủi ro và hoàn tác

- MDE với mẫu số mới lớn hơn SESOI 0.05: ghi thật, đưa thành câu hỏi cho chủ dự án trước M5; không đổi SESOI.
- Hoàn tác: hoàn nguyên diff ở `contrasts.py` hoặc `analyze.py`.
