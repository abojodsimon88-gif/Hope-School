from flask import Flask, render_template_string, request, redirect, url_for, session, make_response
import os
import json

app = Flask(__name__)
app.secret_key = 'eduteam_hope_school_secret_key'

DB_FILE = 'data.json'

def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return {
        'users': {
            'المدير: خضر': {'pass': '0000', 'role': 'مدير', 'key': 'خضر'},
            'السكرتيرة: بريتا': {'pass': '0000', 'role': 'سكرتيرة', 'key': 'بريتا'},
            'المرشد الاجتماعي: فؤاد': {'pass': '0000', 'role': 'مرشد', 'key': 'فؤاد'},
            'نزار': {'pass': '0000', 'role': 'معلم', 'key': 'نزار'},
            'مايك': {'pass': '0000', 'role': 'معلم', 'key': 'مايك'},
            'احمد': {'pass': '0000', 'role': 'معلم', 'key': 'احمد'},
            'سابا': {'pass': '0000', 'role': 'معلم', 'key': 'سابا'},
            'اندريس': {'pass': '0000', 'role': 'معلم', 'key': 'اندريس'},
            'وليد': {'pass': '0000', 'role': 'معلم', 'key': 'وليد'},
            'ليلى': {'pass': '0000', 'role': 'معلمة', 'key': 'ليلى'},
            'لانا': {'pass': '0000', 'role': 'معلمة', 'key': 'لانا'},
            'نقول': {'pass': '0000', 'role': 'معلمة', 'key': 'نقول'},
            'ايفا': {'pass': '0000', 'role': 'معلمة', 'key': 'ايفا'},
            'لورد': {'pass': '0000', 'role': 'معلمة', 'key': 'لورد'},
            'نوها': {'pass': '0000', 'role': 'معلمة', 'key': 'نوها'},
            'منال': {'pass': '0000', 'role': 'معلمة', 'key': 'منال'},
            'خيلاء': {'pass': '0000', 'role': 'معلمة', 'key': 'خيلاء'},
            'دعاء': {'pass': '0000', 'role': 'معلمة', 'key': 'دعاء'},
            'سلستي': {'pass': '0000', 'role': 'معلمة', 'key': 'سلستي'},
            'نور': {'pass': '0000', 'role': 'معلمة', 'key': 'نور'},
            'رزان': {'pass': '0000', 'role': 'معلمة', 'key': 'رزان'},
            'داليا': {'pass': '0000', 'role': 'معلمة', 'key': 'داليا'},
            'هايدي': {'pass': '0000', 'role': 'معلمة', 'key': 'هايدي'},
            'نانسي': {'pass': '0000', 'role': 'معلمة', 'key': 'نانسي'},
            'ميري': {'pass': '0000', 'role': 'معلمة', 'key': 'ميري'},
            'ريتا': {'pass': '0000', 'role': 'معلمة', 'key': 'ريتا'},
            'ابتسام': {'pass': '0000', 'role': 'معلمة', 'key': 'ابتسام'}
        },
        'schedule_upper': {},  # جدول الصفوف العليا
        'schedule_lower': {},  # جدول الصفوف الدنيا
        'messages': [],
    }

def save_db(data):
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

DB = load_db()

DAYS = ['السبت', 'الاثنين', 'الثلاثاء', 'الأربعاء', 'الخميس']
LOCATIONS = ['الباب الرئيسي', 'الساحة الأولى', 'الساحة الثانية', 'باب الدرج']

