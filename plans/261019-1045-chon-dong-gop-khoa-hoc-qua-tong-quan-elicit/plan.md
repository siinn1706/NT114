---
title: "NT114: chọn đóng góp khoa học qua tổng quan tài liệu chuyên sâu bằng Elicit MCP"
description: "Kế hoạch chỉ nghiên cứu: tổng quan có hệ thống, tái lập được, để thách thức H1 (abstention theo độ tin cậy ở cùng coverage) và so với H2 (thu thập bằng chứng có ngân sách) và H3 (lỗi sinh ứng viên so với xếp hạng), rồi chọn đóng góp có căn cứ."
status: completed-with-open-items
priority: P1
effort: 6-9 ngày-người, 0 GPU, 0 lần chạy model thật
branch: main
tags: [research, literature-review, elicit, novelty, rca, selective-prediction]
blockedBy: []
blocks: ["protocol-v2 §9.5 confirmatory family (open slot)", "chọn hướng H1/H2/H3 trong research/02"]
created: 2026-10-19
---

# Chọn đóng góp khoa học của NT114 qua tổng quan tài liệu bằng Elicit MCP

## 1. Kết quả mong muốn

Một báo cáo Markdown **duy nhất, chi tiết**:
`plans/reports/research-261019-tong-quan-elicit-chon-dong-gop-nt114.md`. Báo cáo trả lời, với bằng
chứng truy được:

1. H1 đã bị làm chưa, làm đến đâu, và có phản chứng nào khiến H1 yếu hoặc vô ích?
2. H2 và H3 so với H1 về tính mới, tương thích protocol v2, cỡ mẫu độc lập, power, công sức và
   số thí nghiệm tối thiểu.
3. Khuyến nghị một hướng (hoặc "không hướng nào đủ mới") kèm điều kiện có thể làm đảo khuyến nghị.

Kế hoạch **không** giả định hướng nào là mới. Câu hỏi mặc định là: "Đã có ai làm việc này chưa?"

## 2. Phạm vi và ràng buộc

**Trong phạm vi:** tìm kiếm, sàng lọc, đọc toàn văn, trích xuất, snowballing, tổng hợp, vòng gap
cuối và báo cáo. Nguồn: tạp chí, hội nghị, preprint (ghi trạng thái xuất bản), artifact chính thức
(repo, dataset, model card, trang benchmark).

**Ngoài phạm vi (cấm):**
- Sửa source code, `evidence.py`, `llm.py`, `splits.py`, `score.py`, adapter, evidence, split,
  prompt v1, protocol v2, `decisions.md` hay bất kỳ input đã đóng băng nào.
- Chạy model thật, dùng GPU, commit hay push.
- Gửi tới Elicit bất cứ thứ gì không phải truy vấn nghiên cứu công khai: không gửi dữ liệu repo,
  nhãn, bằng chứng, ID sự cố, kết quả đo nội bộ, hay toàn văn trong `private/fulltext/`.
- Đặt `isPublic: true` cho report, hay tạo share link.
- Coi bài mạng xã hội, blog, video là bằng chứng chính. Chúng chỉ là tín hiệu yếu dẫn tới nguồn gốc.

**Nơi ghi file:** chỉ trong thư mục kế hoạch này (`work/`, `research/`) và báo cáo cuối ở
`plans/reports/`. Toàn văn tải về (nếu có) để trong `private/fulltext/261019/` (đã được `.gitignore`
dòng 2 bỏ qua); **không** để toàn văn trong thư mục kế hoạch.

## 3. Đầu vào đã đọc

