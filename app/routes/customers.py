from urllib.parse import quote

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import delete, select
from sqlalchemy.orm import Session, joinedload

from app.database.session import get_db
from app.models.operation_log import OperationLog
from app.routes.common import current_user_or_redirect
from app.services.customers import (
    add_transfer,
    create_customer,
    get_customer_for_user,
    parse_amount,
    receive_payment,
    search_customers_for_user,
)


router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.post("/customers")
def store_customer(request: Request, customer_name: str = Form(""), db: Session = Depends(get_db)):
    user = current_user_or_redirect(request, db)
    if isinstance(user, RedirectResponse):
        return user
    try:
        customer = create_customer(db, user, customer_name)
        db.commit()
    except HTTPException:
        db.rollback()
        return RedirectResponse(url="/dashboard", status_code=303)
    return RedirectResponse(url=f"/customers/{customer.id}", status_code=303)


@router.get("/customers/search")
def search_customers(request: Request, q: str = "", db: Session = Depends(get_db)):
    user = current_user_or_redirect(request, db)
    if isinstance(user, RedirectResponse):
        return JSONResponse({"customers": []}, status_code=401)
    customers = search_customers_for_user(db, user, q)
    return {
        "customers": [
            {
                "id": customer.id,
                "customer_name": customer.customer_name,
            }
            for customer in customers
        ]
    }


@router.get("/customers/{customer_id}")
def customer_page(request: Request, customer_id: int, db: Session = Depends(get_db)):
    user = current_user_or_redirect(request, db)
    if isinstance(user, RedirectResponse):
        return user
    customer = get_customer_for_user(db, customer_id, user)
    operations = list(
        db.scalars(
            select(OperationLog)
            .options(joinedload(OperationLog.customer))
            .where(OperationLog.customer_id == customer.id)
            .order_by(OperationLog.created_at.desc())
        )
    )
    return templates.TemplateResponse(
        "customer_detail.html",
        {"request": request, "current_user": user, "customer": customer, "operations": operations, "error": request.query_params.get("error")},
    )


@router.post("/customers/{customer_id}/transfer")
def customer_transfer(request: Request, customer_id: int, amount: str = Form(""), db: Session = Depends(get_db)):
    user = current_user_or_redirect(request, db)
    if isinstance(user, RedirectResponse):
        return user
    customer = get_customer_for_user(db, customer_id, user)
    try:
        add_transfer(db, customer, user, parse_amount(amount))
        db.commit()
    except HTTPException as error:
        db.rollback()
        return RedirectResponse(url=f"/customers/{customer.id}?error={quote(error.detail)}", status_code=303)
    return RedirectResponse(url=f"/customers/{customer.id}", status_code=303)


@router.post("/customers/{customer_id}/payment")
def customer_payment(request: Request, customer_id: int, amount: str = Form(""), db: Session = Depends(get_db)):
    user = current_user_or_redirect(request, db)
    if isinstance(user, RedirectResponse):
        return user
    customer = get_customer_for_user(db, customer_id, user)
    try:
        receive_payment(db, customer, user, parse_amount(amount))
        db.commit()
    except HTTPException as error:
        db.rollback()
        return RedirectResponse(url=f"/customers/{customer.id}?error={quote(error.detail)}", status_code=303)
    return RedirectResponse(url=f"/customers/{customer.id}", status_code=303)


@router.post("/customers/{customer_id}/clear-log")
def clear_customer_log(request: Request, customer_id: int, db: Session = Depends(get_db)):
    user = current_user_or_redirect(request, db)
    if isinstance(user, RedirectResponse):
        return user
    customer = get_customer_for_user(db, customer_id, user)
    db.execute(delete(OperationLog).where(OperationLog.customer_id == customer.id))
    db.commit()
    return RedirectResponse(url=f"/customers/{customer.id}", status_code=303)
