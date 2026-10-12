---
phase: 4
title: "Khung đánh giá giải thích đa tầng"
status: completed
effort: 2h
---

# Phase 04 — Khung đánh giá giải thích đa tầng

## Góp ý gốc
> Thành phần giải thích: nên tìm hiểu và xây dựng khung đánh giá định lượng đa tầng. Ví dụ ở tầng 1, LLM-as-a-Judge
> đánh giá dựa trên bộ tiêu chí chuẩn kèm trọng số; các kết quả có độ tin cậy thấp từ tầng 1 được chuyển sang tầng 2
> để chuyên gia trực tiếp thẩm định.

## Mục tiêu
Viết **mục 6.4 Đánh giá phần giải thích** và bổ sung vào mô tả trường `Explain` ở mục 4.2. Trường này phải trích dẫn
bằng chứng có ID, ví dụ `metric:cartservice.cpu`, để có thể kiểm tra tự động.

## Nội dung cần đưa vào

**Tầng 1 — LLM-as-a-Judge.** Chấm trên toàn bộ 90 sự cố.

| Tiêu chí | Mô tả | Thang | Trọng số |
|---|---|---|---|
| Faithfulness (bám bằng chứng) | Mọi nhận định đều có trong incident card hoặc tài liệu đã truy hồi | 1–5 | 0.35 |
| Correctness (tính đúng) | Lập luận nhất quán với service gốc và loại lỗi thật | 1–5 | 0.25 |
| Evidence completeness | Nêu đủ các tín hiệu chính (metric, log, trace) | 1–5 | 0.20 |
| Actionability | Gợi ý bước kiểm tra tiếp theo hợp lý | 1–5 | 0.10 |
| Clarity | Ngắn gọn, dễ hiểu với người vận hành | 1–5 | 0.10 |

- Điểm tổng S = Σ w_j · s_j, chuẩn hóa về [0,1].
- Kiểm tra tất định trước khi gọi judge: mọi ID bằng chứng được trích phải tồn tại trong input. Tỷ lệ trích dẫn hợp lệ là một chỉ số riêng.
- Judge là mô hình **open-weight** (không dùng API trả phí), khác họ với mô hình sinh để tránh self-preference. Ví dụ: sinh bằng Qwen2.5-7B-Instruct, chấm bằng Llama-3.1-8B-Instruct, hoặc bản lớn hơn lượng tử hóa 4-bit nếu GPU đủ; chốt tên mô hình khi chạy thử.
- Vì judge open-weight cỡ nhỏ kém tin cậy hơn các mô hình lớn, tầng 2 và độ đo đồng thuận càng quan trọng. Nêu điều này trong phần hạn chế.
- Giảm thiên lệch của judge: prompt judge có rubric và ví dụ neo cho từng mức điểm; bắt judge viết lý do trước rồi mới cho điểm; chấm n = 3 lần với temperature > 0.
- **Độ tin cậy** của một kết quả được tính từ: độ lệch chuẩn giữa 3 lần chấm, và độ tự tin do judge tự báo cáo.

**Quy tắc chuyển xuống tầng 2.** Một kết quả được chuyển xuống nếu thỏa một trong các điều kiện:
(a) độ lệch chuẩn của S lớn hơn τ_σ, ví dụ 0.15;
(b) S nằm trong vùng biên [0.4, 0.6];
(c) judge chấm Faithfulness cao nhưng kiểm tra tất định phát hiện trích dẫn không hợp lệ;
(d) thuộc mẫu ngẫu nhiên khoảng 15% dùng để hiệu chỉnh judge, lấy cả những ca judge rất tự tin.

**Tầng 2 — Chuyên gia thẩm định.** Người chấm là GVHD và 1–2 người có kinh nghiệm vận hành.
- Chấm theo đúng rubric của tầng 1. Người chấm không biết điểm của judge và không biết output đến từ phương pháp nào (chấm mù).
- Điểm chuyên gia thay thế điểm judge ở các ca được chuyển xuống.
- Đo độ đồng thuận: giữa các chuyên gia dùng Cohen's κ (hoặc Krippendorff's α nếu có 3 người); giữa judge và chuyên gia dùng Spearman ρ và κ.
  Nếu judge đồng thuận kém, ví dụ κ < 0.4, thì chỉnh prompt hoặc rubric và báo cáo kết quả này như một phát hiện.

**Kết quả báo cáo.** Điểm giải thích trung bình theo từng phương pháp, tỷ lệ ca bị chuyển xuống tầng 2, độ đồng thuận
judge–chuyên gia, và tỷ lệ trích dẫn hợp lệ.

## Các bước
1. Tìm 2–3 tài liệu về LLM-as-a-Judge (ví dụ Zheng et al., 2023, "Judging LLM-as-a-Judge with MT-Bench…") và về độ tin cậy của judge. Kiểm tra trích dẫn thật ở phase 07.
2. Viết mục 6.4, có bảng rubric và sơ đồ luồng tầng 1 → quy tắc chuyển → tầng 2.
3. Bổ sung vào mục 4.2: trường `Explain` phải kèm danh sách ID bằng chứng.

## Kiểm tra
- Rubric có trọng số và tổng trọng số bằng 1. Quy tắc chuyển tầng có ngưỡng số cụ thể. Có độ đo đồng thuận.

## Rủi ro
- Chuyên gia có ít thời gian. Giới hạn tầng 2 ở khoảng 30 ca và ước lượng trước khoảng 3–5 phút cho mỗi ca.