| Đầu vào | Dùng để |
|---|---|
| [llms.txt](../../llms.txt) | Bản đồ repo hiện tại, kiến trúc một LLM |
| [decisions.md](../261018-2300-single-llm-simplification-and-evaluation-hardening/decisions.md) | Họ confirmatory còn mở (dòng 22) |
| [protocol-v2.md](../261018-2300-single-llm-simplification-and-evaluation-hardening/design/protocol-v2.md) | Endpoint cố định; giả thuyết và MDE là ô trống (dòng 10–11, 185–186); MDE ở dòng 129 |
| [research/02](../../research/02_research_directions.md) | H1 (dòng 37–110), H2 (112), H3 (183), câu hỏi mở (355) |
| [research/03](../../research/03_elicit_search_pack.md) | RQ1–RQ5, từ khoá, schema trích xuất, quy tắc "overlap exists" (dòng 178–180) |
| [research/04](../../research/04_evidence_visibility_results.md) | `in_candidates = 1` mọi bản ghi (dòng 50, 175) → H3 thành bài toán xếp hạng nếu không thêm nhánh shortlist |
| [research/05](../../research/05_evidence_instrument_audit.md) | Manipulation check yếu của `blind_root`/`blind_nonroot`; DecompRCA 404 (dòng 275) |
| [research/06](../../research/06_statistics_validation.md) | MDE: RCAEval 0.10, giao 52 sự cố 0.18, Nezha 0.14, RCA100 0.16, AIOps2025 0.08 (20 % discordance, dòng 74–109) |
| [Tổng quan Q1 trước](../261011-1345-aiops-q1-literature-gap/plan.md) | Corpus hạt giống (601 bài Q1, 47 toàn văn, 32 thẻ ý tưởng), gồm bài nền P18, P31, P42, P50; chỉ có tạp chí Q1, hội nghị/arXiv chỉ dùng để phản bác |

Bản tóm tắt ChatGPT **không** dùng làm đầu vào (quyết định của chủ dự án, xem Validation Log):
codebase và các file research/ là nguồn chính.
| [Hồ sơ năng lực Elicit](research/elicit-mcp-capability-record.md) | Công cụ, giới hạn, kết quả tìm phạm vi |

## 4. Giả thuyết cần thách thức

| ID | Phát biểu (dạng có thể bác bỏ) | Điều sẽ làm hướng này **mất tính mới** | Điều sẽ làm hướng này **vô ích** |
|---|---|---|---|
| **H1** (dẫn đầu) | Dưới telemetry bị thiếu có kiểm soát, abstention theo độ tin cậy của chính LLM giảm tỉ lệ chẩn đoán sai-mà-tự-tin ở **cùng coverage** so với baseline đơn giản (max-z B1, vote share, verbal) | Một bài peer-reviewed đã đo selective risk/AURC hoặc risk ở coverage cố định cho LLM-RCA dưới cắt modality có kiểm soát | Bằng chứng mạnh rằng confidence của LLM không phân biệt đúng/sai (AUROC ≈ 0.5) trong RCA hoặc tác vụ gần, hoặc mọi lợi ích biến mất khi so cùng coverage |
| **H2** | Thu thập bằng chứng có ngân sách (chọn modality/công cụ tiếp theo) giữ độ chính xác với ít chi phí hơn | TraceBudget, VerifyRCA hoặc tương đương đã làm trên benchmark công khai | Chi phí thu thập không phải nút thắt trong benchmark offline |
| **H3** | Phân rã lỗi thành sinh ứng viên và xếp hạng giải thích phần lớn lỗi | DecompRCA đã làm đúng điều này | `in_candidates = 1` khiến H3 suy biến thành xếp hạng nếu không thêm nhánh shortlist (research/04 dòng 175) |

## 5. Quy tắc quyết định

Lấy từ research/03 dòng 178–180 và mở rộng:

- **"Chồng lấn có"**: ≥ 1 bài **peer-reviewed** có relevance 2 với kết quả định lượng so sánh được,
  đã xác minh toàn văn. Preprint relevance 2 → "chồng lấn có khả năng", phải nêu trong báo cáo.
- **"Chưa thấy chồng lấn"** chỉ được phát biểu sau khi qua đủ: tìm chính, snowballing hai chiều
  và vòng gap cuối. Luôn kèm câu "vắng mặt trong tìm kiếm không chứng minh tính mới".
- **Phản chứng H1** được tìm chủ động: mỗi luận điểm ủng hộ H1 phải có ít nhất một truy vấn
  ngược chiều được ghi lại.
- **Khẳng định đơn nguồn có hệ quả** (một nguồn duy nhất mà nếu sai sẽ đổi khuyến nghị) phải được
  kiểm lại ở Phase 07 hoặc gắn nhãn `ĐƠN-NGUỒN` trong báo cáo.

## 6. Schema bắt buộc cho mọi phát hiện

Mọi phát hiện (dòng trong `work/findings.csv` và mọi khẳng định trong báo cáo) phải có:

