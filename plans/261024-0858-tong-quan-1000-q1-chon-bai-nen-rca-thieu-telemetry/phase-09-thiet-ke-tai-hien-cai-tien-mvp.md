---
phase: 9
title: "Thiết kế tái hiện, cải tiến, phép thử và đề cương MVP"
status: done-conditional
receipt: work/receipts/09-design-check-05.json
owner_skills: [nckh-method, nckh-research, nckh-statistics]
---

# Giai đoạn 09: Thiết kế sau chọn bài

## Yêu cầu

- Chạy trên bài đề xuất ở phase 08, ghi rõ “có điều kiện: chờ chủ dự án chấp nhận bài nền”.
- Chỉ tạo tài liệu thiết kế; không code, không chạy model, không sửa protocol v2 hay `decisions.md`.
- Không khẳng định novelty: mỗi giả thuyết cải tiến có kiểm prior work với truy vấn, ngày, kết quả; phát biểu dạng “chưa thấy trong tìm kiếm X tại ngày Y”.

## Tệp

- Đọc: `research/selection-memo.md`, `research/cards/t3/<bài nền>.md`, [protocol v2](../261018-2300-single-llm-simplification-and-evaluation-hardening/design/protocol-v2.md), [decisions.md](../261018-2300-single-llm-simplification-and-evaluation-hardening/decisions.md), [data contract](../../nt114-rca/nt114-rca/docs/data_contract.md), [llms.txt](../../llms.txt).
- Tạo: `design/reproduction-protocol.md`, `design/improvement-hypotheses.md`, `design/test-matrix.md`, `design/mvp-outline.md`, `work/prior-work-improvements.csv`, `work/receipts/09-*.json`.

## Các bước

1. **Tái hiện** (`reproduction-protocol.md`): số liệu đích của bài (bảng/trang, verdict evidence), code/commit, dataset và căn chỉnh với bundle NT114 (ID sự cố, preprocessing, split, granularity, candidate set), môi trường, sai số chấp nhận được định trước, điều kiện “tái hiện đạt/một phần/không đạt”, thứ tự: tái hiện nguyên bản → chuyển sang một LLM cục bộ → chạy trên bundle NT114.
2. **Cải tiến** (`improvement-hypotheses.md`): từ limitation/failure mode quan sát được trong card và từ lớp đo NT114 (telemetry thiếu, confidence/abstention), viết 2–4 giả thuyết có thể bác bỏ: cơ chế, dự đoán phân biệt, falsifier, chi phí; liên hệ với H1 (hỗ trợ, độc lập hay xung đột).
3. Kiểm prior work cho từng giả thuyết (tạp chí + hội nghị + preprint), ghi `prior-work-improvements.csv`.
4. **Phép thử** (`test-matrix.md`): đơn vị độc lập (injection), điều kiện thiếu telemetry, comparator (bài nền tái hiện, B1/B1m, L0/L1 của protocol v2), endpoint, kiểm định (cluster bootstrap/sign-flip/Holm đã có), MDE theo [research/06](../../research/06_statistics_validation.md), quy tắc DEV → test, ngân sách.
5. **MVP** (`mvp-outline.md`): phạm vi tối thiểu chứng minh được tái hiện + một cải tiến, thành phần mới cần code (đối chiếu module hiện có), mốc, cổng, cái gì cần kế hoạch nckh-plan mới.
6. Review ngữ cảnh mới (nckh-reviewer) cho bốn tài liệu.

## Kiểm tra

- Mỗi giả thuyết có falsifier và dòng prior work; không câu nào khẳng định “đầu tiên”/“mới” không giới hạn.
- Mỗi số đích tái hiện có locator + verdict.
- `test-matrix.md` không dùng DEV/mock/oracle làm kết quả chính; không đưa nhãn ca đang hỏi vào prompt (đối chiếu `llms.txt`).
- Review không còn phát hiện chặn mở.

## Rủi ro và hoàn tác

- Chủ dự án không chấp nhận bài nền: phase 09 thành `stale`; chạy lại với bài khác từ T3.
- Giả thuyết cải tiến đụng H1/protocol v2: ghi như quyết định mở cho chủ dự án, không sửa protocol.
- Hoàn tác: tài liệu design có version; không có thay đổi ngoài thư mục kế hoạch.
