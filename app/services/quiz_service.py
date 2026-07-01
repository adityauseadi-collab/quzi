import random
from datetime import datetime
from app.extensions import db
from app.models.quiz import Quiz, QuizQuestion, Result, StudentAnswer
from app.models.question import Question, Category
from app.models.user import User


class QuizService:

    @staticmethod
    def create_quiz(title, description, category_id, num_questions, time_limit,
                    pass_percentage, is_published, created_by):
        quiz = Quiz(
            title=title,
            description=description,
            category_id=category_id,
            num_questions=num_questions,
            time_limit=time_limit,
            pass_percentage=pass_percentage,
            is_published=is_published,
            created_by=created_by
        )
        db.session.add(quiz)
        db.session.flush()

        # Randomly select questions from category
        questions = Question.query.filter_by(category_id=category_id).all()
        if len(questions) < num_questions:
            selected = questions
        else:
            selected = random.sample(questions, num_questions)

        for i, q in enumerate(selected):
            qq = QuizQuestion(quiz_id=quiz.id, question_id=q.id, order=i)
            db.session.add(qq)

        db.session.commit()
        return quiz

    @staticmethod
    def submit_quiz(student_id, quiz_id, answers, time_taken=None):
        """
        answers: dict of {question_id: selected_answer}
        """
        quiz = Quiz.query.get(quiz_id)
        if not quiz:
            return None

        questions = quiz.get_questions()
        correct = 0
        wrong = 0

        result = Result(
            student_id=student_id,
            quiz_id=quiz_id,
            total_questions=len(questions),
            time_taken=time_taken
        )
        db.session.add(result)
        db.session.flush()

        for q in questions:
            selected = answers.get(str(q.id))
            is_correct = (selected == q.correct_answer) if selected else False
            if selected:
                if is_correct:
                    correct += 1
                else:
                    wrong += 1

            sa = StudentAnswer(
                student_id=student_id,
                result_id=result.id,
                question_id=q.id,
                selected_answer=selected,
                is_correct=is_correct
            )
            db.session.add(sa)

        result.correct_answers = correct
        result.wrong_answers = wrong
        result.marks_obtained = float(correct)
        result.percentage = round((correct / len(questions)) * 100, 2) if questions else 0
        result.grade = result.calculate_grade()

        db.session.commit()

        # Send in-app notification to student
        try:
            from app.services.notification_service import NotificationService
            NotificationService.send_quiz_result(
                user_id=student_id,
                quiz_title=quiz.title,
                grade=result.grade,
                percentage=result.percentage,
                result_id=result.id
            )
        except Exception:
            pass   # notifications are non-critical

        return result

    @staticmethod
    def get_leaderboard(limit=10):
        students = User.query.filter_by(role='student', is_active=True).all()
        leaderboard = []
        for s in students:
            results = s.results.all()
            if not results:
                continue
            avg = round(sum(r.percentage for r in results) / len(results), 1)
            best = max(r.percentage for r in results)
            leaderboard.append({
                'user': s,
                'average_score': avg,
                'best_score': best,
                'total_quizzes': len(results),
                'full_name': s.full_name or s.username
            })
        leaderboard.sort(key=lambda x: (-x['average_score'], -x['total_quizzes']))
        return leaderboard[:limit]

    @staticmethod
    def get_admin_analytics():
        from sqlalchemy import func
        total_students = User.query.filter_by(role='student').count()
        total_questions = Question.query.count()
        total_quizzes_taken = Result.query.count()
        all_results = Result.query.all()
        avg_score = round(sum(r.percentage for r in all_results) / len(all_results), 1) if all_results else 0

        # Most difficult questions
        difficult_questions = db.session.query(
            Question,
            func.count(StudentAnswer.id).label('total'),
            func.sum(db.case((StudentAnswer.is_correct == False, 1), else_=0)).label('wrong')
        ).join(StudentAnswer).group_by(Question.id).order_by(
            db.text('wrong DESC')
        ).limit(5).all()

        # Category performance
        cat_stats = []
        for cat in Category.query.all():
            cat_results = db.session.query(Result).join(Quiz).filter(Quiz.category_id == cat.id).all()
            if cat_results:
                cat_avg = round(sum(r.percentage for r in cat_results) / len(cat_results), 1)
                cat_stats.append({'name': cat.name, 'avg': cat_avg, 'color': cat.color})

        # Monthly trends — convert Row objects to plain lists for JSON safety
        monthly_rows = db.session.query(
            func.strftime('%Y-%m', Result.submitted_at).label('month'),
            func.count(Result.id).label('count'),
            func.avg(Result.percentage).label('avg_score')
        ).group_by('month').order_by('month').limit(12).all()

        monthly = [
            [row[0], row[1], round(row[2], 1) if row[2] else 0]
            for row in monthly_rows
        ]

        return {
            'total_students': total_students,
            'total_questions': total_questions,
            'total_quizzes_taken': total_quizzes_taken,
            'avg_score': avg_score,
            'difficult_questions': difficult_questions,
            'cat_stats': cat_stats,
            'monthly': monthly
        }
