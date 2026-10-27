---
phase: 4
title: "Khử trùng, cổng Q1/năm/loại/chủ đề, bổ sung abstract"
status: done
receipt: work/receipts/04-t0-review-r2-01.json
owner_skills: [nckh-literature, nckh-evidence]
---

# Giai đoạn 04: Khử trùng và cổng Q1 → T0 tạm

## Yêu cầu

- Từ seed (phase 02) + search (phase 03) tạo T0 tạm: bản ghi duy nhất qua Q-1…Q-9 và cổng chủ đề §4.
- Khử trùng tất định: DOI chuẩn hóa → OpenAlex ID → (tiêu đề chuẩn hóa + năm + tác giả đầu) chỉ gợi ý `needs-review`, không tự gộp.
- Bổ sung abstract cho bản ghi thiếu trước screening.
- Dossier qua `check-literature.py` của nckh-literature.

## Tệp

- Đọc: `work/records/seed-reused.csv`, `work/records/search-*.csv`, CSV SJR.
- Tạo: `work/records/t0-candidates.csv`, `work/records/t0-excluded.csv` (mã lý do), `work/dedup-groups.csv`, `work/abstract-fill-log.csv`, `work/t0-gate-check.csv` (mẫu 50 sai âm), `work/dossier/` (input/manifest cho `search-literature.py`), `work/receipts/04-*.json`.

## Các bước

1. Gộp mọi nguồn, chuẩn hóa DOI (bỏ prefix, chữ thường, giữ ký tự hợp lệ của suffix).
2. Nhóm trùng; bản tạp chí được giữ làm bản chính, preprint/hội nghị liên kết qua `dup_group`.
3. Áp Q-1…Q-9 (script phase 02), cổng §4; ghi `q1_rule_trace`.
4. Bổ sung abstract: OpenAlex `abstract_inverted_index` → Crossref `abstract` → Semantic Scholar (nếu gọi được) → trang publisher qua WebFetch. Ghi nguồn abstract.
5. Kiểm sai âm cổng §4 trên 50 bản ghi loại (seed 20261024).
6. Xuất dossier, chạy `search-literature.py --project <plan-dir> --input <dossier-input> --output <new>` rồi `check-literature.py`; ghi exit riêng.
7. Báo N T0 tạm theo nguồn và theo truy vấn.

## Kiểm tra

- `len(t0-candidates) + len(t0-excluded) = số bản ghi duy nhất sau khử trùng`.
- Không hai dòng T0 cùng DOI hoặc cùng OpenAlex ID.
- Kiểm tay 30 bản ghi T0 ngẫu nhiên: Q1-CS đúng theo CSV SJR, năm đúng, loại đúng.
- `check-literature.py` exit 0, hoặc phát hiện được ghi và sửa.
- Mẫu sai âm ≤ 2/50; nếu không, amendment regex (protocol đã đóng băng → amendment có ngày) và chạy lại bước 3.

## Rủi ro và hoàn tác

- T0 tạm < 1.000 là bình thường ở bước này (snowball ở phase 05 còn bổ sung); chỉ báo, chưa kích hoạt §10.
- ISSN OpenAlex sai cho một số tạp chí: fallback Crossref; ghi xung đột.
- Hoàn tác: các output là hàm tất định của input; xóa và chạy lại.
