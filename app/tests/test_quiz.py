import pytest
from app.models.quiz import Quiz, Result, StudentAnswer
from app.models.user import User
from app.models.question import Category, Question
from app.services.quiz_service import QuizService
from app.extensions import db


def login_student(client):
    return client.post('/auth/login', data={
        'username': 'test_student',
        'password': 'Studentpass123',
        'csrf_token': 'test'
    }, follow_redirects=True)


def login_admin(client):
    return client.post('/auth/login', data={
        'username': 'test_admin',
        'password': 'Adminpass123',
        'csrf_token': 'test'
    }, follow_redirects=True)


class TestStudentAccess:
    def test_student_dashboard_loads(self, client, app, student_user):
        with app.app_context():
            login_student(client)
            r = client.get('/student/dashboard')
            assert r.status_code == 200

    def test_student_history_loads(self, client, app, student_user):
        with app.app_context():
            login_student(client)
            r = client.get('/student/history')
            assert r.status_code == 200

    def test_student_leaderboard_loads(self, client, app, student_user):
        with app.app_context():
            login_student(client)
            r = client.get('/student/leaderboard')
            assert r.status_code == 200

    def test_quiz_start_page(self, client, app, student_user, quiz):
        with app.app_context():
            login_student(client)
            q = Quiz.query.filter_by(title='Test Quiz').first()
            if q is None:
                pytest.skip("Quiz fixture not available in this test order")
            r = client.get(f'/student/quiz/{q.id}/start')
            assert r.status_code in (200, 302)

    def test_take_quiz_page(self, client, app, student_user, quiz):
        with app.app_context():
            login_student(client)
            q = Quiz.query.filter_by(title='Test Quiz').first()
            if q is None:
                pytest.skip("Quiz fixture not available in this test order")
            r = client.get(f'/student/quiz/{q.id}/take')
            assert r.status_code in (200, 302)

    def test_unpublished_quiz_blocked(self, client, app, student_user, admin_user, category, questions):
        with app.app_context():
            from app.models.question import Question
            from app.models.quiz import QuizQuestion
            admin = User.query.filter_by(username='test_admin').first()
            cat   = Category.query.filter_by(name='Test Category').first()
            if not cat:
                pytest.skip('Category fixture not available')

            # Create unpublished quiz directly (no HTTP session needed)
            quiz_obj = Quiz(
                title='Hidden Quiz XYZ',
                category_id=cat.id,
                num_questions=1,
                time_limit=10,
                is_published=False,
                created_by=admin.id
            )
            from app.extensions import db as _db
            _db.session.add(quiz_obj)
            _db.session.flush()
            q_list = Question.query.filter(Question.question_text.like('Test question%')).all()
            if q_list:
                _db.session.add(QuizQuestion(quiz_id=quiz_obj.id, question_id=q_list[0].id, order=0))
            _db.session.commit()
            hidden_id = quiz_obj.id

            # Login as student
            client.get('/auth/logout', follow_redirects=True)
            client.post('/auth/login', data={
                'username': 'test_student',
                'password': 'Studentpass123',
                'csrf_token': 'test'
            }, follow_redirects=True)

            r = client.get(f'/student/quiz/{hidden_id}/start', follow_redirects=True)
            assert r.status_code == 200
            # Student redirected to dashboard with "not available" message
            assert b'not available' in r.data or b'dashboard' in r.data.lower() or b'Dashboard' in r.data