| Trường | Ý nghĩa |
|---|---|
| `finding_id` | ID ổn định |
| `source_url` | URL nguồn gốc (DOI, arXiv abs, OpenReview, repo chính thức). Không dùng URL của Elicit làm nguồn duy nhất |
| `pub_status` | `journal` / `conference` / `workshop` / `preprint` / `artifact` / `weak-signal`; kèm venue, năm, ngày kiểm |
| `claim` | Câu khẳng định cụ thể mà nguồn hỗ trợ |
| `evidence_location` | Mục, bảng, hình, trang hoặc dòng (ví dụ "Table 3, p. 7"); `abstract-only` nếu chưa đọc toàn văn |
| `verified_full_text` | `yes` / `no` / `unavailable` |
| `uncertainty` | `low` / `medium` / `high` + lý do (cỡ mẫu, setting khác, preprint, đơn nguồn…) |
| `decision_relevance` | Ảnh hưởng tới H1/H2/H3: tính mới, phản chứng, protocol, power, công sức |
| `hypothesis` | H1 / H2 / H3 / chung |
| `direction` | `supports` / `contradicts` / `overlaps` / `context` |
| `transfer` | `in-domain` (RCA microservice/cloud) / `adjacent` (AIOps, log, sự cố khác) / `out-of-domain` (QA, toán, NLI…). Phản chứng `out-of-domain` không đủ một mình để bác H1 |

## 7. Các phase

| # | Phase | File | Phụ thuộc | Đầu ra chính |
|---|---|---|---|---|
| 01 | Đóng băng giao thức và kiểm năng lực Elicit | [phase-01](phase-01-dong-bang-giao-thuc-va-kiem-elicit.md) | Phê duyệt kế hoạch | `work/search-protocol.md`, `work/usage-log.csv` |
| 02 | Tìm kiếm có hệ thống | [phase-02](phase-02-tim-kiem-co-he-thong.md) | 01 | `work/raw/*.json`, `work/search-log.csv` |
| 03 | Khử trùng lặp và sàng lọc tiêu đề/tóm tắt | [phase-03](phase-03-khu-trung-lap-va-sang-loc.md) | 02 | `work/corpus.csv`, `work/screening.csv`, `work/prisma-counts.json` |
| 04 | Xác minh toàn văn và trích xuất có cấu trúc | [phase-04](phase-04-xac-minh-toan-van-va-trich-xuat.md) | 03 | `work/extraction.csv`, `work/findings.csv` |
| 05 | Snowballing và hồ sơ DecompRCA | [phase-05](phase-05-snowballing-va-ho-so-decomprca.md) | 04 | `work/snowball-log.csv`, `research/decomprca-dossier.md` |
| 06 | Tổng hợp và chấm điểm H1/H2/H3 | [phase-06](phase-06-tong-hop-va-cham-diem-huong.md) | 04, 05 | `work/direction-scores.csv`, bản nháp báo cáo |
| 07 | Vòng gap cuối và báo cáo duy nhất | [phase-07](phase-07-vong-gap-cuoi-va-bao-cao.md) | 06 | Báo cáo cuối tại `plans/reports/` |

## 8. Tiêu chí chấp nhận (toàn kế hoạch)

Trạng thái 2026-10-19 (sửa theo [review 261019-1441](../reports/review-261019-1441-tong-quan-elicit-va-huong-h1.md),
xem [kế hoạch sửa](../261019-1501-sua-review-h1-power-va-sang-loc/plan.md)): 6 phase xong; Phase 03 đạt
một phần. `[~]` nghĩa là đạt một phần, kèm lý do. Báo cáo cuối:
[research-261019-tong-quan-elicit-chon-dong-gop-nt114.md](../reports/research-261019-tong-quan-elicit-chon-dong-gop-nt114.md).

