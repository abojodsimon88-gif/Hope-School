from flask import Flask, render_template_string, request, redirect, url_for, session, flash, get_flashed_messages

app = Flask(__name__)
app.secret_key = 'simon_hope_school_2026_ultimate'

# المستخدمين والباسورد تبعهم '000' افتراضياً
users_db = {
    'admin': {'password': '000', 'role': 'admin', 'name': 'المدير العام'},
    'berta': {'password': '000', 'role': 'secretary', 'name': 'الست بيرتا (السكرتيرة)'},
    'ahmad': {'password': '000', 'role': 'teacher', 'name': 'الأستاذ أحمد'},
    'nizar': {'password': '000', 'role': 'teacher', 'name': 'الأستاذ نزار'},
    'mike': {'password': '000', 'role': 'teacher', 'name': 'الأستاذ مايك'},
    'sohaila': {'password': '000', 'role': 'teacher', 'name': 'المس سهيلة'}
}

# جدول الحصص الأسبوعي الشامل
teachers_schedule = {
    'الأستاذ أحمد': {
        'الثلاثاء': 'رياضيات', 'الأربعاء': 'فراغ', 'الخميس': 'رياضيات'
    },
    'الأستاذ نزار': {
        'الثلاثاء': 'فراغ', 'الأربعاء': 'لغة عربية', 'الخميس': 'فراغ'
    },
    'الأستاذ مايك': {
        'الثلاثاء': 'لغة إنجليزية', 'الأربعاء': 'أنشطة', 'الخميس': 'مراجعة'
    },
    'المس سهيلة': {
        'الثلاثاء': 'تربية إسلامية', 'الأربعاء': 'محفوظات', 'الخميس': 'تربية إسلامية'
    }
}

HOME_HTML = '''
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <title>مدرسة الأمل - تسجيل الدخول</title>
    <style>
        body { font-family: Tahoma, sans-serif; background-color: #f4f7f6; margin: 0; padding: 20px; direction: rtl; text-align: right; }
        .container { max-width: 500px; margin: 50px auto; background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); }
        h2 { color: #2c3e50; text-align: center; }
        .form-group { margin-bottom: 20px; }
        label { display: block; margin-bottom: 8px; font-weight: bold; color: #34495e; }
        input, select { width: 100%; padding: 12px; border: 1px solid #ccc; border-radius: 6px; box-sizing: border-box; }
        button { background: #3498db; color: white; border: none; padding: 12px; width: 100%; border-radius: 6px; font-size: 16px; cursor: pointer; font-weight: bold; }
        button:hover { background: #2980b9; }
        .alert { padding: 12px; margin-bottom: 20px; border-radius: 6px; background: #e74c3c; color: white; text-align: center; }
        .footer-note { text-align: center; margin-top: 15px; font-size: 13px; color: #7f8c8d; }
    </style>
</head>
<body>
    <div class="container">
        <h2>مدرسة الأمل - تسجيل الدخول</h2>
        {% with messages = get_flashed_messages() %}
            {% if messages %}
                {% for message in messages %}
                    <div class="alert">{{ message }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}
        <form method="POST">
            <div class="form-group">
                <label>اختر المستخدم:</label>
                <select name="username" required>
                    <option value="">-- اضغط للاختيار --</option>
                    <option value="admin">المدير العام (admin)</option>
                    <option value="berta">الست بيرتا (السكرتيرة)</option>
                    <option value="ahmad">الأستاذ أحمد</option>
                    <option value="nizar">الأستاذ نزار</option>
                    <option value="mike">الأستاذ مايك</option>
                    <option value="sohaila">المس سهيلة</option>
                </select>
            </div>
            <div class="form-group">
                <label>كلمة المرور (الافتراضية: 000):</label>
                <input type="password" name="password" required placeholder="أدخل كلمة المرور">
            </div>
            <button type="submit">تسجيل الدخول</button>
        </form>
        <div class="footer-note">كلمة المرور لجميع الحسابات هي: 000</div>
    </div>
</body>
</html>
'''

COMMON_STYLE = '''
<style>
    body { font-family: Tahoma, sans-serif; background: #f4f7f6; padding: 20px; direction: rtl; text-align: right; margin: 0; }
    .container { max-width: 900px; margin: auto; background: white; padding: 25px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.08); }
    .nav { display: flex; justify-content: space-between; align-items: center; background: #2c3e50; padding: 12px 20px; border-radius: 8px; color: white; margin-bottom: 25px; }
    .nav a { color: #ecf0f1; text-decoration: none; font-weight: bold; margin-left: 10px; }
    .nav a:hover { color: #3498db; }
    table { width: 100%; border-collapse: collapse; margin-top: 15px; margin-bottom: 25px; }
    th, td { border: 1px solid #dcdde1; padding: 12px; text-align: center; }
    th { background: #34495e; color: white; font-size: 15px; }
    td { background: #fff; color: #2f3640; }
    .alert { padding: 12px; background: #d4edda; color: #155724; border-radius: 6px; margin-bottom: 20px; font-weight: bold; text-align: center; }
    .card { background: #f8f9fa; border: 1px solid #e9ecef; padding: 15px; border-radius: 8px; margin-bottom: 15px; }
</style>
'''

