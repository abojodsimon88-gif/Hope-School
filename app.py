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
TEMP_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZabcdefghjkmnpqrstuvwxyz23456789"

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


def new_temp_password():
    return ''.join(secrets.choice(TEMP_ALPHABET) for _ in range(8))


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


def clear_fails_for_user(username):
    """يفك القفل عن مستخدم (من كل العناوين) بعد إعادة تعيين كلمة مروره."""
    suffix = '|' + username
    for key in [k for k in FAILS if k.endswith(suffix)]:
        FAILS.pop(key, None)


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


def require_admin():
    """يرجع (db, me, None) للمدير، أو (None, None, استجابة) لغيره."""
    db, me = current()
    if me is None:
        return None, None, redirect(url_for('login'))
    if me.get('must_change'):
        return None, None, redirect(url_for('change_password'))
    if me['role'] != 'مدير':
        abort(403)
    return db, me, None


# ----------------------------------------------------------------------
# التصميم
# ----------------------------------------------------------------------
BASE_CSS = '''
:root { --bg:#f1f5f9; --card:#fff; --ink:#0f172a; --muted:#64748b; --line:#e2e8f0;
        --brand:#4f46e5; --brand2:#7c3aed; --ok:#16a34a; --warn:#f59e0b; --bad:#dc2626; }
* { box-sizing: border-box; }
body { font-family: Tahoma, Arial, sans-serif; background: var(--bg); color: var(--ink); margin: 0; }
a { color: var(--brand); }
.topbar { background: linear-gradient(135deg, var(--brand), var(--brand2)); color: #fff; padding: 16px 18px; }
.topbar-in { max-width: 1000px; margin: auto; display: flex; justify-content: space-between;
             align-items: center; flex-wrap: wrap; gap: 12px; }
.brand { font-size: 20px; font-weight: bold; }
.who { font-size: 14px; opacity: .95; margin-top: 4px; }
.nav { display: flex; gap: 8px; flex-wrap: wrap; }
.btn { display: inline-block; border: 0; border-radius: 10px; padding: 9px 14px; font-size: 14px;
       font-weight: bold; cursor: pointer; text-decoration: none; color: #fff; background: var(--brand); }
.btn:hover { filter: brightness(1.08); }
.btn.light { background: rgba(255,255,255,.2); }
.btn.ok { background: var(--ok); } .btn.warn { background: var(--warn); color: #1f2937; }
.btn.bad { background: var(--bad); }
.btn.small { padding: 5px 10px; font-size: 12px; border-radius: 8px; }
.wrap { max-width: 1000px; margin: 20px auto; padding: 0 14px 40px; }
.card { background: var(--card); border: 1px solid var(--line); border-radius: 16px; padding: 20px;
        margin-bottom: 18px; box-shadow: 0 2px 12px rgba(15,23,42,.05); }
.card h2 { margin: 0 0 14px; font-size: 18px; }
.card h3 { margin: 0 0 10px; font-size: 16px; }
.notice { padding: 12px 14px; border-radius: 12px; margin-bottom: 16px; font-weight: bold; }
.notice.ok { background: #dcfce7; color: #166534; }
.notice.err { background: #fee2e2; color: #991b1b; }
.notice.info { background: #fef9c3; color: #854d0e; }
.tablewrap { overflow-x: auto; }
table { width: 100%; border-collapse: separate; border-spacing: 0; min-width: 560px; }
th { background: #eef2ff; color: #3730a3; padding: 10px; font-size: 14px; border-bottom: 2px solid #c7d2fe; }
td { padding: 10px; text-align: center; border-bottom: 1px solid var(--line); font-size: 14px; }
tr:last-child td { border-bottom: 0; }
td.dayname { font-weight: bold; background: #f8fafc; }
.chip { display: inline-block; background: #e0e7ff; color: #3730a3; padding: 3px 10px; border-radius: 999px;
        font-weight: bold; font-size: 13px; }
.empty { color: #cbd5e1; }
.tag { display: inline-block; background: #e0e7ff; color: #3730a3; border-radius: 6px; padding: 2px 8px;
       font-size: 12px; font-weight: bold; margin-left: 6px; }
.tag.low { background: #ccfbf1; color: #115e59; }
.muted { color: var(--muted); }
.days { display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); gap: 12px; }
.day { border: 1px solid var(--line); border-radius: 14px; padding: 14px; background: #f8fafc; }
.day.busy { background: #eef2ff; border-color: #c7d2fe; }
.day-name { font-weight: bold; margin-bottom: 8px; font-size: 16px; }
.line { margin: 6px 0; font-size: 14px; }
form.box { background: #f8fafc; border: 1px solid var(--line); border-radius: 14px; padding: 16px; margin-top: 14px; }
label { display: block; font-size: 14px; color: var(--muted); margin-bottom: 2px; }
input, select, textarea { width: 100%; padding: 10px; margin: 4px 0 12px; border: 1px solid #cbd5e1;
                          border-radius: 10px; font-size: 15px; font-family: inherit; background: #fff; }
.row { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 10px; }
.msg { border-right: 4px solid var(--brand); background: #eef2ff; border-radius: 10px; padding: 10px 12px; margin: 10px 0; }
.msg .meta { font-size: 13px; color: var(--muted); }
.msg p { margin: 6px 0 0; white-space: pre-wrap; }
.temp { direction: ltr; unicode-bidi: plaintext; display: inline-block; font-family: monospace; font-size: 22px;
        background: #fff; border: 2px dashed #16a34a; padding: 4px 14px; border-radius: 10px; letter-spacing: 2px; }
.status-ok { color: var(--ok); font-weight: bold; }
.status-wait { color: #b45309; font-weight: bold; }
.center-page { min-height: 100vh; display: flex; justify-content: center; align-items: center; padding: 16px;
               background: linear-gradient(135deg, #e0e7ff, #f5f3ff); }
.auth-card { background: #fff; padding: 28px; border-radius: 18px; box-shadow: 0 10px 30px rgba(79,70,229,.15);
             width: 380px; max-width: 100%; }
.auth-card h2 { text-align: center; margin-top: 0; }
.auth-card .btn { width: 100%; padding: 12px; font-size: 16px; }
@media (max-width: 600px) { .card { padding: 14px; } .brand { font-size: 17px; } }
'''

