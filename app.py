from flask import Flask, render_template_string, request, redirect, url_for, session, flash

app = Flask(__name__)
app.secret_key = 'simon_secret_key_2026'

# قاعدة بيانات مؤقتة بذاكرة النظام للتجربة والتعديل السريع
users_db = {
    'admin': {'password': '123', 'role': 'admin', 'name': 'المدير العام'},
    'berta': {'password': '123', 'role': 'secretary', 'name': 'السكرتيرة بيرتا'},
    'teacher1': {'password': '123', 'role': 'teacher', 'name': 'الأستاذ أحمد'},
    'teacher2': {'password': '123', 'role': 'teacher', 'name': 'الأستاذ محمد'}
}

# جدول الحصص لكل معلم
teachers_schedule = {
    'الأستاذ أحمد': {'السبت': ['رياضيات - أولى ثانوي', 'فيزياء - ثاني ثانوي'], 'الأحد': ['فراغ', 'رياضيات - عاشر']},
    'الأستاذ محمد': {'السبت': ['لغة عربية - ثامن', 'فراغ'], 'الأحد': ['تاريخ - أولى ثانوي', 'جغرافيا - تاسع']}
}

# لوحة الإداريات والاجتماعات للمدير
system_events = []

# --- صفحة تسجيل الدخول ---
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username in users_db and users_db[username]['password'] == password:
            session['username'] = username
            session['role'] = users_db[username]['role']
            session['name'] = users_db[username]['name']
            
            # توجيه حسب الصلاحية
            if session['role'] == 'admin':
                return redirect(url_for('admin_dashboard'))
            elif session['role'] == 'secretary':
                return redirect(url_for('secretary_dashboard'))
            else:
                return redirect(url_for('teacher_dashboard'))
        else:
            flash('اسم المستخدم أو كلمة المرور خطأ!', 'danger')
    return render_template_string(LOGIN_HTML)

# --- لوحة المدير ---
@app.route('/admin', methods=['GET', 'POST'])
def admin_dashboard():
    if 'username' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        event = request.form.get('event')
        if event:
            system_events.append(event)
            flash('تم إضافة الاجتماع/التعميم بنجاح', 'success')
            
    return render_template_string(ADMIN_HTML, events=system_events, name=session['name'])

# --- لوحة السكرتيرة (تعديل جداول المعلمين) ---
@app.route('/secretary', methods=['GET', 'POST'])
def secretary_dashboard():
    if 'username' not in session or session['role'] not in ['admin', 'secretary']:
        return redirect(url_for('login'))
    
    selected_teacher = request.form.get('teacher_name')
    day = request.form.get('day')
    subject = request.form.get('subject')
    
    if request.method == 'POST' and selected_teacher and day and subject:
        if selected_teacher not in teachers_schedule:
            teachers_schedule[selected_teacher] = {}
        if day not in teachers_schedule[selected_teacher]:
            teachers_schedule[selected_teacher][day] = []
        teachers_schedule[selected_teacher][day].append(subject)
        flash(f'تم إضافة الحصة بنجاح للمعلم {selected_teacher}', 'success')

    teachers_list = [u['name'] for u in users_db.values() if u['role'] == 'teacher']
    return render_template_string(SECRETARY_HTML, teachers=teachers_list, schedule=teachers_schedule, name=session['name'])

# --- لوحة المعلم ---
@app.route('/teacher')
def teacher_dashboard():
    if 'username' not in session or session['role'] != 'teacher':
        return redirect(url_for('login'))
    
    teacher_name = session['name']
    my_sched = teachers_schedule.get(teacher_name, {})
    return render_template_string(TEACHER_HTML, schedule=my_sched, events=system_events, name=teacher_name)

# --- تغيير كلمة المرور لأي مستخدم ---
@app.route('/change_password', methods=['GET', 'POST'])
def change_password():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        new_pass = request.form.get('new_password')
        if new_pass:
            users_db[session['username']]['password'] = new_pass
            flash('تم تغيير كلمة السر بنجاح!', 'success')
            
    return render_template_string(CHANGE_PASS_HTML)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ================= Templates (واجهات التصميم) =================

COMMON_STYLE = '''
<style>
    body { font-family: Tahoma, sans-serif; background-color: #f4f7f6; margin: 0; padding: 20px; direction: rtl; text-align: right; }
    .container { max-width: 600px; margin: auto; background: white; padding: 20px; border-radius: 10px; box-shadow: 0px 0px 10px rgba(0,0,0,0.1); }
    h2 { color: #333; }
    input, select, textarea { width: 100%; padding: 10px; margin: 8px 0; border: 1px solid #ccc; border-radius: 5px; box-sizing: border-box; }
    button { background-color: #007bff; color: white; padding: 10px 15px; border: none; border-radius: 5px; cursor: pointer; width: 100%; font-size: 16px; }
    button:hover { background-color: #0056b3; }
    .alert { padding: 10px; margin: 10px 0; border-radius: 5px; }
    .alert-danger { background-color: #f8d7da; color: #721c24; }
    .alert-success { background-color: #d4edda; color: #155724; }
    .nav { margin-bottom: 20px; display: flex; gap: 10px; }
    .nav a { background: #6c757d; color: white; padding: 8px 12px; text-decoration: none; border-radius: 4px; font-size: 14px; }
</style>
'''

