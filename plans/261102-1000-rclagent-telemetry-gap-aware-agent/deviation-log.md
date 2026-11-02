# Nhật ký deviation: hướng A

Ghi các chỗ đặc tả trong [prereg](../reports/prereg-261102-rclagent-telemetry-gap-method.md) lệch khỏi [plan](plan.md) và các file phase. Mỗi dòng nêu lý do. Các mục ở đây chưa có hiệu lực trước khi sếp duyệt prereg.

| # | Ngày | Plan ghi | Prereg làm | Lý do |
|---|---|---|---|---|
| 1 | 2026-11-02 | M2 dùng độ trễ tự thân (phase 3) | M2 và M3 dùng `duration` | Span client chỉ phản ánh độ trễ của bên được gọi khi giữ cả thời gian chờ callee. Khám phá trên train: p95 phía client có R@1 0,685 trên truy vấn có phủ. |
| 2 | 2026-11-02 | M3 có điều kiện kích hoạt (phase 3) | M3 luôn được thêm khi cờ bật | Không có luật kích hoạt nào đã kiểm trên dữ liệu. Một luật đặt thêm sẽ là bậc tự do mới nhìn thấy sau khám phá. |
| 3 | 2026-11-02 | Trần số trace của M3 (phase 3) | Không có trần số trace; chỉ có trần token | Mọi trace trong cửa sổ được gộp trước trên CPU thành 10 dòng, nên số trace không ảnh hưởng ngữ cảnh. |
| 4 | 2026-11-02 | 6 điều kiện × 24 truy vấn, khoảng 34 giờ (plan) | 7 điều kiện × 25 truy vấn, khoảng 47 giờ | Review đòi thêm seed thứ hai cho mốc để ước nhiễu, và tách đóng góp của M2 với M3. Sếp quyết ở câu hỏi 1 của prereg. |
| 5 | 2026-11-02 | Baseline ReAct tự do truy vấn là tùy chọn (plan) | Hoãn tới đánh giá cuối nếu có Go, khi đó là bắt buộc | Nguyên văn 2610.35767 và 2608.21310 cho thấy nó là đối thủ trực tiếp của M3; chưa đủ ngân sách ở lượt dev. |
| 6 | 2026-11-02 | Luật Go chưa có (phase 3) | Luật Go chỉ so với bộ xếp hạng p95 trước truy vấn | Các baseline của phase 4 biết `inject_ts`, nên không so công bằng với agent chỉ thấy dữ liệu trước truy vấn. |
| 7 | 2026-11-02 | Lượt dev chạy trên Kaggle (phase 6) | 70 run trên Kaggle T4×2, 105 run trên Modal T4 (2 core, 12 GiB) | Quota T4 Kaggle chỉ còn 10 giờ. Modal dùng cùng GPU, FP16, model, giới hạn và sampling; mỗi run ghi `platform`. Luật chia site theo hash cố định trước khi chạy. |
| 8 | 2026-11-02 | Giới hạn harness không nêu (phase 5) | Giữ đúng giới hạn S1 v3: 8 vòng tool mỗi span, 320 request, 2400 s | Để mốc `base_*` so được với S1 v3; test `test_grid_keeps_the_s1_v3_limits` khóa giá trị này. |
| 9 | 2026-11-02 | Gói mỗi trace chỉ chứa dòng metric của case đó (kiểm tra nguồn gốc của `K/prepare-bundle.py`) | Cửa sổ ±1200 s của `d896c60f…` (recommendationservice_cpu_1) và `5f4c1e61…` (checkoutservice_mem_2) chạm case train kế tiếp; gói giữ đúng các dòng đó | Tool của tác giả trên dữ liệu gộp cũng trả các dòng này, nên gói vẫn khớp từng byte với dữ liệu đầy đủ. Kiểm tra nguồn gốc giờ đòi hợp các case train mà cửa sổ chạm, và vẫn dừng nếu chạm case val hoặc test. Tập dev không đổi. |
