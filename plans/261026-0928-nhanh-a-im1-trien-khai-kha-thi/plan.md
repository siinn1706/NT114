---
title: "NT114: kế hoạch triển khai nhánh (a) adaptation RCLAgent một lời gọi + IM1, có kiểm rò rỉ, confidence, feasibility và cổng dừng"
description: "Kế hoạch triển khai và khả thi cho adaptation RCLAgent không recursion-of-thought (một lời gọi tổng hợp) và cải tiến IM1 (khung phụ thuộc dịch vụ lịch sử cho no_trace). Lập kế hoạch thôi; mọi lần chạy model/GPU cần chủ dự án duyệt riêng."
status: paused
priority: P1
effort: "ước tính 6-10 phiên làm việc cho phase 01-07; 0 GPU; 0 lần chạy model trong kế hoạch này"
branch: main
mode: "nckh-cook --auto, phase 03–08 cấp quyền 2026-10-26 (xem §6)"
plan_location: "plans/ (quy ước repo {date}-{issue}-{slug})"
tags: [implementation-plan, single-llm, rclagent-adaptation, im1, no-trace, leakage, feasibility]
blockedBy: []
blocks: ["M5 đóng băng", "chạy DEV pilot và feasibility GPU"]
created: 2026-10-26
---

# Nhánh (a) + IM1: kế hoạch triển khai và khả thi

## 1. Kết quả mong muốn

Một bộ thay đổi mã nguồn có kiểm thử trong `nt114-rca/nt114-rca` (chỉ sau khi chủ dự án cấp quyền theo §6) tạo ra:

- **R-a**: adaptation RCLAgent **không có recursion-of-thought**. Phân rã theo đồ thị trace, chọn bằng chứng và chạy tool bằng code tất định; LLM chỉ tổng hợp và xếp hạng trong **một lời gọi** cuối. Không gọi là tái hiện đầy đủ RCLAgent.
- **Đường xử lý theo telemetry sẵn có**: có trace, không trace (tool metric/log tất định, bằng chứng phẳng theo ứng viên), không khung. Quy tắc chọn đường chỉ dựa trên telemetry, đóng băng trước đánh giá.
- **IM1**: khung phụ thuộc dịch vụ dựng từ trace vai train (cửa sổ trước anchor), theo hệ và split, đóng băng trước val/test; arm có khung, đối chứng không khung, khung xáo cạnh, arm H1 hiện có.
- **Gói khả thi** (không chạy): cấu hình máy thực đo, model dự kiến, lượng tử hóa, trần bộ nhớ/thời gian, cổng dừng, và một yêu cầu cấp quyền chạy để chủ dự án duyệt.

Đây là kế hoạch; nó không cấp quyền sửa source hay chạy model. Thiết kế nguồn: [mvp-outline.md](../261024-0858-tong-quan-1000-q1-chon-bai-nen-rca-thieu-telemetry/design/mvp-outline.md), [test-matrix.md](../261024-0858-tong-quan-1000-q1-chon-bai-nen-rca-thieu-telemetry/design/test-matrix.md), [improvement-hypotheses.md](../261024-0858-tong-quan-1000-q1-chon-bai-nen-rca-thieu-telemetry/design/improvement-hypotheses.md), [reproduction-protocol.md](../261024-0858-tong-quan-1000-q1-chon-bai-nen-rca-thieu-telemetry/design/reproduction-protocol.md) (bản 0.2). Quyết định: [decisions.md](../261018-2300-single-llm-simplification-and-evaluation-hardening/decisions.md), các dòng 2026-10-26.

## 2. Phạm vi, ràng buộc, ngoài phạm vi