- [x] **AC1** _(Bằng chứng: research/elicit-mcp-capability-record.md §3b; usage-log.csv có 0 → 24 → 100 %.)_ Hồ sơ năng lực Elicit đầy đủ; mọi lệnh tốn hạn mức có `percentUsed` trước/sau trong `work/usage-log.csv`.
- [~] **AC2** _(search-log.csv: 93 dòng, có chuỗi truy vấn, filter, giới hạn, thời điểm, số kết quả và file raw. Ngoại lệ: kết quả của 4 truy vấn scoping lúc lập kế hoạch (P-*) không được lưu; 6 truy vấn Elicit thất bại vì hết hạn mức; raw dùng CSV rút gọn, sai lệch D2.)_ Mỗi truy vấn có: chuỗi chính xác, chế độ, filter, `maxResults`, ngày giờ, số kết quả, file raw. Chạy lại được.
- [x] **AC3** _(Chỉ gửi chuỗi truy vấn tiếng Anh công khai; toàn bộ đầu vào được trích lại từ transcript và ghi trong search-log.csv.)_ Mọi truy vấn gửi Elicit đã qua kiểm "chỉ công khai" (Phase 01, mục 4) và được ghi lại.
- [~] **AC4** _(Sửa 2026-10-19: luồng bản ghi → công trình tách riêng trong [prisma-flow.json](../261019-1501-sua-review-h1-power-va-sang-loc/work/out/prisma-flow.json). 390 bản ghi loại ở abstract đều có tiêu chí. 310 bản ghi "không lý do" thực ra là 286 không lấy được toàn văn và 24 có lý do trong cột `Exclusion reason`; loại theo nội dung ở toàn văn là 40, đều có lý do. Còn thiếu: 279 công trình ngoài SR1 chỉ qua luật tiêu đề, không có quyết định tay kèm lý do.)_ PRISMA có đủ số: thô, sau khử trùng lặp, loại ở tiêu đề/tóm tắt (kèm lý do), đọc toàn văn, loại ở toàn văn (kèm lý do), giữ lại, thêm từ snowballing.
- [x] **AC5** _(Cột pub_status_auto trong corpus.csv; pub_status kiểm tay trong findings.csv; LM-PACE/PACE-LM được gộp tay.)_ Mỗi bài trong tập cuối có `pub_status`; preprint và bản xuất bản của cùng công trình được gộp.
- [~] **AC6** _(Sửa 2026-10-19: relevance 0/1/2 chưa được gán theo từng bài, nên "mọi bài relevance 2" không kiểm được đầy đủ. Các bài quyết định đã đọc toàn văn; SADE đọc thêm qua arXiv 2605.04530. TraceBudget, VerifyRCA, BudgetSRE: `unavailable`. OpenAlex ghi bản OA qua DOI ResearchGate, nhưng người thực thi bị kiểm tra bot Cloudflare chặn và không giải CAPTCHA. Bản trước ghi "IEEE paywall, không có arXiv" là chưa chính xác.)_ Mọi bài relevance 2 với bất kỳ H nào đã đọc toàn văn hoặc ghi `unavailable` kèm lý do.
- [x] **AC7** _(research/decomprca-dossier.md trả lời đủ 7 câu, có HTTP check lúc 06:54Z.)_ Có hồ sơ DecompRCA: trạng thái xuất bản, trạng thái repo, phương pháp, dataset, so sánh với RE1 của NT114, tác động lên H3.
- [x] **AC8** _(Khối C, X-C1, X-C2, O-C1, GAP-C1; bảng phản chứng ở báo cáo §5.3.)_ Có ≥ 1 khối truy vấn phản chứng H1 riêng và một bảng phản chứng trong báo cáo (kể cả khi rỗng).
- [x] **AC9** _(Báo cáo §5–§8; direction-scores.csv.)_ Mỗi H có: verdict tính mới, tương thích protocol v2, cỡ mẫu độc lập, power theo MDE ở research/06, công sức, thí nghiệm tối thiểu.
- [~] **AC10** _(contradictions.csv: C1–C6; single-source-claims.csv: SS1–SS6, đã gắn nhãn. Vòng gap chạy trên arXiv/OpenAlex; phần Elicit không chạy được vì hết hạn mức tới 2026-11-18.)_ Vòng gap cuối đã xử lý mọi mâu thuẫn và mọi khẳng định đơn nguồn có hệ quả (hoặc gắn nhãn).
- [x] **AC11** _(`work/verify-report.py`: ALL CHECKS PASSED, 57/57 phát hiện sau bản sửa; kiểm tay 10 mẫu, cả 10 khớp. Script chỉ kiểm cấu trúc, ID, URL, file và link; nó không xác minh nội dung khoa học hay điều kiện phương pháp.)_ Mọi phát hiện trong báo cáo có đủ 11 trường ở mục 6; kiểm bằng script đọc CSV (không chạy model).
- [x] **AC12** _(HEAD f354d11 không đổi; porcelain chỉ thêm báo cáo; `git diff --stat` rỗng; `private/` bị ignore.)_ So với ảnh chụp `git status --porcelain` và `git rev-parse HEAD` lưu ở Phase 01 (`work/git-baseline.txt`): chỉ thêm file mới trong thư mục kế hoạch này và báo cáo cuối; `git diff --stat` của file đã track rỗng; HEAD không đổi (không commit); không push. Các file chưa track có sẵn của chủ dự án (`note/*`, …) giữ nguyên.