LOGIN_HTML = '''
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="theme-color" content="#4f46e5">
<title>تسجيل الدخول - EduTeam Hope School</title>
<style>{{ css|safe }}</style>
</head>
<body>
    <div class="center-page">
        <div class="auth-card">
            <h2>🏫 مدرسة الأمل</h2>
            <p class="muted" style="text-align:center;margin-top:-6px">EduTeam Hope School</p>
            {% if error %}<div class="notice err">{{ error }}</div>{% endif %}
            <form method="POST">
                <input type="hidden" name="csrf" value="{{ csrf_token() }}">
                <label>اسم المستخدم</label>
                <select name="username" required>
                    <option value="">--- اختر اسمك ---</option>
                    {% for label, names in groups %}
                    <optgroup label="{{ label }}">
                        {% for n in names %}<option value="{{ n }}">{{ n }}</option>{% endfor %}
                    </optgroup>
                    {% endfor %}
                </select>
                <label>كلمة المرور</label>
                <input type="password" name="password" required>
                <button type="submit" class="btn">دخول</button>
            </form>
            <p class="muted" style="text-align:center;font-size:13px">نسيت كلمة المرور؟ اطلب من المدير إعادة تعيينها.</p>
        </div>
    </div>
</body>
</html>
'''

CHANGE_PW_HTML = '''
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="theme-color" content="#4f46e5">
<title>تغيير كلمة المرور - EduTeam Hope School</title>
<style>{{ css|safe }}</style>
</head>
<body>
    <div class="center-page">
        <div class="auth-card">
            <h2>🔑 تغيير كلمة المرور</h2>
            {% if forced %}<div class="notice info">يجب تغيير كلمة المرور المؤقتة قبل المتابعة.</div>{% endif %}
            {% if error %}<div class="notice err">{{ error }}</div>{% endif %}
            <form method="POST">
                <input type="hidden" name="csrf" value="{{ csrf_token() }}">
                <label>كلمة المرور الحالية</label>
                <input type="password" name="old_password" required>
                <label>كلمة المرور الجديدة (8 أحرف على الأقل)</label>
                <input type="password" name="new_password" required minlength="8">
                <label>تأكيد كلمة المرور الجديدة</label>
                <input type="password" name="confirm_password" required minlength="8">
                <button type="submit" class="btn ok">حفظ</button>
            </form>
            <p style="text-align:center">
                {% if not forced %}<a href="{{ url_for('dashboard') }}">العودة للوحة التحكم</a> | {% endif %}
                <a href="{{ url_for('logout') }}">تسجيل خروج</a>
            </p>
        </div>
    </div>
</body>
</html>
'''

