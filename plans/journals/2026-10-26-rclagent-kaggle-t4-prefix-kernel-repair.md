---
title: RCLAgent Kaggle T4 prefix kernel repair
date: 2026-10-26
summary: GPU kernel fixed and tool gate passed; trace stopped on out-of-package cartservice query
---

# RCLAgent Kaggle T4 prefix kernel repair

Kernel vLLM 0.10.2 non-ALiBi prefix prefill dùng BLOCK_M=128 trên T4, cần 96 KiB shared memory trong giới hạn 64 KiB. Patch có kiểm hash đổi tile thành 64 riêng Turing; giữ source gốc/diff và RCLAgent bất biến.

Kaggle native: kernel gốc tái hiện lỗi, bản vá qua 15 dense-reference cases. Đã sửa regression helper tạo bytecode ngoài manifest, thêm kiểm red/green. 4 kiểm patch/cache và 14 kiểm harness qua.

Version 5 qua D (3 requests), E dừng sau 2 requests vì Qwen hỏi cartservice ngoài trace/domain đóng gói. Chưa có RCA cuối/chấm; không mở rộng dữ liệu, sửa prompt/tool hoặc retry theo kết quả. Mọi process sở hữu đã dừng. Lỗi GPU đã sửa; smoke end-to-end vẫn dừng ở E.

Artifact và bằng chứng: plans/261026-1713-rclagent-tai-hien-toi-thieu/kaggle/repair-report.md, kaggle-repair-v5-summary.json, rclagent-kaggle-repair-v5-results.zip. Không chạy LLM trên Windows, không commit/push. AgentWiki publish skipped.

> Historical work record — not durable authority. Prefer docs/specs/ADRs for current decisions.
