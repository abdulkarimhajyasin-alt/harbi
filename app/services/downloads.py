from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.download_operation import DownloadOperation
from app.models.user import User


def download_balance(user: User) -> Decimal:
    return user.download_balance or Decimal("0.00")


def list_download_operations(db: Session, user: User) -> list[DownloadOperation]:
    return list(
        db.scalars(
            select(DownloadOperation)
            .where(DownloadOperation.user_id == user.id)
            .order_by(DownloadOperation.created_at.desc())
        )
    )


def create_download_operation(db: Session, user: User, operation_type: str, amount: Decimal) -> DownloadOperation:
    balance = download_balance(user)
    if operation_type == "download":
        balance -= amount
    else:
        balance += amount

    user.download_balance = balance
    operation = DownloadOperation(
        user_id=user.id,
        operation_type=operation_type,
        amount=amount,
        balance_after=balance,
    )
    db.add(operation)
    return operation
