from fastapi import Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.models.user import User


def current_user_or_redirect(request: Request, db: Session) -> User | RedirectResponse:
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(url="/login", status_code=303)
    user = db.get(User, user_id)
    if not user:
        request.session.clear()
        return RedirectResponse(url="/login", status_code=303)
    if user.role != "admin" and not user.is_active:
        request.session.clear()
        return RedirectResponse(url="/login?inactive=1", status_code=303)
    return user


def admin_or_redirect(request: Request, db: Session) -> User | RedirectResponse:
    user = current_user_or_redirect(request, db)
    if isinstance(user, RedirectResponse):
        return user
    if user.role != "admin":
        return RedirectResponse(url="/dashboard", status_code=303)
    return user
