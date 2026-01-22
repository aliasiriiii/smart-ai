import os
import re
import io
import time
import logging
import asyncio
from functools import lru_cache

from flask import Flask, render_template, request
from werkzeug.utils import secure_filename
import requests
import openai
from pdf2image import convert_from_bytes
from PIL import Image
import numpy as np

# إعداد التطبيق
app = Flask(__name__)
app.config.update(
    UPLOAD_FOLDER='uploads',
    MAX_CONTENT_LENGTH=16 * 1024 * 1024,  # 16MB حد أقصى لرفع الملفات
    THREAD_POOL_WORKERS=4
)

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# العناصر التربوية الرسمية
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

ELEMENT_WEIGHTS = np.array([10, 10, 10, 10, 10, 10, 10, 5, 5, 10, 10], dtype=np.float32)
MAX_SCORE = 5

# مفاتيح API
client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
OCR_API_KEY = os.environ.get("OCR_API_KEY")

# تسجيل الأحداث
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler('app.log'), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# الكلمات المفتاحية الموسعة
KEYWORDS = {
    "أداء المهام الوظيفية": ["تحضير", "شرح", "تنفيذ", "جدول", "خطة", "مهمة", "متابعة", "إنجاز", "سجلات", "توزيع"],
    "التفاعل الإيجابي مع منسوبي المدرسة والمجتمع": ["زملاء", "فعالية", "مشاركة", "مجتمع", "تعاون", "اجتماع", "شراكة", "تنسيق"],
    "التفاعل مع أولياء الأمور": ["ولي أمر", "رسالة", "تواصل", "لقاء", "استدعاء", "اجتماع", "إشعار", "تنسيق"],
    "تنويع استراتيجيات التدريس": ["عصف", "نشط", "مناقشة", "استراتيجية", "تعاوني", "مجموعات", "مسرح", "مشروع"],
    "تحسين نواتج التعلم": ["تحسن", "نتائج", "تقدم", "تحصيل", "تميّز", "مخرجات", "نجاح"],
    "إعداد وتنفيذ خطة الدرس": ["خطة", "أهداف", "تحضير", "توزيع", "مراحل الدرس", "تخطيط", "عرض"],
    "توظيف التقنيات والوسائل التعليمية": ["تقنية", "فيديو", "بوربوينت", "حاسب", "تفاعلي", "تطبيق", "شاشة", "ذكية"],
    "تهيئة البيئة التعليمية": ["تهيئة", "صف", "ترتيب", "جو", "إضاءة", "نظافة", "راحة"],
    "ضبط سلوك الطلاب": ["ضبط", "سلوك", "نظام", "التزام", "هدوء", "تحفيز", "قواعد"],
    "تحليل نتائج المتعلمين وتشخيص مستواهم": ["تحليل", "تشخيص", "مستوى", "نتائج", "تقارير", "اختبارات", "ضعف"],
    "تنويع أساليب التقويم": ["تقويم", "تقييم", "اختبار", "أداة", "أوراق عمل", "شفوي", "ملف إنجاز"]
}

# prompt لتحليل GPT
@lru_cache(maxsize=100)
def get_analysis_prompt(input_text: str) -> str:
    return f"""
أنت محلل تربوي متخصص. حلل النص التالي بدقة، واستنتج ما يمكن أن يدل على تحقق عناصر الأداء الوظيفي للمعلم وفق 11 معيارًا معتمدة من وزارة التعليم. لا تكتب جدولًا. فقط استخرج أدلة الأداء، نقاط القوة، وأي مؤشرات تدل على الممارسات التربوية والصفية.

النص:
{input_text}
"""

# تحويل PDF إلى صور
def optimize_pdf_conversion(pdf_data: bytes) -> list:
    return convert_from_bytes(
        pdf_data,
        dpi=150,
        thread_count=os.cpu_count() or 4,
        fmt='jpeg',
        jpegopt={"quality": 70, "optimize": True, "progressive": True}
    )

# استخراج النص من صورة باستخدام OCR.space
async def extract_text_from_image_ocr_space(image_bytes: bytes, filename: str = "image.jpg") -> str:
    if not OCR_API_KEY:
        logger.warning("⚠️ OCR_API_KEY غير موجود")
        return ""

    try:
        def _do_request():
            files = {'file': (filename, image_bytes)}
            data = {
                'apikey': OCR_API_KEY,
                'language': 'ara',
                'isOverlayRequired': False,
                'detectOrientation': True,
                'scale': True
            }
            return requests.post('https://api.ocr.space/parse/image', files=files, data=data, timeout=30)

        response = await asyncio.to_thread(_do_request)
        result = response.json()

        if not result.get('IsErroredOnProcessing', True):
            parsed = result.get('ParsedResults', [])
            if parsed and parsed[0].get('ParsedText'):
                return parsed[0]['ParsedText'].strip()
        return ""
    except Exception as e:
        logger.error(f"OCR Exception: {e}", exc_info=True)
        return ""

# استخراج النص من PDF باستخدام OCR
async def extract_text_from_pdf(pdf_path: str) -> tuple[str, int]:
    try:
        with open(pdf_path, 'rb') as f:
            pdf_data = f.read()

        images = optimize_pdf_conversion(pdf_data)
        total_pages = len(images)
        texts = []

        # تشغيل OCR بشكل متوازٍ مضبوط بعدد THREAD_POOL_WORKERS
        sem = asyncio.Semaphore(app.config['THREAD_POOL_WORKERS'])

        async def _ocr_one(img: Image.Image, idx: int) -> str:
            async with sem:
                img_byte_arr = io.BytesIO()
                img.save(img_byte_arr, format='JPEG', quality=80)
                img_bytes = img_byte_arr.getvalue()
                return await extract_text_from_image_ocr_space(img_bytes, filename=f"page_{idx+1}.jpg")

        tasks = [_ocr_one(img, i) for i, img in enumerate(images)]
        results = await asyncio.gather(*tasks)
        texts.extend(results)

        return "\n".join(filter(None, texts)), total_pages
    except Exception as e:
        logger.error(f"PDF Processing Error: {e}", exc_info=True)
        return "", 0

