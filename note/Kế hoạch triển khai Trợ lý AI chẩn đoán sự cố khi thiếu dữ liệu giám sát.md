# Kế hoạch triển khai: Trợ lý AI chẩn đoán sự cố khi thiếu dữ liệu giám sát

Oct 13, 2026 · @Văn Nam

## Tóm tắt

Kế hoạch có 12 tuần, chia 6 giai đoạn: tuần 1–3 viết code, tuần 4–7 chạy thí nghiệm, phần viết bài làm song song từ tuần 3. Tên đề tài chốt sau khi có kết quả tuần 7.

**Bài toán thực tế.** Lúc 3 giờ sáng hệ thống báo lỗi, kỹ sư trực hỏi trợ lý AI dịch vụ nào gây lỗi. Trợ lý trả lời rất chắc chắn nhưng sai, vì dịch vụ gây lỗi thật chưa được gắn trace. Đề tài đo xem tình huống này xảy ra bao nhiêu lần và cách nào giảm được nó.

**Ba câu hỏi nghiên cứu**

1. Khi thiếu dữ liệu giám sát, trợ lý chỉ sai bao nhiêu lần, và bao nhiêu lần sai mà vẫn rất chắc chắn?
2. Tra lại các sự cố cũ giống ca hiện tại có giúp trợ lý đoán đúng hơn không, hay làm nó lạc hướng?
3. Nếu cho trợ lý được nói "chưa đủ dữ liệu, hãy kiểm tra X", kỹ sư có đỡ mất công hơn không?

**Bài nền.** Tái lập và mở rộng pipeline truy hồi ca cũ của P31 (Complex & Intelligent Systems, 2025). Giả thuyết "RAG có thể gây hại" lấy từ P50, cách đo ECE và coverage theo P42. Động lực thiếu trace lấy từ phần hạn chế của P18.

**Phạm vi**

- Dữ liệu: RCAEval RE2 và RE3, tổng 360 ca trên Online Boutique, Sock Shop và Train Ticket. Đây là hai bộ duy nhất có đủ metric, log và trace. Sock Shop không có trace.
- Mô hình: LLM open-weight 3B và 8B, lượng tử 4-bit, chạy bằng vLLM trên laptop RTX 4080 12 GB. Jev gọi qua API.
- Demo: Online Boutique chạy trên K8s cục bộ, tiêm lỗi rồi tắt trace của một dịch vụ.

## Lộ trình 12 tuần

&#91;embedded content: lộ trình 12 tuần · 6 giai đoạn, 4 mốc kiểm tra\]

Code xong trước rồi mới chạy; phần viết bài chạy song song từ tuần 3. Điểm dừng cuối tuần 5 quyết định có giữ phần truy hồi hay thu bài về câu hỏi 1.

## Giai đoạn 0 · Chuẩn bị (tuần 1, nửa đầu)

Mục tiêu: máy chạy được RCAEval, vLLM và có sẵn khung repo trước khi viết dòng code nghiên cứu đầu tiên.

1. **Môi trường.** Dùng Ubuntu 22.04 (hoặc WSL2) với Python 3.12, đúng khuyến nghị của RCAEval. Tạo hai môi trường riêng: `rcaeval` cho dữ liệu và baseline, `llm` cho vLLM, để tránh xung đột thư viện.
2. **Dữ liệu.** Chạy `pip install RCAEval[default]`, rồi tải RE2 và RE3 từ Hugging Face bằng `snapshot_download` với `allow_patterns` là `re2*` và `re3*`. Mỗi ca là một thư mục `{bộ}_{dịch vụ}_{lỗi}_{lần}` gồm metric, `logs.csv`, `traces.csv` và `inject_time.txt`.
3. **Kiểm tra dữ liệu.** Chạy `python -m pytest tests/test.py::test_basic`, rồi chạy một baseline có sẵn (BARO hoặc Multi-source BARO) trên RE2 để có số Avg@5 làm mốc so sánh.
4. **LLM.** Cài vLLM, tải một mô hình 8B bản AWQ 4-bit và một mô hình 3B. Mở server kiểu OpenAI với `--max-model-len 16384` và `--gpu-memory-utilization 0.85`, rồi gửi thử một prompt.
5. **Jev.** Đăng ký early access ngay từ tuần 1, vì có thể phải chờ được cấp quyền.

