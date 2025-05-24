from flask import Flask, render_template, request
import os
import requests
import openai
from pdf2image import convert_from_path
from PIL import Image
import re
from werkzeug.utils import secure_filename

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
OCR_API_KEY = os.environ.get("OCR_API_KEY")

def extract_text_from_image_ocr_space(image_path):
    try:
        with open(image_path, 'rb') as f:
            response = requests.post(
                'https://api.ocr.space/parse/image',
                files={'filename': f},
                data={'apikey': OCR_API_KEY, 'language': 'ara'}
            )
        result = response.json()
        return result['ParsedResults'][0]['ParsedText'] if not result['IsErroredOnProcessing'] else ""
    except:
        return ""

def extract_text_from_pdf(pdf_path):
    images = convert_from_path(pdf_path)
    full_text = ""
    for i, img in enumerate(images):
        img_path = os.path.join(app.config['UPLOAD_FOLDER'], f"page_{i}.jpg")
        img.save(img_path, 'JPEG')
        text = extract_text_from_image_ocr_space(img_path)
        full_text += text + "\n"
    return full_text, len(images)

def generate_progress_bar(percent):
    return f"""
    <div style='background:#eee; border-radius:10px; overflow:hidden; margin-top:10px;'>
      <div style='width:{percent}%; background:#2ecc71; padding:10px; color:white; text-align:center;'>
        {percent}%
      </div>
    </div>
    """

def colorize_table_rows(table_html):
    def get_class_by_score(score):
        if score == 5:
            return 'grade-5'
        elif score == 4:
            return 'grade-4'
        else:
            return 'grade-low'

    pattern = r'(<tr>.*?<td>.*?)(\d)\s*(?:من 5)?(.*?</tr>)'

    def replacer(match):
        prefix, score_str, suffix = match.groups()
        score = int(score_str)
        row_class = get_class_by_score(score)
        return f'<tr class="{row_class}">{prefix}{score_str} من 5{suffix}'

    return re.sub(pattern, replacer, table_html, flags=re.DOTALL)

def inject_link_column(table_html, file_link):
    if not file_link:
        return table_html

    table_html = re.sub(r'(<tr>\s*<th>.+?</th>)', r'\1<th>رابط الشاهد</th>', table_html, count=1)

    table_html = re.sub(
        r'(<tr[^>]*>.*?</tr>)',
        lambda m: re.sub(r'(</tr>)', f"<td><a href='{file_link}' target='_blank'>رابط</a></td>\\1", m.group()),
        table_html,
        flags=re.DOTALL
    )

    return table_html

def calculate_final_score_from_table(table_html):
    weights = [10, 10, 10, 10, 10, 10, 10, 5, 5, 10, 10]
    scores = re.findall(r'>(\d)\s*(?:من 5)?</td>', table_html)
    total_score = 0
    total_weight = 0

    if 7 <= len(scores) <= 11:
        for i, score_str in enumerate(scores):
            if i >= len(weights):
                break
            score = int(score_str)
            percent = (score / 5) * 100
            weight = weights[i]
            total_weight += weight
            total_score += (percent * weight) / 100

        final_score_5 = round((total_score / total_weight) * 5, 2)
        percent_score = int(total_score)
        box = f"<div style='margin-top:20px; font-size:18px; color:#2c3e50; background:#e8f8f5; padding:15px; border-radius:10px;'><strong>الدرجة النهائية:</strong> {final_score_5} من 5 ({percent_score}%)</div>"
        progress = generate_progress_bar(percent_score)
        message = f"<div style='margin-top:10px; font-size:15px; color:#7f8c8d;'>تم الحساب بناءً على {len(scores)} عنصرًا من أصل 11.</div>"
        return box + progress + message
    else:
        return "<div style='color:red;'>تعذر حساب الدرجة النهائية: عدد العناصر أقل من المطلوب (الحد الأدنى 7).</div>"

def append_link_to_analysis(content, file_link):
    if not file_link:
        return content

    modified_lines = []
    for line in content.split("\n"):
        if line.strip().startswith("- العنصر"):
            modified_lines.append(line)
        elif line.strip():
            link_html = f" <span style='color:#7f8c8d; font-size:13px;'> - <a href='{file_link}' target='_blank'>رابط الشاهد</a></span>"
            modified_lines.append(line.strip() + link_html)
        else:
            modified_lines.append("")
    return "\n".join(modified_lines)

