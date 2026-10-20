# Review trước khi chuyển máy chạy model — 2026-10-19

## Kết luận

**Chưa thông qua để chạy thí nghiệm chính.** Có 6 lỗi chức năng đã xác minh: 3 lỗi P1 về tính đúng đắn của kết quả và 3 lỗi P2 về đường chạy GPU/phạm vi lưới. 113 test được chọn đều pass; các probe bổ sung vẫn tái hiện được các lỗi bên dưới.

Revision được review: `f8112a2f22a7001d736b0aa0579e832981217bde`, nhánh `main`. Các thay đổi của phiên trước đã nằm trong commit này; không còn diff tracked khi bắt đầu và kết thúc review. Phạm vi gồm commit sửa 7 finding trước, các caller phân tích, config DEV/sampling và runbook GPU. Đây là review, không thực hiện sửa source.

Mục tiêu là kiểm tra rò rỉ split/store, resume, scoring, feasibility, tái tạo kết quả và tính đúng của bảng phân tích trước khi chuyển máy. Giữ nguyên single LLM, prompt v1, evidence, split và bundle. Điều kiện dừng của lượt review: có vị trí source, tác động, bằng chứng tái hiện, kết quả test và kết luận readiness; không yêu cầu các bug được sửa trong một yêu cầu review-only.

## Findings

### 1. [P1] Resume bỏ qua thay đổi `top_k`, rồi ghi config mới cho kết quả cũ

Owner: [run_grid.py](../../nt114-rca/nt114-rca/src/rca/run_grid.py), dòng 631–638; [llm.py](../../nt114-rca/nt114-rca/src/rca/llm.py), `execution()`.

Key của grid có evidence/store fingerprint và execution signature, nhưng không có `top_k` hay digest của prompt thực tế sau retrieval. `_check_resumable` cũng chỉ kiểm tra execution signature. Khi đổi `top_k` và dùng lại `out`, row cũ bị coi là hoàn tất trước khi retrieval và `build_messages` được thực hiện. Cuối lượt, `config.yaml` và manifest được ghi lại theo config mới.

Bằng chứng: probe trên canonical synthetic fixture chạy `top_k=3`, sau đó `top_k=1`, với hash config được tính lại. 18 row giữ nguyên từng byte và vẫn có 3 hit/row, còn config được lưu ghi `top_k: 1`. Đây là sai provenance và có thể khiến so sánh các cấu hình retrieval dùng nhầm kết quả.

Sửa: đưa hợp đồng tạo prompt/retrieval, ít nhất `top_k`, vào identity được kiểm tra trước resume; từ chối output cũ khi hợp đồng khác hoặc yêu cầu output mới. Thêm regression test đổi `top_k`, kiểm tra cả grid và config/manifest.

### 2. [P1] DEV-fit chấp nhận mock hoặc model revision khác cho bảng chính

Owner: [analyze.py](../../nt114-rca/nt114-rca/src/rca/analyze.py), dòng 264–271 và 400–406.

DEV bị tách khỏi `main` trước `guard_headline(main)`. Việc chọn source cho threshold chỉ dựa trên dataset, granularity, set-scored, tên model, condition và retrieval/store mode. Backend, revision, prompt và execution signature của DEV không được kiểm tra tương thích với test. Vì thế cùng tên model nhưng DEV là mock hoặc dùng sampling/revision khác vẫn được dùng để fit threshold của live test, mà không bị đánh dấu `no_source` hay bị headline guard từ chối.

Bằng chứng: synthetic fixture có test `backend=vllm`, DEV `backend=mock`, khác revision/server fingerprint/execution signature. `analyze.run` với `preregistration_sha` vẫn trả `headline: true` và 2 dòng `dev_fit` hợp lệ. Đây là kiểm tra đường code, không phải real-model run.

Sửa: kiểm tra identity và provenance tương thích giữa DEV và test trước khi fit; reject hoặc ghi `no_source` nếu khác. Metadata của source phải lưu được identity này. Thêm negative tests cho mock DEV và khác revision/sampling/prompt.

