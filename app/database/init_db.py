from sqlalchemy import inspect, text

import app.models  # noqa: F401
from app.database.base import Base
from app.database.session import engine


def upgrade_local_schema() -> None:
    inspector = inspect(engine)
    if "users" in inspector.get_table_names():
        user_columns = {column["name"] for column in inspector.get_columns("users")}
        if "download_balance" not in user_columns:
            with engine.begin() as connection:
                connection.execute(text("ALTER TABLE users ADD COLUMN download_balance NUMERIC(12, 2) DEFAULT 0 NOT NULL"))
        if "is_active" not in user_columns:
            with engine.begin() as connection:
                connection.execute(text("ALTER TABLE users ADD COLUMN is_active BOOLEAN DEFAULT TRUE NOT NULL"))
                connection.execute(text("UPDATE users SET is_active = TRUE WHERE role = 'admin'"))
        else:
            with engine.begin() as connection:
                connection.execute(text("UPDATE users SET is_active = TRUE WHERE role = 'admin'"))

    if "operation_logs" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("operation_logs")}
    if "balance_after" in columns:
        return

    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE operation_logs ADD COLUMN balance_after NUMERIC(12, 2)"))
        connection.execute(
            text(
                """
                UPDATE operation_logs AS target
                SET balance_after = totals.balance_after
                FROM (
                    SELECT
                        id,
                        SUM(
                            CASE
                                WHEN operation_type = 'transfer' THEN amount
                                ELSE amount * -1
                            END
                        ) OVER (
                            PARTITION BY customer_id
                            ORDER BY created_at, id
                            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                        ) AS balance_after
                    FROM operation_logs
                ) AS totals
                WHERE target.id = totals.id
                """
            )
        )
        connection.execute(text("UPDATE operation_logs SET balance_after = 0 WHERE balance_after IS NULL"))
        connection.execute(text("ALTER TABLE operation_logs ALTER COLUMN balance_after SET NOT NULL"))


def main() -> None:
    Base.metadata.create_all(bind=engine)
    upgrade_local_schema()
    print("تم إنشاء الجداول المحلية")


if __name__ == "__main__":
    main()
