# Giao thức lọc Q1 (cố định ngày 11/10/2026)

## Nguồn xếp hạng

- SCImago Journal Rank, năm **2025** (năm mới nhất trên https://www.scimagojr.com/journalrank.php ngày 11/10/2026).
- Tệp đầy đủ `journalrank.php?out=xls`: 11.253.130 byte, 32.195 dòng,
  sha256 `6f20399957173a13e3c1729a5fb3b5821844ba75e8d640c8b3040ab19a6f7180`.
- Cách lấy: SCImago chặn tải tự động (Cloudflare 403 với curl và WebFetch). Tệp được tải bằng `fetch` trong Chrome của
  người dùng (đã cho phép) và xử lý trong bộ nhớ trang. Chrome không lưu được tệp xuống đĩa, nên chỉ trích phần cần dùng.
- Phần trích: [sjr-2025-q1-matched.txt](sjr-2025-q1-matched.txt). Mỗi mục có dạng `issn[/issn],SJR,cs` cho mọi tạp chí
  **SJR Best Quartile = Q1** có ISSN khớp ứng viên. `cs = 1` khi tạp chí có ít nhất một chuyên ngành Computer Science đạt Q1.
  Phần trích cho tìm kiếm chính có sha256 `7e308ec9b403a61a65899b84db116589ffeeb15dac96077ebc6ac299fa49e757`; hash này
  được tính trong trình duyệt và khớp với bản ghi xuống đĩa. Phần cho snowball được nối thêm sau đó (27 mục);
  [bản sao lưu trước khi nối](sjr-2025-q1-matched.search.bak) vẫn giữ.
- Các danh mục được tính là "Computer Science": Artificial Intelligence, Computer Networks and Communications, Software,
  Information Systems, Computer Science Applications, Hardware and Architecture, Computational Theory and Mathematics,
  Computer Science (miscellaneous), Computer Vision and Pattern Recognition, Human-Computer Interaction, Signal Processing,
  Theoretical Computer Science, Computer Graphics and Computer-Aided Design.

## Quy tắc

| Mã | Quy tắc |
|---|---|
| D1 | Bài được giữ khi một ISSN của nơi đăng (print hoặc electronic, theo OpenAlex, bỏ gạch, chữ hoa) có trong phần trích, tức Best Quartile 2025 = Q1. Quartile theo năm xuất bản không được kiểm |
| D2 | Hội nghị, arXiv, luận văn không vào corpus (truy vấn OpenAlex lọc `primary_location.source.type:journal`, `type:article\|review`) |
| D3 | IEEE Access (2169-3536) và Scientific Reports (2045-2322) giữ, gắn `q1_weak = 1`, điểm V × 0,5 |
| D4 | Loại khi publisher theo OpenAlex chứa "MDPI" hoặc "Multidisciplinary Digital Publishing" |
| D7 | `from_publication_date:2020-01-01` |
| Đổi tên tạp chí | Chỉ khớp theo ISSN; tạp chí đổi ISSN mà SJR 2025 không còn liệt kê sẽ bị coi là không Q1 |

## Kiểm tra mẫu (đã chạy)

- IEEE TSC (1939-1374), ACM TOSEM (1049-331X), JSS (0164-1212), IEEE TNSM (1932-4537) có trong phần trích ở mức Q1.
- Sensors (1424-8220, MDPI) đạt Q1 trong SJR 2025 nhưng bị loại theo D4. Đây đúng là trường hợp D4 được đặt ra để xử lý.
