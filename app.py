import base64
import hmac
import json
import os
import secrets
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from urllib.parse import urlparse

import pymysql
from pymysql.cursors import DictCursor
from flask import (
    Flask, render_template_string, request, redirect, url_for, session,
    make_response, abort, Response, jsonify,
)
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.security import generate_password_hash, check_password_hash

try:
    from pywebpush import webpush, WebPushException
except Exception:   # المكتبة غير مثبّتة: يعمل الموقع بدون إشعارات
    webpush = None
    WebPushException = Exception

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
        'push': {},             # اشتراكات الإشعارات لكل مستخدم
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
    data.setdefault('push', {})
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
        sent = (request.form.get('csrf') or request.headers.get('X-CSRF-Token') or '').encode()
        expected = (session.get('csrf') or '').encode()
        if not expected or not hmac.compare_digest(sent, expected):
            abort(400)


@app.after_request
def add_security_headers(response):
    if 'Cache-Control' not in response.headers:
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
input[type=checkbox] { width: auto; margin: 0 0 0 10px; padding: 0; transform: scale(1.3); }
.recv-group { border: 1px solid var(--line); border-radius: 12px; padding: 10px 12px; margin: 10px 0; background: #fff; }
.recv-title { font-weight: bold; margin-bottom: 8px; color: var(--ink); }
.recv-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 6px; }
.recv-item { display: flex; align-items: center; padding: 9px 10px; border: 1px solid var(--line); border-radius: 10px;
             background: #f8fafc; font-size: 15px; color: var(--ink); cursor: pointer; margin: 0; }
.recv-item:has(input:checked) { background: #eef2ff; border-color: #c7d2fe; }
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
<link rel="manifest" href="/manifest.webmanifest">
<link rel="apple-touch-icon" href="/icons/icon-192.png">
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
            <p style="text-align:center;font-size:13px"><a href="/privacy">سياسة الخصوصية</a></p>
        </div>
    </div>
<script>if ('serviceWorker' in navigator) { window.addEventListener('load', function () { navigator.serviceWorker.register('/sw.js'); }); }</script>
</body>
</html>
'''

CHANGE_PW_HTML = '''
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="theme-color" content="#4f46e5">
<link rel="manifest" href="/manifest.webmanifest">
<link rel="apple-touch-icon" href="/icons/icon-192.png">
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
<script>if ('serviceWorker' in navigator) { window.addEventListener('load', function () { navigator.serviceWorker.register('/sw.js'); }); }</script>
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
<link rel="manifest" href="/manifest.webmanifest">
<link rel="apple-touch-icon" href="/icons/icon-192.png">
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
        <form method="POST" class="box" style="margin-top:0" onsubmit="return checkRecv()">
            <input type="hidden" name="csrf" value="{{ csrf_token() }}">
            <input type="hidden" name="send_message" value="1">
            <label>إرسال إلى (اختر بالمربعات)</label>
            <div class="actions" style="margin:6px 0 10px">
                <button type="button" class="btn small ok" onclick="setAllRecv(true)">✔ اختيار الكل</button>
                <button type="button" class="btn small bad" onclick="setAllRecv(false)">✖ إلغاء الكل</button>
                <span class="muted" id="recv-count">لم يتم اختيار أحد</span>
            </div>
            {% for group_label, names in recv_groups %}{% if names %}
            <div class="recv-group">
                <div class="recv-title">
                    <label class="recv-item" style="border:0;background:none;padding:0">
                        <input type="checkbox" class="group-box" onchange="toggleGroup(this)"> {{ group_label }} (الكل)
                    </label>
                </div>
                <div class="recv-grid">
                    {% for n in names %}
                    <label class="recv-item"><input type="checkbox" name="receivers" value="{{ n }}" onchange="updateRecvCount()"> {{ n }}</label>
                    {% endfor %}
                </div>
            </div>
            {% endif %}{% endfor %}
            <label>نص الرسالة</label>
            <textarea name="text" rows="3" maxlength="2000" required placeholder="اكتب رسالتك هنا..."></textarea>
            <button type="submit" class="btn">إرسال الرسالة</button>
        </form>
        <script>
        function recvBoxes() { return document.querySelectorAll('input[name="receivers"]'); }
        function syncGroups() {
          document.querySelectorAll('.recv-group').forEach(function (g) {
            var boxes = g.querySelectorAll('input[name="receivers"]');
            var all = true;
            boxes.forEach(function (b) { if (!b.checked) all = false; });
            g.querySelector('.group-box').checked = boxes.length > 0 && all;
          });
        }
        function updateRecvCount() {
          var boxes = recvBoxes(), n = 0;
          boxes.forEach(function (b) { if (b.checked) n++; });
          document.getElementById('recv-count').textContent = n ? ('تم اختيار ' + n + ' من ' + boxes.length) : 'لم يتم اختيار أحد';
          syncGroups();
        }
        function setAllRecv(v) { recvBoxes().forEach(function (b) { b.checked = v; }); updateRecvCount(); }
        function toggleGroup(g) {
          g.closest('.recv-group').querySelectorAll('input[name="receivers"]').forEach(function (b) { b.checked = g.checked; });
          updateRecvCount();
        }
        function checkRecv() {
          if (!document.querySelector('input[name="receivers"]:checked')) {
            alert('اختر مستلماً واحداً على الأقل.');
            return false;
          }
          return true;
        }
        </script>
    </div>
    {% endif %}

    <div class="card" id="push-card" data-key="{{ vapid_public }}" data-csrf="{{ csrf_token() }}">
        <h2>🔔 الإشعارات</h2>
        <p class="muted" id="push-status">جارٍ التحقق...</p>
        <button type="button" class="btn ok" id="push-btn" style="display:none">تفعيل الإشعارات على هذا الجهاز</button>
    </div>
    <script>
    (function () {
        var card = document.getElementById('push-card');
        var status = document.getElementById('push-status');
        var btn = document.getElementById('push-btn');
        var key = card.dataset.key, csrf = card.dataset.csrf;
        function setStatus(t) { status.textContent = t; }
        if (!('serviceWorker' in navigator) || !('PushManager' in window) || !('Notification' in window)) {
            setStatus('هذا الجهاز أو المتصفح لا يدعم الإشعارات. على الآيفون: ثبّت الموقع على الشاشة الرئيسية أولاً ثم افتحه منها.');
            return;
        }
        function toBytes(b64) {
            var pad = '='.repeat((4 - b64.length % 4) % 4);
            var raw = atob((b64 + pad).replace(/-/g, '+').replace(/_/g, '/'));
            var out = new Uint8Array(raw.length);
            for (var i = 0; i < raw.length; i++) { out[i] = raw.charCodeAt(i); }
            return out;
        }
        function post(url, body) {
            return fetch(url, {method: 'POST', headers: {'Content-Type': 'application/json', 'X-CSRF-Token': csrf}, body: JSON.stringify(body)});
        }
        function refresh(reg) {
            reg.pushManager.getSubscription().then(function (sub) {
                btn.style.display = 'inline-block';
                if (sub && Notification.permission === 'granted') {
                    btn.textContent = 'إيقاف الإشعارات على هذا الجهاز';
                    btn.className = 'btn bad';
                    btn.dataset.mode = 'off';
                    setStatus('✅ الإشعارات مفعّلة على هذا الجهاز.');
                } else {
                    btn.textContent = 'تفعيل الإشعارات على هذا الجهاز';
                    btn.className = 'btn ok';
                    btn.dataset.mode = 'on';
                    setStatus(Notification.permission === 'denied'
                        ? '⚠️ الإشعارات محظورة لهذا الموقع من إعدادات المتصفح.'
                        : 'فعّل الإشعارات لتصلك رسائل المدير فور إرسالها.');
                }
            });
        }
        navigator.serviceWorker.ready.then(function (reg) {
            refresh(reg);
            btn.addEventListener('click', function () {
                if (btn.dataset.mode === 'off') {
                    reg.pushManager.getSubscription().then(function (sub) {
                        if (!sub) { return; }
                        return post('/push/unsubscribe', {endpoint: sub.endpoint}).then(function () { return sub.unsubscribe(); });
                    }).then(function () { refresh(reg); });
                    return;
                }
                Notification.requestPermission().then(function (perm) {
                    if (perm !== 'granted') { refresh(reg); return; }
                    return reg.pushManager.subscribe({userVisibleOnly: true, applicationServerKey: toBytes(key)})
                        .then(function (sub) { return post('/push/subscribe', sub.toJSON()); })
                        .then(function (r) {
                            if (!r.ok) { setStatus('تعذّر حفظ الاشتراك. حاول مرة أخرى.'); return; }
                            refresh(reg);
                        });
                }).catch(function () { setStatus('تعذّر تفعيل الإشعارات على هذا الجهاز.'); });
            });
        });
    })();
    </script>

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
<script>if ('serviceWorker' in navigator) { window.addEventListener('load', function () { navigator.serviceWorker.register('/sw.js'); }); }</script>
</body>
</html>
'''

USERS_HTML = '''
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="theme-color" content="#4f46e5">
<link rel="manifest" href="/manifest.webmanifest">
<link rel="apple-touch-icon" href="/icons/icon-192.png">
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
<script>if ('serviceWorker' in navigator) { window.addEventListener('load', function () { navigator.serviceWorker.register('/sw.js'); }); }</script>
</body>
</html>
'''



# ----------------------------------------------------------------------
# تطبيق ويب (PWA) + متطلبات Google Play
# ----------------------------------------------------------------------
_ICON_192 = """
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
0wPg/wGZ56tOhXfNVQAAAABJRU5ErkJggg==
"""
_ICON_512 = """
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
pw5YTD/6J1D/rgBAf/SPNV7TmzrQ/I63XJNiWZSN9KN/MvVfDwD0R3+bYiCsqQNdnZ0qxh396I/+AwMA/dHfsgo8dWDQJi2O
FmPpa8Vsr8TqLyIu+qO/fRV46sCgTVrQfwb6m9hf/jHTX8T/hjDoj/4xM27sqQPz36SFe3/0n6H+IQQA+qN/XGJgyNSBSGzS
gv7oP1v9Jw0A9Ef/2MXA+tSBgizlJZ2S5YIUK632nnht0hL4rYX+6D9pAKA/+sexOqcOvLUiSonpWK7ZYv3bbxYVxlca6G+B
/sEDAP3R34KnAbX2P5LyK3Pvj/7dpeP7kqF/ZN/KlN0pgv526B8kANAf/Sn0R38L9PcdAOhvvf5WfwZOoT/6Bw0A9Ofen0J/
9LdGfx8BgP7oT6H/XPRX6D8d/ccNAPRHfwr953XvbxT6T0X/sQIA/dGfQv85fvKj0H86+quRAYD+6E+h/3w/9xf0n47+I54A
0B/9KfSfs/7xhTvy+g8LAPRHfwr90d9i/QcGAPqjP4X+6G+3/v0DAP3Rn0J/9Lde/z4BgP7oT6E/+idB/94AQH/0p9Af/ROi
f1cAoD/6U+iP/snRfz0A0B/9KfSf8zo/6D9b/VsBgP7oT6E/q7wlTX+R9b3w0B/9KfRH/wTpL8F2BEN/9KfQH/3jrr9Msik8
+qM/hf4hXv7Gk0ZdvMb6Ls1eo/Xf0X9Kh+HO9yVDf/Sn0L95LeSWlOOK02GSdkREsovKGPSfymG4UTn96I/+1Kz0N5HSX4lS
4qbVc39T/tUlb8s12nGUEVEihWWvuGx+9kptIafQfxqH4c7/9KM/+lNJvffXjngNufKm9473uu+/Na203HRXxk2J8URp+b8v
1X5yppZeUMaT4rLJb1b1GvqH+bu48z396B/7tzIV6xSY6+XvuLJ6xeQW1Wf/3eJHDuTyS71jv/1dzm33LYjIyyeqTz1U/OHR
yua3axExBv3D+V3cOZ5+9I8U3Ar90X+2+q9c9m66M/Opf5n7wK60iDQaIiK6ozPRGDGeaEdu+FD6g7enH//zwlNfLdar4qZH
fzOM/uEHAPpbfO9PUTO9979sdn5y4Yv/c7OINOriOOI4G/7+2qaFnicicv+/zr/vhtT//vdXjKeUEmPmfMnEXX/xNQ8A/S3W
nwihZqe/I6tXzA13pP7oTzZ7nngNcdwRP0Br0VrqVbnxjvQXv7SlXDDxu2Sip7+PAEB/9KfQf/LLXylpNCSbV5/+4qLWYkyr
13OszyvS0qjLjXekb7svUy6Y8f8h+k8UAOiP/hT6h3L5a0dWr3j3/5vcb92can7y4w8sR4yRP/yvS1uu0fXq+pQx9J9WAKA/
+lPoH8rlr5TUKrL9Pc7d+3PNb3d9j6bEa0gqrT72uWy54Gkd+Usmqvo3mz40+qM/Rc3m8teOFFe8O/ct5DYpz/N9/94eRCm5
e39uyzVOrTbuIOjv+wkA/dGfQv9wL3+lZGExhDUo3bQ0J4ih/ySDaPRHf4qaweXf/Pxn2zucOx5YEJFgX+E2x2nUJZ1RH9q3
UC54I8dB/yGDaPRHf4qa2eWvlKTSIbwHlZJUevRUAPQfPohGf/SnqNld/qa1yPPkNXIc9B85iEZ/9KeomemvHUlnw3knprPR
WyY6Vvr3BgD6oz+F/lO6/I0R7crqVfPK89Xm/w1WxojSUquYV09XB30PjP5jDqLbf4z+6E+h/1Qvfzclq1e8f3i5ZoyYCT4I
0lpEqwsv1FPpPg8B6D/+IDq0NxD6oz+F/kPLa0gmq/7xlbpSooJ2ARlPjJGfvVyrVPqsBoH+vgbR3PujP4X+s7n8PU8WFtXz
T1UuvFjTOui3wUqUkse/UqgUTXNlCPQPPEgITwDob5P+qmP1Xcqaap5Qpeepf+vvK1FKvv1/CpWSMcb3NwFeQ7SScz+ovnyi
ml9SnRGC/gEG0TM+/egfaf2VVEtGa8ltEuMRA5bQbzzJbRKtpVoySoX5Ngtw+XsNyW9WPzxaOfqNouNKo+bvd9GO1GrmL/7L
VcdV3PtPPohzy2/+R/RHfxExRlIL6uc/qb16prq4VW9/j5tKS70qxgRcs4Wa/12/kWxenJT89HT1r7+08qO/q6TW2mbm+MGv
ZySbVz99ofbeD6a2v9dpPZ2MOiCvIdoRz5M/+0/LF1+tp7Pr/T/oH3gQ9Qef+AX6o39nVUpGK3n/rem79uffvzOjlJQLYrr3
6qMiTr8SWciLMfLT09UfHC5eOF0Vs96AP/ev/ZSWelWUmD/6k803fzgjIo26aEfUxoMz4pnWB0elVfOX/2P51JHy0tt0+8Mf
9J9kkIABgP626i9r0JcLRim57tb0h4mB+NOfySvV/iZg3vq332bGk3LR7Lwn88//81JubUd4r7H+xYDTsWXt2e9X/vK/rxSX
vUyu9dF/WM+lidU/YACgv8X6q87rkxiIURlpNCS7KCJTpD/cy7/5sU+laDZfoz/22eyH92dTaZXpnidcWDb/+OPak18t/uhU
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
/uiP/uiP/nHXP0gAoD/6oz/6o78F+vsOAPRHf/RHf/S3Q39/AYD+6I/+6I/+1ujvIwDQH/3RH/3R3yb9xw0A9Ed/9Ed/9LdM
fxlnNVD0R3/0R3/0t0x/Nc4TAPqjP/qjP/rbd+8vIwMA/dEf/dEf/e3TX40MAPRHf/RHf/S3WP+BAYD+6I/+6I/+duvfPwDQ
H/3RH/3R33r9+wQA+qM/+qM/+idB/94AQH/0R3/0R/+E6C/teQBBDhT90R/90R/9Y6u/BN8QBv3RH/3RH/3jrL+IuNz7oz/6
oz/6J1D/QE8A6I/+6I/+6B9//f0HAPqjP/qjP/pbob/PAEB/9Ed/9Ed/W/T3EwDoj/7oj/7ob5H+YwcA+qM/+qM/+tul/3gB
gP7oj/7oj/7W6T9GAKA/+qM/+qO/jfqPCgD0R3/0R3/0t1T/oQGA/uiP/uiP/vbqPzgA0B/90R/90d9q/QcEAPqjP/qjP/rb
rn+/AEB/9Ed/9Ef/BOgv7eWg0R/90R/90T85+qveJwD0R3/0R3/0T8a9v3QFAPqjP/qjP/onQ3/VFQDoj/7oj/7onzD9RUSj
P/qjP/qjfwL1l94vgdEf/dEf/dE/Cfqb5hMA+qM/+qM/+ifs3r/3CQD90R/90R/9E3Lv3yyN/uiP/uiP/gnUvxUA6I/+6I/+
6J80/UVEoz/6oz/6o38C9Rd/m8KjP/qjP/qjvy36hxAA6I/+6I/+6B9H/ScNAPRHf/RHf/SPqf4TBQD6oz/6oz/6x1f/4AGA
/uiP/uiP/rHWP2AAoD/6oz/6o3/c9Q8SAOiP/uiP/uhvgf6+AwD90R/90R/97dDfXwCgP/qjP/qjvzX6+wgA9Ed/9Ed/9LdJ
/3EDAP3RH/3RH/0t03+sAEB/9Ed/9Ed/+/RXIwMA/dEf/dEf/a3Uf8QTAPqjP/qjP/rbqv+wAEB/9Ed/9Ed/i/UfGADoj/7o
j/7ob7f+/QMA/dEf/dEf/a3Xv08AoD/6oz/6o38S9O8NAPRHf/RHf/RPiP5dAYD+6I/+6I/+ydF/PQDQH/3RH/3RP1H6twIA
/dEf/dEf/ZOmv4ho9Ed/9Ed/9E+g/jLhpvDoj/7oj/7oH9/LX8fk9KM/+qM/+qN/yIeh43D60R/90R/90T/8w9CRP/3oj/7o
j/7oP5XD0NE+/eiP/uiP/ug/rcPQET796I/+6I/+6D/Fw9BRPf3oj/7oj/7oP93D0JE8/eiP/uiP/ug/9cPQ0Tv96I/+6I/+
6D+Lw9ARO/3oj/7oj/7oP6PD0FE6/eiP/uiP/ug/u8PQkTn96I/+6I/+6D/Tw9Doj/7oj/7on8zLX6M/+qM/+qN/Mi9/jf7o
j/7oj/6JvPwHBAD6oz/6oz/6261//wBAf/RHf/RHf+v17xMA6I/+6I/+6J8E/XsDAP3RH/3RH/0Tor+IuCH+DPRHf/RHf/SP
i/4Syp7A6I/+6I/+6B87/UXE5d4f/dEf/dE/gfqH9gSA/uiP/uiP/vHSP5wAQH/0R3/0R//Y6R9CAKA/+qM/+qN/HPWfNADQ
H/3RH/3RP6b6TxQA6I/+6I/+6B9f/YMHAPqjP/qjP/rHWv+AAYD+6I/+6I/+cdc/SACgP/qjP/qjvwX6+w4A9Ed/9Ed/9LdD
f38BgP7oj/7oj/7W6O8jANAf/dEf/dHfJv3HDQD0R3/0R3/0t0x/aS8Hjf7oj/7oj/7J0V+N8wSA/uiP/uiP/vbd+8vIAEB/
9Ed/9Ed/+/RXIwMA/dEf/dEf/S3Wf2AAoD/6oz/6o7/d+vcPAPRHf/RHf/S3Xv8+AYD+6I/+6I/+SdC/NwDQH/3RH/3RPyH6
S3segPL/7kd/9Ed/9Ef/WJ9cHezdj/7oj/7oj/5xP7ku9/7oj/7oj/4J1H+MJwD0R3/0R3/0t/TdrtEf/dEf/dE/gfoPDQD0
R3/0R3/0t/rdrtEf/dEf/dE/gfoPCAD0R3/0R3/0T8C7XaM/+qM/+qN/AvXfEADoj/7oj/7onwz9uwMA/dEf/dEf/ROjv3Rs
CamS8NuGLCb6oz/vdgv0T/DJdVsjmAS/6PMPfzXnF8Qk+4oyKtHEzP/eXyX78p/nCDpG+kenbHpBonPvP58yvNu5/JP7gvx/
LjWv75WvxGYAAAAASUVORK5CYII=
"""
_ICON_MASKABLE_512 = """
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
xUB50z55vPL4g5UL50yhpLq3CvqndOw/MQDQPz365wK5/Wjpnn+61rnxWiIK+mlpiYFW0wZLqp0Ex//j9hPHKq2maDX4MUb/
tFEWoL8D3a/EGHn+6Z3iqrrlC8X1fVrn9n6Uo9EW/hCwlFcisnXePPW96otP1axBfwf0H/kEgP4p7P56zdar9sqr2K+Rlopm
7V6x2dnT9Veeq59+rPr2L1r5gsovK775Sb/+wwMA/dPZ/Xrsju2s60mbm/tiRZQoJdbKiz+uPfZA5eXTtWZDims6yIs1/eKj
f1r1HxIA6J/y7ldKdE5ZY1nZnzZ/+ntnhL1xtvHIfeWzp+vGSqGk6jvSatnBTzv6p1j/wQBAf4e6n729aPOkv7smRK1qf/Fq
4+9es2St7FRNcU1rJZVt+x++9m512+aCnnkA6J9u/aX7I/DMlnhF/1mdRnv+fXFVWZHnTu6cOlF95MEKa8DRZkR/LieVLfvE
8cqJb1VMU/7w2PuKa6q4lut+TBW/+rqmv4ypAkJ/J7q/EwMlpdbU5kVz3zc2//p4hVWgadO37rrQuVxnQdAnj1XOvdXKL6u1
fbq9XnT746eUtJro757+IhIw9veg+40RMRIEsrFPb140931j66+PVw/fXWjvA9P+sY4YoIX/OLU3lhDd2Rnmyd0tATb260a9
82TQpr/9333Df/R3RP/EngDQPw3db620WrsxcME88M2t791XvvrapfZOkMQALQL9lyzwsL5fGyOtiZvFo787+icTAOifqu63
VrVaEixJflk3G/LiqfpLz9QPHsp//p7Sx27sxAA1o7QBtY3to793ibeNXfq7Q/5kG/ovkLIgyZdB/8V3v+r8x4ppiVJSXFUi
8sKp+ovP1A8eyh+5t3Twk8vtcg5+JaZ1Kzv1sEWeC6vKtDr0hwwS9HeLsiCxl0H/dOh/6UO9yF4MvHC6fv1nlj9yMH/znQVq
RjNOf7u8R+Vkp2xfP9t49L7y2Wf6tnlpRdrwC/0dpCxI5mXQPzX6Dz1Ib83omZO10yd2HnmwctvRwl7NaFOU5ueBbNHfqew8
VvnBX1Q3z5v6ji2udei37t256B/nIEECL4P+6dZ/MAZ2a0bv/8bW48ertx0t3Pbl4uo6NaP+t1GVnStFHSzJ0royLbFzORP0
TwllwbQvg/6O6N8XAz01o/f/ydYT36nedHilvcAcxUK+0j+qsnN9n25v42Vb87pl0D81lAVTvQz6u6Z/7/cAnZrR/frie+b4
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
527/bOnf/vygP/qjv6tj/5nrr8QayeXkX/zRZQduyjcbYq3kgr7veZQSnRNrpdmQAzfl//kfXZbLiTXRvgtC//nrLyIa/dEf
/R3VP9GDDD+ezsn2BXPk68UDN+abDQmWRrKulARL0mzIgRvzR75e3L5gdM6h2z+L+suUm8KjP/rTvIiQkRWfjZr85lW5m+8q
WiO5EIvH5wKxRv7RXcXfvCrXqIV6CED/RemfQACgP/rTvNS/PfwvXzQ33L5SXFMm3Fc6SokxUlxTn7h9pXxx8kMA+i9Q/2kD
AP3Rn+ar/iJiWlLaUAduzLdlD3twJSJy4MZ8aUOZFvqnV/+pAgD90Z/msf5KSashqxv6mo/nRUSFpqL9L6/5eH51Q7cao38z
QP9F6x8/ANAf/Wke69/9J6Yl9Wqce7VetaY18kXQPw36xwwA9Ed/mv/67/5DHWuBB51D/7TrHycA0B/9aVnRX8RaqddiPQHU
rLXon2r9IwcA+qM/LSP6WytLy/Lur1rPPbZjrYz/Obe3mZZYK88+tvPur1pLy30rRaN/qvSPFgDoj/7hL40222bjdW60frZW
giX1yrMNpaJVASklrz7bCJYU+qdZ/wgBgP7oP+5jlOuM+2gzl9+KaYnKxejcyP1sWlJcU88/WXv9hYbOSSvEQ0CrJTonr73Q
+OmTteLaXhko+qdQ/7ABgP7oP/7qalVb2pBcQAzMnP5cIMUNqVdtmPc5gZ0dlWgtf/ln28aIVhPWd7NGtBJj5KE/21Z67zXR
P536i0ju4If+Nfqjf/wRhJZWU174wU5ly77/qmDjfcq0pNUUUdOuC0/rpd8aCZaksCbb5+1T/6vy/T/dqlWt1rPVX4mIleWC
+tvXWm+93vzE4ZV2d1/6jVA7nNpLwv2nf3PxhZP11d1ZYOifTv2ViJoYAOiP/mEOUtux/+fZ2s9+VKtuEwMzo/89+9SDlYf+
+OLLT+1YI7PWv/uX1shKSb3xUuOdX7SuvXF5udDZ/bHV7Jye1qKUaC2VLftf//3mM4/urP+GbjXRP9Vj//ZB1O9/7lfoj/5T
HkQpUVqaddmpmP1XBDd8vnjoSHH/FWqnIs26KE0MxGmmJUFeloty4R373Pcrzz1cufBOa7mog7xYM+6rtgT133vUy8nOtt24
XH/29wqf/mJhbV9f/mydN0/9ZfXJb1UvnjMrq4z93dB/XACgP/pHPQgxkCD9OifFNTn/tn3u4Qj0z0j/TgZoadSlvmOK6/oj
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
"""

ICONS = {
    'icon-192.png': base64.b64decode(''.join(_ICON_192.split())),
    'icon-512.png': base64.b64decode(''.join(_ICON_512.split())),
    'icon-maskable-512.png': base64.b64decode(''.join(_ICON_MASKABLE_512.split())),
}

SW_JS = """
const CACHE = 'hope-school-offline-v1';
const OFFLINE_URL = '/offline';
self.addEventListener('install', (event) => {
  event.waitUntil(caches.open(CACHE).then((cache) => cache.add(OFFLINE_URL)));
  self.skipWaiting();
});
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
  );
  self.clients.claim();
});
self.addEventListener('fetch', (event) => {
  if (event.request.mode === 'navigate') {
    event.respondWith(fetch(event.request).catch(() => caches.match(OFFLINE_URL)));
  }
});
self.addEventListener('push', (event) => {
  let data = {};
  try { data = event.data ? event.data.json() : {}; } catch (e) { data = {}; }
  const title = data.title || 'مدرسة الأمل';
  event.waitUntil(self.registration.showNotification(title, {
    body: data.body || '',
    icon: '/icons/icon-192.png',
    dir: 'rtl',
    lang: 'ar',
    tag: 'school-message',
    renotify: true,
    data: { url: data.url || '/dashboard' }
  }));
});
self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  const url = (event.notification.data && event.notification.data.url) || '/dashboard';
  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then((list) => {
      for (const c of list) {
        if ('focus' in c) { c.navigate(url); return c.focus(); }
      }
      return clients.openWindow(url);
    })
  );
});
"""

OFFLINE_HTML = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>لا يوجد اتصال</title>
<style>
  body { font-family: Tahoma, Arial, sans-serif; background: #f1f5f9; display: flex; justify-content: center;
         align-items: center; min-height: 100vh; margin: 0; text-align: center; color: #0f172a; }
  .box { background: #fff; padding: 30px; border-radius: 16px; max-width: 340px; box-shadow: 0 4px 20px rgba(0,0,0,.08); }
  button { background: #4f46e5; color: #fff; border: 0; border-radius: 10px; padding: 10px 20px; font-size: 16px; cursor: pointer; }
</style>
</head>
<body><div class="box">
  <h2>📡 لا يوجد اتصال</h2>
  <p>تعذّر الوصول للموقع. تأكد من الإنترنت وحاول مرة أخرى.<br>
  (إذا كان الموقع نائماً قد يحتاج حوالي دقيقة ليصحو.)</p>
  <button onclick="location.reload()">إعادة المحاولة</button>
</div></body>
</html>
"""

PRIVACY_HTML = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="theme-color" content="#4f46e5">
<title>سياسة الخصوصية - مدرسة الأمل</title>
<style>{{ css|safe }}</style>
</head>
<body>
<div class="topbar"><div class="topbar-in"><div class="brand">🏫 مدرسة الأمل - EduTeam</div></div></div>
<div class="wrap">
<div class="card">
  <h2>سياسة الخصوصية</h2>
  <p class="muted">آخر تحديث: نوفمبر 2026</p>

  <h3>1. ما هذا التطبيق؟</h3>
  <p>تطبيق داخلي لكادر مدرسة الأمل (EduTeam) لعرض جداول المناوبة (الديوتي) وتبادل الرسائل بين الإدارة والكادر.</p>

  <h3>2. البيانات التي نحفظها</h3>
  <ul>
    <li>اسم المستخدم المعروض والدور الوظيفي (مدير، سكرتيرة، معلم...).</li>
    <li>كلمة المرور بصيغة مشفّرة؛ لا نخزّن كلمة المرور الأصلية.</li>
    <li>جداول المناوبة التي تضعها الإدارة.</li>
    <li>الرسائل التي ترسلها الإدارة للكادر.</li>
    <li>إذا فعّلت الإشعارات: عنوان اشتراك الإشعارات الخاص بجهازك، ويُستخدم فقط لإرسال تنبيه عند وصول رسالة جديدة، ويمكنك إيقافه في أي وقت من لوحة التحكم.</li>
  </ul>
  <p>لا نجمع الموقع الجغرافي، ولا جهات الاتصال، ولا الصور، ولا أي بيانات أخرى من جهازك.</p>

  <h3>3. كيف نستخدم البيانات</h3>
  <p>فقط لتشغيل التطبيق: تسجيل الدخول، وعرض المناوبات والرسائل. لا نبيع البيانات ولا نستخدمها للإعلانات أو التحليلات.</p>

  <h3>4. مشاركة البيانات</h3>
  <p>لا نشارك بياناتك مع أي جهة. تُحفظ البيانات على خوادم مزوّدي الاستضافة وقاعدة البيانات لأغراض التشغيل فقط.</p>

  <h3>5. الأمان</h3>
  <p>الاتصال بالموقع مشفّر (HTTPS)، وكلمات المرور مشفّرة، وهناك حماية من المحاولات الخاطئة المتكررة.</p>

  <h3>6. الاحتفاظ بالبيانات وحذفها</h3>
  <p>تبقى البيانات طالما الحساب فعّال. يمكنك طلب حذف حسابك أو بياناتك من إدارة المدرسة.</p>

  <h3>7. الأطفال</h3>
  <p>التطبيق مخصص لكادر المدرسة البالغين، ولا يستهدف الأطفال.</p>

  <h3>8. التواصل</h3>
  <p>{{ contact }}</p>

  <h3>9. تعديل السياسة</h3>
  <p>قد نحدّث هذه السياسة، وسيظهر تاريخ آخر تحديث في أعلى الصفحة.</p>
</div>
</div>
</body>
</html>
"""


@app.route('/manifest.webmanifest')
def manifest():
    data = {
        "name": "مدرسة الأمل - EduTeam",
        "short_name": "مدرسة الأمل",
        "description": "جداول المناوبة والرسائل لكادر مدرسة الأمل",
        "id": "/",
        "start_url": "/",
        "scope": "/",
        "display": "standalone",
        "lang": "ar",
        "dir": "rtl",
        "background_color": "#f1f5f9",
        "theme_color": "#4f46e5",
        "icons": [
            {"src": "/icons/icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any"},
            {"src": "/icons/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any"},
            {"src": "/icons/icon-maskable-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable"},
        ],
    }
    resp = Response(json.dumps(data, ensure_ascii=False), mimetype='application/manifest+json')
    resp.headers['Cache-Control'] = 'public, max-age=3600'
    return resp


@app.route('/sw.js')
def service_worker():
    resp = Response(SW_JS, mimetype='application/javascript')
    resp.headers['Cache-Control'] = 'no-cache'
    resp.headers['Service-Worker-Allowed'] = '/'
    return resp


@app.route('/icons/<name>')
def pwa_icon(name):
    data = ICONS.get(name)
    if data is None:
        abort(404)
    resp = Response(data, mimetype='image/png')
    resp.headers['Cache-Control'] = 'public, max-age=604800'
    return resp


@app.route('/offline')
def offline():
    return Response(OFFLINE_HTML, mimetype='text/html')


@app.route('/privacy')
def privacy():
    email = (os.environ.get('CONTACT_EMAIL') or '').strip()
    contact = ('للتواصل أو لطلب حذف بياناتك: ' + email) if email else 'للتواصل أو لطلب حذف بياناتك، يرجى مراجعة إدارة المدرسة.'
    return render_template_string(PRIVACY_HTML, css=BASE_CSS, contact=contact)


@app.route('/.well-known/assetlinks.json')
def assetlinks():
    """ملف التحقق الذي يربط الموقع بتطبيق أندرويد (يُضبط من متغيرات Render)."""
    package = (os.environ.get('ANDROID_PACKAGE') or '').strip()
    prints = [f.strip() for f in (os.environ.get('ANDROID_SHA256') or '').split(',') if f.strip()]
    if not package or not prints:
        abort(404)
    data = [{
        "relation": ["delegate_permission/common.handle_all_urls"],
        "target": {
            "namespace": "android_app",
            "package_name": package,
            "sha256_cert_fingerprints": prints,
        },
    }]
    resp = Response(json.dumps(data), mimetype='application/json')
    resp.headers['Cache-Control'] = 'public, max-age=300'
    return resp



# ----------------------------------------------------------------------
# الإشعارات (Web Push)
# ----------------------------------------------------------------------
PUSH_HOSTS = (
    'fcm.googleapis.com',
    'updates.push.services.mozilla.com',
    'push.services.mozilla.com',
    'push.apple.com',
    'notify.windows.com',
)
MAX_DEVICES_PER_USER = 5


def _b64u(raw):
    return base64.urlsafe_b64encode(raw).rstrip(b'=').decode()


def get_vapid_keys(db):
    """مفاتيح VAPID تُولَّد تلقائياً أول مرة وتُحفظ في القاعدة (لا حاجة لضبطها يدوياً)."""
    keys = db.get('vapid')
    if keys and keys.get('private') and keys.get('public'):
        return keys
    priv = ec.generate_private_key(ec.SECP256R1())
    raw_priv = priv.private_numbers().private_value.to_bytes(32, 'big')
    raw_pub = priv.public_key().public_bytes(
        serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint
    )
    keys = {'private': _b64u(raw_priv), 'public': _b64u(raw_pub)}
    db['vapid'] = keys
    save_db(db)
    return keys


def valid_push_endpoint(endpoint):
    """يقبل فقط عناوين خدمات الإشعارات المعروفة (حماية من إرسال طلبات لعناوين أخرى)."""
    if not isinstance(endpoint, str) or len(endpoint) > 600:
        return False
    parts = urlparse(endpoint)
    host = (parts.hostname or '').lower()
    if parts.scheme != 'https' or not host:
        return False
    return any(host == h or host.endswith('.' + h) for h in PUSH_HOSTS)


def notify_users(db, receivers, title, body):
    """يرسل إشعاراً للمستلمين. يرجع (عدد من وصله إشعار، عدد من لم يفعّل الإشعارات)."""
    push = db.setdefault('push', {})
    receivers = [u for u in receivers if u in db['users']]
    no_sub = len([u for u in receivers if not push.get(u)])
    if webpush is None:
        return 0, len(receivers)
    jobs = [(u, dict(sub)) for u in receivers for sub in push.get(u, [])]
    if not jobs:
        return 0, no_sub

    keys = get_vapid_keys(db)
    email = (os.environ.get('CONTACT_EMAIL') or '').strip()
    claim_sub = ('mailto:' + email) if email else request.host_url.rstrip('/')
    payload = json.dumps({'title': title, 'body': body, 'url': '/dashboard'}, ensure_ascii=False)

    def send(job):
        user, sub = job
        try:
            webpush(
                subscription_info=sub, data=payload, vapid_private_key=keys['private'],
                vapid_claims={'sub': claim_sub}, timeout=6, ttl=86400,
            )
            return user, sub['endpoint'], 'ok'
        except WebPushException as exc:
            code = getattr(getattr(exc, 'response', None), 'status_code', None)
            return user, sub['endpoint'], ('gone' if code in (404, 410) else 'fail')
        except Exception:
            return user, sub['endpoint'], 'fail'

    with ThreadPoolExecutor(max_workers=16) as pool:
        results = list(pool.map(send, jobs))

    ok_users = {u for u, _e, r in results if r == 'ok'}
    gone = {(u, e) for u, e, r in results if r == 'gone'}
    if gone:   # أجهزة ألغت الاشتراك: نحذفها
        for u, e in gone:
            push[u] = [s2 for s2 in push.get(u, []) if s2['endpoint'] != e]
        save_db(db)
    return len(ok_users), no_sub


@app.route('/push/subscribe', methods=['POST'])
def push_subscribe():
    db, me = current()
    if me is None or me.get('must_change'):
        abort(403)
    sub = request.get_json(silent=True) or {}
    keys = sub.get('keys') or {}
    endpoint, p256dh, auth = sub.get('endpoint'), keys.get('p256dh'), keys.get('auth')
    if not (valid_push_endpoint(endpoint) and isinstance(p256dh, str) and isinstance(auth, str)
            and 0 < len(p256dh) <= 200 and 0 < len(auth) <= 100):
        return jsonify({'ok': False}), 400
    user = session['user']
    push = db.setdefault('push', {})
    # الجهاز الواحد لمستخدم واحد فقط (حتى لا تصل رسائل شخص لجهاز غيره)
    for name in list(push):
        push[name] = [x for x in push[name] if x['endpoint'] != endpoint]
    mine = push.setdefault(user, [])
    mine.append({'endpoint': endpoint, 'keys': {'p256dh': p256dh, 'auth': auth}})
    push[user] = mine[-MAX_DEVICES_PER_USER:]
    save_db(db)
    return jsonify({'ok': True})


@app.route('/push/unsubscribe', methods=['POST'])
def push_unsubscribe():
    db, me = current()
    if me is None:
        abort(403)
    endpoint = (request.get_json(silent=True) or {}).get('endpoint')
    user = session['user']
    push = db.setdefault('push', {})
    push[user] = [x for x in push.get(user, []) if x['endpoint'] != endpoint]
    save_db(db)
    return jsonify({'ok': True})


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
                preview = text if len(text) <= 100 else text[:100] + '…'
                sent_n, missing_n = notify_users(db, receivers, 'رسالة جديدة من المدير', preview)
                flash_msg('تم إرسال الرسالة. وصل إشعار لـ %d، ولم يفعّل الإشعارات %d.' % (sent_n, missing_n))
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
        recv_groups=[(lbl, [n for n in names if n != user and n in db['users']]) for lbl, names in LOGIN_GROUPS],
        user_messages=user_messages, flash=flash, vapid_public=get_vapid_keys(db)['public'],
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