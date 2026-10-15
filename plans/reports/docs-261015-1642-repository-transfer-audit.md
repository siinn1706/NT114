# Kiểm tra repository trước khi chuyển máy

Ngày kiểm tra: 2026-10-15, Asia/Saigon. Đây là snapshot bàn giao, không phải chứng nhận Linux/GPU hay kết quả nghiên cứu.

## Phạm vi và kết luận

Đã đọc runbook, release manifest, hợp đồng dữ liệu, cấu hình và entry point của pipeline, kế hoạch LLM/Jev và training strategy. Chỉ cập nhật tài liệu; không thay đổi code, dữ liệu, quyền truy cập, model, kết quả hay trạng thái các gate.

- Agent bắt đầu tại [llms.txt](../../llms.txt); lệnh máy mới thuộc [GPU deployment](../../nt114-rca/nt114-rca/docs/gpu_deployment.md).
- GitHub và Hugging Face phục vụ hai phạm vi khác nhau: source trên GitHub; dữ liệu chuẩn hóa trên HF. HF không phải bản mirror GitHub.
- Fine-tuning chưa có exporter/trainer; chỉ là phần mở rộng QLoRA sau các gate trong [training strategy](../261015-0047-nt114-rca-llm-jev-research-and-implementation/design/training-strategy.md). Inference/DEV readiness không đồng nghĩa training readiness.

## GitHub

Kiểm tra trực tiếp bằng `gh repo view` và `git ls-remote`, không chỉ dựa vào remote-tracking branch local:

- Repository `siinn1706/NT114` private, default branch `main`.
- Trước thay đổi tài liệu, local HEAD và remote `refs/heads/main` cùng là `924f5b1113583f0d73b32213f95660ba7056207d`.
- Working tree không có thay đổi tracked hoặc file untracked cần bàn giao. Git cảnh báo không đọc được `.pytest_cache/`; đây là cache local, không phải source hay dữ liệu phát hành.
- Commit bàn giao chứa file này và tài liệu liên quan được định danh bằng Git history; trạng thái remote sau push được xác nhận riêng, không tự ghi SHA của chính commit vào nội dung.

## Hugging Face

Đối chiếu trực tiếp `HfApi.repo_info(..., repo_type="dataset", files_metadata=True)` với [release manifest](../../nt114-rca/nt114-rca/releases/nt114-data-v1.json), manifest checksum và bytes local:

| Mục | Kết quả |
|---|---|
| Dataset | `siinn1706/nt114-rca-data`, vẫn private |
| Revision | `c5c4a6dc455cac5d0545b98d8d40266b2bbdaa05`, đúng release manifest |
| Bundle | `nt114-data-v1-20261014-6fdd9835` |
| File bundle local đúng SHA-256 | 3.265 / 3.265, gồm `bundle.json` và `MANIFEST.sha256` |
| File HF khớp local | 3.098 theo LFS SHA-256; 167 theo Git blob SHA-1 và kích thước |
| File thiếu hoặc thừa trên HF trong thư mục bundle | 0 |
| Dữ liệu hiện tại so với tập file `parts/` | Không thiếu/thừa; 3.250 khớp byte, 4 chỉ khác xuống dòng |

Bốn file khác byte đều bằng nhau sau chuẩn hóa CRLF thành LF:

- `manifests/checksums-levels.tsv`
- `provenance/_aiops-upstream-file-metadata-20261014.json`
- `provenance/evidence/lemma-rca-github-io-20261014.html`
- `provenance/evidence/lemmarca-info-expired-20261014.html`

Do đó không có nội dung dữ liệu mới cần upload và không thay đổi bundle bất biến. Đây là kiểm tra byte local cộng object-hash metadata từ HF, không phải tải lại toàn bộ 10,67 GB để hash lại phía client. Raw data, work, output/cache, model weights, venv và tài liệu private ngoài bundle không thuộc phạm vi đồng bộ này.

## Kiểm tra thực thi

- `rca.prep status` đọc đủ bốn canonical builds từ bundle bằng code hiện tại.
- `rca.prep verify-splits` xác nhận 16/16 split hợp lệ trên bundle.
- Chạy chọn lọc `tests/test_bundle.py`, `tests/test_feasibility.py`, `tests/test_pipeline.py`: sandbox ban đầu chặn pytest tạo khóa ở thư mục tạm; đã chạy lại với quyền phù hợp. Kết quả lần chạy lại: 29 passed, 1 failed.
- Test thất bại là `test_run_end_to_end_with_fake_server`: Bash mặc định là Windows WSL launcher, log báo `execvpe(/bin/bash) failed: No such file or directory`. Đây chưa phải bằng chứng lỗi GPU hoặc lỗi model.
- Đã chạy lại riêng test đó với Git Bash cài sẵn, chỉ thay `PATH` của process: 1 passed. Như vậy 30 test chọn lọc đã pass qua hai lượt; không sửa code hay bỏ assertion. Kết quả này không thay thế Linux/GPU gate.
- `rca.run_grid` và `rca.decide` dùng CLI positional, không hỗ trợ `--help`. `rca.analyze --help` cần stdout UTF-8 trên Windows; lệnh trong runbook dành cho Linux/Bash.
- Kiểm tra 33 liên kết local trong ba tài liệu: đều tồn tại; `llms.txt` có H1, blockquote và mục Optional cuối cùng. `git diff --check` không có lỗi khoảng trắng.
- Chưa chạy đầy đủ test suite, Linux portability, live GPU/model, TypeSafe Jev, main experiments hoặc fine-tuning trong lượt bàn giao.

## Các sửa chữa tài liệu

- Tạo một entry point `llms.txt` theo cấu trúc llms.txt, chọn lọc các nguồn trong repository thay vì gom private/raw files.
- Runbook clone `main`, không còn yêu cầu nhánh feature cũ; tải HF bằng revision và bundle path chính xác.
- Giữ worktree tại commit tạo bundle cho portability, kiểm tra code hiện tại riêng; bật `pipefail` để lỗi portability không bị `tee` che mất.
- Thay lời hứa chạy `realdata` trên máy chỉ có bundle bằng canonical smoke có sẵn. `tests/conftest.py` cố định `REAL_DATA` ở `data/`, và raw-parity cần raw/work không được chuyển trong bundle. Skip không được coi là pass dữ liệu.
- Giữ nguyên các quyết định nghiên cứu, staged model download, giới hạn chia sẻ dữ liệu và điều kiện fine-tuning.

## Còn phải xác nhận trên máy mới

Linux portability tại commit dữ liệu; GPU/driver/CUDA và serving dependencies; feasibility và DEV; TypeSafe access/model response/rate limit; các gate dữ liệu/nghiên cứu còn mở trong decision log. Các điều kiện này không được đánh dấu hoàn tất bởi commit tài liệu.
