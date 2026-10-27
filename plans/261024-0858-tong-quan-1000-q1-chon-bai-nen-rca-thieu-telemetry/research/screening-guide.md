# Hướng dẫn chấm screening T1 (metadata + abstract)

Nguồn quy tắc duy nhất: [protocol.md §6](../protocol.md) (bản đã đóng băng, SHA-256 trong `work/protocol-freeze.json`). File này chỉ quy định cách ghi kết quả; không thêm tiêu chí.

## Đầu vào

Mỗi batch là `work/screen/input/<prefix>-NNN.jsonl`, 50 dòng JSON: `openalex_id, doi, title, venue, year, type, abstract, abstract_source, sjr_cs_categories, q1_weak, topic_gate`. Chỉ dùng nội dung trong dòng đó. Không tra web, không dùng hiểu biết riêng về bài để nâng điểm; chỉ chấm những gì tiêu đề/abstract nói.

## Đầu ra

Một CSV UTF-8 `work/screen/<prefix>-NNN-<screener>.csv`, đúng một dòng cho mỗi `openalex_id` của batch, theo thứ tự đầu vào, header:

```
openalex_id,decision,codes,R1,R2,R3,R4,R5,R6,R_total,read_level,evidence
```

- `decision`: `include` | `exclude` | `needs-review` | `context-survey`.
  - `include` khi I1, I2, I3 cùng đạt và không có mã E nào.
  - `context-survey` cho survey/review (E5).
  - `needs-review` chỉ khi thiếu abstract (E6) hoặc abstract mâu thuẫn tiêu đề; ghi lý do trong `evidence`.
- `codes`: các mã I/E đã áp, nối bằng `|` (ví dụ `I1|I2|I3`, `E1`, `I1|E7`).
- `R1`…`R6`: số nguyên theo bảng mô tả mức §6, chấm cho **mọi** bản ghi, kể cả bản bị loại. `R_total` là tổng.
- `read_level`: `abstract` nếu có abstract, ngược lại `title-only`.
- `evidence`: tối đa 30 từ trích **nguyên văn** từ tiêu đề/abstract làm căn cứ cho R1 (và R3 nếu R3 > 0), đặt trong ngoặc kép; dùng `;` nếu cần hai trích đoạn. Không diễn giải thêm. Bỏ dấu phẩy trong trích đoạn hoặc đặt cả ô trong ngoặc kép CSV.

## Nhắc lại các ranh giới hay gặp (theo §6)

- RCA công nghiệp, cơ khí, điện, y tế, viễn thông truy nhập → E1, kể cả khi dùng LLM.
- Log anomaly detection không định vị/chẩn đoán → E7 (I2 không đạt), R1 = 1.
- RCA mức hệ phân tán/cloud/DB/job nhưng không ở mức service microservice → R1 = 2; RCA root cause service/pod/instance của microservice/cloud-native → R1 = 3.
- “noise/noisy” chung chung không đủ cho R3 = 1.
- Bài lý thuyết diagnosability của đồ thị mạng DC (BCube, DCell…) → E4.
- Không đọc file kết quả của người chấm khác.
