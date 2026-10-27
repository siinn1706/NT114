# Xuất bản mã và artifact

Mã, test, notebook, tài liệu và các kết quả tổng hợp được lưu ở [GitHub private](https://github.com/siinn1706/NT114). Dữ liệu benchmark và archive chứa telemetry được lưu ở [Hugging Face dataset private](https://huggingface.co/datasets/siinn1706/nt114-rca-data). Hai nơi phục vụ chuyển giao nghiên cứu; đợt xuất bản này không triển khai ứng dụng hoặc khởi chạy model.

## Phạm vi và nguồn đúng

- [Release manifest canonical](../nt114-rca/nt114-rca/releases/nt114-data-v1.json) sở hữu bundle ID, revision, checksum và bản quyền nguồn. Thư mục canonical hiện có giữ nguyên, không được thay bằng gói Kaggle rút gọn.
- [Manifest artifact mới](../plans/261026-2141-publish-latest/artifact-manifest.json) liệt kê chính xác file bổ sung, hash và đường dẫn trên HF. [Receipt HF](../plans/261026-2141-publish-latest/hf-publish-receipt.json) ghi revision thực tế và hash tải ngược.
- [Data card](hugging-face-data-card.md) là nguồn README cho repo dữ liệu; [README dự án](../README.md) là điểm vào cho người đọc mã và kết quả nghiên cứu.
- [Báo cáo Kaggle](../plans/261026-1713-rclagent-tai-hien-toi-thieu/kaggle/repair-report.md) sở hữu trạng thái native. Upload thành công không biến trace bị dừng thành pass.

## Quyền truy cập và cách xác minh

Dùng tài khoản chủ dự án hoặc quyền cộng tác đã được cấp; credential lấy từ đăng nhập lưu sẵn của `gh` và Hugging Face Hub, không ghi token vào file/URL. Repo phải được kiểm `private=true` trước và sau xuất bản. Connector HF hiện phục vụ tra cứu; upload dùng `huggingface_hub.HfApi` qua [publisher](../plans/261026-2141-publish-latest/publish-hf-artifacts.py).

Publisher tạo commit chỉ với danh sách file đã chuẩn bị, khóa vào `parent_commit` đã đọc và tải lại từng file tại revision trả về để đối chiếu SHA256. Nếu HEAD đã đổi, dừng để đối chiếu thay vì ghi đè. GitHub dùng push thông thường sau test/review, không force-push hoặc bypass branch protection. Có thể kiểm lại đích Git bằng `git ls-remote origin refs/heads/main`.

## Tệp được giữ ngoài Git

Runtime/venv, model cache, đầu ra test sinh tự động, crash dump và cache truy vấn không thuộc source snapshot. PDF/toàn văn có bản quyền và credential giữ cục bộ; không đưa vào HF trong đợt này. Bảng phản hồi metadata khảo cứu được đóng archive riêng để giữ provenance mà không lặp hàng trăm MB CSV trong Git. Archive native chứa request/response benchmark chỉ đi vào HF private; nhãn vẫn tách khỏi inference input.

Khi cần đối chiếu các đường dẫn khảo cứu cũ sau khi clone, tải archive metadata ở revision HF trong receipt, kiểm hash rồi giải nén về `source_directory` ghi trong corpus manifest. Raw log/cache cục bộ được loại khỏi Git; các receipt và báo cáo lịch sử không mặc nhiên chứng minh mọi log gốc đã được xuất bản.

Không tự chạy lại benchmark, mở thêm kết quả test, sửa split hoặc cấp quyền công khai khi xuất bản. Mã R-a/IM1 đang tạm hoãn được lưu như snapshot công việc có test; commit không phải quyết định tiếp tục nghiên cứu.

## Khôi phục

Canonical release tiếp tục dùng revision bất biến trong release manifest. Với artifact mới, dùng revision và hash trong receipt để tải đúng bản; không cần di chuyển HEAD về quá khứ. Khi cần hoàn tác tài liệu/file mới, tạo commit đảo ngược có phạm vi sau khi đọc lại HEAD; giữ lịch sử và các archive thất bại, không reset/force-push hoặc xóa repo. Revision HF trước đợt xuất bản được lưu trong receipt và `hf-before.json`.
