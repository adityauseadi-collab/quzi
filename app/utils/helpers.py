"""
app/utils/helpers.py
====================
Shared helper functions and Jinja2 template filters.
"""
import re
from datetime import datetime, timedelta


def time_ago(dt: datetime) -> str:
    """Return a human-friendly relative timestamp, e.g. '3 minutes ago'."""
    if not dt:
        return 'Never'
    now  = datetime.utcnow()
    diff = now - dt
    secs = int(diff.total_seconds())

    if secs < 60:
        return 'Just now'
    if secs < 3600:
        m = secs // 60
        return f'{m} minute{"s" if m != 1 else ""} ago'
    if secs < 86400:
        h = secs // 3600
        return f'{h} hour{"s" if h != 1 else ""} ago'
    if secs < 604800:
        d = secs // 86400
        return f'{d} day{"s" if d != 1 else ""} ago'
    return dt.strftime('%b %d, %Y')


def format_duration(seconds: int) -> str:
    """Convert seconds to mm:ss or hh:mm:ss string."""
    if not seconds:
        return '—'
    seconds = int(seconds)
    if seconds < 3600:
        m, s = divmod(seconds, 60)
        return f'{m}m {s}s'
    h, remainder = divmod(seconds, 3600)
    m, s = divmod(remainder, 60)
    return f'{h}h {m}m {s}s'


def truncate_words(text: str, limit: int = 15) -> str:
    """Truncate text to `limit` words, adding ellipsis."""
    if not text:
        return ''
    words = text.split()
    if len(words) <= limit:
        return text
    return ' '.join(words[:limit]) + '…'


def grade_color_class(grade: str) -> str:
    """Return a Bootstrap / CSS colour class for a given grade."""
    return {
        'A+': 'success',
        'A':  'success',
        'B':  'primary',
        'C':  'warning',
        'D':  'warning',
        'F':  'danger',
    }.get(grade, 'secondary')


def percentage_to_bar_class(pct: float) -> str:
    """Return Bootstrap bg- class based on percentage."""
    if pct >= 70:
        return 'bg-success'
    if pct >= 50:
        return 'bg-warning'
    return 'bg-danger'


def sanitize_filename(name: str) -> str:
    """Strip unsafe characters from a filename."""
    name = re.sub(r'[^\w\s\-.]', '', name)
    return re.sub(r'\s+', '_', name).strip('_')


def register_template_filters(app):
    """Register custom Jinja2 filters and globals on the Flask app."""
    app.jinja_env.filters['time_ago']         = time_ago
    app.jinja_env.filters['duration']         = format_duration
    app.jinja_env.filters['truncate_words']   = truncate_words
    app.jinja_env.filters['grade_color']      = grade_color_class
    app.jinja_env.filters['pct_bar']          = percentage_to_bar_class

    # Useful globals
    app.jinja_env.globals['now'] = datetime.utcnow
