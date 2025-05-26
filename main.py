from flask import Flask, render_template, request
import os
import requests
import openai
from pdf2image import convert_from_bytes
from PIL import Image
import re
import io
import logging
from werkzeug.utils import secure_filename
from concurrent.futures import ThreadPoolExecutor
import time

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

executor = ThreadPoolExecutor(max_workers=2)
client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
OCR_API_KEY = os.environ.get("OCR_API_KEY")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

REQUIRED_ELEMENTS = [
    "أداء المهام الوظيفية",
    "التفاعل الإيجابي مع منسوبي المدرسة والمجتمع",
    "التفاعل مع أولياء الأمور",
    "تنويع استراتيجيات التدريس",
    "تحسين نواتج التعلم",
    "إعداد وتنفيذ خطة الدرس",
    "توظيف التقنيات والوسائل التعليمية",
    "تهيئة البيئة التعليمية",
    "ضبط سلوك الطلاب",
    "تحليل نتائج المتعلمين وتشخيص مستواهم",
    "تنويع أساليب التقويم"
]

def analyze_with_keywords(input_text):
    weights = [10, 10, 10, 10, 10, 10, 10, 5, 5, 10, 10]
    KEYWORDS = {
        "أداء المهام الوظيفية": ["تحضير", "شرح", "تنفيذ", "جدول"],
        "التفاعل الإيجابي مع منسوبي المدرسة والمجتمع": ["زملاء", "فعالية", "مشاركة", "مجتمع"],
        "التفاعل مع أولياء الأمور": ["ولي أمر", "رسالة", "تواصل", "استدعاء"],
        "تنويع استراتيجيات التدريس": ["نشط", "تعاوني", "عصف", "مناقشة", "مجموعات"],
        "تحسين نواتج التعلم": ["تحسن", "نتائج", "إنجاز", "تقدم"],
        "إعداد وتنفيذ خطة الدرس": ["خطة", "جدول", "مراحل الدرس"],
        "توظيف التقنيات والوسائل التعليمية": ["فيديو", "عرض", "شاشة", "بوربوينت", "تطبيق"],
        "تهيئة البيئة التعليمية": ["تهيئة", "جو صفي", "مقاعد", "مناسب"],
        "ضبط سلوك الطلاب": ["سلوك", "هدوء", "نظام", "إجراءات"],
        "تحليل نتائج المتعلمين وتشخيص مستواهم": ["تحليل", "تشخيص", "مستوى", "ضعف"],
        "تنويع أساليب التقويم": ["اختبار", "تقييم", "أوراق عمل", "مقابلة", "ذاتية"]
    }

    rows = ""
    total_score = 0
    for i, elem in enumerate(REQUIRED_ELEMENTS):
        score = sum([1 for word in KEYWORDS.get(elem, []) if word in input_text])
        score = min(score, 5) if score > 0 else 1
        weight = weights[i]
        percent = (score / 5) * 100
        total_score += (percent * weight) / 100
        status = "ممتاز" if score == 5 else "جيد جدًا" if score == 4 else "مقبول" if score == 3 else "ضعيف"
        color = "#d4edda" if score >= 4 else "#fff3cd" if score == 3 else "#f8d7da"
        note = "تم رصد إشارات مباشرة" if score > 1 else "البيانات غير كافية"

        rows += f"<tr style='background:{color};'><td>{elem}</td><td>{score} من 5</td><td>{status}</td><td>{note}</td></tr>"

    final_score_5 = round((total_score / sum(weights)) * 5, 2)
    percent_score = int((total_score / sum(weights)) * 100)

    return f"""
    <div dir='rtl'>
        <h3 style='color:#2c3e50;'>النتائج التقديرية (تحليل بالكلمات المفتاحية)</h3>
        <table style='width:100%; border-collapse:collapse; margin-top:20px;'>
            <tr style='background-color:#007bff; color:white;'>
                <th>العنصر</th>
                <th>الدرجة</th>
                <th>الحالة</th>
                <th>الملاحظات</th>
            </tr>
            {rows}
        </table>
        <div style='margin-top:30px; font-weight:bold;'>الدرجة النهائية: {final_score_5} من 5 ({percent_score}%)</div>
    </div>
    """