**Khung repo**

```
nt114-rca/
  configs/          # mỗi thí nghiệm một file YAML
  src/
    data.py         # đọc ca RCAEval
    ablate.py       # bỏ modality
    evidence.py     # tóm tắt bằng chứng thành văn bản
    retrieve.py     # kho ca cũ + BM25 / dense / hybrid
    llm.py          # gọi vLLM, parse JSON, lấy mẫu
    gate.py         # ngưỡng / bandit / Jev
    metrics.py      # AC@k, sai-mà-chắc, ECE, AURC
    run_grid.py     # chạy lưới, ghi kết quả từng ca
  results/          # mỗi ca một dòng JSONL, không ghi đè
  notebooks/        # phân tích, vẽ hình
  paper/            # bản thảo
```

**Xong khi:** baseline ra được số trên RE2, vLLM trả lời được một prompt, repo đã lên Git.

## Giai đoạn 1 · Viết code pipeline (tuần 1–3)

Code xong theo thứ tự dưới đây. Mỗi module có test nhỏ chạy trên 5 ca trước khi làm module sau. Tuần 1 làm 1–3, tuần 2 làm 4–5, tuần 3 làm 6–8.

| # | Module | Làm gì | Xong khi |
| --- | --- | --- | --- |
| 1 | `data.py` | Đọc một ca: cắt cửa sổ quanh `inject_time`, lấy danh sách dịch vụ ứng viên, lấy nhãn đúng từ tên ca | Đọc đủ 360 ca, không lỗi, in ra số dịch vụ mỗi hệ thống |
| 2 | `ablate.py` | Tạo 5 điều kiện: đủ, bỏ trace, bỏ log, bỏ metric, và "mù dịch vụ gốc" (xóa trace của chính dịch vụ gây lỗi, đúng câu chuyện 3 giờ sáng) | Test xác nhận dữ liệu bị bỏ không còn sót trong đầu ra |
| 3 | `evidence.py` | Biến telemetry thành văn bản ngắn: metric lệch nhiều nhất so với trước lỗi (z-score), số lần xuất hiện của mẫu log lỗi (Drain3), thay đổi độ trễ và lỗi trên các cạnh trace. Xáo trộn thứ tự dịch vụ | Văn bản dưới 4.000 token, người đọc 5 ca thấy đủ ý |
| 4 | `llm.py` | Gọi vLLM, ép đầu ra JSON: top-5 dịch vụ, độ tự tin 0–100, cờ "chưa đủ dữ liệu", việc cần kiểm tra tiếp. Lấy 5 mẫu mỗi ca. Cache theo hash của prompt | 100% câu trả lời parse được, chạy lại không tốn thêm lượt gọi |
| 5 | `retrieve.py` | Kho ca cũ gồm tóm tắt bằng chứng và nhãn. Ba kiểu tra: BM25, dense (mô hình embedding nhỏ), hybrid (gộp hạng bằng RRF). Lấy top-3 đưa vào prompt | Tra được cho mọi ca, không bao giờ trả về chính ca đang hỏi |
| 6 | `metrics.py` | AC@1, AC@3, Avg@5; tỷ lệ sai mà chắc (sai với độ tin cậy từ 0,8); số dịch vụ phải kiểm tra; ECE, AURC; McNemar và bootstrap | Ra đúng số trên ví dụ tính tay |
| 7 | `gate.py` | Ba chính sách đầu: luôn trả lời, ngưỡng trên độ tin cậy, Jev. Bandit để sang giai đoạn 3 | Chạy offline trên file kết quả, không gọi lại LLM |
| 8 | `run_grid.py` | Đọc YAML, chạy từng ô của lưới, ghi mỗi ca một dòng JSONL (đầu ra, số token, độ trễ). Tắt giữa chừng vẫn chạy tiếp được | Giết tiến trình rồi chạy lại, không ca nào bị chạy hai lần |

**Ba điểm dễ làm sai, phải chốt từ đầu**

