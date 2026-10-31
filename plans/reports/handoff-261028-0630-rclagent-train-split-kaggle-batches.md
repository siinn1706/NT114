# Bàn giao: chạy RCLAgent trên 240 trace train RE2-OB theo 5 lô Kaggle — 2026-10-28

**Trạng thái:** harness đã chạy ổn định trên Kaggle T4. Lượt pilot 5 trace (version 11) passed 5/5. Đã có kế hoạch chia 240 trace train thành 5 lô, mỗi lô một phiên Kaggle khoảng 6–8 giờ, tổng khoảng 37 giờ GPU T4. Chưa lô nào được dựng gói hay chạy.

Việc của người nhận là lần lượt từng lô: dựng gói trên CPU, kiểm, đẩy lên Kaggle ở chế độ private, chạy, tải kết quả, tóm tắt và ghi report.

Mọi đường dẫn bên dưới tính từ thư mục `plans/261026-1713-rclagent-tai-hien-toi-thieu/kaggle/`, trừ khi ghi khác.

## 1. Đọc trước

| Tài liệu | Để làm gì |
|---|---|
| [kaggle/README.md](../261026-1713-rclagent-tai-hien-toi-thieu/kaggle/README.md) | Cấu hình, dữ liệu, wrapper và giới hạn diễn giải |
| [scan-261028-0619-train-split-span-count-and-batches.md](scan-261028-0619-train-split-span-count-and-batches.md) | Cách đếm span, mô hình thời gian, rủi ro và cách chia lô |
| [run-261027-2337-rclagent-kaggle-v11-train-pilot-unchunked.md](run-261027-2337-rclagent-kaggle-v11-train-pilot-unchunked.md) | Lượt pilot mới nhất, dùng làm mẫu cho report mỗi lô |
| [bench-261027-2232-t4-prefill-chunked-vs-unchunked.md](bench-261027-2232-t4-prefill-chunked-vs-unchunked.md) | Lý do server không dùng chunked prefill |
| [run-261027-2115-rclagent-kaggle-v10-train-pilot-null-guard.md](run-261027-2115-rclagent-kaggle-v10-train-pilot-null-guard.md) và [run-261027-1922-rclagent-kaggle-v9-train-pilot.md](run-261027-1922-rclagent-kaggle-v9-train-pilot.md) | Hai lượt pilot trước và các lỗi đã sửa |

## 2. Không được đổi

Các thiết lập dưới đây đã đóng băng. Muốn đổi bất kỳ thứ gì phải có quyết định của chủ dự án, vì kết quả sẽ không còn so được với các lô khác.

- **Code:** upstream RCLAgent-V2 ở commit `3052e7a`, giữ nguyên prompt, không sửa source.
- **Model:** `Qwen/Qwen3-4B-Instruct-2507`, revision `cdbee75f`.
- **Sampling:** temperature 0,7; top_p 0,8; top_k 20; seed 20261026.
- **Giới hạn:** context 16.384 token; output 512 token (1.024 cho tổng hợp); 3 lần retry; tối đa 4 vòng tool mỗi span; mỗi trace tối đa 160 request và 1.800 giây.
- **Server vLLM:** không chunked prefill, `--max-num-batched-tokens` bằng context. Đây là cấu hình từ version 11 và cả 5 lô phải dùng đúng cấu hình này.
- **Dữ liệu:** không đổi dữ liệu chuẩn hay split. Không fine-tune. Nhãn chỉ dùng lúc chấm.
- **Quyền riêng tư:** dataset và notebook trên Kaggle luôn để private. Không in hay commit credential.
- **Chạy một lượt:** trace failed được ghi lại, không chạy lại, không chọn lại trace.

## 3. Cần có trước khi bắt đầu

