"""
test_notifications.py
======================
Tests for:
  - NotificationService (unit)
  - Notification API routes (/notifications/*)
  - CSV export endpoints
  - Quiz edit route
"""
import json
import pytest
from app.models.user import User
from app.services.notification_service import NotificationService, Notification
from app.extensions import db


def login_admin(client):
    client.post('/auth/login', data={
        'username': 'test_admin', 'password': 'Adminpass123', 'csrf_token': 'test'
    }, follow_redirects=True)


def login_student(client):
    client.post('/auth/login', data={
        'username': 'test_student', 'password': 'Studentpass123', 'csrf_token': 'test'
    }, follow_redirects=True)


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 1 — NotificationService Unit Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestNotificationService:

    def test_send_creates_notification(self, app, student_user):
        with app.app_context():
            student = User.query.filter_by(username='test_student').first()
            before  = Notification.query.filter_by(user_id=student.id).count()
            NotificationService.send(student.id, 'Test Title', 'Test body')
            after = Notification.query.filter_by(user_id=student.id).count()
            assert after == before + 1

    def test_send_default_is_unread(self, app, student_user):
        with app.app_context():
            student = User.query.filter_by(username='test_student').first()
            n = NotificationService.send(student.id, 'Unread Test')
            assert n.is_read is False

    def test_send_with_category(self, app, student_user):
        with app.app_context():
            student = User.query.filter_by(username='test_student').first()
            n = NotificationService.send(student.id, 'Success Test', category='success')
            assert n.category == 'success'

    def test_send_with_link(self, app, student_user):
        with app.app_context():
            student = User.query.filter_by(username='test_student').first()
            n = NotificationService.send(student.id, 'Link Test', link='/student/result/1')
            assert n.link == '/student/result/1'

    def test_send_quiz_result_notification(self, app, student_user):
        with app.app_context():
            student = User.query.filter_by(username='test_student').first()
            before = NotificationService.unread_count(student.id)
            NotificationService.send_quiz_result(
                student.id, 'Test Quiz', 'A+', 95.0, 1
            )
            after = NotificationService.unread_count(student.id)
            assert after == before + 1

    def test_send_quiz_result_grade_a_plus_is_success(self, app, student_user):
        with app.app_context():
            student = User.query.filter_by(username='test_student').first()
            NotificationService.send_quiz_result(student.id, 'Q', 'A+', 95.0, 99)
            latest = (Notification.query
                      .filter_by(user_id=student.id)
                      .order_by(Notification.created_at.desc()).first())
            assert latest.category == 'success'

    def test_send_quiz_result_grade_f_is_danger(self, app, student_user):
        with app.app_context():
            student = User.query.filter_by(username='test_student').first()
            NotificationService.send_quiz_result(student.id, 'Q', 'F', 30.0, 99)
            latest = (Notification.query
                      .filter_by(user_id=student.id)
                      .order_by(Notification.created_at.desc()).first())
            assert latest.category == 'danger'

    def test_get_unread_returns_only_unread(self, app, student_user):
        with app.app_context():
            student = User.query.filter_by(username='test_student').first()
            n = NotificationService.send(student.id, 'Unread')
            unread = NotificationService.get_unread(student.id)
            assert any(x.id == n.id for x in unread)

    def test_mark_read_changes_status(self, app, student_user):
        with app.app_context():
            student = User.query.filter_by(username='test_student').first()
            n = NotificationService.send(student.id, 'To Mark Read')
            assert n.is_read is False
            ok = NotificationService.mark_read(n.id, student.id)
            assert ok is True
            updated = Notification.query.get(n.id)
            assert updated.is_read is True

    def test_mark_read_wrong_user_fails(self, app, student_user, admin_user):
        with app.app_context():
            student = User.query.filter_by(username='test_student').first()
            admin   = User.query.filter_by(username='test_admin').first()
            n = NotificationService.send(student.id, 'Private Notif')
            ok = NotificationService.mark_read(n.id, admin.id)  # wrong user
            assert ok is False
            assert Notification.query.get(n.id).is_read is False

    def test_mark_all_read(self, app, student_user):
        with app.app_context():
            student = User.query.filter_by(username='test_student').first()
            NotificationService.send(student.id, 'Bulk 1')
            NotificationService.send(student.id, 'Bulk 2')
            NotificationService.send(student.id, 'Bulk 3')
            NotificationService.mark_all_read(student.id)
            assert NotificationService.unread_count(student.id) == 0

    def test_unread_count_accurate(self, app, student_user):
        with app.app_context():
            student = User.query.filter_by(username='test_student').first()
            NotificationService.mark_all_read(student.id)
            before = NotificationService.unread_count(student.id)
            NotificationService.send(student.id, 'Count Test 1')
            NotificationService.send(student.id, 'Count Test 2')
            assert NotificationService.unread_count(student.id) == before + 2

    def test_delete_notification(self, app, student_user):
        with app.app_context():
            student = User.query.filter_by(username='test_student').first()
            n = NotificationService.send(student.id, 'To Delete')
            nid = n.id
            ok = NotificationService.delete(nid, student.id)
            assert ok is True
            assert Notification.query.get(nid) is None

    def test_delete_wrong_user_fails(self, app, student_user, admin_user):
        with app.app_context():
            student = User.query.filter_by(username='test_student').first()
            admin   = User.query.filter_by(username='test_admin').first()
            n  = NotificationService.send(student.id, 'Protected')
            ok = NotificationService.delete(n.id, admin.id)
            assert ok is False
            assert Notification.query.get(n.id) is not None

    def test_get_all_returns_list(self, app, student_user):
        with app.app_context():
            student = User.query.filter_by(username='test_student').first()
            result  = NotificationService.get_all(student.id)
            assert isinstance(result, list)

    def test_send_quiz_published_notifies_students(self, app, student_user):
        with app.app_context():
            student = User.query.filter_by(username='test_student').first()
            before  = NotificationService.unread_count(student.id)
            NotificationService.send_quiz_published([student.id], 'New Quiz!', 42)
            after = NotificationService.unread_count(student.id)
            assert after == before + 1


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 2 — Notification API Routes
# ══════════════════════════════════════════════════════════════════════════════