LOGIN_HTML = COMMON_STYLE + '''
<div class="container">
    <h2>تسجيل الدخول</h2>
    {% with messages = get_flashed_messages(with_categories=true) %}
      {% if messages %}
        {% for category, message in messages %}
          <div class="alert alert-{{ category }}">{{ message }}</div>
        {% endfor %}
      {% endif %}
    {% endwith %}
    <form method="POST">
        <label>اسم المستخدم (admin, berta, teacher1, teacher2):</label>
        <input type="text" name="username" required>
        <label>كلمة المرور (123):</label>
        <input type="password" name="password" required>
        <button type="submit">دخول</button>
    </form>
</div>
'''

CHANGE_PASS_HTML = COMMON_STYLE + '''
<div class="container">
    <div class="nav">
        <a href="javascript:history.back()">رجوع</a>
        <a href="/logout">تسجيل خروج</a>
    </div>
    <h2>تغيير كلمة المرور</h2>
    {% with messages = get_flashed_messages(with_categories=true) %}
      {% if messages %}
        {% for category, message in messages %}
          <div class="alert alert-{{ category }}">{{ message }}</div>
        {% endfor %}
      {% endif %}
    {% endwith %}
    <form method="POST">
        <label>كلمة المرور الجديدة:</label>
        <input type="password" name="new_password" required>
        <button type="submit">تحديث كلمة السر</button>
    </form>
</div>
'''

ADMIN_HTML = COMMON_STYLE + '''
<div class="container">
    <div class="nav">
        <a href="/change_password">تغيير كلمة السر</a>
        <a href="/logout">تسجيل خروج</a>
    </div>
    <h2>أهلاً بك يا مدير: {{ name }}</h2>
    <hr>
    <h3>إضافة اجتماع أو تعميم عام:</h3>
    {% with messages = get_flashed_messages(with_categories=true) %}
      {% if messages %}
        {% for category, message in messages %}
          <div class="alert alert-{{ category }}">{{ message }}</div>
        {% endfor %}
      {% endif %}
    {% endwith %}
    <form method="POST">
        <textarea name="event" placeholder="اكتب تفاصيل الاجتماع أو التعميم هنا..." rows="3" required></textarea>
        <button type="submit">نشر الاجتماع</button>
    </form>
    
    <h3>الاجتماعات والتعاميم الحالية:</h3>
    <ul>
        {% for ev in events %}
            <li>{{ ev }}</li>
        {% else %}
            <p>لا توجد اجتماعات حالياً.</p>
        {% endfor %}
    </ul>
</div>
'''

SECRETARY_HTML = COMMON_STYLE + '''
<div class="container">
    <div class="nav">
        <a href="/change_password">تغيير كلمة السر</a>
        <a href="/logout">تسجيل خروج</a>
    </div>
    <h2>لوحة السكرتيرة (تعديل جداول المعلمين)</h2>
    {% with messages = get_flashed_messages(with_categories=true) %}
      {% if messages %}
        {% for category, message in messages %}
          <div class="alert alert-{{ category }}">{{ message }}</div>
        {% endfor %}
      {% endif %}
    {% endwith %}
    <form method="POST">
        <label>اختر المعلم:</label>
        <select name="teacher_name" required>
            <option value="">-- اختر المعلم من القائمة --</option>
            {% for t in teachers %}
                <option value="{{ t }}">{{ t }}</option>
            {% endfor %}
        </select>
        
        <label>اليوم:</label>
        <select name="day" required>
            <option value="السبت">السبت</option>
            <option value="الأحد">الأحد</option>
            <option value="الإثنين">الإثنين</option>
            <option value="الثلاثاء">الثلاثاء</option>
            <option value="الأربعاء">الأربعاء</option>
            <option value="الخميس">الخميس</option>
        </select>
        
        <label>الحصة / المادة:</label>
        <input type="text" name="subject" placeholder="مثال: رياضيات - صف أول" required>
        
        <button type="submit">إضافة الحصة للمعلم</button>
    </form>
    
    <hr>
    <h3>الجداول الحالية لجميع المعلمين:</h3>
    {{ schedule }}
</div>
'''

TEACHER_HTML = COMMON_STYLE + '''
<div class="container">
    <div class="nav">
        <a href="/change_password">تغيير كلمة السر</a>
        <a href="/logout">تسجيل خروج</a>
    </div>
    <h2>أهلاً بك يا أستاذ: {{ name }}</h2>
    <hr>
    <h3>جدولي الأسبوعي:</h3>
    <ul>
        {% for day, classes in schedule.items() %}
            <li><strong>{{ day }}:</strong> {{ classes | join(', ') }}</li>
        {% else %}
            <p>ليس لديك حصص مضافة حالياً.</p>
        {% endfor %}
    </ul>
    
    <hr>
    <h3>الاجتماعات والتعاميم الموجهة إليك:</h3>
    <ul>
        {% for ev in events %}
            <li>📌 {{ ev }}</li>
        {% else %}
            <p>لا توجد اجتماعات جديدة.</p>
        {% endfor %}
    </ul>
</div>
'''

if __name__ == '__main__':
    app.run(debug=True)
