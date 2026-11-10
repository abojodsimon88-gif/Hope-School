import hmac
import json
import os
import secrets
import time
from datetime import timedelta

import pymysql
from pymysql.cursors import DictCursor
from flask import (
    Flask, render_template_string, request, redirect, url_for, session,
    make_response, abort,
)
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.security import generate_password_hash, check_password_hash

# ----------------------------------------------------------------------
# الإعدادات
# ----------------------------------------------------------------------
app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

ON_RENDER = bool(os.environ.get("RENDER"))

_secret = os.environ.get("SECRET_KEY")
if not _secret:
    if ON_RENDER:
        raise RuntimeError("يجب ضبط متغير البيئة SECRET_KEY على Render.")
    _secret = secrets.token_hex(32)
app.secret_key = _secret

app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=ON_RENDER,
    PERMANENT_SESSION_LIFETIME=timedelta(hours=8),
    MAX_CONTENT_LENGTH=256 * 1024,
)

_missing = [n for n in ("DB_HOST", "DB_NAME", "DB_USER", "DB_PASSWORD") if not os.environ.get(n)]
if _missing:
    raise RuntimeError("متغيرات البيئة التالية ناقصة: " + ", ".join(_missing))

DB_CONFIG = dict(
    host=os.environ["DB_HOST"],
    user=os.environ["DB_USER"],
    password=os.environ["DB_PASSWORD"],
    database=os.environ["DB_NAME"],
    port=int(os.environ.get("DB_PORT", "3306")),
    charset="utf8mb4",
    cursorclass=DictCursor,
    connect_timeout=10,
    autocommit=False,
)

DEFAULT_PASSWORD = "0000"   # كلمة المرور الأولى، ويُجبر المستخدم على تغييرها
MIN_PASSWORD_LEN = 8
MAX_FAILS = 5
FAIL_WINDOW = 15 * 60

DAYS = ['السبت', 'الاثنين', 'الثلاثاء', 'الأربعاء', 'الخميس']
LOCATIONS = ['الباب الرئيسي', 'الساحة الأولى', 'الساحة الثانية', 'باب الدرج']

# (اسم الدخول، الدور، الاسم الحقيقي)
USER_LIST = [
    ('المدير: خضر', 'مدير', 'خضر'),
    ('السكرتيرة: بريتا', 'سكرتيرة', 'بريتا'),
    ('المرشد الاجتماعي: فؤاد', 'مرشد', 'فؤاد'),
    ('نزار', 'معلم', 'نزار'),
    ('مايك', 'معلم', 'مايك'),
    ('احمد', 'معلم', 'احمد'),
    ('سابا', 'معلم', 'سابا'),
    ('اندريس', 'معلم', 'اندريس'),
    ('وليد', 'معلم', 'وليد'),
    ('ليلى', 'معلمة', 'ليلى'),
    ('لانا', 'معلمة', 'لانا'),
    ('نقول', 'معلمة', 'نقول'),
    ('ايفا', 'معلمة', 'ايفا'),
    ('لورد', 'معلمة', 'لورد'),
    ('نوها', 'معلمة', 'نوها'),
    ('منال', 'معلمة', 'منال'),
    ('خيلاء', 'معلمة', 'خيلاء'),
    ('دعاء', 'معلمة', 'دعاء'),
    ('سلستي', 'معلمة', 'سلستي'),
    ('نور', 'معلمة', 'نور'),
    ('رزان', 'معلمة', 'رزان'),
    ('داليا', 'معلمة', 'داليا'),
    ('هايدي', 'معلمة', 'هايدي'),
    ('نانسي', 'معلمة', 'نانسي'),
    ('ميري', 'معلمة', 'ميري'),
    ('ريتا', 'معلمة', 'ريتا'),
    ('ابتسام', 'معلمة', 'ابتسام'),
]

TEACHER_LIST = [key for _name, role, key in USER_LIST if role in ('معلم', 'معلمة')]

LOGIN_GROUPS = [
    ('الإدارة والإرشاد', [n for n, r, _k in USER_LIST if r in ('مدير', 'سكرتيرة', 'مرشد')]),
    ('المربون', [n for n, r, _k in USER_LIST if r == 'معلم']),
    ('المربيات', [n for n, r, _k in USER_LIST if r == 'معلمة']),
]


# ----------------------------------------------------------------------
# التخزين الدائم في MySQL (صف واحد يحمل كل بيانات التطبيق بصيغة JSON)
# ----------------------------------------------------------------------
def _connect():
    return pymysql.connect(**DB_CONFIG)


