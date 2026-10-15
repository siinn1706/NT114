# nt114-rca — Trợ lý AI chẩn đoán sự cố khi thiếu dữ liệu giám sát

Code tham khảo cho kế hoạch 12 tuần. Pipeline:
**telemetry → bỏ modality → tóm tắt bằng chứng → (tra ca cũ) → LLM → lớp quyết định → độ đo.**

```
src/rca/
  data.py       đọc ca RCAEval (layout Zenodo và Hugging Face), chuẩn hóa tên dịch vụ
  ablate.py     5 điều kiện: full, no_trace, no_log, no_metric, blind_root
  evidence.py   telemetry -> văn bản ngắn (z-score metric, log lỗi, trace p90/lỗi/cạnh gọi)
  retrieve.py   kho ca cũ; BM25 (tự viết), dense (bge-small), hybrid (RRF); chế độ precedent/no_precedent
  llm.py        gọi vLLM bằng HTTP, ép JSON schema, n mẫu, cache SQLite; backend "mock" để test
  metrics.py    AC@k, Avg@5, số dịch vụ phải kiểm tra, sai-mà-chắc, ECE, AURC, McNemar, Holm, bootstrap
  gate.py       lớp quyết định offline: luôn trả lời / luôn tra / ngưỡng / học được / Jev
  run_grid.py   prepare (lưu bằng chứng) + run (gọi LLM từng ô, ghi JSONL, chạy tiếp được)
  analyze.py    bảng cho 3 câu hỏi nghiên cứu
scripts/make_synthetic.py   dữ liệu GIẢ đúng định dạng RCAEval, chỉ để test
configs/synthetic.yaml      test toàn bộ không cần GPU
configs/pilot.yaml          chạy thử thật: 10 ca/hệ thống, 1 mô hình 8B
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

```bash
python scripts/make_synthetic.py data_synth
PYTHONPATH=src python -m rca.run_grid prepare configs/synthetic.yaml
PYTHONPATH=src python -m rca.run_grid run     configs/synthetic.yaml
PYTHONPATH=src python -m rca.analyze results_synth/grid.jsonl --gate mock-small mock-big
PYTHONPATH=src python tests/test_pipeline.py
```
Số liệu ra từ bước này là vô nghĩa (LLM giả). Chỉ dùng để kiểm tra đường ống chạy đủ.

## 3. Chạy thật

> Máy GPU 12 GB (RTX 4080 Laptop): làm theo [docs/gpu_deployment.md](docs/gpu_deployment.md). Tài liệu này gồm
> hai venv, các mô hình ghim theo revision và phép thử khả thi `rca.feasibility`. Lệnh `vllm serve` dưới đây
> là cấu hình pilot cũ.

```bash
# tải dữ liệu (khoảng 30 phút cho cả 3 bộ, RE2+RE3 nhanh hơn)
python -c "from RCAEval.utility import download_re2_dataset, download_re3_dataset; download_re2_dataset(); download_re3_dataset()"

# terminal 1: mở vLLM (laptop 4080 12 GB: bản AWQ 4-bit, ngữ cảnh 16k)
vllm serve Qwen/Qwen2.5-7B-Instruct-AWQ --quantization awq --max-model-len 16384 --gpu-memory-utilization 0.85

# terminal 2
PYTHONPATH=src python -m rca.run_grid prepare configs/pilot.yaml
PYTHONPATH=src python -m rca.run_grid run     configs/pilot.yaml
PYTHONPATH=src python -m rca.analyze results/pilot.jsonl
```
Đổi tên mô hình trong `configs/pilot.yaml` theo bản bạn tải. Lưới đầy đủ: copy `pilot.yaml`, bỏ `limit_per_system`,
thêm mô hình thứ hai và 3B vào `models`, đổi `out`.

## 4. Những chỗ phải kiểm tra lại khi có dữ liệu thật

- **Tên dịch vụ.** `canon()` gộp `frontendservice`/`frontend`, bỏ tiền tố `ts-` và hậu tố `service`. Sau `prepare`,
  mở vài file trong `results/evidence/` xem danh sách ứng viên có bị trùng (vd `redis` và `rediscart`) không.
- **Cửa sổ thời gian** 10 phút trước / 5 phút sau `inject_time` (trong `evidence.py`). So với độ dài dữ liệu từng ca.
- **Độ dài bằng chứng** dưới ~3.500 token. Train Ticket nhiều dịch vụ, có thể phải giảm `max_services`.
- **So sánh công bằng giữa điều kiện:** Sock Shop không có trace nên `no_trace`/`blind_root` chỉ có ở OB và TT.
  Khi so với `full`, lọc `full` về cùng tập ca OB+TT.
- **Kho ca cũ** dùng bằng chứng đầy đủ modality của ca khác cùng hệ thống. Kết luận chính và Jev lấy chế độ `precedent`
  (không dùng nhãn của ca hỏi); `no_precedent` là phép thử oracle, báo cáo riêng (`oracle_store: true`).
- **Jev:** `gate.jev_payload` có một trường đánh dấu TODO; xác nhận với docs.typesafe.ai trước khi gọi.

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
dữ liệu, cách chia tập, quy tắc chống rò rỉ nhãn, trạng thái Jev): [docs/data_contract.md](docs/data_contract.md).

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

Chạy thử toàn bộ đường canonical trên dữ liệu giả, không cần GPU: xem các lệnh ở đầu
`configs/canonical_synthetic.yaml`. Bộ test nhanh: `python -m pytest -q -m "not realdata"`;
test trên dữ liệu thật: `python -m pytest -q -m realdata`.
