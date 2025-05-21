from flask import Flask, render_template, request
from PIL import Image
import pytesseract
import os
import openai

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# مفتاح OpenAI مدموج مباشرة
openai.api_key = "sk-proj-wxZoZ5Y1I8QA0sUy9kj_ie2fxg4YzFxfImRPV"

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
    result = ""
    teacher_name = ""
    school_name = ""
    job_title = ""

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

        result = analyze_with_gpt(text)

    return render_template('index.html', result=result,
                           teacher_name=teacher_name,
                           school_name=school_name,
                           job_title=job_title)

if __name__ == '__main__':
port = int(os.environ.get('PORT', 5000))
app.run(host='0.0.0.0', port=port)