def get_analysis_prompt(input_text):
    table_rows = "\n".join(
        f"<tr><td>{elem}</td><td>X من 5</td><td>[تحليل]</td></tr>"
        for elem in REQUIRED_ELEMENTS
    )
    return f"""
أنت محلل تربوي خبير تتبع إطارًا صارمًا. المطلوب:

1. جدول HTML بالهيكل التالي تمامًا:
<table dir='rtl'>
<tr><th>العنصر</th><th>الدرجة (من 5)</th><th>الملاحظات</th></tr>
{table_rows}
</table>

2. الالتزام الحرفي بالتالي:
- أسماء العناصر كما هي دون تغيير
- استخدم نفس الترتيب المحدد
- التقييم من 5 فقط (1-5)
- اكتب "غير واضح" إذا لم تجد دليلًا
- لا تختصر أو تعدل في الأسماء

3. بعد الجدول، اكتب تحليلًا لكل عنصر:
العنصر 1: [الاسم]
- نقاط القوة: [...]
- مجالات التحسين: [...]
- المقترحات: [...]

النص المطلوب تحليله:
{input_text}
"""

def validate_gpt_response(response_text):
    missing = [e for e in REQUIRED_ELEMENTS if e not in response_text]
    if missing or response_text.count("من 5") < len(REQUIRED_ELEMENTS):
        raise ValueError("التحليل غير مكتمل")
    return response_text

def process_with_gpt(input_text, max_retries=3):
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": get_analysis_prompt(input_text)}],
                temperature=0.2,
                max_tokens=2500
            )
            content = response.choices[0].message.content
            validated = validate_gpt_response(content)
            return calculate_final_score_from_table(validated)
        except Exception as e:
            logger.error(f"GPT فشل المحاولة {attempt+1}: {e}")
            if attempt == max_retries - 1:
                logger.warning("تشغيل التحليل اليدوي بالكلمات المفتاحية")
                return analyze_with_keywords(input_text)
            time.sleep(1)

def extract_text_from_image_ocr_space(image_file):
    try:
        response = requests.post(
            'https://api.ocr.space/parse/image',
            files={'filename': image_file},
            data={'apikey': OCR_API_KEY, 'language': 'ara', 'isOverlayRequired': False}
        )
        result = response.json()
        return result['ParsedResults'][0]['ParsedText'] if not result['IsErroredOnProcessing'] else ""
    except Exception as e:
        logger.error(f"OCR Error: {e}")
        return ""

def extract_text_from_pdf(pdf_path):
    try:
        with open(pdf_path, 'rb') as f:
            pdf_data = f.read()

        images = convert_from_bytes(pdf_data, dpi=150)
        full_text = ""

        for img in images:
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format='JPEG', quality=70)
            img_byte_arr.seek(0)
            text = extract_text_from_image_ocr_space(img_byte_arr)
            full_text += text + "\n"

        return full_text, len(images)
    except Exception as e:
        logger.error(f"PDF Processing Error: {e}")
        return "", 0

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        try:
            form_data = {
                'teacher_name': request.form.get('teacher_name', ''),
                'job_title': request.form.get('job_title', ''),
                'school': request.form.get('school', ''),
                'principal_name': request.form.get('principal_name', ''),
                'file_link': request.form.get('file_link', ''),
                'shahid_text': request.form.get('shahid', '')
            }

            uploaded_files = {
                'image': request.files.get('image'),
                'pdf_file': request.files.get('pdf_file')
            }

            input_text = form_data['shahid_text']

            if not input_text.strip():
                if uploaded_files['image']:
                    filename = secure_filename(uploaded_files['image'].filename)
                    path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    uploaded_files['image'].save(path)
                    input_text = extract_text_from_image_ocr_space(open(path, 'rb'))
                    os.remove(path)
                elif uploaded_files['pdf_file']:
                    filename = secure_filename(uploaded_files['pdf_file'].filename)
                    pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    uploaded_files['pdf_file'].save(pdf_path)
                    input_text, _ = extract_text_from_pdf(pdf_path)
                    os.remove(pdf_path)

            if input_text.strip():
                gpt_result = process_with_gpt(input_text)
            else:
                gpt_result = "<div style='color:red;'>لم يتم تقديم نص للتحليل</div>"

            return render_template("index.html",
                gpt_result=gpt_result,
                teacher_name=form_data['teacher_name'],
                job_title=form_data['job_title'],
                school=form_data['school'],
                principal_name=form_data['principal_name'])

        except Exception as e:
            logger.error(f"فشل أثناء المعالجة: {e}")
            return render_template("index.html", error_message=f"حدث خطأ: {str(e)}")

    return render_template("index.html")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, threaded=True)
