# -*- coding: utf-8 -*-
from flask import Flask, render_template, request
import openai
import os

app = Flask(__name__)

# إعداد عميل OpenAI الرسمي
client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze_text', methods=['POST'])
def analyze_text():
    input_text = request.form['input_text']

    try:
        # إرسال النص إلى GPT
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system",
                    "content": "أنت محلل تربوي، حلل النص التالي وفق 11 عنصرًا تربويًا مع تقييم من 5 وملاحظات وتوصيات."
                },
                {"role": "user", "content": input_text}
            ]
        )

        result = response.choices[0].message.content

        # إزالة الرموز المخفية + معالجة الترميز العربي
        cleaned_result = result.replace('\u200f', '').encode('utf-8').decode('utf-8')

        return render_template('index.html', result=cleaned_result)

    except Exception as e:
        return render_template('index.html', result=f"حدث خطأ: {str(e)}")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
