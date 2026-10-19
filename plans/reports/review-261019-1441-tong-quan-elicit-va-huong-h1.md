# Review tổng quan Elicit và đề xuất H1 của NT114

Ngày review: 19/10/2026. Revision: `f354d11e845e812e1f2dc002f69258159ef92084`.

## Kết luận

Giữ H1 thu hẹp làm hướng ưu tiên để khảo sát trên DEV. Báo cáo có giá trị để chọn hướng, nhưng chưa đủ để dùng ngưỡng AUROC 0.75 làm điều kiện loại H1 hoặc đóng băng ba kiểm định confirmatory ở §12. Có hai vấn đề P1 trong thiết kế thống kê và hai vấn đề P2 trong mức độ khẳng định, khả năng kiểm toán.

Review này không sửa báo cáo gốc, protocol, code, dữ liệu hoặc trạng thái phase. Không chạy model, GPU, paid API, commit hay push.

## Phạm vi và kiểm chứng

- Đọc báo cáo, plan, yêu cầu bảy phase, search protocol, dossier DecompRCA, findings, extraction, corpus, search log, screening check và usage log.
- Đối chiếu protocol v2, research/06, DEV pilot config và các hàm selective/metrics/analyze đang được dùng.
- Chạy lại `verify-report.py`: `findings=53 cited=53 uncited_in_body=0`, `ALL CHECKS PASSED`. Đây là kiểm tra cấu trúc, file và liên kết; script không xác minh nội dung khoa học của từng claim.
- Đếm trực tiếp CSV: 2,255 records, 1,958 works, 1,259 works có nguồn SR1 và 699 works ngoài SR1. `extraction.csv` có 17 bài; bảng Elicit có 551 dòng, nhiều dòng chưa được trích xuất.
- Tính lại screening: 119/127 đồng thuận, κ = 0.8456865. Mẫu gồm 95 bài Elicit giữ và 32 bài Elicit loại.
- Kiểm trực tiếp các nguồn công khai: DecompRCA abstract/full text; TelemetrySuffBench abstract; Reported Confidence abstract/full text; PACE-LM và EviRCA abstract. Bốn truy vấn tìm bổ sung có phạm vi hẹp không thay thế một tổng quan độc lập.
- Hai DOI H2 và GitHub DecompRCA không đọc được bằng web tool trong phiên review. Không dùng lỗi truy cập này để kết luận bài không tồn tại hoặc xác nhận HTTP 404 hiện tại. Quota Elicit là bằng chứng từ log của phiên trước, không phải trạng thái provider vừa đo lại.
- `git diff --stat` và `git diff --cached --stat` rỗng trước khi ghi báo cáo review. HEAD khớp recap.

## Phát hiện

### 1. [P1] Ngưỡng AUROC loại H1 không được suy ra từ power của endpoint đang đề xuất

**Vị trí:** [báo cáo §5.4](research-261019-tong-quan-elicit-chon-dong-gop-nt114.md:226), dòng 226–233; [§12](research-261019-tong-quan-elicit-chon-dong-gop-nt114.md:712), dòng 712–713.

MDE 0.10 trong research/06 thuộc phép so sánh AC@1 ghép cặp giữa hai arm, với discordance giả định 20%. Báo cáo chuyển nó sang selective risk bằng `MDE / sqrt(coverage)`, rồi suy ngưỡng AUROC khoảng 0.74–0.78. Hai estimator không có cùng phương sai. C2 giải tích là lỗi nền trên chính mẫu đang dùng, nên phải giữ covariance giữa lỗi nền và lỗi trong phần được trả lời.

`selective-gain.py` tính đúng câu hỏi mô hình hóa của nó: gain dưới giả định binormal, phương sai bằng nhau, lỗi nền cho trước. Nó không tính sampling distribution, power, fit ngưỡng DEV, confidence đồng hạng, hay Holm. AUROC cũng không xác định duy nhất risk ở một coverage cụ thể.

**Kiểm chứng độc lập:** liệt kê mọi vị trí của ba lỗi trong mười dự đoán, score giảm dần và không đồng hạng. Hai thứ tự có cùng AUROC `13/21 = 0.61905`, cùng lỗi nền 0.3 và coverage 0.7, nhưng selective risk lần lượt `1/7` và `2/7`. Đây là phản ví dụ toán học nhỏ, không phải kết quả NT114. Trong một null khác chỉ để đối chiếu phương sai, N=218, 65 lỗi và chọn ngẫu nhiên 153 câu trả lời cho SD của contrast với C2 giải tích khoảng 0.02024; con số này không xác nhận power thực tế của H1.

**Tác động:** có thể loại một tín hiệu hữu ích hoặc đánh giá sai độ chắc chắn của nghiên cứu. Việc báo cáo đã ghi “xấp xỉ” không đủ để biến ngưỡng này thành điều kiện quyết định ở §12.

