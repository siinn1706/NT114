# Công trình liên quan cho hướng A: đối chiếu từ nguyên văn PDF

Ngày 2026-11-02. Báo cáo này thay phần "chưa đối chiếu nguyên văn" của [báo cáo tra tính mới](research-261102-rclagent-direction-a-novelty.md). PDF nằm trong scratchpad của phiên (không đưa vào repo); text trích bằng `pypdf` chạy `python -I`. Phần đọc là các mục nêu ở cột "Trang đã đọc", cộng với grep từ khóa trên toàn bộ text của từng bài.

## Kết luận đầu báo cáo

**Không tìm thấy bài nào đã làm M3 cho agent LLM đúng theo định nghĩa của hướng A** (agent tự mở rộng bằng chứng sang trace khác trong cùng cửa sổ thời gian khi trace được giao không phủ dịch vụ lỗi). Có ba bài chạm vào M3 một phần, sếp cần biết trước khi viết claim:

1. **AMER-RCL (2601.02732, cùng nhóm tác giả RCLAgent).** Mục 3.2 (tr. 4) mô tả "horizontal expansion": SRE đối chiếu các alert và trace trong cùng cửa sổ bất thường. Hệ thống xử lý nhiều alert trong một cửa sổ (tr. 2, 5). Nhưng Algorithm 1 (tr. 7) chỉ đệ quy xuống span con của một alert trace. Phần "nhiều alert" dùng để tái sử dụng suy luận qua Agentic Memory. Đầu vào đã là tập alert cho sẵn; không có điều kiện kích hoạt "trace được giao không phủ GT" và không có phép đo phủ. Mức: M3 một phần.
2. **Agent tự do truy vấn dữ liệu thô** ("Free to Look", 2610.35767, tr. 3 và 5; 2608.21310, tr. 6 và 10). SQL agent và Codex chạy trên toàn bộ bảng trace của cửa sổ, nên về khả năng chúng đã có thể nhìn mọi trace. Chúng không nhận một trace truy vấn, không nói gì về phủ trace, và không có cơ chế kích hoạt. Hệ quả: M3 **không thể** tuyên bố là "khả năng mà agent LLM chưa từng có". M3 chỉ có thể tuyên bố ở dạng cải tiến có kiểm soát cho agent bám theo trace (kiểu RCLAgent), kèm phép đo trần phủ, và phải có baseline "SQL agent trên toàn cửa sổ".
3. **GALA+ (2608.08968, tr. 3).** STRIX dựng đồ thị từ cả "trace corpus" chứ không từ một trace. Đây là thống kê, không phải agent mở rộng theo điều kiện.

Phần mới còn lại sau khi đọc nguyên văn: (a) M2 dạng kết hợp (KPI độ trễ có mốc train, cả bên gọi lẫn bên được gọi, đưa vào agent LLM khi metric vắng); (b) phép đo P trên RE2-OB; (c) M3 dạng kích hoạt theo điều kiện cho agent bám trace, có so với baseline tự do truy vấn.

## 1. Bảng truy cập

Tất cả tải bằng `curl`, kiểm tra magic `%PDF-`. Thư mục PDF: `...\scratchpad\pdfs`; text: `...\scratchpad\txt`; script `...\scratchpad\pdf-tools\extract.py`.

