from flask import Flask, render_template, request
from PIL import Image
import pytesseract
import os
from openai import OpenAI

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

openai.api_key = "sk-proj-wxZoZ5Y1I8QA0sUy9kj_ie2fxg4YzFxfImRPV"

rubric_keywords = {
    "التخطيط": ["خطة", "تخطيط", "أهداف"],
    "استراتيجيات التدريس": ["استراتيجية", "تعلم تعاوني", "عصف ذهني"],
    "المحتوى العلمي": ["معلومة", "شرح", "نظرية", "تجربة"],
    "الوسائل التعليمية": ["وسيلة", "لوحة", "مجسم", "عرض"],
    "التقنية": ["بوربوينت", "منصة", "كلاسيرا", "تيمز", "عالمية"],
    "الأنشطة الصفية": ["نشاط", "تمرين", "مجموعة", "بطاقة"],
    "إدارة الصف": ["ضبط", "تنظيم", "هدوء", "مشاركة"],
    "القياس والتقويم": ["اختبار", "واجب", "تقييم", "عرض", "تحصيل"],
    "الرعاية الطلابية": ["مراعاة", "فروق", "احتياجات", "تحفيز"],
    "التنمية المهنية": ["دورة", "تدريب", "تطوير", "ملتقى"],
    "التفاعل المجتمعي": ["ولي", "مبادرة", "شراكة", "مجتمع", "تواصل"]
}

def analyze_with_keywords(text):
    results = []
    total_score = 0
    for item, keywords in rubric_keywords.items():
        matches = sum(1 for word in keywords if word in text)
        score = min(matches, 2)
        weight = 100 / len(rubric_keywords)
        percent = round((score / 5) * 100, 1)
        note = "العنصر ظاهر" if score > 0 else "العنصر غير ظاهر"
        results.append({
            "item": item,
            "score": score,
            "weight": f"{weight:.1f}%",
            "percent": f"{percent}%",
            "note": note
        })
        total_score += score
    final_grade = round(total_score / len(rubric_keywords), 2)
    return results, final_grade

def analyze_with_gpt(text):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "أنت أداة تقييم ذكية لتحليل الشواهد التعليمية. حلل الشاهد التالي بناءً على عناصر الأداء التربوي، وقدم تقييمًا ذكيًا مفصلًا يشمل ملاحظات وتوصيات."},
                {"role": "user", "content": text}
            ]
        )
        return response.choices[0].message["content"]
    except Exception as e:
        return f"حدث خطأ أثناء التحليل: {str(e)}"

@app.route('/', methods=['GET', 'POST'])
def index():
    result = False
    teacher_name = ""
    school_name = ""
    job_title = ""
    keyword_result = []
    final_score = 0
    gpt_result = ""

    if request.method == 'POST':
        teacher_name = request.form['teacher_name']
        school_name = request.form['school_name']
        job_title = request.form['job_title']
        text = request.form.get('shahid', '')

        if 'image' in request.files:
            image_file = request.files['image']
            if image_file and image_file.filename != '':
                image_path = os.path.join(app.config['UPLOAD_FOLDER'], image_file.filename)
                image_file.save(image_path)
                img = Image.open(image_path)
                extracted_text = pytesseract.image_to_string(img, lang='ara')
                text += "\n" + extracted_text

        keyword_result, final_score = analyze_with_keywords(text)
        gpt_result = analyze_with_gpt(text)
        result = True

    return render_template(
        'index.html',
        result=result,
        teacher_name=teacher_name,
        school_name=school_name,
        job_title=job_title,
        keyword_result=keyword_result,
        grade=final_score,
        gpt_result=gpt_result
    )

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
