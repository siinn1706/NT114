---
phase: 7
title: "Thẩm định toàn văn có mục tiêu → T2 (10)"
status: done
receipt: work/receipts/07-rank-t2-01.json
owner_skills: [nckh-research]
---

# Giai đoạn 07: Thẩm định toàn văn

## Yêu cầu

- Mỗi bài có toàn văn được đọc có mục tiêu (abstract, bài toán, phương pháp, setup, bảng kết quả, limitation, artifact) và chấm F1–F6 theo [protocol §7](protocol.md), mỗi điểm có locator trang/mục/bảng.
- Bài `abstract-only` không được chấm F, không vào T2.
- Chọn 10 theo cổng T2 và tie-break.

## Tệp

- Đọc: `private/fulltext/261024/*.txt` (và PDF khi cần kiểm bảng), `work/access-ledger.csv`.
- Tạo: `research/cards/t2/<record_id>.md` (reader card ngắn: câu hỏi, phương pháp, dữ liệu, modality, LLM, baseline, metric, kết quả chính có locator, artifact, limitation), `work/appraisal/batch-NN.csv` (4 bài/batch), `work/appraisal/f-scores.csv`, `work/records/t2-top10.csv`, `work/receipts/07-*.json`.

## Các bước

1. Batch 4 bài; người đọc = agent chính (hoặc `nckh-researcher`, tối đa 5 worker song song, mỗi worker sở hữu batch riêng).
2. Với mỗi bài: reader card + điểm F + locator; ghi rõ phần chưa đọc.
3. Sau mỗi batch: output + receipt + state.
4. Khi xong mọi bài có toàn văn: kiểm lại 10% bài (ít nhất 5, gồm hạng 9–12) bằng reviewer ngữ cảnh mới, so điểm F; lệch ≥ 3 điểm tổng → rà lại bài đó.
5. Xếp F, áp cổng T2, chọn 10; ghi khoảng cách điểm giữa hạng 10 và 11.

## Kiểm tra

- Mỗi điểm F trỏ tới locator tồn tại trong text đã hash (spot-check 20 locator).
- Không bài `abstract-only` nào trong `f-scores.csv`.
- `t2-top10.csv` sinh lại tất định từ `f-scores.csv`.

## Rủi ro và hoàn tác

- Bài dài/đa phiên bản: đọc bản đã hash trong ledger; ghi version.
- Nhiều bài hòa ở biên: ghi danh sách hòa, áp tie-break, báo trong báo cáo.
- Hoàn tác: chấm lại bằng batch mới, giữ batch cũ.