def _execute(sql, params=(), fetch=None):
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            result = cur.fetchone() if fetch == "one" else None
        conn.commit()
        return result
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_default_db():
    users = {}
    admin_pw = os.environ.get("ADMIN_INITIAL_PASSWORD")
    for name, role, key in USER_LIST:
        pw_hash = ''   # فارغ = لم يغيّر كلمة المرور الأولى بعد
        if role == 'مدير' and admin_pw:
            pw_hash = generate_password_hash(admin_pw)
        users[name] = {'pass': pw_hash, 'role': role, 'key': key, 'must_change': True}
    return {
        'users': users,
        'schedule_upper': {},   # جدول الصفوف العليا
        'schedule_lower': {},   # جدول الصفوف الدنيا
        'messages': [],
    }


def init_db():
    _execute(
        "CREATE TABLE IF NOT EXISTS app_state ("
        "id INT NOT NULL PRIMARY KEY,"
        "data LONGTEXT NOT NULL"
        ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4"
    )
    row = _execute("SELECT id FROM app_state WHERE id = 1", fetch="one")
    if row is None:
        _execute(
            "INSERT IGNORE INTO app_state (id, data) VALUES (1, %s)",
            (json.dumps(get_default_db(), ensure_ascii=False),),
        )


def load_db():
    row = _execute("SELECT data FROM app_state WHERE id = 1", fetch="one")
    if row is None:
        init_db()
        row = _execute("SELECT data FROM app_state WHERE id = 1", fetch="one")
    data = json.loads(row["data"])
    data.setdefault('users', {})
    data.setdefault('schedule_upper', {})
    data.setdefault('schedule_lower', {})
    data.setdefault('messages', [])
    return data


def save_db(data):
    _execute(
        "INSERT INTO app_state (id, data) VALUES (1, %s) "
        "ON DUPLICATE KEY UPDATE data = VALUES(data)",
        (json.dumps(data, ensure_ascii=False),),
    )


# ----------------------------------------------------------------------
# الأمان: كلمات المرور، تحديد المحاولات، CSRF
# ----------------------------------------------------------------------
def check_login(user, password):
    stored = user.get('pass') or ''
    if not stored:
        return hmac.compare_digest(password.encode(), DEFAULT_PASSWORD.encode())
    try:
        return check_password_hash(stored, password)
    except ValueError:
        return False


FAILS = {}


def too_many(ident):
    now = time.time()
    recent = [t for t in FAILS.get(ident, []) if now - t < FAIL_WINDOW]
    FAILS[ident] = recent
    return len(recent) >= MAX_FAILS


def record_fail(ident):
    if len(FAILS) > 5000:
        FAILS.clear()
    FAILS.setdefault(ident, []).append(time.time())


def clear_fails(ident):
    FAILS.pop(ident, None)


def csrf_token():
    if 'csrf' not in session:
        session['csrf'] = secrets.token_hex(16)
    return session['csrf']


app.jinja_env.globals['csrf_token'] = csrf_token


@app.before_request
def csrf_protect():
    if request.method == 'POST':
        sent = (request.form.get('csrf') or '').encode()
        expected = (session.get('csrf') or '').encode()
        if not expected or not hmac.compare_digest(sent, expected):
            abort(400)


