# Handoff: tổng quan 1.000 bài Q1 → bài nền, sau phase 10 và quyết định chủ dự án

Cập nhật 2026-10-26 (Asia/Saigon), lần 2: sau quyết định của chủ dự án cùng ngày. Kế hoạch: `plans/261024-0858-tong-quan-1000-q1-chon-bai-nen-rca-thieu-telemetry/` (P; đường dẫn dưới đây tính từ P). Thay cho bản phục hồi [context-261026-0847-claude-resume.md](../context-261026-0847-claude-resume.md) và cho bản handoff lần 1 cùng ngày (bản lần 1 ghi nhầm "268 verified / 317"; số đúng ở mục Receipt).

## Trạng thái

- Kế hoạch tổng quan: `ready-for-review`. Phase 01–07 `done`; 08 `waiting-human` trong frontmatter, bảng plan ghi chủ dự án đã chấp nhận RCLAgent có điều kiện; 09 `done-conditional` (design 0.2, receipt `09-design-check-05`); 10 `ready-for-review`. `check-plan.py` VERIFIED.
- Quyết định chủ dự án 2026-10-26 ghi append-only ở [decisions.md](../../261018-2300-single-llm-simplification-and-evaluation-hardening/decisions.md) (8 dòng cuối): RCLAgent là bài nền **có điều kiện** (không khẳng định tốt nhất, thắng ổn định, đã tái hiện hay hợp model 4–9B); nhánh (a) một lời gọi, adaptation không recursion-of-thought; H1 giữ nguyên; IM1 chọn cho MVP; D5–D8, D10, D12, D13; PR-06 giữ CS; Perplexity thay Elicit.
- Design 0.2 (`design/*.md`) và mục quyết định cuối `research/selection-memo.md` đã cập nhật theo quyết định; số liệu và lựa chọn tổng quan không đổi.
- Kế hoạch triển khai tiếp theo: [plans/261026-0928-nhanh-a-im1-trien-khai-kha-thi/plan.md](../../261026-0928-nhanh-a-im1-trien-khai-kha-thi/plan.md), 8 phase, `planned`, `check-plan.py` VERIFIED. Kế hoạch đó chưa cấp quyền sửa source hay chạy model.

## Việc đã làm trong lượt này

1. Provenance 8 card T3: đối chiếu transcript phiên trước, phần đổi sau checkpoint chỉ là hai loại ghi chú điều phối nối cuối file. Bỏ ghi chú thì 8/8 card khớp đúng hash đã commit (`work/t3-card-delta-10.csv`, receipt `10-card-delta-01`). Các batch card commit lại thành attempt a02; a01 giữ trong `attempts`. Không tạo bằng chứng hồi tố cho nội dung ghi chú.
2. Tìm có mục tiêu bằng Perplexity Pro (3 truy vấn, chỉ từ khóa, tên bài, DOI công khai), mọi dòng đối chiếu arxiv.org, Crossref hoặc OpenAlex: `work/targeted-search-261026.csv` → `work/targeted-search-261026-dedup.csv` (receipt `10-targeted-search-dedup-01`). 10/11 nguồn đã có trong corpus cũ; 1 DOI do Perplexity đưa bị loại vì trỏ sai bài; DOI và venue MonitorRank do Perplexity đưa cũng sai và đã sửa theo OpenAlex.
3. Phản chứng bên thứ ba cho RCLAgent ghi thành amendment có ngày trong `work/amendments.md` (PRISM arXiv:2601.21359: RE2OB Top-1 0,18; arXiv:2607.13548: 8/70; arXiv:2608.21310: 53,4%). Không đổi tập hay điểm của tổng quan.
4. Bản TDSC: Crossref xác nhận DOI (issued 2026-09); chưa tìm thấy bản tác giả hay OA hợp pháp ngoài arXiv:2605.14866.
5. Kiểm lại thiết kế 0.2 bằng `check-design.py` (receipt `09-design-check-05`, exit 0).

## Receipt

- Lần verify cuối: `work/receipt-verify-10-a04.csv` (`10-receipt-verify-04`) có 318 dòng: 268 verified, 23 `superseded-state`, 19 `changed-later`, 8 `other`; 268 + 23 + 19 + 8 = 318. Không nâng 50 receipt không verified thành pass.
  - `superseded-state` gồm các receipt chỉ lệch `work/state.json` do checkpoint sau (có `10-sync-phase-status-01`, `10-sync-phase-status-02`, `10-card-delta-01`).
  - `changed-later` thêm `09-design-check-04` vì design lên 0.2; bản 0.2 được kiểm bởi `09-design-check-05`.
  - `other`: 8 lệnh ghép không ghi exit từng đoạn ở checkpoint phase 04–05 (7 seed, 1 `04-checkpoint-full-02`).
- Giải thích phép đếm lần trước: `receipt-verify-10-a03.csv` có 315 dòng (268 + 21 + 18 + 8); lúc đó trên đĩa có 316 receipt vì `10-receipt-verify-03` không nằm trong CSV của chính nó. Con số 317 trong handoff lần 1 là lỗi ghi của tôi.
- Sau `10-receipt-verify-04`, hai receipt tạo thêm được kiểm riêng bằng `check-receipt.py verify`: `09-design-check-05` VERIFIED; `10-receipt-verify-04` VERIFIED. Tổng receipt trên đĩa: 320.

