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

# تكوين نظام التسجيل
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# العناصر الإجبارية المطلوبة
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
    missing_elements = []
    for element in REQUIRED_ELEMENTS:
        if element not in response_text:
            missing_elements.append(element)
    
    if missing_elements:
        raise ValueError(f"العناصر الناقصة: {', '.join(missing_elements)}")
    
    # التحقق من وجود التقييمات
    if response_text.count("من 5") < len(REQUIRED_ELEMENTS):
        raise ValueError("تقييمات ناقصة")
    
    return response_text

def generate_fallback_response():
    table_rows = "\n".join(
        f"<tr><td>{elem}</td><td>غير محدد</td><td>بيانات غير كافية</td></tr>"
        for elem in REQUIRED_ELEMENTS
    )
    
    return f"""
    <div style='color: #dc3545; padding: 15px; border: 1px solid #f5c6cb; background-color: #f8d7da; border-radius: 5px;'>
        <h3>⚠️ حدث خطأ في التحليل</h3>
        <p>تعذر تحليل النص بشكل كامل. الجدول التالي يحتوي على القيم الافتراضية:</p>
        <table dir='rtl' style='width:100%; margin-top:15px; border-collapse: collapse;'>
            <tr style='background-color: #007bff; color: white;'>
                <th>العنصر</th><th>الدرجة</th><th>الملاحظات</th>
            </tr>
            {table_rows}
        </table>
    </div>
    """

def process_with_gpt(input_text, max_retries=3):
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[{
                    "role": "user",
                    "content": get_analysis_prompt(input_text)
                }],
                temperature=0.2,
                max_tokens=2500
            )
            
            content = response.choices[0].message.content
            validated_content = validate_gpt_response(content)
            return calculate_final_score_from_table(validated_content)
            
        except Exception as e:
            logger.error(f"المحاولة {attempt+1} فشلت: {str(e)}")
            if attempt == max_retries - 1:
                logger.error("فشل جميع المحاولات، استخدام النتيجة الاحتياطية")
                return generate_fallback_response()
            time.sleep(1)

# باقي الدوال الأصلية (بدون تعديل)
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

def generate_progress_bar(percent):
    return f"""
    <div style='background:#eee; border-radius:10px; overflow:hidden; margin-top:10px;'>
      <div style='width:{percent}%; background:#2ecc71; padding:10px; color:white; text-align:center;'>
        {percent}%
      </div>
    </div>
    """

def calculate_final_score_from_table(gpt_response):
    weights = [10, 10, 10, 10, 10, 10, 10, 5, 5, 10, 10]
    
    try:
        scores = re.findall(r'<td>(\d+)\s*من 5</td>', gpt_response)
        scores = [int(score) for score in scores][:len(REQUIRED_ELEMENTS)]
        
        notes = []
        for i in range(1, len(REQUIRED_ELEMENTS)+1):
            pattern = rf"العنصر {i}:.*?-\s*نقاط القوة:\s*(.*?)\s*-\s*مجالات التحسين:\s*(.*?)\s*-\s*المقترحات:\s*(.*?)(?=\n\n|$)"
            match = re.search(pattern, gpt_response, re.DOTALL)
            notes.append({
                'strengths': match.group(1).strip() if match else "لا توجد ملاحظة",
                'improvements': match.group(2).strip() if match else "لا توجد ملاحظة",
                'suggestions': match.group(3).strip() if match else "لا توجد ملاحظة"
            })

        total_score = 0
        rows = ""
        
        for i in range(len(REQUIRED_ELEMENTS)):
            score = scores[i] if i < len(scores) else 1
            weight = weights[i]
            note = notes[i]
            
            status = "ممتاز" if score == 5 else "جيد جدًا" if score == 4 else "مقبول" if score == 3 else "ضعيف"
            color = "#d4edda" if score >= 4 else "#fff3cd" if score == 3 else "#f8d7da"
            
            rows += f"""
            <tr style='background:{color};'>
                <td>{REQUIRED_ELEMENTS[i]}</td>
                <td>{score} من 5</td>
                <td>{status}</td>
                <td>
                    <strong>نقاط القوة:</strong> {note['strengths']}<br>
                    <strong>مجالات التحسين:</strong> {note['improvements']}<br>
                    <strong>المقترحات:</strong> {note['suggestions']}
                </td>
            </tr>
            """
            total_score += (score / 5) * weight

        final_score_5 = round((total_score / sum(weights)) * 5, 2)
        percent_score = int((total_score / sum(weights)) * 100)

        return f"""
        <div dir='rtl'>
            <h3 style='color:#2c3e50;'>نتائج التحليل</h3>
            <table style='width:100%; border-collapse:collapse; margin-top:20px;'>
                <tr style='background-color:#007bff; color:white;'>
                    <th>العنصر</th>
                    <th>الدرجة</th>
                    <th>الحالة</th>
                    <th>الملاحظات</th>
                </tr>
                {rows}
            </table>
            
            <div style='margin-top:30px; padding:15px; background:#f8f9fa; border-radius:5px;'>
                <h4 style='color:#2c3e50;'>الدرجة النهائية: {final_score_5} من 5 ({percent_score}%)</h4>
                {generate_progress_bar(percent_score)}
            </div>
            
            <div style='margin-top:20px; padding:15px; background:#e2e3e5; border-radius:5px;'>
                <h4 style='color:#2c3e50;'>التفاصيل الكاملة:</h4>
                <div style='white-space:pre-line;'>{gpt_response}</div>
            </div>
        </div>
        """
    except Exception as e:
        logger.error(f"Error in score calculation: {e}")
        return generate_fallback_response()

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
            logger.error(f"Request processing failed: {e}")
            return render_template("index.html", 
                               error_message=f"حدث خطأ: {str(e)}")
    
    return render_template("index.html")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, threaded=True)





