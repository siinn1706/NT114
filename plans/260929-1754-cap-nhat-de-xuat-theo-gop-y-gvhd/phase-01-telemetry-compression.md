---
phase: 1
title: "Chiến lược nén và biến đổi telemetry"
status: completed
effort: 2h
---

# Phase 01 — Chiến lược nén và biến đổi telemetry

## Góp ý gốc
> Định dạng và tiền xử lý dữ liệu telemetry: cần làm rõ chiến lược nén/tổng hợp hoặc biến đổi cấu trúc
> dữ liệu trước khi đưa vào mô hình tìm kiếm/LLM, để tránh vượt quá giới hạn cửa sổ ngữ cảnh và tối ưu chi phí tính toán.

## Mục tiêu
Viết mục mới **5.1 Tiền xử lý và nén telemetry** cho Proposal. Mục này mô tả đường đi từ telemetry thô đến
một **incident card**, tức là bản tóm tắt có cấu trúc của sự cố với số token có giới hạn.

## Nội dung cần đưa vào (bản nháp kỹ thuật)

**Cửa sổ phân tích.** Lấy dữ liệu trong khoảng [t_inject − W_normal, t_inject + W_abnormal]. Đoạn trước thời
điểm tiêm lỗi dùng làm baseline, đoạn sau là cửa sổ bất thường. Ví dụ W_normal = 10 phút và W_abnormal = 5 phút,
sẽ được tinh chỉnh trên tập validation.

**Metric → đặc trưng bất thường**
- Với mỗi cặp (service, metric), tính robust z-score so với baseline: z = (x − median) / (1.4826 · MAD).
- Tóm mỗi chuỗi thời gian thành một vài số: max |z|, thời điểm bắt đầu bất thường, hướng tăng/giảm, % thay đổi.
- Chỉ giữ top-K metric bất thường nhất cho mỗi service (K≈5). Phần còn lại bị loại khỏi input của LLM.

**Log → template**
- Trích template bằng Drain3 để gom các dòng log gần giống nhau vào cùng một mẫu.
- Đếm tần suất từng template trong cửa sổ bình thường và cửa sổ bất thường. Giữ template mới xuất hiện, template tăng đột biến, và template chứa ERROR/WARN hoặc exception.
- Mỗi template chỉ giữ một dòng log ví dụ, tối đa N template cho mỗi service (N≈5).

**Trace → đồ thị gọi**
- Gộp các span thành cạnh caller→callee, mỗi cạnh có: số lần gọi, error rate, latency p50/p95/p99 và độ thay đổi so với baseline.
- Chỉ giữ các cạnh có latency hoặc error rate thay đổi lớn. Đánh dấu dịch vụ nằm ở đầu chuỗi lan truyền, tức callee bất thường mà các callee phía dưới của nó vẫn bình thường.

**Lọc trước ứng viên (pre-ranking).** Tính điểm bất thường tổng hợp cho từng service, dùng weighted sum
của ba nguồn metric, log và trace. Chỉ top-M service (M≈5) được mô tả chi tiết trong incident card; các service
còn lại chỉ ghi một dòng tóm tắt.

**Incident card và ngân sách token**
- Định dạng JSON hoặc YAML gọn, gồm các khối: `summary`, `services[]` (metric/log/trace evidence), `call_graph`, `timeline`.
- Ngân sách cứng khoảng 4k token cho telemetry. Chia theo phân cấp: service xếp hạng cao được nhiều token hơn. Nếu vượt ngân sách thì cắt từ service có hạng thấp nhất.
- Incident card được dùng cho hai việc: làm truy vấn của Hybrid Retrieval (phase 02) và làm ngữ cảnh cho LLM.

**Cách đánh giá chiến lược nén**
- Số token trung bình và tỷ lệ nén (token thô / token sau nén), thời gian xử lý và chi phí suy luận cho mỗi sự cố.
- Ablation: bỏ lần lượt từng nguồn (metric, log, trace) và thử nhiều mức ngân sách (1k/2k/4k/8k), đo ảnh hưởng tới AC@k.
- Recall của bước pre-ranking: tỷ lệ sự cố mà dịch vụ gốc vẫn nằm trong top-M. Đây là cận trên của các bước sau.

## Tệp liên quan
- Đọc: `D:/NT114/Proposal.docx` (mục 4.1, 5)
- Ghi: chỉ viết nội dung vào phase này. Việc ghép vào docx làm ở phase 06.

## Các bước
1. Kiểm tra cấu trúc thật của RE2-OB trong RCAEval: tên cột metric, định dạng log và trace, thời điểm tiêm lỗi. Điều chỉnh bản nháp cho khớp.
2. Chốt các tham số mặc định (W, K, N, M, ngân sách token) và ghi rõ là "sẽ tinh chỉnh trên tập validation".
3. Viết mục 5.1, khoảng 1–1,5 trang, có một sơ đồ pipeline gồm raw → feature → pre-rank → incident card.

## Kiểm tra
- Mỗi kỹ thuật được nêu đều có tham số và lý do chọn.
- Có ít nhất một độ đo định lượng cho hiệu quả nén.

## Rủi ro
- RE2-OB có thể thiếu một vài loại dữ liệu ở một số sự cố. Khi đó incident card phải ghi rõ nguồn nào bị thiếu, không được bịa bằng chứng.