### 3. [P1] Bảng baseline chính vẫn trộn DEV vào test

Owner: [analyze.py](../../nt114-rca/nt114-rca/src/rca/analyze.py), dòng 306–315 và 433–436.

`joint_baselines` đã loại DEV cho contrasts, nhưng nhánh `table_baselines` lại đọc trực tiếp toàn bộ baseline đã có điểm. `baselines_table` group theo dataset × model × condition, bỏ `split_role` và granularity. Nếu file hoặc danh sách baseline chứa cả DEV và test, bảng chính trộn chúng mà không còn cột để nhận biết. Nhánh này cũng chưa áp dụng cùng primary-exclusion mask như frame LLM.

Bằng chứng: baseline synthetic có DEV AC@1=1.0 và test AC@1=0.0. Trong analysis có `headline: true`, `table_baselines.csv` báo AC@1=0.5 cho cả hai condition, không có `split_role`. Kết quả test đúng của fixture phải là 0.0.

Sửa: áp dụng selection của population chính cho baseline trước khi tạo bảng, giữ các strata cần thiết và kiểm tra exclusions. Thêm regression test baseline kết hợp DEV/test; xử lý reference-only rows theo hợp đồng hiện có.

### 4. [P2] `run` dùng mọi condition trên đĩa, không lọc theo config hiện hành

Owner: [run_grid.py](../../nt114-rca/nt114-rca/src/rca/run_grid.py), dòng 622–625.

Runner duyệt thẳng `r['conditions'].items()`. Nó không lấy giao với conditions được yêu cầu và không kiểm tra đầy đủ các condition đang cần có trong evidence. `dev-pilot.yaml` và `dev-sampling.yaml` dùng chung evidence directory, nên prepare một config có thể thay đổi nội dung mà config kia sẽ chạy khi resume. Có thể gọi thừa model hoặc âm thầm thiếu các cell của pilot.

Bằng chứng: cùng probe ở finding 1 yêu cầu `conditions: [full]`, nhưng output có 7 condition: `full`, `blind_root`, `blind_nonroot`, `metrics_only`, `no_log`, `no_metric`, `no_trace`. Evidence được lấy từ fixture đã prepare nhiều condition; fingerprint vẫn hợp lệ.

Sửa: giới hạn vòng lặp theo `cn.conditions(uid)`, xử lý `skipped` có chủ đích, và báo lỗi yêu cầu prepare lại nếu evidence thiếu condition cần thiết. Thêm regression test hai config dùng chung evidence directory theo cả hai thứ tự.

### 5. [P2] Lệnh serve thủ công không dùng venv serving đã cài

Owner: [gpu_deployment.md](../../nt114-rca/nt114-rca/docs/gpu_deployment.md), dòng 80–82, 171–172; [serve_model.sh](../../nt114-rca/nt114-rca/scripts/serve_model.sh), dòng 17–19.

Runbook giữ analysis venv đang active, cài vLLM vào `.venv-serve` và chỉ export `VLLM_VENV`. Feasibility tự thêm `VLLM_VENV/bin` vào PATH của subprocess, nhưng lệnh serve thủ công ở M2 gọi shell script trực tiếp. Script dùng `python` và `vllm` trên PATH, không đọc `VLLM_VENV`. Trên môi trường hai venv đúng như runbook, lệnh thất bại với `vllm: not found`; nếu có vLLM toàn cục, có thể chạy nhầm môi trường.

Bằng chứng: shell fixture cô lập, export `VLLM_VENV` nhưng không thêm serving bin vào PATH: exit 127 tại `exec vllm`. Thêm serving bin vào PATH: exit 0. Chỉ dùng executable stub, không start real vLLM/GPU.

Sửa: lệnh M2 phải prefix PATH bằng serving bin hoặc dùng launcher chủ động resolve serving environment, đồng thời giữ analysis Python cho các lệnh client.

### 6. [P2] Sampling đọc nhầm đường dẫn launch arguments so với runbook

Owner: [dev-sampling.yaml](../../nt114-rca/nt114-rca/configs/exp/dev-sampling.yaml), dòng 35; [gpu_deployment.md](../../nt114-rca/nt114-rca/docs/gpu_deployment.md), dòng 171–173.

