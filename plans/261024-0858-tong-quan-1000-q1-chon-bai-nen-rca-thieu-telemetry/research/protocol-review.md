# Review giao thức trước freeze: tổng quan 1.000 → 100 → 10 → 1

- Ngày: 24/10/2026, Asia/Saigon. Reviewer chạy ngữ cảnh mới, chỉ đọc (agent `nckh-reviewer`, không có công cụ ghi). Agent điều phối lưu nguyên nội dung báo cáo vào file này.
- Đối tượng: `protocol.md` (revision `draft-261024`) và `work/amendments.md` (3 dòng sửa trước freeze).
- Reviewer đã đọc: `plan.md`, `phase-01`, các dòng liên quan của `phase-04/05/07/08`, `work/query-probe-02.csv`, `work/regex-calibration.json`, `work/sjr-regex-summary.json`, `work/sjr-edition-check.md`, `work/scripts/common.py`, `work/scripts/queries.py`, `decisions.md` (18–20/10). Reviewer có grep CSV SJR (hash `6f2039…7180`) để kiểm PR-06.
- Không chạy truy vấn mạng, không chạy script.
- Giới hạn: reviewer là mô hình, không thay cho chủ dự án hay chuyên gia; không kiểm lại số probe trực tiếp trên OpenAlex.

## Kết luận của reviewer

- Câu hỏi và PCC khớp mục tiêu. Giao thức không chọn trước bài nào.
- Chuẩn Q1 thực thi được; ấn bản 2025 đã được xác nhận.
- **Chặn:** PR-01 (§8 không có nhánh khi 0 hoặc 1 bài đạt cổng G), PR-02 (late-records thay T1 qua amendment không tiêu chí).
- **Nên sửa ưu tiên cao:** PR-03 đến PR-05.
- Status: DONE_WITH_CONCERNS.

## Bảng phát hiện (nguyên văn rút gọn) và cách xử lý

