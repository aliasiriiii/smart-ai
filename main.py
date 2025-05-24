from flask import Flask, render_template, request
import os
import requests
import openai
from pdf2image import convert_from_path
from PIL import Image
import re
from werkzeug.utils import secure_filename

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
OCR_API_KEY = os.environ.get("OCR_API_KEY")

def extract_text_from_image_ocr_space(image_path):
    try:
        with open(image_path, 'rb') as f:
            response = requests.post(
                'https://api.ocr.space/parse/image',
                files={'filename': f},
                data={'apikey': OCR_API_KEY, 'language': 'ara'}
            )
        result = response.json()
        return result['ParsedResults'][0]['ParsedText'] if not result['IsErroredOnProcessing'] else ""
    except:
        return ""

def extract_text_from_pdf(pdf_path):
    images = convert_from_path(pdf_path)
    full_text = ""
    for i, img in enumerate(images):
        img_path = os.path.join(app.config['UPLOAD_FOLDER'], f"page_{i}.jpg")
        img.save(img_path, 'JPEG')
        text = extract_text_from_image_ocr_space(img_path)
        full_text += text + "\n"
    return full_text, len(images)

def generate_progress_bar(percent):
    return f"""
    <div style='background:#eee; border-radius:10px; overflow:hidden; margin-top:10px;'>
      <div style='width:{percent}%; background:#2ecc71; padding:10px; color:white; text-align:center;'>
        {percent}%
      </div>
    </div>
    """

def calculate_final_score_from_table(table_html):
    weights = [10, 10, 10, 10, 10, 10, 10, 5, 5, 10, 10]
    scores = re.findall(r'>(\d)\s*(?:من 5)?</td>', table_html)
    total_score = 0
    total_weight = 0

    if 7 <= len(scores) <= 11:
        for i, score_str in enumerate(scores):
            if i >= len(weights):
                break
            score = int(score_str)
            percent = (score / 5) * 100
            weight = weights[i]
            total_weight += weight
            total_score += (percent * weight) / 100

        final_score_5 = round((total_score / total_weight) * 5, 2)
        percent_score = int(total_score)

        elements = [
            "أداء المهام الوظيفية", "التفاعل الإيجابي مع منسوبي المدرسة والمجتمع", "التفاعل مع أولياء الأمور",
            "تنويع استراتيجيات التدريس", "تحسين نواتج التعلم", "إعداد وتنفيذ خطة الدرس", 
            "توظيف التقنيات والوسائل التعليمية", "تهيئة البيئة التعليمية", "ضبط سلوك الطلاب",
            "تحليل نتائج المتعلمين وتشخيص مستواهم", "تنويع أساليب التقويم"
        ]

        def get_status(score):
            return "متحقق" if score == 5 else "متحقق جزئيًا" if score == 4 else "لم يتحقق"

        def get_color(score):
            return "#d4edda" if score == 5 else "#fff3cd" if score == 4 else "#f8d7da"

        rows = ""
        for i in range(len(elements)):
            score = int(scores[i]) if i < len(scores) else 1
            status = get_status(score)
            color = get_color(score)
            rows += f"<tr style='background:{color};'><td>{elements[i]}</td><td>{score} من 5</td><td>{status}</td><td>---</td></tr>"

        table = f"""
        <h4 style='margin-top:30px; color:#2c3e50;'>الجدول التشخيصي للدرجات:</h4>
        <table style='width:100%; border-collapse: collapse; margin-top: 10px;'>
            <tr style='background-color:#007bff; color:white; text-align:right;'>
                <th>العنصر</th><th>الدرجة</th><th>الحالة</th><th>ملاحظة</th>
            </tr>
            {rows}
        </table>
        """

        box = f"<div style='margin-top:20px; font-size:18px; color:#154360; background:#d6eaf8; padding:15px; border-radius:10px; text-align:center;'><strong>النسبة المحققة:</strong> {percent_score}%</div>"
        progress = generate_progress_bar(percent_score)
        message = f"<div style='margin-top:10px; font-size:15px; color:#7f8c8d;'>تم الحساب بناءً على {len(scores)} عنصرًا من أصل 11.</div>"

        return box + table + progress + message
    else:
        return "<div style='color:red;'>تعذر حساب الدرجة النهائية: عدد العناصر أقل من المطلوب (الحد الأدنى 7).</div>"

@app.route('/', methods=['GET', 'POST'])
def index():
    gpt_result = ""
    teacher_name = request.form.get('teacher_name', '')
    job_title = request.form.get('job_title', '')
    school = request.form.get('school', '')
    principal_name = request.form.get('principal_name', '')
    file_link = request.form.get('file_link', '')
    input_text = ""
    pdf_page_count = 0

    if request.method == 'POST':
        file = request.files.get('image')
        pdf_file = request.files.get('pdf_file')
        if file and file.filename and file.filename.lower().endswith(('.png', '.jpg', '.jpeg')):
            filename = secure_filename(file.filename)
            path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(path)
            input_text = extract_text_from_image_ocr_space(path)
        elif pdf_file and pdf_file.filename and pdf_file.filename.lower().endswith('.pdf'):
            filename = secure_filename(pdf_file.filename)
            pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            pdf_file.save(pdf_path)
            input_text, pdf_page_count = extract_text_from_pdf(pdf_path)
        else:
            input_text = request.form.get('shahid', '')

        prompt = f"""
أنت محلل تربوي متخصص في تقييم أداء المعلمين بناءً على الشواهد المكتوبة أو المصورة.
مهمتك تحليل الشاهد أدناه باستخدام العناصر المعتمدة من وزارة التعليم وعددها 11 عنصرًا.
ابدأ دائمًا بإخراج جدول HTML يحتوي: العنصر، الدرجة، الحالة، الملاحظة.
يجب أن يحتوي الجدول على جميع العناصر الإحدى عشر حتى وإن لم يكن هناك شواهد كافية.

النص:
{input_text}
"""

        try:
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3
            )
            content = response.choices[0].message.content
            final_block = calculate_final_score_from_table(content)
            gpt_result = f"<h3>تحليل الشاهد المقدم من: {teacher_name}</h3><br>{final_block}"
        except Exception as e:
            gpt_result = f"<div style='color:red;'>حدث خطأ أثناء التحليل: {str(e)}</div>"

    return render_template("index.html",
                           gpt_result=gpt_result,
                           teacher_name=teacher_name,
                           job_title=job_title,
                           school=school,
                           principal_name=principal_name)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
