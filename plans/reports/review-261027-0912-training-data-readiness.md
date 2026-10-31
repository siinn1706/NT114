# Review dữ liệu và khả năng bắt đầu chạy — 2026-10-27

**Kết luận:** dữ liệu canonical đã xử lý và có manifest train/val/test. Nhánh hiện tại là suy luận/tái hiện RCLAgent bằng model có sẵn, chưa phải fine-tuning. Chưa sẵn sàng chạy đánh giá chính thức: ca thật trên Kaggle vẫn dừng trước kết quả cuối. Có thể tiếp tục xử lý và kiểm thử ca train tối thiểu sau khi giải quyết lỗi phạm vi tool.

Phạm vi: review tại HEAD `7941e17`, đọc source, manifest, dữ liệu local và artifact Kaggle; chỉ chạy kiểm CPU/checksum, không chạy model, GPU, cài thư viện hoặc sửa sản phẩm.

## Findings

1. **Chặn đánh giá chính thức — smoke với dữ liệu thật chưa hoàn tất.** [Summary version 5](../261026-1713-rclagent-tai-hien-toi-thieu/kaggle/kaggle-repair-v5-summary.json) ghi `status=failed`, `stage=E`, `scoring_ran=false`. Model gọi tool cho `cartservice` ngoài service/time domain của gói sau 2 requests. Gate D qua 3 requests không chứng minh recursion và synthesis chạy hết với dữ liệu thật. SHA256 archive version 5 đã được tính lại và khớp summary. Cần giải quyết hợp đồng query và dữ liệu của tool, sau đó hoàn tất một trace train, kết quả cuối và scorer trước khi mở rộng lượt chạy; không bỏ guard để ép qua.
2. **Chưa có đường fine-tuning để bắt đầu train trọng số.** [README hiện tại](../../README.md) xác định không thực hiện fine-tuning; không có `src/rca/sft_export.py` hoặc `scripts/train_lora.py` trong project Python hiện tại. Dữ liệu canonical và vai train không tương đương dataset SFT đã token hóa, có target/loss và trainer. Nếu “train” có nghĩa chạy mô hình cho thí nghiệm, dùng kết luận ở finding 1; nếu có nghĩa cập nhật trọng số, phần đó chưa sẵn sàng và chưa thuộc nhánh tái hiện hiện tại.
3. **Cần làm rõ ánh xạ một ca trước khi đóng băng batch RE2-OB.** [Bảng vai](../261026-1713-rclagent-tai-hien-toi-thieu/work/re2ob-case-roles.csv) có 90 case ID duy nhất: 47 dòng `train`, 1 dòng `train;unassigned`, 21 `val`, 21 `test`. `checkoutservice_cpu_1` khớp hai canonical UID qua inject time. Không thấy ca này thuộc nhiều vai train/val/test, nên chưa có bằng chứng rò rỉ giữa các tập; cần chốt ánh xạ thay vì coi cả 48 ca train đều ánh xạ một-một. Ca smoke `checkoutservice_cpu_2` có vai train rõ ràng.
4. **Môi trường CPU RCLAgent local thiếu dependency của harness.** Venv riêng tại `F:/Nam/UIT/nt114-paper-artifacts/W7165616276/env` chạy harness được 9/14 test, 5 lỗi `ModuleNotFoundError: jsonschema`. Venv NT114 thử trước đó thiếu `requests`, lỗi setup cả 14 test. Đây là lỗi môi trường local; runtime Kaggle có khai báo riêng `jsonschema==4.25.1` và `requests==2.32.5`. Không suy ra môi trường Kaggle có cùng lỗi và không cài/sửa dependency trong review này.

## Dữ liệu đã xử lý

Đếm lại `visible/incidents.jsonl`, `eval_only/quality.jsonl` và kiểm sự tồn tại của từng đường dẫn telemetry:

| Nguồn | Bản ghi | ACCEPT | Có cảnh báo | REJECT | File telemetry thiếu |
|---|---:|---:|---:|---:|---:|
| RCAEval | 736 | 703 | 32 | 1 | 0/1.338 |
| AIOps2025 | 400 | 381 | 19 | 0 | 0/1.145 |
| RCA100 | 103 | 9 | 94 | 0 | 0/309 |
| Nezha | 101 | 0 | 101 | 0 | 0/303 |
| Tổng | 1.340 | 1.093 | 246 | 1 | 0/3.095 |