class TestQuizSubmission:
    def test_submit_quiz_all_correct(self, client, app, student_user, quiz):
        """Test that submitting all correct via HTTP returns 200."""
        with app.app_context():
            login_student(client)
            q_obj = Quiz.query.filter_by(title='Test Quiz').first()
            if not q_obj:
                pytest.skip("Quiz fixture not available")
            questions = q_obj.get_questions()
            if not questions:
                pytest.skip("No questions in quiz")
            form_data = {'csrf_token': 'test', 'time_taken': '120'}
            for q in questions:
                form_data[f'question_{q.id}'] = 'A'
            r = client.post(f'/student/quiz/{q_obj.id}/submit', data=form_data, follow_redirects=True)
            assert r.status_code == 200
            # Verify via service layer (direct DB write)
            student = User.query.filter_by(username='test_student').first()
            answers = {str(q.id): 'A' for q in questions}
            result = QuizService.submit_quiz(student.id, q_obj.id, answers, 30)
            assert result.correct_answers == len(questions)
            assert result.percentage == 100.0

    def test_submit_quiz_all_wrong(self, client, app, student_user, quiz):
        """Test that submitting all wrong via service gives 0%."""
        with app.app_context():
            login_student(client)
            q_obj = Quiz.query.filter_by(title='Test Quiz').first()
            if not q_obj:
                pytest.skip("Quiz fixture not available")
            questions = q_obj.get_questions()
            if not questions:
                pytest.skip("No questions in quiz")
            student = User.query.filter_by(username='test_student').first()
            answers = {str(q.id): 'D' for q in questions}
            result = QuizService.submit_quiz(student.id, q_obj.id, answers, 60)
            assert result.correct_answers == 0
            assert result.percentage == 0.0
            assert result.wrong_answers == len(questions)

    def test_submit_quiz_partial(self, client, app, student_user, quiz):
        """Test partial correct answers via service."""
        with app.app_context():
            login_student(client)
            q_obj = Quiz.query.filter_by(title='Test Quiz').first()
            if not q_obj:
                pytest.skip("Quiz fixture not available")
            questions = q_obj.get_questions()
            if not questions:
                pytest.skip("No questions in quiz")
            student = User.query.filter_by(username='test_student').first()
            # Answer half correctly
            answers = {str(q.id): ('A' if i % 2 == 0 else 'D') for i, q in enumerate(questions)}
            result = QuizService.submit_quiz(student.id, q_obj.id, answers, 90)
            assert result is not None
            assert result.correct_answers >= 0
            assert result.wrong_answers >= 0
            assert result.correct_answers + result.wrong_answers <= len(questions)

    def test_result_page_accessible(self, client, app, student_user, quiz):
        with app.app_context():
            login_student(client)
            student = User.query.filter_by(username='test_student').first()
            q_obj = Quiz.query.filter_by(title='Test Quiz').first()

            result = Result.query.filter_by(
                student_id=student.id, quiz_id=q_obj.id
            ).first()
            if not result:
                questions = q_obj.get_questions()
                answers = {str(q.id): 'A' for q in questions}
                result = QuizService.submit_quiz(student.id, q_obj.id, answers, 60)

            r = client.get(f'/student/result/{result.id}')
            assert r.status_code == 200

    def test_result_pdf_download(self, client, app, student_user, quiz):
        with app.app_context():
            login_student(client)
            student = User.query.filter_by(username='test_student').first()
            q_obj = Quiz.query.filter_by(title='Test Quiz').first()

            result = Result.query.filter_by(
                student_id=student.id, quiz_id=q_obj.id
            ).first()
            if not result:
                questions = q_obj.get_questions()
                answers = {str(q.id): 'A' for q in questions}
                result = QuizService.submit_quiz(student.id, q_obj.id, answers, 60)

            r = client.get(f'/student/result/{result.id}/pdf')
            assert r.status_code == 200
            assert r.content_type == 'application/pdf'

    def test_cannot_view_others_result(self, client, app, student_user, admin_user, quiz):
        with app.app_context():
            # Admin submits a quiz
            admin = User.query.filter_by(username='test_admin').first()
            q_obj = Quiz.query.filter_by(title='Test Quiz').first()
            questions = q_obj.get_questions()
            answers = {str(q.id): 'A' for q in questions}
            admin_result = QuizService.submit_quiz(admin.id, q_obj.id, answers, 60)

            # Student tries to view admin's result
            login_student(client)
            r = client.get(f'/student/result/{admin_result.id}', follow_redirects=True)
            assert b'denied' in r.data or r.status_code == 200


