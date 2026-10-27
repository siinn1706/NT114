---
phase: 2
title: "Kiểm kê và xác minh lại corpus 11/10 và 19/10"
status: done
receipt: work/receipts/02-reuse-seed-01.json
owner_skills: [nckh-literature, nckh-evidence]
---

# Giai đoạn 02: Tái sử dụng corpus cũ sau xác minh

## Yêu cầu

- Corpus cũ là **seed**, không phải kết quả: mọi bản ghi tái sử dụng phải qua lại cổng §3–§4 của protocol đã đóng băng.
- Không kế thừa quyết định screening, điểm, cụm hay xếp hạng cũ (tiêu chí khác). Chỉ kế thừa metadata đã xác minh và vị trí toàn văn/trích xuất để phase 06–08 dùng sau khi kiểm lại hash.
- Mỗi bản ghi giữ `origin: reuse:<file>:<row>` và hash file nguồn.

## Tệp

- Đọc (input bất biến): `../261011-1345-aiops-q1-literature-gap/work/{raw-hits,q1-hits,snowball-q1,screened,read-final,extraction,access-log}.csv`, `../261019-1045-chon-dong-gop-khoa-hoc-qua-tong-quan-elicit/work/{corpus,extraction,findings}.csv`, `private/fulltext/` (liệt kê, hash).
- Hash tham chiếu đo ngày 24/10/2026 (SHA-256): `raw-hits.csv` `d5ce30d14e311163634c93aaf15cc839e01183a155d88ef7b647882d5446d808`; `q1-hits.csv` `91375232c9509585582fb31e9285125c60e3cffb104c851289538266249ca9fe`; `snowball-q1.csv` `15afb54374893cda182ee1f544af5fa94f3a39b473b440daf4a5ba25cc1bb330`; `screened.csv` `7704d93ade3c5ca68c12f9d8106206a5c04cc8e1c1fe8142608ac22f8828ba10`; `read-final.csv` `54a44048f7670d54640196bb3df4de74b92ef64415d6e327d11122564c74af6d`; Elicit `corpus.csv` `f70702a3031673c031a49c9e7bb7b9f6db74d65bf75f69f75531a7fa96f5e987`.
- Tạo: `work/reuse-inventory.csv` (file, hash, số dòng), `work/records/seed-reused.csv`, `work/reuse-fulltext-map.csv`, `work/receipts/02-*.json`.

## Các bước

1. Hash mọi input; nếu khác hash tham chiếu, ghi lệch và dùng bản trên đĩa (không sửa input).
2. Hợp nhất DOI/OpenAlex ID từ các file seed; với mỗi bản ghi, gọi lại OpenAlex theo ID (batch 50 ID/lần bằng filter `openalex:W…|W…`) để lấy metadata hiện hành; Crossref cho DOI thiếu ISSN và trạng thái retraction.
3. Áp Q-1…Q-9 và cổng chủ đề §4 bằng script tất định; ghi `q1_rule_trace`.
4. Từ corpus Elicit, chỉ đưa bản ghi tạp chí vào seed T0; bản ghi hội nghị/preprint vào `work/records/prior-work-pool.csv` cho phase 08–09.
5. Map toàn văn cũ: với mỗi PDF/text trong `private/fulltext/`, tính SHA-256, khớp với `read-final.csv`/`access-log.csv`; chỉ ghi `reusable=1` khi hash và DOI khớp.
6. Ghi receipt và commit batch vào state.

## Kiểm tra

- Tổng dòng input = dòng `seed-reused.csv` + dòng loại có lý do (không mất bản ghi im lặng).
- Kiểm tay 20 bản ghi ngẫu nhiên (seed 20261024): DOI phân giải, ISSN, category SJR khớp `q1_rule_trace`.
- Số bản ghi `q1_cs=1` được báo; so với ~562 bản ghi CS trước khử trùng chỉ để phát hiện bất thường, không làm chỉ tiêu.

## Rủi ro và hoàn tác

- Metadata OpenAlex đổi so với 11/10 (venue, năm): dùng bản hiện hành, ghi bản cũ ở cột `prior_value`.
- Script cũ ở `../261011-1345-aiops-q1-literature-gap/work/scripts/` có thể tái dùng chỉ sau khi đọc code và chạy trên 20 bản ghi đối chiếu; script mới đặt trong `work/scripts/`.
- Hoàn tác: các file output mới là bất biến theo attempt; xóa attempt hỏng, input cũ không bị chạm.
