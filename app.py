from flask import Flask, render_template_string, request, redirect, url_for, session, flash, get_flashed_messages

app = Flask(__name__)
app.secret_key = 'simon_hope_school_2026_complete_staff'

# قائمة المستخدمين وصلاحياتهم مع الكادر الجديد
users_db = {
    'khader': {'password': '000', 'role': 'admin', 'name': 'المدير خضر'},
    'berta': {'password': '000', 'role': 'secretary', 'name': 'الست بيرتا (السكرتيرة)'},
    'fuad': {'password': '000', 'role': 'counselor', 'name': 'الأستاذ فؤاد (المرشد الاجتماعي)'},
    # الأساتذة
    'nizar': {'password': '000', 'role': 'teacher', 'name': 'الأستاذ نزار'},
    'mike': {'password': '000', 'role': 'teacher', 'name': 'الأستاذ مايك'},
    'ahmad': {'password': '000', 'role': 'teacher', 'name': 'الأستاذ أحمد'},
    'waleed': {'password': '000', 'role': 'teacher', 'name': 'الأستاذ وليد'},
    'andress': {'password': '000', 'role': 'teacher', 'name': 'الأستاذ أندريس'},
    # المعلمات
    'khawla': {'password': '000', 'role': 'teacher', 'name': 'المعلمة خيلاء'},
    'duaa': {'password': '000', 'role': 'teacher', 'name': 'المعلمة دعاء'},
    'celeste': {'password': '000', 'role': 'teacher', 'name': 'المعلمة سلستي'},
    'heidi': {'password': '000', 'role': 'teacher', 'name': 'المعلمة هايدي'},
    'eva': {'password': '000', 'role': 'teacher', 'name': 'المعلمة إيفا'},
    'nour': {'password': '000', 'role': 'teacher', 'name': 'المعلمة نور'},
    'razan': {'password': '000', 'role': 'teacher', 'name': 'المعلمة رزان'},
    'dalia': {'password': '000', 'role': 'teacher', 'name': 'المعلمة داليا'},
    'mary': {'password': '000', 'role': 'teacher', 'name': 'المعلمة ميري'},
    'nancy': {'password': '000', 'role': 'teacher', 'name': 'المعلمة نانسي'},
    'rita': {'password': '000', 'role': 'teacher', 'name': 'المعلمة ريتا'}
}

# أيام الأسبوع كاملة
days_list = ['السبت', 'الأحد', 'الإثنين', 'الثلاثاء', 'الأربعاء', 'الخميس']

# جدول الحصص الأولي الشامل للجميع
teachers_schedule = {data['name']: {d: ('فراغ' if d != 'الخميس' else 'تحضير واجتماع') for d in days_list} for data in users_db.values() if data['role'] in ['teacher', 'counselor']}