- **Rò rỉ nhãn khi truy hồi.** RCAEval có nhiều ca cùng dịch vụ và cùng loại lỗi. Nếu kho có ca "anh em" của ca đang hỏi, LLM chỉ cần chép nhãn. Vì vậy chạy hai chế độ kho: *có tiền lệ* (chỉ loại chính ca đó, giống sự cố lặp lại ngoài đời) và *không tiền lệ* (loại mọi ca cùng dịch vụ và cùng lỗi).
- **Độ tự tin đo bằng hai cách.** Cách thứ nhất là con số LLM tự khai. Cách thứ hai là mức đồng thuận: tỷ lệ trong 5 mẫu cùng chọn một dịch vụ đứng đầu. Báo cáo cả hai.
- **Cố định mọi thứ.** Ghi seed, phiên bản mô hình, prompt và hash của config vào từng dòng kết quả. Prompt chốt trước khi chạy lưới lớn và không sửa giữa chừng.

## Giai đoạn 2 · Chạy thí nghiệm (tuần 4–7)

Chạy thử nhỏ trước, chốt prompt, rồi mới chạy lưới. Mỗi mô hình xong là phân tích ngay, không chờ chạy hết cả ba.

**Lưới thí nghiệm**

| Yếu tố | Mức |
| --- | --- |
| Modality | đủ · bỏ trace · bỏ log · bỏ metric · mù dịch vụ gốc |
| Truy hồi | không · BM25 · dense · hybrid |
| Kho ca cũ | có tiền lệ · không tiền lệ (chỉ khi có truy hồi) |
| Mô hình | 8B họ A · 8B họ B · 3B |
| Mẫu | 5 mẫu mỗi ca, nhiệt độ 0,7 |

Mỗi mô hình có khoảng 12.600 prompt trên 360 ca. vLLM sinh 5 mẫu từ cùng một lần đọc prompt, nên chi phí chủ yếu nằm ở phần đọc. Sock Shop không có trace nên có ít ô hơn.

**Các bước**

1. **Chạy thử (đầu tuần 4).** Lấy 30 ca (10 ca mỗi hệ thống), một mô hình 8B, đủ mọi ô. Kiểm tra:
   - tỷ lệ parse được JSON đạt 100%,
   - độ dài prompt nằm trong 16k token,
   - thời gian thật cho mỗi ca,
   - AC@1 khi đủ modality cao hơn chọn ngẫu nhiên và đặt cạnh baseline BARO.
2. **Chốt prompt và ước lại thời gian.** Nhân thời gian mỗi ca đo được với số ca của lưới. Ước lượng thô hiện tại là khoảng 10–20 giờ cho một mô hình 8B trên laptop 4080. Nếu vượt 2 ngày mỗi mô hình, giảm xuống 3 mẫu mỗi ca.
3. **Lưới đầy đủ với 8B họ A (tuần 4–5).** Chạy qua đêm. Sáng hôm sau kiểm tra log và số ca đã xong.
4. **Phân tích câu hỏi 1 và 2 (cuối tuần 5).** Vẽ bảng AC@1 theo modality × truy hồi và tỷ lệ sai mà chắc. Đây là điểm dừng (phần Rủi ro).
5. **8B họ B và 3B (tuần 6–7).** Chạy cùng lưới để kiểm tra kết luận có lặp lại ở họ mô hình khác và cỡ nhỏ hơn không.

**Khi chạy dài trên laptop:** cắm sạc, để chế độ hiệu năng cao, kê máy cho thoáng. Ghi `nvidia-smi` mỗi phút để biết GPU có bị hạ xung vì nóng không.

## Giai đoạn 3 · Lớp quyết định và Jev (tuần 7–8)

Lớp quyết định chạy hoàn toàn trên file kết quả của lưới. Lưới đã có đầu ra của mọi hành động cho mọi ca, nên không phải gọi lại LLM. Chỉ Jev cần gọi API.

**Hành động được chọn cho mỗi sự cố:** trả lời luôn · tra ca cũ rồi trả lời · chuyển từ 3B lên 8B · báo "chưa đủ dữ liệu, hãy kiểm tra X".

**Các chính sách được so sánh**

