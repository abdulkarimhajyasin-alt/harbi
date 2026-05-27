from getpass import getpass
from os import getenv

from app.auth.passwords import PasswordValidationError, validate_password_length
from app.database.session import SessionLocal
from app.services.users import create_user, find_by_username


def main() -> None:
    name = getenv("ADMIN_NAME") or input("الاسم: ")
    username = getenv("ADMIN_USERNAME") or input("اسم المستخدم: ")
    password = getenv("ADMIN_PASSWORD") or getpass("كلمة المرور: ")
    name = name.strip()
    username = username.strip()
    if not name or not username or len(password) < 6:
        print("يرجى إدخال بيانات صحيحة")
        return
    try:
        validate_password_length(password)
    except PasswordValidationError as error:
        print(str(error))
        return
    with SessionLocal() as db:
        if find_by_username(db, username):
            print("اسم المستخدم موجود مسبقا")
            return
        create_user(db, name=name, username=username, password=password, role="admin")
        db.commit()
        print("تم إنشاء حساب المدير")


if __name__ == "__main__":
    main()
