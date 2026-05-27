from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.passwords import hash_password, verify_password
from app.models.user import User
from app.services.notifications import create_notification


def create_user(db: Session, name: str, username: str, password: str, role: str = "user") -> User:
    user = User(
        name=name.strip(),
        username=username.strip().lower(),
        password_hash=hash_password(password),
        role=role,
        is_active=role == "admin",
    )
    db.add(user)
    db.flush()
    create_notification(db, "حساب جديد", f"تم إنشاء حساب باسم {user.name}", "new_account")
    return user


def find_by_username(db: Session, username: str) -> User | None:
    return db.scalar(select(User).where(User.username == username.strip().lower()))


def authenticate_user(db: Session, username: str, password: str) -> User | None:
    user = find_by_username(db, username)
    if not user:
        return None
    if verify_password(password, user.password_hash):
        return user
    return None
