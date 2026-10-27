---
phase: 3
title: "Chiến dịch tìm kiếm theo batch"
status: done
receipt: work/receipts/03-synonym-search-01.json
owner_skills: [nckh-literature]
---

# Giai đoạn 03: Chiến dịch tìm kiếm

## Yêu cầu

- Chạy hết 17 truy vấn đã đóng băng ([protocol §5](protocol.md)), mọi trang; một truy vấn = một batch có checkpoint.
- Làn Elicit (tùy chọn, truy vấn công khai): tối đa các truy vấn tương ứng họ A, B, C; chỉ lấy bản ghi tạp chí vào T0.
- Ghi cả truy vấn rỗng, lỗi, rate limit; không chạy lại im lặng.

## Tệp

- Tạo: `work/raw/openalex/<query>-p<n>.json` (gitignore), `work/raw/elicit/<query>.json`, `work/search-log.csv` (query, provider, filter, as-of UTC, trang, count meta, số bản ghi nhận, HTTP status, raw SHA-256), `work/records/search-<query>.csv`, `work/receipts/03-<query>-<attempt>.json`.
- Script mới: `work/scripts/search-openalex-cursor.py` (stdlib, `python -X utf8 -I`).

## Các bước

1. Viết script phân trang cursor (`cursor=*`, `per_page=200`, `select` các trường §12), retry có backoff cho 429/5xx tối đa 5 lần, ghi mỗi trang một file mới.
2. Với mỗi truy vấn theo thứ tự A1 → D8: kiểm state; nếu `committed` và hash khớp thì bỏ qua; nếu không, attempt mới.
3. Chuẩn hóa trang thô thành `search-<query>.csv`; ghi `origin: search:<query>:<page>`.
4. Kiểm nhất quán: số bản ghi nhận = `meta.count` (± bản ghi thay đổi trong lúc chạy, ghi chênh).
5. Làn Elicit: dùng `search_papers` với truy vấn công khai; lưu kết quả thô; ghi usage.
6. Cập nhật state sau từng batch; cuối phase ghi tổng bản ghi thô theo truy vấn.

## Kiểm tra

- `search-log.csv` có ≥ 17 dòng truy vấn OpenAlex, mỗi trang có raw SHA-256 khớp file trên đĩa.
- Mỗi batch có receipt với exit của từng lệnh; không batch nào `running` khi kết thúc phase.
- Resume test: dừng giữa một truy vấn (hoặc mô phỏng bằng xóa state batch), chạy lại, xác nhận batch đã commit không bị gọi lại.

## Rủi ro và hoàn tác

- OpenAlex đòi API key hoặc giới hạn ngày: ghi `NOT_CALLABLE`/`rate-limited`, tiếp tục phiên sau từ checkpoint; dùng Crossref làm làn thay thế cho truy vấn họ A/B.
- Kết quả thay đổi giữa các phiên: as-of riêng mỗi batch; không trộn batch cùng truy vấn từ hai ngày khác nhau mà không ghi.
- Hoàn tác: xóa attempt lỗi khỏi state (giữ file và receipt), chạy attempt mới.
