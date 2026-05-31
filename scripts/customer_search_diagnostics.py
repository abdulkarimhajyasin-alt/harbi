from os import getenv
from pathlib import Path
import sys

from sqlalchemy import exists, func, select

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app.models  # noqa: F401
from app.database.session import SessionLocal
from app.models.customer import Customer
from app.models.operation_log import OperationLog
from app.models.user import User
from app.services.customers import search_customers_for_user, visible_customers_for_user


def main() -> None:
    username = (getenv("CUSTOMER_REPAIR_USERNAME") or "").strip()
    sample_query = (getenv("CUSTOMER_SEARCH_QUERY") or "").strip()
    apply_repair = getenv("CUSTOMER_REPAIR_APPLY") == "1"

    if not username:
        print("Set CUSTOMER_REPAIR_USERNAME to the exact username before running.")
        return

    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.username == username))
        if not user:
            print(f"User not found: {username}")
            return

        owner_count = db.scalar(select(func.count(Customer.id)).where(Customer.owner_id == user.id)) or 0
        visible_customers = visible_customers_for_user(db, user)
        search_count = len(search_customers_for_user(db, user, sample_query)) if sample_query else 0

        owner_exists = exists(select(User.id).where(User.id == Customer.owner_id))
        legacy_user_count = (
            select(func.count(func.distinct(OperationLog.user_id)))
            .where(OperationLog.customer_id == Customer.id)
            .scalar_subquery()
        )
        legacy_candidates = list(
            db.scalars(
                select(Customer)
                .where(
                    ((Customer.owner_id.is_(None)) | (~owner_exists)),
                    legacy_user_count == 1,
                    exists(
                        select(OperationLog.id).where(
                            OperationLog.customer_id == Customer.id,
                            OperationLog.user_id == user.id,
                        )
                    ),
                )
                .order_by(Customer.id.asc())
            )
        )

        print(f"user id: {user.id}")
        print(f"username: {user.username}")
        print(f"customer count by owner_id: {owner_count}")
        print(f"total visible customers through dashboard query: {len(visible_customers)}")
        print(f"search result count for sample query: {search_count}")
        print(f"legacy repair candidates: {len(legacy_candidates)}")

        for customer in legacy_candidates:
            print(f"candidate customer id={customer.id} name={customer.customer_name} current_owner_id={customer.owner_id}")

        if not legacy_candidates:
            return

        if not apply_repair:
            print("Dry run only. Set CUSTOMER_REPAIR_APPLY=1 to assign these candidates to this username.")
            return

        for customer in legacy_candidates:
            customer.owner_id = user.id
        db.commit()
        print(f"Updated owner_id for {len(legacy_candidates)} customers. Balances and operation logs were not changed.")


if __name__ == "__main__":
    main()
