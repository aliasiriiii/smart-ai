from flask import Flask, render_template, request
import os
import requests
import openai

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
    return result['ParsedResults'][0]['ParsedText'] if result['IsErroredOnProcessing'] == False else ""

@app.route('/', methods=['GET', 'POST'])
def index():
    gpt_result = ""
    input_text = ""
    teacher_name = request.form.get('teacher_name', '')
    job_title = request.form.get('job_title', '')
    school = request.form.get('school', '')

    if request.method == 'POST':
        file = request.files.get('image')
        if file and file.filename:
            path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(path)
            input_text = extract_text_from_image_ocr_space(path)
        else:
            input_text = request.form.get('shahid', '')

        prompt = f"""
أنت محلل تربوي متخصص في تقييم أداء المعلمين بناءً على شواهد مكتوبة. مهمتك تحليل الشاهد أدناه وفق 11 عنصرًا معتمدة من وزارة التعليم.

لكل عنصر:
- إذا وُجد في الشاهد شاهد واحد فقط → أعطه 3 من 5.
- إذا وُجد شاهدين أو أكثر → أعطه 5 من 5.
- إذا لم يُذكر أي شيء يدل عليه → 0 من 5.

**النسبة تحسب حسب الوزن الوزاري:**
- تهيئة البيئة التعليمية = 5%
- ضبط سلوك الطلاب = 5%
- باقي العناصر = 10%

**أخرج النتيجة على النحو التالي:**

1. جدول HTML منسق يحتوي الأعمدة التالية:
   - اسم العنصر
   - تحقق العنصر (نعم / لا)
   - الدرجة من 5
   - النسبة المحققة / الأصلية (مثال: 6% / 10%)

2. بعد الجدول مباشرة، أضف:
   - المجموع النهائي للنسب المحققة (من 100%)
   - الدرجة النهائية من 5
   - فقرة ملاحظات تحليلية ذكية تشرح لماذا تم اعتبار كل عنصر متحققًا أو لا، مع ذكر العبارات الدالة من الشاهد إن وُجدت.

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
        except Exception as e:
            gpt_result = f"حدث خطأ: {str(e)}"

    return render_template("index.html", gpt_result=gpt_result,
                           teacher_name=teacher_name, job_title=job_title, school=school)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
