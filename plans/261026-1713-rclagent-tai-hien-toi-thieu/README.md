# Chuẩn bị tái hiện tối thiểu RCLAgent: kiểm CPU (2026-10-26)

Phạm vi theo quyết định chủ dự án ngày 2026-10-26 (decisions.md, ba dòng cuối). Không gọi model, không GPU/API, không commit. Không phải chuỗi kế hoạch; chỉ là bản ghi kết quả kiểm và receipt.

## Vị trí

- Code tác giả: `F:/Nam/UIT/nt114-paper-artifacts/W7165616276/code`, clone `LLM4AIOps/RCLAgent-V2` tại `3052e7a6a9598d984ba1482f3dc41123c8823a99` (bằng HEAD remote ngày 2026-10-26, nên không có bản mới hơn để so). MIT. Không sửa file nào.
- Môi trường: `.../W7165616276/env`, Python 3.12.10, cài từ `requirements.txt` trừ `baro`; danh sách bản cài ở `.../W7165616276/env-freeze.txt` (pandas 3.1.0, numpy 2.5.4; tác giả chỉ ghim cận dưới).
- Dữ liệu: `RE2-OB.zip` của bản sao Zenodo 14590730 trong NT114 (sha256 khớp manifest) giải nén ra `.../W7165616276/data/raw`; đầu ra preprocess ở `.../W7165616276/data/re2ob`. Zip gốc chỉ được đọc.

## Receipt (`work/receipts`, đều `check-receipt` VERIFIED)

| Id | Nội dung | Kết quả |
|---|---|---|
| 01-scorer-fixtures-01 | Chép `sample_data`, dựng fixture tổng hợp | exit 0 |
| 01-scorer-sample-01 | `evaluate.py` trên mẫu tác giả | R@1 = MRR = 1.0 (1/1), khớp tính tay |
| 01-scorer-fixture-01 | `evaluate.py` trên fixture best-of/mẫu số | 2/3 lỗi được chấm, R@1 0.5, R@3 1.0, MRR 0.6667, khớp tính tay |
| 02-extract-re2ob-01 | Kiểm hash, giải nén | 90 ca số + 1 thư mục `checkoutservice_cpu/multi-source-data` (bị preprocess bỏ qua), đủ file |
| 03-preprocess-re2ob-01 | `preprocess_re2ob.py` không sửa | 90 ca, 450 error trace, 34,46 triệu span, 9,41 triệu dòng metric, 15,05 triệu dòng log |
| 04-case-roles-01 | Ghép ca với vai split qua thời điểm inject | train 48 (1 ca khớp hai incident), val 21, test 21 |
| 05-trial-case-profile-01 | Profile ca thử `checkoutservice_cpu_2` | 5 trace, 33–39 span, sâu 4; ≥ 67–79 lời gọi/trace; đo bộ nhớ thất bại (peak 0.0, lỗi đo) |

Kiểm này chỉ là kiểm bộ chấm và dữ liệu, không phải kết quả tái hiện phương pháp.

## Lượt Kaggle theo yêu cầu tiếp theo

Quyền chạy Kaggle GPU với gói công khai tối thiểu được người dùng bổ sung sau bản ghi CPU trên. Notebook, bundle và hướng dẫn hiện ở [kaggle/README.md](kaggle/README.md); phân tích và sửa lỗi T4 ở [kaggle/repair-report.md](kaggle/repair-report.md). Vẫn không chạy LLM trên Windows hoặc commit/push. Bản ghi CPU phía trên là lịch sử chuẩn bị, không thay thế trạng thái native Kaggle.
