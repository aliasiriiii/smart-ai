from flask import Flask, render_template, request
import os
import requests
import openai
from pdf2image import convert_from_bytes
from PIL import Image
import re
import io
from werkzeug.utils import secure_filename
from concurrent.futures import ThreadPoolExecutor

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

executor = ThreadPoolExecutor(max_workers=2)

client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
OCR_API_KEY = os.environ.get("OCR_API_KEY")


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
        print(f"OCR Error: {e}")
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
        print(f"PDF Processing Error: {e}")
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
    elements = [
        "أداء المهام الوظيفية", "التفاعل الإيجابي مع منسوبي المدرسة والمجتمع", "التفاعل مع أولياء الأمور",
        "تنويع استراتيجيات التدريس", "تحسين نواتج التعلم", "إعداد وتنفيذ خطة الدرس",
        "توظيف التقنيات والوسائل التعليمية", "تهيئة البيئة التعليمية", "ضبط سلوك الطلاب",
        "تحليل نتائج المتعلمين وتشخيص مستواهم", "تنويع أساليب التقويم"
    ]

    scores = re.findall(r'<td>(\d)\s*من 5</td>', gpt_response)
    scores = [int(score) for score in scores] + [1] * (11 - len(scores))
    scores = scores[:11]

    notes = []
    for i in range(1, 12):
        pattern = rf"العنصر {i}.*?\n(.*?)\n"
        match = re.search(pattern, gpt_response, re.DOTALL)
        notes.append(match.group(1).strip() if match else "لا توجد ملاحظة متاحة.")

    total_score = 0
    total_weight = 0
    rows = ""

    def get_status(score): return "متحقق" if score == 5 else "متحقق جزئيًا" if score == 4 else "لم يتحقق"
    def get_color(score): return "#d4edda" if score == 5 else "#fff3cd" if score == 4 else "#f8d7da"

    for i in range(11):
        score = scores[i]
        percent = (score / 5) * 100
        weight = weights[i]
        total_weight += weight
        total_score += (percent * weight) / 100
        status = get_status(score)
        color = get_color(score)
        rows += f"<tr style='background:{color};'><td>{elements[i]}</td><td>{score} من 5</td><td>{status}</td><td>{notes[i]}</td></tr>"

    final_score_5 = round((total_score / total_weight) * 5, 2)
    percent_score = int(total_score)

    table = f"""
    <h4 style='margin-top:30px; color:#2c3e50;'>الجدول التشخيصي للدرجات:</h4>
    <table style='width:100%; border-collapse: collapse; margin-top: 10px;'>
        <tr style='background-color:#007bff; color:white; text-align:right;'>
            <th>العنصر</th><th>الدرجة</th><th>الحالة</th><th>ملاحظة</th>
        </tr>
        {rows}
    </table>
    """

    result_block = f"""
    <div style='margin-top:20px; font-size:18px; color:#154360; background:#d6eaf8; padding:15px; border-radius:10px; text-align:center;'>
        <strong>الدرجة النهائية:</strong> {final_score_5} من 5 ({percent_score}%)
    </div>
    {generate_progress_bar(percent_score)}
    <div style='margin-top:10px; font-size:15px; color:#7f8c8d;'>تم الحساب بناءً على {len(scores)} عنصرًا من أصل 11.</div>
    """

    return table + result_block


def process_uploaded_files(form_data, uploaded_files):
    teacher_name = form_data['teacher_name']
    job_title = form_data['job_title']
    school = form_data['school']
    principal_name = form_data['principal_name']
    file_link = form_data['file_link']
    input_text = form_data['shahid_text']
    pdf_page_count = 0
    gpt_result = ""

    try:
        file = uploaded_files['image']
        pdf_file = uploaded_files['pdf_file']

        if file and file.filename and file.filename.lower().endswith(('.png', '.jpg', '.jpeg')):
            filename = secure_filename(file.filename)
            path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(path)
            input_text = extract_text_from_image_ocr_space(open(path, 'rb'))
            os.remove(path)

        elif pdf_file and pdf_file.filename and pdf_file.filename.lower().endswith('.pdf'):
            filename = secure_filename(pdf_file.filename)
            pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            pdf_file.save(pdf_path)
            input_text, pdf_page_count = extract_text_from_pdf(pdf_path)
            os.remove(pdf_path)

        if input_text.strip():
            prompt = f"""
أنت محلل تربوي متخصص في تقييم أداء المعلمين بناءً على الشواهد المكتوبة أو المصورة.
مهمتك تحليل الشاهد أدناه باستخدام العناصر المعتمدة من وزارة التعليم وعددها 11 عنصرًا.

ابدأ دائمًا بجدول HTML يحتوي: <table><tr><td> فقط.
ثم أضف تحليلًا ذكيًا لكل عنصر على حدة بهذا الشكل:
- "العنصر 1: ..."
- ملاحظة ذكية

النص:
{input_text}
"""

            response = client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3
            )
            gpt_text = response.choices[0].message.content
            result_table = calculate_final_score_from_table(gpt_text)

            full_result = f"""
                <h3>تحليل الشاهد المقدم من: {teacher_name}</h3>
                {result_table}
                <hr>
                <h4>تفاصيل التحليل الذكي:</h4>
                <div style='background:#fefefe; border:1px solid #ccc; padding:15px; border-radius:10px; margin-top:10px; font-family:"Tahoma",sans-serif; white-space:pre-line;'>
                    {gpt_text}
                </div>
            """
            gpt_result = full_result

    except Exception as e:
        gpt_result = f"<div style='color:red;'>حدث خطأ أثناء التحليل: {str(e)}</div>"
        print(f"Error in processing: {str(e)}")

    return gpt_result, teacher_name, job_title, school, principal_name


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
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

        future = executor.submit(process_uploaded_files, form_data, uploaded_files)
        gpt_result, teacher_name, job_title, school, principal_name = future.result()

        return render_template("index.html",
                               gpt_result=gpt_result,
                               teacher_name=teacher_name,
                               job_title=job_title,
                               school=school,
                               principal_name=principal_name)

    return render_template("index.html")


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, threaded=True)
