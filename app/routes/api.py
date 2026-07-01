"""
app/routes/api.py
=================
Internal JSON API used by the frontend JavaScript.
All endpoints require authentication; admin endpoints require the admin role.
"""
from functools import wraps
from flask import Blueprint, jsonify, request, abort
from flask_login import login_required, current_user
from sqlalchemy import func, desc

from app.extensions import db
from app.models.user import User
from app.models.question import Category, Question
from app.models.quiz import Quiz, Result, StudentAnswer

api_bp = Blueprint('api', __name__, url_prefix='/api')


# ─── Auth helpers ─────────────────────────────────────────────────────────────
def admin_required_api(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            return jsonify({'error': 'Admin access required'}), 403
        return f(*args, **kwargs)
    return login_required(decorated)


# ─── Ping / health ────────────────────────────────────────────────────────────
@api_bp.route('/ping')
def ping():
    return jsonify({'status': 'ok', 'version': '1.0'})


# ─── Question search (AJAX) ───────────────────────────────────────────────────
@api_bp.route('/questions/search')
@admin_required_api
def search_questions():
    q        = request.args.get('q', '').strip()
    cat_id   = request.args.get('category', 0, type=int)
    diff     = request.args.get('difficulty', '')
    page     = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)

    query = Question.query
    if q:
        query = query.filter(Question.question_text.ilike(f'%{q}%'))
    if cat_id:
        query = query.filter_by(category_id=cat_id)
    if diff in ('easy', 'medium', 'hard'):
        query = query.filter_by(difficulty=diff)

    pagination = query.order_by(desc(Question.created_at)).paginate(
        page=page, per_page=min(per_page, 50), error_out=False
    )

    return jsonify({
        'questions': [{
            'id':            q.id,
            'text':          q.question_text[:120],
            'category':      q.category.name,
            'category_color': q.category.color,
            'difficulty':    q.difficulty,
            'correct':       q.correct_answer,
        } for q in pagination.items],
        'total':   pagination.total,
        'pages':   pagination.pages,
        'current': pagination.page,
    })


# ─── Category list (for dynamic selects) ─────────────────────────────────────
@api_bp.route('/categories')
@login_required
def list_categories():
    cats = Category.query.order_by(Category.name).all()
    return jsonify([{
        'id':    c.id,
        'name':  c.name,
        'color': c.color,
        'count': c.get_question_count(),
    } for c in cats])


# ─── Category question count ──────────────────────────────────────────────────
@api_bp.route('/categories/<int:cat_id>/count')
@admin_required_api
def category_question_count(cat_id):
    cat = Category.query.get_or_404(cat_id)
    return jsonify({'category_id': cat_id, 'count': cat.get_question_count()})


# ─── Dashboard stats (live refresh) ──────────────────────────────────────────
@api_bp.route('/stats/admin')
@admin_required_api
def admin_stats():
    total_students      = User.query.filter_by(role='student').count()
    total_questions     = Question.query.count()
    total_quizzes_taken = Result.query.count()
    results = Result.query.all()
    avg_score = round(
        sum(r.percentage for r in results) / len(results), 1
    ) if results else 0

    return jsonify({
        'total_students':      total_students,
        'total_questions':     total_questions,
        'total_quizzes_taken': total_quizzes_taken,
        'avg_score':           avg_score,
    })


@api_bp.route('/stats/student')
@login_required
def student_stats():
    if current_user.is_admin:
        return jsonify({'error': 'Student endpoint'}), 400
    results = current_user.results.all()
    return jsonify({
        'total_quizzes': len(results),
        'avg_score':     current_user.get_average_score(),
        'best_score':    max((r.percentage for r in results), default=0),
        'a_plus_count':  sum(1 for r in results if r.grade == 'A+'),
    })


# ─── Per-quiz stats (admin) ───────────────────────────────────────────────────
@api_bp.route('/quiz/<int:quiz_id>/stats')
@admin_required_api
def quiz_stats(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    results = quiz.results.all()
    if not results:
        return jsonify({'quiz_id': quiz_id, 'attempts': 0, 'avg_score': 0,
                        'pass_rate': 0, 'grade_distribution': {}})

    grade_dist = {}
    for r in results:
        grade_dist[r.grade] = grade_dist.get(r.grade, 0) + 1

    passed   = sum(1 for r in results if r.percentage >= quiz.pass_percentage)
    pass_rate = round((passed / len(results)) * 100, 1)

    return jsonify({
        'quiz_id':           quiz_id,
        'title':             quiz.title,
        'attempts':          len(results),
        'avg_score':         round(sum(r.percentage for r in results) / len(results), 1),
        'best_score':        max(r.percentage for r in results),
        'worst_score':       min(r.percentage for r in results),
        'pass_rate':         pass_rate,
        'grade_distribution': grade_dist,
    })


# ─── Student performance timeline ─────────────────────────────────────────────
@api_bp.route('/student/<int:student_id>/timeline')
@admin_required_api
def student_timeline(student_id):
    student = User.query.get_or_404(student_id)
    results = (student.results
               .order_by(Result.submitted_at.asc())
               .limit(20).all())
    return jsonify({
        'student': student.full_name or student.username,
        'data': [{
            'date':       r.submitted_at.strftime('%Y-%m-%d'),
            'quiz':       r.quiz.title[:30],
            'percentage': r.percentage,
            'grade':      r.grade,
        } for r in results]
    })


# ─── Leaderboard JSON ─────────────────────────────────────────────────────────
@api_bp.route('/leaderboard')
@login_required
def leaderboard_json():
    from app.services.quiz_service import QuizService
    board = QuizService.get_leaderboard(limit=10)
    return jsonify([{
        'rank':          i + 1,
        'name':          entry['full_name'],
        'avg_score':     entry['average_score'],
        'best_score':    entry['best_score'],
        'total_quizzes': entry['total_quizzes'],
        'is_me':         entry['user'].id == current_user.id,
    } for i, entry in enumerate(board)])


# ─── Quick question count for quiz form (live feedback) ──────────────────────
@api_bp.route('/quiz/question-count')
@admin_required_api
def quiz_question_count():
    cat_id = request.args.get('category_id', 0, type=int)
    if not cat_id:
        return jsonify({'count': 0})
    count = Question.query.filter_by(category_id=cat_id).count()
    return jsonify({'category_id': cat_id, 'count': count})


# ─── Recent activity feed (admin dashboard widget) ────────────────────────────
@api_bp.route('/activity')
@admin_required_api
def recent_activity():
    recent = (Result.query
              .order_by(desc(Result.submitted_at))
              .limit(15).all())
    return jsonify([{
        'student':     r.student.full_name or r.student.username,
        'quiz':        r.quiz.title[:30],
        'percentage':  r.percentage,
        'grade':       r.grade,
        'submitted_at': r.submitted_at.strftime('%b %d, %H:%M'),
    } for r in recent])
