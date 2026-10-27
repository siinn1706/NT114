# Phụ lục data contract cho IM1 (phiên bản a02)

- Ngày: 2026-10-26 (Asia/Saigon). Phiên bản **a02**: hiện thực đúng các quyết định của chủ dự án ngày 2026-10-26 trên bản nháp a01 (K2; thêm `trace_id`; ngưỡng hợp lệ 3 cố định; khung xáo cạnh một seed, ngưỡng 0,5, không diễn giải là kiểm soát mọi đặc tính topology; trường `arm` và 4 mã; báo cáo độ phủ). Quyết định và hash a02 ghi ở dòng 2026-10-26 "IM1 amendment a02" của [decisions.md](../../261018-2300-single-llm-simplification-and-evaluation-hardening/decisions.md). Tệp không chứa hash của chính nó.
- Bản a01 ([data-contract-addendum-im1-draft.md](data-contract-addendum-im1-draft.md), sha256 `438f8b17…6709`) giữ nguyên làm lịch sử; a01 **không** được duyệt nguyên trạng.
- Đích: `nt114-rca/nt114-rca/docs/data_contract.md` §7, quy tắc 8. Phần A chép nguyên vào data contract ở phase 05. Mã arm: [arm-ids-a02.csv](arm-ids-a02.csv).

## A. Văn bản quy tắc (chép vào data contract §7)

> 8. **Train-role structure for the IM1 frame** (owner decisions D9 and D11 of 2026-10-26; amendment a02 of 2026-10-26, sha256 in `plans/261018-2300-single-llm-simplification-and-evaluation-hardening/decisions.md`). This is a new use of train-role information, separate from rule 3 (retrieval).
>    - **Arms.** Result rows carry `arm` ∈ {`l0`, `ra`, `ra_im1`, `ra_im1_shuf`}. Only `ra_im1` (`train_structure = im1_frame`) and `ra_im1_shuf` (`im1_frame_shuffled`) read a frame. `ra` is also IM1's same-pipeline frame-free control. `retrieval = none` keeps its meaning: no precedent store and no retrieved text. Rows without an `arm` field are read as `l0` when `retrieval = none` and stay the existing retrieval arm when `retrieval = hybrid`. Rows of different arms are never pooled, thresholds are never fitted across arms, and every table names the arm. Framed rows also carry `frame_sha256`.
>    - **Source.** Incidents that the run's split assigns to `train` (`assignments.jsonl`), read through the visible zone. No val or test incident, and no incident outside the split, is opened to build, check or tune a frame.
>    - **Window.** Per train incident, trace rows with `anchor_ns − 600 s ≤ ts_ns < anchor_ns` (the evidence "before" window, `evidence.NORMAL_S`). No row at or after the anchor is read. The anchor is used only to place this window, as in §5 (anchor visibility).
>    - **Fields.** `trace_id`, `span_id`, `parent_span_id` and `service_id`; `ts_ns` only for the window filter. `trace_id` is read only to resolve a `parent_span_id` within its trace. `duration_ns`, `status_code`, `operation`, `entity_raw`, logs and metrics are not read.
>    - **Edges.** A directed edge `parent service → child service` for each span whose `parent_span_id` resolves to a span of the same `trace_id`, when both `service_id`s are non-null and differ. The frame stores the node set, the edge set and, per edge, the number of contributing train incidents, nothing else.
>    - **Key.** One frame per `(dataset, dataset_subset, system, split)`. A frame is never transferred to another subset of the same system (for example RE2-TT to RE3-TT) in the current MVP, because a shared topology or deployment has not been established. The key is fixed here and is never chosen by comparing keys on results.
>    - **Validity.** A frame is valid when at least 3 train incidents of its key contributed at least one edge. Otherwise the key has no frame. The threshold is fixed and is not lowered after seeing coverage or results.
>    - **Freezing.** Each frame is written once as JSON with its sha256 before any val or test evidence of a framed arm is built. The run manifest records the frame hashes; a run refuses a frame whose hash differs from the manifest, and rebuilding a frame after val or test evidence exists must give the same hash or the run stops.
>    - **Edge-shuffled control.** For each valid frame, one shuffled frame with the same node set and the same number of edges, no self-loops, drawn uniformly without replacement first from ordered pairs that are not real edges (filled from real edges only when too few remain), with the single seed derived from the real frame's sha256. No other seed is tried. Its share of retained real edges is recorded; above 0.5 the control is reported as not informative for that key. The control keeps node set and edge count only; it does not control other topology properties (degree sequence, direction pattern, reachability).
>    - **Use.** A frame enters only the `no_trace` path of framed arms. Evidence and prompts may show service names and frame edges, never train incident ids, times or any other field above.
>    - **Fallback.** A key without a valid frame uses the `frame_free` path declared before evaluation. Those cases stay in the denominator and are reported as `frame_free`.
>    - **Reporting.** The declared pool (for H1, `single_modality` with all its records) is the population of every arm's primary result, including records on the `frame_free` path. Results on the subgroup with a valid frame are exploratory and are reported separately; they never replace the full-pool result, and IM1 is never described as covering all of H1. The frame coverage reported is the coverage measured after building the frames, not a projection.
>    - **Forbidden.** Labels (`eval_only/`, `LabelRecord`, `Truth`), root services, fault types and families, any key or column in `schema.LABEL_DENYLIST`, val or test telemetry, and any model output, for building, checking, keying or tuning a frame.
>    - **Checks** (`tests/test_im1_frame.py`, `tests/test_im1_leakage.py`): permuting train labels leaves the frame hash unchanged; a canary label value never appears in a frame; rows at or after the anchor are excluded; a val or test incident passed to the builder raises; building val/test evidence leaves the frame hash unchanged; the builder imports no label-reading module (rule 7); the shuffled frame keeps the node and edge counts and records its retained share; a key without a valid frame yields `frame_free` and the record stays counted.

