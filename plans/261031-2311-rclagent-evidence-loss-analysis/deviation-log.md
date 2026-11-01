# Nhật ký deviation: đo nơi mất bằng chứng theo giai đoạn (RQ b)

Mọi thay đổi luật, analyzer hay module nạp **sau khi đóng băng** ghi ở đây, kèm số liệu trước và sau. Thay đổi trong giai đoạn hiệu chỉnh không phải deviation (xem bảng thay đổi hiệu chỉnh ở mục 13.3 của codebook).

## Mốc đóng băng

- Phiên bản codebook: v1, đóng băng cục bộ lúc 2026-11-01T03:50:04+07:00 (Asia/Saigon).
- Biên nhận: `plans/261026-1713-rclagent-tai-hien-toi-thieu/kaggle/evidence-loss-prereg.json` (SHA256 codebook, analyzer và bốn module nạp, đã chuẩn hóa CRLF thành LF).
- SHA256 codebook v1: `f06077a1a3eb2ab0301f605edbe7e48ef5d94a80b7a99fcd0f5fb3a6f73fc769`.
- **Đóng băng cục bộ, không có thứ tự thời gian độc lập**: chưa commit (câu hỏi mở 7 của kế hoạch chờ sếp). Hash này là bằng chứng thứ tự duy nhất; sếp có thể tự lưu nó ở nơi có dấu thời gian ngoài repo.
- Chưa có nhãn nào của analyzer trên `metric` hay `no_metric` tại thời điểm đóng băng; chỉ có nhãn của hai run hiệu chỉnh `metric_no_log` (case `99f095`).

## Bảng deviation

| Mã deviation | Ngày | Nội dung | Lý do | Tác động trước và sau | Hash codebook mới |
|---|---|---|---|---|---|
| (chưa có deviation về luật hay code) | | | | | |
| Erratum 1 (chỉ chữ, không phải deviation) | 2026-11-01 | Codebook v1 mục 4, đoạn I1 (dòng khoảng 178) viết `de6a50` `metric_no_log` s26 đến s28 có I1 đúng và I3 sai. Sự kiện thô: s26 và s27 có carrier `frontendservice` (`fecaffccd09a1711`) với `is_abnormal=true` (I1 đúng, I3 sai); s28 có carrier duy nhất cùng span với `is_abnormal=false` và `has_metric_anomaly=false`, nên I1 sai (`S1_not_flagged`), không phải I1 đúng và I3 sai | Chữ của codebook sai ở s28; analyzer đúng (đọc cờ bằng `json.loads` từ `agent_complete`) | Không đổi luật, code, hash hay nhãn nào; chỉ chú thích văn bản. Nhãn S1 v2 `de6a50 metric_no_log`: s26 `S3`, s27 `S2`, s28 `S1`; vòng 2 giống hệt | Không đổi (`f06077a1a3eb2ab0301f605edbe7e48ef5d94a80b7a99fcd0f5fb3a6f73fc769`); codebook không sửa |