Runbook bước M2.1 tạo `results_dev_pilot/server/qwen35-4b.args`, rồi bước M2.2 chạy sampling. Config sampling lại yêu cầu `results_dev_sampling/server/qwen35-4b.args`. Trên checkout mới file thứ hai không tồn tại, nên `LLM.server_fingerprint()` ném `RuntimeError` trước request đầu tiên dù server đã chạy đúng.

Bằng chứng: đối chiếu hai config và gọi fingerprint với file sampling chưa tồn tại tái hiện đúng lỗi `launch arguments file ... not found`; không có network call.

Sửa: đồng bộ `launch_args` với file của server thực tế đang phục vụ cho cả sampling và pilot; thêm kiểm tra đường chạy M2 từ môi trường mới.

## Kiểm tra đã chạy trong lượt này

Chạy từ `nt114-rca/nt114-rca` bằng `.venv/Scripts/python.exe`:

```powershell
python -m pytest -q tests/test_leakage.py tests/test_run_grid_canonical.py tests/test_score.py tests/test_reproduce.py tests/test_feasibility.py --basetemp=<review-scratch>/pytest-focused-verified --tb=short -rfEs
python -u -m pytest -q tests/test_analyze.py tests/test_selective.py tests/test_leakage_audit.py tests/test_pipeline.py --basetemp=<review-scratch>/pytest-analysis-verified --tb=short -rfEs
```

- Nhóm đầu: **65 passed**, 1 warning sklearn trên fixture degenerate, 363.74 s.
- Nhóm phân tích: **48 passed**, 42.82 s.
- Tổng **113 passed**, không có failed/skipped trong hai selection cuối.
- SHA256 đối chiếu snapshot evidence: **862 expected, 0 missing, 0 changed**.
- `git diff --check HEAD^ HEAD` pass; tracked working diff và staged diff rỗng.
- Probe source và kết quả nằm dưới [review-runtime-261019-2254](../review-runtime-261019-2254/): `review-probes.py/.json`, `resume-probe.py/.json/.log`, `serve-env-probe/result.json`, `evidence-check.json` và hai log test `*-verified.log`.

Các lần chạy chưa hợp lệ cũng được phân loại: lần đầu thiếu parent directory của basetemp; lần sau gặp `PermissionError` do sandbox; rerun ngoài sandbox pass. Một lệnh nhóm phân tích dùng nhầm tên `test_metrics.py` không tồn tại nên exit 4, không chạy test; lệnh đã sửa dùng các file test thực tế và pass 48 test. Không dùng các lần này làm bằng chứng lỗi product hoặc test thành công.

Không chạy lại toàn bộ suite hay raw-parity suite trong lượt này. Các probe dùng synthetic fixtures hoặc shell stubs; không phải chất lượng mô hình hay GPU runtime. Các file source và frozen inputs giữ nguyên.

## Readiness để mang đi chạy

| Mục tiêu | Kết luận |
|---|---|
| Chuyển source/data sang máy mới để tiếp tục chuẩn bị | Có thể chuyển, kèm report này và revision đã nêu. |
| Chạy DEV zero-shot để chốt pipeline | Sửa đường serve/sampling và các lỗi runner trước; sau đó vẫn phải chạy Linux portability, GPU probe và feasibility trên máy đích. |
| Chạy main experiments và dùng bảng cho nghiên cứu | Chưa thông qua: cần sửa các P1, kiểm tra regression mới, rồi thực hiện DEV/pilot/preregistration gates hiện hành. |
| Fine-tune trọng số bằng QLoRA | Chưa có đường train hoàn chỉnh: `sft_export.py` và `scripts/train_lora.py` chưa tồn tại. `llms.txt` và training strategy hiện hành xác định zero-shot là chính, QLoRA là phần mở rộng có gate. |

Không có quyết định khoa học nào bị đảo ngược trong review này. Các fix đề xuất giữ nguyên single-LLM, prompt v1, split, evidence và bundle.