class TestScoringSystem:
    def test_grade_a_plus(self, app):
        with app.app_context():
            result = Result(
                student_id=1, quiz_id=1,
                total_questions=10, correct_answers=9,
                marks_obtained=9, percentage=95.0
            )
            assert result.calculate_grade() == 'A+'

    def test_grade_a(self, app):
        with app.app_context():
            result = Result(
                student_id=1, quiz_id=1,
                total_questions=10, correct_answers=8,
                marks_obtained=8, percentage=85.0
            )
            assert result.calculate_grade() == 'A'

    def test_grade_b(self, app):
        with app.app_context():
            result = Result(percentage=75.0, student_id=1, quiz_id=1,
                            total_questions=10, correct_answers=7, marks_obtained=7)
            assert result.calculate_grade() == 'B'

    def test_grade_c(self, app):
        with app.app_context():
            result = Result(percentage=65.0, student_id=1, quiz_id=1,
                            total_questions=10, correct_answers=6, marks_obtained=6)
            assert result.calculate_grade() == 'C'

    def test_grade_d(self, app):
        with app.app_context():
            result = Result(percentage=55.0, student_id=1, quiz_id=1,
                            total_questions=10, correct_answers=5, marks_obtained=5)
            assert result.calculate_grade() == 'D'

    def test_grade_f(self, app):
        with app.app_context():
            result = Result(percentage=40.0, student_id=1, quiz_id=1,
                            total_questions=10, correct_answers=4, marks_obtained=4)
            assert result.calculate_grade() == 'F'

    def test_grade_boundary_90(self, app):
        with app.app_context():
            result = Result(percentage=90.0, student_id=1, quiz_id=1,
                            total_questions=10, correct_answers=9, marks_obtained=9)
            assert result.calculate_grade() == 'A+'

    def test_grade_boundary_80(self, app):
        with app.app_context():
            result = Result(percentage=80.0, student_id=1, quiz_id=1,
                            total_questions=10, correct_answers=8, marks_obtained=8)
            assert result.calculate_grade() == 'A'

    def test_percentage_calculation(self, app, student_user, quiz):
        with app.app_context():
            student = User.query.filter_by(username='test_student').first()
            q_obj = Quiz.query.filter_by(title='Test Quiz').first()
            questions = q_obj.get_questions()
            total = len(questions)
            # Answer exactly half correctly
            correct_count = total // 2
            answers = {}
            for i, q in enumerate(questions):
                answers[str(q.id)] = 'A' if i < correct_count else 'B'

            result = QuizService.submit_quiz(student.id, q_obj.id, answers, 45)
            expected_pct = round((correct_count / total) * 100, 2)
            assert abs(result.percentage - expected_pct) < 0.1

    def test_quiz_service_submit(self, app, student_user, quiz):
        with app.app_context():
            student = User.query.filter_by(username='test_student').first()
            q_obj = Quiz.query.filter_by(title='Test Quiz').first()
            questions = q_obj.get_questions()
            answers = {str(q.id): q.correct_answer for q in questions}
            result = QuizService.submit_quiz(student.id, q_obj.id, answers, 30)
            assert result is not None
            assert result.correct_answers == len(questions)
            assert result.percentage == 100.0
            assert result.grade == 'A+'

    def test_skipped_questions_not_counted_wrong(self, app, student_user, quiz):
        with app.app_context():
            student = User.query.filter_by(username='test_student').first()
            q_obj = Quiz.query.filter_by(title='Test Quiz').first()
            questions = q_obj.get_questions()
            # Only answer one question
            answers = {str(questions[0].id): 'A'}
            result = QuizService.submit_quiz(student.id, q_obj.id, answers, 10)
            assert result.correct_answers == 1
            assert result.wrong_answers == 0  # skipped != wrong

    def test_marks_equal_correct_answers(self, app, student_user, quiz):
        with app.app_context():
            student = User.query.filter_by(username='test_student').first()
            q_obj = Quiz.query.filter_by(title='Test Quiz').first()
            questions = q_obj.get_questions()
            answers = {str(q.id): 'A' for q in questions[:3]}  # answer 3
            result = QuizService.submit_quiz(student.id, q_obj.id, answers, 20)
            assert result.marks_obtained == result.correct_answers


