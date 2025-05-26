<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>منصة التقييم الذكي لشواهد المعلمين</title>
  <style>
    body {
      font-family: 'Tahoma', sans-serif;
      background: #f4f8fc;
      padding: 20px;
      color: #333;
      line-height: 1.6;
    }
    h1 {
      text-align: center;
      color: #1a5276;
      margin-bottom: 30px;
      padding-bottom: 15px;
      border-bottom: 2px solid #eee;
    }
    .container {
      max-width: 900px;
      margin: 0 auto;
    }
    form {
      background: #ffffff;
      padding: 25px;
      border-radius: 12px;
      box-shadow: 0 2px 10px rgba(0,0,0,0.08);
      margin-bottom: 30px;
    }
    .form-group {
      margin-bottom: 20px;
    }
    label {
      display: block;
      margin-bottom: 8px;
      font-weight: bold;
      color: #2c3e50;
    }
    input, textarea, select {
      width: 100%;
      padding: 12px;
      border: 1px solid #ddd;
      border-radius: 6px;
      font-family: inherit;
      font-size: 16px;
      transition: border 0.3s;
    }
    input:focus, textarea:focus {
      border-color: #3498db;
      outline: none;
      box-shadow: 0 0 0 3px rgba(52,152,219,0.1);
    }
    button {
      background-color: #3498db;
      color: white;
      padding: 14px 24px;
      border: none;
      border-radius: 6px;
      cursor: pointer;
      font-size: 16px;
      font-weight: bold;
      transition: background 0.3s;
      width: 100%;
      margin-top: 10px;
    }
    button:hover {
      background-color: #2980b9;
    }
    .result {
      background: #ffffff;
      padding: 25px;
      border-radius: 12px;
      box-shadow: 0 2px 10px rgba(0,0,0,0.08);
      margin-bottom: 40px;
      animation: fadeIn 0.5s ease;
    }
    @keyframes fadeIn {
      from { opacity: 0; transform: translateY(10px); }
      to { opacity: 1; transform: translateY(0); }
    }
    .loader {
      border: 5px solid #f3f3f3;
      border-top: 5px solid #3498db;
      border-radius: 50%;
      width: 50px;
      height: 50px;
      animation: spin 1s linear infinite;
      margin: 30px auto;
      display: none;
    }
    @keyframes spin {
      0% { transform: rotate(0deg); }
      100% { transform: rotate(360deg); }
    }
    .file-inputs {
      display: flex;
      gap: 15px;
      margin-bottom: 20px;
    }
    .file-inputs input[type="file"] {
      flex: 1;
      padding: 10px;
    }
    .footer-note {
      margin-top: 40px;
      font-size: 13px;
      text-align: center;
      color: #7f8c8d;
      padding-top: 20px;
      border-top: 1px solid #eee;
    }
    @media (max-width: 768px) {
      body {
        padding: 15px;
      }
      form {
        padding: 20px;
      }
      .file-inputs {
        flex-direction: column;
      }
    }
  </style>
</head>
<body>
  <div class="container">
    <h1>منصة التقييم الذكي لشواهد المعلمين</h1>

    <form method="POST" enctype="multipart/form-data" id="analysisForm">
      <div class="form-group">
        <label for="teacher_name">اسم المعلم:</label>
        <input type="text" id="teacher_name" name="teacher_name" placeholder="مثال: أ. محمد القحطاني" value="{{ teacher_name or '' }}">
      </div>

      <div class="form-group">
        <label for="job_title">المسمى الوظيفي / التخصص:</label>
        <input type="text" id="job_title" name="job_title" placeholder="مثال: معلم فيزياء" value="{{ job_title or '' }}">
      </div>

      <div class="form-group">
        <label for="school">اسم المدرسة:</label>
        <input type="text" id="school" name="school" placeholder="مثال: ثانوية الظهران" value="{{ school or '' }}">
      </div>

      <div class="form-group">
        <label for="principal_name">اسم القائد:</label>
        <input type="text" id="principal_name" name="principal_name" placeholder="مثال: أ. خالد الدوسري" value="{{ principal_name or '' }}">
      </div>

      <div class="form-group">
        <label for="file_link">رابط الشاهد (اختياري):</label>
        <input type="text" id="file_link" name="file_link" placeholder="مثال: https://drive.google.com/..." value="{{ file_link or '' }}">
      </div>

      <div class="form-group">
        <label>رفع الشاهد:</label>
        <div class="file-inputs">
          <input type="file" name="image" accept="image/*" title="صورة الشاهد">
          <input type="file" name="pdf_file" accept=".pdf" title="ملف PDF">
        </div>
      </div>

      <div class="form-group">
        <label for="shahid">أو أدخل الشاهد نصيًا:</label>
        <textarea id="shahid" name="shahid" rows="5" placeholder="اكتب الشاهد هنا...">{{ input_text or '' }}</textarea>
      </div>

      <button type="submit" id="submitBtn">تحليل الشاهد</button>
    </form>

    <div id="loader" class="loader"></div>

    {% if gpt_result %}
      <div class="result">
        {{ gpt_result|safe }}
        <div class="footer-note">
          تم توليد هذا التقرير باستخدام منصة التقييم الذكي – إشراف الأستاذ علي عسيري - ثانوية الظهران<br>
          هذا التحليل يُستخدم لمرة واحدة سنويًا ويُبنى على شواهد موثقة
        </div>
      </div>
      
      <div class="form-group">
        <button onclick="window.print()" style="background:#27ae60;">طباعة التقرير</button>
        <button onclick="location.reload()" style="background:#7f8c8d; margin-top:10px;">تحليل جديد</button>
      </div>
    {% endif %}
  </div>

  <script>
    // إظهار مؤشر التحميل عند إرسال النموذج
    document.getElementById('analysisForm').addEventListener('submit', function() {
      document.getElementById('loader').style.display = 'block';
      document.getElementById('submitBtn').disabled = true;
      document.getElementById('submitBtn').textContent = 'جاري التحليل...';
    });

    // عرض تنبيه إذا لم يتم اختيار أي ملف أو إدخال نص
    document.getElementById('analysisForm').addEventListener('submit', function(e) {
      const imageInput = document.querySelector('input[name="image"]');
      const pdfInput = document.querySelector('input[name="pdf_file"]');
      const textInput = document.querySelector('textarea[name="shahid"]');
      
      if (!imageInput.files[0] && !pdfInput.files[0] && textInput.value.trim() === '') {
        e.preventDefault();
        alert('الرجاء إدخال الشاهد إما كصورة أو ملف PDF أو نص');
      }
    });
  </script>
</body>
</html>
