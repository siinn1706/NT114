# Phụ lục data contract cho IM1 (bản nháp a01, chờ chủ dự án duyệt)

- Ngày soạn: 2026-10-26 (Asia/Saigon). Bản nháp **a01**. Trạng thái: **chưa được duyệt**. Hash SHA-256 của tệp này nằm trong receipt `01-consistency-01` và trong handoff; tệp không chứa hash của chính nó.
- Cơ sở: dòng 2026-10-26 "D9, D11" trong [decisions.md](../../261018-2300-single-llm-simplification-and-evaluation-hardening/decisions.md); [improvement-hypotheses.md](../../261024-0858-tong-quan-1000-q1-chon-bai-nen-rca-thieu-telemetry/design/improvement-hypotheses.md) IM1; [test-matrix.md](../../261024-0858-tong-quan-1000-q1-chon-bai-nen-rca-thieu-telemetry/design/test-matrix.md) §10.4.
- Đích: thêm thành quy tắc 8 của `nt114-rca/nt114-rca/docs/data_contract.md` §7 (Leakage rules). Việc chép vào repo là bước đầu của phase 05, chỉ sau khi chủ dự án duyệt **đúng phiên bản này** (theo hash). Tệp này không sửa `docs/data_contract.md`.
- Phần A là văn bản quy tắc bằng tiếng Anh để chép nguyên vào data contract (data contract viết bằng tiếng Anh). Phần B–D là ghi chú để duyệt, không chép vào repo.
- Mã arm: [arm-ids.csv](arm-ids.csv). Quyết định → kiểm tra: [decision-check-map.csv](decision-check-map.csv).

## A. Văn bản quy tắc (chép vào data contract §7 sau khi duyệt)

> 8. **Train-role structure for the IM1 frame** (owner decisions D9 and D11 of 2026-10-26; amendment dated `<date of approval>`, draft sha256 `<hash>`). This is a new use of train-role information, separate from rule 3 (retrieval).
>    - **Scope.** Only arms whose `train_structure` is `im1_frame` or `im1_frame_shuffled` (`arm-ids.csv`) read a frame. `retrieval = none` keeps its meaning: no precedent store and no retrieved text. Framed rows carry `arm` and `frame_sha256`; they are never pooled with, or reported as, `arm = l0` rows, and every H1 table states the arm.
>    - **Source.** Incidents that the run's split assigns to `train` (`assignments.jsonl`), read through the visible zone (`CanonicalStore.incidents(..., role="train")`). No val or test incident, and no incident outside the split, is opened to build, check or tune a frame.
>    - **Window.** Per train incident, trace rows with `anchor_ns − 600 s ≤ ts_ns < anchor_ns` (the evidence "before" window, `evidence.NORMAL_S`). No row at or after the anchor is read. The anchor is used only to place this window, as in §5 (anchor visibility).
>    - **Fields.** `trace_id`, `span_id`, `parent_span_id`, `service_id`, and `ts_ns` for the window filter only. `duration_ns`, `status_code`, `operation`, `entity_raw`, logs and metrics are not read.
>    - **Edges.** A directed edge `parent service → child service` for each span whose `parent_span_id` resolves to a span of the same `trace_id`, when both `service_id`s are non-null and differ. The frame stores the node set, the edge set and, per edge, the number of contributing train incidents, nothing else (no incident ids, times or counts per incident).
>    - **Key.** One frame per `(dataset, system, split)` [**K1**, proposed default] — or per `(dataset, dataset_subset, system, split)` [**K2**]. The owner chooses K1 or K2 when approving this rule; the choice is never revised after seeing val or test data.
>    - **Validity.** A frame is valid when at least 3 train incidents of its key contributed at least one edge. Otherwise the key has no frame. This threshold is fixed here and is not tuned.
>    - **Freezing.** Each frame is written once as JSON with its sha256 before any val or test evidence of a framed arm is built. The run manifest records the frame hashes; a run refuses a frame whose hash differs from the manifest, and rebuilding a frame after val or test evidence exists must give the same hash or the run stops.
>    - **Edge-shuffled control.** For each valid frame, a shuffled frame with the same node set and the same number of edges, no self-loops, drawn uniformly without replacement first from ordered pairs that are not real edges (filled from real edges only when too few remain), seeded by the real frame's sha256. Its share of retained real edges is recorded; above 0.5 the control is reported as not informative for that key.
>    - **Use.** A frame enters only the `no_trace` path of framed arms (`path-selection-spec.md`). Evidence and prompts may show service names and frame edges, never train incident ids, times or any field above beyond the edge set.
>    - **Fallback.** A key without a valid frame uses the `frame_free` path declared before evaluation. Those cases stay in the denominator and are reported as `frame_free`.
>    - **Forbidden.** Labels (`eval_only/`, `LabelRecord`, `Truth`), root services, fault types and families, any key or column in `schema.LABEL_DENYLIST`, val or test telemetry, and any model output, for building, checking, choosing the key of, or tuning a frame.
>    - **Checks** (`tests/test_im1_frame.py`, `tests/test_im1_leakage.py`): permuting train labels leaves the frame hash unchanged; a canary label value never appears in a frame; rows at or after the anchor are excluded; a val or test incident passed to the builder raises; building val/test evidence leaves the frame hash unchanged; the builder imports no label-reading module (rule 7); the shuffled frame keeps the node and edge counts and records its retained share; a key without a valid frame yields `frame_free` and the record stays counted.

## B. Đối chiếu điều kiện D11 → quy tắc → kiểm ở phase 05

