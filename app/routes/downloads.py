from urllib.parse import quote

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.routes.common import current_user_or_redirect
from app.services.customers import parse_amount
from app.services.downloads import create_download_operation, list_download_operations


router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/downloads")
def downloads_page(request: Request, db: Session = Depends(get_db)):
    user = current_user_or_redirect(request, db)
    if isinstance(user, RedirectResponse):
        return user
    return templates.TemplateResponse(
        "downloads.html",
        {
            "request": request,
            "current_user": user,
            "operations": list_download_operations(db, user),
            "error": request.query_params.get("error"),
        },
    )


@router.post("/downloads/download")
def store_download(request: Request, amount: str = Form(""), db: Session = Depends(get_db)):
    user = current_user_or_redirect(request, db)
    if isinstance(user, RedirectResponse):
        return user
    try:
        create_download_operation(db, user, "download", parse_amount(amount))
        db.commit()
    except HTTPException as error:
        db.rollback()
        return RedirectResponse(url=f"/downloads?error={quote(error.detail)}", status_code=303)
    return RedirectResponse(url="/downloads", status_code=303)


@router.post("/downloads/return")
def store_return(request: Request, amount: str = Form(""), db: Session = Depends(get_db)):
    user = current_user_or_redirect(request, db)
    if isinstance(user, RedirectResponse):
        return user
    try:
        create_download_operation(db, user, "return", parse_amount(amount))
        db.commit()
    except HTTPException as error:
        db.rollback()
        return RedirectResponse(url=f"/downloads?error={quote(error.detail)}", status_code=303)
    return RedirectResponse(url="/downloads", status_code=303)