**Giữ nguyên (quyết định chủ dự án 2026-10-26):**
- Một model, một lời gọi mỗi câu trả lời (protocol v2 §1). Không multi-agent recursion, judge, escalation (D2).
- H1 không thu hẹp: pool `single_modality` (`no_metric`, `no_log`, `no_trace`, các hệ của nó); ca thiếu trace ở lại mẫu số (D3). 69/108 là độ phủ của thiết kế dựa trên trace, không phải số ca đúng.
- Confidence theo registry hiện hành (`src/rca/confidence.py`: mọi điểm đến từ chính lời gọi của ô; `token_prob` chưa xác thực nên chỉ thăm dò). Không lời gọi LLM thứ hai; verbalized confidence và logprob không mặc nhiên coi là hợp lệ (D3).
- `retrieval = none` giữ nghĩa cũ; arm IM1 có mã riêng và phụ lục data contract có ngày (D11).
- Niêm phong chặt: không mở kết quả test RE2-OB trước M5, kể cả tổng gộp 90 (D12).
- H1 (`gain_exact@0.7` so với C2, SESOI 0.05) là ứng viên confirmatory chính; họ kiểm định chưa đóng băng; IM1 là thăm dò (D13).
- Không API trả phí, không gửi telemetry/evidence ra ngoài (D6). Không GPU/model/cloud/benchmark dài khi chưa duyệt (D7). Không ngoại lệ nhiều lời gọi (D8).

**Ngoài phạm vi:** chạy LLM thật (kể cả DEV pilot), GPU, sửa protocol v2, sửa prompt `v1`, sửa splits/bundle, sửa `evidence.py` (`BUILDER_VERSION = 3`), IM2–IM4, DiagFusion, chạy code gốc RCLAgent có LLM, commit/push. Phân tích tĩnh và kiểm CPU không LLM của code gốc là **kế hoạch riêng** (D8), không thuộc kế hoạch này.

## 3. Bằng chứng nền đã đọc trong lượt lập kế hoạch (2026-10-26)

| Dữ kiện | Nguồn | Hệ quả |
|---|---|---|
| Máy đang chạy phiên: Intel Core i5-14400F (10 nhân, 16 luồng), RAM 31,8 GB, GPU AMD Radeon RX 5600 XT, không có `nvidia-smi` | lệnh CIM/WMI trong phiên này (PowerShell, exit 0) | Máy này không chạy được cấu hình vLLM/CUDA hiện có. WMI báo AdapterRAM 4 GB (trường 32 bit); dung lượng thật chưa đo |
| Máy GPU dự kiến: RTX 4080 Laptop 12 GB, "owner-reported, not yet probed" | `nt114-rca/nt114-rca/configs/hardware/rtx4080-laptop-12gb.yaml` dòng 1 | Feasibility phải probe máy thật bằng `scripts/gpu_probe.py`; mọi số VRAM hiện là ước lượng |
| Model ứng viên đã ghim: Qwen3.5-4B, Qwen3-4B-Instruct-2507, Phi-4-mini, Gemma-4-E4B (bf16/fp8), Qwen3.5-9B (fp8/nf4), Qwen3-8B (fp8/awq4) | cùng file, khối `serve.precisions` | Dùng lại danh sách; không thêm model mới khi chưa có lý do |
| Feasibility hiện có: 12 sự cố DEV (val), `conditions: [full, no_trace]`, `n_samples: 10`, "NOT RUN YET" | `configs/exp/gpu-feasibility.yaml` | Phase 07 mở rộng cho R-a và IM1, không chạy |
| Confidence registry: điểm từ chính lời gọi của ô; `token_prob` chưa xác thực | `src/rca/confidence.py` dòng 1-9 | Phase 06 dùng lại, không thêm nguồn |
| Bằng chứng phản chứng bên thứ ba: RCLAgent RE2OB Top-1 0,18 (PRISM, arXiv:2601.21359 v1, Table 3); RCLAgent V2 53,4% trên RCABench (arXiv:2608.21310 v2) | `../261024-0858-tong-quan-1000-q1-chon-bai-nen-rca-thieu-telemetry/work/targeted-search-261026-dedup.csv`; amendment 2026-10-26 trong `work/amendments.md` | Không kế thừa số của bài; cổng dừng DEV ở phase 07 so với B1m/L0 |

## 4. Tiêu chí chấp nhận

