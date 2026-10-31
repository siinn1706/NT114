# Review: đã sẵn sàng bắt đầu chạy RCLAgent trên tập train chưa — 2026-10-27

**Kết luận:** chưa nên chạy cả tập train. Code đang pending của harness (ngân sách `search_logs`, guard theo cửa sổ thời gian và theo khoảng dữ liệu đầy đủ) không có lỗi chặn, và gate một trace đã qua ở Kaggle version 8. Nhưng harness hiện chỉ chạy được đúng một trace (`checkoutservice_cpu_2`), và chưa có batch runner. Tập train có 240 trace, ước tính tốn khoảng 73 giờ GPU T4, trong khi metric tool gần như luôn trả rỗng. Nên chốt 3 điểm dưới đây rồi chạy pilot vài trace trước.

"Train" ở đây hiểu theo [review 0912](review-261027-0912-training-data-readiness.md): chạy RCLAgent với backbone có sẵn trên các ca thuộc tập train. Không có fine-tuning; phần đó vẫn chưa có trong dự án.

Phạm vi: diff pending trong `plans/261026-1713-rclagent-tai-hien-toi-thieu/kaggle/` tại HEAD `7941e17`, artifact Kaggle version 8, endpoint gốc `tool_server.py` (upstream `3052e7a`) và `work/tool-result-budget-impact/trace-impact.csv`. Review-only, không sửa code.

## Đã xác minh, không phải vấn đề

- **Biên của guard khớp endpoint gốc.** Upstream lọc bằng `timestamp.between(ts-60, ts+60)` cho log và `between(ts-1200, ts+1200)` cho metric, bao gồm cả hai biên. Guard chỉ cho qua khi `second+half < lo` hoặc `second-half > hi`, khớp đúng các biên đó. Test biên 939/940 và 3.200/3.201 cũng khớp.
- **Guard thêm `.strip()` mà upstream không có** (`smoke-worker.py:202`). Vì vậy comment "Same parse as the upstream endpoints" không đúng hoàn toàn, nhưng sai lệch này an toàn. Nếu có khoảng trắng đầu chuỗi, upstream parse ra số ít hơn 10 chữ số, nằm ngoài toàn bộ dữ liệu, nên gói và dữ liệu đầy đủ cùng trả rỗng. Khoảng trắng cuối chuỗi không làm đổi `[:10]`.
- **Đã chốt ánh xạ ca.** `work/re2ob-case-roles-by-source-key.csv` gán `checkoutservice_cpu_1` theo source key, đúng một khớp, vai train. Finding 3 của review 0912 coi như xong.
- **Môi trường harness local.** `runtime/harness-env` chạy đủ 20/20 test harness, 9/9 test ngân sách và 4/4 test T4. Finding 4 của review 0912 không còn chặn.
- **Context.** Synthesis là prompt lớn nhất: 6.444 token với 33 span, tức khoảng 180 token mỗi span. Với trace lớn nhất trong train (45 span), ước tính khoảng 8.600 token, cộng 1.024 output vẫn dưới 16.384.

## Findings (theo mức độ)

1. **Chặn: harness cứng cho một trace.** Các chỗ hard-code:
   - `prepare-bundle.py:28-30,111-113,135,161,207,212,266` (case, `TRACE_ID`, 33 span, tiền tố `log_id`, partition);
   - `smoke-worker.py:400` (`assert len(nodes) == 33`);
   - `verify-package.py:36,71`;
   - `selection.json` chỉ có một `query_window` và một `root_span_id`.

   Ngoài ra `kaggle-runtime.py:471` dừng toàn bộ lượt chạy khi trace lỗi, theo thiết kế smoke. Một batch cần: gói và kiểm CPU equivalence cho từng ca; chính sách ghi nhận trace thất bại mà không retry và không dừng các trace khác; artifact tách theo trace; và khả năng chạy tiếp sau khi session Kaggle bị ngắt.
