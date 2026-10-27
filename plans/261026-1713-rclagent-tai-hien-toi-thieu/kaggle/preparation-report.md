# Kết quả chuẩn bị Kaggle — 2026-10-26

Đã tạo notebook và gói dữ liệu thực, đã tải lên dataset private, đã gửi notebook private chạy GPU trên Kaggle. Kết quả inference phải đọc riêng từ phiên Kaggle; không suy từ các kiểm CPU dưới đây.

## existing-before-attempt

- Phiên Claude “Tổng quan Q1 bài nền RCA”: `bba26fa1-becf-454d-ae28-afac9c1138f4`; đã đọc các quyết định, phần tóm tắt/trao đổi và artifact liên quan, rồi kiểm trực tiếp owner source. Không đưa transcript vào gói upload.
- Code tác giả ở `F:/Nam/UIT/nt114-paper-artifacts/W7165616276/code`, commit `3052e7a6a9598d984ba1482f3dc41123c8823a99`.
- Các CSV preprocess tác giả và raw case RE2-OB ở thư mục artifact riêng. Chỉ ca đã chọn được chuyển đổi/rút gọn cho lần này; không mở kết quả test cũ hoặc canonical bundle NT114.
- Quyết định tạm dừng H1/IM1/R-a và các thay đổi source cũ được giữ nguyên.

## created-this-attempt

- `rclagent-kaggle-smoke.ipynb`: 4 code cell theo thứ tự Bootstrap, A, B, C–F. C–F được bao cùng lifecycle để dọn server khi lỗi/Interrupt.
- `rclagent-kaggle-bundle.zip`, `.sha256`, `manifest.json`, `cpu-equivalence.json` và `package-validation.json`.
- Các wrapper và script chuẩn bị/kiểm tra trong thư mục này; không vá code upstream. Loader hỗ trợ cả ZIP lẫn dataset Kaggle tự giải nén, gắn manifest hash vào notebook.
- Dataset private: https://www.kaggle.com/datasets/siinn1706/rclagent-one-trace-smoke-261026 . Version 2 giữ nguyên telemetry; chỉ cập nhật loader cho hành vi giải nén thực tế của Kaggle.
- Notebook private GPU: https://www.kaggle.com/code/siinn1706/rclagent-one-trace-gpu-smoke-261026 . Version 1 và 2 dừng trong setup/startup với 0 model request; version 3 thực hiện request model đầu tiên ở D rồi dừng. Mọi version yêu cầu T4, Internet bật, tổng timeout notebook 3.600 giây. Trần riêng lượt RCLAgent luôn là 160 model requests tính cả retry và 1.800 giây.

## verified-this-attempt

