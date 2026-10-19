from pathlib import Path
import hashlib
import json
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'plans/reports/bao-cao-tien-do-nt114-2026-10-16.docx'
ASSETS = Path(__file__).resolve().parent
sources = [
    ROOT / 'plans/reports/research-261012-q1-survey-and-directions.md',
    ROOT / 'nt114-rca/nt114-rca/releases/nt114-data-v1.json',
    ROOT / 'plans/261015-0047-nt114-rca-llm-jev-research-and-implementation/decisions.md',
    ROOT / 'plans/reports/docs-261015-1642-repository-transfer-audit.md',
]
before = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}

doc = Document()
sec = doc.sections[0]
sec.page_width, sec.page_height = Inches(8.5), Inches(11)
sec.top_margin, sec.bottom_margin = Inches(.65), Inches(.65)
sec.left_margin, sec.right_margin = Inches(.8), Inches(.8)
sec.header_distance, sec.footer_distance = Inches(.25), Inches(.3)

for style_name in ['Normal', 'Title', 'Subtitle', 'Heading 1', 'Heading 2', 'List Bullet', 'List Number']:
    style = doc.styles[style_name]
    style.font.name = 'Times New Roman'
    style.font.color.rgb = RGBColor(0, 0, 0)
    style.element.get_or_add_rPr().get_or_add_rFonts().set(qn('w:eastAsia'), 'Times New Roman')
normal = doc.styles['Normal']
normal.font.size = Pt(12)
normal.paragraph_format.line_spacing = 1.08
normal.paragraph_format.space_after = Pt(6)
normal.paragraph_format.widow_control = True
title = doc.styles['Title']
title.font.size, title.font.bold = Pt(16), True
title.paragraph_format.space_after = Pt(6)
title.paragraph_format.line_spacing = 1
h = doc.styles['Heading 1']
h.font.size, h.font.bold = Pt(12.5), True
h.paragraph_format.space_before, h.paragraph_format.space_after = Pt(9), Pt(4)
h.paragraph_format.keep_with_next = True

p = doc.add_paragraph('BÁO CÁO TIẾN ĐỘ NGHIÊN CỨU', 'Title')
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
p = doc.add_paragraph('Chẩn đoán nguyên nhân sự cố microservice\nkhi thiếu dữ liệu giám sát')
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
p.paragraph_format.space_after = Pt(3)
for r in p.runs:
    r.bold = True
p = doc.add_paragraph('Môn NT114  |  Cập nhật ngày 16 tháng 10 năm 2026')
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
p.paragraph_format.space_after = Pt(10)
for r in p.runs:
    r.font.size = Pt(10.5)

doc.add_paragraph('Đến hiện tại, em đã hoàn thành phần mã nguồn phục vụ thử nghiệm và commit lên repository. Em chưa chạy được trên GPU nên chưa có kết quả thực nghiệm để đánh giá độ chính xác hoặc hiệu quả của phương pháp.')

doc.add_heading('1 Công việc đã thực hiện', 1)
items = [
    ('Khảo sát tài liệu và xác định bài toán. ', 'Em đã tổng hợp tài liệu về phân tích nguyên nhân gốc bằng mô hình ngôn ngữ lớn (LLM), truy hồi thông tin và độ tin cậy của câu trả lời. Hướng đang tập trung là xem việc thiếu log, chỉ số vận hành hoặc dữ liệu truy vết ảnh hưởng thế nào đến chẩn đoán.'),
    ('Viết mã xử lý dữ liệu. ', 'Đã có mã đọc và chuẩn hóa bốn nguồn RCAEval, Nezha, AIOps2025 và RCA100 về cùng cấu trúc. Phần này có tách dữ liệu đầu vào khỏi đáp án, chia tập dữ liệu và tạo các trường hợp thiếu thông tin để phục vụ so sánh.'),
    ('Xây dựng luồng thử nghiệm. ', 'Đã viết các bước tổng hợp thông tin sự cố, tìm sự cố tương tự, gọi LLM và chấm điểm câu trả lời. Đã có mã tích hợp Jev để lựa chọn chấp nhận câu trả lời, tìm thêm thông tin, chuyển sang mô hình khác hoặc từ chối kết luận.'),
    ('Chuẩn bị phần đánh giá và triển khai. ', 'Đã bổ sung mã cho các phương pháp so sánh, thống kê kết quả và kiểm tra tránh đưa đáp án vào đầu vào mô hình. Mã nguồn, cấu hình và hướng dẫn chuyển sang máy GPU đã được commit để tiếp tục triển khai.'),
]
for lead, body in items:
    p = doc.add_paragraph()
    p.add_run(lead).bold = True
    p.add_run(body)

doc.add_heading('2 Tình trạng hiện tại', 1)
doc.add_paragraph('Phần triển khai hiện mới dừng ở viết code và commit. Chưa chạy mô hình thật trên GPU, chưa gọi Jev thật và chưa thực hiện bộ thí nghiệm chính. Vì vậy, hiện chưa có số liệu về độ chính xác, thời gian xử lý hay mức cải thiện so với các phương pháp so sánh. Phần tinh chỉnh mô hình cũng chưa thực hiện.')

doc.add_heading('3 Công việc tiếp theo', 1)
for text in [
    'Thiết lập môi trường trên máy GPU, kiểm tra dữ liệu và khả năng chạy mô hình với bộ nhớ hiện có.',
    'Chạy thử trên một tập dữ liệu nhỏ, kiểm tra đầu ra của LLM và kết nối Jev; sửa các lỗi phát sinh khi chạy thực tế.',
    'Sau khi chạy thử ổn định, thực hiện các thí nghiệm so sánh giữa dữ liệu đầy đủ và dữ liệu thiếu, rồi tổng hợp kết quả để báo cáo thầy.',
]:
    p = doc.add_paragraph(text, 'List Number')
    p.paragraph_format.space_after = Pt(4)

foot = sec.footer.paragraphs[0]
foot.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = foot.add_run()
field = OxmlElement('w:fldSimple')
field.set(qn('w:instr'), 'PAGE')
run._r.addnext(field)
doc.core_properties.title = 'Báo cáo tiến độ nghiên cứu NT114 ngày 16 tháng 10 năm 2026'
doc.core_properties.subject = 'Tiến độ mã nguồn và kế hoạch chạy thử trên GPU'
doc.core_properties.author = ''
doc.core_properties.last_modified_by = ''
for element in [doc.styles.element, doc.element]:
    for border in list(element.iter(qn('w:pBdr'))):
        border.getparent().remove(border)
    for fonts in element.iter(qn('w:rFonts')):
        for key in list(fonts.attrib):
            if key.rsplit('}', 1)[-1].endswith('Theme'):
                del fonts.attrib[key]
doc.save(OUT)

after = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
assert before == after
receipt = {
    'output': str(OUT),
    'input_hashes_before': before,
    'input_hashes_after': after,
    'status_authority': 'User clarification in this conversation: code completed and committed; no GPU execution.',
    'editorial_changes': [
        'Converted internal implementation descriptions into short Vietnamese paragraphs for the advisor.',
        'Removed test counts, software milestone codes, baseline metrics and release acceptance wording.',
        'Described implemented modules as written code; did not claim successful real-model execution.',
    ],
    'factual_delta': {'added_results': [], 'strengthened_claims': [], 'unresolved_factual_changes': []},
    'output_sha256': hashlib.sha256(OUT.read_bytes()).hexdigest(),
}
(ASSETS / 'authoring-receipt.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')
print(OUT)
