from flask import Flask, render_template, request
import os
import requests
import openai
from pdf2image import convert

أكيد يا علي، تفضل الآن نسخة **نظيفة 100%** من ملف `main.py`،  
جاهزة للنسخ بدون أي رموز خفية أو مشاكل — ومطابقة تمامًا للتعديلات الأخيرة:

---

## **`main.py` كامل ومحدث**

```python
from flask import Flask, render_template, request
import os
import requests
import openai
from pdf2image import convert_from_path
from PIL import Image

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

def extract_text_from_image_ocr_space(image_path):
    api_key = "helloworld"  # استبدلها بمفتاحك الحقيقي من OCR.space
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

@app.route('/', methods=['GET', 'POST'])
def index():
    gpt_result = ""
    final_score = None
    final_percentage = None

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

        if input_text.strip():
            prompt = f"""
أنت محلل تربوي متخصص في تقييم أداء المعلمين بناءً على الشواهد المكتوبة أو المصورة. مهمتك تحليل الشاهد أدناه باستخدام العناصر المعتمدة من وزارة التعليم.

ملاحظة مهمة: لا تذكر أسماء أشخاص (مثل المعلم/المعلمة) ما لم تكن واردة صراحة في الشاهد.

نص الشاهد:
{input_text}
"""

            try:
                response = client.chat.completions.create(
                    model="gpt-4",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3
                )
                gpt_result = response.choices[0].message.content

                # حساب الدرجات - مؤقتًا ثابتة، ويمكن تطويرها لاحقًا من gpt_result
                final_score = 5
                final_percentage = 92

            except Exception as e:
                gpt_result = f"حدث خطأ: {str(e)}"

    return render_template("index.html",
                           gpt_result=gpt_result,
                           teacher_name=teacher_name,
                           job_title=job_title,
                           school=school,
                           principal_name=principal_name,
                           final_score=final_score,
                           final_percentage=final_percentage)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
