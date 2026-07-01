from datetime import datetime
from app.extensions import db


class Category(db.Model):
    __tablename__ = 'categories'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)
    color = db.Column(db.String(7), default='#6366f1')  # hex color
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    questions = db.relationship('Question', backref='category', lazy='dynamic')
    quizzes = db.relationship('Quiz', backref='category', lazy='dynamic')

    def get_question_count(self):
        return self.questions.count()

    def __repr__(self):
        return f'<Category {self.name}>'


class Question(db.Model):
    __tablename__ = 'questions'

    id = db.Column(db.Integer, primary_key=True)
    question_text = db.Column(db.Text, nullable=False)
    option_a = db.Column(db.String(500), nullable=False)
    option_b = db.Column(db.String(500), nullable=False)
    option_c = db.Column(db.String(500), nullable=False)
    option_d = db.Column(db.String(500), nullable=False)
    correct_answer = db.Column(db.String(1), nullable=False)  # 'A', 'B', 'C', or 'D'
    explanation = db.Column(db.Text, nullable=True)
    difficulty = db.Column(db.String(20), default='medium')  # easy, medium, hard
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    quiz_questions = db.relationship('QuizQuestion', backref='question', lazy='dynamic', cascade='all, delete-orphan')
    student_answers = db.relationship('StudentAnswer', backref='question', lazy='dynamic', cascade='all, delete-orphan')

    def get_options(self):
        return {
            'A': self.option_a,
            'B': self.option_b,
            'C': self.option_c,
            'D': self.option_d
        }

    def get_correct_option_text(self):
        return self.get_options().get(self.correct_answer, '')

    def get_times_answered(self):
        return self.student_answers.count()

    def get_times_wrong(self):
        return self.student_answers.filter_by(is_correct=False).count()

    def get_difficulty_rate(self):
        total = self.get_times_answered()
        if total == 0:
            return 0
        return round((self.get_times_wrong() / total) * 100, 1)

    def __repr__(self):
        return f'<Question {self.id}: {self.question_text[:50]}>'
