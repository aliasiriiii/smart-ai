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
    teacher_name = request.form.get('teacher_name', '').strip()
    job_title = request.form.get('job_title', '')
    school = request.form.get('school', '')
    principal_name = request.form.get('principal_name', '').strip()

    if request.method == 'POST':
        file = request.files.get('image')
        if file and file.filename:
            path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(path)
            input_text = extract_text_from_image_ocr_space(path)
        else:
            input_text = request.form.get('shahid', '')

        name_usage = f"استخدم اسم المعلم في الملاحظات: {teacher_name}." if teacher_name else "لا تستخدم أي أسماء أشخاص. استخدم فقط تعبير 'المعلم'."

        prompt = f"""
أنت محلل تربوي متخصص في تقييم أداء المعلمين بناءً على شواهد مكتوبة. مهمتك تحليل الشاهد أدناه وفق العناصر الرسمية المعتمدة فقط.

لكل عنصر:
- إذا وُجد شاهد واحد → الدرجة = 3 من 5.
- إذا وُجد شاهدين أو أكثر → الدرجة = 5 من 5.
- إذا لم يُذكر شيء يدل عليه → الدرجة = 0.

احسب النسبة المحققة بناء على الوزن التالي:
- تهيئة البيئة التعليمية = 5%
- ضبط سلوك الطلاب = 5%
- باقي العناصر = 10%

اعرض النتيجة بصيغة جدول HTML يحتوي الأعمدة التالية:
- اسم العنصر
- تحقق العنصر (نعم / لا)
- الدرجة من 5
- النسبة المحققة / الأصلية (مثال: 6% / 10%)

بعد الجدول، أضف:
- المجموع الكلي للنسب المحققة من 100%
- الدرجة النهائية من 5
- ملاحظات تحليلية ذكية بناءً على الشاهد، توضّح سبب تحقق أو عدم تحقق كل عنصر.

تأكد من أنك تفسر العبارات التربوية المتنوعة بشكل ذكي.
حتى لو لم تُذكر الكلمات المطابقة بالضبط لاسم العنصر، فمثلاً:

- "تعليق لوحات تعليمية" = تهيئة البيئة التعليمية
- "وزع شهادات شكر" = ضبط سلوك الطلاب
- "ملف إنجاز" = تنويع أساليب التقويم
- "رسائل نصية وتقارير متابعة" = تفاعل مع أولياء الأمور
- "حللت نتائج الطلاب" = تحليل نتائج وتشخيص

واعتبر العنصر محققًا إذا وُجدت عبارات تدل عليه بشكل مباشر أو غير مباشر، ولا تشترط التطابق الحرفي.

{name_usage}

**مهم: لا تخرج عن هذه العناصر فقط، ولا تذكر أسماء غير واقعية:**

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
                           teacher_name=teacher_name, job_title=job_title,
                           school=school, principal_name=principal_name)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
