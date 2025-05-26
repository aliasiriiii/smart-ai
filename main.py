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

executor = ThreadPoolExecutor(max_workers=4)
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

KEYWORDS = {
    "أداء المهام الوظيفية": ["تحضير", "شرح", "تنفيذ", "جدول", "مهمة", "وظيفي", "متابعة", "إنجاز"],
    "التفاعل الإيجابي مع منسوبي المدرسة والمجتمع": ["زملاء", "فعالية", "مشاركة", "مجتمع", "تعاون", "اجتماع"],
    "التفاعل مع أولياء الأمور": ["ولي أمر", "تواصل", "رسالة", "لقاء", "أولياء"],
    "تنويع استراتيجيات التدريس": ["عصف", "نشط", "مناقشة", "استراتيجية", "طريقة تدريس"],
    "تحسين نواتج التعلم": ["تحسن", "نتائج", "تقدم", "إنجاز", "تحصيل"],
    "إعداد وتنفيذ خطة الدرس": ["خطة", "إعداد", "تنفيذ", "أهداف", "مراحل الدرس"],
    "توظيف التقنيات والوسائل التعليمية": ["تقنية", "فيديو", "بوربوينت", "حاسب", "عرض تقديمي"],
    "تهيئة البيئة التعليمية": ["تهيئة", "صف", "ترتيب", "جو تعليمي", "مقاعد"],
    "ضبط سلوك الطلاب": ["ضبط", "سلوك", "نظام", "التزام", "هدوء"],
    "تحليل نتائج المتعلمين وتشخيص مستواهم": ["تحليل", "تشخيص", "ضعف", "مستوى", "نتائج"],
    "تنويع أساليب التقويم": ["تقويم", "تقييم", "اختبار", "أداة", "ذاتية", "أوراق عمل"]
}

def analyze_gpt_response_with_keywords(gpt_text):
    weights = [10, 10, 10, 10, 10, 10, 10, 5, 5, 10, 10]
    rows = ""
    total_score = 0

    for i, elem in enumerate(REQUIRED_ELEMENTS):
        hits = sum([1 for word in KEYWORDS.get(elem, []) if word in gpt_text])
        score = min(hits, 5) if hits > 0 else 1
        weight = weights[i]
        percent = (score / 5) * 100
        total_score += (percent * weight) / 100
        status = "ممتاز" if score == 5 else "جيد جدًا" if score == 4 else "مقبول" if score == 3 else "ضعيف"
        color = "#d4edda" if score >= 4 else "#fff3cd" if score == 3 else "#f8d7da"
        note = "تم رصد إشارات واضحة" if score > 2 else "إشارات محدودة أو ضعيفة"

        rows += f"<tr style='background:{color};'><td>{elem}</td><td>{score} من 5</td><td>{status}</td><td>{note}</td></tr>"

    final_score_5 = round((total_score / sum(weights)) * 5, 2)
    percent_score = int((total_score / sum(weights)) * 100)

    return f'''
    <div dir="rtl">
        <h3 style="color:#2c3e50;">نتائج التحليل الذكي</h3>
        <table style='width:100%; border-collapse:collapse; margin-top:20px;'>
            <tr style="background-color:#007bff; color:white;">
                <th>العنصر</th><th>الدرجة</th><th>الحالة</th><th>الملاحظات</th>
            </tr>
            {rows}
        </table>
        <div style='margin-top:20px; font-weight:bold;'>الدرجة النهائية: {final_score_5} من 5 ({percent_score}%)</div>
    </div>
    '''