SECRETARY_HTML = COMMON_STYLE + '''
<div class="container">
    <div class="nav">
        <span>لوحة السكرتيرة (الست بيرتا) - إدارة الجداول</span>
        <div>
            <a href="/change_password">تغيير كلمة السر</a> | 
            <a href="/logout">تسجيل خروج</a>
        </div>
    </div>
    
    {% with messages = get_flashed_messages() %}
        {% if messages %}
            {% for message in messages %}
                <div class="alert">{{ message }}</div>
            {% endfor %}
        {% endif %}
    {% endwith %}

    <div class="card">
        <h3>تعديل حصص المعلمين:</h3>
        <form method="POST">
            <label style="font-weight:bold; margin-bottom:5px; display:block;">اختر المعلم:</label>
            <select name="teacher_name" required style="width:100%; padding:10px; margin-bottom:10px; border-radius:5px; border:1px solid #ccc;">
                <option value="">-- اختر المعلم --</option>
                {% for t in teachers_schedule.keys() %}
                    <option value="{{ t }}">{{ t }}</option>
                {% endfor %}
            </select>
            
            <label style="font-weight:bold; margin-bottom:5px; display:block;">يوم الثلاثاء:</label>
            <input type="text" name="tue" placeholder="المادة / الحصة" style="width:100%; padding:10px; margin-bottom:10px; border-radius:5px; border:1px solid #ccc; box-sizing:border-box;">
            
            <label style="font-weight:bold; margin-bottom:5px; display:block;">يوم الأربعاء:</label>
            <input type="text" name="wed" placeholder="المادة / الحصة" style="width:100%; padding:10px; margin-bottom:10px; border-radius:5px; border:1px solid #ccc; box-sizing:border-box;">
            
            <label style="font-weight:bold; margin-bottom:5px; display:block;">يوم الخميس:</label>
            <input type="text" name="thu" placeholder="المادة / الحصة" style="width:100%; padding:10px; margin-bottom:15px; border-radius:5px; border:1px solid #ccc; box-sizing:border-box;">
            
            <button type="submit" style="background: #27ae60; color: white; padding: 12px; border: none; width: 100%; border-radius: 6px; font-weight: bold; cursor: pointer; font-size:16px;">حفظ التعديل فوراً</button>
        </form>
    </div>

    <h3>الجداول الحالية المعتمدة في المدرسة:</h3>
    <table>
        <tr>
            <th>المعلم</th>
            <th>الثلاثاء</th>
            <th>الأربعاء</th>
            <th>الخميس</th>
        </tr>
        {% for teacher, days in teachers_schedule.items() %}
        <tr>
            <td><b>{{ teacher }}</b></td>
            <td>{{ days['الثلاثاء'] }}</td>
            <td>{{ days['الأربعاء'] }}</td>
            <td>{{ days['الخميس'] }}</td>
        </tr>
        {% endfor %}
    </table>
</div>
'''

TEACHER_HTML = COMMON_STYLE + '''
<div class="container">
    <div class="nav">
        <span>لوحة المعلم: {{ teacher_name }}</span>
        <div>
            <a href="/change_password">تغيير كلمة السر</a> | 
            <a href="/logout">تسجيل خروج</a>
        </div>
    </div>
    
    <h3>جدول الحصص الأسبوعي الخاص بك:</h3>
    <table>
        <tr>
            <th>اليوم</th>
            <th>الحصة / المادة الدراسية</th>
        </tr>
        <tr>
            <td>الثلاثاء</td>
            <td><b>{{ schedule.get('الثلاثاء', 'لا يوجد حصة') }}</b></td>
        </tr>
        <tr>
            <td>الأربعاء</td>
            <td><b>{{ schedule.get('الأربعاء', 'لا يوجد حصة') }}</b></td>
        </tr>
        <tr>
            <td>الخميس</td>
            <td><b>{{ schedule.get('الخميس', 'لا يوجد حصة') }}</b></td>
        </tr>
    </table>
</div>
'''

