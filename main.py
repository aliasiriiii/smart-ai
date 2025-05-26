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

# إعداد التطبيق
app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# عدد العمال في الخلفية
executor = ThreadPoolExecutor(max_workers=4)

# إعداد مفاتيح GPT وOCR
client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
OCR_API_KEY = os.environ.get("OCR_API_KEY")

# تفعيل سجل الأخطاء
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# العناصر التربوية الرسمية المطلوبة
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

# قاعدة الكلمات المفتاحية لكل عنصر (نسخة موسعة)
KEYWORDS = {
    "أداء المهام الوظيفية": ["تحضير", "شرح", "تنفيذ", "جدول", "مهمة", "وظيفي", "متابعة", "إنجاز"],
    "التفاعل الإيجابي مع منسوبي المدرسة والمجتمع": ["زملاء", "فعالية", "مشاركة", "مجتمع", "تعاون", "اجتماع"],
    "التفاعل مع أولياء الأمور": ["ولي أمر", "تواصل", "رسالة", "لقاء", "أولياء"],
    "تنويع استراتيجيات التدريس": ["عصف", "نشط", "مناقشة", "استراتيجية", "طريقة تدريس", "تعاوني", "مجموعات"],
    "تحسين نواتج التعلم": ["تحسن", "نتائج", "تقدم", "إنجاز", "تحصيل", "تطور"],
    "إعداد وتنفيذ خطة الدرس": ["خطة", "إعداد", "تنفيذ", "أهداف", "مراحل الدرس", "تخطيط"],
    "توظيف التقنيات والوسائل التعليمية": ["تقنية", "فيديو", "بوربوينت", "حاسب", "عرض", "تفاعلي", "تطبيق"],
    "تهيئة البيئة التعليمية": ["تهيئة", "صف", "ترتيب", "جو تعليمي", "مقاعد", "إضاءة", "نظافة"],
    "ضبط سلوك الطلاب": ["ضبط", "سلوك", "نظام", "التزام", "هدوء", "لوائح"],
    "تحليل نتائج المتعلمين وتشخيص مستواهم": ["تحليل", "تشخيص", "ضعف", "مستوى", "نتائج", "تقارير"],
    "تنويع أساليب التقويم": ["تقويم", "تقييم", "اختبار", "أداة", "ذاتية", "أوراق عمل", "مقابلة"]
}

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

# إعداد التطبيق
app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# عدد العمال في الخلفية
executor = ThreadPoolExecutor(max_workers=4)

# إعداد مفاتيح GPT وOCR
client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
OCR_API_KEY = os.environ.get("OCR_API_KEY")

# تفعيل سجل الأخطاء
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# العناصر التربوية الرسمية المطلوبة
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

# قاعدة الكلمات المفتاحية لكل عنصر (نسخة موسعة)
KEYWORDS = {
    "أداء المهام الوظيفية": ["تحضير", "شرح", "تنفيذ", "جدول", "مهمة", "وظيفي", "متابعة", "إنجاز"],
    "التفاعل الإيجابي مع منسوبي المدرسة والمجتمع": ["زملاء", "فعالية", "مشاركة", "مجتمع", "تعاون", "اجتماع"],
    "التفاعل مع أولياء الأمور": ["ولي أمر", "تواصل", "رسالة", "لقاء", "أولياء"],
    "تنويع استراتيجيات التدريس": ["عصف", "نشط", "مناقشة", "استراتيجية", "طريقة تدريس", "تعاوني", "مجموعات"],
    "تحسين نواتج التعلم": ["تحسن", "نتائج", "تقدم", "إنجاز", "تحصيل", "تطور"],
    "إعداد وتنفيذ خطة الدرس": ["خطة", "إعداد", "تنفيذ", "أهداف", "مراحل الدرس", "تخطيط"],
    "توظيف التقنيات والوسائل التعليمية": ["تقنية", "فيديو", "بوربوينت", "حاسب", "عرض", "تفاعلي", "تطبيق"],
    "تهيئة البيئة التعليمية": ["تهيئة", "صف", "ترتيب", "جو تعليمي", "مقاعد", "إضاءة", "نظافة"],
    "ضبط سلوك الطلاب": ["ضبط", "سلوك", "نظام", "التزام", "هدوء", "لوائح"],
    "تحليل نتائج المتعلمين وتشخيص مستواهم": ["تحليل", "تشخيص", "ضعف", "مستوى", "نتائج", "تقارير"],
    "تنويع أساليب التقويم": ["تقويم", "تقييم", "اختبار", "أداة", "ذاتية", "أوراق عمل", "مقابلة"]
}
# دالة إعداد البرومبت لتحليل GPT بشكل حر
def get_analysis_prompt(input_text):
    return f"""
أنت محلل تربوي متخصص. حلل النص التالي بدقة، واستنتج ما يمكن أن يدل على تحقق عناصر الأداء الوظيفي للمعلم وفق 11 معيارًا معتمدة من وزارة التعليم. لا تكتب جدولًا. فقط استخرج أدلة الأداء، نقاط القوة، وأي مؤشرات تدل على الممارسات التربوية والصفية.

النص:
{input_text}
"""