| # | Điều kiện D11 (decisions.md, dòng D9/D11) | Mục trong quy tắc A | Kiểm (phase 05) |
|---|---|---|---|
| 1 | Chỉ cửa sổ trước anchor và các trường cần để dựng cạnh | Window; Fields | bản ghi tại/sau anchor bị loại; builder chỉ đọc 5 cột đã liệt kê |
| 2 | Không nhãn, loại lỗi hay telemetry val/test để dựng hay tinh chỉnh | Source; Forbidden | hoán vị nhãn train không đổi hash khung; canary; ca val/test vào builder phải ném lỗi; quét import |
| 3 | Dựng theo từng hệ và split, đóng băng trước val/test | Key; Freezing | hash khung ghi trong manifest; dựng val/test xong hash không đổi |
| 4 | Có kiểm rò rỉ | Checks | `tests/test_im1_leakage.py` |
| 5 | Đối chứng không khung cùng pipeline | Scope; arm `ra` | arm `ra` chạy cùng builder, khác `ra_im1` chỉ ở đường của ca không span |
| 6 | Kiểm cơ chế bằng khung xáo cạnh | Edge-shuffled control | cùng số nút và số cạnh; ghi tỷ lệ cạnh thật giữ lại |
| 7 | Đường không khung khai báo trước khi không có khung hợp lệ | Validity; Fallback | khóa không có khung trả `frame_free`; tổng loại kết quả bằng số ca |
| — | `retrieval = none` không đổi nghĩa; arm H1 hiện có giữ; H1 báo riêng cho arm có khung | Scope | trường `arm` và `frame_sha256` trong khóa báo cáo; bảng H1 theo arm |

## C. Dữ kiện đã kiểm, ảnh hưởng trực tiếp tới quy tắc (đọc không nhãn, receipt `02-h1-membership-03`)

Ca vai train có trace trên split `within-rcaeval-grouped-0-e9b2c81c` ([h1-membership-recheck.csv](h1-membership-recheck.csv)):

| Subset, hệ | Ca train có trace | Ca có trace trong pool H1 vai val | Ca có trace trong pool H1 vai test |
|---|---:|---:|---:|
| RE2 online-boutique | 48 | 21 | 21 |
| RE3 online-boutique | 15 | 15 | 0 |
| RE2 train-ticket | 54 | 18 | 18 |
| RE3 train-ticket | 0 | 0 | 30 |
| sock-shop (mọi subset) | 0 | 0 (24 ca không trace) | 0 (39 ca RE2-SS không trace) |

Hệ quả:

- **sock-shop không có khung ở cả K1 lẫn K2** (không có ca nào có trace hiện diện; RE3-SS có 13 ca trace ở trạng thái `empty`). Mọi ca sock-shop của pool đi đường `frame_free` ở mọi arm R-a. IM1 không thể tác động lên 39 injection RE2-SS.
- **K1** (theo hệ): khung train-ticket dựng từ RE2-TT train và dùng cho 30 injection RE3-TT test. Trên test, `ra_im1` khác `ra` ở 69 bản ghi `no_trace`; trên val, ở 54. DEV không có ca RE3-TT nào, nên cách khung RE2 dùng cho RE3 chưa được thử trên DEV.
- **K2** (theo subset và hệ): RE3-TT không có khung; trên test `ra_im1` khác `ra` ở 39 bản ghi (RE2-OB 21, RE2-TT 18); 30 injection RE3-TT đi `frame_free`. Trên val vẫn là 54, nên DEV phủ khung nhiều hơn test.
- Tôi **không** so tập dịch vụ giữa RE2-TT và RE3-TT để chọn khóa: RE3-TT chỉ có ở vai test, và D11 cấm dùng telemetry val/test để tinh chỉnh khung. Việc chọn K1 hay K2 vì vậy phải dựa trên lý do thiết kế, không dựa trên dữ liệu test.

## D. Điểm cần chủ dự án quyết khi duyệt (không tự chốt)

1. **Khóa khung: K1 hay K2.** Đề xuất mặc định K1, vì D11 viết "theo từng hệ và split", và giả định của IM1 là cấu trúc lịch sử của cùng hệ. Rủi ro của K1: nếu RE3-TT được triển khai khác RE2-TT, khung có thể lỗi thời. Rủi ro này đúng là giả định hiệu lực ngoài mà improvement-hypotheses đã ghi. K2 an toàn hơn về cấu trúc nhưng thu hẹp phạm vi IM1 trên test còn 39 bản ghi.
2. **Thêm trường `trace_id`** so với danh sách trong plan (`service_id`, `span_id`, `parent_span_id`, thời gian). Lý do: `parent_span_id` chỉ tra được trong cùng một trace; `trace_id` không mang nhãn.
3. **Ngưỡng hợp lệ** "ít nhất 3 ca train góp cạnh" và ngưỡng 0,5 cho tỷ lệ cạnh thật giữ lại trong khung xáo. Cả hai được đặt trước, không tinh chỉnh.
4. **Trường `arm` mới** thay vì thêm giá trị vào trục `retrieval`. Protocol v2 §1 chỉ khai báo `retrieval: [none, hybrid]`; nhét khung vào trục đó sẽ đổi nghĩa ngầm.
5. **Arm R-a và đối chứng không khung là một** (`ra`). Hai mục trong plan có cùng pipeline và cùng đầu vào, nên ra cùng prompt và cùng đầu ra. Tách thành hai arm chỉ nhân đôi số lần chạy.
