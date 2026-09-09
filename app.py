from flask import Flask, render_template_string, request, redirect, url_for, session, flash

app = Flask(__name__)
app.secret_key = 'simon_hope_school_2026_pro'

# قاعدة بيانات المستخدمين (شاملة الإدارة، السكرتيرة، والمعلمين الجدد والقدامى)
users_db = {
    'admin': {'password': '123', 'role': 'admin', 'name': 'المدير خضر'},
    'berta': {'password': '123', 'role': 'secretary', 'name': 'السكرتيرة بيرتا'},
    'ahmad': {'password': '123', 'role': 'teacher', 'name': 'الأستاذ أحمد'},
    'nizar': {'password': '333', 'role': 'teacher', 'name': 'الأستاذ نزار'},
    'mike': {'password': '123', 'role': 'teacher', 'name': 'الأستاذ مايك'},
    'sohaila': {'password': '123', 'role': 'teacher', 'name': 'المس سهيلة'}
}

# جدول الحصص الشامل لكل معلم (مرتب لكل أيام الأسبوع)
teachers_schedule = {
    'الأستاذ أحمد': {
        'السبت': 'رياضيات - أولى ثانوي', 'الأحد': 'فيزياء', 'الإثنين': 'فراغ', 'الثلاثاء': 'رياضيات', 'الأربعاء': 'فراغ', 'الخميس': 'رياضيات'
    },
    'الأستاذ نزار': {
        'السبت': 'لغة عربية', 'الأحد': 'تاريخ', 'الإثنين': 'جغرافيا', 'الثلاثاء': 'فراغ', 'الأربعاء': 'لغة عربية', 'الخميس': 'فراغ'
    },
    'الأستاذ مايك': {
        'السبت': 'لغة إنجليزية', 'الأحد': 'محادثة', 'الإثنين': 'قواعد إنجليزية', 'الثلاثاء': 'لغة إنجليزية', 'الأربعاء': 'أنشطة', 'الخميس': 'مراجعة'
    },
    'المس سهيلة': {
        'السبت': 'تربية إسلامية', 'الأحد': 'فراغ', 'الإثنين': 'تلاوة', 'الثلاثاء': 'تربية إسلامية', 'الأربعاء': 'محفوظات', 'الخميس': 'تربية إسلامية'
    }
}

# نظام الإشعارات والاجتماعات المتقدم (يحتوي على النص، المرسل إليهم، ورقم التعريف)
system_announcements = []

# --- 1. صفحة تسجيل الدخول ---
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username in users_db and users_db[username]['password'] == password:
            session['username'] = username
            session['role'] = users_db[username]['role']
            session['name'] = users_db[username]['name']
            
            if session['role'] == 'admin':
                return redirect(url_for('admin_dashboard'))
            elif session['role'] == 'secretary':
                return redirect(url_for('secretary_dashboard'))
            else:
                return redirect(url_for('teacher_dashboard'))
        else:
            flash('اسم المستخدم أو كلمة المرور خطأ!', 'danger')
    return render_template_string(LOGIN_HTML)

# --- 2. لوحة المدير المتقدمة (إرسال تعاميم واختيار المعلمين) ---
@app.route('/admin', methods=['GET', 'POST'])
def admin_dashboard():
    if 'username' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        title = request.form.get('title')
        message = request.form.get('message')
        target_teacher = request.form.get('target_teacher', 'الكل')
        
        if title and message:
            announcement_data = {
                'id': len(system_announcements) + 1,
                'title': title,
                'message': message,
                'target': target_teacher
            }
            system_announcements.append(announcement_data)
            flash('تم نشر الاجتماع/التعميم بنجاح وإرساله للمعلمين المعنيين مع جرس التنبيه!', 'success')
            
    teachers_list = [u['name'] for u in users_db.values() if u['role'] == 'teacher']
    return render_template_string(ADMIN_HTML, teachers=teachers_list, announcements=system_announcements, name=session['name'])

# --- 3. لوحة السكرتيرة (تعديل الجدول الكامل لكل أيام الأسبوع دفعة واحدة) ---
@app.route('/secretary', methods=['GET', 'POST'])
def secretary_dashboard():
    if 'username' not in session or session['role'] not in ['admin', 'secretary']:
        return redirect(url_for('login'))
    
    selected_teacher = request.form.get('teacher_name')
    
    if request.method == 'POST' and selected_teacher:
        sat = request.form.get('sat', '')
        sun = request.form.get('sun', '')
        mon = request.form.get('mon', '')
        tue = request.form.get('tue', '')
        wed = request.form.get('wed', '')
        thu = request.form.get('thu', '')
        
        teachers_schedule[selected_teacher] = {
            'السبت': sat, 'الأحد': sun, 'الإثنين': mon, 'الثلاثاء': tue, 'الأربعاء': wed, 'الخميس': thu
        }
        flash(f'تم حفظ وتحديث الجدول الأسبوعي الكامل للمعلم: {selected_teacher} بنجاح!', 'success')

    teachers_list = [u['name'] for u in users_db.values() if u['role'] == 'teacher']
    return render_template_string(SECRETARY_HTML, teachers=teachers_list, schedule=teachers_schedule, name=session['name'])

