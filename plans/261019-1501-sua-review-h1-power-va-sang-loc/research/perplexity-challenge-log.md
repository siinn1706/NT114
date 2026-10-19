# Nhật ký vòng thách thức H1 bằng Perplexity

Ngày 2026-10-19, 15:05–15:50 (Asia/Saigon). Dùng tài khoản Perplexity Pro đã đăng nhập sẵn của chủ dự
án, qua Claude in Chrome. Không mua nâng cấp, không dùng API trả phí, không tải file nào lên.

## Năng lực quan sát được

| Mục | Quan sát |
|---|---|
| Chế độ | Tìm kiếm; **Nghiên cứu chuyên sâu (Deep Research)**; Hội đồng mô hình (khoá, cần gói Max); Học từng bước |
| Model mặc định ở chế độ Tìm kiếm | GPT-6.1 Sol (Đang suy nghĩ) |
| Chế độ đã dùng | Nghiên cứu chuyên sâu, cho cả hai truy vấn (theo yêu cầu "GPT-6.1 Sol thinking hoặc Deep Research") |
| Thời gian | Truy vấn 1: 11 phút 11 giây. Truy vấn 2: khoảng 4 phút |

## Truy vấn (chỉ nội dung nghiên cứu công khai)

1. **Q1 (15:05):** câu hỏi H1 tổng quát. Gồm bài gần nhất về confidence, selective prediction và
   abstention cho LLM-RCA; bài về telemetry bị thiếu; phản chứng (verbal và self-consistency yếu);
   có bài nào báo risk ở cùng coverage so với deferral ngẫu nhiên chưa.
2. **Q2 (follow-up):** kiểm tra đối kháng TelemetrySuffBench, Nautil, CoreSec, JustDiag và mọi bài
   07–10/2026 về evidence sufficiency hoặc abstention cho agent sự cố. Thêm câu hỏi về self-consistency
   "nhất quán mà sai".

Không gửi dữ liệu, nhãn, kết quả nội bộ, đường dẫn hay file của repository.

## Kết quả và cách xử lý

Tóm tắt của Perplexity chỉ là công cụ phát hiện. Mọi số đưa vào báo cáo đều được đối chiếu với bài gốc.

| Mục Perplexity nêu | Đối chiếu nguồn gốc | Dùng trong báo cáo |
|---|---|---|
| Kết luận: chưa thấy bài RCA nào báo selective risk ở cùng coverage so với abstention ngẫu nhiên, kể cả khi bỏ metric, log hay trace | Khớp với F-009 và vòng gap cũ. Đây vẫn là kết luận vắng mặt | SS1 vẫn giữ nhãn ĐƠN-NGUỒN (vắng mặt); thêm nguồn tìm thứ hai |
| LM-PACE: chỉ ECE và reliability, không có risk–coverage | Khớp F-001, F-002 (đã đọc toàn văn) | Không đổi |
| Xiong et al. (arXiv 2306.13063): AUROC của verbal gần ngẫu nhiên | **Đã tải và đọc toàn văn.** Bài gốc còn ghi consistency 5 mẫu tăng AUROC GSM8K từ 54.8 % lên 92.7 %; Perplexity không nhấn điểm này | F-054 mới; sửa cách đọc F-014 |
| arXiv 2601.22208 (FORGE@ICSE 2026): bỏ từng modality, ΔLA −0.155, ΔTA −0.128, bỏ trace có thể làm tốt hơn tới +0.28 | **Khớp toàn văn** (dòng 878–893) | F-055 mới |
| GALA+ (arXiv 2608.08968, ASE 2026): confidence do LLM sinh ra | **Đã tải và đọc toàn văn.** Confidence chỉ dùng để dừng hay mở rộng tìm kiếm trên đồ thị (θ ≈ 0.6). Không có abstention hay risk–coverage | F-057 mới (overlaps, không pre-empt) |
| DiagGuard (arXiv 2608.21310): có verifier riêng, không abstention | Đã có F-030 (đọc toàn văn) | Không đổi |
| TelemetrySuffBench, Nautil, CoreSec: thu hẹp tính mới nhưng không pre-empt | Khớp F-004, F-005, F-007 (đã đọc toàn văn trước đó) | Không đổi |
| Nghiên cứu y khoa 48 LLM, AUROC tốt nhất 0.626 (DOI 10.1038/s44355-026-00053-3); một nghiên cứu Text-to-SQL selective | Chưa đối chiếu nguồn gốc | **Không dùng** |
| Eadro, Nezha có ablation modality; RC-LLM nhận modality vắng | Perplexity tự ghi là không trích được số | Không dùng số |

Perplexity còn đề xuất một phát biểu tính mới hẹp hơn, khớp với phát biểu đang dùng: chưa thấy nghiên
cứu nào đánh giá confidence hoặc mức đồng thuận mẫu của chính LLM so với abstention ngẫu nhiên ở
cùng coverage trên sự cố microservice, có bỏ metric, log hay trace có kiểm soát. Đây vẫn là kết luận
vắng mặt, không phải bằng chứng tính mới.

Toàn văn tải thêm (gitignored) nằm trong `private/fulltext/261019/`: `2306.13063.txt`, `2605.04530.txt`
(SADE) và `2608.08968.txt`.