## Artifact và SHA-256 (đo sau mọi sửa của lượt này, trước khi ghi tệp này)

| Tệp | SHA-256 |
|---|---|
| `work/state.json` | f8ce7155a366b01721180e2c507103cbdc764cfa68bc9aadafb49739a976a663 |
| `plans/reports/research-261026-0430-tong-quan-1000-q1-chon-bai-nen.md` (v2, thêm ghi chú card) | 9a963272f3cae124745d9cc6ed71e9e00e06c440941c229e3099fc1cb49295b3 |
| `research/final-review.md` | bc4c597532fe6638146e9a103ab778ac3dec6c636fa11bccad69aab7f5a3b0ca |
| `research/selection-memo.md` | 6006d4c78c1390edd91a2d5bb86f5a68c9237d05a4369fb78b614c157884a8b8 |
| `work/gate-matrix.csv` | d863a5eff489e89b2be93b3137074b6c12e5c7242e348b8ddf610e5932f37cad |
| `work/amendments.md` | ca6af8177069ec785e408bd8dc175c109869764db84245fb8694a440d4697de0 |
| `work/targeted-search-261026-dedup.csv` | 30c3488435bfa1e58506a97a0f8bad3a58d779085b91004870b7fdb7d9e0deed |
| `work/t3-card-delta-10.csv` | 2ff2b20f52dfe2c42a15717bf72360a0e1a45b8b19d679d21675bca03371af0a |
| `work/receipt-verify-10-a04.csv` | 77423c43a543c956c7ff83d55cf28729da9a25eda92b9ed140bf7bdce83a8223 |
| `design/reproduction-protocol.md` (0.2) | bf1a3ba417b4ba792aae332dab0c59a0cd6040ec8c4115345d35a7532ed6edfd |
| `design/improvement-hypotheses.md` (0.2) | 85d74d2ee1b0dbe903b0795dee4fd0d95d87d402ee07a2b7299fbb97779bf79d |
| `design/test-matrix.md` (0.2) | af6eb47aca83204e94b7c0371a1933b44c62db2fcb2ff4cf20f2f61673ac55ee |
| `design/mvp-outline.md` (0.2) | a38970448d203ad7e3d5b6d5994f6f657acbcf9e768fe327be45bbd796b131c6 |
| `../261018-2300-single-llm-simplification-and-evaluation-hardening/decisions.md` | 05941ac088fb24fc483e3ab0f33f00ad3a1c2a7af9f9b01b5bb07509de302e8d |
| `../261026-0928-nhanh-a-im1-trien-khai-kha-thi/plan.md` | d43f3802ffde54a2cb6e9d1b7fefca64a8a729d64b9fb12e40323da7f0093833 |

`protocol.md` vẫn ca65919f18ecc443548b2fea38c9b57a4e08ab1fbeeb86859a42243c0f36005d (không sửa). Phần cập nhật design 0.2 do một agent `nckh-maker` làm theo brief, chưa qua review ngữ cảnh mới; chỉ có kiểm cơ học `09-design-check-05`.

## Giới hạn bằng chứng còn lại

- G3 chỉ là ước lượng tĩnh; chưa đo runtime, VRAM hay độ chính xác backbone 4–9B.
- Số liệu bản TDSC chưa đối chiếu; arXiv v1 là bản đã đọc.
- Phản chứng bên thứ ba là preprint; trong PRISM chưa xác định backbone và phiên bản RCLAgent họ dùng.
- Tính mới của IM1 không được khẳng định; câu "chưa thấy phương pháp nào" của Perplexity không được dùng làm bằng chứng. MonitorRank (SIGMETRICS PER 2013) là tiền lệ gần cho đồ thị gọi dịch vụ lâu dài kết hợp metric, mới kiểm ở mức metadata.
- Review PASS phase 08/09 và 23 dòng độ nhạy tính lại tay chỉ có ghi chú state (attested).
- Máy của phiên này là i5-14400F, RAM 31,8 GB, AMD RX 5600 XT, không CUDA; máy RTX 4080 Laptop 12 GB chưa được probe.

## Waiting-human

1. Duyệt phụ lục data contract IM1 và mã arm (phase 01 của kế hoạch triển khai) trước mọi sửa source.
2. Giao lệnh `nckh-cook` cho kế hoạch triển khai khi muốn bắt đầu phase 01–02 (chỉ tài liệu và kiểm CPU).
3. Xác nhận máy sẽ chạy model sau này và cấp quyền chạy theo gói khả thi (phase 07); hiện chưa có quyền GPU/model.
4. Xem phản chứng bên thứ ba trong `work/amendments.md`; quyết định chấp nhận có điều kiện vẫn giữ trừ khi chủ dự án đổi.
5. Bản TDSC: tải nếu có quyền truy cập; 17 PDF top-30 và 152 abstract vẫn ở ledger, chưa đánh giá được do thiếu nguồn.

## Lệnh tiếp theo

- Phiên sau: đọc tệp này và [plan triển khai](../../261026-0928-nhanh-a-im1-trien-khai-kha-thi/plan.md). Kiểm hash bảng trên trước khi tiếp tục.
- Kiểm lại: `check-plan.py` cho cả hai thư mục kế hoạch phải exit 0; `verify-receipts.py` để verify receipt.
- Không commit/push, không chạy model/GPU/API trả phí, không sửa source/config/protocol v2/prompt/splits/bundle khi chưa có quyền mới.