| Mã | Mức | Vấn đề | Đề xuất của reviewer | Xử lý của agent điều phối |
|---|---|---|---|---|
| PR-01 | chặn | §8 không có nhánh khi 0 hoặc 1 bài đạt G; độ nhạy tầm thường khi 1 bài đạt | 0 bài → không đề xuất, `waiting-human`, chủ dự án chọn nới đúng một cổng bằng amendment hoặc mở rộng hạng 11–20; 1 bài → nhãn `single-eligible`, độ nhạy chạy trên cả 10 bài bỏ cổng G; cấm nới cổng sau khi biết bài nào đạt | Áp dụng ở §8 |
| PR-02 | chặn | late-record vào T1 qua amendment không tiêu chí | Vào T1 chỉ khi hạng tất định ≤ 100 và chưa ghi điểm F nào; sau điểm F đầu tiên chỉ báo, kiểm prior work, không làm bài nền; ngoại lệ cần amendment được chủ dự án duyệt trước khi đọc toàn văn | Áp dụng ở §5 |
| PR-03 | cao | F chưa có mô tả mức | Mô tả từng mức F1–F6; đưa luật kiểm 10% phase 07 vào §7 | Áp dụng ở §7 |
| PR-04 | cao | Chấm lại F ở T3 không ràng buộc | `f-rescore-log` có locator + lý do trước khi xếp hạng; báo cả hai bảng; hạng 1 đổi → reviewer mới chấm độc lập hai bài đầu | Áp dụng ở §8 |
| PR-05 | cao | “1.000” đo trên T0 nhiễu; §10 không kích hoạt | Ghi rõ 1.000 là metadata; báo N(I1∧I2) và precision T0 kèm CI; nếu N(T0)×precision < 500 vẫn chạy bước 1–2 §10 | Áp dụng ở §4, §10 |
| PR-06 | nên sửa | Q-4 loại tạp chí reliability (IEEE TR không có category CS); 2614 thuộc nhóm Mathematics | Giữ Q-4; báo `q1_noncs` theo tạp chí; bài `q1_noncs` đạt ngưỡng top-100 liệt kê ở độ nhạy | Áp dụng ở §3; quyết định thêm Engineering vẫn của chủ dự án |
| PR-07 | nên sửa | Kiểm sai âm 50 mẫu yếu; số hiệu chỉnh in-sample | Định nghĩa “đúng ra phải giữ” = I1∧I2; mẫu phân tầng 25 giáp ranh + 25 không khớp; > 1 sai âm giáp ranh → amendment; báo cận Clopper-Pearson; ghi in-sample | Áp dụng ở §4 |
| PR-08 | nên sửa | Cổng trên chỉ tiêu đề loại oan | Cổng chạy sau bổ sung abstract; chỉ có tiêu đề mà trượt → `needs-review` | Áp dụng ở §4 |
| PR-09 | nên sửa | Recall B1/C1; parser boolean có thể sai im lặng | Mở rộng B1, C1; kiểm tất định tỉ lệ khớp mệnh đề AND trên trang 1, < 80% → kiểm cú pháp | Áp dụng ở §5, chạy probe lại |
| PR-10 | nên sửa | Elicit chưa đóng băng | Dùng lại chuỗi §5, giới hạn kết quả, `origin: elicit:<query>` | Áp dụng ở §2/§5 |
| PR-11 | nên sửa | Độ tin cậy R chưa kiểm; R3 mức 1 mơ hồ | Mô tả mức R1–R3; báo đồng thuận R1–R3; luật giải bất đồng hạng 90–110 | Áp dụng ở §6 |
| PR-12 | nên sửa | T1 nghiêng LLM | Đếm bài R1=3∧R5=1∧R6=1 ngoài top-100; tối đa 10 bài vào T2 nhãn `reserve-nonllm` | Áp dụng ở §6 |
| PR-13 | nên sửa | Thiên lệch truy cập toàn văn | Luôn yêu cầu tải tay bài không OA trong top-30 theo R; báo tỉ lệ truy cập theo tầng R | Áp dụng ở §7/§9 |
| PR-14 | nên sửa | Độ nhạy chưa phủ lát cắt top-10, bất định điểm, hòa | Định nghĩa Σwᵢ·Fᵢ; hòa = không giữ hạng; chạy 18 kịch bản trên toàn bộ bài có F; thêm kịch bản ±1 ở ô lệch | Áp dụng ở §8 |
| PR-15 | nên sửa | G1/G3 không kiểm được tĩnh | G1: repo + license + entry point, hoặc checklist {thuật toán, siêu tham số, prompt, tiền xử lý}; G3 `static-estimate` | Áp dụng ở §8 |
| PR-16 | nên sửa | Tương thích H1 chỉ hậu kiểm; “ba vai trò cũ” không định nghĩa | Cờ `h1-compat`; “không” ở hạng 1 → `waiting-human`; định nghĩa hoặc xóa câu “ba vai trò cũ” | Áp dụng ở §8; xóa câu ở plan.md |
| PR-17 | nên sửa | Luật thiếu 1.000 còn khe hở | Mỗi bước chạy một lần; bão hòa chỉ báo; N < 300 → dừng; “hợp lệ” = qua §3–§4 | Áp dụng ở §10 |
| PR-18 | nên sửa | Q-5 online-first không thực thi được | Dùng `publication_date`; mốc `to_publication_date` cố định = ngày bắt đầu phase 03 | Áp dụng ở §3 |
| PR-19 | nên sửa | Q-9 chưa nói cách xác định | `language == "en"`; null → kiểm tiêu đề/abstract | Áp dụng ở §3 |
| PR-20 | nên sửa | Mạng DC/SDN chưa rõ Population | Mạng DC/cloud phục vụ dịch vụ → I1 có, R1 ≤ 2; lý thuyết diagnosability → E4/E3 | Áp dụng ở §6 |
| PR-21 | nên sửa | Script lệch schema §11 | Giữ `attempts[]`, raw path có mã attempt, resume kiểm protocol hash và input | Sửa `common.py` và §11 cho khớp |
| PR-22 | ghi nhận | Khóa tie-break cuối thiếu khi không DOI | DOI, nếu thiếu thì `openalex_id` | Áp dụng |
| PR-23 | ghi nhận | Q-7 ngoài định nghĩa SJR | Báo riêng số loại theo Q-7, `q1_weak` | Áp dụng ở §3 |
| PR-24 | ghi nhận | Đa modality tính ba lần | Nêu trong báo cáo | Ghi trong §8 |
| PR-25 | ghi nhận | `localiz` không khớp “localisation” | `locali[sz]` | Áp dụng |
| PR-26 | ghi nhận | Số 984.389 không có receipt | Giữ nguyên, không dùng làm bằng chứng chính | Giữ |
| PR-27 | ghi nhận | Screening theo thứ tự record_id dễ trôi theo cụm | Hoán vị bằng seed 20261024 | Áp dụng ở §6 |
| PR-28 | ghi nhận | Phase 01 ghi `per_page=1`, kiểm 30+30 cũ, `query-probe.csv` | Ghi trong `protocol-freeze.json` | Áp dụng |