# دالة استخراج النص من صورة باستخدام OCR.space
def extract_text_from_image_ocr_space(image_file):
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
            logger.info(f"تم استخراج نص من صورة: {text[:100]}...")
            return text
        else:
            logger.error(f"OCR فشل: {result.get('ErrorMessage', 'Unknown error')}")
            return ""
    except Exception as e:
        logger.error(f"OCR Exception: {e}")
        return ""

# دالة استخراج النص من ملف PDF باستخدام pdf2image + OCR
def extract_text_from_pdf(pdf_path):
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
            logger.info(f"تمت معالجة صفحة {i+1} من {total_pages}")

        return full_text, total_pages
    except Exception as e:
        logger.error(f"PDF Processing Error: {e}")
        return "", 0
# دالة تحليل النص الذي أرجعه GPT واستخدام الكلمات المفتاحية لتعبئة الجدول
def analyze_gpt_response_with_keywords(gpt_text):
    weights = [10, 10, 10, 10, 10, 10, 10, 5, 5, 10, 10]
    rows = ""
    total_score = 0

    for i, elem in enumerate(REQUIRED_ELEMENTS):
        hits = sum(1 for kw in KEYWORDS.get(elem, []) if kw in gpt_text)
        score = 1 if hits == 0 else 2 if hits <= 2 else 3 if hits <= 4 else 4 if hits <= 6 else 5
        weight = weights[i]
        percent = (score / 5) * 100
        total_score += (percent * weight) / 100

        status = "ممتاز" if score == 5 else "جيد جدًا" if score == 4 else "جيد" if score == 3 else "مقبول" if score == 2 else "ضعيف"
        color = "#d4edda" if score >= 4 else "#fff3cd" if score == 3 else "#f8d7da" if score == 2 else "#f5f5f5"
        note = "إشارات واضحة" if score >= 4 else "مؤشرات محدودة" if score == 3 else "دليل ضعيف" if score == 2 else "لا توجد إشارات كافية"

        rows += f"""
        <tr style='background:{color};'>
            <td>{elem}</td>
            <td>{score} من 5</td>
            <td>{status}</td>
            <td>{note}</td>
        </tr>
        """

    final_score_5 = round((total_score / sum(weights)) * 5, 2)
    percent_score = int((total_score / sum(weights)) * 100)

    return f"""
    <div dir='rtl'>
        <h3 style="color:#2c3e50;">نتائج التحليل الذكي</h3>
        <table style='width:100%; border-collapse:collapse; margin-top:20px;'>
            <tr style='background-color:#007bff; color:white;'>
                <th>العنصر</th>
                <th>الدرجة</th>
                <th>الحالة</th>
                <th>الملاحظات</th>
            </tr>
            {rows}
        </table>
        <div style='margin-top:30px; font-weight:bold;'>
            الدرجة النهائية: {final_score_5} من 5 ({percent_score}%)
        </div>

        <div class="ai-note-box">
            تم تحليل الشاهد باستخدام نظام تقييم ذكي يعتمد على GPT وفحص الكلمات المفتاحية داخل التحليل لاستخلاص تحقق العناصر التربوية.  
            المنصة تم تطويرها بواسطة الأستاذ علي عسيري – ثانوية الظهران، وهي تجمع بين التحليل التربوي الذكي والمعالجة الآلية الدقيقة.
        </div>
    </div>
    """
# دالة تحليل النص باستخدام GPT ثم تحليل الناتج بالكلمات المفتاحية
def process_with_gpt(input_text, max_retries=3):
    for attempt in range(max_retries):
        try:
            prompt = get_analysis_prompt(input_text)

            response = client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=3000
            )

            gpt_text = response.choices[0].message.content
            logger.info(f"تم استلام استجابة من GPT بطول {len(gpt_text)} حرف")
            return analyze_gpt_response_with_keywords(gpt_text)

        except Exception as e:
            logger.error(f"فشل GPT في المحاولة {attempt+1}: {e}")
            if attempt == max_retries - 1:
                logger.warning("سيتم استخدام التحليل اليدوي بالكلمات المفتاحية")
                return analyze_gpt_response_with_keywords(input_text)
            time.sleep(2)
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
            pages = 0

            # معالجة الملفات إذا لم يتم إدخال نص
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
                    logger.info(f"تم استخراج نص من PDF مكون من {pages} صفحة")

            # بدء التحليل
            if input_text.strip():
                gpt_result = process_with_gpt(input_text)
            else:
                gpt_result = "<div style='color:red;'>لم يتم تقديم نص للتحليل</div>"

            return render_template("index.html",
                gpt_result=gpt_result,
                teacher_name=form_data['teacher_name'],
                job_title=form_data['job_title'],
                school=form_data['school'],
                principal_name=form_data['principal_name'],
                page_count=pages)

        except Exception as e:
            logger.error(f"فشل أثناء المعالجة: {e}")
            return render_template("index.html",
                error_message=f"حدث خطأ أثناء التحليل: {str(e)}")

    return render_template("index.html")
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, threaded=True, debug=True)
