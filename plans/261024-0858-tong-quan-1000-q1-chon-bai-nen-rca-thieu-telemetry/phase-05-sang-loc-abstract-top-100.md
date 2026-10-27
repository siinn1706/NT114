---
phase: 5
title: "Sàng lọc abstract, snowball, mẫu kép, xếp hạng → T0 cuối và T1 (100)"
status: done
receipt: work/receipts/05-rank-final-01.json
owner_skills: [nckh-literature, nckh-method]
---

# Giai đoạn 05: Sàng lọc T1

## Yêu cầu

- Mỗi bản ghi T0 có đúng một quyết định I/E/needs-review + mã lý do + điểm R1–R6 từ **metadata + abstract**, ghi `read_level: abstract` hoặc `title-only`.
- Snowball vòng 1 từ T1 tạm; bản ghi mới qua cổng phase 04 và cùng rubric; xếp lại T1 một lần rồi chốt.
- Kích hoạt [protocol §10](protocol.md) nếu T0 cuối < 1.000.
- Mẫu kép đạt κ ≥ 0,7.

## Tệp

- Đọc: `work/records/t0-candidates.csv`, [protocol §6](protocol.md).
- Tạo: `work/screen/batch-NNN.csv` (50 bản ghi/batch, bất biến), `work/screen/screen-all.csv` (sinh lại từ batch), `work/raw/snowball/`, `work/records/snowball-r1.csv`, `work/screen/double-screen.csv`, `work/screen/kappa.json`, `work/records/t0-final.csv`, `work/records/t1-top100.csv`, `work/records/context-surveys.csv`, `work/prisma-counts.json`, `work/receipts/05-*.json`.

## Các bước

1. Screening theo batch 50 bản ghi, thứ tự `record_id`; mỗi dòng có trích ngắn từ abstract làm căn cứ cho R1–R3. Sau mỗi batch: output + receipt + state.
2. Xếp T1 tạm theo §6.
3. Snowball vòng 1 (backward + forward) từ T1 tạm; khử trùng với T0; cổng Q1/chủ đề; screening các bản ghi mới cùng rubric.
4. Ghi T0 cuối. Nếu < 1.000: chạy §10 (snowball vòng 2, truy vấn đồng nghĩa có amendment, tiêu chí bão hòa); vẫn thiếu → ghi `waiting-human` trong state, tiếp tục nếu N ≥ 300, dừng nếu N < 300.
5. Mẫu kép: spawn `nckh-reviewer` ngữ cảnh mới với mẫu phân tầng 10% + needs-review + hạng 90–110, **không** gửi điểm người chấm 1; tính κ; giải bất đồng.
6. Xếp lại T1 một lần theo §6 (tie-break tất định) → `t1-top100.csv`; ghi `fill-r1` nếu có.
7. Ghi PRISMA-style counts: identified, duplicate, gate-excluded theo mã, screened, included, top-100, late-records.

## Kiểm tra

- Mỗi `record_id` T0 cuối xuất hiện đúng một lần trong `screen-all.csv`.
- `kappa.json` có κ, n, ma trận nhầm; κ ≥ 0,7 hoặc amendment + chấm lại.
- `t1-top100.csv` đúng 100 dòng (hoặc báo số thực và lý do), sinh lại tất định từ `screen-all.csv` bằng script (chạy hai lần, hash giống nhau).
- Tổng PRISMA khớp số dòng các file.

## Rủi ro và hoàn tác

- Người chấm 1 và reviewer cùng họ mô hình: ghi là giới hạn, không gọi là đánh giá con người; chủ dự án có thể chấm tay mẫu 30 bài làm cổng tùy chọn.
- Drift rubric qua nhiều phiên: mỗi phiên chấm lại 5 bản ghi “neo” cố định trước batch mới; lệch → dừng, rà lại.
- Hoàn tác: batch bất biến; chấm lại = batch mới với attempt mới, `screen-all.csv` lấy attempt mới nhất đã commit.
