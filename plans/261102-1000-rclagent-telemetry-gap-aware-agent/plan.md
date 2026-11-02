---
title: "Hướng A: agent RCA dựa trên trace, nhận biết và bù chỗ thiếu telemetry"
description: "Phát triển RCLAgent thành một phương pháp mới cho bài báo: agent nhận ra nguồn telemetry đang thiếu, bù metric bằng KPI độ trễ dựng từ trace, và mở rộng bằng chứng ra ngoài trace được giao khi trace đó không phủ dịch vụ lỗi; đánh giá có baseline và ablation, dev trên train, kết luận trên test split khi sếp mở niêm phong."
status: in-progress
priority: P1
effort: 60h
branch: feat/rclagent-telemetry-gap-aware-agent
tags: [rclagent, paper, method, kaggle, research]
blockedBy: []
blocks: []
created: 2026-11-02
---

# Hướng A: agent RCA nhận biết và bù chỗ thiếu telemetry

## Overview

Sếp chốt hướng A ngày 2026-11-02. Mục tiêu là một đóng góp mới cho bài báo phát triển từ RCLAgent (arXiv 2605.14866), không phải kiểm chứng lại bài gốc.

Cơ sở ([tra tính mới](../reports/research-261102-rclagent-direction-a-novelty.md)):
- **Trần do trace được giao.** 59/240 truy vấn train của RCLAgent trên RE2-OB (24,6%) có trace không chứa span nào của dịch vụ lỗi. Vì vậy agent chỉ đi trong trace có trần R@1 khoảng 75%. RCLAgent chỉ nêu giả định "đồ thị trace phủ đường lan truyền" như một giới hạn, ở Sec. VI.
- **Mất bằng chứng khi bỏ metric.** Khi bỏ metric, R@1 giảm 0,208 trên 8 case. Tín hiệu độ trễ có trong trace, nhưng mất ở bước self-state ([kết quả RQ (c) bước 1](../reports/analysis-261102-rclagent-metric-drop-substitutes-results.md)).
- **Tình trạng tài liệu.**
  - Đã có bài gỡ modality trên agent LLM (2601.22208) và bài đặt tên hiện tượng "im lặng bị đọc thành khỏe" (2608.21310, MIS1).
  - Chưa thấy bài nào bù nguồn ngay trong agent LLM, hay mở rộng bằng chứng ra ngoài trace được giao.
  - Mọi kết luận trên đều mới đọc qua tóm tắt của công cụ.

Ba thành phần của phương pháp (tên tạm):
- **M1 Nhận biết thiếu nguồn:** agent biết nguồn nào vắng ở dịch vụ nào, và không coi "không có dữ liệu" là "khỏe".
- **M2 KPI độ trễ dựng từ trace:** khi metric vắng, một tool trả bảng độ trễ so với mốc train, tính cho cả bên gọi lẫn bên được gọi.
- **M3 Mở rộng tập trace:** khi trace được giao không đủ bằng chứng, agent lấy tóm tắt theo dịch vụ từ các trace khác trong cùng cửa sổ thời gian, có trần ngân sách.

`K/` là `F:/Nam/UIT/NT114 - NCKH/plans/261026-1713-rclagent-tai-hien-toi-thieu/kaggle/`.

## Kết quả mong đợi (outcome)

1. Ma trận công trình liên quan đã đọc nguyên văn, kèm câu tuyên bố tính mới được phép viết.
2. Script có test đo phạm vi trace (span GT có hay không trong mỗi truy vấn) trên train và val.
3. Đặc tả phương pháp và prereg có hash: điều kiện, giả thuyết, chỉ số, baseline, ngân sách GPU. Sếp duyệt trước khi chạy.
4. Kết quả các baseline không dùng LLM trên cùng truy vấn: TraceRCA, MicroRank, BARO và bộ xếp hạng chỉ theo độ trễ.
5. M1 đến M3 cài trong wrapper của harness, có cờ bật tắt; khi tắt, request giống từng byte với S1 v3.
6. Một lượt dev trên Kaggle với tập train phân tầng, có ablation, và báo cáo go/no-go cho đánh giá trên test split.

## Phi mục tiêu (non-goals)

- Không sửa `upstream/`. Mọi thay đổi nằm trong wrapper (`adapt_payload`, `get_tool` trong `K/smoke-worker.py`).
- Không đọc kết quả hay cấu trúc test split RE2-OB nếu sếp chưa mở niêm phong theo D12. Phase 7 chỉ đề xuất.
- Không viết bản thảo bài báo trong plan này.
- Không chạy RE2-TT trong plan này. Phase 7 ước ngân sách cho nó.