**Cần làm:** giữ bảng binormal như sensitivity analysis. Bỏ ngưỡng AUROC cứng khỏi điều kiện go/no-go cho tới khi power được tính bằng đúng estimator, đơn vị injection, tie rule, quá trình fit DEV và family dự định dùng. DEV phải đo cả gain/AURC và độ bất định, không chỉ AUROC.

### 2. [P1] “Risk tại coverage 0.7, ngưỡng fit DEV” đang trộn hai phép đánh giá

**Vị trí:** [báo cáo §12(b)](research-261019-tong-quan-elicit-chon-dong-gop-nt114.md:706), dòng 706–707; đối chiếu `selective.py:251–280`, `metrics.py:172–195`, `analyze.py:209–252` trong Python project.

Ngưỡng đóng băng từ DEV không bảo đảm coverage 0.7 trên test. Code hiện tại đã tách `goal_value` khỏi coverage thực tế trong kết quả `dev_fit`. Các điểm đường cong cũng giữ nguyên cả nhóm score đồng hạng. Với consensus n=10, số mức score ít nên khác biệt này cần được đặc tả.

**Kiểm chứng bằng hàm hiện tại:** DEV có tám score 0.9 và hai score 0.5, fit mục tiêu 0.7 trả tau=0.9 và coverage DEV=0.8. Áp tau đó lên test có chín score 0.9 và một score 0.5 cho coverage=0.9. Nếu mọi score đều 0.8, đường cong chỉ có điểm coverage=1.0; hàm `selective_risk_at(..., 0.7)` trả risk của điểm đó.

**Tác động:** đặc tả hiện tại không xác định rõ đang kiểm định khả năng xếp hạng confidence ở coverage cố định hay khả năng chuyển ngưỡng từ DEV sang test. Cách diễn giải kết quả và power vì vậy có thể sai.

**Cần làm:** định nghĩa hai phân tích riêng. Với chính sách DEV đã đóng băng, báo coverage thực tế và so C2 trên cùng cell; với đường cong fixed-coverage, ghi chính sách xử lý ties và coverage đạt được. Chốt trước cách gộp single-modality, arm retrieval chính và bootstrap đồng thời mọi điều kiện của cùng injection.

### 3. [P2] Verdict H2 vượt mức bằng chứng mà kế hoạch tự yêu cầu

**Vị trí:** [bảng verdict](research-261019-tong-quan-elicit-chon-dong-gop-nt114.md:29), dòng 29; [kết luận H2](research-261019-tong-quan-elicit-chon-dong-gop-nt114.md:274), dòng 274. Quy tắc đối chiếu ở [plan §5](../261019-1045-chon-dong-gop-khoa-hoc-qua-tong-quan-elicit/plan.md:78), dòng 78–79.

“Chồng lấn có” yêu cầu ít nhất một bài peer-reviewed, relevance 2, có kết quả so sánh được và đã xác minh toàn văn. TraceBudget, VerifyRCA và BudgetSRE đều đang dùng abstract. EviRCA đã đọc toàn văn nhưng là preprint; báo chi phí thấp hơn cũng chưa đồng nghĩa với chính sách thu thập bằng chứng có ngân sách giống H2.

**Tác động:** recap “H2 already done” mạnh hơn chứng cứ và có thể đóng hướng quá sớm. Cờ chất lượng nguồn không chứng minh bài sai; tương tự, DOI và abstract không thay thế xác minh phương pháp.

**Cần làm:** đổi mức kết luận thành “có dấu hiệu chồng lấn mạnh; chưa đạt điều kiện xác nhận theo kế hoạch”. Vẫn có thể không ưu tiên H2 vì phạm vi hiện tại và chi phí đổi protocol. Hai lý do đó phải được tách khỏi kết luận novelty.

### 4. [P2] Phase sàng lọc và một số AC được đánh dấu hoàn tất trước khi đủ bằng chứng kiểm toán

**Vị trí:** [plan AC4/AC6/AC11](../261019-1045-chon-dong-gop-khoa-hoc-qua-tong-quan-elicit/plan.md:125), dòng 125–132; [phase 03](../261019-1045-chon-dong-gop-khoa-hoc-qua-tong-quan-elicit/phase-03-khu-trung-lap-va-sang-loc.md:38), dòng 38–49; [PRISMA](research-261019-tong-quan-elicit-chon-dong-gop-nt114.md:97), dòng 97–130.

Phase 03 yêu cầu quyết định include/exclude/maybe và relevance H1/H2/H3 cho từng bài, kiểm 10% bài Elicit loại, cùng tái sàng lọc 30 bài sau ít nhất 24 giờ. Workspace không có `work/screening.csv`; `corpus.csv` không có các quyết định/relevance thủ công cho 699 works ngoài SR1. Mẫu 127 có 32 bài bị loại, nhỏ hơn 39 bài tương ứng 10% của 390. Không có bằng chứng trong bộ bàn giao cho kiểm tra trễ 24 giờ.

