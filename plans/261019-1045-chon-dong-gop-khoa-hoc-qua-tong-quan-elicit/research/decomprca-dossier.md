# Hồ sơ DecompRCA (kiểm ngày 2026-10-19)

Bài: "Where Root Cause Analysis Fails: A Retrieval-Reranking Decomposition" — Hada Melino Muhammad, Luan
Pham, Laure Barrière, Sachin Shetty, Leonardo Pulga, Flora Salim. Toàn văn arXiv lưu ở
`private/fulltext/261019/2609.36686.txt` (git ignore). Phát hiện liên quan: F-041 đến F-044 trong
[findings.csv](../work/findings.csv); mâu thuẫn C1, C2 trong [contradictions.csv](../work/contradictions.csv).

## 1. Trạng thái xuất bản

| Nguồn | Kết quả (2026-10-19) |
|---|---|
| https://neurips.cc/virtual/2026/poster/139698 | HTTP 200. Poster NeurIPS 2026, thứ Ba 8/12/2026, 17:00–20:00 AEDT, Hall 1-4; 6 tác giả như trên |
| https://arxiv.org/abs/2609.36686 | HTTP 200. Bản v1 là bản đã đọc toàn văn |
| https://openreview.net/forum?id=A2XdbroU25 | HEAD trả 200, nhưng nội dung là trang xác minh trình duyệt; API trả 403 trong Phase 02. Không đọc được review |

Kết luận: bài đã được nhận ở NeurIPS 2026 (poster); bản đọc là arXiv v1. Tóm tắt trên trang NeurIPS khác
bản arXiv (C1: "78–100 %", "+2 đến +26" và "+9 đến +13" so với "79–100 %", "tới +12"), nên
camera-ready có thể khác v1.

## 2. Artifact

- `https://github.com/cruiseresearchgroup/DecompRCA` trả **404** (HEAD, 06:54Z), và GitHub API
  `repos/cruiseresearchgroup/DecompRCA` cũng trả **404**.
- Tổ chức `cruiseresearchgroup` tồn tại (HTTP 200). Các repo đẩy gần nhất (TSAS26-EvoXXLTraffic
  2026-10-09, XXLTraffic, FASim, …) không có DecompRCA.
- Không tìm thấy mirror, Zenodo hay supplementary trong arXiv v1. Không dựa vào bài mạng xã hội nào.

## 3. Phương pháp

- top@k được tách thành Retrieval@K (nguyên nhân thật có trong pool K ứng viên) × Rerank@k.
  - Retrieval failure = 1 − Retrieval@15.
  - Reranking failure = Retrieval@15 − top@1.
  - Rerank@1 = top@1 / Retrieval@15 (Table 2, dòng 573–636).
- Retriever đa tín hiệu chia một ngân sách K cố định cho magnitude, onset và state-change (Table 1,
  dòng 460–541).
- Reranker là gpt-oss-120b, chạy n = 3 lần ở T = 1.0, không có seed, K = 15.
- Kết quả trên RCAEval RE1:

  | Hệ | BARO top@1 | LLM top@1 (không DK) | Retrieval@15 (+stc) | Lỗi retrieval | Lỗi reranking | Rerank@1 |
  |---|---:|---:|---:|---:|---:|---:|
  | OB | 0.784 | 0.875 ± 0.009 | 0.98 | 0.02 | 0.10 | 0.90 |
  | SS | 0.856 | 0.872 ± 0.024 | 1.00 | 0.00 | 0.13 | 0.87 |
  | TT | 0.560 | 0.653 ± 0.024 | 0.91 | 0.09 | 0.26 | 0.72 |

  Riêng magnitude ở K = 15 đạt 1.00 / 1.00 / 0.98 (Table 1). Retriever +stc mà pipeline dùng thì kém
  hơn trên TT (C2).

## 4. Dữ liệu và độ khớp với NT114

- Dataset của bài: RCAEval RE1-OB, RE1-SS, RE1-TT (mỗi hệ n = 125, mức service; 95, 63 và 241 cột
  metric), cùng WADI (14), SWaT (36) và HVAC (48).
- Tiền xử lý tái lập `main-ase.py` (dòng 1403–1423): bỏ cột thời gian và cột hằng, giữ cột chung,
  đổi `*_mem` từ byte sang MB, giữ nguyên các quantile latency.
- So với NT114, chỉ ở mức metadata công khai (research/05 V8, research/02):

  | Khía cạnh | DecompRCA | NT114 |
  |---|---|---|
  | Số sự cố RE1 | 125 mỗi hệ | 375 (125 mỗi hệ). Bằng số lượng không có nghĩa là khớp |
  | Tiền xử lý | `main-ase.py` (giữ `_latency-50`, `_latency-90` thô) | Port BARO-style theo `main.py` @ `259ea41` |
  | Split | Chấm toàn bộ 125 sự cố mỗi hệ | Grouped split cell-held-out RE1–RE3, vai test/DEV |
  | Tập ứng viên | Tiền tố cột metric | Danh sách ứng viên chuẩn hoá |
  | Granularity | Service, gộp `-db` | Service, gộp `-db` |

- V8 bước 2 (so khớp ID và fingerprint) **không chạy được** vì repo 404. Không gửi inventory của NT114
  ra ngoài.

## 5. Confidence và abstention

Không có. Bài không đo confidence, calibration, risk–coverage hay abstention; ba lần chạy chỉ được báo
dưới dạng mean ± std. Vì vậy DecompRCA **không** chồng lấn H1.

## 6. Hệ quả cho H3

- Ở NT114, `in_candidates = 1` với mọi bản ghi (research/04 dòng 50, 175), tức Retrieval@K = 1 theo
  định nghĩa. Do đó toàn bộ lỗi là lỗi xếp hạng, và phép phân rã không còn gì để tách.
- DecompRCA đã cho thấy điều này trên chính RE1: lỗi retrieval chỉ 0.00–0.09.
- Muốn phép phân rã có ý nghĩa, NT114 phải thêm một nhánh shortlist: shortlist oracle và shortlist bỏ
  root, K = 5 (research/02). Nhánh này dùng nhãn nên chỉ để phân tích.
  - Nó cần thêm một arm mà protocol v2 chưa có. Đây là đề xuất, protocol không bị sửa.
  - Nó không vi phạm bất biến single-LLM (§1), vì shortlist là đầu vào cố định, không do model chọn.
- Kết luận: H3 không thể nhận tính mới về phép phân rã. Phần còn lại (hành vi abstain khi root bị bỏ
  khỏi shortlist) thực chất là một biến thể của H1.

## 7. Hệ quả cho V8 bước 2 (kế hoạch 261018-2300)

Khuyến nghị, không sửa kế hoạch:

1. V8 bước 2 **vẫn bị chặn** cho tới khi repo công khai.
2. Nên đổi tiêu chí từ "khớp ID sự cố" sang "khớp quy trình". Nghĩa là thêm biến thể tiền xử lý
   theo `main-ase.py` (research/05, câu hỏi mở 4), rồi báo BARO top@1 trên cả 125 sự cố mỗi hệ để so
   với 0.784 / 0.856 / 0.560. Cách này kiểm được mà không cần artifact của bài.
3. Mọi số của DecompRCA trong báo cáo NT114 phải gắn nhãn "external reference, not directly comparable",
   như research/02 đã làm.