# --- 4. لوحة المعلم (مع جرس التنبيه الصوتي عند وجود تعميم جديد) ---
@app.route('/teacher')
def teacher_dashboard():
    if 'username' not in session or session['role'] != 'teacher':
        return redirect(url_for('login'))
    
    teacher_name = session['name']
    my_sched = teachers_schedule.get(teacher_name, {})
    
    # تصفية التعاميم الموجهة لهذا المعلم خصيصاً أو للكل
    my_announcements = [
        ann for ann in system_announcements 
        if ann['target'] == 'الكل' or ann['target'] == teacher_name
    ]
    
    return render_template_string(TEACHER_HTML, schedule=my_sched, announcements=my_announcements, name=teacher_name)

# --- 5. تغيير كلمة المرور لأي مستخدم ---
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

# ================= Templates & Design (التصميم الحديث وجرس الصوت) =================

COMMON_STYLE = '''
<style>
    body { font-family: Tahoma, sans-serif; background-color: #f4f7f6; margin: 0; padding: 20px; direction: rtl; text-align: right; }
    .container { max-width: 650px; margin: auto; background: white; padding: 25px; border-radius: 12px; box-shadow: 0px 4px 15px rgba(0,0,0,0.08); }
    h2 { color: #2c3e50; }
    input, select, textarea { width: 100%; padding: 12px; margin: 8px 0 15px 0; border: 1px solid #ddd; border-radius: 6px; box-sizing: border-box; font-size: 14px; }
    button { background-color: #0275d8; color: white; padding: 12px; border: none; border-radius: 6px; cursor: pointer; width: 100%; font-size: 16px; font-weight: bold; }
    button:hover { background-color: #025aa5; }
    .alert { padding: 12px; margin: 15px 0; border-radius: 6px; font-size: 14px; }
    .alert-danger { background-color: #f8d7da; color: #721c24; }
    .alert-success { background-color: #d4edda; color: #155724; }
    .nav { margin-bottom: 20px; display: flex; gap: 10px; }
    .nav a { background: #6c757d; color: white; padding: 8px 15px; text-decoration: none; border-radius: 6px; font-size: 14px; }
    .card { background: #fdfdfd; border: 1px solid #e1e8ed; padding: 15px; border-radius: 8px; margin-bottom: 12px; }
</style>
'''

LOGIN_HTML = COMMON_STYLE + '''
<div class="container">
    <h2>تسجيل الدخول - مدرسة الأمل</h2>
    {% with messages = get_flashed_messages(with_categories=true) %}
      {% if messages %}
        {% for category, message in messages %}
          <div class="alert alert-{{ category }}">{{ message }}</div>
        {% endfor %}
      {% endif %}
    {% endwith %}
    <form method="POST">
        <label>اسم المستخدم:</label>
        <input type="text" name="username" placeholder="admin, berta, ahmad, mike, sohaila..." required>
        <label>كلمة المرور:</label>
        <input type="password" name="password" required>
        <button type="submit">دخول النظام</button>
    </form>
</div>
'''

CHANGE_PASS_HTML = COMMON_STYLE + '''
<div class="container">
    <div class="nav">
        <a href="javascript:history.back()">رجوع</a>
        <a href="/logout">تسجيل خروج</a>
    </div>
    <h2>تغيير كلمة المرور الخاصة بك</h2>
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
        <button type="submit">حفظ التغيير</button>
    </form>
</div>
'''

