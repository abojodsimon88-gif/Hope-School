from flask import Flask, render_template_string, request, session, redirect, url_for

app = Flask(__name__)
app.secret_key = 'hope_school_secret_key_123'

# قاعدة بيانات المعلمين والإدارة والموظفين
TEACHERS = {
    # الإدارة
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
    
    # المعلمون
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
            'الإثنين': ['صصف أول', 'فراغ', 'تربية إسلامية'],
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

    # المعلمات
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
    'maha': {  # نهى
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
            <input type="text" name="username" placeholder="اسم المستخدم (مثال: khader, berta, ahmad...)" required>
            <input type="password" name="password" placeholder="كلمة المرور" required>
            <button type="submit">دخول للجدول</button>
        </form>
        {% if error %}
            <div class="error">{{ error }}</div>
        {% endif %}
        <div class="users-hint">
            <strong>أمثلة للحسابات:</strong><br>
            - المدير: khader (كلمة المرور: 111)<br>
            - السكرتيرة: berta (كلمة المرور: 222)<br>
            - المعلمون: ahmad, nizar, fouad, andres, waleed<br>
            - المعلمات: doaa, khawla, nour, celeste, eva, maha, miry, nancy, haidy
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
        .header { background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.05); display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
        .header h2 { margin: 0; color: #333; }
        .role-badge { background: #e2e8f0; padding: 4px 10px; border-radius: 15px; font-size: 12px; color: #4a5568; margin-top: 5px; display: inline-block; }
        .logout { background: #d9534f; color: white; padding: 8px 15px; border-radius: 5px; text-decoration: none; font-size: 14px; }
        .logout:hover { background: #c9302c; }
        .day-card { background: white; padding: 15px 20px; border-radius: 8px; margin-bottom: 15px; box-shadow: 0 2px 5px rgba(0,0,0,0.05); border-right: 5px solid #0275d8; }
        .day-title { font-weight: bold; color: #0275d8; margin-bottom: 10px; font-size: 18px; }
        ul { margin: 0; padding-right: 20px; color: #555; }
        li { margin-bottom: 5px; font-size: 15px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div>
                <h2>أهلاً بك، {{ teacher.name }}</h2>
                <span class="role-badge">{{ teacher.role }}</span>
            </div>
            <a href="/logout" class="logout">تسجيل خروج</a>
        </div>

        <h3 style="color: #444; margin-bottom: 15px;">الجدول الأسبوعي:</h3>

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

@app.route('/', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.username.strip().lower() if hasattr(request, 'username') else request.form.get('username', '').strip().lower()
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
    return render_template_string(DASHBOARD_PAGE, teacher=teacher)

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
