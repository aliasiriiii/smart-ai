from flask import Flask, render_template, request
import os
import requests
import openai
from pdf2image import convert_from_bytes  # تغيير مهم للسرعة
from PIL import Image
import re
import io  # مطلوب للتعامل مع البيانات في الذاكرة
from werkzeug.utils import secure_filename
from concurrent.futures import ThreadPoolExecutor  # للمعالجة المتوازية

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLUPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# تهيئة معالجة متوازية (بدون تعطيل الخطة المجانية)
executor = ThreadPoolExecutor(max_workers=2)

client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
OCR_API_KEY = os.environ.get("OCR_API_KEY")

# دالة OCR محسنة للسرعة
def extract_text_from_image_ocr_space(image_data):
    try:
        response = requests.post(
            'https://api.ocr.space/parse/image',
            files={'file': image_data},
            data={
                'apikey': OCR_API_KEY,
                'language': 'ara',
                'isOverlayRequired': False,
                'scale': True
            },
            timeout=10  # تقليل وقت الانتظار
        )
        result = response.json()
        return result['ParsedResults'][0]['ParsedText'] if not result['IsErroredOnProcessing'] else ""
    except Exception as e:
        print(f"OCR Error: {e}")
        return ""

# دالة PDF محسنة (تعمل في الذاكرة)
def extract_text_from_pdf(pdf_path):
    try:
        with open(pdf_path, 'rb') as f:
            pdf_data = f.read()
        
        images = convert_from_bytes(pdf_data, dpi=150)  # تقليل الدقة لزيادة السرعة
        full_text = ""
        
        for img in images:
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format='JPEG', quality=70)  # ضغط الصورة
            img_byte_arr.seek(0)
            text = extract_text_from_image_ocr_space(img_byte_arr)
            full_text += text + "\n"
        
        return full_text, len(images)
    except Exception as e:
        print(f"PDF Error: {e}")
        return "", 0

# بقية الدوال (generate_progress_bar, calculate_final_score_from_table) تبقى كما هي

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # معالجة الملفات في خيط منفصل (بدون تعطيل الواجهة)
        future = executor.submit(process_uploaded_files, request)
        gpt_result, teacher_name, job_title, school, principal_name = future.result()
        
        return render_template("index.html",
                           gpt_result=gpt_result,
                           teacher_name=teacher_name,
                           job_title=job_title,
                           school=school,
                           principal_name=principal_name)
    
    return render_template("index.html")

def process_uploaded_files(request):
    # ... (نفس منطق معالجة الملفات السابق)
    # يُنفذ في الخيط الخلفي

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, threaded=True)  # تفعيل الخيوط
