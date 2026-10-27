---
title: "NT114: tổng quan 1.000 bài Q1 để đề xuất một bài nền cho MVP RCA một-LLM khi thiếu telemetry"
description: "Kế hoạch nghiên cứu tài liệu: thu thập ≥1.000 bài tạp chí Q1 (SJR 2025, category Computer Science) duy nhất, sàng lọc 100, phân tích sâu 10, đề xuất MỘT bài nền để tái hiện và cải tiến, rồi thiết kế tái hiện/cải tiến/phép thử/MVP."
status: ready-for-review
priority: P1
effort: "ước tính 8-14 phiên làm việc; 0 GPU; 0 lần chạy model"
branch: main
mode: nckh-cook --auto
plan_location: "plans/ (quy ước repo {date}-{issue}-{slug})"
tags: [literature-review, q1, screening, rca, missing-telemetry, single-llm, base-paper]
blockedBy: []
blocks: ["chọn bài nền cho MVP", "kế hoạch tái hiện và cải tiến"]
created: 2026-10-24
---

# Tổng quan 1.000 → 100 → 10 → 1 bài nền cho MVP RCA một-LLM khi thiếu telemetry

## 1. Kết quả mong muốn

Một bộ artifact tái lập được dẫn tới **một bài nền được đề xuất** (không phải được chủ dự án chấp nhận sẵn) cho MVP “RCA microservice bằng một LLM khi thiếu telemetry”, kèm thiết kế tái hiện, giả thuyết cải tiến, phép thử và đề cương MVP. Báo cáo cuối: `plans/reports/research-<ngày>-tong-quan-1000-q1-chon-bai-nen.md`.

Phễu và mức bằng chứng ở mỗi tầng:

| Tầng | Số bài | Mức đọc | Quyết định dựa trên |
|---|---|---|---|
| T0 corpus | ≥ 1.000 duy nhất | metadata | cổng Q1/năm/loại/chủ đề rộng ([protocol §3–§4](protocol.md)) |
| T1 sàng lọc | 100 | metadata + abstract | rubric R ([protocol §6](protocol.md)) |
| T2 thẩm định | 10 | toàn văn (đọc có mục tiêu) | rubric F ([protocol §7](protocol.md)) |
| T3 chọn | 1 | toàn văn đầy đủ + artifact | cổng G + ma trận quyết định ([protocol §8](protocol.md)) |

Nguyên tắc: không chọn trước bài, không khẳng định trước novelty, không nâng nhãn metadata/abstract thành bằng chứng về phương pháp hay kết quả.

## 2. Phạm vi, ràng buộc, ngoài phạm vi

**Trong phạm vi:** tìm kiếm, khử trùng, kiểm Q1, sàng lọc, truy cập toàn văn, đọc, kiểm chứng trích dẫn/số liệu của các bài vào T2–T3, đọc tĩnh artifact (repo, license, dataset) của 10 bài, thiết kế tái hiện/cải tiến/phép thử/MVP dạng tài liệu.

**Ràng buộc:**
- Chỉ tạp chí đạt chuẩn Q1 ở [protocol §3](protocol.md) được đếm vào 1.000 và được chọn làm bài nền. Hội nghị/preprint chỉ thuộc làn *prior work* để kiểm tính mới và phản chứng, không đếm.
- Giữ quyết định của chủ dự án: một LLM, không judge/escalation; H1 là hướng chính, P1 bắt buộc, P2 thăm dò, P3 không triển khai ([decisions.md](../261018-2300-single-llm-simplification-and-evaluation-hardening/decisions.md)). Nếu bài nền đề xuất đòi đổi H1 hoặc protocol v2, ghi `waiting-human`, không tự đảo.
- Quyết định mới của chủ dự án (yêu cầu ngày 24/10/2026): đề xuất **một** bài nền. Review ngày 23/10 từng nêu phương án ba bài; kế hoạch này thay bằng một bài theo yêu cầu; ba vai trò cũ không là tiêu chí chấm điểm.
- Internet được phép không giới hạn cho nghiên cứu ([decisions 18/10](../261018-2300-single-llm-simplification-and-evaluation-hardening/decisions.md)); chỉ gửi truy vấn công khai ra ngoài, không gửi dữ liệu repo, nhãn, evidence hay toàn văn.
- Toàn văn chỉ ở `private/fulltext/261024/` (đã gitignore); response thô ở `work/raw/` (gitignore theo `plans/*/work/raw/`).

**Ngoài phạm vi:** sửa source/config/protocol v2/prompt/split/bundle; chạy model, GPU hoặc paid API; clone rồi chạy code của bài; commit/push; công bố hoặc chia sẻ. Thiết kế ở phase 09 không cấp quyền triển khai — triển khai cần kế hoạch mới.

## 3. Khảo sát khả thi đã chạy trong lượt lập kế hoạch (24/10/2026)

