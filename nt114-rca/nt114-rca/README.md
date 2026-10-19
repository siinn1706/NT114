# nt114-rca — Trợ lý AI chẩn đoán sự cố khi thiếu dữ liệu giám sát

Code tham khảo cho kế hoạch 12 tuần. Pipeline:
**telemetry → bỏ modality → tóm tắt bằng chứng → (tra ca cũ) → một LLM → đánh giá chọn lọc → độ đo.**

```
src/rca/
  data.py       đọc ca RCAEval (layout Zenodo và Hugging Face), chuẩn hóa tên dịch vụ
  ablate.py     5 điều kiện: full, no_trace, no_log, no_metric, blind_root
  evidence.py   telemetry -> văn bản ngắn (z-score metric, log lỗi, trace p90/lỗi/cạnh gọi)
  retrieve.py   kho ca cũ; BM25 (tự viết), dense (bge-small), hybrid (RRF); chế độ precedent/no_precedent
  llm.py        gọi vLLM bằng HTTP, ép JSON schema, n mẫu, cache SQLite; backend "mock" để test
  metrics.py    AC@1-5, MRR@5 (hạng sau 5 bị cắt), sai-mà-chắc, ECE, AURC, McNemar, Holm, bootstrap theo cụm
  selective.py  đánh giá chọn lọc offline trên ô đã lưu của cùng một LLM: trả lời / tra cứu / từ chối
  run_grid.py   prepare (lưu bằng chứng) + run (gọi LLM từng ô, ghi JSONL, chạy tiếp được)
  confidence.py danh mục điểm tự tin, chỉ từ đầu ra của cùng một LLM (đồng thuận, tự khai, Borda, entropy...)
  contrasts.py  so sánh ghép cặp khai báo trong config: đơn vị = lần tiêm lỗi, bootstrap cụm, sign-flip, Holm
  analyze.py    điểm vào phân tích: `python -m rca.analyze <analysis.yaml | grid.jsonl>`
  cost.py       chi phí đầu-cuối mỗi ô và mỗi đường nhánh: token, độ trễ LLM, giây tra cứu, giây chuẩn bị
  reproduce.py  tạo lại mọi bảng từ đầu vào đã lưu và so sha256: `python -m rca.reproduce <thư mục phân tích>`
  baselines.py  mốc không-LLM: B0, B1 (metric/log/trace), B1m thứ tự bằng chứng, B3 prior từ train; `--baro`
  baro.py       BARO-style bằng NumPy, đối chiếu với bản chính thức của RCAEval qua fixture (tests/fixtures/baro)
  leakage_audit.py  gần-trùng văn bản giữa bằng chứng truy vấn và kho truy hồi (TF-IDF cosine, Jaccard dòng)
  alignment.py  kiểm kê ca RE1 (uid, thời điểm tiêm, sha256) và đối chiếu với danh sách ca của một bản phát hành ngoài
scripts/export_baro_inputs.py  xuất khung metric thô + sha256 cho phía tham chiếu BARO
scripts/simulate_contrasts.py  mô phỏng độ phủ CI, sai lầm loại I và MDE của `contrasts` trên cấu trúc lần tiêm thật
scripts/make_synthetic.py   dữ liệu GIẢ đúng định dạng RCAEval, chỉ để test
configs/canonical_synthetic.yaml  test toàn bộ đường canonical không cần GPU
configs/canonical_pilot.yaml      chạy thử thật: 10 ca/hệ thống, 1 mô hình 8B
tests/test_pipeline.py      test đơn vị + giả lập server vLLM
```

