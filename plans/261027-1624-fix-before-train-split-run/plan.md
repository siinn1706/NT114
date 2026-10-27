---
title: "Sửa các lỗi chặn trước khi chạy tập train"
description: "Sửa các finding đã xác minh từ ultrareview và review toàn repo để chạy được tập train trên harness Kaggle RCLAgent (đường B) và run_grid (đường A), giữ nguyên mọi thiết lập đã đóng băng."
status: completed
priority: P1
effort: 5d
branch: feat/rclagent-harness-budget-guard
tags: [bugfix, backend, critical]
blockedBy: []
blocks: []
created: 2026-10-27
---

# Sửa các lỗi chặn trước khi chạy tập train

**Kết quả cần đạt:** hai đường chạy tập train đều chạy được, mỗi bước có test hồi quy chứng minh, không đổi thiết lập đã đóng băng.

- **Đường B — harness Kaggle RCLAgent:** chạy được nhiều trace, có thể chạy tiếp sau khi bị ngắt, và ghi nhận trace thất bại mà không dừng cả lượt.
- **Đường A — `run_grid` của `nt114-rca`:** chạy được với `split_role: train`. Không để dữ liệu hay split bị trôi mà không ai biết.

Đã thực hiện ngày 2026-10-27; kết quả và các kiểm nằm trong [report](../reports/fix-261027-1745-before-train-split-run.md). Pilot GPU chưa chạy, chờ duyệt riêng.

## Nguồn findings

- Ultrareview (cloud, 24 file, nhánh `review/ultrareview-head` so với `review/ultrareview-base`): 5 finding mức nit. Em đã đối chiếu lại cả 5 với source và artifact v7/v8.
- [Review toàn repo](../reports/review-261027-1525-full-repo-ultrareview-prep.md) và [review sẵn sàng của tập train](../reports/review-261027-1400-rclagent-train-batch-readiness.md). Hai finding High của `run_grid` em đã đọc lại code. Các finding còn lại do reviewer con báo; mỗi phase phải tái hiện bằng một test đỏ trước khi sửa.

**Đối chiếu finding 1 của ultrareview (ngân sách tính theo từng kết quả, không theo cả request):**
- Trên v7 và v8, model thường gọi 2 tool mỗi lượt, một `search_logs` và một metric (v8: 36 lượt có 2 call, 4 lượt có 1 call, 66 lượt không gọi).
- Chưa lượt nào có 2 `search_logs`. Phép tính 4×(103+512+B+10) đã gồm phần metric khoảng 10 token.
- Vậy lỗ hổng này có thật nhưng chưa từng xảy ra. Nếu xảy ra, guard dừng trước khi vượt context, không cắt ngữ cảnh.

## Thiết lập đóng băng (không phase nào được đổi)

Upstream `RCLAgent-V2@3052e7a`, prompt, model và revision, sampling, context 16.384, output 512/1.024, retry 3, 4 vòng tool, trần 160 requests và 1.800 giây, recursion-of-thought, một backbone, nhãn chỉ dùng khi chấm. Ngân sách B = 2.048 cho `search_logs` là sai lệch đã duyệt. Mọi thay đổi cách áp ngân sách phải được sếp duyệt (câu hỏi Q1).

## Phases

| # | Phase | Đường | Phụ thuộc | Ước lượng | Trạng thái |
|---|---|---|---|---|---|
| 1 | [Ngân sách, môi trường và nguồn service của harness](phase-01-harness-budget-and-env.md) | B | — | 0,5d | completed |
| 2 | [Gom phần chung của hai script scan](phase-02-shared-scan-module.md) | B | — | 0,5d | completed |
| 3 | [Batch runner nhiều trace](phase-03-multi-trace-batch-runner.md) | B | 1 | 2d | completed |
| 4 | [Gỡ chặn `run_grid` trên tập train](phase-04-run-grid-train-blockers.md) | A | — | 1d | completed |
| 5 | [Toàn vẹn dữ liệu, adapter và parse câu trả lời](phase-05-data-and-parser-integrity.md) | A | — | 1d | completed |
| 6 | [Tài liệu và kiểm toàn bộ](phase-06-docs-and-full-verification.md) | A+B | 1–5 | 0,5d | completed |

Phase 1, 2, 4, 5 sửa các nhóm file tách biệt nên có thể làm song song. Phase 3 cần phase 1 xong trước, vì cả hai cùng sửa `smoke-worker.py`.

## Tiêu chí nghiệm thu

1. Mỗi finding đã xác minh có một test đỏ trước khi sửa và xanh sau khi sửa, hoặc có lý do ghi rõ vì sao không áp dụng.
2. Các test hiện có vẫn pass: harness 20/20, ngân sách 9/9, T4 4/4, `nt114-rca` `pytest -m "not realdata"`, `verify-splits` 16/16.
3. Kiểm CPU equivalence pass cho mọi ca thuộc lượt pilot; `verify-package` pass cho từng gói.
4. Output của script scan sau khi tách phần chung trùng byte với file CSV/JSON đã commit.
5. Không đổi thiết lập đóng băng nào. Mọi thay đổi về cách áp ngân sách đều có quyết định của sếp và được ghi là sai lệch.
6. Chạy GPU (pilot Kaggle) chỉ khi sếp duyệt riêng; plan này không tự kích hoạt.

## Rủi ro chính

- Batch runner là thay đổi lớn nhất, chạm runtime, worker, đóng gói và validator. Phải giữ nguyên hành vi một trace (chạy lại smoke `checkoutservice_cpu_2` trên CPU và so artifact).
- Kiểm CPU equivalence cho mỗi trace phải quét 9,4 triệu dòng metric. Cần gom theo ca (5 trace mỗi ca) để không tốn hàng giờ.
- Bộ test `nt114-rca` cần `.venv`, mà hook hiện chặn mọi lệnh Bash có chuỗi `.venv`. Sếp chạy giúp, hoặc nới `.ckignore`.

## Quyết định của sếp (2026-10-27)

- **Q1 Ngân sách:** chia đều ngân sách cho các `search_logs` trong cùng một lượt, mỗi call nhận ⌊2.048 / n⌋. Khi n = 1 thì không đổi so với hiện tại. Ghi đây là phần mở rộng của sai lệch đã khai báo.
- **Q2 Retrieval trên tập train:** kho leave-one-group-out, tức mỗi query dùng kho train trừ chính nhóm của nó. Test và val giữ nguyên hành vi cũ.
- **Q3 Tier B:** loại khỏi query khi chạy tập train, có đếm và ghi log số ca bị loại.
- **Q4 Thứ tự:** làm đường B trước (phase 1 → 3), sau đó xin duyệt riêng để chạy pilot Kaggle khoảng 5 trace train. Phase 4–5 làm sau hoặc song song.

## Còn mở

- Chuỗi thời gian RCA100 thật có kèm offset không. Kiểm ở bước đầu của phase 5, chỉ đọc file.
- Có tái tạo release dữ liệu canonical không, nếu A6/A7 làm đổi output normalize. Đây là quyết định riêng của sếp, đưa ra sau phase 5.
