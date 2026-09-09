from flask import Flask, render_template_string, request, redirect, url_for, session

app = Flask(__name__)
app.secret_key = 'hope_school_secret_key_123'

# قاعدة بيانات وهمية مؤقتة للمعلمين وجداولهم (سنقوم بربطها بقاعدة بيانات حقيقية لاحقاً)
TEACHERS = {
    'ali': {
        'password': '123',
        'name': 'الأستاذ علي',
        'schedule': {
            'السبت': ['حصص صيانة', 'فراغ', 'رياضيات صف ثالث (حصة 3)', 'رياضيات صف رابع'],
            'الأحد': ['رياضيات صف خامس', 'فراغ', 'فراغ', 'رياضيات صف سادس'],
            'الإثنين': ['رياضيات صف ثالث (حصة 2)', 'رياضيات صف ثالث (حصة 3)', 'فراغ', 'نشاط'],
            'الثلاثاء': ['فراغ', 'رياضيات صف رابع', 'فراغ', 'فراغ'],
            'الأربعاء': ['رياضيات صف خامس', 'رياضيات صف سادس', 'فراغ', 'فراغ'],
            'الخميس': ['رياضيات صف ثالث', 'فراغ', 'نشاط أسبوعي', 'انصراف']
        }
    },
    'ahmad': {
        'password': '456',
        'name': 'الأستاذ أحمد',
        'schedule': {
            'السبت': ['لغة عربية صف أول', 'لغة عربية صف ثاني', 'فراغ', 'فراغ'],
            'الأحد': ['فراغ', 'لغة عربية صف أول', 'فراغ', 'مكتبة'],
            'الإثنين': ['فراغ', 'فراغ', 'لغة عربية صف ثاني', 'فراغ'],
            'الثلاثاء': ['لغة عربية صف أول', 'فراغ', 'لغة عربية صف ثاني', 'فراغ'],
            'الأربعاء': ['فراغ', 'فراغ', 'فراغ', 'أنشطة'],
            'الخميس': ['لغة عربية صف أول', 'لغة عربية صف ثاني', 'فراغ', 'انصراف']
        }
    }
}

LOGIN_PAGE = '''
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>تسجيل دخول - مدرسة الأمل</title>
    <style>
        body { font-family: Tahoma, sans-serif; background: #f0f4f8; text-align: center; padding: 50px 20px; }
        .login-box { background: white; max-width: 400px; margin: 0 auto; padding: 30px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); }
        h2 { color: #0284c7; margin-bottom: 20px; }
        input { width: 100%; padding: 12px; margin: 10px 0; border: 1px solid #cbd5e1; border-radius: 6px; box-sizing: border-box; font-size: 16px; }
        button { background: #0284c7; color: white; border: none; padding: 12px; width: 100%; border-radius: 6px; font-size: 16px; cursor: pointer; font-weight: bold; }
        button:hover { background: #0369a1; }
        .error { color: #dc2626; margin-top: 10px; font-size: 14px; }
    </style>
</head>
<body>
    <div class="login-box">
        <h2>مدرسة الأمل</h2>
        <p style="color: #64748b; margin-bottom: 20px;">تسجيل دخول المعلمين</p>
        <form method="POST">
            <input type="text" name="username" placeholder="اسم المستخدم (مثال: ali أو ahmad)" required>
            <input type="password" name="password" placeholder="كلمة المرور" required>
            <button type="submit">دخول للجدول</button>
        </form>
        {% if error %}
            <p class="error">{{ error }}</p>
        {% endif %}
    </div>
</body>
</html>
'''

DASHBOARD_PAGE = '''
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>جدول الحصص - {{ teacher.name }}</title>
    <style>
        body { font-family: Tahoma, sans-serif; background: #f8fafc; margin: 0; padding: 20px; }
        .container { max-width: 600px; margin: 0 auto; background: white; padding: 20px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); }
        .header { display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #e2e8f0; padding-bottom: 15px; margin-bottom: 20px; }
        h2 { color: #0f172a; margin: 0; }
        .logout { background: #ef4444; color: white; padding: 8px 15px; border-radius: 6px; text-decoration: none; font-size: 14px; }
        .day-card { background: #f1f5f9; border-radius: 8px; padding: 12px 15px; margin-bottom: 12px; border-right: 4px solid #0284c7; }
        .day-title { font-weight: bold; color: #0369a1; margin-bottom: 5px; font-size: 16px; }
        ul { margin: 0; padding-right: 20px; color: #334155; }
        li { margin-bottom: 4px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div>
                <h2>مرحباً، {{ teacher.name }}</h2>
                <p style="color: #64748b; margin: 5px 0 0 0; font-size: 14px;">جدول الحصص الأسبوعي</p>
            </div>
            <a href="/logout" class="logout">تسجيل خروج</a>
        </div>

        {% for day, classes in teacher.schedule.items() %}
        <div class="day-card">
            <div class="day-title">{{ day }}</div>
            <ul>
                {% for c in classes %}
                    <li>{{ c }}</li>
                {% endfor %}
            </ul>
        </div>
        {% endfor %}
    </div>
</body>
</html>
'''

@app.route('/', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username in TEACHERS and TEACHERS[username]['password'] == password:
            session['user'] = username
            return redirect(url_for('dashboard'))
        else:
            error = 'اسم المستخدم أو كلمة المرور غير صحيحة!'
    return render_template_string(LOGIN_PAGE, error=error)

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))
    username = session['user']
    teacher = TEACHERS[username]
    return render_template_string(DASHBOARD_PAGE, teacher=teacher)

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
