# Phạm vi trace và baseline không dùng LLM trên 240 truy vấn train RE2-OB

Ngày 2026-11-02. Plan: [hướng A](../261102-1000-rclagent-telemetry-gap-aware-agent/plan.md), phase 2 và 4. `K/` là `plans/261026-1713-rclagent-tai-hien-toi-thieu/kaggle/`. Chỉ dùng train và val; không đụng test split (D12). Đây là mô tả, chưa có lượt chạy LLM nào trên 240 truy vấn này.

## 1. Kết luận

- Trace được giao không chứa span nào của dịch vụ lỗi ở 59/240 truy vấn train (24,6%) và 25/105 truy vấn val (23,8%). Ở mọi truy vấn như vậy, cửa sổ lỗi có ít nhất 396 trace khác đi qua dịch vụ lỗi. Nghĩa là bằng chứng có sẵn, chỉ nằm ngoài trace được giao.
- **Một bộ xếp hạng độ trễ vài dòng, không dùng LLM, đạt R@1 0,50 trên train** khi nhìn cả cửa sổ lỗi. Con số này cao hơn hẳn TraceRCA (0,083), MicroRank (0) và BARO (0,104). Đây là mức sàn mà phương pháp LLM phải vượt.
- Ở nhóm 59 truy vấn không có span GT, mọi bộ xếp hạng chỉ nhìn trace được giao đều cho R@1 bằng 0, đúng như cấu trúc dữ liệu buộc. Nhìn cả cửa sổ thì bộ xếp hạng độ trễ lên được 0,22–0,25. Như vậy M3 có tín hiệu để khai thác, nhưng tín hiệu đó yếu và kém đặc hiệu.
- Chưa có R@1 của RCLAgent trên cùng 240 truy vấn: S1 mới chạy 8 case. Phase 3 phải đặt RCLAgent gốc vào tập dev để có so sánh trực tiếp.

## 2. Phạm vi trace (phase 2)

Script `K/measure-trace-coverage.py` có 4 test, thoát 0. Output ở `K/runtime/trace-coverage/` (gitignored).

| Vai trò | Có span server của GT | Chỉ có span client gọi GT | Không có span của GT | Tổng | Case có mọi truy vấn không phủ / có ít nhất một |
|---|---|---|---|---|---|
| train | 171 | 10 | 59 | 240 | 5 / 17 trên 48 |
| val | 79 | 1 | 25 | 105 | 2 / 7 trên 21 |

- Theo dịch vụ trên train, phần không phủ tập trung ở emailservice (27/30) và checkoutservice (21/45), không có ở currencyservice và productcatalogservice. Trên val, emailservice có 15/30 và checkoutservice 10/30.
- Số trace khác đi qua GT trong cửa sổ lỗi, ở nhóm không phủ: thấp nhất 512 và trung vị 1 419 trên train; thấp nhất 396 và trung vị 516 trên val.

## 3. Baseline không dùng LLM (phase 4)

- **Môi trường:** RCAEval 1.11.0, commit `dc9f48786db50cf9469f2c596b79f01907d4ac91`, cài trong `K/runtime/rcaeval-env`. Ví dụ BARO của chính RCAEval chạy được.
- **Code:** script `K/run-non-llm-baselines.py`; test `K/test-run-non-llm-baselines.py` có 24 test, thoát 0. Controller đã chạy lại test.
- **Thời gian chạy:** khoảng 49 phút.
- **Đầu vào của TraceRCA, MicroRank và BARO:** dữ liệu cả case trong cửa sổ [`inject_ts` − 1200 s, `inject_ts` + 600 s), kèm thời điểm tiêm lỗi. Kết quả mỗi case được chép cho cả 5 truy vấn của case đó.
- **Bộ xếp hạng độ trễ:** điểm của một dịch vụ là max của `duration / p50 train` trên các span trỏ tới dịch vụ đó. Mốc p50 lấy từ `build_baseline()` của `analyze-metric-substitutes.py`. Có hai cách nhìn:
  - `latency_*` nhìn cả cửa sổ lỗi [`inject_ts`, +600 s).
  - `latency_query_*` chỉ nhìn trace được giao.

