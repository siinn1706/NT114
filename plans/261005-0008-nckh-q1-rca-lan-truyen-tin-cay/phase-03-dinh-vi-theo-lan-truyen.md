# Phase 03 — Định vị theo lan truyền (RQ1)

## Mục tiêu
Trả lời câu "lỗi từ server a→b, hay từ b của a→c": tách nơi phát sinh khỏi nơi biểu hiện, và trả về cả đường lan truyền.

## Hướng kỹ thuật (chốt sau Phase 1)
1. **Sinh giả thuyết** từ pre-ranking: top-M dịch vụ ứng viên.
2. **Kiểm giả thuyết dọc cạnh đồ thị gọi:** với mỗi ứng viên s, kiểm các callee của s. Nếu một callee bất thường sớm hơn và
   giải thích được bất thường của s, chuyển giả thuyết xuống callee đó; nếu callee bình thường mà s bất thường, s là ứng viên
   phát sinh. Kiểm bằng các phép đo tất định (thời điểm bắt đầu bất thường, thay đổi độ trễ cạnh, tỉ lệ lỗi cạnh), LLM chỉ
   tổng hợp và phân loại lỗi.
3. **Đầu ra mở rộng:** đường lan truyền `root → … → dịch vụ bị cảnh báo`, mỗi cạnh có evidence id.
4. **Tầng lỗi:** gắn nhãn service / pod-node / code nếu dữ liệu cho phép (RE3 nếu được dùng).

## Đánh giá
- AC@k, Avg@5, MRR so với baseline Phase 2 trên cả 3 hệ thống; tỉ lệ nhầm sang upstream giảm bao nhiêu.
- Chất lượng đường lan truyền: so với đường suy từ trace quanh root cause thật (định nghĩa nhãn đường trong hồ sơ bài; nếu
  RCAEval không có nhãn đường thì nêu rõ cách suy và giới hạn).
- Ablation: bỏ kiểm cạnh; chỉ trace; chỉ metric; đổi M.

## Kiểm tra
- Không gán cho bước kiểm cạnh tác dụng mà luồng dữ liệu không cho phép (quy chuẩn mục 8).
- Thứ tự thời gian bất thường tính từ dữ liệu, không lấy từ nhãn thời điểm tiêm lỗi khi đánh giá online.

## Rủi ro
Một số lỗi (network loss/delay) biểu hiện ở caller nhiều hơn callee; ghi rõ theo từng loại lỗi trong phân tích thay vì
khẳng định chung.
