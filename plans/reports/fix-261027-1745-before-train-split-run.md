# Sửa các lỗi chặn trước khi chạy tập train

**Kết quả:** cả 6 phase của [plan](../261027-1624-fix-before-train-split-run/plan.md) đã xong. Đường B (harness Kaggle RCLAgent) chạy được nhiều trace, chạy tiếp được sau khi bị ngắt, và ghi nhận trace thất bại rồi chuyển sang trace kế tiếp. Gói pilot 5 trace train đã dựng, đã đối chiếu CPU và đã qua `verify-package`; **chưa chạy GPU**. Đường A (`run_grid`) chạy được với `split_role: train`, và dừng khi split hoặc ma trận điều kiện không khớp build hiện tại. Không đổi thiết lập đóng băng nào. Chưa commit hay push.

## Thay đổi

### Đường B: harness Kaggle

- **Ngân sách theo phản hồi (Q1).** Các `search_logs` trong cùng một phản hồi của model chia đều ngân sách, mỗi kết quả nhận ⌊2.048 / n⌋ token. Khi n = 1 (mọi lượt version 7 và 8) không có byte nào đổi. Test mới cho hai `search_logs` trong một phản hồi: không chia thì tổng là 4.010 token (> 2.048, test đỏ), có chia thì tổng ≤ 2.048.
- **Ladder parse một lần** (`merged_templates`). Output giống byte trên 100 body × 4 mức ngân sách.
- **`harness-requirements.txt`** nay đủ cả transformers, tokenizers và các gói phụ thuộc. Một venv sạch dựng từ file cho đúng danh sách freeze.
- **`KNOWN_SERVICES`** đọc từ `config.py` của upstream, không chép tay.
- **Gom phần chung của hai script scan** vào `work/scripts/re2ob-endpoint-common.py`. Hai script ngắn đi 119 và 116 dòng. Chạy lại trên 450 trace: CSV, `spans/`, `changed-responses.json` và `samples/` giống byte với bản đã commit. Hai file JSON tóm tắt chỉ khác dòng `elapsed_seconds`, vì dòng này ghi thời gian chạy thực tế. Log so sánh: `work/logs/scan-refactor-compare.log`.
- **Batch runner.**
  - Mỗi trace một thư mục `traces/<trace_id>/` trong gói. `prepare-bundle.py` dựng gói vào `runtime/package-NAME`; `refresh-package.py` đưa gói đó lên làm bundle.
  - Mỗi trace có tool server, trần 160 requests và deadline 1.800 giây riêng. `run/progress.json` ghi trạng thái của từng trace.
  - Chạy lại cùng bundle thì bỏ qua trace đã xong. Một trace đang chạy dở thì phần output cũ được cất sang chỗ khác rồi chạy lại. Kết quả cũ có thể gắn làm input của phiên mới. Nếu model server chết, cả lượt dừng.
  - `verify-package.py` kiểm từng gói con, và `summarize-repair-run.py` đọc được lượt theo lô.
  - Tạo lại gói của trace version 8 theo cách mới: cả 9 file giống byte với gói cũ, kể cả `cpu-equivalence.json` với 822 phép so.

### Đường A: `nt114-rca`

- **Retrieval trên train (Q2).** `_store_entries` không còn từ chối query train nằm trong kho. Chính incident và nhóm của query đã bị loại khi tìm kiếm. Với vai test, cấu hình ghi đè cũ vẫn bị chặn.
- **Evidence lạc.** File của incident ngoài tập query được bỏ qua và đếm. File thuộc tập query vẫn phải khớp fingerprint.
- **Ghim build.** `Canon` dừng khi `split.json` hoặc ma trận điều kiện thuộc build khác, kèm lệnh cần chạy (`verify-splits` hoặc `conditions`).
- **Tier B (Q3).** Khi chạy tập train, query chỉ có nhãn node bị loại, đếm, in ra và ghi vào `manifest.json` (`excluded_queries`). Trên dữ liệu thật: rcaeval loại 0 ca, aiops2025 loại 29 ca (còn 112), rca100 loại 17 ca (còn 52). Số query test không đổi.
- **`normalize` một phần** (`--limit` hoặc `--incident`) không chạy đè lên build đầy đủ; phải dùng `--data-home` riêng.
- **AIOps2025.** Một archive ngày có trong `raw/` mà chưa giải nén đầy đủ sẽ làm dừng `normalize`, thay vì để incident của ngày đó thành `natural_absent`. Dữ liệu thật: cả 18 ngày đều đã giải nén và có receipt, nên output không đổi.
- **RCA100.** Đã kiểm dữ liệu thật (chỉ đọc): mọi chuỗi thời gian đều có offset (`+08:00` hoặc `+0800`), nên output thật không phụ thuộc múi giờ. Code nay coi chuỗi thiếu offset là lỗi của incident, thay vì đọc theo múi giờ của máy.
- **LLM parse.**
  - Service lặp trong `ranking` chỉ tính một lần, kể cả với mẫu đã cache.
  - `confidence` không phải số trong khoảng 0–100 làm mẫu đó lỗi parse (`ok=False`), không làm vỡ grid.
  - JSON hợp lệ nhưng sai dạng (mảng, chuỗi, `ranking` không phải list) cũng thành lỗi parse.
  - Schema gửi cho vLLM giữ nguyên, không thêm `uniqueItems`: đổi `schema()` phải tăng `PROMPT_VERSION`, kéo theo đổi mọi khóa cache.
