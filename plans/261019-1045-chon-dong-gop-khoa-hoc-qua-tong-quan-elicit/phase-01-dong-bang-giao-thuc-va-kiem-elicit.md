---
phase: 1
title: "Đóng băng giao thức và kiểm năng lực Elicit"
status: completed
effort: 0.5 ngày
depends_on: [plan approval]
---

# Phase 01: Đóng băng giao thức và kiểm năng lực Elicit

## Bối cảnh

Lúc lập kế hoạch chỉ chạy kiểm năng lực và 4 tìm kiếm phạm vi
([hồ sơ](research/elicit-mcp-capability-record.md)). Phase này đóng băng toàn bộ giao thức **trước**
khi chạy tìm kiếm chính, để mọi thay đổi về sau đều có ghi chép.

## Yêu cầu

1. Kiểm lại truy cập: `get_usage`, `list_library_collections`. Nếu `hasUsageRemaining = false` hoặc
   lỗi xác thực → dừng, báo **chặn truy cập** cho người dùng, không đi tiếp.
2. Kiểm ba điều chưa biết, mỗi điều một lệnh nhỏ, ghi `percentUsed` trước/sau:
   - `search_papers` với `maxResults: 500` cho một truy vấn H1 → trần thực tế của gói.
   - `save_library_sources` 3 bài đã biết (PACE-LM, LM-PACE, DecompRCA bằng elicitId) vào collection
     riêng `nt114-review-261019`, rồi `get_library_source_full_text` → Elicit có trả toàn văn không.
   - Nếu người dùng đã chọn dùng systematic review (xem Validation Log): **không** chạy thử ở đây;
     chi phí đo ở Phase 03 với lần chạy thật.
3. Viết `work/search-protocol.md`, đóng băng:
   - Bộ truy vấn của Phase 02 (chuỗi chính xác, chế độ, filter, `maxResults`).
   - Tiêu chí chọn/loại (mục bên dưới).
   - Quy tắc khử trùng lặp (Phase 03).
   - Schema trích xuất (Phase 04) và schema phát hiện (plan.md mục 6).
   - Ngân sách hạn mức (plan.md mục 9).
   - Các lựa chọn của người dùng từ Validation Log.
4. Mọi thay đổi sau khi đóng băng ghi vào mục "Sai lệch so với giao thức" ở cuối file, kèm lý do và ngày.

## Tiêu chí chọn (inclusion)

- I1: Chủ đề là chẩn đoán/định vị nguyên nhân gốc (RCA, fault localization, incident diagnosis) trong
  microservice, cloud, AIOps, hệ phân tán **hoặc** là phương pháp selective prediction / calibration /
  abstention / conformal cho LLM có thể chuyển sang RCA (chỉ cho khối phản chứng và phương pháp H1).
- I2: Có đánh giá thực nghiệm định lượng, hoặc là benchmark/dataset/khảo sát có hệ thống.
- I3: Năm 2020–2026 (bài nền trước 2020 chỉ vào qua snowballing).
- I4: Tiếng Anh, có tóm tắt.
- I5: Mọi trạng thái xuất bản: tạp chí, hội nghị, workshop, preprint; artifact chính thức.

## Tiêu chí loại (exclusion)

- E1: RCA trong y tế, an toàn bệnh nhân, sản xuất cơ khí, quản lý chất lượng không có thành phần phần mềm.
- E2: Chỉ phát hiện bất thường, không có bước định vị/chẩn đoán gốc (trừ khi có calibration/abstention liên quan H1).
- E3: Không có kết quả định lượng và không phải khảo sát/benchmark.
- E4: Bài rút lại (`retracted`), bài trùng lặp đã gộp.
- E5: Bài mạng xã hội, blog, video, slide: không vào corpus; nếu dẫn tới bài gốc thì ghi vào
  `work/weak-signals.csv` và tìm bài gốc.
- E6: Tạp chí săn mồi đã biết hoặc venue không xác minh được: **không loại**, nhưng gắn
  `uncertainty: high` và không được dùng một mình để kết luận chồng lấn.

## Kiểm "chỉ truy vấn công khai" (bắt buộc trước mỗi lệnh Elicit)

Một truy vấn chỉ được gửi khi **cả bốn** đúng:
1. Chỉ chứa thuật ngữ nghiên cứu, tên phương pháp/benchmark/bài báo công khai.
2. Không chứa ID sự cố, tên service nội bộ của dataset, số đo nội bộ (ví dụ "67/218"), đường dẫn repo.
3. Không đính kèm file của repo (`import_library_files`, `stage_*_upload` bị cấm với file repo).
4. `isPublic` không được đặt `true`; không gọi `create_session_share`.

Ghi kết quả kiểm vào cột `public_check` của `work/search-log.csv`.

## File

- Tạo: `work/search-protocol.md`, `work/usage-log.csv`, `work/search-log.csv` (header),
  `work/git-baseline.txt` (đầu ra `git rev-parse HEAD` và `git status --porcelain` lúc bắt đầu, cho AC12).
- Không sửa gì ngoài thư mục kế hoạch.

## Kiểm chứng

- `work/usage-log.csv` có ≥ 3 dòng (trước, sau thử trần, sau thử thư viện).
- `work/search-protocol.md` có đủ 6 mục ở yêu cầu 3.
- Hồ sơ năng lực được cập nhật với ba kết quả mới.

## Rủi ro và hoàn tác

- Thử `maxResults: 500` có thể tốn hạn mức → nếu `percentUsed` tăng > 2 %, hạ về 200 cho Phase 02.
- Collection Elicit tạo ra có thể xoá sau khi xong; ghi ID để người dùng tự quyết.