- Package có 22 file, 33 span của đúng trace `68791e1f360d910bd01428c3cd9748ef`, 38.048 hàng metric và 0 hàng log sau lọc tác giả. Một dòng groundtruth được tách ở `scoring/`.
- 86 phản hồi endpoint upstream khớp byte-for-byte giữa đầy đủ và rút gọn: 33 search_span, 33 search_traces, 10 search_logs, 10 search_fluctuating_metrics. Đối chiếu cả toàn bộ baseline metric, không chọn theo bất thường. Quét toàn bộ trace/log nguồn để tìm collision/hàng ảnh hưởng; đọc metric dataframe đầy đủ.
- CPU parity dùng pandas 2.2.3 / numpy 2.2.6 giống các pin notebook. Metric được chép nguyên văn từ CSV preprocess của tác giả. Chỉ kiểm provenance độc lập từ raw case cho phép sai số biểu diễn số thực ở rtol=1e-14; equality của dữ liệu thực cấp tool và HTTP response vẫn là exact.
- 14 kiểm tra fixture CPU pass, gồm client gốc, retry 3 attempt, chặn request 161, timeout, schema sai, text-tool fallback, OOM, output bị cắt, context overflow, localhost restriction, miền query, loader dataset đã giải nén, và 33 self-state + 33 consolidation theo thứ tự con trước cha. Không tải weight hoặc chạy LLM trên Windows.
- Source upstream được so với commit, xuất trực tiếp từ Git object. Cache `__pycache__/` có sẵn không được xem là thay đổi source.
- API đọc lại dataset xác nhận `is_private=true`. Metadata notebook tải ngược từ Kaggle xác nhận `is_private=true`, `enable_gpu=true`, `enable_internet=true`, `machine_shape=NvidiaTeslaT4` và đúng dataset source.
- Bundle SHA256 tại notebook version 1: `5744020bbf0810c6a55a1fb37dc6253fb501c780d0ac2f5f463c436a1bf80122`.
- Notebook SHA256 tại version 1: `7be4ad48d335b883aa46298be388f305af8b815fc4d0a24cfa72917deb9feaa8`.
- Bản sửa bootstrap cho notebook version 2: bundle SHA256 `754c5c98f9c3215c615cab1bd5e082f13fa0a2c2f63036492bf29cd730a578d6`, notebook SHA256 `c9fdbb1c0f4e60aadaed78324c2e4da72100476c5f597e50e4b804fb9ba47ca1`. Telemetry, upstream và CPU parity report không đổi.
- Bundle cuối đã thử ở native version 3: SHA256 `ba347b28130ad546389d2b2d34c8fc98f7f6d6887f6e5f53cf3d6df56b052cde`. Notebook bàn giao có chú thích kết quả native: SHA256 `2a9ee7a5409d5d3863a003aa5932fa25ba83378836cfa7206be3846b49846f4d`; toàn bộ code cell khớp nguyên văn source version 3 tải lại từ Kaggle, chỉ bổ sung Markdown về lỗi D.

## Lịch sử attempt và receipt

Các command observation/receipt có thật được giữ ở thư mục private `private/kaggle-command-observations-261026/` trong workspace. Không upload thư mục này.

| Attempt | Exit | Ý nghĩa |
|---|---:|---|
| cpu-env-01, cpu-pins-01 | 0 | Môi trường CPU cô lập cho kiểm chuẩn bị. |
| bundle-equivalence-01 | 1 | Guard ban đầu coi cache Python không tracked là source dirty; sửa guard chỉ xét source tracked và kiểm từng Git object. |
| bundle-equivalence-02 | 1 | Phát hiện sai khác bit số thực do tái xuất CSV; chuyển sang chép nguyên dòng metric từ CSV upstream. |
| bundle-equivalence-03 | 1 | So provenance raw dataframe còn empty string với CSV đã parse thành NaN; chuẩn hóa phép so provenance đúng semantics đọc CSV. |
| bundle-equivalence-04 | 0 | Exact baseline và 86 endpoint response parity pass; raw case hash trước/sau không đổi. |
| harness-tests-01, harness-tests-02 | 0 | 13 test fixture pass. |
| notebook-build-01, package-validation-01 | 0 | Gói ban đầu hợp lệ. |
| kaggle-dataset-create-01 | 0 | Tạo dataset private; quan sát Kaggle tự giải nén ZIP. |
| package-refresh-01, notebook-build-02 | 0 | Ghim manifest hash và loader cho expanded input; telemetry/upstream/parity report byte-identical. |
| harness-tests-03, package-validation-02 | 0 | 14 test và gói cuối pass. |
| kaggle-dataset-version-02 | 0 | Tải wrapper đã sửa vào dataset private version 2. |
| kaggle-gpu-run-01 | 0 | Kaggle chấp nhận tạo và chạy notebook version 1; exit lệnh gửi không chứng minh inference pass. |
| kaggle-live-log-01 | 0 | Log thật xác nhận version 1 dừng ở B/ensurepip, chưa có model request. |
| package-refresh-02, notebook-build-03, package-validation-03 | 0 | Sửa bootstrap bằng bare venv + pip --python; kiểm hash/syntax pass. |
| kaggle-dataset-version-03, kaggle-setup-resume-02 | 0 | Dataset version 3, notebook version 2; tiếp tục setup trước inference, cùng model và các trần. |

Live log reader `kaggle-live-log-02` được giới hạn 45 giây: `timeout-unknown`, exit null, owned process group đã đóng. Đây là kết thúc cửa sổ đọc log, không phải timeout hoặc dừng phiên Kaggle. Không tạo receipt v2 giả cho lần đọc này.

