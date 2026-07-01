"""
test_api.py
===========
Tests for:
  - /api/* JSON endpoints
  - Error handlers (404, 403, 500)
  - CLI commands
  - Template filters (helpers)
"""
import json
import pytest
from app.models.user import User
from app.models.question import Category, Question
from app.models.quiz import Quiz, Result
from app.utils.helpers import (time_ago, format_duration, truncate_words,
                                grade_color_class, percentage_to_bar_class,
                                sanitize_filename)
from datetime import datetime, timedelta


# ── Login helpers ──────────────────────────────────────────────────────────────
def login_admin(client):
    client.post('/auth/login', data={
        'username': 'test_admin', 'password': 'Adminpass123', 'csrf_token': 'test'
    }, follow_redirects=True)

def login_student(client):
    client.post('/auth/login', data={
        'username': 'test_student', 'password': 'Studentpass123', 'csrf_token': 'test'
    }, follow_redirects=True)


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 1 — API Endpoints
# ══════════════════════════════════════════════════════════════════════════════

class TestAPIEndpoints:

    def test_ping_public(self, client):
        r = client.get('/api/ping')
        assert r.status_code == 200
        data = json.loads(r.data)
        assert data['status'] == 'ok'

    def test_categories_requires_login(self, client):
        r = client.get('/api/categories')
        assert r.status_code in (302, 401)

    def test_categories_list(self, client, app, student_user):
        with app.app_context():
            login_student(client)
            r = client.get('/api/categories')
            assert r.status_code == 200
            data = json.loads(r.data)
            assert isinstance(data, list)

    def test_categories_have_required_keys(self, client, app, student_user, category):
        with app.app_context():
            login_student(client)
            r = client.get('/api/categories')
            data = json.loads(r.data)
            if data:
                cat = data[0]
                assert 'id' in cat
                assert 'name' in cat
                assert 'color' in cat
                assert 'count' in cat

    def test_admin_stats_requires_admin(self, client, app, student_user):
        with app.app_context():
            login_student(client)
            r = client.get('/api/stats/admin')
            assert r.status_code == 403

    def test_admin_stats_for_admin(self, client, app, admin_user):
        with app.app_context():
            login_admin(client)
            r = client.get('/api/stats/admin')
            assert r.status_code == 200
            data = json.loads(r.data)
            assert 'total_students' in data
            assert 'total_questions' in data
            assert 'total_quizzes_taken' in data
            assert 'avg_score' in data

    def test_student_stats(self, client, app, student_user):
        with app.app_context():
            login_student(client)
            r = client.get('/api/stats/student')
            assert r.status_code == 200
            data = json.loads(r.data)
            assert 'total_quizzes' in data
            assert 'avg_score' in data

    def test_question_search_admin_only(self, client, app, student_user):
        with app.app_context():
            login_student(client)
            r = client.get('/api/questions/search')
            assert r.status_code == 403

    def test_question_search_returns_results(self, client, app, admin_user, questions):
        with app.app_context():
            login_admin(client)
            r = client.get('/api/questions/search?q=Test')
            assert r.status_code == 200
            data = json.loads(r.data)
            assert 'questions' in data
            assert 'total' in data
            assert 'pages' in data

    def test_question_search_empty_query(self, client, app, admin_user):
        with app.app_context():
            login_admin(client)
            r = client.get('/api/questions/search')
            assert r.status_code == 200
            data = json.loads(r.data)
            assert 'questions' in data

    def test_question_search_by_difficulty(self, client, app, admin_user):
        with app.app_context():
            login_admin(client)
            r = client.get('/api/questions/search?difficulty=easy')
            assert r.status_code == 200

    def test_category_question_count(self, client, app, admin_user, category):
        with app.app_context():
            login_admin(client)
            cat = Category.query.filter_by(name='Test Category').first()
            r = client.get(f'/api/categories/{cat.id}/count')
            assert r.status_code == 200
            data = json.loads(r.data)
            assert 'count' in data
            assert isinstance(data['count'], int)

    def test_quiz_question_count(self, client, app, admin_user, category):
        with app.app_context():
            login_admin(client)
            cat = Category.query.filter_by(name='Test Category').first()
            r = client.get(f'/api/quiz/question-count?category_id={cat.id}')
            assert r.status_code == 200
            data = json.loads(r.data)
            assert 'count' in data

    def test_quiz_question_count_no_category(self, client, app, admin_user):
        with app.app_context():
            login_admin(client)
            r = client.get('/api/quiz/question-count')
            assert r.status_code == 200
            data = json.loads(r.data)
            assert data['count'] == 0

    def test_leaderboard_json(self, client, app, student_user):
        with app.app_context():
            login_student(client)
            r = client.get('/api/leaderboard')
            assert r.status_code == 200
            data = json.loads(r.data)
            assert isinstance(data, list)

    def test_leaderboard_json_structure(self, client, app, student_user):
        with app.app_context():
            login_student(client)
            r = client.get('/api/leaderboard')
            data = json.loads(r.data)
            if data:
                entry = data[0]
                for key in ('rank', 'name', 'avg_score', 'total_quizzes', 'is_me'):
                    assert key in entry

    def test_recent_activity_admin_only(self, client, app, student_user):
        with app.app_context():
            login_student(client)
            r = client.get('/api/activity')
            assert r.status_code == 403

    def test_recent_activity_for_admin(self, client, app, admin_user):
        with app.app_context():
            login_admin(client)
            r = client.get('/api/activity')
            assert r.status_code == 200
            data = json.loads(r.data)
            assert isinstance(data, list)

    def test_quiz_stats(self, client, app, admin_user, quiz):
        with app.app_context():
            login_admin(client)
            q = Quiz.query.filter_by(title='Test Quiz').first()
            if q:
                r = client.get(f'/api/quiz/{q.id}/stats')
                assert r.status_code == 200
                data = json.loads(r.data)
                assert 'attempts' in data
                assert 'avg_score' in data

    def test_student_timeline_admin_only(self, client, app, student_user, admin_user):
        with app.app_context():
            login_admin(client)
            student = User.query.filter_by(username='test_student').first()
            r = client.get(f'/api/student/{student.id}/timeline')
            assert r.status_code == 200
            data = json.loads(r.data)
            assert 'student' in data
            assert 'data' in data

    def test_api_404_returns_json_or_html(self, client):
        r = client.get('/api/nonexistent-endpoint-xyz')
        # Should return 404
        assert r.status_code == 404


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 2 — Error Handlers
# ══════════════════════════════════════════════════════════════════════════════