| Kiểm tra | Kết quả quan sát | Hệ quả cho kế hoạch |
|---|---|---|
| OpenAlex `title_and_abstract.search`, lọc journal, article/review, từ 2020 | `"root cause" microservice` 239; `"root cause analysis" (cloud OR microservice OR AIOps)` 307; `"large language model" (incident OR "root cause" OR AIOps)` 821; `AIOps OR (incident management cloud) OR (log anomaly detection)` 3.641; `log anomaly detection` 2.393; `cloud incident` 2.894; `trace anomaly` 5.590 (nhiễu ngoài miền) | Lõi RCA-microservice hẹp không đủ 1.000 Q1; cần khái niệm AIOps quản lý lỗi rộng ([protocol §4](protocol.md)) và chấp nhận nhiễu cao ở tầng metadata |
| OpenAlex abstract coverage (50 bản ghi đầu của truy vấn RCA) | 41/50 có abstract | Phase 04 phải có làn bổ sung abstract (Crossref/Semantic Scholar/trang publisher) |
| Crossref `/works` | HTTP 200 | Làn xác minh DOI, retraction, bổ sung metadata |
| Semantic Scholar search không key | HTTP 429 | Làn tùy chọn; không có key thì `NOT_CALLABLE`, không chặn kế hoạch |
| scimagojr.com bằng curl | không kết nối (code 000); lần 11/10 bị Cloudflare 403 | Dùng lại CSV SJR 2025 đã hash; phase 01 kiểm có ấn bản mới hơn qua trình duyệt |
| CSV SJR 2025 | SHA-256 `6f20399957173a13e3c1729a5fb3b5821844ba75e8d640c8b3040ab19a6f7180`; 30.412 `journal`, 913 `book series`, 688 `conference and proceedings`; 9.399 journal Best Q1; 562 journal có ít nhất một category CS ở Q1 | Cổng Q1-CS thực thi được từ cột `Type` và `Categories` |
| Corpus 11/10 | `q1-hits.csv` 601 dòng (439 có `cs_category_q1=1`); `snowball-q1.csv` 135 dòng (123 CS) | Seed ~562 bản ghi Q1-CS trước khử trùng chéo; cần thêm ≥ ~450 bản ghi mới |
| Corpus Elicit 19/10 | `corpus.csv` 1.958 work (gồm hội nghị/preprint) | Nguồn seed cho làn prior work và một phần T0 sau khi qua cổng Q1 |

Các con số trên là đếm thô tại thời điểm chạy, không phải số bài hợp lệ.

## 4. Tiêu chí chấp nhận của toàn kế hoạch

1. Giao thức [protocol.md](protocol.md) được hash và review ở phase 01 **trước** bản ghi screening đầu tiên; mọi sửa sau đó là amendment có ngày, lý do, phạm vi ảnh hưởng.
2. T0: ≥ 1.000 bản ghi duy nhất qua cổng Q1/năm/loại/chủ đề, mỗi bản ghi có provenance (provider, query, trang, thời điểm, hash response hoặc nguồn tái sử dụng + hash file + dòng). Nếu không đủ: báo cáo bão hòa theo [protocol §10](protocol.md), không nới cổng ngầm.
3. T1: mỗi bản ghi T0 có đúng một quyết định include/exclude/needs-review với mã lý do và điểm R; mẫu kép đạt Cohen's κ ≥ 0,7 hoặc rubric được sửa bằng amendment rồi chấm lại.
4. T2: 100 bài có nhãn truy cập (full-text/abstract-only/không truy cập) và điểm F chỉ trên bài đọc được toàn văn; 10 bài vào T3 đều đọc toàn văn.
5. T3: 10 reader card đầy đủ, artifact được kiểm tĩnh, các số liệu/trích dẫn dùng trong quyết định có locator và verdict của nckh-evidence; ma trận quyết định có phân tích độ nhạy; đề xuất 1 bài (hoặc báo hòa hạng có lý do).
6. Phase 09: thiết kế tái hiện, cải tiến, phép thử, MVP; mọi phát biểu tính mới bị giới hạn bởi tìm kiếm đã chạy.
7. Mọi phase có receipt lệnh (exit status riêng từng lệnh) và state checkpoint resume được; báo cáo cuối tách existing/created/verified/unverified.
8. Chấp nhận bài nền là của chủ dự án: trạng thái cuối tối đa là `ready-for-review` / `pending-personal-review`.

## 5. Các giai đoạn

