from decimal import Decimal, InvalidOperation

from fastapi import HTTPException, status
from sqlalchemy import exists, func, or_, select
from sqlalchemy.orm import Session

from app.models.customer import Customer
from app.models.operation_log import OperationLog
from app.models.user import User
from app.services.downloads import create_download_operation
from app.services.notifications import create_notification


def parse_amount(value: str) -> Decimal:
    try:
        amount = Decimal(value)
    except (InvalidOperation, TypeError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="قيمة غير صالحة") from None
    if amount <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="يجب أن يكون المبلغ أكبر من صفر")
    return amount.quantize(Decimal("0.01"))


def create_customer(db: Session, owner: User, customer_name: str) -> Customer:
    if not customer_name.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="اسم الزبون مطلوب")
    customer = Customer(owner_id=owner.id, customer_name=customer_name.strip(), total_due=Decimal("0.00"))
    db.add(customer)
    db.flush()
    create_notification(db, "زبون جديد", f"تمت إضافة الزبون {customer.customer_name}", "customer_added")
    return customer


def visible_customer_filter(user: User):
    legacy_operation_link = exists(
        select(OperationLog.id).where(
            OperationLog.customer_id == Customer.id,
            OperationLog.user_id == user.id,
        )
    )
    legacy_user_count = (
        select(func.count(func.distinct(OperationLog.user_id)))
        .where(OperationLog.customer_id == Customer.id)
        .scalar_subquery()
    )
    owner_exists = exists(select(User.id).where(User.id == Customer.owner_id))
    legacy_owner_missing = Customer.owner_id.is_(None) | ~owner_exists
    legacy_owned_by_user = legacy_operation_link & (legacy_user_count == 1)
    return or_(
        Customer.owner_id == user.id,
        legacy_owner_missing & legacy_owned_by_user,
    )


def visible_customers_for_user(db: Session, user: User) -> list[Customer]:
    return list(
        db.scalars(
            select(Customer)
            .where(visible_customer_filter(user))
            .order_by(Customer.created_at.desc())
        )
    )


def get_customer_for_user(db: Session, customer_id: int, user: User) -> Customer:
    customer = db.get(Customer, customer_id)
    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="الزبون غير موجود")
    if user.role != "admin" and not db.scalar(
        select(visible_customer_filter(user)).where(Customer.id == customer.id)
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="غير مصرح")
    return customer


def search_customers_for_user(db: Session, user: User, query: str, limit: int = 10) -> list[Customer]:
    term = query.strip()
    if not term:
        return []
    escaped_term = term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return list(
        db.scalars(
            select(Customer)
            .where(
                visible_customer_filter(user),
                Customer.customer_name.ilike(f"%{escaped_term}%", escape="\\"),
            )
            .order_by(Customer.customer_name.asc())
            .limit(limit)
        )
    )


def add_transfer(db: Session, customer: Customer, user: User, amount: Decimal) -> OperationLog:
    customer.total_due += amount
    create_download_operation(db, user, "transfer", amount)
    log = OperationLog(
        customer_id=customer.id,
        user_id=user.id,
        operation_type="transfer",
        amount=amount,
        balance_after=customer.total_due,
    )
    db.add(log)
    create_notification(db, "حوالة جديدة", f"تمت إضافة حوالة للزبون {customer.customer_name}", "transfer_added")
    return log


def receive_payment(db: Session, customer: Customer, user: User, amount: Decimal) -> OperationLog:
    if customer.total_due - amount < 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="المبلغ المستلم أكبر من المبلغ المتبقي")
    customer.total_due -= amount
    log = OperationLog(
        customer_id=customer.id,
        user_id=user.id,
        operation_type="payment",
        amount=amount,
        balance_after=customer.total_due,
    )
    db.add(log)
    create_notification(db, "دفعة مستلمة", f"تم تسجيل دفعة من الزبون {customer.customer_name}", "payment_received")
    return log


def user_summary(db: Session, user: User) -> dict[str, Decimal | int]:
    customer_count = db.scalar(select(func.count(Customer.id)).where(visible_customer_filter(user))) or 0
    operation_count = db.scalar(select(func.count(OperationLog.id)).where(OperationLog.user_id == user.id)) or 0
    total_due = db.scalar(select(func.coalesce(func.sum(Customer.total_due), 0)).where(visible_customer_filter(user)))
    transfer_total = db.scalar(
        select(func.coalesce(func.sum(OperationLog.amount), 0)).where(
            OperationLog.user_id == user.id,
            OperationLog.operation_type == "transfer",
        )
    )
    return {
        "customer_count": customer_count,
        "operation_count": operation_count,
        "total_due": total_due or Decimal("0.00"),
        "transfer_total": transfer_total or Decimal("0.00"),
        "download_balance": user.download_balance or Decimal("0.00"),
    }