2. **Chặn về ngân sách: thời gian và quota GPU.** Version 8 tốn 1.332,9 giây cho 33 span, khoảng 40 giây mỗi span. Từ `trace-impact.csv`:

   | Vai | Số trace | Span (trung vị / p90 / tối đa) | Ước tính giờ T4 |
   |---|---:|---|---:|
   | train | 240 | 25 / 39 / 45 | ~73 |
   | val | 105 | 25 / 39 / 43 | ~34 |
   | test | 105 | 25 / 39 / 43 | ~34 |

   - Trace 45 span ước khoảng 1.818 giây, vượt trần 1.800 giây. Thêm phương sai, các trace từ 40 span trở lên có thể bị dừng vì deadline.
   - Mỗi session Kaggle tối đa 12 giờ, tức khoảng 30 trace.
   - Không được nâng trần khi chưa có quyết định của sếp.
3. **Cần xác minh trước khi tốn GPU: metric tool gần như luôn rỗng.**
   - Ở version 8 có 37 lần gọi `search_fluctuating_metrics`: 34 lần trả "No fluctuating metrics found.", 3 lần "No matching records found.". Không lần nào trả metric. Có cả lần hỏi `checkoutservice`, đúng service đang bị lỗi CPU.
   - Quét CPU trước đó cũng thấy phản hồi metric trên RE2-OB luôn tối đa 10 token.
   - Nguyên nhân khả dĩ: baseline ±1.200 giây đã chứa cả cửa sổ ±600 giây đang có lỗi, nên std bị đội lên và ngưỡng 3σ không bao giờ bị vượt. Cùng với `simple_metrics.csv` (đường mặc định của tác giả), metric có thể "chết" trên toàn bộ RE2-OB.
   - Nếu đúng vậy thì đây là hành vi gốc, cần giữ nguyên. Nhưng nó phải được đo trên cả 450 trace và ghi vào report, vì khi đó kết quả chỉ dựa vào trace và log.
4. **Tính lặp lại.** Cùng seed và cấu hình, 28 request đầu của version 7 và 8 trùng byte, sau đó khác nhau; nhiều khả năng do GPU không tất định. Một lượt chạy mỗi trace không lặp lại được y hệt. Cần chọn trước: chạy một lượt và báo cáo kèm cảnh báo, hay chạy lặp một phần nhỏ để đo phương sai.
5. **Diễn giải điểm.** Worker yêu cầu ít nhất 10 candidate, và kết quả version 8 liệt kê 10 trong khoảng 11 service. R@5 và R@10 vì thế gần như tự động bằng 1, chỉ R@1, R@3 và MRR mang thông tin. Version 8 đạt R@1 = 1/1 trên một trace, không phải ước lượng accuracy.
6. **Nhỏ: hai phần dễ lỗi khi tổng quát hóa.**
   - `budget_log_result` lấy giây neo từ tham số JSON của model. Guard ở mức URL thì kiểm tham số server thực sự đọc. Nếu hai giá trị khác nhau (tham số bị chèn qua `service_name`), ngân sách có thể dừng vì "unanchored". Hướng lỗi này là dừng, không phải trả sai.
   - `str.contains(service_name)` của upstream hiểu tên service là regex. Tên có ký tự như `(` sẽ làm server trả 500, và guard dừng trace. Nên giữ nguyên, nhưng một batch cần tính trường hợp này là một kiểu thất bại có thể xảy ra.

## Đề xuất thứ tự

1. Commit hoặc đẩy diff hiện tại lên một nhánh để có một revision cố định cho ultrareview.
2. Đo trên CPU tỷ lệ phản hồi metric có dữ liệu trên 450 trace (finding 3).
3. Viết batch runner: gói theo ca, CPU equivalence theo ca, kết quả theo trace, chạy tiếp được sau khi bị ngắt, giữ nguyên mọi trần.
4. Chạy pilot khoảng 5 trace train phân tầng theo số span, gồm cả trace 45 span. Sau đó mới quyết định chạy cả 240 trace.

## Câu hỏi còn mở

1. Chạy tập train để làm gì khi không có fine-tuning: hiệu chỉnh hay phân tích lỗi? Nếu mục tiêu là tái hiện Table I thì tập cần chạy là test (105 trace, khoảng 34 giờ T4).
2. Khi trace chạm trần 1.800 giây thì ghi là thất bại, hay sếp muốn xét lại trần cho trace nhiều span?
3. Chạy một lượt hay nhiều lượt mỗi trace?