| Bài | URL | SHA256 | Số trang | Trang đã đọc (và grep toàn văn) |
|---|---|---|---|---|
| RCLAgent 2605.14866 | https://arxiv.org/pdf/2605.14866 | 911025c62a8b1347cb72bde5ef3cc38aeb5bbc601d144e4eb5b0aec2cd6f0957 | 20 | 1, 4-5, 7-8, 13-15 (Sec. VI-VIII), 19-20 (phụ lục so sánh) |
| TorAI 2604.13522 (FSE 2026, DOI 10.1145/3808137) | https://arxiv.org/pdf/2604.13522 | 82b727c2d687669e43acd0e186c7f583d416c15b9d88fc698fe58e50d9c72db6 | 23 | 1-3, 6-7, 10-11, 16-19 |
| ARMOR 2603.25538 | https://arxiv.org/pdf/2603.25538 | 4a3714bb89b33c1ede72e61f8b63b88b4b44f9f9c74a2611411308e9f85299e8 | 13 | 1-2, 4-5, 7-8, 11 |
| 2601.22208 | https://arxiv.org/pdf/2601.22208 | 71be7811e5fbd9c514f2dd8beae2851de7c1f80a402dec1b98f1c71a7eb72283 | 19 | 1, 5-8 (Sec. 4.2 nằm ở tr. 7-8) |
| 2608.21310 | https://arxiv.org/pdf/2608.21310 | c8201a582cc535c9b87bed33cb6028efe0308c01b27c2ef4838956e245d29b4e | 23 | 1-3, 6, 9-10, 14-16 (Sec. 5.3 và Table 3 ở tr. 14) |
| GALA+ 2608.08968 | https://arxiv.org/pdf/2608.08968 | 44362b19091d1f981d0a1cea005685044f06e45567e83b2baf7b5f3e7bc0aab2 | 13 | 1, 3-4, 6 |
| 2607.13548 | https://arxiv.org/pdf/2607.13548 | d2476f0f93c2353dc9a9bbaaf47ac61d453a3c28512a60886acbd88b48f1fb22 | 29 | 1, 4, 8, 15-17 |
| Free to Look 2610.35767 | https://arxiv.org/pdf/2610.35767 | b9c2348ffeea1f00f8a28b3ac05b1f4ec97ae0758595812de0a069453c26210a | 12 | 1-5 |
| AMER-RCL 2601.02732 | https://arxiv.org/pdf/2601.02732 | 6646dd54e60f8fa9a60781c231f74ace92d11f7de0658d8a1ee98de7d655fde9 | 12 | 1-2, 4-5, 7-8 |
| Hybrid RCA, CLOSER 2025 | https://www.scitepress.org/Papers/2025/134536/134536.pdf | b8cb4bbcbad6c0f0b4f1ee77f815a4c93c92f575a119353d6f7ef8d96e182873 | 9 | 1-2, 6-8 |
| ReconRCA (ICWS 2025, DOI 10.1109/ICWS67624.2025.00024, tr. 116-126) | không tải được | không có | không có | **Không đọc được nguyên văn.** Bản IEEE trả về trạng thái CLOSED trên Semantic Scholar; Crossref chỉ có metadata. Chỉ đọc abstract (qua API Semantic Scholar) |

Ghi chú: lần `curl` đầu tới scitepress thất bại (không có phản hồi), lần thứ hai thành công. Hash trong bảng là của file tải lần thành công. Bản PDF 2610.35767 là bản tải về hôm nay; số hiệu arXiv và tên bài khớp với tiêu đề trong file.

Về trích dẫn: quy tắc phiên giới hạn mỗi câu trả lời tối đa một trích dẫn dưới 15 từ, chặt hơn yêu cầu "tối đa một trích dẫn mỗi ô". Vì vậy báo cáo này chỉ có đúng một trích dẫn nguyên văn (RCLAgent Sec. VI, ở mục 2) và diễn giải phần còn lại kèm số trang.

## 2. RCLAgent Sec. VI: câu chữ chính xác

Sec. VI "Threats to Validity and Limitations" nằm trọn ở trang 14 của bản arXiv. Hai điểm liên quan:

- Giới hạn (1): RCLAgent "trace-centric but not trace-only", hợp nhất khi hệ thống có độ phủ tracing đủ và đường lan truyền lỗi phản ánh được trong đồ thị trace. Khi không có trace, nó thoái hóa thành agent ReAct kiểu cũ.
- Giới hạn (2) "blind-spot services in the trace graph": nếu dịch vụ không được instrument, hoặc span bị mất do tracing không đầy đủ, lấy mẫu hay lỗi quan sát, thì đồ thị trace dựng được có thể không phản ánh đường lan truyền thật. Agent có thể dừng ở triệu chứng thượng nguồn hoặc đổ lỗi cho dịch vụ láng giềng.
- Giới hạn (4) nêu tiền đề: "the trace graph should sufficiently cover the failure propagation path" (tr. 14).

