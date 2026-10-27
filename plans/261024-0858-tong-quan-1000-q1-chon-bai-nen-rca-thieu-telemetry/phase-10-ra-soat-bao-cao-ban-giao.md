---
phase: 10
title: "Review độc lập, báo cáo cuối và handoff"
status: ready-for-review
receipt: work/receipts/10-report-stats-01.json
owner_skills: [nckh-review, nckh-evidence, nckh-handoff]
---

# Giai đoạn 10: Rà soát, báo cáo, bàn giao

## Yêu cầu

- Một báo cáo tiếng Việt, mở bằng kết luận: bài nền đề xuất, lý do, giới hạn, điều kiện đảo.
- Báo cáo tách bốn danh sách: existing-before-attempt, created-this-attempt, verified-this-attempt, unverified.
- Gate matrix theo từng tiêu chí chấp nhận của [plan §4](plan.md), trạng thái pass/fail/pending kèm receipt.
- Handoff resume được cho phiên sau hoặc cho kế hoạch MVP mới.

## Tệp

- Đọc: mọi output phase 01–09, `work/state.json`, receipt.
- Tạo: `plans/reports/research-<ngày>-tong-quan-1000-q1-chon-bai-nen.md`, `research/final-review.md`, `work/gate-matrix.csv`, `work/handoff.md`, `work/receipts/10-*.json`.

## Các bước

1. Chạy `check-receipt.py verify` cho các receipt chính; chạy lại script sinh T1/T2 để xác nhận tất định.
2. Spawn `nckh-reviewer` ngữ cảnh mới review báo cáo nháp: số liệu khớp file, nhãn mức đọc, Q1 wording, novelty wording, xung đột với quyết định chủ dự án.
3. nckh-evidence triage các nhận định trong báo cáo (pre-publication claim triage).
4. Viết báo cáo: phễu PRISMA, giao thức + amendment, bảng 10 ứng viên, ma trận + độ nhạy, đề xuất, thiết kế sau chọn (tóm tắt + link), giới hạn, câu hỏi mở.
5. Viết `handoff.md` bằng nckh-handoff: trạng thái, artifact + hash, gate mở, lệnh tiếp.

## Kiểm tra

- Mỗi số trong báo cáo truy được tới file + dòng hoặc receipt.
- `gate-matrix.csv` không có `pass` thiếu receipt; chấp nhận bài nền là `pending-personal-review`.
- Chạy `check-plan.py` trên thư mục kế hoạch sau khi cập nhật trạng thái; exit 0.

## Rủi ro và hoàn tác

- Review phát hiện số không khớp: sửa nguồn sinh, sinh lại, không sửa tay số trong báo cáo.
- Hoàn tác: báo cáo có version; trạng thái phase chỉ đổi khi có receipt trên cùng dòng.
