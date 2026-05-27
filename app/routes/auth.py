from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.passwords import PasswordValidationError, hash_password, validate_password_length
from app.database.session import get_db
from app.models.user import User
from app.routes.common import current_user_or_redirect
from app.services.users import authenticate_user, create_user, find_by_username


router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/login")
def login_page(request: Request):
    if request.session.get("user_id"):
        return RedirectResponse(url="/dashboard", status_code=303)
    inactive = request.query_params.get("inactive") == "1"
    return templates.TemplateResponse("auth/login.html", {"request": request, "error": None, "inactive": inactive})


@router.post("/login")
def login(request: Request, username: str = Form(""), password: str = Form(""), db: Session = Depends(get_db)):
    try:
        user = authenticate_user(db, username, password)
    except PasswordValidationError as error:
        return templates.TemplateResponse(
            "auth/login.html",
            {"request": request, "error": str(error), "inactive": False},
            status_code=400,
        )
    if not user:
        return templates.TemplateResponse(
            "auth/login.html",
            {"request": request, "error": "بيانات الدخول غير صحيحة", "inactive": False},
            status_code=400,
        )
    if user.role == "admin":
        request.session["user_id"] = user.id
        return RedirectResponse(url="/admin", status_code=303)
    if not user.is_active:
        request.session.clear()
        return RedirectResponse(url="/login?inactive=1", status_code=303)
    request.session["user_id"] = user.id
    return RedirectResponse(url="/dashboard", status_code=303)


@router.get("/register")
def register_page(request: Request):
    if request.session.get("user_id"):
        return RedirectResponse(url="/dashboard", status_code=303)
    return templates.TemplateResponse("auth/register.html", {"request": request, "error": None})


@router.post("/register")
def register(
    request: Request,
    name: str = Form(""),
    username: str = Form(""),
    password: str = Form(""),
    db: Session = Depends(get_db),
):
    if not name.strip() or not username.strip() or len(password) < 6:
        return templates.TemplateResponse("auth/register.html", {"request": request, "error": "يرجى إدخال بيانات صحيحة"}, status_code=400)
    try:
        validate_password_length(password)
    except PasswordValidationError as error:
        return templates.TemplateResponse("auth/register.html", {"request": request, "error": str(error)}, status_code=400)
    if find_by_username(db, username):
        return templates.TemplateResponse("auth/register.html", {"request": request, "error": "اسم المستخدم موجود مسبقا"}, status_code=400)
    user = create_user(db, name=name, username=username, password=password)
    db.commit()
    return RedirectResponse(url="/login?inactive=1", status_code=303)


@router.post("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=303)


@router.get("/account")
def account_page(request: Request, db: Session = Depends(get_db)):
    user = current_user_or_redirect(request, db)
    if isinstance(user, RedirectResponse):
        return user
    if user.role == "admin":
        return RedirectResponse(url="/admin/account", status_code=303)
    return templates.TemplateResponse(
        "account.html",
        {
            "request": request,
            "current_user": user,
            "username": user.username,
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
    user = current_user_or_redirect(request, db)
    if isinstance(user, RedirectResponse):
        return user
    if user.role == "admin":
        return RedirectResponse(url="/admin/account", status_code=303)

    username = username.strip().lower()
    error = None
    if not username:
        error = "اسم المستخدم مطلوب"
    else:
        existing_user = db.scalar(select(User).where(User.username == username, User.id != user.id))
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
            "account.html",
            {
                "request": request,
                "current_user": user,
                "username": username,
                "error": error,
                "success": False,
            },
            status_code=400,
        )

    user.username = username
    if password_change_requested:
        user.password_hash = hash_password(password)
    request.session["user_id"] = user.id
    db.commit()
    return RedirectResponse(url="/account?saved=1", status_code=303)
