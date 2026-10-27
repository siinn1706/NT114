# Triển khai ngân sách search_logs và smoke Kaggle version 7 — 2026-10-27

**Kết luận:** ngân sách đã được triển khai và hoạt động đúng trên Kaggle. Ở root span, model lại hỏi `cartservice`; phản hồi được rút gọn từ 124.953 xuống 454 token, và lượt chạy đi tiếp thay vì dừng như version 6. E chạy 60 requests trong 620,7 giây, 27/33 span qua self-state, prompt lớn nhất 1.719 token. Lượt chạy vẫn dừng ở E, nhưng vì một lỗi mới: ở request 60, model gõ timestamp metric `1808475368747` (sai một chữ số so với `1708…`), và guard cửa sổ thời gian chặn. Trên dữ liệu đầy đủ, tool tác giả sẽ trả "No matching records found." cho query này, nên guard đang chặt hơn tác giả. Chưa có kết quả cuối hoặc điểm chấm. Không chạy lại; cần sếp quyết định.

Phạm vi theo duyệt của sếp: phương án C (bậc thang), B = 2.048, chỉ `search_logs`, giữ nguyên dòng thông báo; sửa file và test theo mục 7 của [report thiết kế](design-261027-1155-tool-result-budget.md); một smoke Kaggle version 7 trên `checkoutservice_cpu_2`. Không commit/push. Không đổi upstream, prompt, model, sampling, context, output, retry, số vòng tool, các trần, dữ liệu hay split.

## 1. Thay đổi

- [tool-result-budget.py](../261026-1713-rclagent-tai-hien-toi-thieu/kaggle/tool-result-budget.py): module đã đo, chuyển từ `work/scripts/` sang. Thân hàm giữ nguyên; chỉ sửa dòng đầu docstring. Khác với dự kiến "chỉ giữ hàm của C" trong report thiết kế: em giữ cả ba phương án để code chạy thật trùng code đã đo. Worker chỉ gọi `ladder`. Lượt đo lại 2 trace với module ở chỗ mới cho kết quả trùng hệt lượt đo đầy đủ.
- [smoke-worker.py](../261026-1713-rclagent-tai-hien-toi-thieu/kaggle/smoke-worker.py): `LOG_RESULT_BUDGET = 2048` và `budget_log_result`. Wrapper `get_tool` áp ngân sách cho `search_logs`, sau kiểm `[tool error]`. Event `tool_result` vẫn ghi phản hồi gốc; event mới `tool_result_budget` ghi hash, byte và token trước/sau, dòng thông báo và bản model nhận. Nếu không rút gọn được thì `HarnessStop`.
- `prepare-bundle.py` và `refresh-package.py`: thêm module vào bundle và mục `tool_result_budget` (khai báo sai lệch) vào manifest. `verify-package.py`: kiểm module, kiểm file kiểm CPU khớp hash module/worker trong bundle, kiểm có khai báo sai lệch.
- [check-tool-result-budget.py](../261026-1713-rclagent-tai-hien-toi-thieu/kaggle/check-tool-result-budget.py) → `tool-result-budget-check.json`: chạy đúng đường code của worker với tokenizer đúng revision, trên 12 service × 2 giây × 2 dạng timestamp của gói. Script cũng tái dựng request 3 của version 6 từ event native.
- [test-tool-result-budget.py](../261026-1713-rclagent-tai-hien-toi-thieu/kaggle/test-tool-result-budget.py): 9 test.
- `build-notebook.py` (thêm kết quả v6 và mô tả ngân sách), `summarize-repair-run.py` (tóm tắt event ngân sách), `README.md`. `work/scripts/re2ob-tool-result-budget-impact.py` import module từ `kaggle/`.

## 2. Kiểm CPU

| Kiểm | Kết quả |
|---|---|
| Test ngân sách (`harness-env`) | 9/9 pass. Đột biến tắt ngân sách làm hỏng 6/9 test; 3 test còn lại là test "không được đổi" |
| Harness cũ | 18/18 pass |
| T4 compat | 4/4 pass |
| Kiểm trên gói | 48 query: 40 giữ nguyên byte, 8 rút gọn (`cartservice`, `frontend`), tối đa 454 token, không bỏ dòng nào |
| Request 3 của v6 | tái dựng đúng 126.088 token như guard đã ghi; sau ngân sách còn 1.589 |
| Validator gói | pass, 25 member, bundle `5d617b27…2dfc`, manifest `d2406b55…a5a3` |

Log ở `kaggle/runtime/test-logs/` (`tool-result-budget-*`, `harness-after-budget-0{1,2}`, `t4-after-budget-01`, `refresh-package-v7-01`, `build-notebook-v7-01`, `verify-package-v7-01`). Gói v6 được giữ ở `runtime/bundle-v6` và `runtime/package-v6`.

## 3. Kaggle version 7