| Giai đoạn | Nội dung | Phụ thuộc | Skill chủ | Trạng thái |
|---|---|---|---|---|
| [01](phase-01-dong-bang-giao-thuc.md) | Đóng băng giao thức, kiểm SJR, dựng state/checkpoint | — | nckh-method, nckh-literature | done |
| [02](phase-02-tai-su-dung-corpus-cu.md) | Kiểm kê và xác minh lại corpus 11/10 và 19/10 | 01 | nckh-literature, nckh-evidence | done |
| [03](phase-03-chien-dich-tim-kiem.md) | Chiến dịch tìm kiếm theo batch + snowball | 01, 02 | nckh-literature | done (T0 1085 sau §10) |
| [04](phase-04-khu-trung-va-cong-q1.md) | Khử trùng, cổng Q1/năm/loại/chủ đề, bổ sung abstract → T0 | 02, 03 | nckh-literature, nckh-evidence | done |
| [05](phase-05-sang-loc-abstract-top-100.md) | Sàng lọc abstract, mẫu kép, xếp hạng → T1 (100) | 04 | nckh-literature, nckh-method | done (T1 100; 152 needs-review chờ chủ dự án) |
| [06](phase-06-truy-cap-toan-van.md) | Truy cập toàn văn 100 bài, ledger quyền | 05 | nckh-literature | done (34/100 toàn văn; 17 PDF chờ tải tay) |
| [07](phase-07-tham-dinh-toan-van-top-10.md) | Thẩm định toàn văn có mục tiêu → T2 (10) | 06 | nckh-research | done (T2 10) |
| [08](phase-08-phan-tich-sau-va-chon-mot.md) | Phân tích sâu 10, kiểm chứng, prior work, chọn 1 | 07 | nckh-research, nckh-evidence | waiting-human → chủ dự án chấp nhận RCLAgent có điều kiện 2026-10-26 (decision log 261018-2300); kế hoạch triển khai tiếp: `plans/261026-0928-nhanh-a-im1-trien-khai-kha-thi/` |
| [09](phase-09-thiet-ke-tai-hien-cai-tien-mvp.md) | Thiết kế tái hiện, cải tiến, phép thử, đề cương MVP | 08 | nckh-method | done, có điều kiện (chờ chủ dự án chấp nhận bài nền; D1–D13) |
| [10](phase-10-ra-soat-bao-cao-ban-giao.md) | Review độc lập, báo cáo, handoff | 01–09 | nckh-review, nckh-handoff | ready-for-review (báo cáo v2, review 2 vòng; bài nền pending-personal-review) |

## 6. Artifact và nơi lưu

| Artifact | Đường dẫn | Git |
|---|---|---|
| Giao thức + amendment | [protocol.md](protocol.md), `work/amendments.md` | có |
| State checkpoint | `work/state.json` (schema ở [protocol §11](protocol.md)) | có |
| Receipt lệnh | `work/receipts/<phase>-<batch>-<attempt>.json` | có |
| Response thô | `work/raw/<provider>/<query>-p<n>.json` | không (gitignore) |
| Bản ghi chuẩn hóa | `work/records/*.csv` | có |
| Toàn văn, text trích | `private/fulltext/261024/` | không (gitignore) |
| Reader card, ledger | `research/cards/*.md`, `work/evidence-ledger.csv` | có |
| Thiết kế sau chọn | `design/*.md` | có |
| Báo cáo cuối | `plans/reports/research-<ngày>-tong-quan-1000-q1-chon-bai-nen.md` | có |

## 7. Handoff cho nckh-cook --auto

- Chạy tuần tự 01 → 10; trong phase chạy theo batch, sau mỗi batch ghi output bất biến + receipt + cập nhật `work/state.json` rồi mới sang batch kế.
- Đầu mỗi phiên: đọc `work/state.json`, kiểm hash input/output của các batch đã ghi; batch `running` không có output hoàn chỉnh → attempt mới, giữ attempt cũ.
- Tự chạy không hỏi: truy vấn OpenAlex/Crossref/arXiv/Unpaywall công khai, Elicit với truy vấn công khai trong hạn mức, tải PDF open access, đọc, ghi file trong thư mục kế hoạch và `private/fulltext/261024/`.
- Dừng `waiting-human`: PDF chỉ có qua đăng nhập publisher (chủ dự án tải tay), bài nền đề xuất xung đột quyết định H1/protocol v2, hạng 1 không ổn định ở phân tích độ nhạy, T0 < 1.000 sau tiêu chí bão hòa (vẫn tiếp tục phễu với N thực, đánh dấu chờ chủ dự án xác nhận), bất kỳ thao tác ngoài phạm vi ở §2.
- Không commit/push; không đánh dấu phase xong nếu thiếu receipt trên cùng dòng.

## 8. Quyết định còn mở (đã chọn mặc định, chủ dự án có thể sửa trước phase 01)

| Quyết định | Mặc định trong kế hoạch | Lý do | Phương án khác |
|---|---|---|---|
| Hệ xếp hạng | SJR 2025 | Truy cập được, đã hash, quartile theo category | JCR 2025 nếu có quyền Clarivate (đối chiếu cho 10 bài) |
| Chuyên ngành | Q1 ở ≥ 1 category CS (13 category, [protocol §3](protocol.md)) | “Q1” không đồng nghĩa “CS Q1” (audit 23/10) | Thêm Engineering (Electrical and Electronic) |
| Số T0 vượt 1.000 | Chạy hết bộ truy vấn đã đóng băng, giữ toàn bộ bản ghi hợp lệ, báo N thực | Dừng sớm hoặc cắt theo thứ tự truy vấn gây thiên lệch | Lấy mẫu ngẫu nhiên có seed ghi sẵn xuống đúng 1.000 |
| MDPI, IEEE Access, Scientific Reports | Giữ quy tắc D3/D4 của giao thức 11/10 | Liên tục với corpus cũ | Bỏ D4 |