## B. Đối chiếu điều kiện D11 → quy tắc → kiểm ở phase 05

| # | Điều kiện D11 | Mục trong quy tắc A | Kiểm (phase 05) |
|---|---|---|---|
| 1 | Chỉ cửa sổ trước anchor và các trường cần để dựng cạnh | Window; Fields | bản ghi tại/sau anchor bị loại; builder chỉ đọc 5 cột đã liệt kê |
| 2 | Không nhãn, loại lỗi hay telemetry val/test để dựng hay tinh chỉnh | Source; Forbidden | hoán vị nhãn train không đổi hash khung; canary; ca val/test vào builder phải ném lỗi; quét import |
| 3 | Dựng theo từng hệ và split, đóng băng trước val/test | Key (K2); Freezing | hash khung ghi trong manifest; dựng val/test xong hash không đổi |
| 4 | Có kiểm rò rỉ | Checks | `tests/test_im1_leakage.py` |
| 5 | Đối chứng không khung cùng pipeline | Arms (`ra`) | `ra` và `ra_im1` dùng cùng builder, khác nhau chỉ ở đường của ca không span |
| 6 | Kiểm cơ chế bằng khung xáo cạnh | Edge-shuffled control | cùng số nút và số cạnh; một seed; ghi tỷ lệ cạnh thật giữ lại |
| 7 | Đường không khung khai báo trước khi không có khung hợp lệ | Validity; Fallback | khóa không có khung trả `frame_free`; tổng loại kết quả bằng số ca |
| — | `retrieval = none` không đổi nghĩa; arm H1 hiện có giữ; H1 báo riêng cho arm có khung | Arms; Reporting | trường `arm` trong khóa báo cáo, fit và cache; bảng H1 theo arm trên toàn pool |

## C. Độ phủ dự kiến với K2 (chưa phải độ phủ thật)

Số ca train có trace theo khóa K2 (receipt `02-h1-membership-04`): RE2-OB 48, RE3-OB 15, RE2-TT 54; RE3-TT 0; sock-shop 0. Số ca **góp cạnh** chỉ biết sau khi dựng khung ở phase 05; ngưỡng 3 áp dụng trên số đó. Dự kiến trên pool H1: test có tối đa 39/285 bản ghi đi đường `no_trace` của arm có khung (RE2-OB 21, RE2-TT 18); RE3-TT (30 bản ghi `no_trace`) và mọi bản ghi sock-shop đi `frame_free`. Val: tối đa 54/210.

## D. Thay đổi so với a01

1. Khóa: chỉ K2; bỏ phương án K1.
2. `trace_id` được giữ, kèm câu giới hạn dùng.
3. Ngưỡng hợp lệ: thêm "không hạ sau khi thấy độ phủ hay kết quả".
4. Khung xáo cạnh: một seed, không thử seed khác; nói rõ đối chứng không kiểm soát mọi đặc tính topology.
5. Quy tắc dữ liệu cũ thiếu `arm` và cấm fit ngưỡng xuyên arm đưa vào mục Arms (trước ở bảng mã arm).
6. Thêm mục Reporting theo quyết định về độ phủ và mẫu số.