## 1. Cài đặt (Ubuntu 22.04 / WSL2, Python 3.12)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pip install "RCAEval[default]"          # để tải dữ liệu và chạy baseline BARO
pip install vllm                         # môi trường riêng nếu xung đột thư viện
```

## 2. Test ngay, không cần GPU hay dữ liệu thật

Các lệnh dựng kho chuẩn hóa từ dữ liệu giả rồi chạy `prepare`, `run`, `analyze` nằm ở đầu
[configs/canonical_synthetic.yaml](configs/canonical_synthetic.yaml). Bộ test:

```bash
PYTHONPATH=src python -m pytest -q -m "not realdata"
```
Số liệu ra từ bước này là vô nghĩa (LLM giả). Chỉ dùng để kiểm tra đường ống chạy đủ.

Phân tích theo file cấu hình (lưới, đầu ra thô, độ hiển thị, mốc, các so sánh ghép cặp khai báo sẵn):
xem [configs/analysis/example-mock.yaml](configs/analysis/example-mock.yaml). `analyze` ghi
`analysis_config.yaml` và `analysis_meta.json` (sha256 đầu vào và bảng); `rca.reproduce` chạy lại và so sánh.
Không có `preregistration_sha` thì mọi bảng mang tiền tố `exploratory_`.

## 3. Chạy thật

> Máy GPU 12 GB (RTX 4080 Laptop): làm theo [docs/gpu_deployment.md](docs/gpu_deployment.md). Tài liệu này gồm
> hai venv, các mô hình ghim theo revision và phép thử khả thi `rca.feasibility`.

`run_grid` chỉ đọc kho chuẩn hóa (`source: canonical`, mục 6); config khác bị từ chối. Pilot thật trên RE2+RE3:
lệnh `vllm serve`, `prepare` và `run` nằm ở đầu [configs/canonical_pilot.yaml](configs/canonical_pilot.yaml).
Đổi tên mô hình theo bản bạn tải; lưới đầy đủ: copy file, bỏ `limit_per_system`, đổi `out`.

## 4. Những chỗ phải kiểm tra lại khi có dữ liệu thật

- **Tên dịch vụ.** `canon()` gộp `frontendservice`/`frontend`, bỏ tiền tố `ts-` và hậu tố `service`. Sau `prepare`,
  mở vài file trong `results/evidence/` xem danh sách ứng viên có bị trùng (vd `redis` và `rediscart`) không.
- **Cửa sổ thời gian** 10 phút trước / 5 phút sau `inject_time` (trong `evidence.py`). So với độ dài dữ liệu từng ca.
- **Độ dài bằng chứng** dưới ~3.500 token. Train Ticket nhiều dịch vụ, có thể phải giảm `max_services`.
- **So sánh công bằng giữa điều kiện:** Sock Shop không có trace nên `no_trace`/`blind_root` chỉ có ở OB và TT.
  Khi so với `full`, lọc `full` về cùng tập ca OB+TT.
- **Kho ca cũ** dùng bằng chứng đầy đủ modality của ca khác cùng hệ thống. Kết luận chính lấy chế độ `precedent`
  (không dùng nhãn của ca hỏi); `no_precedent` là phép thử oracle, báo cáo riêng (`oracle_store: true`).

## 5. Dữ liệu cần có

| Loại | Dùng để | Bắt buộc? |
|---|---|---|
| RCAEval RE2 (270 ca) + RE3 (90 ca): Online Boutique, Sock Shop, Train Ticket; metric + log + trace (SS không có trace) | Tập đánh giá chính | Có |
| Kho ca cũ | Tự dựng từ chính RE2/RE3 (bằng chứng + nhãn của các ca khác) | Có, không phải tải thêm |
| Trọng số LLM: 1 mô hình 3B, 2 mô hình 8B khác họ, bản AWQ 4-bit | Chạy lưới | Có |
| Mô hình embedding `BAAI/bge-small-en-v1.5` | Truy hồi dense | Có (thiếu thì tự dùng TF-IDF) |
| Dữ liệu demo tự sinh: Online Boutique trên k3d + Prometheus/Loki/Jaeger + Chaos Mesh | Case study, video | Có |
| RCAEval RE1 (375 ca, chỉ metric) | Kiểm tra thêm trường hợp "chỉ có metric" thật | Nên có |
| Nezha (FSE'23): Online Boutique + Train Ticket, metric/log/trace, MIT | Kiểm chứng chéo trên benchmark thứ hai | Nên có, cần viết adapter |
| LEMMA-RCA, AnoMod | Ít phù hợp (trace không đầy đủ / chưa rõ nơi tải) | Không |

Cách tải và kiểm chứng dữ liệu thô (nguồn, checksum, provenance, các bộ chưa tải và lý do): [docs/acquisition_plan.md](docs/acquisition_plan.md).

## 6. Đường dữ liệu chuẩn hóa (canonical)

Dữ liệu thô đã kiểm chứng được chuẩn hóa một lần trên máy chuẩn bị, rồi chuyển sang máy GPU dưới dạng
bundle có checksum. Hợp đồng dữ liệu (vùng `visible`/`eval_only`, trạng thái chất lượng, điều kiện thiếu
dữ liệu, cách chia tập, quy tắc chống rò rỉ nhãn, đánh giá chọn lọc): [docs/data_contract.md](docs/data_contract.md).

```bash
export PYTHONPATH=src
python -m rca.prep normalize --dataset rcaeval       # chạy tiếp được nếu bị dừng; cũng: nezha, aiops2025, rca100
python -m rca.prep validate  --dataset rcaeval
python -m rca.prep audit
python -m rca.prep conditions --dataset rcaeval
python -m rca.prep eval-units --dataset rcaeval      # đơn vị thống kê độc lập (injection), trọng số, loại trừ, độ phủ log/trace
python -m rca.prep split --protocol within-rcaeval-grouped --seed 0     # và -retrieval, loso-, eval-only-, xdata-rcaeval-to-<bộ>
python -m rca.prep verify-splits
python -m rca.prep export --bundle nt114-data-v1
# trên máy GPU, sau khi chép bundle:
python -m rca.prep verify-bundle <bundle> --deep
bash scripts/verify_portability.sh <bundle>
RCA_DATA_HOME=<bundle>/parts python -m rca.run_grid prepare configs/canonical_pilot.yaml
```

Khi đánh giá: đơn vị độc lập là injection (`injection_id` trong `data/reports/eval-units-<bộ>.json`),
không phải task hay biến thể điều kiện; so sánh các điều kiện (kể cả `metrics_only`) theo cặp trên
cùng sự cố; các sự cố trong `configs/eval_exclusions.yaml` bị loại khỏi bảng chính. Chi tiết:
mục 6 của [docs/data_contract.md](docs/data_contract.md).

Đầu ra thô của LLM: `run_grid run` ghi `llm_raw.jsonl` cạnh `out` (văn bản trả lời, mẫu đã phân tích,
`finish_reason`, logprobs khi mô hình đặt `logprobs: true`, siêu dữ liệu yêu cầu không có header và prompt chỉ
lưu sha256). Tắt bằng `raw_outputs: false`; đổi đường dẫn bằng `raw_outputs_path` (phải nằm trong thư mục
git-ignore như `results*/`, vì câu trả lời có thể trích telemetry). Ca đã có trong cache cũ ghi
`raw_available: false`.

Kiểm tra độ hiển thị bằng chứng (chỉ vùng eval-only, sau `prepare`): `python -m rca.visibility <cfg> [--roles val test]`
ghi `evidence_visibility.jsonl` và `table_evidence_visibility.csv` cạnh `out`: dịch vụ gốc có trong danh sách
ứng viên không, có được nêu tên trong bằng chứng không và ở khối nào. Không nêu tên không có nghĩa là không thể đoán đúng.

Chạy thử toàn bộ đường canonical trên dữ liệu giả, không cần GPU: xem các lệnh ở đầu
`configs/canonical_synthetic.yaml`. Bộ test nhanh: `python -m pytest -q -m "not realdata"`;
test trên dữ liệu thật: `python -m pytest -q -m realdata`.
