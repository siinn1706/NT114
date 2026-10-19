from pathlib import Path
import hashlib
import json
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn

ROOT = Path(__file__).resolve().parents[3]
original = ROOT / 'plans/reports/bao-cao-tien-do-nt114-2026-10-16.docx'
output = ROOT / 'plans/reports/bao-cao-tien-do-nt114-2026-10-16-ban-sua.docx'
original_hash = hashlib.sha256(original.read_bytes()).hexdigest()
doc = Document(original)
body = doc.element.body
for element in list(body):
    if element.tag != qn('w:sectPr'):
        body.remove(element)

section = doc.sections[0]
section.top_margin = section.bottom_margin = Inches(.8)
section.left_margin = section.right_margin = Inches(.85)
for p in section.footer.paragraphs:
    p.clear()

normal = doc.styles['Normal']
normal.font.name = 'Times New Roman'
normal.font.size = Pt(13)
normal.font.color.rgb = RGBColor(0, 0, 0)
normal.paragraph_format.line_spacing = 1.15
normal.paragraph_format.space_after = Pt(7)
normal.paragraph_format.first_line_indent = None
title = doc.styles['Title']
title.font.name = 'Times New Roman'
title.font.size = Pt(14)
title.font.bold = True
title.paragraph_format.space_after = Pt(8)

p = doc.add_paragraph('BÁO CÁO TIẾN ĐỘ ĐỀ TÀI', 'Title')
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
p = doc.add_paragraph('Ngày 16/10/2026')
p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
doc.add_paragraph('Đề tài: Chẩn đoán nguyên nhân sự cố microservice khi thiếu dữ liệu giám sát.')
doc.add_paragraph('Em gửi thầy phần tiến độ em đã làm đến hiện tại. Phần code đã viết xong và commit lên GitHub, nhưng em chưa chạy được trên GPU nên chưa có kết quả để báo cáo thầy.')

p = doc.add_paragraph()
p.add_run('1. Những phần em đã làm').bold = True
p.paragraph_format.keep_with_next = True

paragraphs = [
    '- Em đã đọc và tổng hợp các tài liệu liên quan đến việc dùng LLM để tìm nguyên nhân sự cố. Hiện em tập trung vào trường hợp hệ thống bị thiếu log, các chỉ số vận hành hoặc trace, để xem mô hình có còn chẩn đoán đúng hay không.',
    '- Về dữ liệu, em đã viết code đọc bốn bộ RCAEval, Nezha, AIOps2025 và RCA100 rồi đưa về cùng một định dạng. Trong code có chia tập dữ liệu, tách riêng đáp án và tạo các trường hợp thiếu dữ liệu để dùng cho thí nghiệm sau này.',
    '- Phần xử lý chính đã có code tổng hợp thông tin sự cố, tìm các sự cố tương tự, gọi LLM và chấm điểm câu trả lời. Em cũng đã viết phần tích hợp Jev để chọn xem nên nhận câu trả lời, tìm thêm thông tin, dùng mô hình khác hay chưa đưa ra kết luận.',
    '- Ngoài ra, em đã viết các phương pháp dùng để so sánh, phần thống kê kết quả và các kiểm tra để tránh đưa đáp án vào đầu vào của mô hình. Cấu hình chạy và hướng dẫn chuyển sang máy GPU cũng đã có trong repository.',
]
for text in paragraphs:
    doc.add_paragraph(text)

p = doc.add_paragraph()
p.add_run('2. Phần còn lại').bold = True
p.paragraph_format.keep_with_next = True
doc.add_paragraph('Hiện các phần trên mới dừng ở code và commit. Em chưa chạy mô hình thật trên GPU, chưa gọi Jev thật và cũng chưa tinh chỉnh mô hình. Vì vậy, em chưa có số liệu về độ chính xác, thời gian chạy hoặc kết quả so sánh giữa các cách làm.')
doc.add_paragraph('Tiếp theo, em sẽ cài môi trường trên máy GPU và chạy thử một phần dữ liệu nhỏ trước. Khi chạy được, em sẽ kiểm tra đầu ra, sửa lỗi phát sinh rồi mới chạy các thí nghiệm với dữ liệu đầy đủ và dữ liệu thiếu. Sau đó em sẽ tổng hợp kết quả để gửi thầy xem.')

for element in [doc.styles.element, doc.element]:
    for border in list(element.iter(qn('w:pBdr'))):
        border.getparent().remove(border)
    for fonts in element.iter(qn('w:rFonts')):
        for key in list(fonts.attrib):
            if key.rsplit('}', 1)[-1].endswith('Theme'):
                del fonts.attrib[key]
doc.core_properties.title = 'Báo cáo tiến độ đề tài NT114'
doc.save(output)
assert hashlib.sha256(original.read_bytes()).hexdigest() == original_hash
receipt = {
    'input': str(original), 'input_sha256': original_hash,
    'output': str(output), 'output_sha256': hashlib.sha256(output.read_bytes()).hexdigest(),
    'style_changes': [
        'Replaced impersonal module summaries with first-person student prose addressed to the advisor.',
        'Removed subtitle block, page footer and repeated bold paragraph leads.',
        'Used a plain date, two manually numbered section labels and ordinary dash paragraphs.',
    ],
    'factual_delta': {'new_claims': [], 'changed_numbers': [], 'changed_execution_status': []},
}
Path(__file__).with_name('student-revision-receipt.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')
print(output)
