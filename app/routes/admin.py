import os
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from functools import wraps
from app.extensions import db
from app.models.user import User
from app.models.question import Category, Question
from app.models.quiz import Quiz, Result
from app.forms.quiz_forms import CategoryForm, QuestionForm, QuizForm, ImportQuestionsForm
from app.services.quiz_service import QuizService
from app.services.import_service import ImportService

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('Admin access required.', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return login_required(decorated)


@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    analytics = QuizService.get_admin_analytics()
    recent_results = Result.query.order_by(Result.submitted_at.desc()).limit(10).all()
    recent_students = User.query.filter_by(role='student').order_by(User.created_at.desc()).limit(5).all()
    return render_template('admin/dashboard.html', analytics=analytics,
                           recent_results=recent_results, recent_students=recent_students)


# ─── CATEGORIES ───────────────────────────────────────────────────────────────

@admin_bp.route('/categories')
@admin_required
def categories():
    cats = Category.query.order_by(Category.name).all()
    form = CategoryForm()
    return render_template('admin/categories.html', categories=cats, form=form)


@admin_bp.route('/categories/add', methods=['POST'])
@admin_required
def add_category():
    form = CategoryForm()
    if form.validate_on_submit():
        if Category.query.filter_by(name=form.name.data.strip()).first():
            flash('Category already exists.', 'warning')
        else:
            cat = Category(name=form.name.data.strip(),
                           description=form.description.data,
                           color=form.color.data or '#6366f1')
            db.session.add(cat)
            db.session.commit()
            flash('Category created!', 'success')
    return redirect(url_for('admin.categories'))


@admin_bp.route('/categories/<int:cat_id>/delete', methods=['POST'])
@admin_required
def delete_category(cat_id):
    cat = Category.query.get_or_404(cat_id)
    if cat.questions.count() > 0:
        flash('Cannot delete category with existing questions.', 'danger')
    else:
        db.session.delete(cat)
        db.session.commit()
        flash('Category deleted.', 'success')
    return redirect(url_for('admin.categories'))


# ─── QUESTIONS ────────────────────────────────────────────────────────────────

@admin_bp.route('/questions')
@admin_required
def questions():
    page = request.args.get('page', 1, type=int)
    category_id = request.args.get('category', 0, type=int)
    search = request.args.get('q', '')

    query = Question.query
    if category_id:
        query = query.filter_by(category_id=category_id)
    if search:
        query = query.filter(Question.question_text.ilike(f'%{search}%'))

    questions = query.order_by(Question.created_at.desc()).paginate(
        page=page, per_page=current_app.config['QUESTIONS_PER_PAGE'], error_out=False
    )
    categories = Category.query.order_by(Category.name).all()
    return render_template('admin/questions.html', questions=questions,
                           categories=categories, current_category=category_id, search=search)


@admin_bp.route('/questions/add', methods=['GET', 'POST'])
@admin_required
def add_question():
    form = QuestionForm()
    form.category_id.choices = [(c.id, c.name) for c in Category.query.order_by(Category.name).all()]
    if form.validate_on_submit():
        q = Question(
            question_text=form.question_text.data.strip(),
            option_a=form.option_a.data.strip(),
            option_b=form.option_b.data.strip(),
            option_c=form.option_c.data.strip(),
            option_d=form.option_d.data.strip(),
            correct_answer=form.correct_answer.data,
            explanation=form.explanation.data,
            difficulty=form.difficulty.data,
            category_id=form.category_id.data
        )
        db.session.add(q)
        db.session.commit()
        flash('Question added successfully!', 'success')
        return redirect(url_for('admin.questions'))
    return render_template('admin/question_form.html', form=form, title='Add Question')


@admin_bp.route('/questions/<int:q_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_question(q_id):
    q = Question.query.get_or_404(q_id)
    form = QuestionForm(obj=q)
    form.category_id.choices = [(c.id, c.name) for c in Category.query.order_by(Category.name).all()]
    if form.validate_on_submit():
        q.question_text = form.question_text.data.strip()
        q.option_a = form.option_a.data.strip()
        q.option_b = form.option_b.data.strip()
        q.option_c = form.option_c.data.strip()
        q.option_d = form.option_d.data.strip()
        q.correct_answer = form.correct_answer.data
        q.explanation = form.explanation.data
        q.difficulty = form.difficulty.data
        q.category_id = form.category_id.data
        db.session.commit()
        flash('Question updated!', 'success')
        return redirect(url_for('admin.questions'))
    return render_template('admin/question_form.html', form=form, title='Edit Question', question=q)


@admin_bp.route('/questions/<int:q_id>/delete', methods=['POST'])
@admin_required
def delete_question(q_id):
    q = Question.query.get_or_404(q_id)
    db.session.delete(q)
    db.session.commit()
    flash('Question deleted.', 'success')
    return redirect(url_for('admin.questions'))


# ─── IMPORT ───────────────────────────────────────────────────────────────────

@admin_bp.route('/questions/import', methods=['GET', 'POST'])
@admin_required
def import_questions():
    form = ImportQuestionsForm()
    form.category_id.choices = [(0, '-- From File --')] + [
        (c.id, c.name) for c in Category.query.order_by(Category.name).all()
    ]
    result = None
    if form.validate_on_submit():
        f = form.file.data
        filename = f.filename
        ext = os.path.splitext(filename)[1].lower()
        if ext not in ('.xlsx', '.csv'):
            flash('Only .xlsx and .csv files allowed.', 'danger')
        else:
            upload_dir = current_app.config['UPLOAD_FOLDER']
            os.makedirs(upload_dir, exist_ok=True)
            filepath = os.path.join(upload_dir, filename)
            f.save(filepath)
            cat_id = form.category_id.data if form.category_id.data else None
            result = ImportService.import_questions(filepath, default_category_id=cat_id)
            if result['success']:
                flash(f"Import complete: {result['imported']} questions imported, "
                      f"{result.get('duplicates', 0)} duplicates skipped.", 'success')
            else:
                flash(f"Import failed: {result.get('error', 'Unknown error')}", 'danger')
    return render_template('admin/import_questions.html', form=form, result=result)


# ─── QUIZZES ──────────────────────────────────────────────────────────────────

@admin_bp.route('/quizzes')
@admin_required
def quizzes():
    quizzes = Quiz.query.order_by(Quiz.created_at.desc()).all()
    return render_template('admin/quizzes.html', quizzes=quizzes)


@admin_bp.route('/quizzes/create', methods=['GET', 'POST'])
@admin_required
def create_quiz():
    form = QuizForm()
    form.category_id.choices = [(c.id, c.name) for c in Category.query.order_by(Category.name).all()]
    if form.validate_on_submit():
        cat = Category.query.get(form.category_id.data)
        q_count = cat.questions.count() if cat else 0
        if q_count == 0:
            flash('Selected category has no questions.', 'danger')
        else:
            quiz = QuizService.create_quiz(
                title=form.title.data.strip(),
                description=form.description.data,
                category_id=form.category_id.data,
                num_questions=min(form.num_questions.data, q_count),
                time_limit=form.time_limit.data,
                pass_percentage=form.pass_percentage.data or 50.0,
                is_published=form.is_published.data,
                created_by=current_user.id
            )
            flash(f'Quiz "{quiz.title}" created!', 'success')
            return redirect(url_for('admin.quizzes'))
    return render_template('admin/quiz_form.html', form=form, title='Create Quiz')


@admin_bp.route('/quizzes/<int:quiz_id>/toggle', methods=['POST'])
@admin_required
def toggle_quiz(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    quiz.is_published = not quiz.is_published
    db.session.commit()
    status = 'published' if quiz.is_published else 'disabled'

    # Notify all active students when a quiz is published
    if quiz.is_published:
        try:
            from app.services.notification_service import NotificationService
            from app.models.user import User as UserModel
            student_ids = [u.id for u in UserModel.query.filter_by(role='student', is_active=True).all()]
            NotificationService.send_quiz_published(student_ids, quiz.title, quiz.id)
        except Exception:
            pass

    flash(f'Quiz "{quiz.title}" {status}.', 'success')
    return redirect(url_for('admin.quizzes'))


@admin_bp.route('/quizzes/<int:quiz_id>/delete', methods=['POST'])
@admin_required
def delete_quiz(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    db.session.delete(quiz)
    db.session.commit()
    flash('Quiz deleted.', 'success')
    return redirect(url_for('admin.quizzes'))


# ─── STUDENTS ─────────────────────────────────────────────────────────────────

@admin_bp.route('/students')
@admin_required
def students():
    students = User.query.filter_by(role='student').order_by(User.created_at.desc()).all()
    return render_template('admin/students.html', students=students)


@admin_bp.route('/students/<int:student_id>/toggle', methods=['POST'])
@admin_required
def toggle_student(student_id):
    student = User.query.get_or_404(student_id)
    student.is_active = not student.is_active
    db.session.commit()
    status = 'activated' if student.is_active else 'deactivated'
    flash(f'Student {student.username} {status}.', 'success')
    return redirect(url_for('admin.students'))


@admin_bp.route('/analytics')
@admin_required
def analytics():
    analytics = QuizService.get_admin_analytics()
    return render_template('admin/analytics.html', analytics=analytics)


# ─── RESULT VIEWER ────────────────────────────────────────────────────────────

@admin_bp.route('/results')
@admin_required
def all_results():
    page    = request.args.get('page', 1, type=int)
    quiz_id = request.args.get('quiz', 0, type=int)
    query   = Result.query
    if quiz_id:
        query = query.filter_by(quiz_id=quiz_id)
    results = query.order_by(Result.submitted_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    quizzes = Quiz.query.order_by(Quiz.title).all()
    return render_template('admin/results.html', results=results,
                           quizzes=quizzes, current_quiz=quiz_id)


@admin_bp.route('/results/<int:result_id>')
@admin_required
def view_result(result_id):
    from app.models.quiz import Result
    result  = Result.query.get_or_404(result_id)
    answers = result.answers.all()
    return render_template('admin/result_detail.html', result=result, answers=answers)


# ─── STUDENT DETAIL ───────────────────────────────────────────────────────────

@admin_bp.route('/students/<int:student_id>')
@admin_required
def student_detail(student_id):
    student = User.query.get_or_404(student_id)
    results = student.results.order_by(Result.submitted_at.desc()).all()
    return render_template('admin/student_detail.html', student=student, results=results)


# ─── QUIZ EDIT ────────────────────────────────────────────────────────────────

@admin_bp.route('/quizzes/<int:quiz_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_quiz(quiz_id):
    from app.forms.quiz_forms import QuizForm
    quiz = Quiz.query.get_or_404(quiz_id)
    form = QuizForm(obj=quiz)
    form.category_id.choices = [(c.id, c.name) for c in Category.query.order_by(Category.name).all()]

    if form.validate_on_submit():
        quiz.title          = form.title.data.strip()
        quiz.description    = form.description.data
        quiz.time_limit     = form.time_limit.data
        quiz.pass_percentage= form.pass_percentage.data or 50.0
        quiz.is_published   = form.is_published.data
        db.session.commit()
        flash(f'Quiz "{quiz.title}" updated!', 'success')
        return redirect(url_for('admin.quizzes'))

    return render_template('admin/quiz_form.html', form=form,
                           title='Edit Quiz', quiz=quiz)


# ─── EXPORT RESULTS (CSV) ─────────────────────────────────────────────────────

@admin_bp.route('/results/export')
@admin_required
def export_results():
    import csv, io
    from flask import Response

    quiz_id = request.args.get('quiz', 0, type=int)
    query   = Result.query
    if quiz_id:
        query = query.filter_by(quiz_id=quiz_id)
    results = query.order_by(Result.submitted_at.desc()).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        'Result ID', 'Student', 'Username', 'Email',
        'Quiz', 'Category', 'Total Questions', 'Correct',
        'Wrong', 'Marks', 'Percentage', 'Grade',
        'Time Taken (s)', 'Submitted At'
    ])
    for r in results:
        writer.writerow([
            r.id,
            r.student.full_name or r.student.username,
            r.student.username,
            r.student.email,
            r.quiz.title,
            r.quiz.category.name,
            r.total_questions,
            r.correct_answers,
            r.wrong_answers,
            r.marks_obtained,
            round(r.percentage, 2),
            r.grade,
            r.time_taken or '',
            r.submitted_at.strftime('%Y-%m-%d %H:%M:%S'),
        ])

    output.seek(0)
    filename = f'results_export_{quiz_id or "all"}.csv'
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename={filename}'}
    )


# ─── EXPORT QUESTIONS (CSV) ───────────────────────────────────────────────────

@admin_bp.route('/questions/export')
@admin_required
def export_questions():
    import csv, io
    from flask import Response

    cat_id = request.args.get('category', 0, type=int)
    query  = Question.query
    if cat_id:
        query = query.filter_by(category_id=cat_id)
    questions = query.order_by(Question.category_id, Question.id).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Question', 'OptionA', 'OptionB', 'OptionC', 'OptionD',
                     'CorrectAnswer', 'Category', 'Difficulty', 'Explanation'])
    for q in questions:
        writer.writerow([
            q.question_text, q.option_a, q.option_b, q.option_c, q.option_d,
            q.correct_answer, q.category.name, q.difficulty, q.explanation or ''
        ])

    output.seek(0)
    filename = f'questions_export_{cat_id or "all"}.csv'
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename={filename}'}
    )