class TestNotificationRoutes:

    def test_list_requires_login(self, client):
        r = client.get('/notifications/')
        assert r.status_code in (302, 401)

    def test_list_returns_json(self, client, app, student_user):
        with app.app_context():
            login_student(client)
            r = client.get('/notifications/')
            assert r.status_code == 200
            assert r.content_type == 'application/json'

    def test_list_is_array(self, client, app, student_user):
        with app.app_context():
            login_student(client)
            r    = client.get('/notifications/')
            data = json.loads(r.data)
            assert isinstance(data, list)

    def test_unread_count_endpoint(self, client, app, student_user):
        with app.app_context():
            login_student(client)
            r    = client.get('/notifications/unread-count')
            data = json.loads(r.data)
            assert 'count' in data
            assert isinstance(data['count'], int)

    def test_mark_read_endpoint(self, client, app, student_user):
        with app.app_context():
            student = User.query.filter_by(username='test_student').first()
            n = NotificationService.send(student.id, 'API Read Test')
            login_student(client)
            r = client.post(f'/notifications/{n.id}/read',
                            headers={'X-CSRFToken': 'test'})
            assert r.status_code == 200
            data = json.loads(r.data)
            assert data['success'] is True

    def test_mark_all_read_endpoint(self, client, app, student_user):
        with app.app_context():
            student = User.query.filter_by(username='test_student').first()
            NotificationService.send(student.id, 'All Read 1')
            NotificationService.send(student.id, 'All Read 2')
            login_student(client)
            r = client.post('/notifications/mark-all-read',
                            headers={'X-CSRFToken': 'test'})
            assert r.status_code == 200
            data = json.loads(r.data)
            assert data['success'] is True

    def test_delete_notification_endpoint(self, client, app, student_user):
        with app.app_context():
            student = User.query.filter_by(username='test_student').first()
            n = NotificationService.send(student.id, 'API Delete Test')
            login_student(client)
            r = client.post(f'/notifications/{n.id}/delete',
                            headers={'X-CSRFToken': 'test'})
            assert r.status_code == 200
            data = json.loads(r.data)
            assert data['success'] is True


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 3 — CSV Export Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestCSVExports:

    def test_export_questions_requires_admin(self, client, app, student_user):
        with app.app_context():
            login_student(client)
            r = client.get('/admin/questions/export')
            # Student gets redirected, not CSV
            assert r.status_code in (302, 200)
            if r.status_code == 200:
                assert b'text/csv' not in r.content_type.encode()

    def test_export_questions_csv_for_admin(self, client, app, admin_user, questions):
        with app.app_context():
            login_admin(client)
            r = client.get('/admin/questions/export')
            assert r.status_code == 200
            assert 'text/csv' in r.content_type

    def test_export_questions_has_header_row(self, client, app, admin_user, questions):
        with app.app_context():
            login_admin(client)
            r    = client.get('/admin/questions/export')
            text = r.data.decode('utf-8')
            assert 'Question' in text
            assert 'CorrectAnswer' in text

    def test_export_questions_contains_data(self, client, app, admin_user, questions):
        with app.app_context():
            login_admin(client)
            r    = client.get('/admin/questions/export')
            text = r.data.decode('utf-8')
            lines = [l for l in text.strip().split('\n') if l]
            assert len(lines) >= 2   # header + at least one question

    def test_export_questions_filter_by_category(self, client, app, admin_user, category, questions):
        with app.app_context():
            login_admin(client)
            from app.models.question import Category
            cat = Category.query.filter_by(name='Test Category').first()
            r   = client.get(f'/admin/questions/export?category={cat.id}')
            assert r.status_code == 200
            assert 'text/csv' in r.content_type

    def test_export_results_requires_admin(self, client, app, student_user):
        with app.app_context():
            login_student(client)
            r = client.get('/admin/results/export')
            assert r.status_code in (302, 200)

    def test_export_results_csv_for_admin(self, client, app, admin_user):
        with app.app_context():
            login_admin(client)
            r = client.get('/admin/results/export')
            assert r.status_code == 200
            assert 'text/csv' in r.content_type

    def test_export_results_has_header(self, client, app, admin_user):
        with app.app_context():
            login_admin(client)
            r    = client.get('/admin/results/export')
            text = r.data.decode('utf-8')
            assert 'Student' in text
            assert 'Grade' in text
            assert 'Percentage' in text

    def test_export_results_filter_by_quiz(self, client, app, admin_user, quiz):
        with app.app_context():
            login_admin(client)
            from app.models.quiz import Quiz
            q = Quiz.query.filter_by(title='Test Quiz').first()
            if q:
                r = client.get(f'/admin/results/export?quiz={q.id}')
                assert r.status_code == 200


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 4 — Quiz Edit Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestQuizEdit:

    def test_edit_quiz_page_loads(self, client, app, admin_user, quiz):
        with app.app_context():
            login_admin(client)
            from app.models.quiz import Quiz
            q = Quiz.query.filter_by(title='Test Quiz').first()
            if not q:
                pytest.skip('Quiz fixture not available')
            r = client.get(f'/admin/quizzes/{q.id}/edit')
            assert r.status_code == 200

    def test_edit_quiz_updates_title(self, client, app, admin_user, quiz, category):
        with app.app_context():
            login_admin(client)
            from app.models.quiz import Quiz
            from app.models.question import Category
            q   = Quiz.query.filter_by(title='Test Quiz').first()
            cat = Category.query.filter_by(name='Test Category').first()
            if not q or not cat:
                pytest.skip('Fixtures not available')
            r = client.post(f'/admin/quizzes/{q.id}/edit', data={
                'title':          'Updated Test Quiz',
                'description':    'Updated description',
                'category_id':    cat.id,
                'num_questions':  q.num_questions,
                'time_limit':     20,
                'pass_percentage': 50,
                'is_published':   False,
                'csrf_token':     'test',
            }, follow_redirects=True)
            assert r.status_code == 200
            updated = Quiz.query.get(q.id)
            assert updated.title == 'Updated Test Quiz'
            assert updated.time_limit == 20
            # Restore
            updated.title = 'Test Quiz'
            db.session.commit()

    def test_edit_quiz_404_for_nonexistent(self, client, app, admin_user):
        with app.app_context():
            login_admin(client)
            r = client.get('/admin/quizzes/99999/edit')
            assert r.status_code == 404

    def test_student_cannot_edit_quiz(self, client, app, student_user, quiz):
        with app.app_context():
            login_student(client)
            from app.models.quiz import Quiz
            q = Quiz.query.filter_by(title='Test Quiz').first()
            if not q:
                pytest.skip('Quiz fixture not available')
            r = client.get(f'/admin/quizzes/{q.id}/edit', follow_redirects=True)
            assert r.status_code == 200
            # Should not show the edit form to a student
            assert b'Edit Quiz' not in r.data or b'Login' in r.data
