from datetime import datetime
from app.extensions import db


class Quiz(db.Model):
    __tablename__ = 'quizzes'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)
    num_questions = db.Column(db.Integer, nullable=False, default=10)
    time_limit = db.Column(db.Integer, nullable=False, default=30)  # minutes
    is_published = db.Column(db.Boolean, default=False)
    pass_percentage = db.Column(db.Float, default=50.0)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    quiz_questions = db.relationship('QuizQuestion', backref='quiz', lazy='dynamic', cascade='all, delete-orphan')
    results = db.relationship('Result', backref='quiz', lazy='dynamic', cascade='all, delete-orphan')
    creator = db.relationship('User', foreign_keys=[created_by])

    def get_questions(self):
        return [qq.question for qq in self.quiz_questions.order_by(QuizQuestion.order).all()]

    def get_attempt_count(self):
        return self.results.count()

    def get_average_score(self):
        results = self.results.all()
        if not results:
            return 0
        return round(sum(r.percentage for r in results) / len(results), 1)

    def has_been_taken_by(self, user_id):
        return self.results.filter_by(student_id=user_id).first() is not None

    def __repr__(self):
        return f'<Quiz {self.title}>'


class QuizQuestion(db.Model):
    __tablename__ = 'quiz_questions'

    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quizzes.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id'), nullable=False)
    order = db.Column(db.Integer, default=0)

    __table_args__ = (
        db.UniqueConstraint('quiz_id', 'question_id', name='unique_quiz_question'),
    )

    def __repr__(self):
        return f'<QuizQuestion quiz={self.quiz_id} q={self.question_id}>'


class Result(db.Model):
    __tablename__ = 'results'

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quizzes.id'), nullable=False)
    total_questions = db.Column(db.Integer, nullable=False)
    correct_answers = db.Column(db.Integer, nullable=False, default=0)
    wrong_answers = db.Column(db.Integer, nullable=False, default=0)
    marks_obtained = db.Column(db.Float, nullable=False, default=0)
    percentage = db.Column(db.Float, nullable=False, default=0)
    grade = db.Column(db.String(5), nullable=False, default='F')
    time_taken = db.Column(db.Integer, nullable=True)  # seconds
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    answers = db.relationship('StudentAnswer', backref='result', lazy='dynamic', cascade='all, delete-orphan')

    def calculate_grade(self):
        if self.percentage >= 90:
            return 'A+'
        elif self.percentage >= 80:
            return 'A'
        elif self.percentage >= 70:
            return 'B'
        elif self.percentage >= 60:
            return 'C'
        elif self.percentage >= 50:
            return 'D'
        else:
            return 'F'

    def passed(self):
        return self.percentage >= (self.quiz.pass_percentage if self.quiz else 50)

    def __repr__(self):
        return f'<Result student={self.student_id} quiz={self.quiz_id} score={self.percentage}%>'


class StudentAnswer(db.Model):
    __tablename__ = 'student_answers'

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    result_id = db.Column(db.Integer, db.ForeignKey('results.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id'), nullable=False)
    selected_answer = db.Column(db.String(1), nullable=True)  # null = skipped
    is_correct = db.Column(db.Boolean, nullable=False, default=False)
    answered_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<StudentAnswer q={self.question_id} ans={self.selected_answer} correct={self.is_correct}>'
