from flask import Flask, render_template, request
import os
import openai

app = Flask(__name__)

# إعداد مجلد الرفع
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# إعداد GPT
client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze_text', methods=['POST'])
def analyze_text():
    input_text = request.form['input_text']

    # تحليل GPT للنص
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "أنت محلل تربوي، حلل النص التالي وفق 11 عنصرًا تربويًا، أعط درجة من 5 مع ملاحظات وتوصيات."},
            {"role": "user", "content": input_text}
        ]
    )
    ai_analysis = response.choices[0].message.content

    # تحليل يدوي تجريبي (قابل للتعديل لاحقًا حسب الكلمات المفتاحية)
    rubric = [
        'الأهداف', 'الأنشطة', 'الوسائل', 'التقويم', 'إدارة الصف',
        'التحفيز', 'تنوع الأساليب', 'المهارات', 'السلوك',
        'المشاركة', 'التقنية'
    ]

    total_score = 0
    table = []

    for item in rubric:
        score = 5  # درجة مؤقتة لكل عنصر (يمكن تعديلها لاحقًا)
        comment = "جيد جدًا"  # ملاحظة مؤقتة
        total_score += score
        table.append({
            'element': item,
            'score': score,
            'percentage': score * 20,
            'comment': comment
        })

    # حساب الدرجة النهائية والنسبة
    final_score = round(total_score / len(rubric), 2)
    final_percentage = int((final_score / 5) * 100)

    return render_template(
        'index.html',
        table=table,
        ai_analysis=ai_analysis,
        final_score=final_score,
        final_percentage=final_percentage
    )

if __name__ == '__main__':
    app.run(debug=True)
