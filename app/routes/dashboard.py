from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import delete, select
from sqlalchemy.orm import Session, joinedload

from app.database.session import get_db
from app.models.customer import Customer
from app.models.operation_log import OperationLog
from app.routes.common import current_user_or_redirect
from app.services.customers import user_summary


router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


def dashboard_context(db: Session, user):
    customers = list(db.scalars(select(Customer).where(Customer.owner_id == user.id).order_by(Customer.created_at.desc())))
    operations = list(
        db.scalars(
            select(OperationLog)
            .options(joinedload(OperationLog.customer))
            .where(OperationLog.user_id == user.id)
            .order_by(OperationLog.created_at.desc())
            .limit(20)
        )
    )
    summary = user_summary(db, user)
    return {
        "summary": summary,
        "customers": customers,
        "operations": operations,
        "dashboard_user": user,
    }


@router.get("/dashboard")
def dashboard(request: Request, db: Session = Depends(get_db)):
    user = current_user_or_redirect(request, db)
    if isinstance(user, RedirectResponse):
        return user
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={"current_user": user, **dashboard_context(db, user)},
    )


@router.post("/dashboard/clear-log")
def clear_dashboard_log(request: Request, db: Session = Depends(get_db)):
    user = current_user_or_redirect(request, db)
    if isinstance(user, RedirectResponse):
        return user
    db.execute(delete(OperationLog).where(OperationLog.user_id == user.id))
    db.commit()
    return RedirectResponse(url="/dashboard", status_code=303)