Các số là bản ghi canonical, không mặc nhiên là sự cố độc lập. 1.339 bản ghi không bị REJECT không có nghĩa tất cả đủ điều kiện cho mọi giao thức. Bundle `nt114-data-v1-20261014-6fdd9835` khoảng 10,67 GB qua kiểm tất cả checksum bằng `rca.prep verify-bundle`; lần này không chạy `--deep` để tính lại semantic fingerprint.

Đường preprocess tác giả RCLAgent riêng đã tạo đầu ra tại `F:/Nam/UIT/nt114-paper-artifacts/W7165616276/data/re2ob`. Log ghi 90 ca, 450 error traces, 34.461.235 span, 9.409.001 dòng metric và 15.053.223 dòng log. Các file đầu ra vẫn tồn tại; receipt preprocess và receipt ánh xạ vai đều được kiểm lại với verdict `VERIFIED`. Receipt preprocess không chứa hash của toàn bộ CSV đầu ra; lần này không tính lại hash các CSV lớn đó.

Gói Kaggle hiện tại chỉ có một ca train/một trace: 33 span, 38.048 dòng metric, 0 dòng log theo bộ lọc tác giả. Cả 24 member của ZIP khớp allowlist, kích thước và checksum manifest. Nhãn nằm riêng trong `scoring/`.

## Chia tập

| Manifest/giao thức | Train | Val (DEV) | Test | Ghi chú |
|---|---:|---:|---:|---|
| RCAEval grouped | 374 | 143 | 218 | 91 nhóm; tập chính đã có val |
| RCAEval retrieval | 451 | 140 | 144 | Giao thức khác; không trộn với grouped |
| RE2-OB ánh xạ từ RCAEval grouped | 48* | 21 | 21 | *Một ca `train;unassigned` như finding 3 |
| AIOps2025 retrieval | 141 | 36 | 170 | Chỉ các bản ghi đủ điều kiện vào split |
| RCA100 grouped | 48 | 4 | 51 | Val rất nhỏ |
| Nezha eval-only | 0 | 0 | 101 | Giao thức đánh giá ngoài, không có val riêng |

Split được lưu bằng manifest/assignment, không cần ba bản sao telemetry ở ba thư mục. Tỷ lệ đích 60/20/20 được điều chỉnh bởi nguyên tắc giữ nguyên nhóm và đưa strata ít nhóm vào test. AIOps2025 grouped gom thành một nhóm và `headline_ok=false`, nên không dùng giao thức đó như một chia train/val/test hợp lệ cho kết quả chính.

`verify-splits` kiểm 16/16 manifest hiện hành đều OK: hash assignments đúng, không có group vượt nhiều vai, digest build khớp. Kiểm đếm độc lập cũng thấy 0 nhóm trộn vai trong từng manifest. Đây là kiểm các ràng buộc đã cài đặt, không chứng nhận mọi dạng rò rỉ có thể có.

## Kiểm chứng lần này

- `python -m rca.prep verify-splits`: exit 0, 16/16 OK.
- `python -m rca.prep verify-bundle data/export/nt114-data-v1-20261014-6fdd9835`: exit 0, OK.
- `pytest -q -p no:cacheprovider tests/test_splits.py tests/test_leakage.py`: 25 passed trong 162,52 giây; một RuntimeWarning của sklearn SVD trên fixture, không có test lỗi.
- `test-vllm-t4-compat.py`: 4/4 passed, chỉ kiểm CPU/source.
- `test-kaggle-harness.py`: lần đầu NT114 venv 14 setup errors vì thiếu requests; chạy lại bằng venv RCLAgent có 9 pass và 5 errors vì thiếu jsonschema. Không ghi thành pass.
- Hai receipt preprocess/role mapping: VERIFIED. ZIP Kaggle và archive kết quả version 5: checksum khớp.

| Gate | Trạng thái |
|---|---|
| Canonical data tồn tại, bundle checksum | PASS |
| Split manifests và regression split/leakage | PASS trong phạm vi kiểm |
| RE2-OB ánh xạ ca một-một cho batch | PENDING: một ca |
| Harness trong venv RCLAgent local | FAIL: thiếu jsonschema |
| Model/tool-calling trên Kaggle | PASS theo artifact version 5 |
| RCA end-to-end với model thật và scorer | FAIL/PENDING: dừng E, scorer chưa chạy |
| Dataset SFT và trainer fine-tuning | CHƯA CÓ trong project hiện tại |

Bước tiếp theo theo hướng hiện tại: sửa nguyên nhân query ngoài domain ở ca train, hoàn tất smoke và scorer, chốt ánh xạ ca rồi mới chạy pilot val. Không cần fine-tuning để tái hiện RCLAgent bằng backbone có sẵn.
