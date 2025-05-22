# -*- coding: utf-8 -*-

from flask import Flask, render_template, request
import openai
import os

app = Flask(__name__)

# إنشاء العميل الخاص بـ OpenAI
client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze_text', methods=['POST'])
def analyze_text():
    input_text = request.form['input_text']

    try:
        # تحليل النص عبر GPT-4
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system",
                    "content": "أنت خبير تربوي، حلل هذا الشاهد وفق 11 عنصرًا تربويًا، أعطِ درجة من 5 لكل عنصر مع ملاحظات وتوصيات مهنية."
                },
                {"role": "user", "content": input_text}
            ]
        )
        result = response.choices[0].message.content

        # ضمان الترميز الصحيح للعرض بالعربية
        return render_template('index.html', result=result.encode('utf-8').decode('utf-8'))

    except Exception as e:
        return render_template('index.html', result=f"حدث خطأ: {str(e)}")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
