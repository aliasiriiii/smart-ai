from flask import Flask, render_template, request
from PIL import Image
import pytesseract
import os
import requests
import openai
from rubric_keywords import rubric_keywords

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# تحليل يدوي
def analyze_with_keywords(text):
    result = []
    total_score = 0
    for item in rubric_keywords:
        matched = sum(1 for kw in item["keywords"] if kw in text)
        score = 2 if matched >= 2 else 1 if matched == 1 else 0
        percent = round((score / 2) * item["weight"], 2)
        note = "غير محقق" if score == 0 else "محقق جزئياً" if score == 1 else "محقق تماماً"
        result.append({
            "item": item["item"],
            "weight": item["weight"],
            "score": score,
            "percent": percent,
            "note": note
        })
        total_score += percent
    return result, round(total_score, 2)

# OCR Space
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
    result = []
    grade = None
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

        result, grade = analyze_with_keywords(input_text)

        prompt = f"""حلل الشاهد التربوي التالي باستخدام 11 عنصرًا، لكل عنصر:
- درجة من 5
- ملاحظة
- نسبة مئوية مبنية على وزنه الموضح
ثم احسب التقدير النهائي.

النص:\n{input_text}
"""
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        gpt_result = response.choices[0].message.content

    return render_template("index.html", result=result, grade=grade, gpt_result=gpt_result,
                           teacher_name=teacher_name, job_title=job_title, school=school)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