| Chính sách | Cách quyết định | Vai trò |
| --- | --- | --- |
| Luôn trả lời, không tra | Cố định | Mốc thấp nhất |
| Luôn tra hybrid | Cố định | Giống P31 |
| Ngưỡng | Độ tự tin dưới ngưỡng 1 thì tra, dưới ngưỡng 2 thì từ chối. Ngưỡng chọn trên dữ liệu huấn luyện | Cách đơn giản reviewer sẽ hỏi |
| Contextual bandit | Học từ đặc trưng: độ tự tin, mức đồng thuận, modality còn lại, độ giống của ca tra được | Phương pháp học được |
| Jev | Câu hỏi kiểu choice với trạng thái = tóm tắt bằng chứng + câu trả lời đầu của LLM + độ tự tin | Mô hình quyết định có sẵn, không huấn luyện |

**Cách đánh giá công bằng:** huấn luyện ngưỡng và bandit trên 2 hệ thống, kiểm tra trên hệ thống thứ 3, xoay vòng cả 3. Điểm thưởng: đúng +1, sai mà chắc bị phạt nặng, từ chối bị phạt nhẹ, trừ thêm theo số token. Chạy với vài mức phạt để thấy kết luận không phụ thuộc vào một cách chọn.

**Kết quả trình bày theo kiểu kỹ sư đọc được:** "Trên 100 sự cố, chính sách X tránh được N lần chỉ sai mà chắc, bỏ qua M sự cố, tốn T token." Thêm đường cong risk–coverage cho reviewer.

**Với Jev:** ghi phiên bản mô hình trong mỗi phản hồi, lưu toàn bộ đầu ra thô. Chạy thêm một lần cho Jev chọn trực tiếp dịch vụ gốc để đo AC@1 và ECE của chính Jev. Nếu chưa được cấp quyền đến tuần 8 thì bỏ nhánh Jev; bài vẫn đứng được.

## Giai đoạn 4 · Demo chạy thật trên K8s (tuần 9–10)

Demo cho người xem thấy câu chuyện 3 giờ sáng trên một hệ thống đang chạy. Số liệu chính của bài vẫn lấy từ RCAEval; demo dùng cho phần case study, buổi bảo vệ và đáp ứng yêu cầu K8s + tiêm lỗi trong Proposal.

1. **Dựng cụm.** Tạo cụm k3d trên laptop và triển khai Online Boutique (Google microservices-demo). Cài Prometheus cho metric, Loki cho log, OpenTelemetry Collector và Jaeger cho trace.
2. **Viết `live_adapter.py`.** Chuyển dữ liệu từ Prometheus, Loki và Jaeger về đúng định dạng mà `evidence.py` đang đọc, để dùng lại nguyên pipeline.
3. **Tiêm lỗi.** Dùng Chaos Mesh gây CPU cao hoặc trễ mạng trên một dịch vụ, ví dụ `cartservice`.
4. **Tắt trace của dịch vụ đó.** Đặt sampler của riêng dịch vụ này về 0, tái hiện đúng điều kiện "mù dịch vụ gốc".
5. **So hai trợ lý trên cùng sự cố.** Trợ lý thường (luôn trả lời) đứng cạnh trợ lý có lớp quyết định tốt nhất từ giai đoạn 3. Lặp lại khoảng 20 lần với các dịch vụ và loại lỗi khác nhau, ghi lại kết quả.
6. **Quay video 2–3 phút** cho buổi bảo vệ và đưa lên repo.

**Nếu thiếu thời gian:** cắt xuống còn 1 loại lỗi và 5 lần lặp. Không bỏ hẳn, vì đây là phần làm đề tài "thấy được".

## Giai đoạn 5 · Vừa viết vừa chỉnh (tuần 3–12)

Phần viết bắt đầu từ tuần 3, không chờ có đủ kết quả. Mỗi phần của bài được viết ngay khi phần code hoặc kết quả tương ứng xong.

| Phần của bài | Viết từ | Dựa vào |
| --- | --- | --- |
| Related Work | Tuần 3 | Bản đồ khảo sát 69 bài, nhấn vào P31, P50, P42, P18 |
| Method | Tuần 3–4 | Code đã chốt; viết đúng như code làm |
| Setup | Tuần 4 | Config YAML, bảng lưới, phần cứng |
| Kết quả câu hỏi 1–2 | Tuần 5–6 | Lưới của 8B họ A |
| Kết quả câu hỏi 3 | Tuần 8 | Giai đoạn 3 |
| Case study | Tuần 10 | Demo K8s |
| Introduction, Discussion, Threats to validity | Tuần 10–11 | Viết cuối, khi đã biết kết quả nói gì |
| Rà soát, nộp | Tuần 12 | Một người ngoài nhóm đọc trước |

