# Giai đoạn 05 – Chấm điểm và xếp hạng hướng nghiên cứu

Trạng thái: hoàn thành 12/10/2026 ở mức bản nháp một người chấm (chưa có hai thành viên chấm độc lập), biên nhận `work/direction-scores.csv` `work/sensitivity.csv` `work/direction-ranking.csv` · Thực thi: nckh-cook (dùng nckh-research) · Phụ thuộc: [04](phase-04-tong-hop-y-tuong-va-gap.md) · Quay về [plan](plan.md)

Biên nhận: `work/direction-scores.csv` `work/sensitivity.csv` `work/direction-ranking.csv`

## Yêu cầu

- Ghép gap `confirmed`/`partially-filled` với thẻ ý tưởng thành **5–8 hướng ứng viên**; mỗi hướng là một đóng góp chính, không phải một danh sách khối kỹ thuật.
- Chấm mỗi hướng theo bảng dưới, thang 1–5, mỗi điểm kèm một câu lý do và nguồn (gap id, thẻ ý tưởng, mã đoạn Proposal).
- Kiểm độ nhạy: chấm lại với trọng số đều và với trọng số "ưu tiên khả thi"; ghi hướng nào giữ top 3 ở cả ba cách.
- Viết hồ sơ ngắn cho **2–3 hướng tốt nhất**.

| Tiêu chí | Câu hỏi | Trọng số |
|---|---|---|
| Độ mới | Gap còn đứng sau bước cố bác bỏ đến mức nào? | 0,25 |
| Khả thi | Làm được với LLM open-weight 7–8B, GPU Kaggle/Colab, 2 sinh viên, ~4–6 tháng? | 0,20 |
| Đánh giá được | Có dữ liệu công khai đủ (RCAEval RE1/RE2/RE3, nhiều hệ thống), độ đo đã chuẩn? | 0,15 |
| Tận dụng Proposal | Dùng lại được bao nhiêu pipeline hiện có (5.2–6.6)? | 0,15 |
| Khớp góp ý GVHD | 2–3 ứng dụng, tìm nơi phát sinh trên đường lan truyền, trả lời "bao nhiêu %, vì sao" | 0,15 |
| Khả năng đăng Q1 | Có tạp chí Q1 (đã kiểm SJR) từng đăng bài cùng loại trong corpus không? | 0,10 |

Hồ sơ mỗi hướng tốt: phát biểu đóng góp một câu; RQ (2–4); giả thuyết; dữ liệu và chia tập chống rò rỉ; baseline (gồm cả baseline từ bài Q1 đã đọc); độ đo; thí nghiệm tối thiểu chứng minh được giả thuyết trong 4 tuần; 2–3 tạp chí đích kèm quartile và bài tương tự đã đăng; rủi ro; điều kiện dừng (kết quả nào thì bỏ hướng).

## Tệp

- Đọc: `work/gaps.csv`, `work/ideas25.csv`, `work/concept-matrix.csv`, [proposal-paragraphs.txt](source-review/proposal-paragraphs.txt), `note/note-29-9.txt`.
- Tạo: `work/direction-scores.csv`, `work/sensitivity.csv`.

## Các bước

1. Viết các hướng ứng viên từ gap + ý tưởng; bỏ hướng chỉ dựa trên gap `refuted`.
2. Hai thành viên chấm độc lập, so và thống nhất; ghi điểm lệch ≥ 2.
3. Tính điểm có trọng số và hai cách trọng số kiểm độ nhạy.
4. Viết hồ sơ cho 2–3 hướng top; với mỗi tạp chí đích, kiểm lại quartile trong tệp SJR.

## Kiểm tra

- Mỗi điểm có lý do và nguồn truy được.
- Script tính điểm chạy lại cho cùng kết quả.
- Mỗi hướng top có thí nghiệm tối thiểu chạy được trên dữ liệu đã có, không cần dữ liệu riêng.
- Không hướng nào được ghi là "chưa ai làm" nếu gap của nó chỉ ở mức `partially-filled`; khi đó ghi rõ điểm khác biệt.

## Rủi ro / hoàn tác

- Thiên vị Proposal hiện có (chấm "tận dụng" quá cao): trọng số độ nhạy "ưu tiên độ mới" để lộ ra.
- Hướng quá rộng cho một bài báo: tách thành đóng góp chính + phần phụ.
- Hoàn tác: bảng điểm là CSV, chấm lại được.
