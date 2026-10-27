---
title: Ultrareview và plan sửa trước khi chạy tập train
date: 2026-10-27
summary: "Ultrareview 5 nit đã đối chiếu; plan 6 phase cho đường B (harness Kaggle) và đường A (run_grid), có quyết định Q1–Q4."
---

# Ultrareview và plan sửa trước khi chạy tập train

## What happened
- Ultrareview chạy trên cloud bằng acc Pro, review 24 file / 2.244 dòng. Hai lần chạy đầu bị từ chối vì diff quá lớn, do diff ba chấm lấy merge-base là `main`.
  - Cách xử lý: dựng nhánh `review/ultrareview-base` (main + 16 file generated) và nhánh `review/ultrareview-head` (cây file giống hệt `feat/rclagent-harness-budget-guard`, cha là base).
- Ultrareview trả 5 finding, đều mức nit. Em đã đối chiếu với source và artifact v7/v8:
  - Ngân sách tính theo từng kết quả. Model thường gọi 1 log + 1 metric mỗi lượt, chưa từng gọi 2 `search_logs`. Nếu xảy ra, guard dừng sạch.
  - `harness-requirements.txt` thiếu transformers, tokenizers, huggingface-hub.
  - `ladder()` parse hai lần.
  - Code chép giữa hai script scan.
  - `KNOWN_SERVICES` chép tay.
- Review toàn repo do reviewer con làm, em kiểm lại 2 finding High:
  - `run_grid` không chạy được retrieval trên tập train (`run_grid.py:193-197,470-476`).
  - Một file evidence lạc làm hỏng cả lượt (`:418-432`).
- Không có bí mật nào trong file tracked. README gốc lỗi thời. Bộ test `nt114-rca` chưa chạy vì hook chặn `.venv`.

## Decision
- Plan: `plans/261027-1624-fix-before-train-split-run/`, 6 phase, `ak plan validate` OK.
- Q1: chia ngân sách đều cho các `search_logs` trong một lượt (⌊2.048/n⌋).
- Q2: kho retrieval leave-one-group-out trên tập train.
- Q3: loại ca tier B khỏi query khi chạy tập train.
- Q4: làm đường B trước, rồi xin duyệt riêng pilot Kaggle khoảng 5 trace.

## Next steps
- Phase 1 → 3 (harness), sau đó xin duyệt pilot GPU. Phase 4–5 (`nt114-rca`) làm sau hoặc song song.
- Working tree đang ở nhánh `review/ultrareview-head` do session kia switch sang; cây file giống hệt nhánh feat.

> Historical work record — not durable authority. Prefer docs/specs/ADRs for current decisions.