@app.after_request
def add_security_headers(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Referrer-Policy'] = 'same-origin'
    if ON_RENDER:
        response.headers['Strict-Transport-Security'] = 'max-age=31536000'
    return response


@app.errorhandler(400)
def bad_request(_e):
    return 'طلب غير صالح. أعد تحميل الصفحة وحاول مرة أخرى.', 400


@app.errorhandler(403)
def forbidden(_e):
    return 'ليس لديك صلاحية لهذه العملية.', 403


def client_ip():
    return (request.remote_addr or 'unknown')[:45]


def flash_msg(text, ok=True):
    session['flash'] = ['ok' if ok else 'error', text]


def current():
    """يرجع (قاعدة البيانات، سجل المستخدم الحالي) أو (None, None)."""
    username = session.get('user')
    if not username:
        return None, None
    db = load_db()
    me = db['users'].get(username)
    if me is None:
        session.clear()
        return None, None
    return db, me


# ----------------------------------------------------------------------
# القوالب
# ----------------------------------------------------------------------
LOGIN_HTML = '''
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>تسجيل الدخول - EduTeam Hope School</title>
<style>
    body { font-family: Tahoma, sans-serif; background: #f0f2f5; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; }
    .login-card { background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); width: 340px; max-width: 90%; text-align: center; }
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
            <input type="hidden" name="csrf" value="{{ csrf_token() }}">
            <select name="username" required>
                <option value="">--- اختر اسم المستخدم ---</option>
                {% for label, names in groups %}
                <optgroup label="{{ label }}">
                    {% for n in names %}<option value="{{ n }}">{{ n }}</option>{% endfor %}
                </optgroup>
                {% endfor %}
            </select>
            <input type="password" name="password" placeholder="كلمة المرور" required>
            <button type="submit">دخول</button>
        </form>
    </div>
</body>
</html>
'''

CHANGE_PW_HTML = '''
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>تغيير كلمة المرور - EduTeam Hope School</title>
<style>
    body { font-family: Tahoma, sans-serif; background: #f0f2f5; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; }
    .card { background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); width: 360px; max-width: 90%; }
    input { width: 100%; padding: 10px; margin: 5px 0 12px 0; border: 1px solid #ddd; border-radius: 6px; box-sizing: border-box; }
    button { background: #10b981; color: white; border: none; padding: 10px; width: 100%; border-radius: 6px; cursor: pointer; font-size: 16px; }
    .error { background: #fee2e2; color: #991b1b; padding: 10px; border-radius: 6px; margin-bottom: 10px; }
    .notice { background: #fef9c3; color: #854d0e; padding: 10px; border-radius: 6px; margin-bottom: 10px; }
    a { color: #2563eb; }
</style>
</head>
<body>
    <div class="card">
        <h2>🔑 تغيير كلمة المرور</h2>
        {% if forced %}<div class="notice">يجب تغيير كلمة المرور الأولى قبل المتابعة.</div>{% endif %}
        {% if error %}<div class="error">{{ error }}</div>{% endif %}
        <form method="POST">
            <input type="hidden" name="csrf" value="{{ csrf_token() }}">
            <label>كلمة المرور الحالية:</label>
            <input type="password" name="old_password" required>
            <label>كلمة المرور الجديدة (8 أحرف على الأقل):</label>
            <input type="password" name="new_password" required minlength="8">
            <label>تأكيد كلمة المرور الجديدة:</label>
            <input type="password" name="confirm_password" required minlength="8">
            <button type="submit">حفظ</button>
        </form>
        <p>
            {% if not forced %}<a href="{{ url_for('dashboard') }}">العودة للوحة التحكم</a> | {% endif %}
            <a href="{{ url_for('logout') }}">تسجيل خروج</a>
        </p>
    </div>
</body>
</html>
'''

DASHBOARD_HTML = '''
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>لوحة التحكم - EduTeam Hope School</title>
<style>
    body { font-family: Tahoma, sans-serif; background: #f8fafc; margin: 0; padding: 20px; color: #334155; }
    .container { max-width: 950px; margin: auto; background: white; padding: 25px; border-radius: 12px; box-shadow: 0 2px 10px rgba(0,0,0,0.05); }
    h1, h2, h3 { color: #1e293b; }
    .header { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px; border-bottom: 2px solid #e2e8f0; padding-bottom: 15px; margin-bottom: 20px; }
    .logout-btn { background: #ef4444; color: white; padding: 8px 15px; border-radius: 6px; text-decoration: none; }
    .pw-btn { background: #f59e0b; color: white; padding: 8px 15px; border-radius: 6px; text-decoration: none; }
    .tablewrap { overflow-x: auto; }
    table { width: 100%; border-collapse: collapse; margin-top: 15px; margin-bottom: 25px; }
    th, td { border: 1px solid #cbd5e1; padding: 10px; text-align: center; }
    th { background: #f1f5f9; }
    .alert { background: #dcfce7; color: #166534; padding: 10px; border-radius: 6px; margin-bottom: 15px; font-weight: bold; }
    .alert.err { background: #fee2e2; color: #991b1b; }
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
                <a href="{{ url_for('change_password') }}" class="pw-btn">🔑 كلمة المرور</a>
                <a href="{{ url_for('logout') }}" class="logout-btn">تسجيل خروج</a>
            </div>
        </div>

        {% if flash %}<div class="alert {{ 'err' if flash[0] == 'error' else '' }}">{{ flash[1] }}</div>{% endif %}

        {% if role in ['سكرتيرة', 'مدير'] %}
        <!-- 1. جدول الصفوف العليا -->
        <h2>📋 جدول المراقبة ديوتي - الصفوف العليا</h2>
        <div class="tablewrap">
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
        </div>

        <form method="POST" id="upper-section">
            <input type="hidden" name="csrf" value="{{ csrf_token() }}">
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
        <div class="tablewrap">
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
        </div>

        <form method="POST" id="lower-section">
            <input type="hidden" name="csrf" value="{{ csrf_token() }}">
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

        <!-- المراسلة للمدير -->
        {% if role == 'مدير' %}
        <form method="POST">
            <input type="hidden" name="csrf" value="{{ csrf_token() }}">
            <h3>📨 لوحة رسائل المدير (خضر)</h3>
            <input type="hidden" name="send_message" value="1">
            <label>إرسال إلى:</label>
            <select name="receivers" multiple style="height: 120px;" required>
                <option value="الكل">--- إرسال للجميع (ما عدا المدير) ---</option>
                {% for u in users %}{% if u != user %}<option value="{{ u }}">{{ u }}</option>{% endif %}{% endfor %}
            </select>
            <label>نص الرسالة:</label>
            <textarea name="text" rows="3" maxlength="2000" required placeholder="اكتب رسالتك هنا..."></textarea>
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


# ----------------------------------------------------------------------
# المسارات
# ----------------------------------------------------------------------
@app.route('/')
def index():
    if 'user' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = (request.form.get('username') or '')[:100]
        password = (request.form.get('password') or '')[:128]
        ident = client_ip() + '|' + username

        if too_many(ident):
            error = 'محاولات كثيرة خاطئة. انتظر 15 دقيقة ثم حاول مرة أخرى.'
        else:
            db = load_db()
            user = db['users'].get(username)
            if user is not None and check_login(user, password):
                clear_fails(ident)
                session.clear()
                session.permanent = True
                session['user'] = username
                return redirect(url_for('dashboard'))
            record_fail(ident)
            error = 'اسم المستخدم أو كلمة المرور غير صحيحة'

    return render_template_string(LOGIN_HTML, error=error, groups=LOGIN_GROUPS)


@app.route('/change_password', methods=['GET', 'POST'])
def change_password():
    db, me = current()
    if me is None:
        return redirect(url_for('login'))
    username = session['user']
    error = None

    if request.method == 'POST':
        old_p = (request.form.get('old_password') or '')[:128]
        new_p = (request.form.get('new_password') or '')[:128]
        confirm = (request.form.get('confirm_password') or '')[:128]
        ident = 'chpw|' + username

        if too_many(ident):
            error = 'محاولات كثيرة خاطئة. انتظر 15 دقيقة.'
        elif not check_login(me, old_p):
            record_fail(ident)
            error = 'كلمة المرور الحالية غير صحيحة.'
        elif len(new_p) < MIN_PASSWORD_LEN:
            error = 'كلمة المرور الجديدة يجب ألا تقل عن %d أحرف.' % MIN_PASSWORD_LEN
        elif new_p != confirm:
            error = 'تأكيد كلمة المرور غير مطابق.'
        elif new_p == old_p or new_p == DEFAULT_PASSWORD:
            error = 'اختر كلمة مرور مختلفة وغير الافتراضية.'
        else:
            me['pass'] = generate_password_hash(new_p)
            me['must_change'] = False
            save_db(db)
            clear_fails(ident)
            flash_msg('تم تغيير كلمة المرور بنجاح!')
            return redirect(url_for('dashboard'))

    return render_template_string(
        CHANGE_PW_HTML, error=error, forced=bool(me.get('must_change'))
    )


@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    db, me = current()
    if me is None:
        return redirect(url_for('login'))
    if me.get('must_change'):
        return redirect(url_for('change_password'))

    user = session['user']
    role = me['role']
    real_name = me['key']

    if request.method == 'POST':
        form = request.form
        if 'update_upper' in form or 'update_lower' in form:
            if role not in ('سكرتيرة', 'مدير'):
                abort(403)
            if 'update_upper' in form:
                table, label = 'schedule_upper', 'العليا'
            else:
                table, label = 'schedule_lower', 'الدنيا'
            day = form.get('day')
            loc = form.get('location')
            teacher = form.get('teacher')
            if day in DAYS and loc in LOCATIONS and teacher in TEACHER_LIST:
                db[table].setdefault(day, {})[loc] = teacher
                save_db(db)
                flash_msg('تم حفظ وتحديث جدول الصفوف ' + label + ' بنجاح!')
            else:
                flash_msg('بيانات غير صالحة.', ok=False)

        elif 'send_message' in form:
            if role != 'مدير':
                abort(403)
            chosen = form.getlist('receivers')
            text = (form.get('text') or '').strip()[:2000]
            if 'الكل' in chosen:
                receivers = [u for u in db['users'] if u != user]
            else:
                receivers = [r for r in chosen if r in db['users'] and r != user]
            if receivers and text:
                db['messages'].append({'sender': user, 'receivers': receivers, 'text': text})
                save_db(db)
                flash_msg('تم إرسال الرسالة بنجاح!')
            else:
                flash_msg('اختر مستلماً واكتب نص الرسالة.', ok=False)
        return redirect(url_for('dashboard'))

    flash = session.pop('flash', None)
    user_messages = [
        m for m in db['messages'] if user in m['receivers'] or m['sender'] == user
    ]
    return render_template_string(
        DASHBOARD_HTML,
        user=user, role=role, real_name=real_name, days=DAYS, locations=LOCATIONS,
        schedule_upper=db['schedule_upper'], schedule_lower=db['schedule_lower'],
        users=db['users'], teacher_list=TEACHER_LIST, user_messages=user_messages,
        flash=flash,
    )


@app.route('/logout')
def logout():
    session.clear()
    resp = make_response(redirect(url_for('login')))
    resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    return resp


init_db()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
