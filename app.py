from flask import Flask, render_template_string, request, session, redirect, url_for

app = Flask(__name__)
app.secret_key = 'hope_school_secret_key_123'

# قاعدة بيانات المعلمين والإدارة والموظفين مع كلمات المرور القابلة للتحديث
TEACHERS = {
    'khader': {
        'password': '111',
        'name': 'المدير خضر (الليدر)',
        'role': 'مدير المدرسة',
        'schedule': {
            'السبت': ['إدارة عامة', 'اجتماع الهيئة التدريسية', 'متابعة الإتحاد'],
            'الأحد': ['متابعة سير العمل', 'فراغ', 'لقاء أولياء الأمور'],
            'الإثنين': ['إدارة عامة', 'فراغ', 'تقييم الأداء'],
            'الثلاثاء': ['اجتماع إداري', 'فراغ', 'إشراف عام'],
            'الأربعاء': ['متابعة الميزانية', 'فراغ', 'جولة صفية'],
            'الخميس': ['تقييم أسبوعي', 'فراغ', 'إقرار الجدول القادم']
        }
    },
    'berta': {
        'password': '222',
        'name': 'السكرتيرة بيرتا',
        'role': 'سكرتارية الإدارة',
        'schedule': {
            'السبت': ['تسجيل الطلاب', 'تنسيق المواعيد', 'أرشفة الملفات'],
            'الأحد': ['استقبال المراجعين', 'فراغ', 'صادر ووارد'],
            'الإثنين': ['متابعة الغياب', 'فراغ', 'طباعة التعاميم'],
            'الثلاثاء': ['تسجيل الطلاب', 'فراغ', 'تنسيق المواعيد'],
            'الأربعاء': ['أرشفة الملفات', 'فراغ', 'استقبال المراجعين'],
            'الخميس': ['إعداد التقارير', 'فراغ', 'إنهاء المهام الأسبوعية']
        }
    },
    'ahmad': {
        'password': '456',
        'name': 'الأستاذ أحمد',
        'role': 'معلم',
        'schedule': {
            'السبت': ['لغة عربية صف ثاني', 'فراغ', 'لغة عربية صف أول'],
            'الأحد': ['فراغ', 'مكتبة', 'لغة عربية صف أول', 'فراغ'],
            'الإثنين': ['فراغ', 'لغة عربية صف ثاني', 'فراغ'],
            'الثلاثاء': ['لغة عربية صف ثاني', 'فراغ', 'لغة عربية صف أول'],
            'الأربعاء': ['أنشطة', 'فراغ', 'فراغ'],
            'الخميس': ['لغة عربية صف ثاني', 'فراغ', 'لغة عربية صف أول']
        }
    },
    'nizar': {
        'password': '333',
        'name': 'الأستاذ نزار',
        'role': 'معلم',
        'schedule': {
            'السبت': ['رياضيات صف ثالث', 'فراغ', 'حصص صيانة'],
            'الأحد': ['فراغ', 'فراغ', 'رياضيات صف خامس'],
            'الإثنين': ['حصص 3', 'فراغ', 'رياضيات صف ثالث'],
            'الثلاثاء': ['فراغ', 'فراغ', 'رياضيات صف رابع'],
            'الأربعاء': ['رياضيات صف سادس', 'فراغ', 'رياضيات صف خامس'],
            'الخميس': ['نشاط أسبوعي', 'فراغ', 'رياضيات صف ثالث']
        }
    },
    'fouad': {
        'password': '444',
        'name': 'الأستاذ فؤاد',
        'role': 'معلم',
        'schedule': {
            'السبت': ['تربية إسلامية', 'فراغ', 'تلاوة'],
            'الأحد': ['فراغ', 'تربية إسلامية', 'فراغ'],
            'الإثنين': ['صف أول', 'فراغ', 'تربية إسلامية'],
            'الثلاثاء': ['فراغ', 'أنشطة دينية', 'فراغ'],
            'الأربعاء': ['تربية إسلامية', 'فراغ', 'فراغ'],
            'الخميس': ['تلاوة ومحفوظات', 'فراغ', 'تربية إسلامية']
        }
    },
    'andres': {
        'password': '555',
        'name': 'الأستاذ أندريس',
        'role': 'معلم',
        'schedule': {
            'السبت': ['لغة إنجليزية', 'فراغ', 'محادثة'],
            'الأحد': ['فراغ', 'لغة إنجليزية', 'فراغ'],
            'الإثنين': ['قواعد إنجليزية', 'فراغ', 'أنشطة لغة'],
            'الثلاثاء': ['فراغ', 'لغة إنجليزية', 'فراغ'],
            'الأربعاء': ['محادثة', 'فراغ', 'تطبيقات صوتية'],
            'الخميس': ['لغة إنجليزية', 'فراغ', 'مراجعة أسبوعية']
        }
    },
    'waleed': {
        'password': '666',
        'name': 'الأستاذ وليد',
        'role': 'معلم',
        'schedule': {
            'السبت': ['تاريخ', 'فراغ', 'جغرافيا'],
            'الأحد': ['فراغ', 'تاريخ', 'فراغ'],
            'الإثنين': ['جغرافيا', 'فراغ', 'دراسات اجتماعية'],
            'الثلاثاء': ['فراغ', 'تاريخ', 'فراغ'],
            'الأربعاء': ['دراسات اجتماعية', 'فراغ', 'خرائط'],
            'الخميس': ['تاريخ', 'فراغ', 'جغرافيا']
        }
    },
    'doaa': {
        'password': '777',
        'name': 'المعلمة دعاء',
        'role': 'معلمة',
        'schedule': {
            'السبت': ['علوم صف رابع', 'فراغ', 'تجارب علمية'],
            'الأحد': ['فراغ', 'علوم صف خامس', 'فراغ'],
            'الإثنين': ['علوم صف رابع', 'فراغ', 'مختبر'],
            'الثلاثاء': ['فراغ', 'علوم صف خامس', 'فراغ'],
            'الأربعاء': ['أنشطة علمية', 'فراغ', 'علوم صف رابع'],
            'الخميس': ['علوم صف خامس', 'فراغ', 'مراجعة']
        }
    },
    'khawla': {
        'password': '888',
        'name': 'المعلمة خيلاء',
        'role': 'معلمة',
        'schedule': {
            'السبت': ['لغة عربية', 'فراغ', 'تعبير'],
            'الأحد': ['فراغ', 'قواعد', 'فراغ'],
            'الإثنين': ['لغة عربية', 'فراغ', 'مطالعة'],
            'الثلاثاء': ['فراغ', 'تعبير', 'فراغ'],
            'الأربعاء': ['لغة عربية', 'فراغ', 'قواعد'],
            'الخميس': ['إملاء وخط', 'فراغ', 'نشاط']
        }
    },
    'nour': {
        'password': '999',
        'name': 'المعلمة نور',
        'role': 'معلمة',
        'schedule': {
            'السبت': ['تربية فنية', 'فراغ', 'رسم وتلوين'],
            'الأحد': ['فراغ', 'تربية فنية', 'فراغ'],
            'الإثنين': ['أشغال يدوية', 'فراغ', 'تربية فنية'],
            'الثلاثاء': ['فراغ', 'رسم', 'فراغ'],
            'الأربعاء': ['تربية فنية', 'فراغ', 'معرض مصغر'],
            'الخميس': ['أشغال يدوية', 'فراغ', 'تقييم الأعمال']
        }
    },
    'celeste': {
        'password': '101',
        'name': 'المعلمة سلستي',
        'role': 'معلمة',
        'schedule': {
            'السبت': ['حاسوب', 'فراغ', 'تطبيقات مكتبية'],
            'الأحد': ['فراغ', 'حاسوب', 'فراغ'],
            'الإثنين': ['تدريب عملي', 'فراغ', 'حاسوب'],
            'الثلاثاء': ['فراغ', 'مهارات رقمية', 'فراغ'],
            'الأربعاء': ['حاسوب', 'فراغ', 'برمجة مبسطة'],
            'الخميس': ['تطبيقات', 'فراغ', 'متابعة مختبر']
        }
    },
    'eva': {
        'password': '102',
        'name': 'المعلمة إيفا',
        'role': 'معلمة',
        'schedule': {
            'السبت': ['موسيقى ونشيد', 'فراغ', 'إيقاع'],
            'الأحد': ['فراغ', 'موسيقى', 'فراغ'],
            'الإثنين': ['تدريب كورال', 'فراغ', 'موسيقى'],
            'الثلاثاء': ['فراغ', 'أنشطة موسيقية', 'فراغ'],
            'الأربعاء': ['موسيقى', 'فراغ', 'أناشيد مدرسية'],
            'الخميس': ['نشاط ترفيهي', 'فراغ', 'تقييم']
        }
    },
    'maha': {
        'password': '103',
        'name': 'المعلمة نهى',
        'role': 'معلمة',
        'schedule': {
            'السبت': ['رياض الأطفال', 'فراغ', 'ألعاب إدراكية'],
            'الأحد': ['فراغ', 'رياض الأطفال', 'فراغ'],
            'الإثنين': ['تأهيل مبكر', 'فراغ', 'رياض الأطفال'],
            'الثلاثاء': ['فراغ', 'أنشطة حركية', 'فراغ'],
            'الأربعاء': ['رياض الأطفال', 'فراغ', 'قصص أطفال'],
            'الخميس': ['أنشطة تفاعلية', 'فراغ', 'تقييم يومي']
        }
    },
    'miry': {
        'password': '104',
        'name': 'المعلمة ميري',
        'role': 'معلمة',
        'schedule': {
            'السبت': ['لغة أجنبية ثانية', 'فراغ', 'محادثة'],
            'الأحد': ['فراغ', 'لغة أجنبية', 'فراغ'],
            'الإثنين': ['تمارين لغوية', 'فراغ', 'لغة أجنبية'],
            'الثلاثاء': ['فراغ', 'استماع', 'فراغ'],
            'الأربعاء': ['لغة أجنبية', 'فراغ', 'قراءة'],
            'الخميس': ['مراجعة', 'فراغ', 'نشاط تفاعلي']
        }
    },
    'nancy': {
        'password': '105',
        'name': 'المعلمة نانسي',
        'role': 'معلمة',
        'schedule': {
            'السبت': ['صحة وسلامة', 'فراغ', 'توعية'],
            'الأحد': ['فراغ', 'تربية رياضية', 'فراغ'],
            'الإثنين': ['أنشطة صحية', 'فراغ', 'توعية غذائية'],
            'الثلاثاء': ['فراغ', 'رياضة خفيفة', 'فراغ'],
            'الأربعاء': ['تربية رياضية', 'فراغ', 'فحوصات دورية'],
            'الخميس': ['نشاط بدني', 'فراغ', 'إرشادات']
        }
    },
    'haidy': {
        'password': '106',
        'name': 'المعلمة هايدي',
        'role': 'معلمة',
        'schedule': {
            'السبت': ['مكتبة ومطالعة', 'فراغ', 'بحث علمي مبسط'],
            'الأحد': ['فراغ', 'قصص وهوايات', 'فراغ'],
            'الإثنين': ['مطالعة حرة', 'فراغ', 'أنشطة مكتبية'],
            'الثلاثاء': ['فراغ', 'تلخيص قصص', 'فراغ'],
            'الأربعاء': ['بحث وثائق', 'فراغ', 'مطالعة'],
            'الخميس': ['تقييم القراءة', 'فراغ', 'نشاط ختامي']
        }
    }
}

