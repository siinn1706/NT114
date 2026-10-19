# Hồ sơ năng lực Elicit MCP (kiểm tra ngày 2026-10-19)

Ghi lại **những gì thực sự quan sát được** qua MCP trong buổi lập kế hoạch. Không suy ra tính năng
Pro nào từ trang web của Elicit. Mọi điều chưa quan sát được ghi là `CHƯA KIỂM`.

## 1. Truy cập

| Kiểm tra | Kết quả | Ghi chú |
|---|---|---|
| Kết nối MCP `claude_ai_Elicit` | OK | Không có lỗi xác thực |
| `get_usage` (lần 1, trước tìm kiếm) | `hasUsageRemaining: true`, `percentUsed: 0` | Kỳ 2026-10-18T16:00Z → 2026-11-18T16:00Z; `extraUsage: null` |
| `get_usage` (lần 2, sau 4 lần `search_papers`) | `percentUsed: 0` | `search_papers` có vẻ không tiêu hạn mức, hoặc làm tròn về 0. CHƯA KIỂM với report/review |
| `list_library_collections` | 0 collection | Thư viện trống |
| Chặn truy cập | **Không có** | |

Giới hạn quan sát được duy nhất là `percentUsed` (phần trăm, không có đơn vị tuyệt đối). Không có
API trả số lượt còn lại. Trần `maxResults` thực tế theo gói Pro: CHƯA KIỂM (schema cho phép tới
10000, có thể bị gói giới hạn; không có phân trang).

## 2. Công cụ và tham số

| Công cụ | Năng lực đã đọc từ schema | Đã gọi? |
|---|---|---|
| `search_papers` | corpus `elicit` / `pubmed`; chế độ semantic hoặc keyword (Lucene; keyword **không** nhận filter); filter minYear/maxYear, epoch, maxQuartile, include/exclude keywords, hasPdf, typeTags, retracted; trả elicitId, title, authors, year, abstract, doi, venue, citedByCount, journalQuartile, urls, studyTypeTags, fullTextUrl | Có (4 lần) |
| `create_report` | maxSearchPapers ≤ 1000, maxExtractPapers ≤ 80; `isPublic` mặc định false | Không |
| `create_systematic_review` | ≤ 20 truy vấn; tiêu chí sàng lọc abstract và fulltext (≤ 40 mỗi loại); độ sâu `fast`/`thorough` và `useFigures` **do người dùng chọn**; ≤ 40 câu hỏi trích xuất (có thể có lựa chọn); generateReport; không sửa được review đang chạy | Không |
| `get_systematic_review` | Trạng thái, xuất CSV/XLSX | Không |
| `create_agent_session` | Độ sâu nghiên cứu; trên Pro `smartest` bị hạ thành `smart`; tiêu hạn mức | Không |
| `save_library_sources` | 1–100 mục; nhận elicitId, pdfUrls hoặc title+meta; **DOI đơn lẻ bị từ chối** | Không |
| `create_library_collection`, `list_library_collections`, `add_to_library_collection` | Quản lý collection | `list` có |
| `search_library` | Chỉ AND, ≤ 10 term | Không |
| `get_library_source`, `get_library_source_full_text` | Markdown của PDF đã parse; trả mã 404 khi chưa có | Không |
| `get_report`, `search_trials`, chia sẻ/nhập/upload phiên | Có trong danh mục | Không |

Điều chưa biết cần kiểm ở Phase 01 (mỗi điều tốn tối đa một lệnh nhỏ):
- `create_systematic_review` có chạy được trên gói này không và tốn bao nhiêu `percentUsed`.
- `get_library_source_full_text` có trả toàn văn cho arXiv/ACM/IEEE không, hay chỉ cho PDF mở.
- `create_report` với `maxExtractPapers` nhỏ (ví dụ 10) tốn bao nhiêu.

## 3. Tìm kiếm phạm vi (bounded scoping)

Chỉ gửi truy vấn công khai bằng tiếng Anh; không gửi dữ liệu repo, nhãn hay bằng chứng.