1. Phụ lục data contract cho IM1 và bảng mã arm tồn tại, có ngày, được chủ dự án duyệt **trước** mọi sửa source của phase 03–06.
2. Kiểm lịch sử tiếp xúc test RE2-OB (D12) và kiểm lại membership của pool H1 (69/108 và 39 RE2-SS) xong, ghi kết quả thật, trước khi cố định mẫu số.
3. Mọi module viết thêm có test: tất định (hash đầu ra ổn định qua hai lần chạy), hoán vị nhãn, canary, quét import; quy tắc chọn đường không đọc nhãn; khung IM1 không đọc nhãn, fault type hay telemetry val/test; khung xáo cạnh khác khung thật.
4. Pipeline R-a và IM1 chạy hết bằng mock LLM trên dữ liệu tổng hợp, đúng một lời gọi mỗi câu trả lời (đếm trong sổ chi phí); ba loại kết quả không áp dụng / lỗi thực thi / dự đoán sai được tách.
5. Toàn bộ test hiện có của `nt114-rca` vẫn pass (không suy yếu test).
6. Gói khả thi có cấu hình máy đo thực, model, lượng tử hóa, trần bộ nhớ/thời gian, cổng dừng và yêu cầu cấp quyền chạy; không có lần chạy model nào.
7. Không có kết luận nào gọi R-a là tái hiện RCLAgent, gọi IM1 là cải tiến đã chứng minh hay mới, hay coi CI chứa 0 là bác bỏ.
8. Trạng thái cuối tối đa `ready-for-review`; chạy model, M5 và họ confirmatory thuộc chủ dự án.

## 5. Các giai đoạn

| Giai đoạn | Nội dung | Phụ thuộc | Skill chủ | Trạng thái |
|---|---|---|---|---|
| [01](phase-01-phu-luc-data-contract-va-ma-arm.md) | Phụ lục data contract IM1, mã arm, ràng buộc quyết định | — | nckh-method | done: a02 được chủ dự án quyết 2026-10-26; a01 giữ làm lịch sử ([receipt a02](work/receipts/01-a02-hash-01.json)) |
| [02](phase-02-kiem-truoc-trien-khai.md) | Kiểm lộ test, membership H1, đặc tả quy tắc chọn đường (CPU, chỉ đọc) | — (trước 2026-10-26: 01; xem §8) | nckh-data, nckh-statistics | done: S1 quyết "ghi nhận và tiếp tục, có giới hạn" 2026-10-26 ([receipt](work/receipts/02-h1-membership-04.json)) |
| [03](phase-03-thanh-phan-chung-va-tool-tat-dinh.md) | Đồ thị trace, S-first, tool metric/log/trace tất định, bộ chọn đường | 01 (a02), 02 | nckh-backend, nckh-test | planned |
| [04](phase-04-builder-nhanh-a-mot-loi-goi.md) | Builder bằng chứng R-a, một lời gọi tổng hợp, sổ chi phí, phân loại kết quả | 03 | nckh-backend, nckh-test | planned |
| [05](phase-05-khung-im1-va-kiem-ro-ri.md) | Khung IM1 từ trace vai train, khung xáo cạnh, đường không khung, kiểm rò rỉ | 03, 04, 01 (a02) | nckh-backend, nckh-security | planned |
| [06](phase-06-confidence-thong-ke-va-power.md) | Confidence theo registry, bootstrap `group_id`, quy ước đọc CI, MDE/power với mẫu số đã kiểm | 02, 04, 05 | nckh-statistics | planned |
| [07](phase-07-goi-kha-thi-va-cong-dung.md) | Gói khả thi không chạy, cổng dừng, yêu cầu cấp quyền chạy | 04, 05, 06 | nckh-experiment | planned |
| [08](phase-08-review-va-ban-giao.md) | Review ngữ cảnh mới, chạy toàn bộ test, handoff | 01–07 | nckh-review, nckh-handoff | planned |

## 6. Quyền và cổng dừng

