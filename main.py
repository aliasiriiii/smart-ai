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
- إذا ذُكر أو تمت الإشارة إليه بأي طريقة → اكتب (نعم) وامنحه الدرجة الكاملة (2).
- إذا لم يُذكر → اكتب (لا) وامنحه (0).
- احسب النسبة وفق وزن كل عنصر.

**أخرج النتيجة في جدول منسق** يشمل:
- اسم العنصر
- تحقق العنصر (نعم / لا)
- الدرجة من 2
- النسبة المحققة

**ثم أضف في الأسفل ملاحظات نصية تشرح لماذا اعتبرت كل عنصر (متحقق)**، مع ذكر العبارات الدالة التي وجدتها في الشاهد، إن وُجدت.

العناصر هي:
1. أداء الواجبات الوظيفية (10%)
2. التفاعل مع المجتمع المحلي (10%)
3. التفاعل مع أولياء الأمور (10%)
4. تنويع استراتيجيات التدريس (10%)
5. تحسين نواتج المتعلمين (10%)
6. إعداد وتنفيذ خطة الدرس (10%)
7. توظيف تقنيات ووسائل التعليم المناسبة (10%)
8. تهيئة البيئة التعليمية (5%)
9. ضبط سلوك الطلاب (5%)
10. تحليل نتائج المتعلمين وتشخيص مستوياتهم (10%)
11. تنويع أساليب التقويم (10%)

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
