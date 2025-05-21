
from flask import Flask, render_template, request
from PIL import Image
import pytesseract
import os
from rubric_keywords import rubric_keywords

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def analyze_with_keywords(text):
    result = []
    total_score = 0
    for item in rubric_keywords:
        matched = sum(1 for kw in item["keywords"] if kw in text)
        score = min(matched, 2)
        percent = round((score / 2) * 5, 1)
        note = "العنصر غير ظاهر" if score == 0 else "محقق بدرجة عالية" if score == 2 else "محقق جزئياً"
        result.append({
            "item": item["item"],
            "score": score,
            "weight": item["weight"],
            "percent": percent,
            "note": note
        })
        total_score += percent
    final_score = round(total_score / len(rubric_keywords), 2)
    return result, final_score

@app.route('/', methods=['GET', 'POST'])
def index():
    result = []
    grade = None
    text = ""
    if request.method == 'POST':
        file = request.files.get('image')
        if file and file.filename:
            path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(path)
            text = pytesseract.image_to_string(Image.open(path), lang='ara')
        else:
            text = request.form.get('shahid', '')

        result, grade = analyze_with_keywords(text)

    return render_template("index.html", result=result, grade=grade)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
