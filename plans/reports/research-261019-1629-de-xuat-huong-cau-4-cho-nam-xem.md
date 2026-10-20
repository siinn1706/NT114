# Đề xuất: đưa câu 4 (thiếu telemetry hay mất khi tóm tắt) vào NT114

Ngày: 19/10/2026, sửa theo review ngày 20/10/2026. Người đề xuất: Trí. **Trạng thái: đề xuất, chờ Nam xem.** File
này không đổi plan, protocol v2, `decisions.md` hay code. Nam đọc rồi quyết có đưa vào plan 261018 hay không.

## Kết luận ngắn

Câu 4 **không nên thay H1**. H1 vẫn là hướng chính; câu 4 chỉ nên là phân tích phụ.

Số liệu hiện có chỉ đo một việc hẹp: bản tóm tắt có **nêu tên** dịch vụ gốc hay không (`named`). Ở điều kiện `full`
trên RCAEval test, tên gốc vắng mặt ở 2/218 bản ghi (`research/04` §2.2). Như vậy, **mất tên gốc** khi tóm tắt hiếm
trên bộ chính. Ba câu hỏi khác vẫn chưa được đo:

- bản tóm tắt có giữ đủ **bằng chứng chẩn đoán** khi đã nêu tên gốc hay không;
- lỗi của LLM phân bố thế nào giữa các tầng `named` (chưa có accuracy);
- các ca mất tên thuộc nhóm A (dữ liệu thô không có tín hiệu) hay nhóm B (có tín hiệu nhưng bộ tóm tắt bỏ).

DecompRCA (NeurIPS 2026) đã tách lỗi retrieval/reranking trên RE1. Theo toàn văn, "retrieval failure" của bài tương
đương với việc gốc không có mặt trong danh sách bằng chứng đưa cho LLM, trên dữ liệu chỉ có metric (§3).

Đề xuất gồm ba phần, cùng là phân tích phụ của H1:

1. **P1**, mô tả: báo cáo kết quả H1 theo tầng `named` và ghép `correct@1` với `named` trên cùng bản ghi.
2. **P2**, mô tả: phân loại A/B/chưa xác định ở các bản ghi mất tên gốc, theo tiêu chí định trước.
3. **P3**, đề xuất: can thiệp oracle thăm dò, tách khỏi kết quả chính, chỉ chạy khi đã được ghi vào protocol v2.

## 1. Câu 4 hỏi gì

Note 16/10, câu 4: lỗi RCA đến từ telemetry bị thiếu, hay từ bằng chứng bị mất trong quá trình tóm tắt? Với một ca
LLM trả lời sai, có thể đặt nó vào một trong các nhóm sau:

| Nhóm | Điều kiện | Ứng với `research/02` (H3) |
|---|---|---|
| A | Bản tóm tắt không nêu tên gốc, và telemetry còn lại sau thao tác của điều kiện không cho tín hiệu của gốc theo tiêu chí P2 | Một phần của `named = false` |
| B | Bản tóm tắt không nêu tên gốc, nhưng telemetry còn lại có tín hiệu của gốc theo tiêu chí P2 | Một phần của `named = false` |
| Chưa xác định | Bản tóm tắt không nêu tên gốc, và tiêu chí P2 không phân loại chắc chắn | Phần còn lại của `named = false` |
| C | Bản tóm tắt nêu tên gốc, LLM vẫn xếp sai | "ranking failure despite the root being named" |

