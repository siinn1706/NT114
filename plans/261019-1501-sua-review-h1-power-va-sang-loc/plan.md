---
title: "Sửa bốn phát hiện của review 261019-1441: power H1, tách endpoint, verdict H2, sàng lọc/PRISMA"
status: in-progress
priority: P1
effort: 1 ngày-người, 0 GPU, 0 lần chạy model thật
branch: main
tags: [research, review-repair, power-analysis, selective-prediction, prisma]
blockedBy: []
blocks: ["DEV pilot H1 (cần máy GPU)", "protocol v2 §9.5 (đề xuất)"]
created: 2026-10-19
---

# Sửa review 261019-1441 cho tổng quan Elicit và hướng H1

Đầu vào: [review](../reports/review-261019-1441-tong-quan-elicit-va-huong-h1.md),
[báo cáo đã sửa](../reports/research-261019-tong-quan-elicit-chon-dong-gop-nt114.md),
[kế hoạch gốc](../261019-1045-chon-dong-gop-khoa-hoc-qua-tong-quan-elicit/plan.md).

## Phạm vi và ràng buộc

- Chỉ phân tích CPU, dữ liệu tổng hợp và nguồn công khai.
- Không sửa source, dữ liệu, split, prompt v1 hay protocol v2. Mọi thay đổi protocol chỉ là đề xuất.
- Không dùng nhãn test. Không chạy model. Không commit hay push.
- Perplexity Pro (tài khoản của chủ dự án) chỉ nhận truy vấn nghiên cứu công khai.

## Kết quả theo từng phát hiện

| # | Phát hiện | Trạng thái | Bằng chứng |
|---|---|---|---|
| 1 | Cổng AUROC 0.75 không có căn cứ | **Đã sửa.** Thay bằng mô phỏng power với estimator thật, cụm injection, confidence đồng hạng, fit ngưỡng DEV và Holm | [h1_power.py](work/h1_power.py), [h1-mde.csv](work/out/h1-mde.csv), [ghi chú](research/h1-endpoint-va-power.md) |
| 2 | Trộn coverage cố định với ngưỡng DEV | **Đã sửa.** E1 và E2 được định nghĩa riêng; E2 báo coverage thực | [ghi chú §1](research/h1-endpoint-va-power.md#1-hai-phép-đánh-giá-phải-tách-riêng) |
| 3 | Verdict H2 vượt chuẩn | **Đã sửa.** Hạ thành "dấu hiệu chồng lấn mạnh, chưa xác nhận". SADE đã đọc toàn văn; ba bài còn lại bị kiểm tra bot chặn | [update_findings.py](work/update_findings.py) |
| 4 | Sàng lọc, PRISMA, AC quá tay | **Phần lớn đã sửa.** Có sổ sàng lọc, luồng bản ghi → công trình, kiểm đủ 10 % bài bị loại, giải thích 310 bản ghi loại. **Còn mở:** sàng lọc lại có trễ (chỉ hợp lệ từ 2026-10-20 13:42) và relevance 0/1/2 cho 279 bài ngoài SR1 | [screening_repair.py](work/screening_repair.py), [prisma-flow.json](work/out/prisma-flow.json) |

## Tiêu chí chấp nhận

- [x] Power tính bằng estimator `rca.metrics`/`rca.selective`, có cụm và đồng hạng; test tập trung pass (8/8).
- [x] Endpoint chính và quy tắc DEV pilot được đặc tả, có code (`pilot_decision`) và test.
- [x] Báo cáo bỏ cổng AUROC, tách E1/E2, hạ verdict H2, sửa PRISMA; `verify-report.py` pass.
- [x] Vòng thách thức H1 bằng Perplexity Deep Research; mọi số dùng đều đã đối chiếu bài gốc ([nhật ký](research/perplexity-challenge-log.md)).
- [ ] Sàng lọc lại có trễ 30 bài, sau 2026-10-20 13:42 (giờ VN), bằng [delayed-rescreen-sample.csv](work/out/delayed-rescreen-sample.csv).
- [ ] DEV pilot: **không chạy được trên máy này** (GPU AMD Radeon RX 5600 XT, không có NVIDIA/CUDA, chưa qua Linux gate và GPU probe). Các bước còn lại nằm ở [ghi chú §5](research/h1-endpoint-va-power.md#5-quy-tắc-quyết-định-của-dev-pilot-đề-xuất-cài-trong-pilot_decision) và llms.txt.

## Tái lập

```text
# từ plans/261019-1501-sua-review-h1-power-va-sang-loc/work, dùng venv phân tích nt114-rca/nt114-rca/.venv
python -m pytest -q -p no:cacheprovider test_h1_power.py           # 8 passed
python -I h1_power.py out --reps 1000 --boot 1999                    # 682 s CPU
python -I screening_repair.py out                                   # sổ sàng lọc, PRISMA, mẫu bổ sung/trễ
python -I update_findings.py                                        # idempotent
python -I ../../261019-1045-chon-dong-gop-khoa-hoc-qua-tong-quan-elicit/work/verify-report.py \
  ../../reports/research-261019-tong-quan-elicit-chon-dong-gop-nt114.md \
  ../../261019-1045-chon-dong-gop-khoa-hoc-qua-tong-quan-elicit/work/findings.csv --write-appendix
```

`screening_repair.py` không ghi đè `screening-check-supplement.csv` hay `delayed-rescreen-sample.csv`
khi chúng đã tồn tại, vì hai file này chứa quyết định tay.