class TestErrorHandlers:

    def test_404_page(self, client):
        r = client.get('/this/page/does/not/exist/at/all')
        assert r.status_code == 404
        assert b'404' in r.data

    def test_404_contains_helpful_text(self, client):
        r = client.get('/nonexistent-route-xyz')
        assert r.status_code == 404
        # Should contain page not found messaging
        assert b'404' in r.data or b'Not Found' in r.data

    def test_admin_access_by_student_shows_redirect(self, client, app, student_user):
        with app.app_context():
            login_student(client)
            r = client.get('/admin/dashboard', follow_redirects=False)
            # Should redirect (302) or show error
            assert r.status_code in (302, 200)


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 3 — Template Filter / Helper Functions
# ══════════════════════════════════════════════════════════════════════════════

class TestHelperFunctions:

    # ── time_ago ──────────────────────────────────────────────────────────────

    def test_time_ago_none(self):
        assert time_ago(None) == 'Never'

    def test_time_ago_just_now(self):
        dt = datetime.utcnow() - timedelta(seconds=30)
        assert time_ago(dt) == 'Just now'

    def test_time_ago_minutes(self):
        dt = datetime.utcnow() - timedelta(minutes=5)
        result = time_ago(dt)
        assert 'minute' in result

    def test_time_ago_hours(self):
        dt = datetime.utcnow() - timedelta(hours=3)
        result = time_ago(dt)
        assert 'hour' in result

    def test_time_ago_days(self):
        dt = datetime.utcnow() - timedelta(days=2)
        result = time_ago(dt)
        assert 'day' in result

    def test_time_ago_old_date(self):
        dt = datetime.utcnow() - timedelta(days=30)
        result = time_ago(dt)
        # Old dates return formatted date string
        assert len(result) > 5   # e.g. "May 27, 2025"

    # ── format_duration ───────────────────────────────────────────────────────

    def test_duration_none(self):
        assert format_duration(None) == '—'

    def test_duration_zero(self):
        assert format_duration(0) == '—'

    def test_duration_seconds(self):
        result = format_duration(90)
        assert 'm' in result

    def test_duration_hours(self):
        result = format_duration(3661)
        assert 'h' in result

    def test_duration_exact_minute(self):
        result = format_duration(60)
        assert '1m' in result

    # ── truncate_words ────────────────────────────────────────────────────────

    def test_truncate_short_text(self):
        text = 'Hello world'
        assert truncate_words(text, 5) == text

    def test_truncate_long_text(self):
        words = ['word'] * 20
        text = ' '.join(words)
        result = truncate_words(text, 10)
        assert result.endswith('…')
        assert len(result.split()) <= 11  # 10 words + ellipsis token

    def test_truncate_empty_string(self):
        assert truncate_words('', 5) == ''

    def test_truncate_none(self):
        assert truncate_words(None, 5) == ''

    # ── grade_color_class ─────────────────────────────────────────────────────

    def test_grade_color_a_plus(self):
        assert grade_color_class('A+') == 'success'

    def test_grade_color_a(self):
        assert grade_color_class('A') == 'success'

    def test_grade_color_b(self):
        assert grade_color_class('B') == 'primary'

    def test_grade_color_c(self):
        assert grade_color_class('C') == 'warning'

    def test_grade_color_d(self):
        assert grade_color_class('D') == 'warning'

    def test_grade_color_f(self):
        assert grade_color_class('F') == 'danger'

    def test_grade_color_unknown(self):
        assert grade_color_class('X') == 'secondary'

    # ── percentage_to_bar_class ───────────────────────────────────────────────

    def test_pct_bar_high(self):
        assert percentage_to_bar_class(85) == 'bg-success'

    def test_pct_bar_medium(self):
        assert percentage_to_bar_class(60) == 'bg-warning'

    def test_pct_bar_low(self):
        assert percentage_to_bar_class(30) == 'bg-danger'

    def test_pct_bar_boundary_70(self):
        assert percentage_to_bar_class(70) == 'bg-success'

    def test_pct_bar_boundary_50(self):
        assert percentage_to_bar_class(50) == 'bg-warning'

    def test_pct_bar_just_below_50(self):
        assert percentage_to_bar_class(49) == 'bg-danger'

    # ── sanitize_filename ─────────────────────────────────────────────────────

    def test_sanitize_normal_name(self):
        assert 'script' in sanitize_filename('my_script.py')

    def test_sanitize_removes_special_chars(self):
        result = sanitize_filename('file<name>/path')
        assert '<' not in result
        assert '/' not in result

    def test_sanitize_spaces_to_underscores(self):
        result = sanitize_filename('my file name')
        assert ' ' not in result
        assert '_' in result

    def test_sanitize_empty(self):
        result = sanitize_filename('')
        assert result == ''


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 4 — New Admin Pages
# ══════════════════════════════════════════════════════════════════════════════

