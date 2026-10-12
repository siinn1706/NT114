# Phase 04 — Độ tin cậy hiệu chỉnh và bằng chứng kiểm được (RQ2, RQ3)

## Mục tiêu
Trả lời "độ chính xác bao nhiêu %, vì sao chẩn đoán như thế, vì sao ra con số đó" (note 29/09) bằng ba thứ đo được.

## 1. Độ tin cậy (vì sao ra con số đó)
- So sánh các nguồn độ tin cậy: verbalized của LLM; xác suất token của nhãn; độ nhất quán qua nhiều lần lấy mẫu
  (self-consistency); điểm từ bước kiểm cạnh của Phase 3; kết hợp các nguồn.
- Hiệu chỉnh trên fold huấn luyện (temperature scaling hoặc isotonic), đánh giá trên fold kiểm tra và chéo hệ thống.
- Độ đo: ECE, Brier, reliability diagram, đường selective accuracy–coverage (từ chối khi độ tin cậy thấp → chuyển người vận hành).
- Câu trả lời mong muốn có dạng: "khi hệ thống báo 80%, tỉ lệ đúng thực tế là 78% [CI]".

## 2. Bằng chứng (vì sao chẩn đoán như thế)
- Kiểm tất định: mọi evidence id tồn tại trong incident card hoặc tài liệu đã truy hồi (đã có ở Proposal_v2 mục 6.5).
- **Kiểm phản thực:** bỏ bằng chứng LLM đã trích rồi chạy lại; nếu kết luận không đổi thì bằng chứng đó không phải lý do
  thật. Đo độ nhạy này như một chỉ số faithfulness, bổ sung cho LLM-as-a-Judge.
- Giữ khung đánh giá hai tầng của Proposal_v2 (rubric, quy tắc chuyển tầng, Cohen's κ).

## 3. Độ chính xác (bao nhiêu %)
- Báo mọi con số kèm CI 95% bootstrap; so cặp bằng paired bootstrap hoặc McNemar.

## Kiểm tra
- Hiệu chỉnh không dùng dữ liệu kiểm tra; ghi rõ fold nào dùng để fit.
- Với cỡ mẫu nhỏ, chọn số bin ECE hợp lý và báo thêm dạng không bin (ví dụ ECE theo kernel hoặc Brier) để tránh kết luận
  dựa trên một cách chia bin.

## Rủi ro
LLM 7–8B có thể cho độ tin cậy verbalized gần như hằng số; khi đó đó chính là một phát hiện, và nguồn self-consistency
hoặc điểm kiểm cạnh trở thành phương án chính.