Nhận xét:
1. Giả định phủ trace được **nêu rõ, ở dạng tiền đề và giới hạn**, nhưng **không đo** ở đâu trong bài (grep toàn văn không thấy số liệu về tỷ lệ truy vấn có trace chứa dịch vụ lỗi).
2. Giới hạn (2) gán nguyên nhân cho tracing không đầy đủ (không instrument, mất span, lấy mẫu). Trường hợp của sếp khác: dịch vụ lỗi được instrument và xuất hiện ở 540 đến 5748 trace trong cửa sổ, nhưng trace **được giao** không đi qua nó. Câu "missing nodes or edges" có thể bị đọc là bao trùm cả trường hợp này, nên bài mình nên viết "RCLAgent nêu tiền đề này; chúng tôi đo mức vi phạm tiền đề trên RE2-OB", đừng viết "RCLAgent không nhận ra giới hạn".
3. Tool trace của RCLAgent (tr. 7-8, Eq. 2) nhận mã span và trả về span con kèm thời lượng thô. Không có thao tác tra cứu trace khác và không có mốc baseline cho thời lượng. Metric Tool (tr. 8, Eq. 3-4) chỉ trả về metric vượt ngưỡng n-sigma, và văn bản không nói gì về trường hợp nguồn metric vắng. Đây là chỗ M1 chưa có trong RCLAgent, nhưng cần nói đúng là "văn bản không đề cập", không phải "RCLAgent xử lý sai".
4. Ablation của RCLAgent (tr. 13, Fig. 7) gỡ RLDR và GEG, không gỡ modality. Phần cuối (tr. 15) nói hướng tương lai là mô hình nhỏ hơn và mở rộng sang toàn bộ quản lý sự cố; không có hướng về thiếu telemetry. Dataset: AIOps 2022, Augmented-TrainTicket, RCAEval RE2-OB (tr. 10-11).

## 3. Ma trận bài × thành phần

Quy ước: **không** = không thấy trong các mục đã đọc; **một phần** = có chạm nhưng khác cơ chế, khác đối tượng hoặc không đo; **đủ** = làm đúng thành phần. Không có ô nào ở mức "đủ".

- M1: agent phát hiện nguồn telemetry nào đang thiếu theo từng dịch vụ, và coi "không có dữ liệu" khác "khỏe".
- M2: KPI độ trễ dựng từ trace, so với mốc train, cả bên gọi lẫn bên được gọi, đưa cho agent LLM khi metric vắng.
- M3: agent mở rộng bằng chứng ra khỏi trace truy vấn duy nhất, sang trace khác cùng cửa sổ, khi trace được giao không phủ dịch vụ lỗi.
- P: đo và báo cáo tỷ lệ truy vấn có trace không chứa dịch vụ lỗi.