@app.route('/', methods=['GET', 'POST'])
def index():
    gpt_result = ""
    teacher_name = request.form.get('teacher_name', '')
    job_title = request.form.get('job_title', '')
    school = request.form.get('school', '')
    principal_name = request.form.get('principal_name', '')
    file_link = request.form.get('file_link', '')
    input_text = ""
    pdf_page_count = 0

    if request.method == 'POST':
        file = request.files.get('image')
        pdf_file = request.files.get('pdf_file')
        if file and file.filename and file.filename.lower().endswith(('.png', '.jpg', '.jpeg')):
            filename = secure_filename(file.filename)
            path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(path)
            input_text = extract_text_from_image_ocr_space(path)
        elif pdf_file and pdf_file.filename and pdf_file.filename.lower().endswith('.pdf'):
            filename = secure_filename(pdf_file.filename)
            pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            pdf_file.save(pdf_path)
            input_text, pdf_page_count = extract_text_from_pdf(pdf_path)
        else:
            input_text = request.form.get('shahid', '')

        prompt = f"""
أنت محلل تربوي متخصص في تقييم أداء المعلمين بناءً على الشواهد المكتوبة أو المصورة. مهمتك تحليل الشاهد أدناه باستخدام العناصر المعتمدة التالية من وزارة التعليم:

1. أداء المهام الوظيفية - 10%
2. التفاعل الإيجابي مع منسوبي المدرسة والمجتمع - 10%
3. التفاعل مع أولياء الأمور - 10%
4. تنويع استراتيجيات التدريس - 10%
5. تحسين نواتج التعلم - 10%
6. إعداد وتنفيذ خطة الدرس - 10%
7. توظيف التقنيات والوسائل التعليمية - 10%
8. تهيئة البيئة التعليمية - 5%
9. ضبط سلوك الطلاب - 5%
10. تحليل نتائج المتعلمين وتشخيص مستواهم - 10%
11. تنويع أساليب التقويم - 10%

لكل عنصر:
- إذا لم يوجد أي شاهد → الدرجة = 1 من 5
- إذا وُجد شاهد واحد فقط → الدرجة = 4 من 5
- إذا وُجد شاهدين أو أكثر → الدرجة = 5 من 5

مهم:
- لا تُدرج أسماء وهمية. استخدم فقط الاسم المدخل: "{teacher_name}"
- إذا كان الشاهد عبارة عن ملف واحد فقط أو مثال واحد، لا توزع الدرجات على أكثر من عنصرين إلا إذا وُجدت أدلة واضحة وسياقات متعددة.

ابدأ دائمًا بتحليل الشاهد من خلال جدول HTML حقيقي باستخدام <table><tr><th><td> فقط. 
تنبيه: إذا لم تبدأ الجدول بهذه الوسوم، فلن يتم عرض التحليل ولن تظهر النتائج. 
لا تستخدم Markdown أو أعمدة مفصولة بشرطات أو نقاط. فقط جدول HTML متكامل.ثم بعد الجدول مباشرة، أضف ملاحظات تحليلية لكل عنصر بهذا الشكل:
- "العنصر 1: أداء المهام الوظيفية"
- وتحتها الملاحظة التفسيرية
- اترك سطرًا فارغًا بين كل عنصر وآخر

النص:
{input_text}
"""
try:
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
    )

    content = response.choices[0].message.content

    if "<table" not in content or "<tr>" not in content or "<td>" not in content:
        gpt_result = "<div style='color:red;'>لم يتم توليد جدول التحليل من قبل GPT. يرجى التأكد من صيغة الشاهد أو إعادة المحاولة بعد تعديل التنسيق.</div>"
    else:
        content_with_links = append_link_to_analysis(content, file_link)
        colored_table = colorize_table_rows(content_with_links)
        colored_table = inject_link_column(colored_table, file_link)
        final_score_block = calculate_final_score_from_table(content)
        page_info = f"<div style='margin-top:10px; font-size:15px; color:#5d6d7e;'>عدد الصفحات المحللة من PDF: {pdf_page_count}</div>" if pdf_page_count else ""
        gpt_result = f"<h3>تحليل الشاهد المقدم من: {teacher_name}</h3><br>" + colored_table + final_score_block + page_info

except Exception as e:
    gpt_result = f"<div style='color:red;'>حدث خطأ أثناء التحليل: {str(e)}</div>"            gpt_result = f"<div style='color:red;'>حدث خطأ أثناء التحليل: {str(e)}</div>"

    return render_template("index.html",
                           gpt_result=gpt_result,
                           teacher_name=teacher_name,
                           job_title=job_title,
                           school=school,
                           principal_name=principal_name)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
