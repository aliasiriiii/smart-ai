from flask import Flask, render_template, request
import os
import requests
import openai
from pdf2image import convert_from_path
from PIL import Image
import re

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

def extract_text_from_image_ocr_space(image_path):
    api_key = "helloworld"
    with open(image_path, 'rb') as f:
        response = requests.post(
            'https://api.ocr.space/parse/image',
            files={'filename': f},
            data={'apikey': api_key, 'language': 'ara'}
        )
    result = response.json()
    return result['ParsedResults'][0]['ParsedText'] if not result['IsErroredOnProcessing'] else ""

def extract_text_from_pdf(pdf_path):
    images = convert_from_path(pdf_path)
    full_text = ""
    for i, img in enumerate(images):
        img_path = os.path.join(app.config['UPLOAD_FOLDER'], f"page_{i}.jpg")
        img.save(img_path, 'JPEG')
        text = extract_text_from_image_ocr_space(img_path)
        full_text += text + "\n"
    return full_text

def calculate_final_score_from_table(table_html):
    weights = [10, 10, 10, 10, 10, 10, 10, 5, 5, 10, 10]
    scores = re.findall(r'<td>(\d+) من 5</td>\s*<td>(\d+)%</td>', table_html)
    total_score = 0
    if len(scores) == len(weights):
        for i, (score_str, percent_str) in enumerate(scores):
            percent = int(percent_str)
            weight = weights[i]
            total_score += (percent * weight) / 100
        final_score_5 = round((total_score / 100) * 5, 2)
        return f"<div style='margin-top:20px; font-size:18px; color:#2c3e50; background:#fef9e7; padding:15px; border-radius:10px;'><strong>الدرجة النهائية:</strong> {final_score_5} من 5 ({int(total_score)}%)</div>"
    return ""

@app.route('/', methods=['GET', 'POST'])
def index():
    gpt_result = ""
    teacher_name = request.form.get('teacher_name', '')
    job_title = request.form.get('job_title', '')
    school = request.form.get('school', '')
    principal_name = request.form.get('principal_name', '')
    input_text = ""

    if request.method == 'POST':
        file = request.files.get('image')
        pdf_file = request.files.get('pdf_file')
        if file and file.filename:
            path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(path)
            input_text = extract_text_from_image_ocr_space(path)
        elif pdf_file and pdf_file.filename:
            pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], pdf_file.filename)
            pdf_file.save(pdf_path)
            input_text = extract_text_from_pdf(pdf_path)
        else:
            input_text = request.form.get('shahid', '')

        prompt = f"""
أنت محلل تربوي متخصص في تقييم أداء المعلمين بناءً على الشواهد المكتوبة أو المصورة. مهمتك تحليل الشاهد أدناه باستخدام العناصر المعتمدة التالية من وزارة التعليم:

1. أداء الواجبات الوظيفية - 10%
2. التفاعل مع المجتمع المحلي - 10%
3. التفاعل مع أولياء الأمور - 10%
4. تنويع استراتيجيات التدريس - 10%
5. تحسين نواتج المتعلمين - 10%
6. إعداد وتنفيذ خطة الدرس - 10%
7. توظيف التقنيات والوسائل التعليمية - 10%
8. تهيئة البيئة التعليمية - 5%
9. ضبط سلوك الطلاب - 5%
10. تحليل نتائج المتعلمين وتشخيص مستواهم - 10%
11. تنوع أساليب التقويم - 10%

لكل عنصر:
- إذا لم يوجد أي شاهد → الدرجة = 1 من 5
- إذا وُجد شاهد واحد فقط → الدرجة = 4 من 5
- إذا وُجد شاهدين أو أكثر → الدرجة = 5 من 5

ثم احسب النسبة المحققة لكل عنصر بناءً على وزنه.

ابدأ دائمًا بإخراج جدول HTML منسق باستخدام <table><tr><th><td> فقط، لا تستخدم Markdown أو تنسيق نصي.

ثم بعد الجدول مباشرة، أضف ملاحظات تحليلية لكل عنصر بهذا التنسيق:
- "العنصر 1: أداء الواجبات الوظيفية"
- تحته: الملاحظة التي تشرح لماذا اعتبرت العنصر متحقق أو غير متحقق
- اترك سطرًا فارغًا بين كل عنصر وآخر

لا تعتبر وجود كلمات مثل "اختبار"، "كتاب"، "مقرر"، "ورقة عمل" أو "وسيلة" كافية بدون وجود دلالة تربوية واضحة مثل "تحليل نتائج"، "تقويم تكويني"، "خطة علاجية"، أو استخدام فعلي لأداة تدريسية أو تقويمية داخل السياق.

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
            final_score_block = calculate_final_score_from_table(content)
            gpt_result = content + final_score_block
        except Exception as e:
            gpt_result = f"حدث خطأ: {str(e)}"

    return render_template("index.html",
                           gpt_result=gpt_result,
                           teacher_name=teacher_name,
                           job_title=job_title,
                           school=school,
                           principal_name=principal_name)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