# متغير عام لحفظ الاجتماعات أو التعاميم الصادرة من المدير
SCHOOL_ANNOUNCEMENT = ""

LOGIN_PAGE = '''
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>تسجيل دخول - مدرسة الأمل</title>
    <style>
        body { font-family: Tahoma, sans-serif; background-color: #f4f7f6; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
        .login-card { background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); width: 100%; max-width: 400px; text-align: center; }
        h2 { color: #0275d8; margin-bottom: 10px; }
        p { color: #666; font-size: 14px; margin-bottom: 20px; }
        input { width: 100%; padding: 12px; margin: 10px 0; border: 1px solid #ddd; border-radius: 6px; box-sizing: border-box; font-size: 16px; }
        button { width: 100%; padding: 12px; background-color: #0275d8; color: white; border: none; border-radius: 6px; font-size: 16px; cursor: pointer; margin-top: 10px; }
        button:hover { background-color: #025aa5; }
        .error { color: #d9534f; margin-top: 10px; font-size: 14px; }
        .users-hint { margin-top: 20px; font-size: 12px; color: #888; text-align: right; background: #f9f9f9; padding: 10px; border-radius: 5px; }
    </style>
</head>
<body>
    <div class="login-card">
        <h2>مدرسة الأمل</h2>
        <p>تسجيل دخول الكادر التعليمي والإداري</p>
        <form method="POST">
            <input type="text" name="username" placeholder="اسم المستخدم (khader, berta, ahmad...)" required>
            <input type="password" name="password" placeholder="كلمة المرور" required>
            <button type="submit">دخول للجدول</button>
        </form>
        {% if error %}
            <div class="error">{{ error }}</div>
        {% endif %}
        <div class="users-hint">
            <strong>حسابات رئيسية:</strong> المدير khader (111) | السكرتيرة berta (222)
        </div>
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
    <title>لوحة التحكم - {{ teacher.name }}</title>
    <style>
        body { font-family: Tahoma, sans-serif; background-color: #f4f7f6; margin: 0; padding: 20px; }
        .container { max-width: 800px; margin: auto; }
        .header { background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.05); display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; flex-wrap: wrap; gap: 10px; }
        .header h2 { margin: 0; color: #333; }
        .role-badge { background: #e2e8f0; padding: 4px 10px; border-radius: 15px; font-size: 12px; color: #4a5568; margin-top: 5px; display: inline-block; }
        .nav-links { display: flex; gap: 10px; }
        .btn { padding: 8px 15px; border-radius: 5px; text-decoration: none; font-size: 14px; border: none; cursor: pointer; color: white; }
        .logout { background: #d9534f; }
        .logout:hover { background: #c9302c; }
        .admin-btn { background: #f0ad4e; }
        .admin-btn:hover { background: #ec971f; }
        .alert-box { background: #d9edf7; color: #31708f; padding: 15px; border-radius: 8px; margin-bottom: 20px; border-right: 5px solid #31708f; font-weight: bold; }
        .day-card { background: white; padding: 15px 20px; border-radius: 8px; margin-bottom: 15px; box-shadow: 0 2px 5px rgba(0,0,0,0.05); border-right: 5px solid #0275d8; }
        .day-title { font-weight: bold; color: #0275d8; margin-bottom: 10px; font-size: 18px; }
        ul { margin: 0; padding-right: 20px; color: #555; }
        li { margin-bottom: 5px; font-size: 15px; }
        .card-section { background: white; padding: 20px; border-radius: 10px; margin-bottom: 20px; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }
        input, select { padding: 10px; margin: 5px 0 15px 0; width: 100%; border: 1px solid #ddd; border-radius: 5px; box-sizing: border-box; }
        button[type="submit"] { background: #0275d8; color: white; padding: 10px; border: none; border-radius: 5px; width: 100%; font-size: 16px; cursor: pointer; }
        button[type="submit"]:hover { background: #025aa5; }
        .success-msg { color: #2b542c; background: #dff0d8; padding: 10px; border-radius: 5px; margin-bottom: 15px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div>
                <h2>أهلاً بك، {{ teacher.name }}</h2>
                <span class="role-badge">{{ teacher.role }}</span>
            </div>
            <div class="nav-links">
                {% if username == 'khader' %}
                    <a href="/manager_panel" class="btn admin-btn">لوحة تحكم المدير العامة</a>
                {% elif username == 'berta' %}
                    <a href="/secretary_panel" class="btn admin-btn">تعديل جداول المعلمين</a>
                {% endif %}
                <a href="/change_password" class="btn" style="background: #5bc0de;">تغيير كلمة السر</a>
                <a href="/logout" class="btn logout">تسجيل خروج</a>
            </div>
        </div>

        {% if announcement %}
            <div class="alert-box">
                📢 إشعار هام من إدارة المدرسة: {{ announcement }}
            </div>
        {% endif %}

        {% if msg %}
            <div class="success-msg">{{ msg }}</div>
        {% endif %}

        <h3 style="color: #444; margin-bottom: 15px;">الجدول الأسبوعي الخاص بك:</h3>

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

SECRETARY_PANEL = '''
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>لوحة السكرتيرة - تعديل الجداول</title>
    <style>
        body { font-family: Tahoma, sans-serif; background-color: #f4f7f6; margin: 0; padding: 20px; }
        .container { max-width: 600px; margin: auto; background: white; padding: 25px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.05); }
        h2 { color: #0275d8; margin-top: 0; }
        label { font-weight: bold; color: #444; display: block; margin-top: 10px; }
        select, input { width: 100%; padding: 10px; margin: 5px 0 15px 0; border: 1px solid #ddd; border-radius: 5px; box-sizing: border-box; }
        button { background: #0275d8; color: white; border: none; padding: 12px; width: 100%; border-radius: 5px; font-size: 16px; cursor: pointer; }
        button:hover { background: #025aa5; }
        .back { display: inline-block; margin-bottom: 15px; color: #555; text-decoration: none; }
        .msg { background: #dff0d8; color: #3c763d; padding: 10px; border-radius: 5px; margin-bottom: 15px; }
    </style>
</head>
<body>
    <div class="container">
        <a href="/dashboard" class="back">← عودة لوحة التحكم</a>
        <h2>لوحة السكرتيرة (بيرتا) - تعديل حصص المعلمين</h2>
        
        {% if msg %}
            <div class="msg">{{ msg }}</div>
        {% endif %}

        <form method="POST">
            <label>اختر المعلم:</label>
            <select name="target_teacher">
                {% for key, data in teachers.items() %}
                    {% if key not in ['khader', 'berta'] %}
                        <option value="{{ key }}">{{ data.name }}</option>
                    {% endif %}
                {% endfor %}
            </select>

            <label>اختر اليوم:</label>
            <select name="day">
                <option value="السبت">السبت</option>
                <option value="الأحد">الأحد</option>
                <option value="الإثنين">الإثنين</option>
                <option value="الثلاثاء">الثلاثاء</option>
                <option value="الأربعاء">الأربعاء</option>
                <option value="الخميس">الخميس</option>
            </select>

            <label>الحصص الجديدة (مفصولة بفواصل، مثل: حصة دين, فراغ, لغة عربية):</label>
            <input type="text" name="classes_str" placeholder="اكتب الحصص هنا..." required>

            <button type="submit">تحديث جدول المعلم</button>
        </form>
    </div>
</body>
</html>
'''

MANAGER_PANEL = '''
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>لوحة المدير العام</title>
    <style>
        body { font-family: Tahoma, sans-serif; background-color: #f4f7f6; margin: 0; padding: 20px; }
        .container { max-width: 600px; margin: auto; background: white; padding: 25px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.05); }
        h2 { color: #d9534f; margin-top: 0; }
        label { font-weight: bold; color: #444; display: block; margin-top: 10px; }
        textarea { width: 100%; padding: 10px; margin: 5px 0 15px 0; border: 1px solid #ddd; border-radius: 5px; box-sizing: border-box; height: 100px; }
        button { background: #d9534f; color: white; border: none; padding: 12px; width: 100%; border-radius: 5px; font-size: 16px; cursor: pointer; }
        button:hover { background: #c9302c; }
        .back { display: inline-block; margin-bottom: 15px; color: #555; text-decoration: none; }
        .msg { background: #dff0d8; color: #3c763d; padding: 10px; border-radius: 5px; margin-bottom: 15px; }
    </style>
</head>
<body>
    <div class="container">
        <a href="/dashboard" class="back">← عودة لوحة التحكم</a>
        <h2>لوحة تحكم المدير العام (خضر - الليدر)</h2>
        
        {% if msg %}
            <div class="msg">{{ msg }}</div>
        {% endif %}

        <form method="POST">
            <label>إرسال تعميم أو دعوة اجتماع لجميع المعلمين:</label>
            <textarea name="announcement" placeholder="اكتب نص الاجتماع أو التعميم ليظهر لكل الكادر..." required>{{ current_announcement }}</textarea>
            <button type="submit">نشر التعميم للجميع</button>
        </form>
    </div>
</body>
</html>
'''

CHANGE_PASS_PAGE = '''
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>تغيير كلمة المرور</title>
    <style>
        body { font-family: Tahoma, sans-serif; background-color: #f4f7f6; margin: 0; padding: 20px; }
        .container { max-width: 400px; margin: auto; background: white; padding: 25px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.05); }
        h2 { color: #0275d8; margin-top: 0; }
        label { font-weight: bold; color: #444; display: block; margin-top: 10px; }
        input { width: 100%; padding: 10px; margin: 5px 0 15px 0; border: 1px solid #ddd; border-radius: 5px; box-sizing: border-box; }
        button { background: #0275d8; color: white; border: none; padding: 12px; width: 100%; border-radius: 5px; font-size: 16px; cursor: pointer; }
        button:hover { background: #025aa5; }
        .back { display: inline-block; margin-bottom: 15px; color: #555; text-decoration: none; }
        .error { color: #d9534f; margin-bottom: 15px; }
    </style>
</head>
<body>
    <div class="container">
        <a href="/dashboard" class="back">← عودة لوحة التحكم</a>
        <h2>تغيير كلمة المرور</h2>
        
        {% if error %}
            <div class="error">{{ error }}</div>
        {% endif %}

        <form method="POST">
            <label>كلمة المرور الجديدة:</label>
            <input type="password" name="new_password" required>
            <button type="submit">حفظ كلمة المرور الجديدة</button>
        </form>
    </div>
</body>
</html>
'''

@app.route('/', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form.get('username', '').strip().lower()
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
    msg = request.args.get('msg', '')
    return render_template_string(DASHBOARD_PAGE, teacher=teacher, username=username, announcement=SCHOOL_ANNOUNCEMENT, msg=msg)

@app.route('/secretary_panel', methods=['GET', 'POST'])
def secretary_panel():
    if 'user' not in session or session['user'] != 'berta':
        return redirect(url_for('login'))
    
    msg = ""
    if request.method == 'POST':
        target = request.form.get('target_teacher')
        day = request.form.get('day')
        classes_str = request.form.get('classes_str')
        if target and day and classes_str:
            classes_list = [c.strip() for c in classes_str.split(',')]
            TEACHERS[target]['schedule'][day] = classes_list
            msg = "تم تحديث جدول المعلم بنجاح!"

    return render_template_string(SECRETARY_PANEL, teachers=TEACHERS, msg=msg)

@app.route('/manager_panel', methods=['GET', 'POST'])
def manager_panel():
    global SCHOOL_ANNOUNCEMENT
    if 'user' not in session or session['user'] != 'khader':
        return redirect(url_for('login'))
    
    msg = ""
    if request.method == 'POST':
        SCHOOL_ANNOUNCEMENT = request.form.get('announcement', '')
        msg = "تم نشر التعميم لجميع أعضاء المدرسة بنجاح!"

    return render_template_string(MANAGER_PANEL, current_announcement=SCHOOL_ANNOUNCEMENT, msg=msg)

@app.route('/change_password', methods=['GET', 'POST'])
def change_password():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    error = None
    if request.method == 'POST':
        new_pass = request.form.get('new_password')
        if new_pass:
            username = session['user']
            TEACHERS[username]['password'] = new_pass
            return redirect(url_for('dashboard', msg='تم تغيير كلمة المرور بنجاح!'))
        else:
            error = 'الرجاء إدخال كلمة مرور صحيحة.'

    return render_template_string(CHANGE_PASS_PAGE, error=error)

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
