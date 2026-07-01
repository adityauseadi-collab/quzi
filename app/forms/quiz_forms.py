from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import (StringField, TextAreaField, SelectField, IntegerField,
                     BooleanField, SubmitField, FloatField)
from wtforms.validators import DataRequired, Length, NumberRange, Optional


class CategoryForm(FlaskForm):
    name = StringField('Category Name', validators=[DataRequired(), Length(min=2, max=100)])
    description = TextAreaField('Description', validators=[Optional(), Length(max=500)])
    color = StringField('Color', default='#6366f1')
    submit = SubmitField('Save Category')


class QuestionForm(FlaskForm):
    question_text = TextAreaField('Question', validators=[DataRequired(), Length(min=5)])
    option_a = StringField('Option A', validators=[DataRequired(), Length(max=500)])
    option_b = StringField('Option B', validators=[DataRequired(), Length(max=500)])
    option_c = StringField('Option C', validators=[DataRequired(), Length(max=500)])
    option_d = StringField('Option D', validators=[DataRequired(), Length(max=500)])
    correct_answer = SelectField('Correct Answer', choices=[
        ('A', 'A'), ('B', 'B'), ('C', 'C'), ('D', 'D')
    ], validators=[DataRequired()])
    explanation = TextAreaField('Explanation (Optional)', validators=[Optional()])
    difficulty = SelectField('Difficulty', choices=[
        ('easy', 'Easy'), ('medium', 'Medium'), ('hard', 'Hard')
    ], default='medium')
    category_id = SelectField('Category', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Save Question')


class QuizForm(FlaskForm):
    title = StringField('Quiz Title', validators=[DataRequired(), Length(min=3, max=200)])
    description = TextAreaField('Description', validators=[Optional()])
    category_id = SelectField('Category', coerce=int, validators=[DataRequired()])
    num_questions = IntegerField('Number of Questions', validators=[
        DataRequired(), NumberRange(min=1, max=100)
    ], default=10)
    time_limit = IntegerField('Time Limit (minutes)', validators=[
        DataRequired(), NumberRange(min=1, max=300)
    ], default=30)
    pass_percentage = FloatField('Pass Percentage', validators=[
        Optional(), NumberRange(min=0, max=100)
    ], default=50.0)
    is_published = BooleanField('Publish Quiz', default=False)
    submit = SubmitField('Save Quiz')


class ImportQuestionsForm(FlaskForm):
    file = FileField('Upload File', validators=[
        DataRequired(),
        FileAllowed(['xlsx', 'csv'], 'Only Excel and CSV files allowed!')
    ])
    category_id = SelectField('Default Category', coerce=int, validators=[Optional()])
    submit = SubmitField('Import Questions')


class SearchForm(FlaskForm):
    query = StringField('Search', validators=[Optional()])
    category = SelectField('Category', coerce=int, validators=[Optional()])
    submit = SubmitField('Search')
