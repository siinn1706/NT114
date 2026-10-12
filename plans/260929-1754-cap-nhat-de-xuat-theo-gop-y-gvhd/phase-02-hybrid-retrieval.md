---
phase: 2
title: "Đặc tả Hybrid Retrieval"
status: completed
effort: 2h
---

# Phase 02 — Đặc tả Hybrid Retrieval

## Góp ý gốc
> Cơ chế Hybrid Retrieval: nên xác định rõ kỹ thuật kết hợp giữa tìm kiếm từ khóa và tìm kiếm ngữ nghĩa, và thuật toán liên quan.

## Mục tiêu
Viết mục mới **5.2 Cơ chế Hybrid Retrieval**, trả lời 4 câu hỏi: truy hồi cái gì (corpus), truy vấn là gì,
kết hợp hai kiểu tìm kiếm bằng thuật toán nào, và đánh giá ra sao.

## Nội dung cần đưa vào

**Corpus**
1. Tài liệu vận hành: mô tả kiến trúc Online Boutique, vai trò và phụ thuộc của từng service, runbook cho từng loại lỗi (CPU, memory, disk, socket, delay, loss).
2. Kho sự cố lịch sử: incident card (phase 01) của các sự cố trong tập train, kèm nhãn (service gốc, loại lỗi). Mục đích là few-shot theo kiểu case-based reasoning.
- Chống rò rỉ nhãn: chia dữ liệu theo lần lặp. RE2-OB có 90 sự cố = 5 service × 6 loại lỗi × 3 lần lặp. Có thể dùng 3-fold theo lần lặp, và không bao giờ truy hồi chính sự cố đang được đánh giá.

**Truy vấn.** Văn bản sinh từ incident card: tên service bất thường, metric bất thường, template log lỗi, cạnh trace bất thường.

**Nhánh từ khóa (sparse).** BM25 với k1 = 1.2 và b = 0.75, thư viện `bm25s` hoặc `rank_bm25`. Tokenizer giữ nguyên
tên service, mã lỗi và tên metric. Nhánh này mạnh khi cần khớp chính xác các định danh như `cartservice`, `OOMKilled`, `gRPC UNAVAILABLE`.

**Nhánh ngữ nghĩa (dense).** Embedding đa ngữ hoặc tiếng Anh (ví dụ `bge-m3`, `e5-base-v2`), chuẩn hóa L2 rồi đo cosine similarity.
Chỉ mục FAISS: dùng `IndexFlatIP` vì corpus nhỏ; có thể chuyển sang HNSW nếu corpus lớn lên. Nhánh này mạnh khi triệu chứng được
diễn đạt khác nhau nhưng cùng nghĩa, ví dụ "latency tăng" và "slow response".

**Thuật toán kết hợp (fusion).** So sánh hai cách:
- **Reciprocal Rank Fusion (RRF)**: score(d) = Σ_{r∈{bm25,dense}} 1 / (k + rank_r(d)), với k = 60. Cách này không cần chuẩn hóa điểm và là mặc định.
- **Weighted score fusion**: score(d) = α · norm(s_bm25) + (1 − α) · norm(s_dense), dùng min-max normalization, chọn α ∈ [0,1] bằng grid search trên fold validation.
- Mỗi nhánh lấy top-50, sau khi fuse giữ top-k (k = 5) để đưa vào prompt.

**Reranking (tùy chọn).** Dùng cross-encoder (ví dụ `bge-reranker-base`) để xếp lại top-20 sau fusion. Chỉ giữ bước này nếu nó cải thiện nDCG@5 rõ rệt so với chi phí thêm vào.

**Ablation bắt buộc**
BM25-only / Dense-only / Hybrid-RRF / Hybrid-weighted / Hybrid+rerank, và so với không dùng retrieval (LLM chỉ nhận incident card).
Đo cả chất lượng truy hồi và ảnh hưởng xuống AC@k ở bước localization.

**Độ đo truy hồi.** Recall@k, MRR và nDCG@k (k = 5). Tài liệu được xem là liên quan khi đó là runbook đúng loại lỗi hoặc
sự cố lịch sử có cùng service gốc hoặc cùng loại lỗi. Nhãn liên quan được suy ra tự động từ nhãn dataset. Phần này thay cho câu
"sẽ cụ thể hóa sau" ở mục 6 của Proposal.

## Tệp liên quan
- Đọc: phase-01 (cấu trúc incident card), Proposal mục 5 và 6.

## Các bước
1. Liệt kê corpus thực tế có thể thu thập: README và manifest của Online Boutique, tài liệu RCAEval, runbook tự viết cho 6 loại lỗi.
2. Chốt tham số mặc định và kế hoạch ablation như trên.
3. Viết mục 5.2, có công thức RRF và công thức weighted fusion, kèm một sơ đồ 2 nhánh → fusion → rerank → LLM.

## Kiểm tra
- Nêu tên thuật toán, công thức và tham số cho từng nhánh và cho bước fusion.
- Có chiến lược chống rò rỉ nhãn.

## Rủi ro
- Runbook tự viết có thể làm lộ đáp án nếu viết theo từng service. Runbook chỉ được viết theo loại lỗi, không gắn với service cụ thể.