## Tiêu chí chấp nhận

- Mỗi câu tuyên bố tính mới trong ma trận có nguồn đọc nguyên văn kèm vị trí trong bài.
- Prereg có hash trước khi đẩy gói Kaggle, và hash còn khớp lúc phân tích.
- Khi M1 đến M3 tắt, request khớp từng byte với S1 v3 (có test).
- Kết quả dev báo R@1 và MRR theo từng dịch vụ lỗi, tách riêng nhóm truy vấn có và không có span GT, và có cả baseline không dùng LLM.

## Các giai đoạn

| Phase | Tên | Trạng thái | Phụ thuộc | Ước lượng |
|---|---|---|---|---|
| 1 | [Đọc nguyên văn công trình liên quan](./phase-01-full-text-related-work.md) | completed, biên nhận [nguyên văn](../reports/research-261102-rclagent-direction-a-related-work-full-text.md) (chưa ai làm M3 cho agent LLM; phải thêm baseline agent tự do truy vấn) | không | 6h |
| 2 | [Script đo phạm vi trace](./phase-02-trace-coverage-script.md) | completed, biên nhận [báo cáo](../reports/analysis-261102-rclagent-trace-coverage-and-non-llm-baselines.md) (train 59/240, val 25/105 truy vấn không có span GT) | không | 4h |
| 3 | [Đặc tả phương pháp và prereg](./phase-03-method-spec-and-prereg.md) | completed, [prereg bản 3](../reports/prereg-261102-rclagent-telemetry-gap-method.md) sếp duyệt 2026-11-02; hash đóng băng trong `K/telemetry-gap-prereg.json` | 1, 2 | 6h |
| 4 | [Baseline không dùng LLM](./phase-04-non-llm-baselines.md) | completed, biên nhận [báo cáo](../reports/analysis-261102-rclagent-trace-coverage-and-non-llm-baselines.md) (xếp hạng độ trễ cả cửa sổ R@1 0,50; TraceRCA 0,083) | 2 | 8h |
| 5 | [Cài M1, M2, M3 trong harness](./phase-05-implement-m1-m3.md) | completed, `K/telemetry-gap.py` và cờ trong `K/smoke-worker.py`; test `K/test-telemetry-gap.py` | 3 | 14h |
| 6 | [Lượt dev trên Kaggle](./phase-06-kaggle-dev-run.md) | in-progress, Kaggle T4×2 và Modal T4 ([deviation 7](deviation-log.md)) | 4, 5 | 6h công, GPU theo prereg |
| 7 | [Phân tích dev và go/no-go](./phase-07-dev-analysis-and-go-no-go.md) | planned | 6 | 6h |

Phase 1, 2 và 4 chạy song song được (4 chỉ cần danh sách truy vấn của phase 2).

## Ngân sách GPU (ước lượng, chưa đo)

- S1 v3 mất khoảng 14 phút mỗi run trên T4. Chạy cả 240 truy vấn train cho một điều kiện sẽ tốn khoảng 56 giờ, vượt quota 30 giờ mỗi tuần.
- Vì vậy phase 3 chọn một tập dev phân tầng. Cỡ khoảng 24 truy vấn, gồm cả truy vấn có và không có span GT, và đủ 5 dịch vụ lỗi.
- Phase 3 chốt lưới điều kiện. Trần dự kiến là 6 điều kiện × 24 truy vấn × 1 seed, tức khoảng 34 giờ, chia ra 2 tuần.

## Rủi ro chính

- **Tính mới:** các câu "chưa thấy" ở trên mới dựa trên tóm tắt. Nếu phase 1 tìm thấy bài trùng M3, plan quay lại phase 3 để đổi trọng tâm.
- **Đặc hiệu:** M2 và M3 dựa trên độ trễ, nên có thể đẩy `cartservice` lên thay cho dịch vụ lỗi (5/8 case ở RQ (c) bước 1). Prereg phải có chỉ số theo dõi riêng cho rủi ro này.
- **Chi phí ngữ cảnh:** M3 thêm dữ liệu vào ngữ cảnh 16384. Phase 5 phải đặt trần kích thước và test.
- **Baseline mạnh:** theo "Free to Look" (2610.35767), một harness ReAct đơn giản có thể thắng agent thiết kế tay. Phase 3 quyết có thêm baseline này không, tùy ngân sách.

## Câu hỏi còn mở

1. Có cho phép đếm cấu trúc span của test split (không đọc kết quả) để biết trần 75% có giữ trên test không? Mặc định: không, chờ sếp quyết ở phase 7.
