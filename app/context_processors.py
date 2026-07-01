"""
app/context_processors.py
==========================
Flask context processors inject variables into every template automatically.
"""
from flask_login import current_user


def inject_notifications():
    """Make unread notification count available in all authenticated templates."""
    if current_user.is_authenticated:
        try:
            from app.services.notification_service import NotificationService
            count = NotificationService.unread_count(current_user.id)
            recent = NotificationService.get_unread(current_user.id, limit=5)
            return {
                'notif_count': count,
                'recent_notifs': recent,
            }
        except Exception:
            pass
    return {'notif_count': 0, 'recent_notifs': []}


def inject_globals():
    """Inject miscellaneous global template variables."""
    from datetime import datetime
    return {
        'app_name': 'QuizMaster Pro',
        'app_version': '1.0',
        'current_year': datetime.utcnow().year,
    }


def register_context_processors(app):
    """Register all context processors with the Flask app."""
    app.context_processor(inject_notifications)
    app.context_processor(inject_globals)