- Phase 01–02: tài liệu và kiểm CPU trong thư mục kế hoạch (xong).
- Phase 03–08 (cấp quyền 2026-10-26, dòng "Scope granted for phases 03–08" của decision log): sửa source có kiểm thử, kiểm CPU, mock trên dữ liệu tổng hợp, review, gói khả thi. Được mở rộng `selective.py`, khóa fit/cache/strata theo `arm`, với kiểm: ngưỡng, nguồn fit DEV và cache không trộn arm; dòng cũ thiếu `arm` đọc tương thích; `l0` và arm retrieval hiện có không đổi hành vi. Dừng ở gói khả thi và yêu cầu cấp quyền chạy.
- Chưa cho phép: chạy LLM thật (kể cả CPU inference, DEV pilot), GPU, cloud, API trả phí, gửi telemetry/evidence ra ngoài, mở thêm kết quả test trước M5, sửa prompt `v1`, protocol v2, split, bundle, commit/push.
- Cổng dừng chung:
  - **S1** (sau 02): phát hiện test RE2-OB đã lộ, hoặc membership H1 khác thiết kế → ghi thật, dừng trước khi cố định mẫu số, báo chủ dự án.
  - **S2** (sau 03/05): bất kỳ test rò rỉ nào thất bại → dừng, không nới test.
  - **S3** (sau 04): mock cho thấy hơn một lời gọi mỗi câu trả lời ở bất kỳ đường nào → dừng.
  - **S4** (phase 07, chỉ có hiệu lực khi chủ dự án sau này duyệt chạy): R-a trên model 4–9B không vượt B1m trên DEV → quyết định dừng, không tinh chỉnh vào test, không trích số DEV làm kết quả.
  - Rò rỉ, hơn một lời gọi mỗi câu trả lời, hay thay đổi hợp đồng vượt quyết định 2026-10-26 → dừng, báo chủ dự án.
  - **S5**: mọi việc cần API trả phí, gửi dữ liệu ra ngoài, GPU, cloud hay nhiều lời gọi → dừng, `waiting-human`.

## 7. Việc ngoài kế hoạch này

- Kế hoạch riêng (D8): phân tích tĩnh và kiểm CPU không LLM của code gốc RCLAgent (repo `LLM4AIOps/RCLAgent-V2`), tách kết luận về code gốc khỏi adaptation.
- Chờ bản TDSC (D5) trước khi so với số của bản xuất bản.
- M5 (đóng băng prompt, builder, ngưỡng, họ confirmatory) và M6 (chạy test) cần kế hoạch và quyền riêng.

## 8. Lịch sử sửa