def process_with_gpt(input_text):
    try:
        prompt = f\"""أنت محلل تربوي. اقرأ النص التالي جيدًا واستخرج ما يمكن أن يدل على أداء المعلم في 11 عنصرًا تربويًا رئيسيًا.
لا تكتب جدولًا، فقط قدم تحليلك بشكل عام.

النص:
{input_text}
\"""
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=2500
        )
        gpt_text = response.choices[0].message.content
        return analyze_gpt_response_with_keywords(gpt_text)
    except Exception as e:
        logger.error(f"GPT Error: {e}")
        return "<div style='color:red;'>تعذر التحليل باستخدام GPT</div>"

def extract_text_from_image_ocr_space(image_file):
    """استخراج النص من الصور باستخدام OCR"""
    try:
        response = requests.post(
            'https://api.ocr.space/parse/image',
            files={'file': image_file},
            data={
                'apikey': OCR_API_KEY,
                'language': 'ara',
                'isOverlayRequired': False,
                'detectOrientation': True
            },
            timeout=30
        )
        result = response.json()
        if not result['IsErroredOnProcessing']:
            text = result['ParsedResults'][0]['ParsedText']
            logger.info(f"تم استخراج نص من الصورة: {text[:100]}...")
            return text
        else:
            logger.error(f"خطأ في OCR: {result.get('ErrorMessage', 'Unknown error')}")
            return ""
    except Exception as e:
        logger.error(f"خطأ في استخراج النص من الصورة: {e}")
        return ""

def extract_text_from_pdf(pdf_path):
    """استخراج النص من ملف PDF مع تحسينات"""
    try:
        with open(pdf_path, 'rb') as f:
            pdf_data = f.read()

        images = convert_from_bytes(pdf_data, dpi=200, thread_count=4)
        full_text = ""
        total_pages = len(images)

        for i, img in enumerate(images):
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format='JPEG', quality=80)
            img_byte_arr.seek(0)
            text = extract_text_from_image_ocr_space(img_byte_arr)
            full_text += text + "\n"
            logger.info(f"تم معالجة صفحة {i+1} من {total_pages}")

        return full_text, total_pages
    except Exception as e:
        logger.error(f"خطأ في معالجة PDF: {e}")
        return "", 0

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        try:
            form_data = {
                'teacher_name': request.form.get('teacher_name', '').strip(),
                'job_title': request.form.get('job_title', '').strip(),
                'school': request.form.get('school', '').strip(),
                'principal_name': request.form.get('principal_name', '').strip(),
                'file_link': request.form.get('file_link', '').strip(),
                'shahid_text': request.form.get('shahid', '').strip()
            }

            uploaded_files = {
                'image': request.files.get('image'),
                'pdf_file': request.files.get('pdf_file')
            }

            input_text = form_data['shahid_text']

            # معالجة الملفات المرفوعة إذا لم يكن هناك نص مباشر
            if not input_text:
                if uploaded_files['image'] and uploaded_files['image'].filename:
                    filename = secure_filename(uploaded_files['image'].filename)
                    path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    uploaded_files['image'].save(path)
                    input_text = extract_text_from_image_ocr_space(open(path, 'rb'))
                    os.remove(path)
                    logger.info(f"تم استخراج نص من صورة: {len(input_text)} حرف")
                elif uploaded_files['pdf_file'] and uploaded_files['pdf_file'].filename:
                    filename = secure_filename(uploaded_files['pdf_file'].filename)
                    pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    uploaded_files['pdf_file'].save(pdf_path)
                    input_text, pages = extract_text_from_pdf(pdf_path)
                    os.remove(pdf_path)
                    logger.info(f"تم استخراج نص من PDF: {pages} صفحات، {len(input_text)} حرف")

            # معالجة النص إذا كان موجودًا
            if input_text.strip():
                logger.info(f"بدء تحليل نص بطول {len(input_text)} حرف")
                gpt_result = process_with_gpt(input_text)
            else:
                gpt_result = "<div style='color:red;'>لم يتم تقديم نص للتحليل</div>"
                logger.warning("لا يوجد نص للتحليل")

            return render_template("index.html",
                gpt_result=gpt_result,
                teacher_name=form_data['teacher_name'],
                job_title=form_data['job_title'],
                school=form_data['school'],
                principal_name=form_data['principal_name'])

        except Exception as e:
            logger.error(f"فشل أثناء المعالجة: {e}")
            return render_template("index.html", 
                error_message=f"حدث خطأ أثناء المعالجة: {str(e)}",
                teacher_name=form_data.get('teacher_name', ''),
                job_title=form_data.get('job_title', ''),
                school=form_data.get('school', ''),
                principal_name=form_data.get('principal_name', ''))

    return render_template("index.html")
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, threaded=True, debug=True)
