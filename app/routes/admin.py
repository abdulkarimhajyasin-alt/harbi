from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.auth.passwords import PasswordValidationError, hash_password, validate_password_length
from app.database.session import get_db
from app.models.customer import Customer
from app.models.download_operation import DownloadOperation
from app.models.operation_log import OperationLog
from app.models.user import User
from app.routes.common import admin_or_redirect
from app.routes.dashboard import dashboard_context
from app.services.customers import user_summary
from app.services.notifications import (
    all_notifications,
    latest_notifications,
    mark_all_notifications_read,
    mark_notification_read,
    unread_count,
)


router = APIRouter(prefix="/admin")
templates = Jinja2Templates(directory="app/templates")


@router.get("")
def admin_dashboard(request: Request, db: Session = Depends(get_db)):
    admin = admin_or_redirect(request, db)
    if isinstance(admin, RedirectResponse):
        return admin
    users = list(db.scalars(select(User).order_by(User.created_at.desc()).limit(8)))
    return templates.TemplateResponse(
        "admin/dashboard.html",
        {
            "request": request,
            "current_user": admin,
            "users": users,
            "notifications": latest_notifications(db),
            "unread_count": unread_count(db),
        },
    )


@router.get("/users")
def users_page(request: Request, db: Session = Depends(get_db)):
    admin = admin_or_redirect(request, db)
    if isinstance(admin, RedirectResponse):
        return admin
    users = list(db.scalars(select(User).order_by(User.created_at.desc())))
    return templates.TemplateResponse("admin/users.html", {"request": request, "current_user": admin, "users": users})


@router.get("/account")
def account_page(request: Request, db: Session = Depends(get_db)):
    admin = admin_or_redirect(request, db)
    if isinstance(admin, RedirectResponse):
        return admin
    return templates.TemplateResponse(
        "admin/account.html",
        {
            "request": request,
            "current_user": admin,
            "username": admin.username,
            "error": None,
            "success": request.query_params.get("saved") == "1",
        },
    )


@router.post("/account")
def update_account(
    request: Request,
    username: str = Form(""),
    password: str = Form(""),
    confirm_password: str = Form(""),
    db: Session = Depends(get_db),
):
    admin = admin_or_redirect(request, db)
    if isinstance(admin, RedirectResponse):
        return admin

    username = username.strip().lower()
    error = None
    if not username:
        error = "اسم المستخدم مطلوب"
    else:
        existing_user = db.scalar(select(User).where(User.username == username, User.id != admin.id))
        if existing_user:
            error = "اسم المستخدم مستخدم بالفعل"

    password_change_requested = bool(password) or bool(confirm_password)
    if not error and password_change_requested:
        if password != confirm_password:
            error = "كلمتا المرور غير متطابقتين"
        else:
            try:
                validate_password_length(password)
            except PasswordValidationError:
                error = "كلمة المرور طويلة جدا"

    if error:
        return templates.TemplateResponse(
            "admin/account.html",
            {
                "request": request,
                "current_user": admin,
                "username": username,
                "error": error,
                "success": False,
            },
            status_code=400,
        )

    admin.username = username
    if password_change_requested:
        admin.password_hash = hash_password(password)
    db.commit()
    return RedirectResponse(url="/admin/account?saved=1", status_code=303)


@router.post("/users/{user_id}/activation")
def toggle_user_activation(request: Request, user_id: int, db: Session = Depends(get_db)):
    admin = admin_or_redirect(request, db)
    if isinstance(admin, RedirectResponse):
        return admin
    selected_user = db.get(User, user_id)
    if not selected_user:
        return RedirectResponse(url="/admin/users", status_code=303)
    if selected_user.id == admin.id or selected_user.role == "admin":
        selected_user.is_active = True
        db.commit()
        return RedirectResponse(url="/admin/users", status_code=303)
    selected_user.is_active = not selected_user.is_active
    db.commit()
    return RedirectResponse(url="/admin/users", status_code=303)


@router.post("/users/{user_id}/delete")
def delete_user(request: Request, user_id: int, db: Session = Depends(get_db)):
    admin = admin_or_redirect(request, db)
    if isinstance(admin, RedirectResponse):
        return admin
    selected_user = db.get(User, user_id)
    if not selected_user or selected_user.id == admin.id or selected_user.role == "admin":
        return RedirectResponse(url="/admin/users", status_code=303)
    customer_ids = select(Customer.id).where(Customer.owner_id == selected_user.id)
    db.execute(
        delete(OperationLog).where(
            (OperationLog.user_id == selected_user.id) | (OperationLog.customer_id.in_(customer_ids))
        )
    )
    db.execute(delete(DownloadOperation).where(DownloadOperation.user_id == selected_user.id))
    db.execute(delete(Customer).where(Customer.owner_id == selected_user.id))
    db.delete(selected_user)
    db.commit()
    return RedirectResponse(url="/admin/users", status_code=303)


@router.get("/notifications")
def notifications_page(request: Request, db: Session = Depends(get_db)):
    admin = admin_or_redirect(request, db)
    if isinstance(admin, RedirectResponse):
        return admin
    return templates.TemplateResponse(
        "admin/notifications.html",
        {
            "request": request,
            "current_user": admin,
            "notifications": all_notifications(db),
            "unread_count": unread_count(db),
        },
    )


@router.post("/notifications/{notification_id}/read")
def read_notification(request: Request, notification_id: int, db: Session = Depends(get_db)):
    admin = admin_or_redirect(request, db)
    if isinstance(admin, RedirectResponse):
        return admin
    mark_notification_read(db, notification_id)
    db.commit()
    return RedirectResponse(url="/admin/notifications", status_code=303)


@router.post("/notifications/read-all")
def read_all_notifications(request: Request, db: Session = Depends(get_db)):
    admin = admin_or_redirect(request, db)
    if isinstance(admin, RedirectResponse):
        return admin
    mark_all_notifications_read(db)
    db.commit()
    return RedirectResponse(url="/admin/notifications", status_code=303)


@router.get("/users/{user_id}")
def user_detail(request: Request, user_id: int, db: Session = Depends(get_db)):
    admin = admin_or_redirect(request, db)
    if isinstance(admin, RedirectResponse):
        return admin
    selected_user = db.get(User, user_id)
    if not selected_user:
        return RedirectResponse(url="/admin/users", status_code=303)
    return templates.TemplateResponse(
        "admin/user_detail.html",
        {
            "request": request,
            "current_user": admin,
            "selected_user": selected_user,
            "selected_summary": user_summary(db, selected_user),
            **dashboard_context(db, selected_user),
        },
    )
