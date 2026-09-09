from flask import Flask, render_template_string, request, redirect, url_for, session, flash, get_flashed_messages

app = Flask(__name__)
app.secret_key = 'simon_hope_school_2026_ultimate'

# المستخدمين والباسورد تبعهم '000' افتراضياً (مدير، سكرتيرة، وكل المعلمين)
users_db = {
    'admin': {'password': '000', 'role': 'admin', 'name': 'المدير العام'},
    'berta': {'password': '000', 'role': 'secretary', 'name': 'الست بيرتا (السكرتيرة)'},
    'ahmad': {'password': '000', 'role': 'teacher', 'name': 'الأستاذ أحمد'},
    'nizar': {'password': '000', 'role': 'teacher', 'name': 'الأستاذ نزار'},
    'mike': {'password': '000', 'role': 'teacher', 'name': 'الأستاذ مايك'},
    'sohaila': {'password': '000', 'role': 'teacher', 'name': 'المس سهيلة'}
}

# جدول الحصص الأسبوعي الشامل (يشمل مايك وسهيلة وكل الأساتذة)
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

system_announcements = []

HOME_HTML = '''
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <title>مدرسة الأمل - نظام الجداول المدرسية</title>
    <style>
        body { font-family: Tahoma, sans-serif; background-color: #f4f7f6; margin: 0; padding: 20px; direction: rtl; text-align: right; }
        .container { max-width: 600px; margin: 0 auto; background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); }
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
                <label>اسم المستخدم:</label>
                <select name="username" required>
                    <option value="">-- اختر اسم المستخدم --</option>
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
        <div class="footer-note">جميع الباسوردات الافتراضية هي 000 لتسهيل الدخول.</div>
    </div>
</body>
</html>
'''

SECRETARY_HTML = COMMON_STYLE = '''
<style>
    body { font-family: Tahoma, sans-serif; background: #f9f9f9; padding: 20px; direction: rtl; text-align: right; }
    .container { max-width: 800px; margin: auto; background: white; padding: 25px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.08); }
    .nav { display: flex; justify-content: space-between; background: #2c3e50; padding: 10px 15px; border-radius: 6px; color: white; margin-bottom: 20px; }
    .nav a { color: white; text-decoration: none; font-weight: bold; }
    table { width: 100%; border-collapse: collapse; margin-top: 15px; }
    th, td { border: 1px solid #ddd; padding: 10px; text-align: center; }
    th { background: #34495e; color: white; }
    .alert { padding: 10px; background: #d4edda; color: #155724; border-radius: 5px; margin-bottom: 15px; }
</style>
'''

SECRETARY_HTML = COMMON_STYLE + '''
<div class="container">
    <div class="nav">
        <span>لوحة السكرتيرة (تعديل الجداول الأسبوعية)</span>
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

    <form method="POST">
        <label>اختر المعلم:</label>
        <select name="teacher_name" required>
            <option value="">-- اختر المعلم لتعديل جدوله --</option>
            {% for t in teachers_schedule.keys() %}
                <option value="{{ t }}">{{ t }}</option>
            {% endfor %}
        </select>
        
        <label style="margin-top: 10px;">يوم الثلاثاء:</label>
        <input type="text" name="tue" placeholder="الحصة/المادة يوم الثلاثاء">
        
        <label style="margin-top: 10px;">يوم الأربعاء:</label>
        <input type="text" name="wed" placeholder="الحصة/المادة يوم الأربعاء">
        
        <label style="margin-top: 10px;">يوم الخميس:</label>
        <input type="text" name="thu" placeholder="الحصة/المادة يوم الخميس">
        
        <button type="submit" style="margin-top: 15px; background: #27ae60; color: white; padding: 10px; border: none; width: 100%; border-radius: 5px; font-weight: bold; cursor: pointer;">حفظ وتحديث الجدول</button>
    </form>

    <h3 style="margin-top: 30px;">الجداول الحالية لجميع المعلمين:</h3>
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
            <th>الحصة / المادة</th>
        </tr>
        <tr>
            <td>الثلاثاء</td>
            <td>{{ schedule.get('الثلاثاء', 'لا يوجد حصة') }}</td>
        </tr>
        <tr>
            <td>الأربعاء</td>
            <td>{{ schedule.get('الأربعاء', 'لا يوجد حصة') }}</td>
        </tr>
        <tr>
            <td>الخميس</td>
            <td>{{ schedule.get('الخميس', 'لا يوجد حصة') }}</td>
        </tr>
    </table>
</div>
'''

ADMIN_HTML = COMMON_STYLE + '''
<div class="container">
    <div class="nav">
        <span>لوحة الإدارة العامة (المدير)</span>
        <div>
            <a href="/change_password">تغيير كلمة السر</a> | 
            <a href="/logout">تسجيل خروج</a>
        </div>
    </div>
    
    <h2>أهلاً بك يا مدير النظام</h2>
    <p>بإمكانك الاطلاع على كافة جداول المعلمين المعتمدة في المدرسة:</p>
    
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
            <td>{{ days['الثلاثاء'] }}</td>
            <td>{{ days['الأربعاء'] }}</td>
            <td>{{ days['الخميس'] }}</td>
        </tr>
        {% endfor %}
    </table>
</div>
'''

CHANGE_PASS_HTML = COMMON_STYLE + '''
<div class="container">
    <div class="nav">
        <span>تغيير كلمة المرور</span>
        <a href="javascript:history.back()">رجوع</a>
    </div>
    <form method="POST">
        <label>كلمة المرور الجديدة:</label>
        <input type="password" name="new_password" required placeholder="أدخل كلمة المرور الجديدة">
        <button type="submit" style="margin-top: 15px; background: #e67e22; color: white; padding: 10px; border: none; width: 100%; border-radius: 5px; font-weight: bold; cursor: pointer;">تحديث كلمة المرور</button>
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
            flash('تم تحديث جدول المعلم بنجاح!')
            
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
    if session.get('user') not in users_db or users_db[session.get('user இந்தியாவின்')]['role'] != 'admin':
        # Fallback security check
        pass
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
