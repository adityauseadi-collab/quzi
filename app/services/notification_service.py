"""
app/services/notification_service.py
======================================
In-app notification system.
Notifications are stored in the database and shown in the UI header.
"""
from datetime import datetime
from app.extensions import db


class Notification(db.Model):
    """Persistent in-app notification record."""
    __tablename__ = 'notifications'

    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title      = db.Column(db.String(200), nullable=False)
    body       = db.Column(db.Text, nullable=True)
    category   = db.Column(db.String(30), default='info')   # info / success / warning / danger
    is_read    = db.Column(db.Boolean, default=False)
    link       = db.Column(db.String(300), nullable=True)   # optional click-through URL
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('notifications',
                            lazy='dynamic', cascade='all, delete-orphan'))

    def __repr__(self):
        return f'<Notification {self.id} user={self.user_id} read={self.is_read}>'


class NotificationService:

    @staticmethod
    def send(user_id: int, title: str, body: str = '',
             category: str = 'info', link: str = None):
        """Create a notification for a user."""
        notif = Notification(
            user_id=user_id, title=title, body=body,
            category=category, link=link
        )
        db.session.add(notif)
        db.session.commit()
        return notif

    @staticmethod
    def send_quiz_result(user_id: int, quiz_title: str, grade: str,
                         percentage: float, result_id: int):
        """Notify a student about their quiz result."""
        emoji = '🎉' if grade in ('A+', 'A') else ('👍' if grade in ('B', 'C') else '📚')
        cat = 'success' if grade in ('A+', 'A', 'B') else ('warning' if grade == 'C' else 'danger')
        NotificationService.send(
            user_id=user_id,
            title=f'{emoji} Quiz Result: {grade} ({percentage:.1f}%)',
            body=f'You completed "{quiz_title}" and scored {percentage:.1f}% — Grade {grade}.',
            category=cat,
            link=f'/student/result/{result_id}'
        )

    @staticmethod
    def send_quiz_published(student_ids: list, quiz_title: str, quiz_id: int):
        """Notify multiple students about a newly published quiz."""
        for uid in student_ids:
            NotificationService.send(
                user_id=uid,
                title=f'📝 New Quiz Available: {quiz_title}',
                body=f'A new quiz "{quiz_title}" has been published. Take it now!',
                category='info',
                link=f'/student/quiz/{quiz_id}/start'
            )

    @staticmethod
    def get_unread(user_id: int, limit: int = 10):
        return (Notification.query
                .filter_by(user_id=user_id, is_read=False)
                .order_by(Notification.created_at.desc())
                .limit(limit).all())

    @staticmethod
    def get_all(user_id: int, limit: int = 30):
        return (Notification.query
                .filter_by(user_id=user_id)
                .order_by(Notification.created_at.desc())
                .limit(limit).all())

    @staticmethod
    def mark_read(notif_id: int, user_id: int) -> bool:
        notif = Notification.query.filter_by(id=notif_id, user_id=user_id).first()
        if notif:
            notif.is_read = True
            db.session.commit()
            return True
        return False

    @staticmethod
    def mark_all_read(user_id: int):
        (Notification.query
         .filter_by(user_id=user_id, is_read=False)
         .update({'is_read': True}))
        db.session.commit()

    @staticmethod
    def unread_count(user_id: int) -> int:
        return Notification.query.filter_by(user_id=user_id, is_read=False).count()

    @staticmethod
    def delete(notif_id: int, user_id: int) -> bool:
        notif = Notification.query.filter_by(id=notif_id, user_id=user_id).first()
        if notif:
            db.session.delete(notif)
            db.session.commit()
            return True
        return False
