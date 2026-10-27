---
phase: 8
title: "Phân tích sâu 10 ứng viên, kiểm chứng, prior work, đề xuất 1"
status: waiting-human
receipt: work/receipts/08-merge-t3-03.json
owner_skills: [nckh-research, nckh-evidence]
---

# Giai đoạn 08: Phân tích sâu và chọn một bài nền

## Yêu cầu

- 10 reader card đầy đủ (đọc toàn văn), artifact kiểm tĩnh, cổng G1–G5 có bằng chứng, ma trận quyết định + độ nhạy ([protocol §8](protocol.md)).
- Mọi số liệu/trích dẫn dùng trong quyết định có verdict nckh-evidence (supported/contradicted/insufficient/unverified) và locator.
- Đề xuất **một** bài, hoặc báo top-2 khi hạng 1 không ổn định. Đây là đề xuất; chấp nhận thuộc chủ dự án.

## Tệp

- Đọc: `research/cards/t2/*.md`, toàn văn, repo/dataset công khai của 10 bài (đọc tĩnh), [hardware profile](../../nt114-rca/nt114-rca/configs/hardware/rtx4080-laptop-12gb.yaml), [data contract](../../nt114-rca/nt114-rca/docs/data_contract.md), [protocol v2](../261018-2300-single-llm-simplification-and-evaluation-hardening/design/protocol-v2.md).
- Tạo: `research/cards/t3/<record_id>.md`, `work/artifact-audit.csv` (repo URL, commit HEAD tại ngày kiểm, license, README, dataset, dependency, yêu cầu GPU/LLM), `work/evidence-ledger.csv`, `work/q1-pubyear-check.csv`, `work/prior-work-t3.csv`, `work/decision-matrix.csv`, `work/sensitivity.csv`, `research/selection-memo.md`, `work/receipts/08-*.json`.
- Mã của bài clone (nếu cần đọc) đặt ngoài repo NT114, ví dụ `F:/Nam/UIT/nt114-paper-artifacts/<record_id>/`, không chạy, không cài dependency vào môi trường NT114.

## Các bước

1. Một bài một batch: đọc toàn văn đầy đủ; reader card gồm bài toán, giả định, phương pháp (luồng dữ liệu/điều khiển), modality, vai trò LLM, dataset/split, baseline, metric + mẫu số, kết quả chính, chi phí, limitation, threats, phản chứng.
2. Kiểm artifact tĩnh: repo tồn tại, commit, license, dataset tải được (HEAD request), README có lệnh tái hiện, yêu cầu phần cứng/API.
3. nckh-evidence: kiểm 3–8 số liệu/trích dẫn then chốt mỗi bài (giá trị, đơn vị, mẫu số, bảng/trang); ghi verdict.
4. Tra quartile năm xuất bản trên SJR (và JCR nếu có quyền) → `q1-pubyear-check.csv`.
5. Prior work làn hội nghị/preprint cho phương pháp của mỗi bài (OpenAlex/arXiv/DBLP/Elicit, `prior-work-pool.csv`): có bản mới hơn vượt bài không.
6. Áp G1–G5; chấm lại F bằng bằng chứng sâu; độ nhạy 18 kịch bản.
7. Viết `selection-memo.md`: bài đề xuất, lý do theo từng tiêu chí, rủi ro, điều kiện có thể đảo đề xuất, tác động tới H1/protocol v2 (nếu xung đột → `waiting-human`).
8. Spawn `nckh-reviewer` ngữ cảnh mới review memo + ma trận; sửa phát hiện chặn.

## Kiểm tra

- 10 card, mỗi card có ≥ 1 locator cho mỗi trường kết quả và giới hạn.
- Mọi số trong `decision-matrix.csv` trỏ tới card hoặc evidence ledger; không số nào thiếu nguồn.
- `sensitivity.csv` 18 dòng; quy tắc ổn định áp đúng.
- Review không còn phát hiện chặn mở.

## Rủi ro và hoàn tác

- Không bài nào đạt đủ G1–G5: báo rõ cổng trượt phổ biến, đề xuất bài gần nhất kèm điều kiện, `waiting-human`.
- Bài nền là multi-agent: G4 phải chỉ ra phần lõi giữ lại khi rút về một LLM; không giả định đóng góp còn nguyên.
- Repo bị xóa/404: ghi ngày kiểm; G1 chỉ đạt nếu mô tả đủ để cài lại.
- Hoàn tác: memo là đề xuất có version; sửa = version mới.
