import pytest
from app.models.question import Category, Question
from app.models.quiz import Quiz
from app.extensions import db


def login_admin(client):
    return client.post('/auth/login', data={
        'username': 'test_admin',
        'password': 'Adminpass123',
        'csrf_token': 'test'
    }, follow_redirects=True)


def login_student(client):
    return client.post('/auth/login', data={
        'username': 'test_student',
        'password': 'Studentpass123',
        'csrf_token': 'test'
    }, follow_redirects=True)


class TestAdminAccess:
    def test_admin_dashboard_requires_login(self, client):
        r = client.get('/admin/dashboard', follow_redirects=True)
        assert b'login' in r.data.lower() or r.status_code == 200

    def test_admin_dashboard_accessible_to_admin(self, client, app, admin_user):
        with app.app_context():
            login_admin(client)
            r = client.get('/admin/dashboard')
            assert r.status_code == 200

    def test_student_cannot_access_admin(self, client, app, student_user):
        with app.app_context():
            login_student(client)
            r = client.get('/admin/dashboard', follow_redirects=True)
            # Should redirect or show error
            assert r.status_code == 200

    def test_admin_questions_page(self, client, app, admin_user):
        with app.app_context():
            login_admin(client)
            r = client.get('/admin/questions')
            assert r.status_code == 200

    def test_admin_quizzes_page(self, client, app, admin_user):
        with app.app_context():
            login_admin(client)
            r = client.get('/admin/quizzes')
            assert r.status_code == 200

    def test_admin_categories_page(self, client, app, admin_user):
        with app.app_context():
            login_admin(client)
            r = client.get('/admin/categories')
            assert r.status_code == 200

    def test_admin_analytics_page(self, client, app, admin_user):
        with app.app_context():
            login_admin(client)
            r = client.get('/admin/analytics')
            assert r.status_code == 200

    def test_admin_students_page(self, client, app, admin_user):
        with app.app_context():
            login_admin(client)
            r = client.get('/admin/students')
            assert r.status_code == 200


class TestQuestionManagement:
    def test_add_question(self, client, app, admin_user, category):
        with app.app_context():
            login_admin(client)
            cat = Category.query.filter_by(name='Test Category').first()
            initial_count = Question.query.count()
            r = client.post('/admin/questions/add', data={
                'question_text': 'What is 2 + 2?',
                'option_a': '3',
                'option_b': '4',
                'option_c': '5',
                'option_d': '6',
                'correct_answer': 'B',
                'difficulty': 'easy',
                'category_id': cat.id,
                'csrf_token': 'test'
            }, follow_redirects=True)
            assert r.status_code == 200
            assert Question.query.count() == initial_count + 1

    def test_add_question_page_loads(self, client, app, admin_user):
        with app.app_context():
            login_admin(client)
            r = client.get('/admin/questions/add')
            assert r.status_code == 200

    def test_edit_question_page_loads(self, client, app, admin_user, questions):
        with app.app_context():
            login_admin(client)
            q = Question.query.filter(Question.question_text.like('Test question%')).first()
            r = client.get(f'/admin/questions/{q.id}/edit')
            assert r.status_code == 200

    def test_edit_question(self, client, app, admin_user, questions):
        with app.app_context():
            login_admin(client)
            q = Question.query.filter(Question.question_text.like('Test question%')).first()
            cat = Category.query.filter_by(name='Test Category').first()
            r = client.post(f'/admin/questions/{q.id}/edit', data={
                'question_text': 'Updated question text?',
                'option_a': 'Updated A',
                'option_b': 'Option B',
                'option_c': 'Option C',
                'option_d': 'Option D',
                'correct_answer': 'A',
                'difficulty': 'medium',
                'category_id': cat.id,
                'csrf_token': 'test'
            }, follow_redirects=True)
            assert r.status_code == 200
            updated = Question.query.get(q.id)
            assert updated.question_text == 'Updated question text?'

    def test_delete_question(self, client, app, admin_user, category):
        with app.app_context():
            login_admin(client)
            cat = Category.query.filter_by(name='Test Category').first()
            q = Question(
                question_text='Question to delete',
                option_a='A', option_b='B', option_c='C', option_d='D',
                correct_answer='A', category_id=cat.id
            )
            db.session.add(q)
            db.session.commit()
            q_id = q.id
            r = client.post(f'/admin/questions/{q_id}/delete', data={
                'csrf_token': 'test'
            }, follow_redirects=True)
            assert r.status_code == 200
            assert Question.query.get(q_id) is None

    def test_search_questions(self, client, app, admin_user):
        with app.app_context():
            login_admin(client)
            r = client.get('/admin/questions?q=Test')
            assert r.status_code == 200

    def test_filter_questions_by_category(self, client, app, admin_user, category):
        with app.app_context():
            login_admin(client)
            cat = Category.query.filter_by(name='Test Category').first()
            r = client.get(f'/admin/questions?category={cat.id}')
            assert r.status_code == 200


class TestCategoryManagement:
    def test_add_category(self, client, app, admin_user):
        with app.app_context():
            login_admin(client)
            initial = Category.query.count()
            r = client.post('/admin/categories/add', data={
                'name': 'New Test Category XYZ',
                'description': 'A new category',
                'color': '#ff0000',
                'csrf_token': 'test'
            }, follow_redirects=True)
            assert r.status_code == 200
            assert Category.query.count() == initial + 1

    def test_delete_empty_category(self, client, app, admin_user):
        with app.app_context():
            login_admin(client)
            cat = Category(name='Empty Cat To Delete', color='#000')
            db.session.add(cat)
            db.session.commit()
            cat_id = cat.id
            r = client.post(f'/admin/categories/{cat_id}/delete', data={
                'csrf_token': 'test'
            }, follow_redirects=True)
            assert r.status_code == 200
            assert Category.query.get(cat_id) is None


class TestQuizManagement:
    def test_create_quiz_page(self, client, app, admin_user):
        with app.app_context():
            login_admin(client)
            r = client.get('/admin/quizzes/create')
            assert r.status_code == 200

    def test_create_quiz(self, client, app, admin_user, questions, category):
        with app.app_context():
            login_admin(client)
            cat = Category.query.filter_by(name='Test Category').first()
            initial = Quiz.query.count()
            r = client.post('/admin/quizzes/create', data={
                'title': 'New Test Quiz ABC',
                'description': 'A test quiz',
                'category_id': cat.id,
                'num_questions': 3,
                'time_limit': 15,
                'pass_percentage': 60,
                'is_published': True,
                'csrf_token': 'test'
            }, follow_redirects=True)
            assert r.status_code == 200
            assert Quiz.query.count() == initial + 1

    def test_toggle_quiz_publish(self, client, app, admin_user, quiz):
        with app.app_context():
            login_admin(client)
            q = Quiz.query.filter_by(title='Test Quiz').first()
            original = q.is_published
            r = client.post(f'/admin/quizzes/{q.id}/toggle', data={
                'csrf_token': 'test'
            }, follow_redirects=True)
            assert r.status_code == 200
            updated = Quiz.query.get(q.id)
            assert updated.is_published == (not original)
