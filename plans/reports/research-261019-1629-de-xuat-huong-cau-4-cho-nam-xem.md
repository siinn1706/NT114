# Đề xuất: đưa câu 4 (thiếu telemetry hay mất khi tóm tắt) vào NT114

Ngày: 19/10/2026. Người đề xuất: Trí. **Trạng thái: đề xuất, chờ Nam xem.** File này không đổi plan, protocol v2,
`decisions.md` hay code. Nam đọc rồi quyết có đưa vào plan 261018 hay không.

## Kết luận ngắn

Câu 4 **không nên thay H1**. Số liệu `research/04` cho thấy trên RCAEval, bản tóm tắt ở điều kiện `full` gần như luôn
nêu tên dịch vụ gốc, nên phần "mất khi tóm tắt" rất nhỏ ở bộ dữ liệu chính. Ngoài ra, DecompRCA (NeurIPS 2026) đã công
bố một phép tách lỗi gần với câu này trên cùng RE1.

Phần còn đáng làm là một **phân tích phụ cho H1**, chi phí thấp:
1. Tách "dữ liệu thô không có dấu hiệu" khỏi "có dấu hiệu nhưng bản tóm tắt bỏ", ở những ca bản tóm tắt không nêu tên gốc.
2. Can thiệp trên khoảng 48 ca đó: thêm dòng của dịch vụ gốc vào bản tóm tắt rồi hỏi lại LLM.

## 1. Câu 4 hỏi gì

Note 16/10, câu 4: lỗi RCA đến từ telemetry bị thiếu, hay từ bằng chứng bị mất trong quá trình tóm tắt? Mỗi ca sai
thuộc một trong ba nhóm:

| Nhóm | Điều kiện | Ứng với `research/02` (H3) |
|---|---|---|
| A | Telemetry thô không có dấu hiệu của dịch vụ gốc | Một phần của `named = false` |
| B | Telemetry thô có dấu hiệu, bản tóm tắt không nêu tên gốc | Phần còn lại của `named = false` |
| C | Bản tóm tắt nêu tên gốc, LLM vẫn xếp sai | "ranking failure despite the root being named" |

`research/02` đã có cột `named` (E) và `in_candidates` (C), nhưng **chưa tách A khỏi B**. `named = false` gộp cả hai
trường hợp.

## 2. Số liệu `research/04` (không gọi model, chạy 18–19/10)

### 2.1 Bản tóm tắt ở `full` có nêu tên gốc không

| Bộ dữ liệu | Nêu tên | Không nêu tên |
|---|---|---|
| RCAEval test | 216/218 (99,1 %) | 2 |
| RCAEval val (DEV) | 140/143 (97,9 %) | 3 |
| Nezha test | 80/97 (82,5 %) | 17 |
| RCA100 test | 77/86 (89,5 %) | 9 |
| AIOps2025 test | 298/318 (93,7 %) | 20 |

`in_candidates = 1` ở mọi bản ghi, và không bản ghi nào bị cắt vì giới hạn ký tự (`research/04` §2.1, §2.3).

