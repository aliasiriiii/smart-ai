from flask import Flask, render_template, request
import os
import requests
from PIL import Image
import pytesseract

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# العناصر والكلمات المفتاحية والوزن
rubric_keywords = [
    {"item": "أداء الواجبات الوظيفية", "weight": 10, "keywords": ["تحضير", "جدول", "خطة توزيع"]},
    {"item": "التفاعل مع المجتمع المحلي", "weight": 10, "keywords": ["مجتمع", "مبادرة", "شراكة"]},
    {"item": "التفاعل مع أولياء الأمور", "weight": 10, "keywords": ["أولياء", "رسائل", "تواصل"]},
    {"item": "تنويع استراتيجيات التدريس", "weight": 10, "keywords": ["عصف", "تعلم نشط", "لعب أدوار"]},
    {"item": "تحسين نواتج المتعلمين", "weight": 10, "keywords": ["نواتج", "أداء", "تحسن"]},
    {"item": "إعداد وتنفيذ خطة الدرس", "weight": 10, "keywords": ["خطة", "أهداف", "عرض"]},
    {"item": "توظيف تقنيات ووسائل التعليم", "weight": 10, "keywords": ["سبورة", "تقنية", "عرض مرئي"]},
    {"item": "تهيئة البيئة التعليمية", "weight": 5, "keywords": ["تهيئة", "مقاعد", "نظام"]},
    {"item": "ضبط سلوك الطلاب", "weight": 5, "keywords": ["سلوك", "انضباط", "هدوء"]},
    {"item": "تحليل نتائج المتعلمين", "weight": 10, "keywords": ["نتائج", "تشخيص", "الفاقد"]},
    {"item": "تنوع أساليب التقويم", "weight": 10, "keywords": ["تقويم", "اختبار", "ملف إنجاز"]}
]

def analyze_text(text):
    result = []
    total_score = 0
    for item in rubric_keywords:
        matches = [kw for kw in item["keywords"] if kw in text]
        score = 5 if len(matches) >= 2 else 3 if len(matches) == 1 else 1
        percent = round((score / 5) * 100)
        result.append({
            "item": item["item"],
            "score": score,
            "weight": item["weight"],
            "percent": percent,
            "note": f"الكلمات المطابقة: {', '.join(matches) if matches else 'لا يوجد'}"
        })
        total_score += (score * item["weight"]) / 5
    final_score = round(total_score / 10, 2)
    return result, final_score

@app.route('/', methods=['GET', 'POST'])
def index():
    result = []
    grade = None
    teacher_name = ""
    specialty = ""
    if request.method == 'POST':
        text = ""
        teacher_name = request.form.get("teacher_name", "")
        specialty = request.form.get("specialty", "")
        file = request.files.get('image')
        if file and file.filename:
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(image_path)
            text = pytesseract.image_to_string(Image.open(image_path), lang='ara')
        else:
            text = request.form.get('shahid', '')
        result, grade = analyze_text(text)
    return render_template("index.html", result=result, grade=grade,
                           teacher_name=teacher_name, specialty=specialty)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