1. **Repo:** nhánh `feat/rclagent-harness-budget-guard`.
2. **Thư mục artifact ngoài repo**, đặt ở `F:/Nam/UIT/nt114-paper-artifacts/W7165616276`. Đường dẫn này gắn cứng trong `prepare-bundle.py`, ở hằng `ARTIFACT`; đặt chỗ khác thì phải sửa hằng này. Thư mục gồm:
   - `code/`: git checkout sạch của RCLAgent-V2 ở commit `3052e7a6a9598d984ba1482f3dc41123c8823a99`. Script sẽ kiểm commit và working tree sạch.
   - `data/re2ob/`: đầu ra preprocess của tác giả (`trace/all/trace_jaeger-span.csv`, `metric/all/metrics.csv`, `log/all/logs.csv`, `error_traces.txt`).
   - `data/raw/RE2-OB/<fault>/<n>/`: dữ liệu thô RE2-OB, tải từ [RCAEval, Zenodo 14590730](https://zenodo.org/records/14590730).
3. **Môi trường CPU** `runtime/harness-env`, dùng Python 3.12. Cách tạo ghi ở đầu `harness-requirements.txt`. Thư mục `runtime/` bị gitignore, nên máy mới phải tự tạo.
4. **Tài khoản Kaggle** có quota GPU T4 và Kaggle CLI 2.2.5. Script `check-kaggle-private.py` cần Python có module `kaggle`, không chạy trong harness-env.
   - Các slug đang dùng thuộc tài khoản `siinn1706`: dataset `siinn1706/rclagent-one-trace-smoke-261026` và notebook `siinn1706/rclagent-one-trace-gpu-smoke-261026`.
   - Dùng tài khoản khác thì đổi `id` và `dataset_sources` trong hai file metadata ở mục 5, và đổi `ref` trong `check-kaggle-private.py`.
   - Notebook tự tìm bundle dưới `/kaggle/input`, nên không cần sửa notebook.

## 4. File Python

**Dựng và kiểm gói trên CPU:**

| File | Vai trò |
|---|---|
| `plan-train-batches.py` | Chia 240 trace train thành lô, ghi `train-batches.json`. Chỉ chạy lại khi cần đổi cách chia |
| `prepare-bundle.py` | Dựng gói cho một danh sách trace vào `runtime/package-NAME`, kèm đối chiếu endpoint với dữ liệu đầy đủ |
| `refresh-package.py` | Chép wrapper vào gói đã dựng, ghi `manifest.json`, tạo `rclagent-kaggle-bundle.zip` và file `.sha256` |
| `build-notebook.py` | Dựng `rclagent-kaggle-smoke.ipynb` có nhúng hash bundle |
| `verify-package.py` | Kiểm cấu trúc gói, wrapper và notebook, ghi `package-validation.json` |
| `check-tool-result-budget.py TOKENIZER_DIR` | Kiểm ngân sách `search_logs` trên CPU, ghi `tool-result-budget-check.json`. Chỉ chạy lại khi sửa `smoke-worker.py` hoặc `tool-result-budget.py`. Script cần gói một trace cũ (`runtime/package`) và kết quả version 6 trong `runtime/`, nên trên máy mới sẽ không chạy được |
| `test-kaggle-harness.py`, `test-tool-result-budget.py`, `test-vllm-t4-compat.py`, `test-prefill-bench.py` | Test CPU, phải pass hết trước khi đẩy lên Kaggle |

**Chạy trên Kaggle:** các file sau nằm trong bundle, không chạy trên máy local.

| File | Vai trò |
|---|---|
| `kaggle-runtime.py` | Điều phối cài đặt, server vLLM, chạy từng trace, `progress.json`, chạy tiếp khi bị ngắt, chấm điểm |
| `smoke-worker.py` | Wrapper quanh code upstream: đếm request, guard JSON, deadline, ngân sách tool |
| `tool-result-budget.py` | Rút gọn kết quả `search_logs` về 2.048 token |
| `vllm-t4-compat.py`, `verify-t4-prefix-kernel.py` | Bản vá và kiểm kernel cho T4 |

**Sau khi chạy:**

| File | Vai trò |
|---|---|
| `summarize-repair-run.py V` | Kiểm và tóm tắt kết quả tải về của notebook version `V`, tự ghi `kaggle-repair-vV-summary.json`. Đừng chuyển stdout của nó vào chính file này, vì sẽ làm hỏng file |
| `check-kaggle-private.py` | Kiểm dataset và mọi notebook đã tải về đều private, ghi `kaggle-private-status.json` |

**Không dùng:** `stage-kaggle-repair.py`. Script này gọi `refresh-package.py` không kèm tham số, nên sẽ dựng lại gói một trace cũ của version 8, đè lên gói của lô.

## 5. Quy trình cho một lô

Ví dụ cho lô 1, chạy trong PowerShell, đứng ở thư mục `kaggle/`. `$py` là Python của harness-env.

```powershell
$py = 'runtime/harness-env/Scripts/python.exe'
```

**Bước 1. Lấy danh sách trace của lô và dựng gói.** Mỗi lần dựng phải dùng một NAME mới; script từ chối ghi đè thư mục đã có.

```powershell
$ids = & $py -I -c "import json; print(' '.join(json.load(open('train-batches.json'))['batches'][0]['trace_ids']))"
& $py -X utf8 prepare-bundle.py train-b1 $ids.Split(' ')
```

**Bước 2. Đưa gói lên làm bundle hiện hành và dựng notebook.**

```powershell
& $py -X utf8 refresh-package.py runtime/package-train-b1
& $py -X utf8 build-notebook.py
& $py -X utf8 verify-package.py
```

`verify-package.py` kiểm rằng `tool-result-budget-check.json` khớp hash của `smoke-worker.py` và `tool-result-budget.py` trong gói. Hai file này không đổi giữa các lô, nên không cần chạy lại `check-tool-result-budget.py`.

**Bước 3. Chạy test CPU.** Tất cả phải OK.

```powershell
foreach ($t in 'test-kaggle-harness.py','test-tool-result-budget.py','test-vllm-t4-compat.py','test-prefill-bench.py') { & $py -X utf8 $t }
```

**Bước 4. Đẩy lên Kaggle.**

- Chép `rclagent-kaggle-bundle.zip` vào `runtime/kaggle-dataset-upload/`, và `rclagent-kaggle-smoke.ipynb` vào `runtime/kaggle-kernel-upload/`. Mỗi thư mục chỉ chứa file đó và file metadata của nó.
- Đứng trong thư mục dataset, chạy `kaggle datasets version -p . -m "train batch 1"`.
- Đợi dataset xử lý xong, rồi đứng trong thư mục kernel chạy `kaggle kernels push -p .`.
- Ghi lại version notebook Kaggle trả về, gọi là `V`. Các lượt trước kết thúc ở 11, nên lô 1 thường là 12.

Hai file metadata, chỉ đổi `id` nếu dùng tài khoản khác:

```json
{"id": "siinn1706/rclagent-one-trace-smoke-261026", "title": "RCLAgent One Trace Smoke 261026", "licenses": [{"name": "other"}]}
```

```json
{"id": "siinn1706/rclagent-one-trace-gpu-smoke-261026", "title": "RCLAgent One Trace GPU Smoke 261026", "code_file": "rclagent-kaggle-smoke.ipynb", "language": "python", "kernel_type": "notebook", "is_private": true, "enable_gpu": true, "enable_internet": true, "machine_shape": "NvidiaTeslaT4", "dataset_sources": ["siinn1706/rclagent-one-trace-smoke-261026"], "competition_sources": [], "kernel_sources": [], "model_sources": []}
```

**Bước 5. Theo dõi và tải kết quả.**

- Xem trạng thái bằng `kaggle kernels status siinn1706/rclagent-one-trace-gpu-smoke-261026`, vài chục phút một lần là đủ.
- Khi xong, tải kết quả và source vào hai thư mục riêng:

```powershell
kaggle kernels output siinn1706/rclagent-one-trace-gpu-smoke-261026 -p runtime/kaggle-output-v12
kaggle kernels pull siinn1706/rclagent-one-trace-gpu-smoke-261026 -m -p runtime/kaggle-source-v12
```

**Bước 6. Tóm tắt, kiểm private và ghi report.**

```powershell
& $py -X utf8 summarize-repair-run.py 12
C:/Users/Siinn/AppData/Local/Programs/Python/Python312/python.exe check-kaggle-private.py
```

- So hash của `rclagent-kaggle-repair-v12-results.zip` với file `.sha256` của Kaggle.
- Ghi report vào `plans/reports/run-YYMMDD-HHMM-rclagent-kaggle-v12-train-batch-1.md`, theo mẫu report v11. Report gồm: trạng thái từng trace kèm lý do nếu failed, số request, thời gian, R@1/R@3/MRR, tài nguyên, hash và trạng thái private.

**Nếu phiên bị ngắt giữa chừng:**

- Tải kết quả dở dang về.
- Tải ZIP kết quả lên thành một dataset private thứ hai, rồi thêm dataset này vào `dataset_sources` của notebook.
- Chạy lại với **đúng** bundle cũ. Các trace đã có trạng thái cuối sẽ không chạy lại.
- Mỗi lượt chỉ được gắn một bộ kết quả cũ.
- Nếu bundle khác đi, kết quả cũ sẽ không được nhận.

## 6. Năm lô

Danh sách trace đầy đủ nằm ở `train-batches.json`, trong `batches[i].trace_ids`, và ở phụ lục cuối file này. Thời gian là ước lượng từ pilot v11; cột "Phương án chậm" lấy ước lượng nhân 1,25. Mỗi phiên Kaggle tối đa 12 giờ.

| Lô | Trace | Case | Span | Ước lượng | Phương án chậm |
|---:|---:|---:|---:|---:|---:|
| 1 | 45 | 9 | 1.355 | 7,6 giờ | 9,5 giờ |
| 2 | 50 | 10 | 1.400 | 7,9 giờ | 9,9 giờ |
| 3 | 50 | 10 | 1.356 | 7,7 giờ | 9,6 giờ |
| 4 | 50 | 10 | 1.355 | 7,7 giờ | 9,6 giờ |
| 5 | 45 | 9 | 1.067 | 6,1 giờ | 7,6 giờ |

**Các case trong mỗi lô** (sinh từ `train-batches.json`):

- **Lô 1:** `checkoutservice_cpu_1`, `currencyservice_disk_1`, `emailservice_delay_1`, `productcatalogservice_delay_1`, `recommendationservice_cpu_1`, `checkoutservice_cpu_2`, `currencyservice_disk_2`, `emailservice_delay_2`, `productcatalogservice_delay_2`
- **Lô 2:** `recommendationservice_cpu_2`, `checkoutservice_cpu_3`, `currencyservice_disk_3`, `emailservice_delay_3`, `productcatalogservice_delay_3`, `recommendationservice_cpu_3`, `checkoutservice_disk_1`, `currencyservice_loss_1`, `emailservice_socket_1`, `productcatalogservice_disk_1`
- **Lô 3:** `recommendationservice_delay_1`, `checkoutservice_disk_2`, `currencyservice_loss_2`, `emailservice_socket_2`, `productcatalogservice_disk_2`, `recommendationservice_delay_2`, `checkoutservice_disk_3`, `currencyservice_loss_3`, `emailservice_socket_3`, `productcatalogservice_disk_3`
- **Lô 4:** `recommendationservice_delay_3`, `checkoutservice_mem_1`, `currencyservice_mem_1`, `productcatalogservice_mem_1`, `recommendationservice_loss_1`, `checkoutservice_mem_2`, `currencyservice_mem_2`, `productcatalogservice_mem_2`, `recommendationservice_loss_2`, `checkoutservice_mem_3`
- **Lô 5:** `currencyservice_mem_3`, `productcatalogservice_mem_3`, `recommendationservice_loss_3`, `productcatalogservice_socket_1`, `recommendationservice_socket_1`, `productcatalogservice_socket_2`, `recommendationservice_socket_2`, `productcatalogservice_socket_3`, `recommendationservice_socket_3`

Mọi trace của một case nằm chung một lô, và các case được xếp xen kẽ giữa các service. Lô 1–3 có đủ 5 service; lô 4–5 lệch về lỗi mem và socket. Nên chạy theo thứ tự 1 đến 5.

## 7. Rủi ro cần để ý

- **Trần 160 request:** 12 trace từ 40 span trở lên chỉ dư dưới 40 request so với mức tối thiểu. Riêng trace 45 span `2095688a…` dư 24 request, pilot đã dùng hết 9. Trace vượt trần sẽ bị ghi failed. Đó là kết quả hợp lệ, không chạy lại.
- **Deadline 1.800 giây:** trace chậm nhất ước lượng khoảng 890 giây. Trace nào chạm deadline là dấu hiệu server chậm bất thường, nên ghi vào report.
- **Context 16.384:** trace dài nhất tạo prompt 8.445 token. Khó vượt context, nhưng nếu vượt thì guard dừng trace và ghi lý do.
- **Máy mới chưa được thử:** mọi bước đều mới chạy trên máy của chủ dự án, nơi `runtime/` đã có tokenizer cache, các gói cũ và kết quả cũ. Trên máy mới, hãy chạy bước 1–3 cho lô 1 trước, và ghi lại mọi thiếu sót.
- **Dựng gói lớn chưa thử:** `prepare-bundle.py` mới được chạy với tối đa 5 trace. Với 45–50 trace, thời gian, RAM và dung lượng (khoảng 275 MB chưa nén mỗi lô) chưa đo. Hãy xem kết quả dựng lô 1 trước rồi mới dựng các lô sau.
- **Quota GPU:** chưa kiểm. Nếu quota là 30 giờ mỗi tuần, cần khoảng 2 tuần.
- **Không so byte được với các lượt version 8–10:** đổi server làm đổi câu trả lời. Chỉ so trong các lượt từ version 11 trở đi.

## 8. Quyết định còn mở (chủ dự án)

1. **Có dùng lại kết quả v11 cho 5 trace pilot không?** Kế hoạch hiện tại giữ chúng trong các lô để mọi trace thuộc cùng một kiểu bundle. Bỏ chúng đi (`plan-train-batches.py --exclude-pilot`) tiết kiệm khoảng 45 phút.
2. **Chạy bằng tài khoản Kaggle nào?** Có dùng chung slug hiện tại không?
3. **Kết quả 240 trace sẽ được tổng hợp vào đâu?** Hiện chưa có script gộp kết quả nhiều lô.

## Phụ lục: trace của từng lô

### Lô 1 (45 trace)

| Trace | Case | Span |
|---|---|---:|
| `1f31723a0d770d18e9c6109ed4078ffb` | checkoutservice_cpu_1 | 25 |
| `777bc5b5f907d040d455a90a9328ae92` | checkoutservice_cpu_1 | 25 |
| `0d2d45a5bb7da9976cadecc78b367413` | checkoutservice_cpu_1 | 25 |
| `de6a503bf0003321a77f9ca923d0bd87` | checkoutservice_cpu_1 | 25 |
| `9b9f75325a549ca28a4b6b9091b8af48` | checkoutservice_cpu_1 | 35 |
| `57a68940b937d349258a34745558bb03` | currencyservice_disk_1 | 25 |
| `7babb7a2c52a4a910ab657fa6bb01196` | currencyservice_disk_1 | 25 |
| `9e088279802961158eace05dfcb725a3` | currencyservice_disk_1 | 25 |
| `e6b0b3eb453e5566b942dc256f0574a7` | currencyservice_disk_1 | 25 |
| `32c882d5a904e4911ad5acf524632c2a` | currencyservice_disk_1 | 25 |
| `0bd20c44fd8123d525df2eb977a4d79a` | emailservice_delay_1 | 25 |
| `29583dc604a5ce5fdd4daab6bf3144c4` | emailservice_delay_1 | 31 |
| `95087c3121da2d45c7d195999db92a33` | emailservice_delay_1 | 23 |
| `d5f9c2a38a3ed9ee1f393a7c1d88e3e3` | emailservice_delay_1 | 23 |
| `4ac1654a69975b3b8a66831c93ef3217` | emailservice_delay_1 | 23 |
| `08926fcc53e5d68cee17f14d85d3f0e8` | productcatalogservice_delay_1 | 39 |
| `8de3b826557725bf76e0466ab05310f3` | productcatalogservice_delay_1 | 39 |
| `a20f07ee06c7003e4572f25f42bb04da` | productcatalogservice_delay_1 | 39 |
| `5b80462fa3dc971e8a410c4727846278` | productcatalogservice_delay_1 | 41 |
| `52a6ce80ebf0e75b499ab0e0db717e5a` | productcatalogservice_delay_1 | 41 |
| `17b43c3555a9cb5e7520472e442df149` | recommendationservice_cpu_1 | 33 |
| `d896c60f27f2e22c276a793e928c5f89` | recommendationservice_cpu_1 | 25 |
| `83aa62020ca11f652088ad77c526c203` | recommendationservice_cpu_1 | 25 |
| `5cd2b39eab70ada2e47cc729460dedf9` | recommendationservice_cpu_1 | 25 |
| `036148ee6cf62448fc3f9db684152479` | recommendationservice_cpu_1 | 25 |
| `89046194f3473fb1b0febd9081a70f3e` | checkoutservice_cpu_2 | 33 |
| `68791e1f360d910bd01428c3cd9748ef` | checkoutservice_cpu_2 | 33 |
| `72d5fb736b693f9ef7f727c881717946` | checkoutservice_cpu_2 | 37 |
| `a0b125ee66361831f2597c865d3fd6c9` | checkoutservice_cpu_2 | 35 |
| `d6c6ce80cf2b97dc6471ef1924d30237` | checkoutservice_cpu_2 | 39 |
| `60379915de8502ec87083d4921f2da1b` | currencyservice_disk_2 | 25 |
| `68a5d644c2b9e5c2e3c60efd669daec4` | currencyservice_disk_2 | 25 |
| `677278b4e3ef56eccee33c96ec1ec33e` | currencyservice_disk_2 | 25 |
| `64e745911f021e1073e27505b9ee267c` | currencyservice_disk_2 | 25 |
| `e128bd5dcb41875158be4fe64d4c036a` | currencyservice_disk_2 | 25 |
| `c85b7ea20809f41d205ea73d1c730d3b` | emailservice_delay_2 | 31 |
| `f1254007abe2ed044e39b8703ed8d2d0` | emailservice_delay_2 | 23 |
| `29eafef98497da8da62c7c5f66f0c5d3` | emailservice_delay_2 | 25 |
| `a4827710f750885e82b27eda5c48ce36` | emailservice_delay_2 | 25 |
| `d60451bdbcba0f92a8ec84ad57a4c4c0` | emailservice_delay_2 | 37 |
| `1fc9a7403716f8e8706b94792a3940a1` | productcatalogservice_delay_2 | 39 |
| `5c977ab05c8b98780f24a2895de35677` | productcatalogservice_delay_2 | 39 |
| `58450c28319c5bb5fabe08d3bb33aa56` | productcatalogservice_delay_2 | 39 |
| `a978cab5e1d9624c41d241e5db520fb9` | productcatalogservice_delay_2 | 39 |
| `23c2f00f1012d78a4454ff50bda5d910` | productcatalogservice_delay_2 | 39 |

### Lô 2 (50 trace)

| Trace | Case | Span |
|---|---|---:|
| `022d2de14714424c3252fd61a7cc74fe` | recommendationservice_cpu_2 | 25 |
| `4d3ae5b544bee5ce099daa0e33aa3314` | recommendationservice_cpu_2 | 23 |
| `272a47c21e51eefb241d43403e3b2c26` | recommendationservice_cpu_2 | 25 |
| `8889002412632165f4231dd46ec41ad7` | recommendationservice_cpu_2 | 23 |
| `5af7526c6205ca0bc8f5ce44019faebe` | recommendationservice_cpu_2 | 23 |
| `21aae28d0607340358b0563eb462287f` | checkoutservice_cpu_3 | 23 |
| `f661403c673aca15286a500168ed5bae` | checkoutservice_cpu_3 | 23 |
| `eb1ba568f07621555b9de577e1bdf984` | checkoutservice_cpu_3 | 25 |
| `ee90717adfba8b0d102490ab171b9cf8` | checkoutservice_cpu_3 | 25 |
| `e0daa4ab15b1a663fd1a37fdb3d7ce7b` | checkoutservice_cpu_3 | 43 |
| `ad1c27da086fee80da27cbdf90e7b6e8` | currencyservice_disk_3 | 25 |
| `ad74695311a3cafe548e3a737a165ff9` | currencyservice_disk_3 | 25 |
| `eda136bfe6f8a37a8d72dd21f7a78179` | currencyservice_disk_3 | 25 |
| `d84b2e4cc3bf0523c502edbb1f992b37` | currencyservice_disk_3 | 25 |
| `9e5df6ba808e56e617ab05d90526b1c9` | currencyservice_disk_3 | 25 |
| `7330a85217c96a0718a2e10168c1e84d` | emailservice_delay_3 | 25 |
| `c058501be94ddf0f2067e42363efc79a` | emailservice_delay_3 | 25 |
| `30e3c732adf9978eb0814d796e7194a5` | emailservice_delay_3 | 23 |
| `cf3f3e203cf84aaf47b476d07c46f1b1` | emailservice_delay_3 | 23 |
| `87a13f75efe8953d7e571ebda27f448a` | emailservice_delay_3 | 23 |
| `c0b67f23638ea23cbd3d3cd26fbba3cc` | productcatalogservice_delay_3 | 37 |
| `9b9f18e26f1cbe9f37f54ba166004818` | productcatalogservice_delay_3 | 37 |
| `d59461f1a89e292739dd73e19ac9e5be` | productcatalogservice_delay_3 | 37 |
| `333c876ec9a9f85d358634ad8dffb761` | productcatalogservice_delay_3 | 41 |
| `2095688a1eb7e72f9efbd9fad2b36a50` | productcatalogservice_delay_3 | 45 |
| `ec4845a03573b662484d62ae062fce30` | recommendationservice_cpu_3 | 37 |
| `00f6d77b7c0d290fadf61bebfd4683a0` | recommendationservice_cpu_3 | 25 |
| `cf7bab78f2685efd1bdbfab4956718e3` | recommendationservice_cpu_3 | 29 |
| `e320e639c776aaa46a9fe3bd942bed93` | recommendationservice_cpu_3 | 23 |
| `ab060ae181b6490e03366bdc623d48a5` | recommendationservice_cpu_3 | 23 |
| `93e04d3a35b7ed66cb1392247d8861eb` | checkoutservice_disk_1 | 25 |
| `aac08abe0e1d96e6802e7aa584bd612c` | checkoutservice_disk_1 | 25 |
| `e2e93eeb88e389ab20d28c917106e767` | checkoutservice_disk_1 | 25 |
| `4848c5185405d8a288e8af18ef56fac2` | checkoutservice_disk_1 | 25 |
| `947e32e29c0c20ea49583a702268ab47` | checkoutservice_disk_1 | 25 |
| `3467e3d27f5c89ffda6c85800a4c687b` | currencyservice_loss_1 | 38 |
| `5018fe8ee1e61fb6f9e953dc1afa6cc1` | currencyservice_loss_1 | 39 |
| `cd86c132090692758c556f112dab0add` | currencyservice_loss_1 | 21 |
| `1a9f0f5bef36b3ea0f9547f9f3e74533` | currencyservice_loss_1 | 40 |
| `bc7b8f756be41ad226bde6ab381f9659` | currencyservice_loss_1 | 37 |
| `af53588745219a8748c84023344f3c25` | emailservice_socket_1 | 29 |
| `e987d769f042c32f3f1a49cecd83fe6e` | emailservice_socket_1 | 23 |
| `8101bd604281679e0ae6c31e96833d50` | emailservice_socket_1 | 23 |
| `68a86f15cc9dbf60d54c8d8ced8ca859` | emailservice_socket_1 | 25 |
| `80ea9bc7dc4166206df6a04d9026c7a7` | emailservice_socket_1 | 25 |
| `0ac198632dde8cb06c808ba0d37fa248` | productcatalogservice_disk_1 | 39 |
| `23a0c7c41763134ca4b8d0427179e2c5` | productcatalogservice_disk_1 | 25 |
| `66b9b6b271c2460f78529740d14f6b28` | productcatalogservice_disk_1 | 25 |
| `5b8a595ce2cde87dd543a3326ef076c7` | productcatalogservice_disk_1 | 25 |
| `f77110ca410473b01afbb8f0d522380e` | productcatalogservice_disk_1 | 25 |

### Lô 3 (50 trace)

| Trace | Case | Span |
|---|---|---:|
| `de54c25bf4f8aa8e349dbf539f7f8390` | recommendationservice_delay_1 | 23 |
| `1325d08df7793f37c35e0ffa27bc506e` | recommendationservice_delay_1 | 23 |
| `ca7486ba1391a8cd17ca415350d80044` | recommendationservice_delay_1 | 37 |
| `54779d59bfe565287691cac1cca1d263` | recommendationservice_delay_1 | 23 |
| `822b51f20e3a90ae26cb924604dbac8f` | recommendationservice_delay_1 | 23 |
| `5e5f549643251575fcccddff2926d907` | checkoutservice_disk_2 | 29 |
| `210385a3e938aad69916a1d3dc18fc35` | checkoutservice_disk_2 | 25 |
| `39e902d71cdf0cc8520d1cd405ef0293` | checkoutservice_disk_2 | 25 |
| `63e14a5520c2351756c0863cdb26310a` | checkoutservice_disk_2 | 25 |
| `f6d1e7feedada2963169f60023fd23fb` | checkoutservice_disk_2 | 23 |
| `9d3441535ab9cd3f61fc5e718ac60cea` | currencyservice_loss_2 | 25 |
| `84935ab6b9480a64a053f994ff026f48` | currencyservice_loss_2 | 33 |
| `723475c19439577ff01210ac294775be` | currencyservice_loss_2 | 25 |
| `2226d25306281459e1a15f618f128a23` | currencyservice_loss_2 | 25 |
| `5da1db6646563d034e18c3bd123b99a8` | currencyservice_loss_2 | 25 |
| `56daf16467cbd67fac7525edd224faf6` | emailservice_socket_2 | 23 |
| `c603394090ba1fe134efa14ef4851a65` | emailservice_socket_2 | 23 |
| `e930b6432ac53049bbe4e56312dba1e9` | emailservice_socket_2 | 31 |
| `5df3be6fbb3e005d6d36a158f2ed2e98` | emailservice_socket_2 | 23 |
| `0106fe36a11c175481489c289a997961` | emailservice_socket_2 | 23 |
| `52ef289354f1afd36746719a41e9a2a3` | productcatalogservice_disk_2 | 33 |
| `87891002e7b7646bdffe38a693dde8e1` | productcatalogservice_disk_2 | 39 |
| `1e836a08c2cdbdb1e9527e09c1e8d98f` | productcatalogservice_disk_2 | 23 |
| `b33d633b6d67f3c15028618a6bdfbf2c` | productcatalogservice_disk_2 | 39 |
| `71544adfe584e9bbe433eda675fd55bd` | productcatalogservice_disk_2 | 29 |
| `22c11b7d8f9a3657a75daffaf5b77c7a` | recommendationservice_delay_2 | 43 |
| `7ff1d180f92d5d3e9d716898d67993b2` | recommendationservice_delay_2 | 25 |
| `00ea068b86c5d28344634e59e7a528da` | recommendationservice_delay_2 | 25 |
| `585a9a03242e87a88e14dac42d6139b7` | recommendationservice_delay_2 | 23 |
| `f02caf453ac364b1ef76aff378859833` | recommendationservice_delay_2 | 23 |
| `fb4add4eff9d0f6f339dec74cdcc6798` | checkoutservice_disk_3 | 41 |
| `873e0f23425b3480a52ba7ed760759e2` | checkoutservice_disk_3 | 25 |
| `e674a56d8fcf9ea0afbeaee5966aa932` | checkoutservice_disk_3 | 23 |
| `0be1a511a8fe281a34699064fd3fa519` | checkoutservice_disk_3 | 25 |
| `5199690068efdcdef0244ece024d816e` | checkoutservice_disk_3 | 37 |
| `f4a2e4a8eab21aa537aa33da2bc7144d` | currencyservice_loss_3 | 25 |
| `067c320d7c83c28ac1dec6d31a6cc58e` | currencyservice_loss_3 | 25 |
| `f3a7024791cdb084749ed9bb42da98ac` | currencyservice_loss_3 | 25 |
| `51936b6d90cadfb0aa5a07ed183dae9a` | currencyservice_loss_3 | 25 |
| `99f095aeb2571c7f2ee99885e8332c8a` | currencyservice_loss_3 | 25 |
| `3fd2feb960223cf9a3b89248be357f34` | emailservice_socket_3 | 23 |
| `cec9b1a8181f94ca8dd984c07e93b64a` | emailservice_socket_3 | 21 |
| `beb0ae853d590b9e2b2efb4c4b7f3664` | emailservice_socket_3 | 23 |
| `b32833ef9c561718b3a395e9b9837294` | emailservice_socket_3 | 23 |
| `eda7ee8b2db38709b098a3d2921a2506` | emailservice_socket_3 | 23 |
| `6a36dd5205b83509c9b9a7a943aaffc3` | productcatalogservice_disk_3 | 41 |
| `8d2f6d6c33d4b5bd1a9a18087bbeee47` | productcatalogservice_disk_3 | 33 |
| `e0fb9b12a4f06ea37a535f7cf195182b` | productcatalogservice_disk_3 | 33 |
| `6aaff1914455d60cdabb609d0adce09f` | productcatalogservice_disk_3 | 23 |
| `a512f7229150d2678a1998943392c8e8` | productcatalogservice_disk_3 | 23 |

### Lô 4 (50 trace)

| Trace | Case | Span |
|---|---|---:|
| `150d97eb28528230d3a1289154750658` | recommendationservice_delay_3 | 35 |
| `0ea123afc7d6d253fde55a87deba4468` | recommendationservice_delay_3 | 23 |
| `e4a5c277dfbb3d5fd4c534d215607c3e` | recommendationservice_delay_3 | 33 |
| `bafdd3efa42e71c5ed71049b4baf6687` | recommendationservice_delay_3 | 4 |
| `182bfb534ced4f77380465db9e4848fd` | recommendationservice_delay_3 | 41 |
| `5f7a7727f3c44b318a0ff9676d2af7b9` | checkoutservice_mem_1 | 39 |
| `ac83bf3a7a36660d761b1835864bab58` | checkoutservice_mem_1 | 31 |
| `a1055a9f9eb08fc31651f57d0534efe4` | checkoutservice_mem_1 | 35 |
| `6961de52a5bceb20f9253f65c1a73397` | checkoutservice_mem_1 | 33 |
| `480321a4b744b943dd3740c08dff66d3` | checkoutservice_mem_1 | 37 |
| `aea00ff1c4ffedeb51be57741ff2df31` | currencyservice_mem_1 | 25 |
| `7d25d412d07d794e3823686ccd4de3a1` | currencyservice_mem_1 | 25 |
| `8e39f3ee95551f369b1dd4a74b97dccd` | currencyservice_mem_1 | 25 |
| `6deafb2f6d2a921cc661522de603412e` | currencyservice_mem_1 | 25 |
| `a5eb163103b8ce2b5ee3c2aa5d71aa56` | currencyservice_mem_1 | 25 |
| `868e96c5d7f80209d4f5108ac0710342` | productcatalogservice_mem_1 | 33 |
| `5ddd8d0342a39e24b3b82e7abb9601d8` | productcatalogservice_mem_1 | 39 |
| `f6526e739db68628e96673f25da39305` | productcatalogservice_mem_1 | 33 |
| `708585193ff8a4b90a68a6144d89b8af` | productcatalogservice_mem_1 | 41 |
| `cfb8a2c323c40ece4e5ea2c6cc402003` | productcatalogservice_mem_1 | 37 |
| `265e9de6af99e1baef905191619e596d` | recommendationservice_loss_1 | 10 |
| `902028594f0cac6db4f01b8a1eb6e971` | recommendationservice_loss_1 | 10 |
| `0b3307e7063c883d6f6b6070a060c229` | recommendationservice_loss_1 | 10 |
| `669d2290aca6b89ef2e41af6a8d32071` | recommendationservice_loss_1 | 20 |
| `2fb3dd025ae590dd6ae3f5849e85e23a` | recommendationservice_loss_1 | 10 |
| `d3a8ff9275f4a1a62da54ce482f3ccb5` | checkoutservice_mem_2 | 33 |
| `b50bd138553c83cd4cfdb108ab3dc5bf` | checkoutservice_mem_2 | 29 |
| `d18f43cfb16a8a276493f4092e749f9f` | checkoutservice_mem_2 | 35 |
| `5f4c1e613f650a3c04c5949ece5fd280` | checkoutservice_mem_2 | 29 |
| `b1881531ad07ed5f43e481d53d505edb` | checkoutservice_mem_2 | 33 |
| `2e3278be1cf0e8b012b6196b0cb44ef3` | currencyservice_mem_2 | 25 |
| `89d909a46c148ab3abd233151005bcc1` | currencyservice_mem_2 | 25 |
| `0db29b5a3202f3405bd730c6a650c6a3` | currencyservice_mem_2 | 25 |
| `f137a23542c1cf521f1073c1c673c0df` | currencyservice_mem_2 | 25 |
| `8106d0864449a0be000d028dd75e13fa` | currencyservice_mem_2 | 25 |
| `13e5b78c46fa187e7ac1dde98afa75f6` | productcatalogservice_mem_2 | 35 |
| `825fbc5fe611c5caa47bf66ff3dc6be1` | productcatalogservice_mem_2 | 23 |
| `942f9f9724da7342425bf072e61a00e7` | productcatalogservice_mem_2 | 23 |
| `16a8930e1fbfd3f22631677d961a7a2d` | productcatalogservice_mem_2 | 23 |
| `4650c426f373676ef6c44eab33f4f679` | productcatalogservice_mem_2 | 23 |
| `fb39a73ac2f1c2c381ad7a523fb25d79` | recommendationservice_loss_2 | 33 |
| `d3a83c59522d0bb0c9e00d33ce307504` | recommendationservice_loss_2 | 29 |
| `ea700f1d998f128df892fd5f5cada925` | recommendationservice_loss_2 | 12 |
| `c24546079a2384259a0cdc3bde0996e6` | recommendationservice_loss_2 | 16 |
| `0ab9403eaa1a4aeca94d71afd5c15c6f` | recommendationservice_loss_2 | 12 |
| `c35437312f3b4db1ad9969467c4a96ac` | checkoutservice_mem_3 | 37 |
| `7dbfcfd85026c95b1c20b3a20fc17213` | checkoutservice_mem_3 | 29 |
| `f315c392fdadd84d1141a661c7ae27a0` | checkoutservice_mem_3 | 29 |
| `4d9bb8da7dd2498da38988c78c2b35b3` | checkoutservice_mem_3 | 35 |
| `5a964f24c00edc93ffe47c69ef258a11` | checkoutservice_mem_3 | 33 |

### Lô 5 (45 trace)

| Trace | Case | Span |
|---|---|---:|
| `3c6e3aa049c72d43671f649110da812a` | currencyservice_mem_3 | 25 |
| `3b55195f15ebb10851ac35ed0d32c07f` | currencyservice_mem_3 | 25 |
| `027e9e129b645c023d53577313df0b9d` | currencyservice_mem_3 | 25 |
| `1e527c6a967e105118fdc1acdf739e02` | currencyservice_mem_3 | 25 |
| `1605d121c2dffbfba439e90dcf4bc8e6` | currencyservice_mem_3 | 25 |
| `724f0915360a8bb3bcc26bf5ba74c6d1` | productcatalogservice_mem_3 | 23 |
| `c9a7f7aa06b3d6b5c99b207526e4438e` | productcatalogservice_mem_3 | 23 |
| `5d7ee65c1889692dda8d09c7f846b8cb` | productcatalogservice_mem_3 | 23 |
| `eb816900daf83f68172ecb5104e38673` | productcatalogservice_mem_3 | 5 |
| `4e3373113e12acc6263c6f10aac8c09c` | productcatalogservice_mem_3 | 6 |
| `09dedf28a2c929a0e8212ea9f0fdab18` | recommendationservice_loss_3 | 23 |
| `2a70deb73e39f70f12fb51bc7f105852` | recommendationservice_loss_3 | 23 |
| `dd5ca4cc8f439f1206fb07541e8bd299` | recommendationservice_loss_3 | 23 |
| `df1a6aa1fd074b18a7f2f9d9cb2a4234` | recommendationservice_loss_3 | 25 |
| `0acff4b9e6acc18fb3b315a262361e5f` | recommendationservice_loss_3 | 21 |
| `2d64f983643ea9b475ba1962a7d12c9b` | productcatalogservice_socket_1 | 29 |
| `580e2514915baaf2544411ade7093955` | productcatalogservice_socket_1 | 23 |
| `f8c46b276344bc14e77326aa5ad3aea9` | productcatalogservice_socket_1 | 41 |
| `7af08f69435ca4d677165e0f0702e089` | productcatalogservice_socket_1 | 29 |
| `ee50105f978d3747450a7d753519576f` | productcatalogservice_socket_1 | 37 |
| `203c9f76dc9119b696e41cf846f8b917` | recommendationservice_socket_1 | 23 |
| `7bbfa6060d6e01eed1ac0ec2ceead992` | recommendationservice_socket_1 | 23 |
| `214336221eaed0270fe3eb184be560cc` | recommendationservice_socket_1 | 25 |
| `2fc0d7a4ebebe78c947af309c7f20f19` | recommendationservice_socket_1 | 23 |
| `dee50aecdb33d387b9c7012c7ccf8426` | recommendationservice_socket_1 | 23 |
| `a96cf7ac5ed6cfc0e4c5606c65fc46c2` | productcatalogservice_socket_2 | 33 |
| `532d89ab8c538e87fbba761c8d82b869` | productcatalogservice_socket_2 | 23 |
| `c72647e3f9698aeb3665865539d6b16b` | productcatalogservice_socket_2 | 23 |
| `c5f0a77f75cfa74b44385cd21eb0704d` | productcatalogservice_socket_2 | 23 |
| `5bfec818493d973b15cc1f3030b738cc` | productcatalogservice_socket_2 | 23 |
| `8820f31015b14c8f463c6f6fe332b00d` | recommendationservice_socket_2 | 31 |
| `9e495c0d6e0a910394c7bf3d898d1699` | recommendationservice_socket_2 | 23 |
| `5b25a27fa77cc9dede1779df31639af0` | recommendationservice_socket_2 | 29 |
| `b6f992bd9690355248a3c396496da1b8` | recommendationservice_socket_2 | 23 |
| `d16dae1630196a436f143c8eef9e349b` | recommendationservice_socket_2 | 23 |
| `5ce52865a714c78d6d5e706d1298b4ec` | productcatalogservice_socket_3 | 23 |
| `53640f89cd1583f0039412206430daad` | productcatalogservice_socket_3 | 23 |
| `522d7076b6d83326371555fc9e4acc0c` | productcatalogservice_socket_3 | 29 |
| `afd79737ae944156d18e0c38062ba17e` | productcatalogservice_socket_3 | 23 |
| `4c3aabf308c32e254b40ccc0202fe0d1` | productcatalogservice_socket_3 | 23 |
| `06f5b9b0af1d99446662595655b0777d` | recommendationservice_socket_3 | 23 |
| `efefbc5c699b16e7829a2993afaf5864` | recommendationservice_socket_3 | 23 |
| `3753f2a8b337506fffccb4eb515f7530` | recommendationservice_socket_3 | 4 |
| `c8c9750633fcfc76ba2157fcb4cd9610` | recommendationservice_socket_3 | 23 |
| `315e8fe0e54e625234bc270a9937e752` | recommendationservice_socket_3 | 23 |
