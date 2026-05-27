from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.notification import Notification


def create_notification(db: Session, title: str, body: str, type_: str) -> Notification:
    notification = Notification(title=title, body=body, type=type_)
    db.add(notification)
    return notification


def unread_count(db: Session) -> int:
    return db.scalar(select(func.count(Notification.id)).where(Notification.is_read.is_(False))) or 0


def latest_notifications(db: Session, limit: int = 8) -> list[Notification]:
    return list(db.scalars(select(Notification).order_by(Notification.created_at.desc()).limit(limit)))


def all_notifications(db: Session) -> list[Notification]:
    return list(db.scalars(select(Notification).order_by(Notification.created_at.desc())))


def mark_notification_read(db: Session, notification_id: int) -> None:
    notification = db.get(Notification, notification_id)
    if notification:
        notification.is_read = True


def mark_all_notifications_read(db: Session) -> None:
    for notification in db.scalars(select(Notification).where(Notification.is_read.is_(False))):
        notification.is_read = True