# متغير عام لحفظ اجتماع المدرسة
school_meeting = {'day': 'الأربعاء', 'note': 'اجتماع عام وشامل لكافة الكادر التعليمي والإداري'}

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
                    <option value="khader">المدير (خضر)</option>
                    <option value="berta">الست بيرتا (السكرتيرة)</option>
                    <option value="fuad">الأستاذ فؤاد (المرشد الاجتماعي)</option>
                    <optgroup label="الأساتذة (المعلمون)">
                        <option value="nizar">الأستاذ نزار</option>
                        <option value="mike">الأستاذ مايك</option>
                        <option value="ahmad">الأستاذ أحمد</option>
                        <option value="waleed">الأستاذ وليد</option>
                        <option value="andress">الأستاذ أندريس</option>
                    </optgroup>
                    <optgroup label="المعلمات الفاضلات">
                        <option value="khawla">المعلمة خيلاء</option>
                        <option value="duaa">المعلمة دعاء</option>
                        <option value="celeste">المعلمة سلستي</option>
                        <option value="heidi">المعلمة هايدي</option>
                        <option value="eva">المعلمة إيفا</option>
                        <option value="nour">المعلمة نور</option>
                        <option value="razan">المعلمة رزان</option>
                        <option value="dalia">المعلمة داليا</option>
                        <option value="mary">المعلمة ميري</option>
                        <option value="nancy">المعلمة نانسي</option>
                        <option value="rita">المعلمة ريتا</option>
                    </optgroup>
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
    .container { max-width: 1000px; margin: auto; background: white; padding: 25px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.08); }
    .nav { display: flex; justify-content: space-between; align-items: center; background: #2c3e50; padding: 12px 20px; border-radius: 8px; color: white; margin-bottom: 25px; }
    .nav a { color: #ecf0f1; text-decoration: none; font-weight: bold; margin-left: 10px; }
    .nav a:hover { color: #3498db; }
    table { width: 100%; border-collapse: collapse; margin-top: 15px; margin-bottom: 25px; overflow-x: auto; display: block; }
    th, td { border: 1px solid #dcdde1; padding: 10px; text-align: center; white-space: nowrap; }
    th { background: #34495e; color: white; font-size: 14px; }
    td { background: #fff; color: #2f3640; font-size: 13px; }
    .alert { padding: 12px; background: #d4edda; color: #155724; border-radius: 6px; margin-bottom: 20px; font-weight: bold; text-align: center; }
    .card { background: #f8f9fa; border: 1px solid #e9ecef; padding: 15px; border-radius: 8px; margin-bottom: 15px; }
</style>
'''

SECRETARY_HTML = COMMON_STYLE + '''
<div class="container">
    <div class="nav">
        <span>لوحة السكرتيرة (الست بيرتا) - إدارة الجداول الشاملة</span>
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
        <h3>تعديل جداول الكادر التعليمي والمرشد:</h3>
        <form method="POST">
            <label style="font-weight:bold; margin-bottom:5px; display:block;">اختر العضو:</label>
            <select name="teacher_name" required style="width:100%; padding:10px; margin-bottom:10px; border-radius:5px; border:1px solid #ccc;">
                <option value="">-- اختر من الكادر --</option>
                {% for t in teachers_schedule.keys() %}
                    <option value="{{ t }}">{{ t }}</option>
                {% endfor %}
            </select>
            
            <label style="font-weight:bold; margin-bottom:5px; display:block;">اختر اليوم:</label>
            <select name="day_name" required style="width:100%; padding:10px; margin-bottom:10px; border-radius:5px; border:1px solid #ccc;">
                <option value="">-- اختر اليوم --</option>
                {% for d in days_list %}
                    <option value="{{ d }}">{{ d }}</option>
                {% endfor %}
            </select>
            
            <label style="font-weight:bold; margin-bottom:5px; display:block;">الحصة / النشاط الجديد:</label>
            <input type="text" name="subject" required placeholder="مثال: رياضيات، إرشاد، لغة عربية..." style="width:100%; padding:10px; margin-bottom:15px; border-radius:5px; border:1px solid #ccc; box-sizing:border-box;">
            
            <button type="submit" style="background: #27ae60; color: white; padding: 12px; border: none; width: 100%; border-radius: 6px; font-weight: bold; cursor: pointer; font-size:16px;">تحديث الجدول</button>
        </form>
    </div>

    <h3>الجداول والأنشطة المعتمدة في المدرسة:</h3>
    <table>
        <tr>
            <th>العضو / المسمى</th>
            {% for d in days_list %}
                <th>{{ d }}</th>
            {% endfor %}
        </tr>
        {% for teacher, days in teachers_schedule.items() %}
        <tr>
            <td><b>{{ teacher }}</b></td>
            {% for d in days_list %}
                <td>{{ days[d] }}</td>
            {% endfor %}
        </tr>
        {% endfor %}
    </table>
</div>
'''

TEACHER_HTML = COMMON_STYLE + '''
<div class="container">
    <div class="nav">
        <span>لوحة المتابعة: {{ teacher_name }}</span>
        <div>
            <a href="/change_password">تغيير كلمة السر</a> | 
            <a href="/logout">تسجيل خروج</a>
        </div>
    </div>
    
    <div style="background: #e8f4fd; border-right: 5px solid #3498db; padding: 15px; border-radius: 5px; margin-bottom: 20px;">
        <h4 style="margin-top:0; color:#2980b9;">إشعار هام من إدارة المدرسة (المدير خضر):</h4>
        <p style="margin-bottom:0;">موعد الاجتماع العام محدد في يوم: <b>{{ meeting.day }}</b> ({{ meeting.note }})</p>
    </div>

    <h3>جدول الحصص والمهام الأسبوعي الخاص بك:</h3>
    <table>
        <tr>
            {% for d in days_list %}
                <th>{{ d }}</th>
            {% endfor %}
        </tr>
        <tr>
            {% for d in days_list %}
                <td><b>{{ schedule.get(d, 'فراغ') }}</b></td>
            {% endfor %}
        </tr>
    </table>
</div>
'''

ADMIN_HTML = COMMON_STYLE + '''
<div class="container">
    <div class="nav">
        <span>لوحة الإدارة العليا (المدير خضر) - الرقابة الشاملة</span>
        <div>
            <a href="/change_password">تغيير كلمة السر</a> | 
            <a href="/logout">تسجيل خروج</a>
        </div>
    </div>
    
    <div style="background: #e8f4fd; border-right: 5px solid #3498db; padding: 15px; border-radius: 5px; margin-bottom: 20px;">
        <h3 style="margin-top:0; color:#2980b9;">أهلاً بك يا سيادة المدير خضر 🌟</h3>
        <p style="margin-bottom:10px;">من هنا يمكنك مراقبة جداول الكادر التعليمي كاملاً، وتحديد موعد الاجتماع العام.</p>
        
        <form method="POST" style="margin-top: 10px; display: flex; gap: 10px; align-items: center;">
            <label style="font-weight:bold; margin:0;">تحديد يوم الاجتماع:</label>
            <select name="meeting_day" style="padding: 6px; border-radius: 4px; border: 1px solid #ccc;">
                {% for d in days_list %}
                    <option value="{{ d }}" {% if meeting.day == d %}selected{% endif %}>{{ d }}</option>
                {% endfor %}
            </select>
            <input type="text" name="meeting_note" value="{{ meeting.note }}" placeholder="سبب أو ملاحظة الاجتماع" style="flex-grow:1; padding: 6px; border-radius: 4px; border: 1px solid #ccc;">
            <button type="submit" style="background: #2980b9; color: white; border: none; padding: 8px 15px; border-radius: 4px; cursor: pointer; font-weight: bold;">حفظ موعد الاجتماع</button>
        </form>
    </div>
    
    {% with messages = get_flashed_messages() %}
        {% if messages %}
            {% for message in messages %}
                <div class="alert">{{ message }}</div>
            {% endfor %}
        {% endif %}
    {% endwith %}

    <h3>جدول الحصص والأنشطة الشامل لكافة المعلمين والكادر:</h3>
    <table>
        <tr>
            <th>العضو / المسمى</th>
            {% for d in days_list %}
                <th>{{ d }}</th>
            {% endfor %}
        </tr>
        {% for teacher, days in teachers_schedule.items() %}
        <tr>
            <td><b>{{ teacher }}</b></td>
            {% for d in days_list %}
                <td style="color: #2c3e50;">{{ days[d] }}</td>
            {% endfor %}
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
            elif role in ['teacher', 'counselor']:
                return redirect(url_for('teacher_dashboard'))
        flash('اسم المستخدم أو كلمة المرور غير صحيحة!')
    return render_template_string(HOME_HTML)

@app.route('/secretary', methods=['GET', 'POST'])
def secretary_dashboard():
    if session.get('user') not in users_db or users_db[session.get('user')]['role'] != 'secretary':
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        t_name = request.form.get('teacher_name')
        day_name = request.form.get('day_name')
        subject = request.form.get('subject')
        if t_name in teachers_schedule and day_name in days_list:
            teachers_schedule[t_name][day_name] = subject
            flash('تم تحديث جدول العضو بنجاح تام!')
            
    return render_template_string(SECRETARY_HTML, teachers_schedule=teachers_schedule, days_list=days_list)

@app.route('/teacher')
def teacher_dashboard():
    username = session.get('user')
    if username not in users_db or users_db[username]['role'] not in ['teacher', 'counselor']:
        return redirect(url_for('login'))
    
    teacher_name = users_db[username]['name']
    schedule = teachers_schedule.get(teacher_name, {})
    return render_template_string(TEACHER_HTML, teacher_name=teacher_name, schedule=schedule, days_list=days_list, meeting=school_meeting)

@app.route('/admin', methods=['GET', 'POST'])
def admin_dashboard():
    if session.get('user') not in users_db or users_db[session.get('user')]['role'] != 'admin':
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        m_day = request.form.get('meeting_day')
        m_note = request.form.get('meeting_note')
        if m_day:
            school_meeting['day'] = m_day
            school_meeting['note'] = m_note
            flash('تم تحديث موعد وحالة الاجتماع بنجاح!')

    return render_template_string(ADMIN_HTML, teachers_schedule=teachers_schedule, days_list=days_list, meeting=school_meeting)

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