| Bài (LLM?, dữ liệu) | M1 | M2 | M3 | P |
|---|---|---|---|---|
| RCLAgent 2605.14866 (có LLM; AIOps 2022, Aug-TT, RE2-OB) | không. Tr. 8: Metric Tool chỉ trả metric vượt ngưỡng, không nói về nguồn vắng | không. Tr. 7-8: thời lượng span thô, không baseline | không. Tr. 8, 14: chỉ đi theo span con; tự nhận phụ thuộc phủ trace (Sec. VI) | không đo. Tr. 14 nêu tiền đề, không có số |
| TorAI 2604.13522 (không LLM; tự thu OB, Sock Shop, Train Ticket) | không, ngược lại: tr. 7 gán điểm 0 cho nguồn thiếu, tức "không dị thường" | một phần. Tr. 6: độ trễ và mã trạng thái theo từng operation thành chuỗi thời gian, so với giai đoạn bình thường (tr. 6, công thức z-score); không tách bên gọi/bên được gọi, không LLM | không. Tr. 6: cố ý bỏ đồ thị gọi; không có khái niệm trace truy vấn | một phần, khác đơn vị. Tr. 11: 4/11 dịch vụ OB và 37/64 dịch vụ TT không có trace; tr. 18 (Fig. 6) gỡ trace theo tỷ lệ dịch vụ. Đo theo dịch vụ, không theo truy vấn |
| ARMOR 2603.25538 (không LLM; D1 e-commerce 46 nút, D2 AIOps 2021 ngân hàng) | một phần. Tr. 5: vector mặt nạ quan sát O; tr. 2, 4: nêu lỗi điền 0 giống trạng thái "rảnh khỏe"; dùng placeholder học được. Làm bên trong mạng nơ-ron, không phải agent | không | không | không |
| 2601.22208 (có LLM, ReAct và Plan-and-Execute; GAIA/MicroSS, OpenRCA Market) | không. Tr. 7: giữ lại cả modality ở mức alert, không phát hiện sự vắng | không | không | không |
| 2608.21310 (có LLM; RCABench, AIOps 2025, RCA100; không phải RE2) | một phần. Tr. 14 Table 3: MIS1 "silence-as-health" là một mode lỗi quan sát được (Sonnet 30,0%, Qwen 44,2%); tr. 10 Table 1: nhãn ý định "liveness" có kiểm tra im lặng/xuất span. Là phân tích hành vi, không phải cơ chế | một phần. Tr. 14: OMIT1 "baseline gap" (không so với mốc khỏe trước sự cố, 26,0%/51,9%) và MIS3 (đảo chiều lỗi giữa bên gọi và bên được gọi) được gọi tên; không có cơ chế cấp KPI | một phần, về khả năng. Tr. 6, 10: agent SQL truy vấn bảng thô, có thể nhìn mọi trace; không có trace truy vấn, không kích hoạt theo phủ | không |
| GALA+ 2608.08968 (có LLM; OB và TT, nguồn [43]) | một phần yếu. Tr. 4: ứng viên chỉ có metric nhận độ tin cậy thấp khi vắng bằng chứng trace; đây là vắng theo từng ứng viên, không phải phát hiện nguồn vắng | một phần. Tr. 3: STRIX tính p99/p50, tâm đồ thị và thời gian tự xử lý so với callee, trong cùng cửa sổ; không có mốc train | một phần, dạng thống kê. Tr. 3: đồ thị dựng từ toàn bộ trace corpus. Không phải agent mở rộng theo điều kiện | không |
| 2607.13548 (có LLM; OpenRCA, cửa sổ 30 phút) | không. Tr. 15: chỉ metric, kiểm toán sau khi chạy, điều kiện theo nhãn; "absent KPI" (tr. 8, 17) là KPI không tồn tại trong schema, khác nghĩa | không | không. Tr. 4: log và trace của cả cửa sổ được đưa sẵn cho công cụ | không |
| Free to Look 2610.35767 (có LLM; RCAtlas 90 ca từ 8 bộ, có RE1-3 cho 27 ca) | không. Tr. 3 loại các ca có dữ liệu không đầy đủ | không | một phần, về khả năng. Tr. 3, 5: SQL agent trên toàn bảng thô của cửa sổ, tự quyết xem gì; không có trace truy vấn và không đo phủ | không |
| AMER-RCL 2601.02732 (có LLM; AIOps 2022, TrainTicket, FAMOS-Mall) | không | không. Tr. 5: cạnh có call_latency thô | một phần. Tr. 4 (Sec. 3.2) "horizontal expansion" và tr. 2, 5: nhiều alert trong cửa sổ; tr. 7 Algorithm 1 chỉ đệ quy một trace. Mục đích là tái sử dụng suy luận | không |
| Hybrid RCA, CLOSER 2025 (không LLM, rule-based; một bộ ISP của TraceRCA, một ngày) | một phần yếu. Tr. 1: "giả định chỉ có thông tin sức khỏe một phần" (CPU/mạng/lưu trữ không thấy). Không phát hiện theo từng dịch vụ | một phần. Tr. 6-7: so độ trễ của từng thành phần với giá trị cực đại trước lỗi; chưa nêu tách bên gọi/bên được gọi; không LLM; chưa có độ chính xác định lượng (tr. 8) | không | không |
| ReconRCA (ICWS 2025; chỉ abstract) | không đọc được nguyên văn. Abstract: khôi phục metric thiếu bằng mô hình không-thời gian và attention, top-1 33,28% khi thiếu và 39,74% khi đủ; không phải LLM | không đọc được nguyên văn. Hướng của nó là dựng lại metric, không phải dựng KPI từ trace | không đọc được | không đọc được |

### Câu hỏi riêng đã trả lời

