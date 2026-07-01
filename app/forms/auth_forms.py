from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError
from app.models.user import User
from app.utils.password_strength import validate_password_strength


def _check_strength(form, field):
    """WTForms validator — rejects any password that doesn't reach Medium."""
    result = validate_password_strength(field.data or '')
    if not result['valid']:
        # Surface the first (most important) error as the form field message
        raise ValidationError(result['errors'][0] if result['errors'] else
                              'Password is too weak. Please choose a stronger password.')


class LoginForm(FlaskForm):
    username    = StringField('Username or Email', validators=[DataRequired()])
    password    = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit      = SubmitField('Sign In')


class RegistrationForm(FlaskForm):
    full_name        = StringField('Full Name', validators=[DataRequired(), Length(min=2, max=150)])
    username         = StringField('Username',  validators=[DataRequired(), Length(min=3, max=80)])
    email            = StringField('Email',     validators=[DataRequired(), Email()])
    password         = PasswordField('Password', validators=[DataRequired(), Length(min=8), _check_strength])
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(), EqualTo('password', message='Passwords must match.')
    ])
    submit = SubmitField('Register')

    def validate_username(self, field):
        if User.query.filter_by(username=field.data).first():
            raise ValidationError('Username already taken. Please choose another.')

    def validate_email(self, field):
        if User.query.filter_by(email=field.data.lower()).first():
            raise ValidationError('Email already registered.')


class ChangePasswordForm(FlaskForm):
    current_password = PasswordField('Current Password', validators=[DataRequired()])
    new_password     = PasswordField('New Password',     validators=[DataRequired(), Length(min=8), _check_strength])
    confirm_password = PasswordField('Confirm New Password', validators=[
        DataRequired(), EqualTo('new_password', message='Passwords must match.')
    ])
    submit = SubmitField('Change Password')


class ResetPasswordRequestForm(FlaskForm):
    """Step 1: user supplies their email address."""
    email  = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Send Reset Link')


class ResetPasswordForm(FlaskForm):
    """Step 2: user sets a new password (simulated reset — no email required for demo)."""
    new_password     = PasswordField('New Password',     validators=[DataRequired(), Length(min=8), _check_strength])
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(), EqualTo('new_password', message='Passwords must match.')
    ])
    submit = SubmitField('Reset Password')