class TestNewAdminPages:

    def test_all_results_page_loads(self, client, app, admin_user):
        with app.app_context():
            login_admin(client)
            r = client.get('/admin/results')
            assert r.status_code == 200

    def test_all_results_filter_by_quiz(self, client, app, admin_user, quiz):
        with app.app_context():
            login_admin(client)
            q = Quiz.query.filter_by(title='Test Quiz').first()
            if q:
                r = client.get(f'/admin/results?quiz={q.id}')
                assert r.status_code == 200

    def test_student_detail_page_loads(self, client, app, admin_user, student_user):
        with app.app_context():
            login_admin(client)
            student = User.query.filter_by(username='test_student').first()
            r = client.get(f'/admin/students/{student.id}')
            assert r.status_code == 200

    def test_student_detail_shows_username(self, client, app, admin_user, student_user):
        with app.app_context():
            login_admin(client)
            student = User.query.filter_by(username='test_student').first()
            r = client.get(f'/admin/students/{student.id}')
            assert b'test_student' in r.data

    def test_result_detail_page(self, client, app, admin_user, student_user, quiz):
        with app.app_context():
            login_admin(client)
            student = User.query.filter_by(username='test_student').first()
            q_obj   = Quiz.query.filter_by(title='Test Quiz').first()
            if not q_obj:
                pytest.skip('Quiz fixture not available')
            from app.services.quiz_service import QuizService
            questions = q_obj.get_questions()
            if not questions:
                pytest.skip('No questions in quiz')
            answers = {str(q.id): 'A' for q in questions}
            result  = QuizService.submit_quiz(student.id, q_obj.id, answers, 30)
            r = client.get(f'/admin/results/{result.id}')
            assert r.status_code == 200

    def test_student_cannot_access_all_results(self, client, app, student_user):
        with app.app_context():
            login_student(client)
            r = client.get('/admin/results', follow_redirects=True)
            assert r.status_code == 200
            # Should not show the results table
            assert b'All Results' not in r.data or b'Login' in r.data