- **TorAI có dùng span bên gọi không?** Không. Tr. 6 (mục 3.1.3): trace chỉ được đổi thành chuỗi thời gian tần suất độ trễ và mã trạng thái theo từng "trace operation" của từng dịch vụ, và tác giả nói rõ không dựng đồ thị gọi vì nó có thể không đầy đủ. Grep toàn văn không có "client", "caller", "callee" theo nghĩa span.
- **TorAI chạy trên dataset nào, có RE2 không?** Không phải RE2. Tr. 10: tự triển khai Online Boutique, Sock Shop, Train Ticket, mỗi hệ 90 ca (6 loại lỗi), cộng 10 sự cố thật (tr. 17). Mã TorAI được tích hợp vào RCAEval (mục tái lập, tr. 20). "Free to Look" chạy TorAI từ RCAEval như baseline (tr. 5).
- **TorAI có LLM không?** Không (grep "LLM" và "language model" trả 0).
- **Điểm TorAI khác bài mình.** "Blind spot" của TorAI là dịch vụ không có trace nhưng còn metric và log; TorAI dựa vào metric/log khi thiếu trace. Hướng A đi chiều ngược lại (thiếu metric, còn trace). Khi nguồn thiếu, TorAI gán 0 (tr. 7), đúng là hành vi mà ARMOR (tr. 2, 4) và MIS1 phê phán.
- **"Free to Look" có truy vấn tự do mọi trace/telemetry không, có pre-empt M3 không?** Có về khả năng (xem kết luận đầu báo cáo), nhưng không làm M3 như một thành phần: nó không có trace truy vấn, không đo phủ, và loại bỏ các ca dữ liệu không đầy đủ (tr. 3). RCLAgent-V2 bị loại khỏi so sánh vì tốn kém (khoảng 0,9 USD và đến một giờ mỗi ca, tr. 4), nên bài này không cho biết RCLAgent so với SQL agent thế nào. Hệ quả: reviewer sẽ hỏi baseline "SQL agent tự do", và bài mình chưa thể lấy kết quả của họ để trả lời.
- **RCLAgent Sec. VI có nêu giả định phủ trace không?** Có, tr. 14, xem mục 2.

## 4. Câu được phép viết

Mỗi câu kèm giới hạn phạm vi. Mọi câu kiểu "chưa có công trình" chỉ đúng trong phạm vi 10 bài đã đọc nguyên văn, abstract của ReconRCA và các lượt tra trước; cần tra lại tổng quan trước khi nộp.

1. "RCLAgent nêu tiền đề rằng đồ thị trace phải phủ đường lan truyền lỗi (Sec. VI) nhưng không đo mức tiền đề này được thỏa." Đúng theo tr. 14 và grep toàn văn.
2. "Trên 240 truy vấn train RE2-OB, 59 truy vấn (24,6%) có trace không chứa span nào của dịch vụ lỗi." Số của sếp, chỉ trên train; không nói về test.
3. "Chúng tôi chưa thấy agent LLM nào nhận KPI độ trễ dựng từ trace, so với mốc train ở cả bên gọi lẫn bên được gọi, khi metric vắng." Hedge bắt buộc; đối chiếu CLOSER, TorAI, GALA+ đều khác ít nhất một trong ba yếu tố (LLM, mốc train, hai phía).
4. "Chúng tôi chưa thấy agent LLM bám theo trace nào tự mở rộng sang trace khác trong cùng cửa sổ khi trace được giao không phủ dịch vụ lỗi, kèm phép đo mức phủ." Phải đi kèm câu thừa nhận: agent tự do truy vấn bảng thô (SQL agent, Codex) về khả năng đã nhìn được mọi trace, và AMER-RCL xử lý nhiều alert trong cửa sổ cho mục đích tái sử dụng suy luận.
5. "Hiện tượng 'im lặng bị đọc thành khỏe' đã được gọi tên là MIS1 trong 2608.21310; chúng tôi đưa nó thành cơ chế tường minh trong agent và đo tác dụng." Chỉ viết "đo tác dụng" khi phase sau thực sự có phép đo.
6. "TorAI không dùng LLM, không dùng span phía bên gọi, và được đánh giá trên bộ dữ liệu tự thu (OB, Sock Shop, Train Ticket), không phải RE2." Đã kiểm trên nguyên văn.
7. "Gỡ modality có kiểm soát ở agent LLM đã có ở mức alert (2601.22208, Sec. 4.2); phép đo của chúng tôi ở mức span, theo từng tầng mất bằng chứng." Đúng nếu phase sau vẫn đo ở mức span.

