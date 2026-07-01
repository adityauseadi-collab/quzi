import pytest
from app import create_app
from app.extensions import db as _db
from app.models.user import User
from app.models.question import Category, Question
from app.models.quiz import Quiz, QuizQuestion, Result, StudentAnswer
from app.services.notification_service import Notification  # noqa: F401 – ensures table is created


@pytest.fixture(scope='session')
def app():
    app = create_app('testing')
    with app.app_context():
        _db.create_all()
        yield app
        _db.drop_all()


@pytest.fixture(scope='function')
def db(app):
    with app.app_context():
        _db.session.begin_nested()
        yield _db
        _db.session.rollback()


@pytest.fixture(scope='function')
def client(app):
    return app.test_client()


@pytest.fixture(scope='function')
def runner(app):
    return app.test_cli_runner()


@pytest.fixture(scope='function')
def admin_user(app):
    with app.app_context():
        user = User.query.filter_by(username='test_admin').first()
        if not user:
            user = User(username='test_admin', email='admin@test.com',
                        full_name='Test Admin', role='admin')
            # Meets Medium: uppercase + lowercase + digit, 12 chars
            user.set_password('Adminpass123')
            _db.session.add(user)
            _db.session.commit()
        return user


@pytest.fixture(scope='function')
def student_user(app):
    with app.app_context():
        user = User.query.filter_by(username='test_student').first()
        if not user:
            user = User(username='test_student', email='student@test.com',
                        full_name='Test Student', role='student')
            # Meets Medium: uppercase + lowercase + digit, 13 chars
            user.set_password('Studentpass123')
            _db.session.add(user)
            _db.session.commit()
        return user


@pytest.fixture(scope='function')
def category(app):
    with app.app_context():
        cat = Category.query.filter_by(name='Test Category').first()
        if not cat:
            cat = Category(name='Test Category', color='#6366f1')
            _db.session.add(cat)
            _db.session.commit()
        return cat


@pytest.fixture(scope='function')
def questions(app, category):
    with app.app_context():
        cat = Category.query.filter_by(name='Test Category').first()
        qs = []
        for i in range(5):
            q_text = f'Test question {i}?'
            q = Question.query.filter_by(question_text=q_text).first()
            if not q:
                q = Question(
                    question_text=q_text,
                    option_a=f'Option A {i}',
                    option_b=f'Option B {i}',
                    option_c=f'Option C {i}',
                    option_d=f'Option D {i}',
                    correct_answer='A',
                    category_id=cat.id,
                    difficulty='easy'
                )
                _db.session.add(q)
        _db.session.commit()
        return Question.query.filter(
            Question.question_text.like('Test question%')
        ).all()


@pytest.fixture(scope='function')
def quiz(app, category, questions, admin_user):
    with app.app_context():
        admin = User.query.filter_by(username='test_admin').first()
        cat = Category.query.filter_by(name='Test Category').first()
        q_list = Question.query.filter(Question.question_text.like('Test question%')).all()

        quiz_obj = Quiz.query.filter_by(title='Test Quiz').first()
        if not quiz_obj:
            quiz_obj = Quiz(
                title='Test Quiz',
                category_id=cat.id,
                num_questions=min(5, len(q_list)),
                time_limit=30,
                is_published=True,
                created_by=admin.id
            )
            _db.session.add(quiz_obj)
            _db.session.flush()
            for i, q in enumerate(q_list[:5]):
                qq = QuizQuestion(quiz_id=quiz_obj.id, question_id=q.id, order=i)
                _db.session.add(qq)
            _db.session.commit()
        return quiz_obj


def login(client, username, password):
    return client.post('/auth/login', data={
        'username': username,
        'password': password,
        'csrf_token': 'test'
    }, follow_redirects=True)


def logout(client):
    return client.get('/auth/logout', follow_redirects=True)