Dataset private `siinn1706/rclagent-one-trace-smoke-261026` version 9. Notebook private `siinn1706/rclagent-one-trace-gpu-smoke-261026` version 7, một Tesla T4, context 16.384. Lần upload dataset đầu lỗi do Kaggle CLI 2.2.5 không xử lý đường dẫn tương đối (`kaggle-dataset-version-v7.log`); lần hai, dùng đường dẫn tuyệt đối, thành công. Notebook kiểm hash manifest khớp `d2406b55…`; code notebook tải lại khớp bản đã push.

- **B:** kiểm kernel tương thích pass.
- **D:** pass, 3 requests HTTP 200.
- **E:** 60 requests, tất cả HTTP 200, 0 retry. Tổng 61.435 prompt và 5.954 completion token.
  - Root span hỏi `cartservice` tại `1708475368662` như v6. Phản hồi gốc 124.953 token được gộp thành 4 mẫu, 454 token, không bỏ dòng nào. Đây là lần rút gọn duy nhất trong 32 lần gọi `search_logs`.
  - Prompt lớn nhất 1.719 token; 27/33 span hoàn tất self-state (3 span báo `is_abnormal: true`).
  - Model gọi tool cho productcatalogservice 26 lần, checkoutservice 15, recommendationservice 6, frontendservice 4, currencyservice 4, paymentservice 3, cartservice 2, emailservice 2.
  - Request 60, span `d700ad94e2c085ed`: model gọi `search_logs` đúng timestamp `1708475368747`, nhưng `search_fluctuating_metrics` với `1808475368747`. Guard kiểm tool call ngay khi nhận response và dừng: `Tool request timestamp outside the packaged time window`. Không tool nào của response đó được thực thi.
- **Thời gian và tài nguyên:** E 620,7 giây; từ C tới cleanup 727,2 giây. Trần 160 requests/1.800 giây không bị chạm. RSS cây process đỉnh khoảng 9,23 GB; GPU đỉnh 13.418 MiB.
- **Cleanup:** vLLM 0, tools-synthetic −15, worker-protocol 0, tools-telemetry −15, worker-trace 1. Scorer không chạy; ZIP không có groundtruth.
- **Artifact:** `rclagent-kaggle-repair-v7-results.zip`, SHA256 `5fa45e11379df581c65040ec5e744dda2894a8af536aa84771564f4a833c9244`, khớp file `.sha256` của Kaggle. Tóm tắt ở `kaggle-repair-v7-summary.json`.

## 4. Nguyên nhân lần dừng mới

- Dữ liệu metric/log đầy đủ chỉ nằm trong khoảng giây [1.705.339.822, 1.708.489.861] (`work/scripts/re2ob-full-data-time-range.py`, log `work/logs/re2ob-full-data-time-range-01.log`). Giây `1808475368` nằm sau đó khoảng 3,2 năm. Tool tác giả lọc ±1.200 giây quanh giây đó trên dữ liệu đầy đủ, nên sẽ trả `{"message": "No matching records found."}`. Gói cũng không có hàng nào ở đó, nên tool trên gói trả đúng như vậy.
- Guard hiện tại chỉ cho giây trong cửa sổ của trace, nên chặn cả những query mà gói vẫn trả đúng như dữ liệu đầy đủ. Đây là cùng loại lỗi với E ở version 5: harness chặt hơn contract tác giả. Không phải lỗi ngân sách và không phải lỗi HTTP.
- Ước lượng nếu không có lỗi này: khoảng 10,3 giây mỗi request, cần khoảng 107 requests (73 self-state, 33 consolidation, 1 synthesis), tức khoảng 1.100 giây. Vẫn dưới trần 1.800 giây và 160 requests, nhưng chưa được kiểm.

## 5. Đề xuất sửa (chưa làm)

Cho guard chấp nhận thêm các timestamp mà gói chứng minh được là trả đúng như dữ liệu đầy đủ: cửa sổ endpoint ([t−1.200, t+1.200] cho metric, [t−60, t+60] cho log) nằm hoàn toàn ngoài khoảng thời gian của dữ liệu đầy đủ. Khi đó cả hai nguồn đều rỗng.

- `prepare-bundle.py` ghi khoảng thời gian của dữ liệu đầy đủ vào `selection.json`; `verify-package.py` kiểm lại khoảng này.
- `validate_query` cho qua trong hai trường hợp: giây trong cửa sổ trace (như hiện nay), hoặc cửa sổ endpoint nằm ngoài khoảng dữ liệu đầy đủ. Mọi trường hợp khác vẫn dừng.
- Thêm test hồi quy đúng query của v7 (`1808475368747`), và mở rộng kiểm endpoint equivalence cho các timestamp ngoài khoảng.
- Sau đó chạy smoke version 8, cùng trace, cùng cấu hình.

## Câu hỏi cần sếp quyết định

1. Duyệt sửa guard theo mục 5 rồi chạy smoke Kaggle version 8 trên cùng trace?
2. Hay giữ guard hiện tại, và ghi lần dừng này là kết quả của version 7?