- **2026-10-26, phụ thuộc của phase 02.** Bảng §5 ghi trước đó phase 02 phụ thuộc 01. Chủ dự án chỉ rõ (lệnh `nckh-cook` 2026-10-26) rằng việc chờ duyệt phụ lục chỉ chặn các bước cần sửa source. Kiểm lộ test, đếm membership H1 và đặc tả quy tắc chọn đường không dùng nội dung phụ lục, nên phase 02 không phụ thuộc 01. Đặc tả chỉ cần biết khung của khóa có hợp lệ hay không; khóa K1/K2 được chọn khi duyệt phụ lục. Phụ thuộc của 03 và 05 vào "01 duyệt" giữ nguyên.
- **2026-10-26, câu kiểm của phase 03.** Câu "với `no_trace`, bộ chọn đường trả `no_trace`" được sửa theo [đặc tả a01](work/path-selection-spec.md): với điều kiện `no_trace`, bộ chọn trả `no_trace` khi arm dùng khung và khóa có khung hợp lệ, ngược lại trả `frame_free`; không bao giờ trả `trace`. Câu cũ giữ dạng gạch trong phase 03.
- **2026-10-26, kết quả phase 01–02.** Bản nháp a01 của phụ lục, mã arm và bảng quyết định → kiểm tra đã soạn (receipt `01-consistency-01`), **chưa được chủ dự án duyệt**. Membership H1 khớp thiết kế (`02-h1-membership-04`). Kiểm lộ test thấy tổng gộp vai test RCAEval của baseline không-LLM và audit đọc nhãn đã được đọc ngày 18–20/10 (`work/test-exposure-audit.md`, `02-exposure-audit-hash-02`), nên cổng S1 mở. Dừng trước khi cố định mẫu số hay sửa source.
- **2026-10-26, receipt thay thế.** `02-h1-membership-04` thay `02-h1-membership-03`: cùng CSV (sha256 `2a02d52d…97e1`), nhưng hash đầu vào nằm ngoài thư mục plan được ghi vào `work/h1-membership-recheck.inputs.json`, vì `check-receipt` báo path traversal với -03. `02-spec-hash-02` và `02-exposure-audit-hash-02` thay các bản -01, vì `check-receipt` đọc đối số `python -c` của chúng là lệnh ghép. Hash tài liệu không đổi. Phụ lục, đặc tả và báo cáo lộ test vẫn nhắc tên receipt -03/-01; các receipt cũ được giữ.
- **2026-10-26, quyết định của chủ dự án về a01 và S1.** Phụ lục và mã arm được sửa thành bản **a02** ([phụ lục](work/data-contract-addendum-im1-a02.md), [mã arm](work/arm-ids-a02.csv), [bảng quyết định](work/decision-check-map-a02.csv), [đặc tả đường](work/path-selection-spec-a02.md); kiểm 18/18 PASS, receipt `01-a02-hash-01`); a01 giữ làm lịch sử, không được duyệt nguyên trạng. Khóa khung K2 `(dataset, dataset_subset, system, split)`, không chuyển khung RE2-TT sang RE3-TT; thêm `trace_id`; ngưỡng hợp lệ 3 ca train góp cạnh, cố định; khung xáo cạnh một seed, trên 0,5 cạnh thật giữ lại là không thông tin; trường `arm` với 4 mã `l0`, `ra`, `ra_im1`, `ra_im1_shuf`. Pool giữ 108/285 test; RE2-SS và RE3-TT đi `frame_free`; số đường là dự kiến, phase 05 đo độ phủ thật. Kết quả chính trên toàn pool; nhóm có khung là thăm dò, báo riêng.
- **2026-10-26, S1.** Quyết định "ghi nhận và tiếp tục, có giới hạn": tổng gộp đã đọc trước D12, góp phần định hướng ưu tiên nghiên cứu; không thấy bằng chứng tinh chỉnh R-a/IM1 theo chúng, nhưng không loại trừ tuyệt đối. Split và mẫu số không đổi; không phân tích tập sạch chỉ RE2-OB; không gọi đánh giá trên split này là xác nhận độc lập; M5 phải ghi lịch sử tiếp xúc. Không dùng các cụm "không lộ test" hay "khôi phục tính mù".
- **2026-10-26, kiểm D10 ở phase 06.** Yêu cầu "CI theo nhóm không hẹp hơn CI theo injection" được thay: resample theo `group_id` giữ lặp cùng nhóm; hai arm của một contrast ghép cặp dùng cùng nhóm; fixture đối chiếu với tham chiếu độc lập; phân tích chính không đổi, `group_id` là độ nhạy. Không đổi thuật toán hay seed để ép CI rộng hơn. Câu cũ giữ dạng gạch trong phase 06.
- **2026-10-26, phụ thuộc phase 05.** Thêm 04 vì đường `no_trace` có khung nằm trong `rcl_evidence.py` của phase 04.
- **2026-10-26, tạm hoãn.** Chủ dự án quay về hướng một bài nền: kế thừa RCLAgent với cơ chế đệ quy, một backbone gọi nhiều lần, tái hiện tối thiểu trước ([decisions.md](../261018-2300-single-llm-simplification-and-evaluation-hardening/decisions.md), ba dòng cuối ngày 2026-10-26). H1, IM1, MDE, bootstrap và gói khả thi dừng ở trạng thái ghi trong [điểm dừng](work/stop-point.md); source và artifact giữ nguyên, chưa commit. R-a là adaptation từ RCLAgent, không phải bản tái hiện, đã bỏ cơ chế đệ quy trung tâm; việc bỏ đó không tự chứng minh đóng góp mới.
