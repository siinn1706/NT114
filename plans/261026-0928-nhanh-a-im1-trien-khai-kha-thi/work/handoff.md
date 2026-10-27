# Handoff: nhánh (a) + IM1, sau phase 01–02

Cập nhật 2026-10-26 (Asia/Saigon). Lệnh: `/nckh-cook --auto` cho [plan.md](../plan.md), chỉ phase 01–02 (tài liệu và kiểm CPU cục bộ, không gọi model). Dừng tại đây; phase 03 chưa bắt đầu.

## Trạng thái

- Plan: `in-progress`; `check-plan.py` VERIFIED (`02-check-plan-02`).
- Phase 01: `waiting-human`. Bản nháp a01 của phụ lục, mã arm và bảng quyết định → kiểm tra **chưa được chủ dự án duyệt**.
- Phase 02: `waiting-human`. Ba kiểm đã xong; cổng S1 mở do lộ tổng gộp test (mục Kết quả).
- Không sửa source, config, protocol v2, prompt, splits hay bundle. Không chạy model/GPU. Không commit/push.

## Artifact và SHA-256 (đo sau mọi sửa, trước khi viết tệp này)

| Tệp | SHA-256 | Receipt |
|---|---|---|
| `work/data-contract-addendum-im1-draft.md` (a01) | 438f8b17401a045ac20e88311c43cb07f366acb4ba34724783787c4c2c136709 | `01-consistency-01` |
| `work/arm-ids.csv` (a01) | 3be44111f8e2ab141c5d43d6fb2f34b7c3e66aa0737311eaa0e1d3d3ec5f35d6 | `01-consistency-01` |
| `work/decision-check-map.csv` (a01) | 24a6ad58147750cbad68b0dbea1fe5144979dab7d47994789ba3235f0e41ff83 | `01-consistency-01` |
| `work/path-selection-spec.md` (a01) | 90623a22e8af8048d69cf00e14b363270149f474f0e2b4244a89fd4f805da913 | `02-spec-hash-02` |
| `work/test-exposure-audit.md` (a01) | ccd70c7032a5b13f58b1b16b43d112c4ba4eb71263f0c7de59cdf643cb45d457 | `02-exposure-audit-hash-02` |
| `work/h1-membership-recheck.csv` | 2a02d52d87039b52017a8a275b2aa0cc32593b86276d803392916458b39897e1 | `02-h1-membership-04` |
| `work/h1-membership-recheck.inputs.json` (hash 4 đầu vào data home) | 4cf105c35bebf2936f34a74decc7608a2b096900bfd6b7476b5f65541f3aa95b | `02-h1-membership-04` |
| `work/consistency-check-a01.json` | 0ff50b4d95b8b7e3e18c95fd1efeecc9044686e0a26154edc3721fae0944bef5 | `01-consistency-01` |
| `plan.md` | 6b150ca5914977e84b7942a474e34878c8b6b6400a11e074e8303897dc092b0f | `02-check-plan-02` |
| `phase-01-…md` / `phase-02-…md` / `phase-03-…md` | 895df97e…b0f / fcbd06bb…b36 / d42cf40f…a69 | `02-check-plan-02` |

Đầu vào data home (`02-h1-membership-04`): `assignments.jsonl` e9b2c81c96ce…5902 (khớp `assignments_sha256` của split), `visible/incidents.jsonl` 4f71e0a6…33ee, `condition-matrix-rcaeval.json` 89996556…5015, `eval-units-rcaeval.json` 97883d39…0258.

## Kết quả

- **Membership H1: khớp thiết kế.** Test 108 injection / 285 bản ghi; val 78 / 210; 69 injection test có trace (RE2-OB 21, RE2-TT 18, RE3-TT 30); 39 RE2-SS không trace; 0 bản ghi bị loại khỏi phân tích chính.
- **Lộ test (D12):**
  - Không thấy kết quả LLM hay R-a trên test trên máy này.
  - Kết quả riêng của RE2-OB test: không thấy bằng chứng đã đọc; đầy đủ thì không xác định được.
  - Tổng gộp vai test RCAEval (218, chứa 21 RE2-OB) của baseline không-LLM và audit đọc nhãn đã được đọc ngày 18–20/10, trước D12. Một phần đã dùng cho lựa chọn hướng nghiên cứu (câu hỏi 4 xếp sau H1).
  - Máy khác: không xác định được.
  - Trong lượt này tôi có thấy khối `counts.test.by_stratum` (hệ | họ lỗi, suy từ nhãn) khi xem `split.json`.
  - Phương án: [test-exposure-audit.md](test-exposure-audit.md) mục 4. Đề xuất phương án (1), ghi nhận và tiếp tục; chủ dự án chọn.
- **Đường dự kiến trên pool** ([path-selection-spec.md](path-selection-spec.md) §3): trên test, arm có khung khác `ra` ở 69 bản ghi (K1) hoặc 39 (K2) trong 285; sock-shop luôn đi `frame_free`.

