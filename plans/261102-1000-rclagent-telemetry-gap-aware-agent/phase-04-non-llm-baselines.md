---
phase: 4
title: "Baseline không dùng LLM"
status: completed
priority: P2
effort: "8h"
dependencies: [2]
---

# Phase 4: Baseline không dùng LLM

Biên nhận: [báo cáo, mục 3](../reports/analysis-261102-rclagent-trace-coverage-and-non-llm-baselines.md) (2026-11-02).
- [Báo cáo](../reports/analysis-261102-rclagent-trace-coverage-and-non-llm-baselines.md), mục 3.
- RCAEval commit `dc9f4878…ac91`. Test 24 cái, thoát 0. Lệnh chạy đầy đủ thoát 0.
- SHA256 (CRLF thành LF): script `a336eead…2857`, test `4b06817e…9720`, `results.csv` `683189f5…a34d`.
- Bộ xếp hạng độ trễ nhìn cả cửa sổ đạt R@1 0,50 trên 240 truy vấn train; TraceRCA 0,083, MicroRank 0, BARO 0,104.

## Context
- RCAEval (https://github.com/phamquiluan/rcaeval) có sẵn TraceRCA, MicroRank và BARO. Theo tra tính mới, RCLAgent gốc cũng so với các phương pháp này.
- Đơn vị so sánh là truy vấn (error trace) của RCLAgent, không phải case của RCAEval. Cần một bộ chuyển đổi đưa đầu vào theo từng truy vấn: trace thô và metric trong cửa sổ.

## Requirements
- Cài RCAEval vào một env CPU riêng, ghi phiên bản và commit.
- Chạy TraceRCA, MicroRank và BARO trên các truy vấn train của phase 2. Chạy hai chế độ, đủ nguồn và bỏ metric, với BARO chỉ chạy được khi có metric.
- Thêm bộ xếp hạng chỉ theo độ trễ: xếp dịch vụ theo tỉ lệ độ trễ so với p50 train, ba biến thể `either`, `callee`, `caller`.
- Báo R@1 và MRR theo dịch vụ lỗi và theo nhóm phạm vi trace.

## Files
- Create: `K/run-non-llm-baselines.py`, `K/test-run-non-llm-baselines.py`.
- Create (gitignored): `K/runtime/non-llm-baselines/`.

## Steps
1. Cài RCAEval và chạy ví dụ của chính nó để chắc bản cài hoạt động.
2. Viết bộ chuyển đổi theo truy vấn và test.
3. Chạy và ghi kết quả.

## Checks
- Test thoát 0.
- Mỗi baseline có kết quả cho đủ 240 truy vấn, hoặc ghi rõ truy vấn nào lỗi và vì sao.

## Risk / Rollback
- RCAEval không chạy được trên Windows: chạy trong một kernel Kaggle chỉ dùng CPU (không tốn quota GPU).
- Rollback: xóa script và output.