# تقييم عنصر واحد
def calculate_scores(hits: int) -> tuple[int, str, str, str]:
    score = min(5, max(1, hits))
    status_mapping = {
        5: ("ممتاز", "#d4edda"),
        4: ("جيد جدًا", "#fff3cd"),
        3: ("جيد", "#f8d7da"),
        2: ("مقبول", "#f2f2f2"),
        1: ("ضعيف", "#ffcccc")
    }
    status, color = status_mapping.get(score, ("غير معروف", "#ffffff"))
    note = "إشارات قوية" if score >= 4 else "إشارات متوسطة" if score == 3 else "إشارات ضعيفة"
    return score, status, color, note

# تحليل ناتج GPT باستخدام الكلمات المفتاحية
async def analyze_gpt_response_with_keywords(gpt_text: str) -> str:
    rows = []
    total_weighted_score = 0.0

    for i, elem in enumerate(REQUIRED_ELEMENTS):
        hits = sum(
            1 for kw in KEYWORDS.get(elem, [])
            if re.search(rf'\b{re.escape(kw)}\b', gpt_text, re.IGNORECASE)
        )
        score, status, color, note = calculate_scores(hits)
        weighted_score = (score / MAX_SCORE) * ELEMENT_WEIGHTS[i]
        total_weighted_score += weighted_score

        rows.append(f"""
        <tr style='background:{color};'>
            <td>{elem}</td>
            <td>{score} من {MAX_SCORE}</td>
            <td>{status}</td>
            <td>{note}</td>
        </tr>
        """)

    final_score_5 = round((total_weighted_score / ELEMENT_WEIGHTS.sum()) * MAX_SCORE, 2)
    percent_score = int((total_weighted_score / ELEMENT_WEIGHTS.sum()) * 100)

    return f"""
    <div dir='rtl'>
        <h3 style="color:#2c3e50;">نتائج التحليل الذكي</h3>
        <table class='analysis-table'>
            <thead>
                <tr>
                    <th>العنصر</th>
                    <th>الدرجة</th>
                    <th>الحالة</th>
                    <th>الملاحظات</th>
                </tr>
            </thead>
            <tbody>
                {"".join(rows)}
            </tbody>
        </table>
        <div class='score-summary'>
            الدرجة النهائية: <strong>{final_score_5}</strong> من {MAX_SCORE} ({percent_score}%)
        </div>

        <div class="ai-note-box">
            تم تحليل الشاهد باستخدام نموذج GPT وتحليل دقيق للكلمات المفتاحية لاستخلاص تحقق العناصر التربوية. 
            هذا التحليل مدعوم من الأستاذ <strong>علي عسيري - ثانوية الظهران</strong> وبالذكاء الاصطناعي.
        </div>
    </div>
    """

# إرسال النص إلى GPT ثم تحليل الناتج
async def process_with_gpt(input_text: str, max_retries: int = 3) -> str:
    for attempt in range(max_retries):
        try:
            response = await asyncio.to_thread(
                lambda: client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": get_analysis_prompt(input_text)}],
                    temperature=0.3,
                    max_tokens=3000,
                    timeout=60
                )
            )

            gpt_text = response.choices[0].message.content
            logger.info(f"تم استلام استجابة GPT بطول {len(gpt_text)} حرف")
            return await analyze_gpt_response_with_keywords(gpt_text)

        except Exception as e:
            logger.warning(f"محاولة {attempt + 1} فشلت: {str(e)}")
            if attempt == max_retries - 1:
                logger.warning("الانتقال إلى التحليل باستخدام الكلمات المفتاحية")
                return await analyze_gpt_response_with_keywords(input_text)
            await asyncio.sleep(2 ** attempt)

# نقطة الدخول الرئيسية
@app.route('/', methods=['GET', 'POST'])
async def index():
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

            if not input_text:
                if uploaded_files['image'] and uploaded_files['image'].filename:
                    filename = secure_filename(uploaded_files['image'].filename)
                    path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    uploaded_files['image'].save(path)

                    with open(path, 'rb') as f:
                        img_bytes = f.read()

                    input_text = await extract_text_from_image_ocr_space(img_bytes, filename=filename)
                    os.remove(path)

                elif uploaded_files['pdf_file'] and uploaded_files['pdf_file'].filename:
                    filename = secure_filename(uploaded_files['pdf_file'].filename)
                    pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    uploaded_files['pdf_file'].save(pdf_path)

                    input_text, pages = await extract_text_from_pdf(pdf_path)
                    os.remove(pdf_path)

            if input_text.strip():
                gpt_result = await process_with_gpt(input_text)
            else:
                gpt_result = "<div class='error'>لم يتم تقديم نص للتحليل</div>"

            return render_template(
                "index.html",
                gpt_result=gpt_result,
                **form_data,
                page_count=pages
            )

        except Exception as e:
            logger.error(f"خطأ في المعالجة: {str(e)}", exc_info=True)
            return render_template("index.html", error_message=f"حدث خطأ أثناء التحليل: {str(e)}")

    return render_template("index.html")

if __name__ == '__main__':
    # Render يمرر PORT تلقائياً
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port, threaded=True)
