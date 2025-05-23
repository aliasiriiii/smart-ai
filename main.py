from flask import Flask, render_template, request
import os
import requests
import openai

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# إعداد GPT
client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# مفتاح OCR.space (استبدله لاحقًا بمفتاحك الخاص)
OCR_SPACE_API_KEY = "helloworld"

# عناصر التقييم التربوي
elements = [
    "أداء الواجبات الوظيفية", "التفاعل مع المجتمع المحلي", "التفاعل مع أولياء الأمور",
    "تنويع استراتيجيات التدريس", "تحسين نواتج المتعلمين", "إعداد وتنفيذ خطة الدرس",
    "توظيف التقنيات", "تهيئة البيئة التعليمية", "ضبط سلوك الطلاب",
    "تحليل نتائج المتعلمين", "تنوع أساليب التقويم"
]

# استخراج النص من الصورة عبر OCR.space
def extract_text_from_image_ocrspace(image_path, api_key):
    with open(image_path, 'rb') as f:
        response = requests.post(
            'https://api.ocr.space/parse/image',
            files={'filename': f},
            data={'apikey': api_key, 'language': 'ara'}
        )
    result = response.json()
    if result.get("IsErroredOnProcessing"):
        return ""
    return result['ParsedResults'][0]['ParsedText']

# تحليل رد GPT وتحويله لجدول
def parse_gpt_response_to_table(gpt_text):
    table = []
    total_score = 0
    lines = gpt_text.strip().split("\n")
    for line in lines:
        if ":" in line:
            parts = line.split(":")
            item_name = parts[0].strip("1234567890.- ").strip()
            rest = ":".join(parts[1:]).strip()
            # توزيع الدرجات حسب الملاحظة:
            words_count = len(rest.split())
            if words_count >= 2:
                score = 5
            elif words_count == 1:
                score = 3
            else:
                score = 1
            table.append({"item": item_name, "score": score, "note": rest})
            total_score += score
    final_score = round(total_score / len(table), 2) if table else 0
    return table, final_score

@app.route('/', methods=['GET', 'POST'])
def index():
    gpt_result = ""
    gpt_table = []
    final_score = 0
    teacher_name = ""
    specialty = ""

    if request.method == 'POST':
        text = ""
        teacher_name = request.form.get("teacher_name", "")
        specialty = request.form.get("specialty", "")
        file = request.files.get('image')
        if file and file.filename:
            path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(path)
            text = extract_text_from_image_ocrspace(path, OCR_SPACE_API_KEY)
        else:
            text = request.form.get("shahid", "")

        if text:
            prompt = "قيّم هذا الشاهد التعليمي وفق 11 عنصر تربوي، لكل عنصر:\n- درجة من 5\n- ملاحظة\n- ثم احسب التقدير النهائي\n\nالنص:\n" + text
            try:
                response = client.chat.completions.create(
                    model="gpt-4",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3
                )
                gpt_result = response.choices[0].message.content
                gpt_table, final_score = parse_gpt_response_to_table(gpt_result)
            except Exception as e:
                gpt_result = f"حدث خطأ أثناء الاتصال بـ GPT: {str(e)}"

    return render_template("index.html",
                           gpt_result=gpt_result,
                           gpt_table=gpt_table,
                           final_score=final_score,
                           teacher_name=teacher_name,
                           specialty=specialty)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
