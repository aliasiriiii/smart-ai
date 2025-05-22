from flask import Flask, render_template, request
import openai
import os

app = Flask(__name__)

# استخدام مفتاح OpenAI من البيئة
openai.api_key = os.environ.get("OPENAI_API_KEY")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze_text', methods=['POST'])
def analyze_text():
    input_text = request.form['input_text']

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "حلل هذا الشاهد التربوي وفق 11 عنصراً تربوياً وأعطِ درجة من 5 لكل عنصر مع ملاحظات وتوصيات."},
                {"role": "user", "content": input_text}
            ]
        )
        result = response['choices'][0]['message']['content']
        return render_template('index.html', result=result)
    except Exception as e:
        return render_template('index.html', result=f"حدث خطأ: {str(e)}")

if __name__ == '__main__':
    app.run(debug=True)
