‏from flask import Flask, request, render_template
‏import openai
‏import os

‏app = Flask(__name__)
‏openai.api_key = os.getenv("OPENAI_API_KEY")

‏rubric = [
‏    {"name": "أداء الواجبات الوظيفية", "weight": 10},
‏    {"name": "التفاعل مع المجتمع المحلي", "weight": 10},
‏    {"name": "التفاعل مع أولياء الأمور", "weight": 10},
‏    {"name": "تنويع استراتيجيات التدريس", "weight": 10},
‏    {"name": "تحسين نواتج المتعلمين", "weight": 10},
‏    {"name": "إعداد وتنفيذ خطة الدرس", "weight": 10},
‏    {"name": "توظيف تقنيات ووسائل التعليم المناسبة", "weight": 10},
‏    {"name": "تهيئة البيئة التعليمية", "weight": 5},
‏    {"name": "ضبط سلوك الطلاب", "weight": 5},
‏    {"name": "تحليل نتائج المتعلمين وتشخيص مستوياتهم", "weight": 10},
‏    {"name": "تنويع أساليب التقويم", "weight": 10}
]

‏@app.route('/')
‏def index():
‏    return render_template('index.html')

‏@app.route('/analyze_text', methods=['POST'])
‏def analyze_text():
‏    input_text = request.form['input_text']
‏    teacher_name = request.form['teacher_name']
‏    school_name = request.form['school_name']
‏    subject = request.form['subject']

‏    prompt = (
        "أنت محلل تربوي. أمامك نص شاهد، تحقق مما إذا كانت العناصر التالية مذكورة فيه (نعم / لا):\n" +
‏        "\n".join([f"{i+1}. {item['name']} ({item['weight']}%)" for i, item in enumerate(rubric)]) +
‏        f"\n\nالنص:\n{input_text}"
    )

‏    response = openai.ChatCompletion.create(
‏        model="gpt-4",
‏        messages=[{"role": "system", "content": prompt}],
‏        temperature=0.2
    )

‏    content = response.choices[0].message['content']
‏    lines = content.splitlines()

‏    result_rows = ""
‏    achieved_count = 0

‏    for i, item in enumerate(rubric):
‏        found = "نعم" in lines[i]
‏        percent = item['weight'] if found else 0
‏        if found:
‏            achieved_count += 1
‏        result_rows += f"<tr><td>{item['name']}</td><td>{item['weight']}%</td><td>{'نعم' if found else 'لا'}</td><td>{percent}%</td></tr>"

‏    if achieved_count >= 2:
‏        final_score = 5
‏    elif achieved_count == 1:
‏        final_score = 4
‏    else:
‏        final_score = 1

‏    result_table = f"""
‏    <table>
‏      <tr><th>اسم العنصر</th><th>الوزن</th><th>تحقق العنصر</th><th>النسبة المحققة</th></tr>
‏      {result_rows}
‏    </table>
    """

‏    return render_template(
‏        'index.html',
‏        result_table=result_table,
‏        final_score=final_score,
‏        gpt_analysis=content,
‏        teacher_name=teacher_name,
‏        school_name=school_name,
‏        subject=subject
    )

‏if __name__ == '__main__':
‏    port = int(os.environ.get("PORT", 5000))
‏    app.run(host='0.0.0.0', port=port)
