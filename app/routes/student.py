from flask import Blueprint, render_template, redirect, url_for, flash, request, session, send_file
from flask_login import login_required, current_user
from functools import wraps
from app.extensions import db
from app.models.quiz import Quiz, Result
from app.models.user import User
from app.services.quiz_service import QuizService
from app.services.pdf_service import generate_result_pdf

student_bp = Blueprint('student', __name__, url_prefix='/student')


def student_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return login_required(decorated)


@student_bp.route('/dashboard')
@student_required
def dashboard():
    available_quizzes = Quiz.query.filter_by(is_published=True).order_by(Quiz.created_at.desc()).all()
    my_results = Result.query.filter_by(student_id=current_user.id).order_by(Result.submitted_at.desc()).all()
    avg_score = current_user.get_average_score()

    # Chart data: last 10 results
    chart_labels = []
    chart_scores = []
    for r in reversed(my_results[-10:]):
        chart_labels.append(r.quiz.title[:20])
        chart_scores.append(r.percentage)

    taken_quiz_ids = {r.quiz_id for r in my_results}

    return render_template('student/dashboard.html',
                           available_quizzes=available_quizzes,
                           my_results=my_results,
                           avg_score=avg_score,
                           chart_labels=chart_labels,
                           chart_scores=chart_scores,
                           taken_quiz_ids=taken_quiz_ids)


@student_bp.route('/quiz/<int:quiz_id>/start')
@student_required
def start_quiz(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    if not quiz.is_published:
        flash('This quiz is not available.', 'danger')
        return redirect(url_for('student.dashboard'))
    questions = quiz.get_questions()
    if not questions:
        flash('This quiz has no questions.', 'danger')
        return redirect(url_for('student.dashboard'))

    # Clear any previous session data for this quiz
    session.pop(f'quiz_{quiz_id}_answers', None)

    return render_template('student/quiz_start.html', quiz=quiz, questions=questions)


@student_bp.route('/quiz/<int:quiz_id>/take')
@student_required
def take_quiz(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    if not quiz.is_published:
        flash('This quiz is not available.', 'danger')
        return redirect(url_for('student.dashboard'))
    questions = quiz.get_questions()
    return render_template('student/take_quiz.html', quiz=quiz, questions=questions)


@student_bp.route('/quiz/<int:quiz_id>/submit', methods=['POST'])
@student_required
def submit_quiz(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    if not quiz.is_published:
        flash('This quiz is not available.', 'danger')
        return redirect(url_for('student.dashboard'))

    # Collect answers from form
    answers = {}
    for key, value in request.form.items():
        if key.startswith('question_'):
            q_id = key.replace('question_', '')
            answers[q_id] = value.strip().upper()

    time_taken = request.form.get('time_taken', type=int)

    result = QuizService.submit_quiz(
        student_id=current_user.id,
        quiz_id=quiz_id,
        answers=answers,
        time_taken=time_taken
    )

    if not result:
        flash('Error submitting quiz. Please try again.', 'danger')
        return redirect(url_for('student.dashboard'))

    flash('Quiz submitted successfully!', 'success')
    return redirect(url_for('student.result', result_id=result.id))


@student_bp.route('/result/<int:result_id>')
@student_required
def result(result_id):
    result = Result.query.get_or_404(result_id)
    if result.student_id != current_user.id and not current_user.is_admin:
        flash('Access denied.', 'danger')
        return redirect(url_for('student.dashboard'))

    answers = result.answers.all()
    return render_template('student/result.html', result=result, answers=answers)


@student_bp.route('/result/<int:result_id>/pdf')
@student_required
def download_result_pdf(result_id):
    result = Result.query.get_or_404(result_id)
    if result.student_id != current_user.id and not current_user.is_admin:
        flash('Access denied.', 'danger')
        return redirect(url_for('student.dashboard'))

    buffer = generate_result_pdf(result)
    filename = f'result_{result.quiz.title.replace(" ", "_")}_{result_id}.pdf'
    return send_file(buffer, as_attachment=True, download_name=filename, mimetype='application/pdf')


@student_bp.route('/history')
@student_required
def history():
    results = Result.query.filter_by(student_id=current_user.id).order_by(Result.submitted_at.desc()).all()
    return render_template('student/history.html', results=results)


@student_bp.route('/leaderboard')
@student_required
def leaderboard():
    board = QuizService.get_leaderboard(limit=20)
    my_rank = None
    for i, entry in enumerate(board, 1):
        if entry['user'].id == current_user.id:
            my_rank = i
            break
    return render_template('student/leaderboard.html', board=board, my_rank=my_rank)