TOPBAR_HTML = '''
<div class="topbar"><div class="topbar-in">
    <div>
        <div class="brand">🏫 مدرسة الأمل - EduTeam</div>
        <div class="who">مرحباً، <b>{{ user }}</b></div>
    </div>
    <div class="nav">
        <a href="{{ url_for('dashboard') }}" class="btn light">🏠 الرئيسية</a>
        {% if role == 'مدير' %}<a href="{{ url_for('admin_users') }}" class="btn light">👥 المستخدمون</a>{% endif %}
        <a href="{{ url_for('change_password') }}" class="btn light">🔑 كلمة المرور</a>
        <a href="{{ url_for('logout') }}" class="btn light">خروج</a>
    </div>
</div></div>
'''

DASHBOARD_HTML = '''
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="theme-color" content="#4f46e5">
<title>لوحة التحكم - EduTeam Hope School</title>
<style>{{ css|safe }}</style>
<script>
    function enableEdit(prefix, day, loc, currentTeacher) {
        document.getElementById(prefix + '_day').value = day;
        document.getElementById(prefix + '_loc').value = loc;
        document.getElementById(prefix + '_teacher').value = currentTeacher;
        document.getElementById(prefix + '-section').scrollIntoView({behavior: 'smooth', block: 'center'});
    }
</script>
</head>
<body>
''' + TOPBAR_HTML + '''
<div class="wrap">

    {% if flash %}<div class="notice {{ 'err' if flash[0] == 'error' else 'ok' }}">{{ flash[1] }}</div>{% endif %}

    {% if role in ['سكرتيرة', 'مدير'] %}

    {% for prefix, title, schedule in schedules %}
    <div class="card">
        <h2>📋 جدول المراقبة (ديوتي) - {{ title }}</h2>
        <div class="tablewrap">
        <table>
            <tr>
                <th>اليوم</th>
                {% for loc in locations %}<th>{{ loc }}</th>{% endfor %}
            </tr>
            {% for day in days %}
            <tr>
                <td class="dayname">{{ day }}</td>
                {% for loc in locations %}
                <td>
                    {% set current_t = schedule.get(day, {}).get(loc, '-') %}
                    {% if current_t != '-' %}<span class="chip">{{ current_t }}</span>{% else %}<span class="empty">—</span>{% endif %}
                    <br>
                    <button type="button" class="btn small ok" style="margin-top:6px"
                        onclick="enableEdit('{{ prefix }}', '{{ day }}', '{{ loc }}', '{{ current_t if current_t != '-' else teacher_list[0] }}')">تعديل ✏️</button>
                </td>
                {% endfor %}
            </tr>
            {% endfor %}
        </table>
        </div>

        <form method="POST" id="{{ prefix }}-section" class="box">
            <input type="hidden" name="csrf" value="{{ csrf_token() }}">
            <h3>✏️ تعديل جدول {{ title }}</h3>
            <input type="hidden" name="update_{{ prefix }}" value="1">
            <div class="row">
                <div>
                    <label>اليوم</label>
                    <select name="day" id="{{ prefix }}_day" required>{% for d in days %}<option value="{{ d }}">{{ d }}</option>{% endfor %}</select>
                </div>
                <div>
                    <label>الموقع</label>
                    <select name="location" id="{{ prefix }}_loc" required>{% for l in locations %}<option value="{{ l }}">{{ l }}</option>{% endfor %}</select>
                </div>
                <div>
                    <label>المعلم / المربي</label>
                    <select name="teacher" id="{{ prefix }}_teacher" required>{% for t in teacher_list %}<option value="{{ t }}">{{ t }}</option>{% endfor %}</select>
                </div>
            </div>
            <button type="submit" class="btn ok">💾 حفظ التعديل</button>
        </form>
    </div>
    {% endfor %}

    {% else %}

    <div class="card">
        <h2>📅 مناوباتي - {{ real_name }}</h2>
        <div class="days">
        {% for day in days %}
            {% set up = [] %}{% set lo = [] %}
            {% for loc in locations %}
                {% if schedule_upper.get(day, {}).get(loc) == real_name %}{% set _ = up.append(loc) %}{% endif %}
                {% if schedule_lower.get(day, {}).get(loc) == real_name %}{% set _ = lo.append(loc) %}{% endif %}
            {% endfor %}
            <div class="day {{ 'busy' if (up or lo) else '' }}">
                <div class="day-name">{{ day }}</div>
                <div class="line"><span class="tag">عليا</span>{% if up %}{{ up | join(' و ') }}{% else %}<span class="muted">لا توجد مناوبة</span>{% endif %}</div>
                <div class="line"><span class="tag low">دنيا</span>{% if lo %}{{ lo | join(' و ') }}{% else %}<span class="muted">لا توجد مناوبة</span>{% endif %}</div>
            </div>
        {% endfor %}
        </div>
    </div>

    {% endif %}

    {% if role == 'مدير' %}
    <div class="card">
        <h2>📨 إرسال رسالة</h2>
        <form method="POST" class="box" style="margin-top:0">
            <input type="hidden" name="csrf" value="{{ csrf_token() }}">
            <input type="hidden" name="send_message" value="1">
            <label>إرسال إلى (اضغط مطولاً لاختيار أكثر من اسم)</label>
            <select name="receivers" multiple style="height: 140px;" required>
                <option value="الكل">--- إرسال للجميع (ما عدا المدير) ---</option>
                {% for u in users %}{% if u != user %}<option value="{{ u }}">{{ u }}</option>{% endif %}{% endfor %}
            </select>
            <label>نص الرسالة</label>
            <textarea name="text" rows="3" maxlength="2000" required placeholder="اكتب رسالتك هنا..."></textarea>
            <button type="submit" class="btn">إرسال الرسالة</button>
        </form>
    </div>
    {% endif %}

    <div class="card">
        <h2>📥 الرسائل</h2>
        {% if user_messages %}
            {% for m in user_messages %}
            <div class="msg">
                <div class="meta"><b>من: {{ m.sender }}</b> &nbsp;|&nbsp; إلى: {{ m.receivers | join('، ') }}</div>
                <p>{{ m.text }}</p>
            </div>
            {% endfor %}
        {% else %}
            <p class="muted">لا توجد رسائل حالياً.</p>
        {% endif %}
    </div>
</div>
</body>
</html>
'''

