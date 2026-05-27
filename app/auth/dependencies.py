from fastapi import Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.user import User


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    user = db.get(User, user_id)
    if not user:
        request.session.clear()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    if user.role != "admin" and not user.is_active:
        request.session.clear()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    return user


def require_user(request: Request, db: Session = Depends(get_db)) -> User | RedirectResponse:
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


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    return current_user