**Hình và bảng cần có**

1. Sơ đồ pipeline: bằng chứng → truy hồi → LLM → lớp quyết định.
2. Bản đồ nhiệt AC@1 theo modality × truy hồi, mỗi hệ thống một ô.
3. Tỷ lệ sai mà chắc khi đủ và khi thiếu modality. Đây là hình chính của bài.
4. So sánh kho có tiền lệ và không tiền lệ.
5. Đường cong risk–coverage của các chính sách, kèm bảng "trên 100 sự cố".
6. Một ca demo minh họa: câu trả lời của hai trợ lý đặt cạnh nhau.

**Vòng chỉnh hàng tuần.** Mỗi cuối tuần họp 30 phút: kết quả mới có làm đổi nhận định nào trong bản thảo không, cần thêm hay bỏ thí nghiệm nào không. Mọi thay đổi ghi vào `DECISIONS.md` trong repo kèm lý do. Nếu phải đổi prompt sau khi đã chốt, chạy lại toàn bộ các ô bị ảnh hưởng, không trộn kết quả cũ và mới.

## Chia việc, rủi ro và việc cần GVHD duyệt

**Chia việc theo vai.** Gán tên khi nhóm họp; một người có thể giữ nhiều vai.

| Vai | Phụ trách | Giai đoạn chính |
| --- | --- | --- |
| Dữ liệu và đánh giá | `data.py`, `ablate.py`, `evidence.py`, `metrics.py`, baseline BARO | 0–2 |
| LLM và truy hồi | `llm.py`, `retrieve.py`, `run_grid.py`, chạy lưới trên laptop 4080 | 1–3 |
| Quyết định và demo | `gate.py`, Jev, cụm K8s, video | 3–4 |
| Viết bài | Related Work, Method, ghép kết quả vào bản thảo | 5, từ tuần 3 |

**Rủi ro và cách xử lý**

| Rủi ro | Dấu hiệu | Xử lý |
| --- | --- | --- |
| Truy hồi gần như không đổi kết quả | Cuối tuần 5, mọi kiểu truy hồi đổi AC@1 không quá ±2 điểm % ở mọi điều kiện | Bỏ phần gate theo truy hồi, bài tập trung vào câu hỏi 1 (sai mà chắc khi thiếu dữ liệu) và từ chối trả lời |
| LLM 8B quá yếu, AC@1 gần ngẫu nhiên | Chạy thử đầu tuần 4 | Rút gọn bằng chứng, thêm danh sách ứng viên từ BARO; kiểm 14B trên 100 ca bằng Kaggle |
| Chạy quá lâu trên laptop | Thời gian thật mỗi ca ở bước chạy thử | Giảm còn 3 mẫu mỗi ca, bỏ 3B, hoặc chuyển một mô hình sang Kaggle |
| Rò rỉ nhãn làm số đẹp giả | Kho có tiền lệ cho AC@1 cao bất thường | Chỉ dùng kho không tiền lệ cho kết luận chính |
| Không được cấp quyền Jev | Chưa có quyền đến tuần 8 | Bỏ nhánh Jev, giữ ngưỡng và bandit |
| Có bài mới chiếm mất gap | Kiểm lại arXiv và OpenAlex vào tuần 6 và tuần 11 | Trích dẫn và định vị lại điểm khác |

**Cần GVHD duyệt trước tuần 2**

- [ ] Hướng đề tài và ba câu hỏi nghiên cứu
- [ ] Dùng Jev, một mô hình đóng chỉ có qua API, làm một nhánh so sánh
- [ ] Tạp chí đích: Complex & Intelligent Systems hoặc Results in Engineering
- [ ] Mốc nộp bản thảo cuối tuần 12

Nguồn: [RCAEval trên GitHub](https://github.com/phamquiluan/RCAEval) (cấu trúc RE1–RE3, modality từng bộ, cách tải, baseline); [Jev trên Cloudflare AI docs](https://developers.cloudflare.com/ai/models/typesafe/jev/).