ADMIN_HTML = COMMON_STYLE + '''
<div class="container">
    <div class="nav">
        <a href="/change_password">تغيير كلمة السر</a>
        <a href="/logout">تسجيل خروج</a>
    </div>
    <h2>لوحة تحكم المدير العام: {{ name }}</h2>
    <hr>
    <h3>إرسال اجتماع أو تعميم رسمي:</h3>
    {% with messages = get_flashed_messages(with_categories=true) %}
      {% if messages %}
        {% for category, message in messages %}
          <div class="alert alert-{{ category }}">{{ message }}</div>
        {% endfor %}
      {% endif %}
    {% endwith %}
    <form method="POST">
        <label>عنوان الاجتماع / التعميم:</label>
        <input type="text" name="title" placeholder="مثال: اجتماع طارئ للهيئة التدريسية" required>
        
        <label>الموجه إليهم:</label>
        <select name="target_teacher">
            <option value="الكل">جميع المعلمين والمعلمات (الكل)</option>
            {% for t in teachers %}
                <option value="{{ t }}">{{ t }}</option>
            {% endfor %}
        </select>
        
        <label>التفاصيل والمحتوى:</label>
        <textarea name="message" rows="4" placeholder="اكتب تفاصيل الاجتماع أو التعميم هنا..." required></textarea>
        
        <button type="submit" style="background-color: #d9534f;">إرسال التعميم مع جرس التنبيه</button>
    </form>
    
    <h3>التعاميم والاجتماعات السابقة:</h3>
    {% for ann in announcements %}
        <div class="card">
            <strong>📢 {{ ann.title }}</strong> (موجه إلى: <em>{{ ann.target }}</em>)
            <p>{{ ann.message }}</p>
        </div>
    {% else %}
        <p>لا توجد تعاميم مرسلة حالياً.</p>
    {% endfor %}
</div>
'''

SECRETARY_HTML = COMMON_STYLE + '''
<div class="container">
    <div class="nav">
        <a href="/change_password">تغيير كلمة السر</a>
        <a href="/logout">تسجيل خروج</a>
    </div>
    <h2>لوحة السكرتيرة (تعديل الجدول الأسبوعي الكامل)</h2>
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
            <option value="">-- اختر المعلم --</option>
            {% for t in teachers %}
                <option value="{{ t }}">{{ t }}</option>
            {% endfor %}
        </select>
        
        <h4 style="color: #0275d8; margin-top: 15px;">حدد حصص أيام الأسبوع كاملة:</h4>
        
        <label>السبت:</label>
        <input type="text" name="sat" placeholder="مثال: رياضيات, فراغ...">
        
        <label>الأحد:</label>
        <input type="text" name="sun" placeholder="مثال: فيزياء, لغة عربية...">
        
        <label>الإثنين:</label>
        <input type="text" name="mon" placeholder="مثال: فراغ, أنشطة...">
        
        <label>الثلاثاء:</label>
        <input type="text" name="tue" placeholder="مثال: تاريخ, جغرافيا...">
        
        <label>الأربعاء:</label>
        <input type="text" name="wed" placeholder="مثال: لغة إنجليزية...">
        
        <label>الخميس:</label>
        <input type="text" name="thu" placeholder="مثال: مراجعة أسبوعية...">
        
        <button type="submit">حفظ الجدول الأسبوعي الكامل</button>
    </form>
</div>
'''

TEACHER_HTML = COMMON_STYLE + '''
<div class="container">
    <div class="nav">
        <a href="/change_password">تغيير كلمة السر</a>
        <a href="/logout">تسجيل خروج</a>
    </div>
    <h2>أهلاً بك يا أستاذ/ة: {{ name }}</h2>
    <hr>
    
    <!-- جرس تنبيه صوتي تلقائي عند وجود إشعارات جديدة -->
    {% if announcements %}
        <audio id="notifSound" autoplay>
            <source src="https://assets.mixkit.co/active_storage/sfx/2869/2869-preview.mp3" type="audio/mpeg">
        </audio>
        <script>
            window.addEventListener('DOMContentLoaded', (event) => {
                var audio = document.getElementById('notifSound');
                if(audio) {
                    audio.play().catch(error => { console.log("Audio autoplay blocked by browser"); });
                }
            });
        </script>
    {% endif %}

    <h3>الاجتماعات والتعاميم الموجهة إليك:</h3>
    {% for ann in announcements %}
        <div class="card" style="border-right: 4px solid #d9534f; background: #fff5f5;">
            <strong>🔔 {{ ann.title }}</strong>
            <p>{{ ann.message }}</p>
        </div>
    {% else %}
        <p style="color: green;">لا توجد تعاميم أو اجتماعات جديدة حالياً.</p>
    {% endfor %}

    <h3>جدولك الأسبوعي الكامل:</h3>
    {% for day, classes in schedule.items() %}
        <div class="card">
            <strong>{{ day }}:</strong> {{ classes if classes else 'لا توجد حصص' }}
        </div>
    {% else %}
        <p>لم يتم إرفاق جدول حصص لك بعد.</p>
    {% endfor %}
</div>
'''

if __name__ == '__main__':
    app.run(debug=True)