## 5. Câu không được viết

1. "Ablation modality đầu tiên cho RCA bằng LLM." Bị 2601.22208 (tr. 7-8) và 2607.13548 chạm tới.
2. "Chúng tôi phát hiện agent đọc im lặng thành khỏe." MIS1 tr. 14 đã đặt tên, cùng với ARMOR tr. 2 và 4 nêu lỗi tương tự ở mô hình nơ-ron.
3. "Chúng tôi là đầu tiên dùng độ trễ trace khi thiếu metric." CLOSER (tr. 1, 6-7), TorAI (tr. 6) và GALA+ (tr. 3) đều dùng độ trễ trace theo cách nào đó; ReconRCA giải đúng vấn đề thiếu metric theo hướng khác.
4. "Agent LLM chưa từng truy vấn được nhiều trace" hoặc "chưa ai cho agent nhìn toàn bộ cửa sổ." Sai theo 2610.35767 tr. 3 và 5, 2608.21310 tr. 6 và 10.
5. "RCLAgent không biết giới hạn phủ trace." Sai theo tr. 14.
6. "TorAI giải bài toán thiếu telemetry." TorAI giải trường hợp dịch vụ thiếu trace; nguồn thiếu bị gán 0.
7. "Không ai đo trần phủ trace" mà không hedge, và bất kỳ câu nào nêu bộ dữ liệu, cơ chế hay kết quả của ReconRCA ngoài nội dung abstract.
8. "Agent đơn giản tự do truy vấn kém hơn cách của chúng tôi." Chưa có bằng chứng; 2610.35767 báo cáo điều ngược lại trên RCAtlas (PR@1 65-77% so với 16-53% của các agent đã công bố, tr. 1).
9. Bất kỳ con số nào về test split RE2-OB hoặc về trần 75% trên test (còn bị niêm phong theo D12).

## 6. Thay đổi so với báo cáo tra tính mới trước

