from flask import Flask, render_template, request
import os
import requests
import openai
import fitz  # PyMuPDF
from PIL import Image

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

def extract_text_from_image_ocr_space(image_path):
    api_key = "helloworld"
    with open(image_path, 'rb') as f:
        response = requests.post(
            'https://api.ocr.space/parse/image',
            files={'filename': f},
            data={'apikey': api_key, 'language': 'ara'}
        )
    try:
        result = response.json()
        if not result['IsErroredOnProcessing'] and 'ParsedResults' in result:
            return result['ParsedResults'][0].get('ParsedText', '')
        else:
            return ''
    except Exception as e:
        print("OCR Error:", e)
        return ''

def extract_text_from_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    full_text = ""
    for i, page in enumerate(doc):
        pix = page.get_pixmap(dpi=200)
        image_path = os.path.join(UPLOAD_FOLDER, f"page_{i}.png")
        pix.save(image_path)
        extracted = extract_text_from_image_ocr_space(image_path)
        full_text += "\n" + extracted
    return full_text

@app.route('/', methods=['GET', 'POST'])
def index():
    gpt_result = ""
    input_text = ""
    teacher_name = request.form.get('teacher_name', '').strip()
    job_title = request.form.get('job_title', '')
    school = request.form.get('school', '')
    principal_name = request.form.get('principal_name', '').strip()

    if request.method == 'POST':
        file = request.files.get('image') or request.files.get('pdf_file')
        if file and file.filename:
            ext = os.path.splitext(file.filename)[1].lower()
            path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(path)

            if ext == '.pdf':
                input_text = extract_text_from_pdf(path)
            else:
                input_text = extract_text_from_image_ocr_space(path)
        else:
            input_text = request.form.get('shahid', '')

        name_usage = f"استخدم اسم المعلم في الملاحظات: {teacher_name}." if teacher_name else "لا تستخدم أي أسماء أشخاص. استخدم فقط تعبير 'المعلم'."

        prompt = f"""
أنت محلل تربوي متخصص في تقييم أداء المعلمين بناءً على شواهد مكتوبة أو مصورة. مهمتك تحليل الشاهد أدناه وفق العناصر الرسمية المعتمدة فقط.

لكل عنصر:
- إذا لم يُذكر شيء يدل عليه → الدرجة = 1 من 5.
- إذا وُجد شاهد واحد → الدرجة = 4 من 5.
- إذا وُجد شاهدين أو أكثر → الدرجة = 5 من 5.

احسب النسبة المحققة بناء على الوزن التالي:
- تهيئة البيئة التعليمية = 5%
- ضبط سلوك الطلاب = 5%
- باقي العناصر = 10%

ابدأ فورًا بعرض **جدول HTML منسق وواضح** يحتوي الأعمدة التالية:
- اسم العنصر
- تحقق العنصر (نعم / لا)
- الدرجة من 5
- النسبة المحققة / الأصلية (مثال: 8% / 10%)

ثم بعد الجدول مباشرة:
- اذكر المجموع الكلي للنسب المحققة من 100%
- الدرجة النهائية من 5
- ملاحظات تحليلية ذكية توضح سبب تحقق أو عدم تحقق كل عنصر.

مهم:
- لا تعتبر وجود أسئلة أو محتوى أكاديمي بحد ذاته دليلاً كافيًا على تحقق العناصر، إلا إذا تم ربطه بسياق تربوي مثل: تحليل نتائج، خطة علاجية، استراتيجية، تفاعل.
- إذا احتوى الشاهد على صور متعددة، مثل استراتيجية، اختبار، وتقنية، فافترض تحقق كل عنصر يرتبط بشكل مباشر بما ورد فقط، ولا تعمم على بقية العناصر غير الظاهرة.
- إذا احتوى النص فقط على اختبار أو أسئلة بدون أي تعليق تربوي أو هدف أو تحليل، فلا تعتبرها دليلاً على تحقق عناصر الأداء.

تأكد من أنك تفسر العبارات التربوية المتنوعة بشكل ذكي، واعتبر العنصر محققًا إذا وُجدت عبارات أو صور تدل عليه بشكل مباشر أو غير مباشر، ولا تشترط التطابق الحرفي.

أمثلة توجيهية:
- "تعليق لوحات تعليمية" = تهيئة البيئة التعليمية
- "وزع شهادات شكر" = ضبط سلوك الطلاب
- "ملف إنجاز" = تنويع أساليب التقويم
- "رسائل نصية وتقارير متابعة" = تفاعل مع أولياء الأمور
- "حللت نتائج الطلاب" = تحليل نتائج وتشخيص

{name_usage}

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