PRISMA còn trộn số record và work: tổng works 1,958 là đúng, nhưng nhánh SR1 sau khử trùng lặp là 1,259 works, không phải 1,267 records ban đầu. Ghép trực tiếp 1,267 với 699 trong sơ đồ làm thừa tám works. 310 full-text exclusions chưa có lý do cũng không đáp ứng nguyên văn AC4 “kèm lý do”.

**Tác động:** không tái dựng được đầy đủ quyết định loại/giữ hoặc tập bài cần đọc toàn văn. Checker hiện tại vẫn pass vì chỉ kiểm tra trường khác rỗng, ID, URL prefix, file và link, không kiểm tra các điều kiện phương pháp này. κ tính đúng nhưng không thay thế các kiểm tra còn thiếu.

**Cần làm:** ghi trạng thái partial cho phần chưa có chứng cứ; bổ sung sổ sàng lọc và luồng record-to-work. Với 310 exclusions chưa biết lý do, giữ trạng thái chưa xác định hoặc giải thích được cơ chế export trước khi gọi là loại vì nội dung. Kiểm tra trễ phải được làm ở thời điểm hợp lệ sau đó.

## Những phần nên giữ

- H1 được thu hẹp rõ; không tuyên bố confidence hoặc abstention trong RCA là mới hoàn toàn. TelemetrySuffBench là một hàng xóm thiết kế thực sự: [abstract gốc](https://arxiv.org/abs/2608.07899).
- H3 không phù hợp làm đóng góp chính với candidate coverage luôn bằng 1. Phân rã retrieval/reranking đã có trong [DecompRCA](https://arxiv.org/html/2609.36686v1).
- Sửa số RE1-TT Retrieval@15 từ 0.98 sang 0.91 cho pipeline +stc là có căn cứ ở bảng của DecompRCA. Hai số thuộc hai cấu hình retriever khác nhau.
- Giữ baseline đơn giản, phân tầng theo dataset, tách DEV và test, gọi việc bỏ telemetry là stress test có kiểm soát, ghi rõ toàn văn unavailable và extraction chưa xong.
- Quy tắc một LLM và giới hạn không chạy model/không sửa input đóng băng được giữ trong artifact đã review. Chưa có chứng cứ chất lượng model thực tế.

## Bước tiếp theo đề nghị

1. Sửa bốn điểm trên trong báo cáo/acceptance record trước khi chuyển kết luận thành preregistration. Không cần mở rộng thành một tổng quan mới toàn bộ 1,958 bài.
2. Đặc tả một contrast chính cho H1: gain selective risk của consensus so với C2 tại coverage được định nghĩa rõ, trên một dataset và arm retrieval chính. Giữ AURC và transfer ngưỡng DEV làm các endpoint được phân biệt rõ.
3. Nếu muốn kiểm tra thiếu telemetry có làm abstention hữu ích hơn không, dùng contrast của gain so với C2 giữa điều kiện đầy đủ và điều kiện bị bỏ telemetry. Chênh lệch thô confidently-wrong giữa hai điều kiện ở §12(c) có thể phản ánh thay đổi độ khó; nó không tự cô lập lợi ích của abstention. Chốt confidence cutoff, mẫu số và trọng số trước.
4. Sau khi đặc tả estimator, tính power/sensitivity bằng chính estimator đó. Dùng kịch bản có ties, nhiều lỗi nền, nhiều mức gain, cấu trúc injection thật và multiplicity nếu có. Đây là mô phỏng thiết kế, không phải kết quả model.
5. Trên máy GPU: hoàn thành Linux portability, GPU probe và feasibility theo runbook hiện hành, rồi chạy DEV pilot. Đo số injection/số lỗi, AC@1, AUROC kèm CI, AURC/gain, phân bố confidence/ties, coverage thực khi chuyển ngưỡng và chi phí. Nếu dùng cùng DEV để fit và đánh giá khả thi, phải ghi độ lạc quan; có thể dùng resampling/cross-fitting trong DEV, không đụng test.
6. Chọn endpoint và family sau pilot cùng power analysis, rồi đóng băng trước test. AUROC thấp hoặc CI rộng là lý do cân nhắc tính khả thi; không dùng riêng điểm ước lượng 0.75 làm điều kiện loại. Kết quả không có ý nghĩa thống kê cũng chưa đủ để kết luận “không có lợi ích” nếu CI vẫn cho phép lợi ích đáng kể.
7. Cập nhật tìm kiếm các bài sát H1 trước preregistration bằng nguồn công khai hiện có. Chạy lại Elicit khi quota được khôi phục nếu vẫn cần; ngày quota không phải điều kiện kỹ thuật để sửa thiết kế hay chuẩn bị pilot.

## Câu hỏi còn mở

- Chọn đường cong confidence ở coverage cố định hay policy chuyển ngưỡng DEV làm endpoint chính?
- Arm retrieval chính và cách gộp điều kiện missingness là gì; mức gain nhỏ nhất đáng quan tâm là bao nhiêu?
- 310 exclusions không ghi lý do là lỗi nội dung, lỗi lấy toàn văn hay trạng thái export?
