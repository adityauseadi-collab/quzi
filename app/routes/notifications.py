"""
app/routes/notifications.py
============================
Routes for the in-app notification bell and mark-read actions.
"""
from flask import Blueprint, jsonify, redirect, url_for, request
from flask_login import login_required, current_user
from app.services.notification_service import NotificationService

notif_bp = Blueprint('notifications', __name__, url_prefix='/notifications')


@notif_bp.route('/')
@login_required
def list_notifications():
    notifs = NotificationService.get_all(current_user.id)
    # Return JSON for AJAX polling
    return jsonify([{
        'id':         n.id,
        'title':      n.title,
        'body':       n.body or '',
        'category':   n.category,
        'is_read':    n.is_read,
        'link':       n.link or '',
        'created_at': n.created_at.strftime('%b %d, %H:%M'),
        'time_ago':   _time_ago(n.created_at),
    } for n in notifs])


@notif_bp.route('/unread-count')
@login_required
def unread_count():
    count = NotificationService.unread_count(current_user.id)
    return jsonify({'count': count})


@notif_bp.route('/<int:notif_id>/read', methods=['POST'])
@login_required
def mark_read(notif_id):
    ok = NotificationService.mark_read(notif_id, current_user.id)
    return jsonify({'success': ok})


@notif_bp.route('/mark-all-read', methods=['POST'])
@login_required
def mark_all_read():
    NotificationService.mark_all_read(current_user.id)
    return jsonify({'success': True})


@notif_bp.route('/<int:notif_id>/delete', methods=['POST'])
@login_required
def delete_notification(notif_id):
    ok = NotificationService.delete(notif_id, current_user.id)
    return jsonify({'success': ok})


def _time_ago(dt):
    from datetime import datetime
    diff = int((datetime.utcnow() - dt).total_seconds())
    if diff < 60:    return 'Just now'
    if diff < 3600:  return f'{diff // 60}m ago'
    if diff < 86400: return f'{diff // 3600}h ago'
    return f'{diff // 86400}d ago'