| Mục | Báo cáo trước | Sau khi đọc nguyên văn |
|---|---|---|
| Mức tin cậy chung | Mọi số mục, bảng, trích dẫn là [UNVERIFIED] | Đã đối chiếu từ nguyên văn cho 10/11 bài; ReconRCA chỉ có abstract |
| AMER-RCL | Chỉ ghi như venue và baseline | **Mới:** có "horizontal expansion" nhiều trace cùng cửa sổ (tr. 4), nhiều alert đầu vào (tr. 2, 5), nhưng thuật toán chỉ đệ quy một trace (tr. 7). Là điểm gần M3 nhất; cần liệt vào mục C3b của báo cáo trước |
| M3 "Chưa thấy bài agent LLM nào tự mở rộng" | Phát biểu dựa trên tóm tắt | Giữ được, nhưng với ba chú thích (AMER-RCL, agent tự do truy vấn, GALA+ corpus). Phải thêm baseline SQL agent trên toàn cửa sổ |
| TorAI | Không dùng đồ thị gọi, không LLM, cho nguồn thiếu điểm 0 | Đúng cả ba. Bổ sung: không dùng span bên gọi (tr. 6), dữ liệu tự thu OB/SS/TT không phải RE2 (tr. 10), blind spot chiều ngược (thiếu trace, còn metric), có phép đo theo dịch vụ ở tr. 11 và 18 |
| 2608.21310 | MIS1 và taxonomy OMIT | Đúng. Bổ sung: OMIT1 "baseline gap" và MIS3 "đảo chiều bên gọi/bên được gọi" đã được gọi tên (tr. 14) nên động cơ M2 có chỗ trích dẫn; agent SQL truy vấn bảng thô; nghiên cứu có đưa RCLAgent V2 vào số framework khảo sát |
| 2601.22208 | Bỏ metric làm giảm nhiều nhất | Đúng (tr. 7). **Bổ sung đối chứng:** bỏ trace thường làm tăng độ chính xác (Observation 7, tr. 8), vì LLM bám vào quan hệ gọi và trace nhiễu; reviewer có thể dùng điều này hỏi vì sao đưa thêm bằng chứng từ trace là có lợi |
| GALA+ | Dùng thống kê độ trễ span, không trong bối cảnh thiếu metric | Đúng, chi tiết hơn: p99/p50, tâm đồ thị, thời gian tự xử lý, không có mốc train (tr. 3); đồ thị từ cả corpus trace; dữ liệu OB và TT, không RE2 (tr. 6) |
| CLOSER 2025 | Metric bị ẩn, độ trễ so mức bình thường, PoC một dataset | Đúng. Bổ sung: rule-based, không LLM, một ngày của bộ ISP (TraceRCA), so với cực đại trước lỗi (tr. 6-7), chưa có số độ chính xác định lượng (tr. 8) |
| ReconRCA | Chỉ thấy tên trong danh sách tham khảo | **Có thật:** ICWS 2025, DOI 10.1109/ICWS67624.2025.00024, tr. 116-126, abstract đọc được qua Semantic Scholar. Bản đầy đủ không tải được. Khôi phục metric, không LLM, không rõ dataset |
| 2607.13548 | Kiểm toán chỉ cho metric, theo nhãn | Đúng (tr. 1, 15). "Absent KPI" trong bài là KPI không có trong schema, không liên quan M1 |
| "Free to Look" | Mới đọc abstract | Đã đọc phần đầu. Xác nhận SQL agent trên bảng thô; RCLAgent-V2 bị loại vì chi phí (tr. 4); ca dữ liệu không đầy đủ bị loại (tr. 3). Phải có baseline này |
| RCLAgent Sec. VI | "nêu giả định như giới hạn, không đo" | Đúng, giờ có câu chữ và số trang (tr. 14). Bổ sung: giới hạn (2) gán nguyên nhân cho tracing không đầy đủ, khác với trường hợp dịch vụ lỗi được instrument nhưng không nằm trong trace được giao |

Mục 3 của báo cáo tra tính mới (bảng đối chiếu claim) cần cập nhật theo bảng trên; báo cáo này không sửa file đó, theo phạm vi giao.

## 7. Bổ sung tối 2026-11-02: bốn bài mới

Tra lại khi chuẩn bị phương án dự phòng (sếp bỏ ràng buộc quota). Mức đọc: bản HTML nguyên văn trên arXiv, đọc qua WebFetch, tức là qua bản tóm tắt của công cụ chứ chưa phải tự đọc từng trang như mục 1. Số mục là số mục trong HTML. Cần tải PDF và đọc lại trước khi trích trong bài.

| Bài | Nội dung liên quan | M1 | M2 | M3 | P |
|---|---|---|---|---|---|
| EviRCA 2609.19825 (17/9/2026; deepseek-v4-pro, qwen3.7-plus; OpenRCA Bank, Telecom, Market) | Bước tất định dựng "evidence card" từ metric, trace, log của cả cửa sổ truy vấn (Sec. III-B); LLM chỉ đọc card qua tool chỉ đọc. Lỗi chủ yếu nằm ở bằng chứng đã có mặt: chọn nhầm dịch vụ nạn nhân phía sau 35%, sai lý do 21%; dịch vụ thật không lên card ở khoảng 22,5% (Sec. IV-E) | một phần. Tool chỉ được đưa ra khi hệ có modality đó (Sec. III-C); tool thành phần báo kiểu "blind/saturated" (Table II). Không phân biệt "vắng" với "khỏe" như một cơ chế, không thử bỏ metric | một phần. Trace chỉ vào bộ phát hiện "call lỗi hoặc chậm bất thường"; mốc thống kê cả ngày là cho KPI thành phần, không nêu mốc cho độ trễ trace, không tách bên gọi/bên được gọi | một phần. Card tóm tắt cả cửa sổ, không có trace truy vấn, không kích hoạt theo phủ | không |
| Where RCA Fails 2609.36686 (NeurIPS 2026 E&D; có Luan Pham) | Tách RCA thành truy hồi ứng viên và LLM xếp lại (gpt-oss-120b). Trên RCAEval **RE1** (chỉ metric): RE1-OB 0,875 so với BARO 0,784 | không | không (chỉ metric) | không | một phần, khác loại: đo "truy hồi hụt" của ứng viên, không phải phủ trace |
| Rethinking Tool Design 2610.05009 (4/10/2026; Qwen3-8B tới Qwen3.7-Plus; RCAEval **RE1**, 375 case) | 24 tool ba tầng, chỉ metric; log và trace ngoài phạm vi (Sec. 5.2). Thêm bằng chứng làm giảm AC@1 (L3 82,8% xuống L2+L3 78,2%); agent bỏ khuyến nghị đúng nhiều hơn sửa sai (Sec. 4.1-4.2); Qwen3-8B tụt 13,9 điểm khi thêm L3 vì hầu như không gọi nó | không | không | không | không |
| ThinkFL 2504.18776 (TOSEM 2026; cùng nhóm RCLAgent) | GRPO nhiều giai đoạn trên Llama-3.2-3B, trace và metric, reward theo hạng + đường suy luận + phạt ảo giác; SFT 100 câu AIOps 2022; vượt Claude-3.5-Sonnet 13,05% Recall@1 | không thấy trong phần đã đọc | không | không | không |