USERS_HTML = '''
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="theme-color" content="#4f46e5">
<title>إدارة المستخدمين - EduTeam Hope School</title>
<style>{{ css|safe }}</style>
</head>
<body>
''' + TOPBAR_HTML + '''
<div class="wrap">
    {% if flash %}<div class="notice {{ 'err' if flash[0] == 'error' else 'ok' }}">{{ flash[1] }}</div>{% endif %}

    {% if notice %}
    <div class="notice ok">
        تم إعادة تعيين كلمة مرور <b>{{ notice.name }}</b>.<br>
        كلمة المرور المؤقتة: <span class="temp">{{ notice.password }}</span><br>
        <small>تظهر مرة واحدة فقط. أعطها للمستخدم، وسيُطلب منه اختيار كلمة جديدة عند الدخول.</small>
    </div>
    {% endif %}

    <div class="card">
        <h2>👥 إدارة المستخدمين</h2>
        <p class="muted">إذا نسي أحد كلمة المرور، اضغط "إعادة تعيين" وستظهر لك كلمة مؤقتة تعطيها له.
        ({{ waiting }} مستخدم لم يغيّر كلمته الأولى بعد)</p>
        <div class="tablewrap">
        <table>
            <tr><th>الاسم</th><th>الدور</th><th>الحالة</th><th></th></tr>
            {% for u in rows %}
            <tr>
                <td>{{ u.name }}</td>
                <td>{{ u.role }}</td>
                <td>{% if u.waiting %}<span class="status-wait">لم يغيّر كلمته بعد</span>{% else %}<span class="status-ok">مفعّل</span>{% endif %}</td>
                <td>
                    {% if u.name != me_name %}
                    <form method="POST" action="{{ url_for('admin_reset') }}" style="display:inline">
                        <input type="hidden" name="csrf" value="{{ csrf_token() }}">
                        <input type="hidden" name="username" value="{{ u.name }}">
                        <button type="submit" class="btn warn small">إعادة تعيين</button>
                    </form>
                    {% else %}<span class="muted">أنت</span>{% endif %}
                </td>
            </tr>
            {% endfor %}
        </table>
        </div>
    </div>
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

    return render_template_string(LOGIN_HTML, error=error, groups=LOGIN_GROUPS, css=BASE_CSS)


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
        CHANGE_PW_HTML, error=error, forced=bool(me.get('must_change')), css=BASE_CSS
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
    schedules = [
        ('upper', 'الصفوف العليا', db['schedule_upper']),
        ('lower', 'الصفوف الدنيا', db['schedule_lower']),
    ]
    return render_template_string(
        DASHBOARD_HTML,
        css=BASE_CSS, user=user, role=role, real_name=real_name, days=DAYS, locations=LOCATIONS,
        schedule_upper=db['schedule_upper'], schedule_lower=db['schedule_lower'],
        schedules=schedules, users=db['users'], teacher_list=TEACHER_LIST,
        user_messages=user_messages, flash=flash,
    )


def render_users(db, me_name, notice=None):
    rows = []
    for name, info in db['users'].items():
        rows.append({'name': name, 'role': info.get('role', ''), 'waiting': bool(info.get('must_change'))})
    waiting = sum(1 for r in rows if r['waiting'])
    flash = session.pop('flash', None)
    return render_template_string(
        USERS_HTML, css=BASE_CSS, user=me_name, role='مدير', me_name=me_name,
        rows=rows, waiting=waiting, notice=notice, flash=flash,
    )


@app.route('/admin/users')
def admin_users():
    db, me, resp = require_admin()
    if resp is not None:
        return resp
    return render_users(db, session['user'])


@app.route('/admin/reset', methods=['POST'])
def admin_reset():
    db, me, resp = require_admin()
    if resp is not None:
        return resp
    target = (request.form.get('username') or '')[:100]
    if target not in db['users'] or target == session['user']:
        flash_msg('مستخدم غير صالح.', ok=False)
        return redirect(url_for('admin_users'))
    temp = new_temp_password()
    db['users'][target]['pass'] = generate_password_hash(temp)
    db['users'][target]['must_change'] = True
    save_db(db)
    clear_fails_for_user(target)
    return render_users(db, session['user'], notice={'name': target, 'password': temp})


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