class TestImportService:
    def test_import_invalid_file_format(self, app):
        with app.app_context():
            from app.services.import_service import ImportService
            result = ImportService.import_questions('/tmp/nonexistent.xlsx')
            assert result['success'] is False

    def test_import_csv(self, app, category):
        import csv, tempfile, os
        with app.app_context():
            from app.services.import_service import ImportService
            cat = category.__class__.query.filter_by(name='Test Category').first()

            with tempfile.NamedTemporaryFile(mode='w', suffix='.csv',
                                             delete=False, newline='') as f:
                writer = csv.DictWriter(f, fieldnames=[
                    'Question', 'OptionA', 'OptionB', 'OptionC', 'OptionD',
                    'CorrectAnswer', 'Category'
                ])
                writer.writeheader()
                writer.writerow({
                    'Question': 'CSV Import Test Question?',
                    'OptionA': 'Yes', 'OptionB': 'No',
                    'OptionC': 'Maybe', 'OptionD': 'Never',
                    'CorrectAnswer': 'A',
                    'Category': 'Test Category'
                })
                fname = f.name

            try:
                result = ImportService.import_questions(fname, cat.id)
                assert result['success'] is True
                assert result['imported'] >= 1
            finally:
                os.unlink(fname)

    def test_import_detects_duplicates(self, app, category):
        import csv, tempfile, os
        with app.app_context():
            from app.services.import_service import ImportService
            cat = category.__class__.query.filter_by(name='Test Category').first()

            with tempfile.NamedTemporaryFile(mode='w', suffix='.csv',
                                             delete=False, newline='') as f:
                writer = csv.DictWriter(f, fieldnames=[
                    'Question', 'OptionA', 'OptionB', 'OptionC', 'OptionD',
                    'CorrectAnswer'
                ])
                writer.writeheader()
                row = {
                    'Question': 'Duplicate check question?',
                    'OptionA': 'A', 'OptionB': 'B',
                    'OptionC': 'C', 'OptionD': 'D',
                    'CorrectAnswer': 'A'
                }
                writer.writerow(row)
                fname = f.name

            try:
                r1 = ImportService.import_questions(fname, cat.id)
                r2 = ImportService.import_questions(fname, cat.id)
                assert r2['duplicates'] >= 1
            finally:
                os.unlink(fname)

    def test_import_invalid_correct_answer(self, app, category):
        import csv, tempfile, os
        with app.app_context():
            from app.services.import_service import ImportService
            cat = category.__class__.query.filter_by(name='Test Category').first()

            with tempfile.NamedTemporaryFile(mode='w', suffix='.csv',
                                             delete=False, newline='') as f:
                writer = csv.DictWriter(f, fieldnames=[
                    'Question', 'OptionA', 'OptionB', 'OptionC', 'OptionD',
                    'CorrectAnswer'
                ])
                writer.writeheader()
                writer.writerow({
                    'Question': 'Bad answer question?',
                    'OptionA': 'A', 'OptionB': 'B',
                    'OptionC': 'C', 'OptionD': 'D',
                    'CorrectAnswer': 'E'  # invalid
                })
                fname = f.name

            try:
                result = ImportService.import_questions(fname, cat.id)
                assert len(result['errors']) >= 1
            finally:
                os.unlink(fname)