## Khác biệt thực chất so với thiết kế cũ

1. sock-shop không có ca train nào có trace, nên IM1 không tác động được lên 39 injection RE2-SS. IM1 chỉ đổi bản ghi `no_trace` của ca có trace.
2. RE3-TT chỉ có ở vai test (30 injection), không có ở train hay val. Phải chọn khóa khung K1 (theo hệ, dùng khung RE2-TT) hoặc K2 (theo subset và hệ, RE3-TT đi `frame_free`). DEV không thử được trường hợp RE3-TT.
3. Thêm trường `trace_id` vào danh sách trường dựng cạnh.
4. Dùng trường `arm` mới thay vì thêm giá trị vào trục `retrieval`. R-a và đối chứng không khung là một arm (`ra`); bảng còn 4 mã thay vì 5 mục.
5. Phụ thuộc của phase 02 vào 01 đã bỏ, và câu kiểm `no_trace` của phase 03 đã sửa (plan.md §8, giữ lịch sử).
6. Phạm vi sửa source thêm `selective.py`: khóa tầng của DEV-fit (protocol v2 §9) phải có `arm` để arm có khung không gộp với `l0`. Phase 06 hiện chỉ ghi `contrasts.py` hoặc `analyze.py`.

## Phạm vi sửa source dự kiến sau khi duyệt (phase 03–06, chưa làm)

- Tạo: `src/rca/rcl_trace_graph.py`, `rcl_tools.py`, `rcl_path.py`, `rcl_evidence.py`, `im1_frame.py`; các test `tests/test_rcl_trace_graph.py`, `test_rcl_tools.py`, `test_rcl_path.py`, `test_rcl_evidence.py`, `test_im1_frame.py`, `test_im1_leakage.py`; `configs/exp/ra-mock.yaml`.
- Sửa có test:
  - `run_grid.py`: trường `arm`, hash khung trong manifest, bốn loại kết quả, `blind_nonroot_ev` cho builder mới.
  - `cost.py`: đếm lời gọi theo ô và arm.
  - Danh sách quét import ở `audit.py` hoặc `tests/test_leakage.py`.
  - `contrasts.py` hoặc `analyze.py`: bootstrap `group_id`, nhãn đọc CI, khóa báo cáo theo arm.
  - `selective.py`: khóa tầng có `arm`.
  - `docs/data_contract.md` §7 quy tắc 8: chép đúng bản phụ lục đã duyệt.
  - `llms.txt` dòng 17, nếu cần nêu cách dùng train mới.
- Không sửa: `evidence.py` (`BUILDER_VERSION = 3`), prompt `v1`, splits, bundle, protocol v2.

## Sổ attempt

- **Hoàn tất, receipt VERIFIED:** `01-consistency-01` (15/15 PASS), `02-h1-membership-04`, `02-spec-hash-02`, `02-exposure-audit-hash-02`, `02-check-plan-02`.
- **Bị thay, giữ lại** (`check-receipt` FAILED, lý do đã biết):
  - `02-h1-membership-02` và `-03`: script đã sửa sau đó; -03 còn ghi đường dẫn ngoài thư mục plan.
  - `02-spec-hash-01`, `02-exposure-audit-hash-01`: đối số `python -c` bị đọc là lệnh ghép.
  - `02-check-plan-01`: plan.md đã sửa sau đó.
- **Không có receipt:** `02-h1-membership-01`. Lệnh chạy xong, nhưng ghi receipt lỗi vì thư mục `work/receipts` chưa tồn tại; log ở `work/logs/02-h1-membership-01.out`. Đầu ra a02 giữ ở `work/h1-membership-recheck-a02.csv`. Các lệnh đọc config, manifest và mã nguồn cho kiểm lộ test là lệnh chỉ đọc tại chỗ, không có receipt riêng.
- **Chờ:** chủ dự án duyệt phụ lục a01 và mã arm theo hash; chọn K1/K2 và bốn điểm còn lại ở phụ lục mục D; chọn phương án S1.

## Máy

- Máy đang chạy phiên: i5-14400F, RAM 31,8 GB, AMD RX 5600 XT, không CUDA (CIM/WMI).
- Máy GPU dự kiến: RTX 4080 Laptop 12 GB, chưa probe; cấu hình trong repo không phải phần cứng đã đo.

## Bước tiếp theo (chưa có quyền)

1. Chủ dự án ghi quyết định duyệt (hoặc yêu cầu sửa) vào `decisions.md`, kèm hash phụ lục `438f8b17…6709` và mã arm `3be44111…35d6`.
2. Chủ dự án chọn phương án S1.
3. Sau đó mới giao lệnh cho phase 03–06. Chạy model chỉ sau gói khả thi ở phase 07 và quyền riêng.