Nhóm C **không** có nghĩa là bằng chứng chẩn đoán đã được giữ đủ. `named = true` chỉ nói có một dòng `- <gốc>:` hoặc
một cạnh trace có gốc ở đầu mút ([`visibility.py:62–65`](https://github.com/siinn1706/NT114/blob/f8112a2f22a7001d736b0aa0579e832981217bde/nt114-rca/nt114-rca/src/rca/visibility.py#L62-L65)).
Bộ tóm tắt chỉ giữ metric có z ≥ 3, tối đa 3 metric mỗi dịch vụ, tối đa 10 dịch vụ mỗi khối, 2 template lỗi mới mỗi
dịch vụ log và 5 cạnh trace ([`evidence.py:153, 213, 218, 240–246, 256, 270`](https://github.com/siinn1706/NT114/blob/f8112a2f22a7001d736b0aa0579e832981217bde/nt114-rca/nt114-rca/src/rca/evidence.py#L218-L246)).
Một ca có thể nêu tên gốc mà vẫn mất tín hiệu quan trọng của gốc. Việc mất bằng chứng ở tầng `named = true` **chưa
được đo**; đề xuất này không đo nó.

`research/02` đã có cột `named` (E) và `in_candidates` (C), nhưng **chưa tách A khỏi B**.

## 2. Số liệu `research/04` (không gọi model, chạy 18–19/10)

### 2.1 Bản tóm tắt ở `full` có nêu tên gốc không

| Bộ dữ liệu | Nêu tên | Không nêu tên |
|---|---|---|
| RCAEval test | 216/218 (99,1 %) | 2 |
| RCAEval val (DEV) | 140/143 (97,9 %) | 3 |
| Nezha test | 80/97 (82,5 %) | 17 |
| RCA100 test | 77/86 (89,5 %) | 9 |
| AIOps2025 test | 298/318 (93,7 %) | 20 |

`in_candidates = 1` ở mọi bản ghi, và không bản ghi nào bị cắt vì giới hạn ký tự (`research/04` §2.1, §2.3). Không
bị cắt vì giới hạn ký tự không có nghĩa là không mất thông tin: việc chọn lọc theo ngưỡng ở trên xảy ra trước đó.

**Điều số liệu này cho phép nói:**
- Ở `full`, mất **tên** gốc là hiếm trên RCAEval test (2/218) và thường gặp hơn ở Nezha (17/97), AIOps2025 (20/318),
  RCA100 (9/86).
- Đơn vị là bản ghi (sự cố × điều kiện). Tỉ lệ trên là tỉ lệ trên **mọi** bản ghi, không phải trên các ca LLM trả lời
  sai. `research/04` §4 ghi rõ chưa đo accuracy.

**Điều số liệu này không cho phép nói:**
- Không nói được bao nhiêu ca sai thuộc nhóm C. Phản ví dụ: 216 ca có tên đều đúng và 2 ca không tên đều sai vẫn cho
  visibility 216/218, nhưng không lỗi nào thuộc C. Hiện chỉ biết: ở `full` trên RCAEval test, **nhiều nhất 2 bản ghi**
  vừa sai vừa không nêu tên gốc. Muốn biết tỉ lệ lỗi theo nhóm, phải làm P1.
- Không nói được bước tóm tắt "làm mất ít bằng chứng". Giả thuyết ban đầu ("bước tóm tắt làm mất nhiều bằng chứng, nhất
  là ở Train Ticket") chỉ bị thu hẹp ở phần **mất tên gốc** trên RCAEval; phần mất bằng chứng khác chưa được kiểm.
- Các tầng không nêu tên đều nhỏ, khoảng tin cậy sẽ rộng (`research/04` §4, ý 5).

### 2.2 Khi bỏ bớt dữ liệu

`no_metric` là điều kiện làm mất tên gốc nhiều nhất so với `full`: RCA100 69/86, AIOps2025 93/304, RCAEval test 42/108,
Nezha 20/97 (`research/04` §2.3). Số này **không** đủ để xếp các ca đó vào nhóm A. `no_metric` chỉ bỏ metric; logs và
traces giữ nguyên ([`ablate.py:45–54`](https://github.com/siinn1706/NT114/blob/f8112a2f22a7001d736b0aa0579e832981217bde/nt114-rca/nt114-rca/src/rca/ablate.py#L45-L54)). Logs/traces còn lại có thể
có tín hiệu của gốc mà bộ tóm tắt không đưa vào, tức nhóm B. `research/04` §2.3 chỉ đếm việc mất tên so với `full`,
không kiểm tín hiệu thô còn lại. Vì vậy A/B ở các ca này **chưa xác định** cho tới khi P2 kiểm telemetry còn lại sau
đúng thao tác của điều kiện.

`blind_root` là thao tác yếu: nó chỉ làm mất tên gốc ở 1/69 ca RCAEval test, và bản tóm tắt giống hệt `full` ở 20/69
ca (`research/04` §4, ý 2).

## 3. Chồng lấn với DecompRCA (đã đối chiếu toàn văn)

Nguồn: bản toàn văn lưu cục bộ `private/fulltext/261019/2609.36686.txt` (arXiv 2609.36686v1; thư mục `private/` bị
`.gitignore`, không có trên GitHub), cùng [báo cáo Elicit](research-261019-tong-quan-elicit-chon-dong-gop-nt114.md) §7,
F-041 đến F-044. Đây là kiểm tra trên bản lưu; không kiểm lại trạng thái phát hành hay artifact trên Internet ngày 20/10.

| Nhận định | Bằng chứng (dòng trong bản toàn văn) |
|---|---|
| Tách top@k = Retrieval@K × Rerank@k; retrieval failure = 1 − Retrieval@K, reranking failure = Retrieval@K − top@k | 438–454 |
| RE1, 125 sự cố mỗi hệ (OB, SS, TT); dữ liệu chỉ gồm cột metric (95, 63, 241 cột); tiền xử lý theo `main-ase.py`; chấm ở mức dịch vụ | 1403–1423 |
| Với LLM reranker (no-DK, K = 15): retrieval failure 0,02 / 0,00 / 0,09, reranking failure 0,10 / 0,13 / 0,26 trên RE1-OB/SS/TT | Bảng 2, 573–636 |
| Mỗi ứng viên là **một dòng** (tên metric, z-score, thời điểm lệch, giá trị trước/sau); danh sách K dòng chính là khối `anomaly_summary` trong prompt | 1249–1261, 1280–1285 |
| LLM được gọi một lần mỗi kịch bản, gpt-oss-120b, n = 3 lần chạy; tên ngoài danh sách bị bỏ | 1300–1311 |
| Không đo confidence hay abstention; "miscalibrated reranker confidence" chỉ được nêu như rủi ro triển khai | 913 |
| Không có điều kiện bỏ modality, không có logs/traces trong RE1 | 1412; không có đoạn nào mô tả thao tác thiếu dữ liệu |

**Hệ quả cho câu 4:**
- Trong pipeline của DecompRCA, `anomaly_summary` chính là tập ứng viên. Vì vậy retrieval failure của bài **tương đương
  với việc gốc không có mặt trong bản tóm tắt** đưa cho LLM. Bài đã đo đúng loại "mất tên gốc" này trên RE1, ở mức
  0,00–0,09.
- Bài không tách nguyên nhân của retrieval failure thành "dữ liệu thô không có tín hiệu" và "có tín hiệu nhưng bộ chọn
  bỏ" (A/B), không có logs/traces hay thao tác thiếu modality, và không đo mức giữ bằng chứng khi gốc đã có mặt.
- Phần khác biệt còn lại vì vậy **hẹp**: A/B trên dữ liệu đa modality và dưới điều kiện thiếu telemetry. Không nên kết
  luận tính mới chỉ từ khác biệt đó. DecompRCA cũng không đo confidence hay abstention, nên không chồng lấn H1.

Câu hỏi cũ "DecompRCA có đo việc bản tóm tắt bỏ sót tên gốc không?" đã có câu trả lời ở trên: có, dưới dạng retrieval
failure trên RE1 chỉ có metric; không, ở mức tách A/B.

## 4. Đề xuất cụ thể (phân tích phụ của H1)

Cả ba phần đều không thuộc họ confirmatory, không đổi pool H1-primary, SESOI 0,05 hay endpoint `gain_exact@0.7`
(`decisions.md`, 19/10). Mọi bảng mang tiền tố `exploratory_` theo phần mở đầu của protocol v2 cho tới khi có
preregistration.

### P1: phân tầng mô tả theo `named`

- Báo cáo mọi contrast của H1 theo tầng `named`, như `research/04` §5 đã yêu cầu. Code đã có:
  [`analyze.py:362, 428–429`](https://github.com/siinn1706/NT114/blob/f8112a2f22a7001d736b0aa0579e832981217bde/nt114-rca/nt114-rca/src/rca/analyze.py#L428-L429) ghép cờ visibility và tạo
  `table_cells_by_named`.
- Ghép `correct@1` với `named` trên cùng sự cố × điều kiện để báo số ca sai ở tầng `named = true` và `named = false`,
  kèm mẫu số. Giữ quy ước trọng số theo injection của protocol v2 §9 và CI cluster bootstrap theo injection.
- Đây là phân tầng mô tả: nó cho biết lỗi rơi vào tầng nào, không xác định nguyên nhân gây lỗi.
- Chi phí: không thêm, dùng lại output của lượt chạy H1.

### P2: phân loại A/B/chưa xác định ở các bản ghi mất tên gốc

**Phạm vi.** Chỉ các bản ghi `named = false` trên test: 48 bản ghi ở `full` (2 + 17 + 9 + 20) và các bản ghi mất tên ở
các điều kiện thiếu dữ liệu. Ví dụ ở `no_metric`, số bản ghi không nêu tên là 42/108 (RCAEval test), 37/97 (Nezha),
78/86 (RCA100) và 112/304 (AIOps2025), tính từ cột `named` của `research/04` §2.3. P2 chỉ trả lời câu hỏi về **mất
tên gốc**. Nó không bao phủ mọi khả năng mất bằng chứng khi tóm tắt, vì không xét tầng `named = true`.

**Tiêu chí vận hành, định trước khi đọc test.**
1. Đầu vào là telemetry **sau đúng thao tác** `ablate.apply` của điều kiện đó, không phải telemetry `full`.
2. Gốc "có tín hiệu" nếu ít nhất một modality còn lại thỏa tiêu chí lỏng hơn ngưỡng của bộ tóm tắt:
   - metric: ít nhất một metric của gốc có robust z ≥ τ_m, với τ_m < 3 (bộ tóm tắt dùng 3), và không áp giới hạn 3
     metric hay 10 dịch vụ;
   - logs: tỉ lệ log lỗi của gốc tăng theo quy tắc của `log_summary`, hoặc có template lỗi mới, không áp giới hạn
     10 dịch vụ hay 2 template;
   - traces: p90 latency hoặc tỉ lệ span lỗi của gốc tăng, hoặc có cạnh gọi với gốc ở đầu mút có tỉ lệ median
     latency > τ_t, với τ_t < 1,5, không áp giới hạn 5 cạnh.
3. Gán nhóm: **B** nếu có tín hiệu ở tiêu chí chặt nhất trong lưới; **A** nếu không modality nào có tín hiệu ở tiêu
   chí lỏng nhất; **chưa xác định** trong mọi trường hợp còn lại, kể cả khi dữ liệu sau thời điểm sự cố quá ngắn,
   khi nhãn ở mức pod/tập dịch vụ không khớp rõ với tên trong telemetry, hoặc khi chỉ có tín hiệu ở mức lỏng.
4. Chọn lưới ngưỡng (τ_m, τ_t) trên DEV (RCAEval val: 3 bản ghi `full` mất tên và các bản ghi điều kiện mất tên),
   ghi lại rồi mới đọc test. Nezha, RCA100 và AIOps2025 không có DEV; dùng nguyên lưới đã định, không chỉnh trên test.

**Cách đọc kết quả.**
- B nghĩa là phép đo của chúng tôi thấy tín hiệu mà bộ tóm tắt không đưa vào. Nó không chứng minh tín hiệu đó đủ để
  LLM trả lời đúng.
- A nghĩa là không có tín hiệu theo phép đo này. Nó không chứng minh telemetry không thể dùng để chẩn đoán.

**Độ bất định.**
- Báo số đếm A/B/chưa xác định kèm mẫu số theo từng bộ dữ liệu × điều kiện; không gộp các bộ thành một ước lượng.
- Báo kết quả trên toàn lưới ngưỡng như phân tích độ nhạy; một nhóm chỉ đổi khi đổi ngưỡng thì được ghi rõ.
- CI cluster bootstrap theo injection (RCA100 có 86 bản ghi từ 70 injection); với tầng rất nhỏ (RCAEval test có 2 bản
  ghi ở `full`) chỉ báo số đếm, không báo tỉ lệ hay kiểm định.

**Chi phí.** Chỉ CPU. Dùng nhãn eval-only để biết dịch vụ gốc, nên chỉ là phân tích, không đưa vào prompt hay phương
pháp.

### P3: can thiệp oracle thăm dò (đề xuất, chưa chạy)

- Ở các bản ghi nhóm B từ P2, thêm dòng của dịch vụ gốc vào bản tóm tắt rồi hỏi lại LLM; đo AC@1 và confidence trước và
  sau.
- `research/02` (H3) ghi rằng muốn khẳng định nhân quả thì cần can thiệp kiểu này, và code chưa có.
- Bản tóm tắt sau can thiệp chứa thông tin từ nhãn, nên đây là arm **oracle**: không phải phương pháp, không vào bảng
  kết quả chính, chỉ báo dưới tiền tố `exploratory_`.
- Cần một arm phân tích mới và GPU; phải được Nam duyệt và ghi vào protocol v2 trước khi viết code hay chạy.
- Quy mô ước tính: một prompt mỗi bản ghi nhóm B (n = 10 mẫu mỗi prompt), nhiều nhất vài trăm prompt.

P1 và P2 không đụng prompt v1, `evidence.py` hay split.

## 5. Rủi ro

- Các tầng nhỏ (2 bản ghi RCAEval test, 9 bản ghi RCA100 ở `full`) cho khoảng tin cậy rất rộng. Kết quả chủ yếu mang
  tính mô tả.
- Nếu P2 cho thấy hầu hết bản ghi mất tên thuộc nhóm A, kết luận chỉ là: trên tầng mất tên, bộ tóm tắt hiếm khi bỏ một
  tín hiệu đo được. Điều đó không nói gì về mất bằng chứng ở tầng `named = true`. Kết quả vẫn có ích cho phần Threats
  to validity của bài H1.
- Tiêu chí P2 phụ thuộc lưới ngưỡng; nếu nhiều bản ghi nằm ở "chưa xác định", P2 không đủ để trả lời câu 4 ngay cả ở
  tầng mất tên.
- Khác biệt so với DecompRCA hẹp (§3); câu 4 khó đứng như một đóng góp riêng.

## Câu hỏi cho Nam

1. Có đưa P1–P3 vào plan 261018 thành phân tích phụ của H1 không, hay chỉ giữ P1?
2. Có cần đo mất bằng chứng ở tầng `named = true` không? Nếu có, cần một định nghĩa riêng (ví dụ so tín hiệu đo được
   của gốc với phần được giữ trong bản tóm tắt), nằm ngoài đề xuất này.
3. Nếu làm P2, lưới ngưỡng chọn trên RCAEval val như §4 có chấp nhận được không, khi ba bộ eval-only không có DEV?
4. Nếu làm P3, đặt arm can thiệp vào protocol v2 ở mục nào để không lẫn với họ confirmatory?
