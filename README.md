# جرد حساباتي

تطبيق ويب محلي مبني باستخدام FastAPI و PostgreSQL و SQLAlchemy و Jinja2.

## التشغيل المحلي

1. إنشاء قاعدة PostgreSQL محلية.
2. نسخ `.env.example` إلى `.env` وتعديل القيم المحلية.
3. تثبيت الحزم:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

4. إنشاء الجداول:

```powershell
python -m app.database.init_db
```

5. إنشاء حساب مدير:

```powershell
python -m app.database.create_admin
```

6. تشغيل التطبيق محليا:

```powershell
python -m uvicorn app.main:app --reload
```

ثم فتح:

```text
http://127.0.0.1:8000
```

## المتغيرات

```text
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:5432/DATABASE
SESSION_SECRET_KEY=replace-with-a-long-random-secret
APP_NAME=جرد حساباتي
ADMIN_NAME=المدير
ADMIN_USERNAME=admin
ADMIN_PASSWORD=replace-with-a-strong-password
```

## النشر على Render

1. إنشاء قاعدة بيانات PostgreSQL على Render.
2. إنشاء Web Service من مستودع GitHub.
3. ضبط Build Command:

```text
pip install -r requirements.txt
```

4. ضبط Start Command:

```text
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

5. إضافة المتغيرات:

```text
DATABASE_URL=<Render PostgreSQL External Database URL أو Internal Database URL>
SESSION_SECRET_KEY=<قيمة طويلة عشوائية>
APP_NAME=جرد حساباتي
ADMIN_NAME=<اسم المدير>
ADMIN_USERNAME=<اسم مستخدم المدير>
ADMIN_PASSWORD=<كلمة مرور قوية>
```

6. بعد أول نشر، تشغيل أمر إنشاء الجداول مرة واحدة من Render Shell:

```bash
python -m app.database.init_db
```

7. إنشاء حساب المدير من Render Shell:

```bash
python -m app.database.create_admin
```

8. فحص الصحة:

```text
/health
```

## التحقق

```powershell
python -m compileall app
node --check app\static\js\app.js
```