| # | Truy vấn (rút gọn) | Chế độ, giới hạn | Phát hiện chính |
|---|---|---|---|
| S1 | Tiêu đề DecompRCA | semantic, nhỏ | Có trong corpus (`ss-292441290`), nhưng doi, venue, fullTextUrl đều null, citedByCount 0 |
| S2 | LLM RCA confidence / calibration / abstention | semantic, minYear 2023, 25 | PACE-LM (arXiv 2309.05833) và LM-PACE (FSE Companion 2024, 10.1145/3663529.3663858): ước lượng độ tin cậy cho RCA sự cố cloud, >100k sự cố Microsoft → **chồng lấn trực tiếp với H1**. Các bài khác: CausalRCA, TriCalRAG, LATS-RCA (2605.03505), PRISM (2601.21359), MRCA (ASE 2024), HCMA (2410.02173), khảo sát agentic AIOps (2605.12729). Có lạc chủ đề (một bài RCA y tế NHS) |
| S3 | Cùng chủ đề, Lucene | keyword, 10 | Độ chính xác thấp (lượng tử, VLM) → keyword cần neo miền chặt |
| S4 | Thu thập bằng chứng có ngân sách | semantic, minYear 2020, 10 | TraceBudget (CISAT 2026, 180 sự cố, dừng theo ngưỡng tin cậy) và VerifyRCA (ICETIS 2026, RCAEval RE2-OB 90 ca, ngân sách B, "giảm kết luận sai mà quá tự tin") → **chồng lấn với H2 và một phần H1**. Cùng nhóm tác giả, URL qua ResearchGate DOI; citedByCount 12 cho bài hội nghị 2026 là bất thường → phải kiểm chất lượng nguồn. Thêm TELEOS (WJARR, thử nghiệm tổng hợp), Astraea (IC2E 2024), MS-Rank (TSC 2020) |

Phản chứng H1 thấy được trong S2 (ngoài miền RCA, cần xác minh): "Reported Confidence in LLMs Tracks
Commitment More Than Correctness" (arXiv 2606.29490); "Entropy Alone is Insufficient for Safe
Selective Prediction" (arXiv 2603.21172); hiệu chỉnh LLM grader (arXiv 2603.29559); conformal
abstention (arXiv 2405.01563); CIC risk control (arXiv 2607.04430); AbstentionBench (NeurIPS 2025);
khảo sát Know Your Limits (TACL, 10.1162/tacl_a_00754).

Các phát hiện trên **chỉ là tín hiệu phạm vi**, chưa qua sàng lọc hay đọc toàn văn; không được
dùng làm kết luận chồng lấn trước Phase 04.

## 3b. Quan sát khi thực thi (2026-10-19, Phase 01–02)

| Kiểm tra | Kết quả |
|---|---|
| Trần `maxResults` của `search_papers` | **300** (400 `invalid_request: maxResults must be at most 300 for your plan tier`) |
| `create_systematic_review` với `useFigures: true` | **Bị từ chối**: `figure_extraction_required` (không có trong gói) |
| `create_systematic_review` (thorough/thorough, 16 truy vấn × 100, 15 câu hỏi trích xuất) | Chạy được; `percentUsed` 0 → 24 % khi đang sàng lọc, rồi **100 %**. Review dừng ở `pausedForInsufficientQuota`, giai đoạn trích xuất: 551 bài qua toàn văn, chỉ 144 có trích xuất |
| `search_papers` sau khi hết hạn mức | **Thất bại** (`insufficient_quota` / `credits_exhausted`), 6 lần lúc 06:29Z. Như vậy `search_papers` *có* bị chặn khi hết hạn mức dù trước đó không làm tăng `percentUsed` |
| `get_library_source_full_text` | Trả toàn văn markdown cho PDF arXiv (PACE-LM); DecompRCA `fullTextStatus` unavailable |
| Export CSV của review | URL S3 pre-signed có token tạm thời; tải bằng script cục bộ, không in URL |
| Đặt lại hạn mức | 2026-11-18T16:00Z (hết kỳ) |

**Chặn truy cập hiện tại:** Elicit không dùng được cho tới 2026-11-18T16:00Z. Vòng gap và phần tìm kiếm
còn lại chạy trên arXiv API, OpenAlex và Crossref (cho phép theo Validation Log V3). Mọi truy vấn ở
[work/search-log.csv](../work/search-log.csv).

## 4. Hệ quả cho thiết kế kế hoạch

1. Semantic search trôi miền → mọi truy vấn phải neo cụm "microservice / cloud incident / AIOps"
   và dùng `excludeKeywords` (ví dụ `patient`, `clinical`, `hospital`, `nursing`).
2. Keyword mode không nhận filter → lọc năm và loại trừ phải làm sau, ở bước khử trùng lặp.
3. Metadata thiếu (DecompRCA) → không dựa vào Elicit cho trạng thái xuất bản; đối chiếu arXiv,
   OpenReview, DBLP, Crossref, trang hội nghị.
4. Hạn mức chỉ thấy dưới dạng phần trăm → ghi `percentUsed` trước và sau mỗi lệnh tốn kém.