Các attempt sau được giữ ở `command-receipts.json`: log reader 03 cũng timeout-unknown trong cửa sổ đọc; reader 04 và 05 có exit 1 và đã đóng process group. Reader 05 gặp thêm lỗi encoding charmap của Windows khi in live log; gói output native tải qua API vẫn có đủ log. Các lệnh refresh/build/validate tiếp theo exit 0. `native-result-verification-01` exit 0 xác minh ZIP native, 1 request tổng hợp/0 request trace, token usage null và exit status của mọi PID root. `notebook-annotate-native-01` và `final-package-validation-01` exit 0, xác minh notebook có ghi chú nhưng code không đổi sau thử nghiệm. Không nâng native D thành pass từ các exit 0 của validator.

Các lần gọi shell ban đầu trong sandbox và công cụ browser/node_repl thất bại với `CreateProcessSecurityEnvironment`, HRESULT `0x80070005`. Không sửa thiết lập bảo mật. Dùng đường CLI Kaggle có sẵn, xác nhận được quyền truy cập bằng API trước khi upload.

## unverified tại thời điểm gửi notebook

- GPU/driver/VRAM thực được cấp, cài dependency Linux và download/nạp model trên Kaggle.
- Gate D tool-calling thật, kết quả chạy một trace, số request/token và RAM/VRAM thực tế.
- Dọn process trên Kaggle được kiểm tĩnh; kiểm native phải dựa vào process log của lần chạy. Đỉnh tài nguyên là lấy mẫu, không phải CUDA allocator peak tuyệt đối.
- Không có kết luận accuracy, Table I, H1, novelty hoặc hiệu quả backbone từ fixture. Kết quả Kaggle được ghi tiếp trong `kaggle-run-report.md`.

### Cập nhật sau native version 3

A/B/C đã kiểm thật và qua; D thất bại tại request tổng hợp đầu tiên vì Triton attention kernel cần shared memory 98.304 byte, phần cứng T4 giới hạn 65.536 byte. D có 1 model request, E có 0; không chấm. Gói log đã xuất và các process theo dõi đã dừng. Không chạy lại inference sau lỗi D. Các phần chưa qua D/E vẫn unverified; chi tiết/đỉnh tài nguyên/elapsed/exit ở `kaggle-run-report.md` và `kaggle-native-summary.json`.

## Review có phạm vi

Đã review toàn bộ các file mới và hợp đồng gọi tương ứng trong upstream `coordinator.py`, `llm.py`, `tools_gpt.py`, `tool_server.py`, preprocess và scorer, bằng skill `nckh-code-review` trong cùng phiên. Không tuyên bố review độc lập của con người hoặc model thứ hai. Đã sửa đường nhận ZIP bị Kaggle giải nén, đếm usage cả khi response không hợp lệ, chặn telemetry HTTP lỗi, và giữ cleanup cho các executor/process được sở hữu. Không còn finding chưa xử lý trong phạm vi kiểm tĩnh/fixture; native Kaggle vẫn là gate riêng.

## Lượt sửa tiếp theo bằng ak-fix

Đã sửa lỗi shared memory của vLLM trên T4 bằng patch tile có kiểm hash; source RCLAgent bất biến. Bản hiện tại có 24 member, telemetry/upstream/CPU parity report không đổi. 4 kiểm patch/cache + 14 kiểm harness pass; 15 kiểm số học GPU native pass. Regression helper tạo cache ở version 4 đã được chứng minh và sửa.

Native version 5 qua D với 3 requests. E dừng sau 2 requests vì model hỏi cartservice ngoài trace/domain đóng gói; chưa có kết quả cuối hoặc chấm. Không biến lần dừng thành pass và không mở rộng dữ liệu/prompt/tool để chạy lại. Mọi process sở hữu đã dừng. Notebook được thêm ghi chú kết quả, code cell vẫn khớp source version 5 tải lại từ Kaggle; `package-validation.json` giữ hash hiện tại. Chi tiết và các archive thất bại ở [repair-report.md](repair-report.md).