### Sửa câu được phép viết

- **Câu 3 (mục 4) viết lại:** "Chúng tôi chưa thấy agent LLM nào, khi metric vắng, nhận KPI độ trễ dựng từ trace so với mốc train ở cả bên gọi lẫn bên được gọi. EviRCA (2609.19825) đưa bằng chứng tất định dựng từ trace cho LLM, nhưng chỉ ở dạng phát hiện call lỗi hoặc chậm, không có mốc cho độ trễ trace và không xét metric vắng." Bắt buộc trích EviRCA ngay trong câu.
- **Câu 4 giữ, thêm chú thích EviRCA:** card của EviRCA phủ cả cửa sổ, nên "nhìn ra ngoài trace" không mới về khả năng; phần mới chỉ còn là agent bám trace có điều kiện kích hoạt theo phủ cộng phép đo phủ.
- **Câu mới được viết:** "Trên RE1 chỉ có metric, thêm tool bằng chứng có thể làm giảm độ chính xác (2610.05009); chúng tôi đo hiệu ứng này trên RE2-OB, có trace và có metric vắng." Chỉ viết vế sau nếu lượt dev đo được.

### Câu không được viết, bổ sung

1. "Đầu tiên tách bước trích bằng chứng tất định khỏi bước suy luận LLM." Đã có ở EviRCA.
2. "Đầu tiên ghép bộ xếp hạng thống kê với LLM xếp lại." Đã có ở 2609.36686 (trên RE1).
3. "Đầu tiên fine-tune RL model nhỏ cho định vị lỗi microservice." Đã có ở ThinkFL; phần còn mới chỉ có thể là huấn luyện với nguồn bị bỏ ngẫu nhiên, nếu tra lại vẫn không thấy.

## Câu hỏi còn mở

1. ReconRCA: cần bản đầy đủ (qua thư viện UIT hoặc xin tác giả) để biết dataset, và xem nó có chạy trên RE2 hay không. Hiện chỉ được viết tên bài và nội dung abstract.
2. AMER-RCL Sec. 4.1.2 và 4.3 (memory, cách chọn alert tương tự) chưa đọc kỹ. Cần đọc để chắc rằng không có bước nào mở rộng sang trace khác theo điều kiện phủ; hiện kết luận dựa trên Algorithm 1 và phần mô tả tổng quan.
3. Chưa đọc phụ lục của các bài (phần prompt và công cụ của 2608.21310 và 2610.35767). Nếu cần chắc rằng DiagGuard hoặc các harness không có bước "đối chiếu nguồn vắng", phải đọc thêm; hiện chỉ khẳng định theo các mục đã đọc.
4. Chưa tra có bài nào tương tự ngoài danh sách 11 bài và các lượt trước. Trước khi nộp nên tra lại từ khóa "query trace coverage", "trace sampling blind spot LLM" và các bản mới tháng 11.
5. Trần phủ 75% trên train có giữ được trên test split không (D12) vẫn cần sếp quyết, như báo cáo trước.