## 9. Ngân sách hạn mức Elicit

Hạn mức chỉ thấy dưới dạng phần trăm. Ngân sách mềm, dừng để hỏi người dùng nếu vượt:

| Phase | Trần `percentUsed` cộng dồn |
|---|---|
| 01 (thử năng lực) | 5 % |
| 02 | 30 % |
| 03–04 (report/review nếu dùng) | 60 % |
| 05–07 | 75 % |

Giữ ≥ 25 % cho phần còn lại của kỳ (tới 2026-11-18).

## 10. Rủi ro

| Rủi ro | Khả năng | Ảnh hưởng | Giảm thiểu |
|---|---|---|---|
| Semantic search trôi miền (thấy bài RCA y tế) | Cao | Nhiễu sàng lọc | Neo cụm miền, `excludeKeywords`, sàng lọc hai bước |
| Metadata Elicit thiếu hoặc sai (DecompRCA không có venue/DOI) | Cao | Sai `pub_status` | Đối chiếu arXiv, OpenReview, DBLP, Crossref, trang venue |
| Nguồn chất lượng thấp gây ảo giác chồng lấn (TraceBudget/VerifyRCA: cùng nhóm tác giả, link ResearchGate, số trích dẫn bất thường) | Trung bình | Kết luận sai về H2 | Kiểm venue, kỷ yếu IEEE Xplore, đọc toàn văn; ghi `uncertainty` |
| Toàn văn không lấy được qua Elicit | Trung bình | AC6 không đạt | Dùng arXiv, trang tác giả, OpenReview; ghi `unavailable` |
| Bị scoop sau khi báo cáo xong | Trung bình | Mất tính mới | Báo cáo ghi ngày cắt; đề xuất kiểm lại định kỳ |
| Hết hạn mức | Thấp | Dừng giữa chừng | Mục 9; `search_papers` có vẻ không tiêu hạn mức |
| Rò dữ liệu riêng sang Elicit | Thấp | Vi phạm ràng buộc | Kiểm truy vấn ở Phase 01; không dùng `import_library_files` với file của repo |
| Thiên kiến xác nhận H1 | Trung bình | Báo cáo một chiều | Khối phản chứng bắt buộc, AC8, vòng gap |

## 11. Bàn giao

Sau phê duyệt, thực thi bằng `/ak:cook plans/261019-1045-chon-dong-gop-khoa-hoc-qua-tong-quan-elicit/plan.md`.
Kết quả báo cáo sẽ là căn cứ để chủ dự án điền §9.5 của protocol v2 trong một kế hoạch **riêng**;
kế hoạch này không sửa protocol.

## Red Team Review

Ngày 2026-10-19, 4 góc nhìn (7 phase), làm trực tiếp trong phiên. Bằng chứng có đường dẫn.