ADMIN_HTML = COMMON_STYLE + '''
<div class="container">
    <div class="nav">
        <span>لوحة الإدارة العليا (المدير العام) - الرقابة الشاملة</span>
        <div>
            <a href="/change_password">تغيير كلمة السر</a> | 
            <a href="/logout">تسجيل خروج</a>
        </div>
    </div>
    
    <div style="background: #e8f4fd; border-right: 5px solid #3498db; padding: 15px; border-radius: 5px; margin-bottom: 20px;">
        <h3 style="margin-top:0; color:#2980b9;">أهلاً بك يا سيادة المدير 🌟</h3>
        <p style="margin-bottom:0;">من هنا يمكنك مراقبة جداول جميع المعلمين بالتفصيل لضمان سير العملية التعليمية بدقة، ولا يمكن لأي أستاذ الادعاء بأنه لا يعلم جدوله.</p>
    </div>
    
    <h3>جدول الحصص الشامل لجميع المعلمين (المعتمد من السكرتيرة):</h3>
    <table>
        <tr>
            <th>اسم المعلم</th>
            <th>الثلاثاء</th>
            <th>الأربعاء</th>
            <th>الخميس</th>
        </tr>
        {% for teacher, days in teachers_schedule.items() %}
        <tr>
            <td><b>{{ teacher }}</b></td>
            <td style="color: #27ae60;">{{ days['الثلاثاء'] }}</td>
            <td style="color: #2980b9;">{{ days['الأربعاء'] }}</td>
            <td style="color: #d35400;">{{ days['الخميس'] }}</td>
        </tr>
        {% endfor %}
    </table>
</div>
'''

CHANGE_PASS_HTML = COMMON_STYLE + '''
<div class="container">
    <div class="nav">
        <span>تغيير كلمة المرور الشخصية</span>
        <a href="javascript:history.back()">رجوع</a>
    </div>
    <form method="POST">
        <label style="font-weight:bold; margin-bottom:8px; display:block;">كلمة المرور الجديدة:</label>
        <input type="password" name="new_password" required placeholder="أدخل كلمة المرور الجديدة" style="width:100%; padding:12px; margin-bottom:15px; border-radius:6px; border:1px solid #ccc; box-sizing:border-box;">
        <button type="submit" style="background: #e67e22; color: white; padding: 12px; border: none; width: 100%; border-radius: 6px; font-weight: bold; cursor: pointer; font-size:16px;">حفظ كلمة المرور الجديدة</button>
    </form>
</div>
'''

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username in users_db and users_db[username]['password'] == password:
            session['user'] = username
            role = users_db[username]['role']
            if role == 'admin':
                return redirect(url_for('admin_dashboard'))
            elif role == 'secretary':
                return redirect(url_for('secretary_dashboard'))
            elif role == 'teacher':
                return redirect(url_for('teacher_dashboard'))
        flash('اسم المستخدم أو كلمة المرور غير صحيحة!')
    return render_template_string(HOME_HTML)

@app.route('/secretary', methods=['GET', 'POST'])
def secretary_dashboard():
    if session.get('user') not in users_db or users_db[session.get('user')]['role'] != 'secretary':
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        t_name = request.form.get('teacher_name')
        tue = request.form.get('tue')
        wed = request.form.get('wed')
        thu = request.form.get('thu')
        if t_name in teachers_schedule:
            if tue: teachers_schedule[t_name]['الثلاثاء'] = tue
            if wed: teachers_schedule[t_name]['الأربعاء'] = wed
            if thu: teachers_schedule[t_name]['الخميس'] = thu
            flash('تم تحديث جدول المعلم بنجاح تام!')
            
    return render_template_string(SECRETARY_HTML, teachers_schedule=teachers_schedule)

@app.route('/teacher')
def teacher_dashboard():
    username = session.get('user')
    if username not in users_db or users_db[username]['role'] != 'teacher':
        return redirect(url_for('login'))
    
    teacher_name = users_db[username]['name']
    schedule = teachers_schedule.get(teacher_name, {})
    return render_template_string(TEACHER_HTML, teacher_name=teacher_name, schedule=schedule)

@app.route('/admin')
def admin_dashboard():
    if session.get('user') not in users_db or users_db[session.get('user')]['role'] != 'admin':
        return redirect(url_for('login'))
    return render_template_string(ADMIN_HTML, teachers_schedule=teachers_schedule)

@app.route('/change_password', methods=['GET', 'POST'])
def change_password():
    if 'user' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        new_pass = request.form.get('new_password')
        if new_pass:
            users_db[session['user']]['password'] = new_pass
            flash('تم تغيير كلمة المرور بنجاح!')
            role = users_db[session['user']]['role']
            if role == 'admin': return redirect(url_for('admin_dashboard'))
            elif role == 'secretary': return redirect(url_for('secretary_dashboard'))
            else: return redirect(url_for('teacher_dashboard'))
    return render_template_string(CHANGE_PASS_HTML)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