**Hệ quả cho câu 4:**
- Số ca không nêu tên là **cận trên** của A + B ở `full`. Trên RCAEval test, cận trên đó là 2/218. Vì vậy trên bộ chính,
  gần như mọi ca sai ở `full` sẽ thuộc nhóm C. Giả thuyết ban đầu ("bước tóm tắt làm mất nhiều bằng chứng, nhất là ở
  Train Ticket") không đứng trên RCAEval.
- Phần còn mở nằm ở Nezha (17/97), AIOps2025 (20/318) và RCA100 (9/86). Đây là các tầng nhỏ, khoảng tin cậy sẽ rộng
  (`research/04` §4, ý 5).

### 2.2 Khi bỏ bớt dữ liệu

`no_metric` là điều kiện làm mất tên gốc nhiều nhất: RCA100 69/86, AIOps2025 93/304, RCAEval test 42/108, Nezha 20/97
(`research/04` §2.3). Ở đây telemetry bị bỏ có chủ đích, nên phần lớn thuộc nhóm A theo định nghĩa, không phải lỗi của
bộ tóm tắt. `blind_root` là thao tác yếu: nó chỉ làm mất tên gốc ở 1/69 ca RCAEval test, và bản tóm tắt giống hệt
`full` ở 20/69 ca (`research/04` §4, ý 2).

## 3. Chồng lấn với DecompRCA

Theo [báo cáo Elicit](research-261019-tong-quan-elicit-chon-dong-gop-nt114.md) §7 và các phát hiện F-041 đến F-044:

- DecompRCA tách top@k thành Retrieval@K × Rerank@k trên RCAEval RE1, 125 sự cố mỗi hệ thống (poster NeurIPS 2026,
  https://neurips.cc/virtual/2026/poster/139698; arXiv 2609.36686).
- Lỗi xếp hạng chiếm phần lớn: tỉ lệ lỗi retrieval 0,00–0,09, tỉ lệ lỗi reranking 0,10–0,26 (F-042).
- Repo của bài trả 404 khi kiểm ngày 19/10 (F-044). Tiền xử lý dùng `main-ase.py`, khác `main.py` của NT114 (F-043).
- DecompRCA không đo confidence hay abstention, nên không chồng lấn H1.

**Điểm khác của câu 4 so với DecompRCA, cần xác nhận lại:** câu 4 hỏi về bước tóm tắt telemetry thành văn bản cho LLM.
Theo hồ sơ trong repo, giai đoạn retrieval của DecompRCA là bộ lấy ứng viên (K = 15), không phải bộ tóm tắt bằng chứng.
Hồ sơ không nói bài có đo việc bản tóm tắt bỏ sót tên gốc hay không. Trí chưa đọc toàn văn; cần người đã đọc
(`private/fulltext/261019/2609.36686.txt`) xác nhận trước khi dùng điểm khác này trong bài.

## 4. Đề xuất cụ thể (phân tích phụ của H1)

| # | Việc | Dữ liệu | Chi phí | Ghi chú |
|---|---|---|---|---|
| P1 | Báo cáo mọi contrast của H1 theo tầng `named` | Đã có từ `rca.visibility` | Không thêm | `research/04` §5 đã yêu cầu điều này |
| P2 | Tách A khỏi B ở các ca `named = false`: kiểm telemetry thô của dịch vụ gốc với ngưỡng lỏng hơn ngưỡng tóm tắt (ví dụ metric z ≥ 2, có log lỗi, có cạnh trace lệch), báo độ nhạy theo vài ngưỡng | Khoảng 48 ca `full` trên test (2 + 17 + 9 + 20), cộng các điều kiện thiếu dữ liệu | Chỉ CPU | Nhãn chỉ dùng ở bước phân tích |
| P3 | Can thiệp: ở các ca nhóm B, thêm dòng của dịch vụ gốc vào bản tóm tắt rồi hỏi lại LLM; đo AC@1 và confidence trước và sau | Các ca nhóm B từ P2 | Một prompt mỗi ca nhóm B và mỗi điều kiện (n = 10 mẫu mỗi prompt), nhiều nhất vài trăm | `research/02` ghi rằng muốn khẳng định nhân quả thì cần can thiệp kiểu này, và code chưa có. Bản tóm tắt sau can thiệp có chứa nhãn, nên chỉ là phân tích, không phải phương pháp |

P1 và P2 không đụng prompt v1, `evidence.py` hay split. P3 cần một arm phân tích mới, nên phải được ghi vào protocol v2
trước khi chạy.

## 5. Rủi ro

- Các tầng nhỏ (2 ca RCAEval, 9 ca RCA100) cho khoảng tin cậy rất rộng. Kết quả chủ yếu mang tính mô tả.
- Nếu P2 cho thấy hầu hết ca `named = false` thuộc nhóm A, câu 4 khép lại với một kết quả âm: bước tóm tắt không phải
  nút thắt. Kết quả đó vẫn có ích cho phần Threats to validity của bài H1.
- Nếu toàn văn DecompRCA có đo việc bỏ sót trong bản tóm tắt, điểm khác ở mục 3 mất và chỉ còn P1 để giữ.

## Câu hỏi cho Nam

1. Có đưa P1–P3 vào plan 261018 thành phân tích phụ của H1 không, hay chỉ giữ P1?
2. DecompRCA có đo việc bản tóm tắt hoặc bộ tiền xử lý bỏ sót tên dịch vụ gốc không? Nam đã đọc toàn văn.
3. Nếu làm P3, đặt arm can thiệp vào protocol v2 ở mục nào để không lẫn với họ confirmatory?
