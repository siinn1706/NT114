# Phụ lục prereg: chọn hướng dự phòng sau lượt dev telemetry-gap

Viết tối 2026-11-02, khi 175 run đang chạy và **trước khi tải về bất kỳ output nào**. Hash của file này nằm trong `K/telemetry-gap-fallback-prereg.json`, kèm hash của bản prereg chính đã đóng băng (`K/telemetry-gap-prereg.json`). Phụ lục không đổi gì trong prereg chính: luật go/no-go, ngưỡng và lưới điều kiện giữ nguyên. Nó chỉ chốt trước việc **làm gì tiếp** ứng với từng kết cục, để hướng dự phòng không bị chọn sau khi đã nhìn dữ liệu.

`K/` là `plans/261026-1713-rclagent-tai-hien-toi-thieu/kaggle/`. Căn cứ về công trình liên quan: mục 7 của [báo cáo nguyên văn](research-261102-rclagent-direction-a-related-work-full-text.md).

## 1. Chỉ số chẩn đoán

Mọi chỉ số đọc thẳng từ `outcomes.json` do `K/decide-telemetry-gap-outcomes.py` ghi; script này đã nằm trong hash của prereg chính. Không tính thêm chỉ số nào sau khi xem kết quả. Ký hiệu `X.f` là trường `f` của điều kiện `X` trong `conditions`.

| Mã | Tên | Định nghĩa | Đúng khi |
|---|---|---|---|
| D1 | Agent bỏ qua KPI | `a_nometric.queried_gt_metric`: số truy vấn mà agent gọi `search_fluctuating_metrics` với tên dịch vụ lỗi | ≤ 12 trên 25 |
| D2 | Agent bỏ qua bảng cửa sổ | `a_nometric.r1_none` ≤ 1 trên 12 và `a_nometric.top1_outside_trace` ≤ 3 trên 25 | cả hai vế đúng |
| D3 | Thấy mà vẫn chọn sai | D1 sai, đồng thời `O1.net` ≤ `d_noise` | cả hai vế đúng |
| D4 | Bộ xếp hạng vượt xa agent | `O4.ranker.r1` − `O1.r1_x` | ≥ 3 |
| D5 | Lệch về cartservice | `O5.cart_top1_increase` | ≥ 3 |

D2 dùng tầng không phủ vì ở đó câu trả lời đúng bắt buộc nằm ngoài trace được giao, nên R@1 bằng 0 hay 1 ở tầng này cho thấy agent có dùng bảng M3 hay không.

## 2. Luật chọn hướng

Áp theo thứ tự; dòng đầu tiên khớp là quyết định. "Hướng" là đề xuất cho sếp duyệt, không tự chạy GPU.

| # | Kết cục của prereg chính | Chẩn đoán | Hướng tiếp |
|---|---|---|---|
| R1 | "chưa đủ bằng chứng" | bất kỳ | Cứu run thiếu (gói nhỏ chỉ gồm run chưa có trạng thái cuối, ghi deviation), rồi chạy lại script. Không chọn hướng khi chưa đủ |
| R2 | "Go, bài phương pháp" | bất kỳ | Giữ hướng A. Bắt buộc thêm trước khi viết: H-size, H-free và baseline truy hồi + LLM xếp lại (mục 3) |
| R3 | "Go, bài đo lường" | bất kỳ | H-meas làm khung bài, cộng H-size để tách yếu tố cỡ model |
| R4 | "no-go" | D1 hoặc D2 đúng | H-rl, dựng trên môi trường của harness hiện tại |
| R5 | "no-go" | D3 đúng | H-size trước. Nếu ở cỡ lớn hơn `a_nometric` đạt luật Go của prereg chính trên cùng 25 truy vấn, bài đi theo "phương pháp cần đủ năng lực model". Nếu không, H-free |
| R6 | "no-go" | không D nào ở trên đúng | H-free |

D4 và D5 không chọn hướng, nhưng phải báo trong mọi trường hợp. D4 đúng thì phép tách truy hồi/xếp hạng của H-meas được đưa vào bài, dù hướng chính là gì. D5 đúng thì mọi hướng có dùng tín hiệu độ trễ phải có chỉ số theo dõi cartservice như O5.

## 3. Các hướng

Mỗi hướng cần **prereg riêng** được sếp duyệt trước khi chạy GPU. Mọi luật mới phải kiểm trên val bằng CPU trước. Không chạy gì trên test split RE2-OB (D12).

- **H-rl: huấn luyện RL với nguồn bị bỏ ngẫu nhiên.**
  - Fine-tune Qwen3-4B-Instruct-2507 bằng GRPO, reward kiểm chứng được theo hạng của dịch vụ lỗi, chỉ trên 240 truy vấn train trừ tập dev 25 truy vấn.
  - Mỗi episode bỏ ngẫu nhiên metric, log, hoặc thay trace truy vấn bằng trace không phủ.
  - Đánh giá trên tập dev bằng đúng lưới 7 điều kiện.
  - Gần nhất là ThinkFL (2504.18776): GRPO trên Llama-3.2-3B, AIOps 2022, không xét thiếu nguồn. Phần mới chỉ có thể là huấn luyện với nguồn bị bỏ, và phải tra lại trước khi viết prereg của hướng này.
- **H-size: quét cỡ model.**
  - Chạy Qwen3-8B, Qwen3-14B, Qwen3-32B trên đúng lưới 7 điều kiện và 25 truy vấn, với giới hạn S1 v3.
  - Mỗi cỡ cần mốc S1 v3 riêng, vì đổi model là đổi mốc.
  - Căn cứ: 2610.05009 cho thấy lợi ích của tool phụ thuộc model, và Qwen3-8B hầu như không gọi tool tầng cao.
- **H-meas: bài đo lường.**
  - Gồm ba phần:
    - trần phạm vi trace (59/240 train, 25/105 val);
    - phép tách lỗi thành "truy hồi hụt" (trace không phủ dịch vụ lỗi) và "xếp hạng sai" (bằng chứng có mà chọn sai), theo cách tách của 2609.36686;
    - so agent với bộ xếp hạng p95.
  - Không cần GPU thêm.
- **H-free: agent tự do truy vấn bảng thô.**
  - Baseline kiểu "Free to Look" (2610.35767) chạy trên cùng 25 truy vấn, có thêm nhận biết nguồn vắng.
  - Đằng nào cũng là baseline bắt buộc trước khi viết bài (prereg chính, mục 7). Nếu nó thắng thì nó trở thành phương pháp.
- **Baseline truy hồi + LLM xếp lại.**
  - Bộ xếp hạng p95 đề cử top-k, LLM xếp lại trong k ứng viên.
  - Đây là baseline, không phải hướng, vì 2609.36686 đã làm trên RE1.

## 4. Giới hạn

- Ngưỡng D1–D5 đặt trước khi có kết quả LLM của lượt này, nhưng sau khi đã thấy S1 v3 và các lượt khám phá trên train (prereg chính, mục 8). Chúng là ngưỡng mô tả trên n = 25, không phải phép kiểm định.
- Phụ lục không xếp hạng các hướng theo khả năng thành công; thứ tự trong mục 2 là theo chẩn đoán, không theo kỳ vọng.
- Nhận định về EviRCA, 2609.36686, 2610.05009 và ThinkFL mới dựa trên bản HTML đọc qua công cụ; phải đọc PDF trước khi trích.
