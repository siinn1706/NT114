# Tra tính mới cho hướng A: agent RCA dựa trên trace khi thiếu telemetry

Ngày 2026-11-02. Sếp chốt hướng A cùng ngày. Báo cáo này gồm ba lượt tra song song của subagent nckh-researcher và một phép kiểm CPU của controller. `K/` là `plans/261026-1713-rclagent-tai-hien-toi-thieu/kaggle/`.

**Cập nhật 2026-11-02:** đã đọc nguyên văn 10/11 bài ở [báo cáo nguyên văn](research-261102-rclagent-direction-a-related-work-full-text.md). Báo cáo đó thay cho mục 3 dưới đây ở mọi chỗ khác nhau. Ba điểm thay đổi chính:
- **AMER-RCL** (2601.02732, ICSE-SEIP'26, cùng nhóm tác giả RCLAgent) là bài gần M3 nhất. Hệ thống nhận nhiều alert trong cùng cửa sổ thời gian, và Sec. 3.2 nêu "horizontal expansion" qua nhiều trace như cách SRE làm. Nhưng mỗi alert vẫn được suy luận đệ quy trên một trace riêng (Algorithm 1, tr. 7; Fig. 6 cho mỗi alert một kết quả riêng). Bài không có bước mở rộng kích hoạt theo độ phủ, và không đo độ phủ. Controller đã tự kiểm tr. 4–7.
- **Agent tự do truy vấn bảng thô** ("Free to Look" 2610.35767, 2608.21310) về khả năng đã nhìn được mọi trace. Vì vậy M3 phải có baseline "SQL agent trên toàn cửa sổ".
- **2601.22208** thấy rằng bỏ trace thường làm tăng độ chính xác (Observation 7, tr. 8). Reviewer có thể dùng điều này để phản biện việc đưa thêm bằng chứng từ trace.

**Giới hạn quan trọng nhất (của bản đầu):** mọi bài đều được đọc qua công cụ tóm tắt (WebFetch), thường chỉ khoảng 100 nghìn ký tự đầu. Các PDF tải về đều không đọc được. Số mục, số bảng và trích dẫn dưới đây **chưa đối chiếu nguyên văn** [UNVERIFIED]. Phase 1 của plan hướng A là đọc nguyên văn các bài trong mục 3.

## 1. Kết luận

- **Hướng A vẫn còn chỗ mới, nhưng chỉ ở dạng kết hợp, và phải đổi một thành phần.** Riêng việc gỡ một nguồn telemetry rồi đo agent LLM thì đã có người làm. Riêng hiện tượng "thiếu dữ liệu bị đọc thành khỏe" cũng đã được đặt tên.
- Phần mới nhất là **bù nguồn ngay trong agent** (C3). Chưa tìm thấy bài agent LLM nào dựng KPI độ trễ từ trace, có mốc train, để thay cho metric bị thiếu.
- **Phát hiện mạnh nhất cho bài:** 59/240 truy vấn train trong benchmark RE2-OB của RCLAgent (24,6%) có trace không chứa span nào của dịch vụ lỗi (mục 2). Agent chỉ đi trong trace vì thế có trần R@1 khoảng 75% trên train. RCLAgent chỉ nêu giả định này như một giới hạn, không đo.
- **Phép kiểm CPU (mục 2) bác bỏ cách hiểu cũ về điểm mù S0.** Ở 3 case S0, dịch vụ lỗi không phải là dịch vụ không được gắn tracing. Trong 10 phút sau khi tiêm lỗi, nó xuất hiện ở 540 đến 5748 trace. Agent không thấy nó chỉ vì trace duy nhất được giao không đi qua dịch vụ đó. Vì vậy C3b phải đổi từ "suy ra dịch vụ lỗi từ span của bên gọi" thành **"mở rộng bằng chứng ra ngoài trace được giao"**. Đây đúng là giả định mà RCLAgent tự ghi ở Sec. VI: đồ thị trace phải phủ đường lan truyền lỗi.

## 2. Phép kiểm CPU: dịch vụ lỗi ở các case S0 có trong dữ liệu trace thô không

- Script: `gt-in-window.py`, nằm trong scratchpad của phiên, không đưa vào repo.
- Dữ liệu: trace thô RE2-OB (`trace_jaeger-span.csv`) trong khoảng [`inject_ts`, `inject_ts` + 600 s). Cả 4 case đều thuộc train; không đụng test split.
- Cột "Span client gọi tới GT" đếm span có `operation_name` chứa tên RPC của dịch vụ lỗi, do dịch vụ khác phát ra.
- Bundle của cả 4 case chỉ có 1 trace (`K/runtime/analysis-metric-substitutes-s1-v2/cases.csv`, cột `traces`).

| Case | Dịch vụ lỗi | Span của GT trong trace được giao (server / client) | Trace trong 10 phút | Trace có đi qua GT | Span server của GT | Span client gọi tới GT | Trace được giao bắt đầu sau khi tiêm (giây) |
|---|---|---|---|---|---|---|---|
| `de6a50` | checkoutservice | 0 / 0 | 10 011 | 1 476 | 3 852 | 285 | 80,6 |
| `30e3c7` | emailservice | 0 / 0 | 10 472 | 540 | 540 | 300 | 286,8 |
| `272a47` | recommendationservice | 0 / 0 | 10 127 | 5 748 | 11 256 | 5 508 | 129,9 |
| `99f095` (đối chứng, có span GT) | currencyservice | 10 / 10 | 7 770 | 5 431 | 17 058 | 16 960 | 294,0 |

Hệ quả:
- Ở 3 case S0, trace được giao không có span nào của GT, kể cả span client gọi tới GT. Vì vậy cách suy ra GT từ span client không có gì để bám, và C3b theo nghĩa cũ không làm được trên dữ liệu này.
- Bằng chứng về GT vẫn có trong cùng cửa sổ thời gian, nhưng nằm ở các trace khác. Trong số đó, 5,4% (`30e3c7`) đến 56,8% (`272a47`) số trace đi qua GT.
- Bundle chọn trace từ danh sách truy vấn của chính RCLAgent (`error_traces.txt` của bộ RE2-OB đã tiền xử lý, `K/prepare-bundle.py:117-130`). Mỗi error trace là một truy vấn RCA độc lập, và nhãn là dịch vụ lỗi của case.

### Phạm vi trên toàn bộ truy vấn train của RCLAgent

- Script: `error-trace-gt-coverage.py`, cũng nằm trong scratchpad.
- Dữ liệu: 240 error trace thuộc 48 case train, theo `work/tool-response-scan/tool-response-scan.csv`. Không đụng val hay test.
- Dịch vụ lỗi lấy từ tiền tố của `case_id`.
- Một span được tính là "span client gọi GT" khi `operation_name` chứa tên RPC của GT.

| Dịch vụ lỗi | Có span server của GT | Chỉ có span client gọi GT | Không có span nào của GT | Tổng |
|---|---|---|---|---|
| checkoutservice | 24 | 0 | 21 | 45 |
| currencyservice | 45 | 0 | 0 | 45 |
| emailservice | 3 | 0 | 27 | 30 |
| productcatalogservice | 58 | 2 | 0 | 60 |
| recommendationservice | 41 | 8 | 11 | 60 |
| **Tổng** | **171** | **10** | **59** | **240** |

- **59/240 truy vấn train (24,6%) có trace không chứa span nào của dịch vụ lỗi**, kể cả span client gọi tới nó. Một agent chỉ đi trong trace được giao không thể chạm tới GT ở những truy vấn này. Nghĩa là trên train, R@1 của nó có trần khoảng 75%.
- Có 5/48 case mà mọi trace đều như vậy, và 17/48 case có ít nhất một trace như vậy.
- Mức độ khác nhau rõ giữa các dịch vụ: 27/30 truy vấn của emailservice và 21/45 của checkoutservice không có span GT. Hai dịch vụ này chỉ nằm trên luồng thanh toán.
- Chỉ 10/240 truy vấn có span client gọi GT mà không có span server của GT. C3b theo nghĩa cũ (suy GT từ span của bên gọi) vì thế chỉ áp dụng được cho khoảng 4% truy vấn.
- Chưa so với R@1 RCLAgent công bố trên RE2-OB, vì con số đó tính trên test split (niêm phong theo D12).

## 3. Đối chiếu từng claim

Claim là ba ý của hướng A:
- **C1:** gỡ nguồn có kiểm soát, cộng với phép đo chỗ mất bằng chứng theo từng tầng (`U0`–`U4`).
- **C2:** agent nhận ra nguồn nào đang thiếu, và coi "không có dữ liệu" khác với "khỏe".
- **C3:** agent tự bù nguồn bị thiếu. C3a: KPI độ trễ dựng từ trace thay cho metric. C3b: mở rộng bằng chứng ra ngoài trace được giao.

| Claim | Bài gần nhất | Mức trùng | Phần còn lại cho bài mình |
|---|---|---|---|
| C1 | 2601.22208 "Stalled, Biased, and Confused", Sec. 4.2: lần lượt bỏ trace, log, metric khỏi một agent ReAct trên đồ thị tri thức, ở mức alert; bỏ metric làm độ chính xác định vị giảm nhiều nhất. MicroRCA-Agent (2509.15635), Table 1: ablation theo tập con modality. ARMOR (2603.25538, ASE'26): bỏ modality có kiểm soát, không dùng LLM. 2607.13548 (QPIAI): kiểm toán bằng chứng sau khi chạy, có điều kiện theo nhãn, chỉ cho metric. 2608.21310: taxonomy OMIT, tức bằng chứng có nhưng không được truy vấn | Một phần | Phép đo theo từng tầng trên agent đi theo trace, với điều kiện gỡ ở mức span. Không nên tuyên bố là "ablation modality đầu tiên cho RCA bằng LLM" |
| C2 | 2608.21310, Sec. 5.3, Table 3: lỗi MIS1 "silence-as-health", tức im lặng hoặc thiếu dữ liệu bị đọc thành khỏe. ARMOR: mask quan sát cộng placeholder học được. TorAI (FSE 2026): cho nguồn thiếu điểm 0, đúng là hành vi C2 phản đối. LATS-RCA (2605.03505): chỉ đánh dấu metric không có | Một phần, hiện tượng đã được đặt tên | Cơ chế tường minh trong agent LLM, có đo hiệu quả và so với cách mask kiểu ARMOR. Không tuyên bố mình phát hiện ra hiện tượng này |
| C3a | Hybrid RCA cho hệ quan sát một phần (CLOSER 2025): metric bị ẩn, độ trễ trace so với mức bình thường là tín hiệu chính; chỉ là proof of concept trên một bộ dữ liệu. GALA+ (2608.08968, ASE'26): dùng thống kê độ trễ span làm điểm chính, nhưng không đặt trong bối cảnh thiếu metric. MicroRank, TraceRCA, T-Rank: RCA chỉ từ trace, không dùng LLM | Một phần ở ngoài khung agent LLM | KPI có mốc train tính cho cả bên gọi lẫn bên được gọi, đưa vào agent LLM khi metric vắng. Phải so với MicroRank và TraceRCA |
| C3b (đổi nghĩa) | TorAI (FSE 2026): xử lý "blind spot" là dịch vụ không có trace, không dùng đồ thị gọi và không dùng LLM. RCLAgent Sec. VI: nêu giả định đồ thị trace phủ đường lan truyền như một giới hạn, không đo | Chưa thấy bài agent LLM nào tự mở rộng tập trace khi trace được giao không phủ dịch vụ lỗi | Đây là đóng góp mạnh nhất, cần đọc kỹ TorAI trước khi tuyên bố |

## 4. Rủi ro cho mức Q1

- **"Free to Look, Free to Reason"** (2610.35767, tháng 10/2026, mới đọc abstract) cho rằng harness LLM đơn giản chẩn đoán tốt hơn agent RCA thiết kế tay. Reviewer có thể hỏi: một agent ReAct đơn giản, có đủ tool và được truy vấn mọi trace, có đánh bại cả RCLAgent lẫn bản cải tiến của mình không. Vì vậy phải có baseline này.
- **Baseline reviewer sẽ đòi:** RCLAgent gốc; TraceRCA và MicroRank (có sẵn trong RCAEval, https://github.com/phamquiluan/rcaeval); TorAI cho trường hợp blind spot; một harness ReAct đơn giản. ARMOR ít nhất phải được trích; nó dùng bộ dữ liệu khác RE2.
- **Quy mô:**
  - RCLAgent gốc dùng AIOps 2022, Augmented-TrainTicket và RE2-OB. RE2-SS không có trace, nên không chạy được RCLAgent; RE2-TT có đủ ba nguồn.
  - Các điều kiện gỡ metric và log vẫn là giả lập; phải nói rõ như vậy trong bài.
  - Với T4 và quota 30 giờ mỗi tuần, đánh giá trên test split RE2-OB và RE2-TT sẽ kéo dài nhiều tuần.
- **Venue tham khảo:** ICSE-SEIP (AMER-RCL), ASE (GALA+, ARMOR), FSE (TorAI), WWW Companion (RCAEval). Chưa kiểm hạng Q của tạp chí.

## 5. Nhật ký tra

- Lượt dòng RCLAgent: Semantic Scholar citations của 2605.14866 (5 bài), HTML của 2605.14866, abstract của 2601.02732, README của RCAEval.
- Lượt agent LLM: 14 truy vấn WebSearch, HTML của khoảng 12 bài.
- Lượt không dùng LLM: 10 truy vấn WebSearch, HTML của ARMOR và TorAI.
- Danh sách truy vấn đầy đủ nằm trong báo cáo của các subagent (không lưu riêng).

## Câu hỏi còn mở

1. Trần 75% trên train có giữ được trên test split không? Muốn biết phải mở cấu trúc của test split (chỉ đếm span, không đọc kết quả). Việc này cần sếp quyết theo D12.
2. TorAI có dùng span phía bên gọi không, và có chạy trên RE2 không? Cần đọc nguyên văn.
3. ReconRCA ("RCA with incomplete metrics", ICWS 2025) mới thấy tên trong một danh sách tài liệu tham khảo. Nếu có thật, nó là rủi ro cho C3a.