- **`safe_extract`.**
  - Receipt ghi sha256 của archive. Khi chạy tiếp, file đã giải nén phải khớp cả kích thước lẫn sha256 mới được bỏ qua.
  - Receipt cũ, hoặc receipt của archive khác, không được tin: mọi member được giải nén lại.
  - Member tên `.extract.json` bị từ chối, và tên trùng nhau khi bỏ qua hoa/thường cũng vậy.
- **`analyze`** chặn hàng `train` khỏi bảng headline, như đã chặn `val`.
- Mỗi sửa đổi có test đỏ trước khi sửa. Chi tiết phần LLM, extract và analyze: [report của subagent](fullstack-261027-1715-llm-extract-analyze-fixes.md).

### Tài liệu

- `README.md`: trạng thái theo version 8 (A–F đạt, 106 requests); số liệu gói 66.846 dòng metric, 1.747 dòng log, 822 phép so; lịch sử version 5–8.
- `kaggle/README.md`: cách dựng và chạy theo lô, chạy tiếp, ước lượng thời gian, cách chia ngân sách.
- `design-261027-1155-tool-result-budget.md`: phạm vi bảo đảm của ngân sách theo Q1.
- `nt114-rca/docs/data_contract.md`: vai train, `normalize` một phần, archive chưa giải nén, offset RCA100.

## Các kiểm trên revision cuối

| Kiểm | Kết quả |
|---|---|
| `test-kaggle-harness.py` | 29 test OK, exit 0 |
| `test-tool-result-budget.py` | 11 test OK, exit 0 |
| `test-vllm-t4-compat.py` | 4 test OK, exit 0 |
| `check-tool-result-budget.py` | exit 0. Output giống bản phase 1; so với bản đã commit chỉ khác hash module và worker |
| `verify-package.py` trên gói pilot | pass: 5 trace, 130 span, 3.528 phép so endpoint |
| `pytest -m "not realdata"` (nt114-rca) | 447 passed, 56 deselected, exit 0 ([log](../261027-1624-fix-before-train-split-run/logs/pytest-not-realdata.log)) |
| `rca.prep verify-splits` | 16/16 OK, exit 0 ([log](../261027-1624-fix-before-train-split-run/logs/verify-splits.log)) |
| `rca.prep verify-bundle nt114-data-v1-20261014-6fdd9835` | OK, exit 0 ([log](../261027-1624-fix-before-train-split-run/logs/verify-bundle.log)) |
| Script scan sau khi gom phần chung | giống byte, trừ dòng `elapsed_seconds` |

Log của harness nằm trong `kaggle/runtime/test-logs/` (`*-pilot-01.log`, `unit-t4-final.log`). Bộ test `nt114-rca` chạy trong một env tạm dựng từ `requirements-lock.txt`, không dùng `.venv`.

## Gói pilot

| Trace | Ca | Span | Phép so endpoint |
|---|---|---:|---:|
| `2095688a…` | productcatalogservice_delay_3 | 45 | 1.097 |
| `3753f2a8…` | recommendationservice_socket_3 | 4 | 122 |
| `c6033940…` | emailservice_socket_2 | 23 | 578 |
| `1e527c6a…` | currencyservice_mem_3 | 25 | 734 |
| `f6526e73…` | productcatalogservice_mem_1 | 33 | 997 |


Bundle: `rclagent-kaggle-bundle.zip`, 2.422.297 byte, sha256 `bf069dba…3110`. Bản version 8 đã thay thế được sao lưu ngoài repo trước khi promote, và vẫn còn trong git.

**Ước lượng.** Version 8 tốn khoảng 40 giây mỗi span, nên E của pilot (130 span) cần khoảng 90 phút, chưa kể bước cài đặt và nạp model. Trace 45 span ước khoảng 1.820 giây, sát deadline 1.800 giây; nếu vượt, trace đó được ghi `failed` và trần không được nới. Cả 240 trace train ước khoảng 73 giờ T4. Đây là phép ngoại suy từ một trace.

## Giới hạn

- Chưa chạy GPU với batch runner. Batch runner mới được kiểm bằng test CPU và fixture.
- Receipt giải nén thật của AIOps2025 chưa có `archive_sha256`. Lần `prep extract` tới sẽ giải nén lại cả 18 ngày. Dữ liệu không đổi, chỉ tốn thời gian I/O.
- Từ nay, lỗi parse được đánh giá lại trên mọi output đã cache. Mẫu cũ có `confidence` sai dạng sẽ thành lỗi parse nếu được tổng hợp lại.
- `confidence.borda_margin` vẫn đếm trùng trên mẫu cũ đã cache; mẫu mới đã được khử trùng từ lúc parse.
- Kết quả tập train vẫn là adaptation, với backbone 4B, context 16k và ngân sách tool result; không so trực tiếp với Table I.

## Còn chờ sếp

1. Duyệt chạy pilot 5 trace trên Kaggle: tải bundle lên dataset private, rồi chạy notebook private.
2. Commit các thay đổi này lên nhánh `feat/rclagent-harness-budget-guard`; không merge vào main.
3. Không cần tạo lại release dữ liệu canonical: các sửa đổi A6 và A7 không làm đổi output trên dữ liệu thật.