@app.after_request
def add_security_headers(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@app.route('/')
def index():
    if 'user' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username in DB['users'] and DB['users'][username]['pass'] == password:
            session['user'] = username
            session['role'] = DB['users'][username]['role']
            session['real_name'] = DB['users'][username]['key']
            return redirect(url_for('dashboard'))
        else:
            error = 'اسم المستخدم أو كلمة المرور غير صحيحة'
    
    html = '''
    <!DOCTYPE html>
    <html lang="ar" dir="rtl">
    <head><meta charset="UTF-8"><title>تسجيل الدخول - EduTeam Hope School</title>
    <style>
        body { font-family: Tahoma, sans-serif; background: #f0f2f5; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
        .login-card { background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); width: 340px; text-align: center; }
        input, select { width: 100%; padding: 10px; margin: 10px 0; border: 1px solid #ddd; border-radius: 6px; box-sizing: border-box; }
        button { background: #4f46e5; color: white; border: none; padding: 10px; width: 100%; border-radius: 6px; cursor: pointer; font-size: 16px; }
        button:hover { background: #4338ca; }
        .error { color: red; font-size: 14px; margin-bottom: 10px; }
    </style>
    </head>
    <body>
        <div class="login-card">
            <h2>🏫 EduTeam Hope School</h2>
            {% if error %}<div class="error">{{ error }}</div>{% endif %}
            <form method="POST">
                <select name="username" required>
                    <option value="">--- اختر اسم المستخدم ---</option>
                    <optgroup label="الإدارة والإرشاد">
                        <option value="المدير: خضر">المدير: خضر</option>
                        <option value="السكرتيرة: بريتا">السكرتيرة: بريتا</option>
                        <option value="المرشد الاجتماعي: فؤاد">المرشد الاجتماعي: فؤاد</option>
                    </optgroup>
                    <optgroup label="المربون">
                        <option value="نزار">نزار</option>
                        <option value="مايك">مايك</option>
                        <option value="احمد">احمد</option>
                        <option value="سابا">سابا</option>
                        <option value="اندريس">اندريس</option>
                        <option value="وليد">وليد</option>
                    </optgroup>
                    <optgroup label="المربيات">
                        <option value="ليلى">ليلى</option>
                        <option value="لانا">لانا</option>
                        <option value="نقول">نقول</option>
                        <option value="ايفا">ايفا</option>
                        <option value="لورد">لورد</option>
                        <option value="نوها">نوها</option>
                        <option value="منال">منال</option>
                        <option value="خيلاء">خيلاء</option>
                        <option value="دعاء">دعاء</option>
                        <option value="سلستي">سلستي</option>
                        <option value="نور">نور</option>
                        <option value="رزان">رزان</option>
                        <option value="داليا">داليا</option>
                        <option value="هايدي">هايدي</option>
                        <option value="نانسي">نانسي</option>
                        <option value="ميري">ميري</option>
                        <option value="ريتا">ريتا</option>
                        <option value="ابتسام">ابتسام</option>
                    </optgroup>
                </select>
                <input type="password" name="password" placeholder="كلمة المرور (الافتراضية 0000)" required>
                <button type="submit">دخول</button>
            </form>
        </div>
    </body>
    </html>
    '''
    return render_template_string(html, error=error)

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    user = session['user']
    role = session['role']
    real_name = session.get('real_name', user.split(':')[-1].strip())
    success_msg = None

    # تعديل جدول الصفوف العليا
    if request.method == 'POST' and 'update_upper' in request.form:
        if role in ['سكرتيرة', 'مدير']:
            day = request.form.get('day')
            loc = request.form.get('location')
            teacher = request.form.get('teacher')
            if day not in DB['schedule_upper']:
                DB['schedule_upper'][day] = {}
            DB['schedule_upper'][day][loc] = teacher
            save_db(DB)
            success_msg = 'تم حفظ وتحديث جدول الصفوف العليا بنجاح!'

    # تعديل جدول الصفوف الدنيا
    if request.method == 'POST' and 'update_lower' in request.form:
        if role in ['سكرتيرة', 'مدير']:
            day = request.form.get('day')
            loc = request.form.get('location')
            teacher = request.form.get('teacher')
            if day not in DB['schedule_lower']:
                DB['schedule_lower'][day] = {}
            DB['schedule_lower'][day][loc] = teacher
            save_db(DB)
            success_msg = 'تم حفظ وتحديث جدول الصفوف الدنيا بنجاح!'

    # تغيير كلمة السر
    if request.method == 'POST' and 'change_password' in request.form:
        old_p = request.form.get('old_password')
        new_p = request.form.get('new_password')
        if DB['users'][user]['pass'] == old_p and new_p:
            DB['users'][user]['pass'] = new_p
            save_db(DB)
            success_msg = 'تم تغيير كلمة المرور بنجاح!'
        else:
            success_msg = 'خطأ: كلمة المرور القديمة غير صحيحة!'

    # إرسال رسائل المدير
    if request.method == 'POST' and 'send_message' in request.form:
        if role == 'مدير':
            receivers = request.form.getlist('receivers')
            text = request.form.get('text')
            if 'الكل' in receivers:
                receivers = [u for u in DB['users'].keys() if u != user]
            else:
                receivers = [r for r in receivers if r != user]
                
            if receivers and text:
                DB['messages'].append({'sender': user, 'receivers': receivers, 'text': text})
                save_db(DB)
                success_msg = 'تم إرسال الرسالة بنجاح!'

    user_messages = [m for m in DB['messages'] if user in m['receivers'] or m['sender'] == user]
    teacher_list = ['نزار', 'مايك', 'احمد', 'سابا', 'اندريس', 'وليد', 'ليلى', 'لانا', 'نقول', 'ايفا', 'لورد', 'نوها', 'منال', 'خيلاء', 'دعاء', 'سلستي', 'نور', 'رزان', 'داليا', 'هايدي', 'نانسي', 'ميري', 'ريتا', 'ابتسام']

    html = '''
    <!DOCTYPE html>
    <html lang="ar" dir="rtl">
    <head><meta charset="UTF-8"><title>لوحة التحكم - EduTeam Hope School</title>
    <style>
        body { font-family: Tahoma, sans-serif; background: #f8fafc; margin: 0; padding: 20px; color: #334155; }
        .container { max-width: 950px; margin: auto; background: white; padding: 25px; border-radius: 12px; box-shadow: 0 2px 10px rgba(0,0,0,0.05); }
        h1, h2, h3 { color: #1e293b; }
        .header { display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #e2e8f0; padding-bottom: 15px; margin-bottom: 20px; }
        .logout-btn { background: #ef4444; color: white; padding: 8px 15px; border-radius: 6px; text-decoration: none; }
        table { width: 100%; border-collapse: collapse; margin-top: 15px; margin-bottom: 25px; }
        th, td { border: 1px solid #cbd5e1; padding: 10px; text-align: center; }
        th { background: #f1f5f9; }
        .alert { background: #dcfce7; color: #166534; padding: 10px; border-radius: 6px; margin-bottom: 15px; font-weight: bold; }
        form { background: #f8fafc; padding: 15px; border-radius: 8px; margin-top: 15px; border: 1px solid #e2e8f0; }
        input, select, textarea { width: 100%; padding: 8px; margin: 5px 0 12px 0; border: 1px solid #cbd5e1; border-radius: 4px; box-sizing: border-box; }
        button { background: #2563eb; color: white; border: none; padding: 10px 20px; border-radius: 6px; cursor: pointer; font-weight: bold; }
        button:hover { background: #1d4ed8; }
        .save-btn { background: #10b981; }
        .save-btn:hover { background: #059669; }
        .edit-inline-btn { background: #10b981; color: white; border: none; padding: 4px 8px; font-size: 12px; border-radius: 4px; cursor: pointer; margin-top: 5px; }
        .msg-box { background: #eff6ff; border-right: 4px solid #3b82f6; padding: 10px; margin: 10px 0; border-radius: 4px; }
    </style>
    <script>
        function enableEditUpper(day, loc, currentTeacher) {
            document.getElementById('upper_day').value = day;
            document.getElementById('upper_loc').value = loc;
            document.getElementById('upper_teacher').value = currentTeacher;
            window.scrollTo({top: document.getElementById('upper-section').offsetTop, behavior: 'smooth'});
        }
        function enableEditLower(day, loc, currentTeacher) {
            document.getElementById('lower_day').value = day;
            document.getElementById('lower_loc').value = loc;
            document.getElementById('lower_teacher').value = currentTeacher;
            window.scrollTo({top: document.getElementById('lower-section').offsetTop, behavior: 'smooth'});
        }
    </script>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🏫 مدرسة الأمل - EduTeam</h1>
                <div>
                    <span>مرحباً، <b>{{ user }}</b></span> | 
                    <a href="{{ url_for('logout') }}" class="logout-btn">تسجيل خروج</a>
                </div>
            </div>

            {% if success_msg %}<div class="alert">{{ success_msg }}</div>{% endif %}

            {% if role in ['سكرتيرة', 'مدير'] %}
            <!-- 1. جدول الصفوف العليا -->
            <h2>📋 جدول المراقبة ديوتي - الصفوف العليا</h2>
            <table>
                <tr>
                    <th>اليوم / الموقع</th>
                    {% for loc in locations %}<th>{{ loc }}</th>{% endfor %}
                </tr>
                {% for day in days %}
                <tr>
                    <td><b>{{ day }}</b></td>
                    {% for loc in locations %}
                    <td>
                        {% set current_t = schedule_upper.get(day, {}).get(loc, '-') %}
                        {{ current_t }}
                        <br>
                        <button type="button" class="edit-inline-btn" onclick="enableEditUpper('{{ day }}', '{{ loc }}', '{{ current_t if current_t != '-' else teacher_list[0] }}')">تعديل ✏️</button>
                    </td>
                    {% endfor %}
                </tr>
                {% endfor %}
            </table>

            <form method="POST" id="upper-section">
                <h3>✏️ تعديل جدول الصفوف العليا</h3>
                <input type="hidden" name="update_upper" value="1">
                <label>اليوم:</label>
                <select name="day" id="upper_day" required>{% for d in days %}<option value="{{ d }}">{{ d }}</option>{% endfor %}</select>
                <label>الموقع:</label>
                <select name="location" id="upper_loc" required>{% for l in locations %}<option value="{{ l }}">{{ l }}</option>{% endfor %}</select>
                <label>المعلم / المربي:</label>
                <select name="teacher" id="upper_teacher" required>{% for t in teacher_list %}<option value="{{ t }}">{{ t }}</option>{% endfor %}</select>
                <button type="submit" class="save-btn">💾 حفظ التعديل (صفوف عليا)</button>
            </form>

            <hr style="margin: 30px 0; border: 0; border-top: 1px solid #cbd5e1;">

            <!-- 2. جدول الصفوف الدنيا -->
            <h2>📋 جدول المراقبة ديوتي - الصفوف الدنيا</h2>
            <table>
                <tr>
                    <th>اليوم / الموقع</th>
                    {% for loc in locations %}<th>{{ loc }}</th>{% endfor %}
                </tr>
                {% for day in days %}
                <tr>
                    <td><b>{{ day }}</b></td>
                    {% for loc in locations %}
                    <td>
                        {% set current_t = schedule_lower.get(day, {}).get(loc, '-') %}
                        {{ current_t }}
                        <br>
                        <button type="button" class="edit-inline-btn" onclick="enableEditLower('{{ day }}', '{{ loc }}', '{{ current_t if current_t != '-' else teacher_list[0] }}')">تعديل ✏️</button>
                    </td>
                    {% endfor %}
                </tr>
                {% endfor %}
            </table>

            <form method="POST" id="lower-section">
                <h3>✏️ تعديل جدول الصفوف الدنيا</h3>
                <input type="hidden" name="update_lower" value="1">
                <label>اليوم:</label>
                <select name="day" id="lower_day" required>{% for d in days %}<option value="{{ d }}">{{ d }}</option>{% endfor %}</select>
                <label>الموقع:</label>
                <select name="location" id="lower_loc" required>{% for l in locations %}<option value="{{ l }}">{{ l }}</option>{% endfor %}</select>
                <label>المعلم / المربي:</label>
                <select name="teacher" id="lower_teacher" required>{% for t in teacher_list %}<option value="{{ t }}">{{ t }}</option>{% endfor %}</select>
                <button type="submit" class="save-btn">💾 حفظ التعديل (صفوف دنيا)</button>
            </form>

            {% else %}
            <!-- جدول المعلم العادي -->
            <h2>📅 جداول المناوبة الخاصة بي (المعلم: {{ real_name }})</h2>
            
            <h3>الصفوف العليا:</h3>
            <table>
                <tr><th>اليوم</th><th>الموقع</th></tr>
                {% for day in days %}
                <tr>
                    <td><b>{{ day }}</b></td>
                    <td>
                        {% set found = [] %}
                        {% for loc in locations %}{% if schedule_upper.get(day, {}).get(loc) == real_name %}{% set _ = found.append(loc) %}{% endif %}{% endfor %}
                        {{ found | join(' و ') if found else '<span style="color:#94a3b8">لا توجد مناوبة</span>' | safe }}
                    </td>
                </tr>
                {% endfor %}
            </table>

            <h3>الصفوف الدنيا:</h3>
            <table>
                <tr><th>اليوم</th><th>الموقع</th></tr>
                {% for day in days %}
                <tr>
                    <td><b>{{ day }}</b></td>
                    <td>
                        {% set found = [] %}
                        {% for loc in locations %}{% if schedule_lower.get(day, {}).get(loc) == real_name %}{% set _ = found.append(loc) %}{% endif %}{% endfor %}
                        {{ found | join(' و ') if found else '<span style="color:#94a3b8">لا توجد مناوبة</span>' | safe }}
                    </td>
                </tr>
                {% endfor %}
            </table>
            {% endif %}

            <!-- تغيير كلمة السر -->
            <form method="POST">
                <h3>🔑 تغيير كلمة المرور الشخصية</h3>
                <input type="hidden" name="change_password" value="1">
                <label>كلمة المرور القديمة:</label>
                <input type="password" name="old_password" required placeholder="أدخل كلمة المرور الحالية">
                <label>كلمة المرور الجديدة:</label>
                <input type="password" name="new_password" required placeholder="أدخل كلمة المرور الجديدة">
                <button type="submit">تحديث كلمة المرور</button>
            </form>

            <!-- المراسلة للمدير -->
            {% if role == 'مدير' %}
            <form method="POST">
                <h3>📨 لوحة رسائل المدير (خضر)</h3>
                <input type="hidden" name="send_message" value="1">
                <label>إرسال إلى:</label>
                <select name="receivers" multiple style="height: 120px;" required>
                    <option value="الكل">--- إرسال للجميع (ما عدا المدير) ---</option>
                    {% for u in users %}{% if u != user %}<option value="{{ u }}">{{ u }}</option>{% endif %}{% endfor %}
                </select>
                <label>نص الرسالة:</label>
                <textarea name="text" rows="3" required placeholder="اكتب رسالتك هنا..."></textarea>
                <button type="submit">إرسال الرسالة</button>
            </form>
            {% endif %}

            <h2>📥 الرسائل الواردة</h2>
            {% if user_messages %}
                {% for m in user_messages %}
                <div class="msg-box">
                    <b>من: {{ m.sender }}</b> | <b>المستلمون: {{ m.receivers | join(', ') }}</b>
                    <p>{{ m.text }}</p>
                </div>
                {% endfor %}
            {% else %}
                <p>لا توجد رسائل حالياً.</p>
            {% endif %}
        </div>
    </body>
    </html>
    '''
    return render_template_string(html, user=user, role=role, real_name=real_name, days=DAYS, locations=LOCATIONS, schedule_upper=DB['schedule_upper'], schedule_lower=DB['schedule_lower'], users=DB['users'], teacher_list=teacher_list, user_messages=user_messages, success_msg=success_msg)

@app.route('/logout')
def logout():
    session.clear()
    resp = make_response(redirect(url_for('login')))
    resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    return resp

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