| # | Góc | Phát hiện | Bằng chứng | Quyết định |
|---|---|---|---|---|
| R1 | Bảo mật | Bản nháp để toàn văn ở `work/fulltext/` trong thư mục kế hoạch, không được git ignore → có thể commit nhầm PDF có bản quyền | `.gitignore:2` chỉ bỏ qua `private/` | **Sửa:** toàn văn chuyển về `private/fulltext/261019/` (mục 2, Phase 04) |
| R2 | Thất bại | AC12 đòi `git status` "chỉ có file mới của kế hoạch", nhưng repo đã có file chưa track của chủ dự án → AC luôn trượt | gitStatus đầu phiên: `note/note-16-10.md`, `plans/reports/bao-cao-…docx`… | **Sửa:** so với `work/git-baseline.txt` lưu ở Phase 01 |
| R3 | Giả định | Khối H giả định `extraction.csv` có tiêu đề; thực tế chỉ có `id, doi, venue…` | `plans/261011-1345-aiops-q1-literature-gap/work/extraction.csv:1` | **Sửa:** tra tiêu đề từ DOI qua Crossref |
| R4 | Giả định | Phản chứng H1 từ QA/toán (ví dụ arXiv 2606.29490) có thể không chuyển sang RCA; nếu không đánh dấu sẽ bác H1 quá tay | Hồ sơ Elicit mục 3 | **Sửa:** thêm trường `transfer`; phản chứng `out-of-domain` không đủ một mình |
| R5 | Phạm vi | Phase 02/05 dùng arXiv, Semantic Scholar, OpenAlex, Crossref ngoài Elicit; yêu cầu nêu "bằng Elicit qua MCP" | Phase 02 "Nguồn đối chiếu"; Phase 05 forward snowballing | **Hỏi người dùng** (Validation Q3); lý do giữ: Elicit thiếu metadata (DecompRCA venue/DOI null) và không có công cụ trích dẫn |
| R6 | Thất bại | Nguồn nghi chất lượng thấp (TraceBudget, VerifyRCA: cùng nhóm tác giả, URL qua ResearchGate, citedByCount bất thường) có thể tạo "chồng lấn có" giả cho H2 | Hồ sơ Elicit mục 3, S4 | **Đã có:** E6 + quy tắc mục 5 cần toàn văn peer-reviewed; giữ |
| R7 | Bảo mật | So sánh DecompRCA với inventory RE1 của NT114 có thể làm lộ dữ liệu nội bộ nếu gửi lên Elicit | Phase 05 B.4 | **Đã có:** chỉ so metadata công khai, không gửi inventory; giữ |
| R8 | Giả định | "`search_papers` không tiêu hạn mức" chỉ dựa trên 2 lần đọc `percentUsed: 0` | Hồ sơ Elicit mục 1 | **Giữ** dưới dạng quan sát; Phase 01 đo lại, ngân sách mục 9 vẫn áp dụng |
| R9 | Phạm vi | Chấm lại toàn bộ 601 bài Q1 cũ có thể tốn công | Phase 03 "Tái sử dụng corpus 261011" | **Giữ:** sàng lọc tiêu đề/tóm tắt rẻ; câu hỏi đã đổi nên không kế thừa quyết định cũ được |

Không còn phát hiện chặn.

## Validation Log

### Phiên 2026-10-19

**Kiểm chứng trước phỏng vấn:** mọi link tương đối trong plan.md và phase trỏ tới file tồn tại; số MDE
khớp research/06; `in_candidates` khớp research/04 dòng 50, 175; quy tắc chồng lấn khớp research/03
dòng 178–180; ô trống protocol v2 khớp dòng 10–11, 185–186.

| # | Câu hỏi | Trả lời của chủ dự án | Áp dụng |
|---|---|---|---|
| V1 | Dùng `create_systematic_review`? Độ sâu? | **Có, `thorough`** | Phase 02 chạy 3 review ({A+B+C+D}, {E}, {F+G}); Phase 03 kiểm tay mẫu 10 % |
| V2 | `useFigures`? | **Bật** | Áp dụng cho cả 3 review |
| V3 | Nguồn công khai ngoài Elicit? | **Cho phép** | Phase 02 đối chiếu, Phase 03 `pub_status`, Phase 05 forward snowballing |
| V4 | File ghi chú 13/10 có phải bản tóm tắt ChatGPT? | **"Bỏ qua bản tóm tắt GPT, nó không quan trọng bằng codebase"** | Bỏ khỏi đầu vào; P18/P31/P42/P50 vẫn là hạt giống vì có trong corpus 261011 |

**Lưu ý ngân sách:** systematic review `thorough` + `useFigures` có thể tiêu nhiều hạn mức. Trần mục 9
giữ nguyên; nếu review đầu tiên làm `percentUsed` vượt 20 %, dừng và hỏi chủ dự án trước khi chạy hai
review còn lại.

Trạng thái: **đã xác nhận, chờ phê duyệt thực thi.**