| Phương pháp | R@1 | MRR | R@1, có span GT (n=181) | R@1, không có span GT (n=59) |
|---|---|---|---|---|
| TraceRCA | 0,083 | 0,409 | 0,022 | 0,271 |
| MicroRank | 0,000 | 0,221 | 0,000 | 0,000 |
| BARO (cần metric) | 0,104 | 0,525 | 0,138 | 0,000 |
| Độ trễ, cả cửa sổ, `either` | **0,500** | 0,659 | 0,591 | 0,220 |
| Độ trễ, cả cửa sổ, `callee` | 0,375 | 0,538 | 0,497 | 0,000 |
| Độ trễ, cả cửa sổ, `caller` | **0,500** | 0,657 | 0,580 | 0,254 |
| Độ trễ, chỉ trace được giao, `either` | 0,196 | 0,418 | 0,260 | 0,000 |
| Độ trễ, chỉ trace được giao, `callee` | 0,354 | 0,507 | 0,470 | 0,000 |
| Độ trễ, chỉ trace được giao, `caller` | 0,138 | 0,363 | 0,182 | 0,000 |

- Controller đã tính lại hai cột cuối bằng cách nối `results.csv` với `coverage.csv`; kết quả khớp số trong `summary.json`.
- TraceRCA, MicroRank và các bộ xếp hạng độ trễ chỉ đọc trace, nên kết quả ở điều kiện bỏ metric giống hệt điều kiện đủ nguồn. BARO không chạy được khi không có metric.
- Kết quả theo từng dịch vụ lỗi nằm trong `K/runtime/non-llm-baselines/summary.json`. Ví dụ, TraceRCA chỉ trúng R@1 ở checkoutservice (0,444). Điều đó giải thích vì sao nó "tốt hơn" ở nhóm không phủ, nơi checkoutservice chiếm nhiều.

## 4. Giới hạn

- **MicroRank của RCAEval chỉ trả 5 operation** và `frontendservice` thường đứng đầu, nên R@1 bằng 0 phần lớn là do giới hạn của bản cài, không hẳn do phương pháp.
- **Cửa sổ của BARO khác bài RCAEval.** Ở đây là dữ liệu 1 giây trong 1800 giây; bản gốc dùng khoảng 10 phút mỗi bên với nhịp 2 giây. Vì vậy số BARO không so thẳng với bài RCAEval được.
- **Mọi baseline đều được biết thời điểm tiêm lỗi**, theo đúng giao thức RCAEval. Truy vấn của RCLAgent thì chỉ mang thời điểm của trace lỗi. Khi so với agent, phải ghi rõ khác biệt này.
- **Biến thể `callee` gặp tên giả `health`** (từ `grpc.health.v1.Health/Check`). Tên này được giữ đúng theo định nghĩa của RQ (c) bước 1, không lọc.
- **Hai script của phase 4 chưa được reviewer độc lập soi.**

## 5. Hệ quả cho phase 3

1. Tập dev phải có RCLAgent gốc, để so trực tiếp với mức sàn 0,50 của bộ xếp hạng độ trễ.
2. M2 và M3 cần một bước chọn dịch vụ tốt hơn cách lấy max tỉ lệ: ở nhóm không phủ, max tỉ lệ chỉ đạt 0,22–0,25.
3. Thêm baseline "agent tự do truy vấn bảng thô", theo [báo cáo nguyên văn](research-261102-rclagent-direction-a-related-work-full-text.md).

## Câu hỏi còn mở

1. Có lọc tên giả `health` khỏi biến thể `callee` ở phase 3 không? Đổi định nghĩa đó cũng làm đổi số của RQ (c) bước 1.
2. Có thay MicroRank của RCAEval bằng bản gốc (IntelligentDDS) để có danh sách xếp hạng đầy đủ không?
