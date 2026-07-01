from datetime import datetime
from flask import (Blueprint, render_template, redirect, url_for,
                   flash, request, jsonify)
from flask_login import login_user, logout_user, login_required, current_user
from app.extensions import db
from app.models.user import User
from app.forms.auth_forms import (LoginForm, RegistrationForm,
                                   ChangePasswordForm, ResetPasswordRequestForm,
                                   ResetPasswordForm)
from app.utils.password_strength import validate_password_strength

auth_bp = Blueprint('auth', __name__)


# ─── API: real-time strength check ────────────────────────────────────────────
@auth_bp.route('/api/password-strength', methods=['POST'])
def password_strength_api():
    """JSON endpoint consumed by the live strength meter (no CSRF needed for GET-like usage)."""
    password = request.get_json(silent=True, force=True) or {}
    password = password.get('password', '')
    result   = validate_password_strength(password)
    return jsonify(result)


# ─── LOGIN ────────────────────────────────────────────────────────────────────
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('admin.dashboard') if current_user.is_admin
                        else url_for('student.dashboard'))
    form = LoginForm()
    if form.validate_on_submit():
        identifier = form.username.data.strip()
        user = User.query.filter(
            (User.username == identifier) | (User.email == identifier.lower())
        ).first()
        if user and user.check_password(form.password.data):
            if not user.is_active:
                flash('Your account has been disabled. Please contact an administrator.', 'danger')
                return render_template('auth/login.html', form=form)
            login_user(user, remember=form.remember_me.data)
            user.last_login = datetime.utcnow()
            db.session.commit()
            flash(f'Welcome back, {user.full_name or user.username}!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or (
                url_for('admin.dashboard') if user.is_admin else url_for('student.dashboard')
            ))
        flash('Invalid username/email or password.', 'danger')
    return render_template('auth/login.html', form=form)


# ─── REGISTER ─────────────────────────────────────────────────────────────────
@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('student.dashboard'))
    form = RegistrationForm()
    if form.validate_on_submit():
        # Double-check strength server-side (belt & braces)
        result = validate_password_strength(form.password.data)
        if not result['valid']:
            for err in result['errors']:
                form.password.errors.append(err)
            return render_template('auth/register.html', form=form)

        user = User(
            full_name=form.full_name.data.strip(),
            username =form.username.data.strip(),
            email    =form.email.data.strip().lower(),
            role     ='student',
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        login_user(user)
        flash('Registration successful! Welcome to QuizMaster Pro!', 'success')
        return redirect(url_for('student.dashboard'))
    return render_template('auth/register.html', form=form)


# ─── LOGOUT ───────────────────────────────────────────────────────────────────
@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('auth.login'))


# ─── PROFILE / CHANGE PASSWORD ────────────────────────────────────────────────
@auth_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if not current_user.check_password(form.current_password.data):
            flash('Current password is incorrect.', 'danger')
            return render_template('auth/profile.html', form=form)

        # Server-side strength re-check
        result = validate_password_strength(form.new_password.data)
        if not result['valid']:
            for err in result['errors']:
                form.new_password.errors.append(err)
            return render_template('auth/profile.html', form=form)

        current_user.set_password(form.new_password.data)
        db.session.commit()
        flash('Password changed successfully!', 'success')
    return render_template('auth/profile.html', form=form)


# ─── PASSWORD RESET (simulated — no email server required) ───────────────────
@auth_bp.route('/reset-password', methods=['GET', 'POST'])
def reset_password_request():
    """Step 1: accept email and find user."""
    if current_user.is_authenticated:
        return redirect(url_for('student.dashboard'))
    form = ResetPasswordRequestForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.strip().lower()).first()
        # Always show the same message to avoid user enumeration
        flash('If that email is registered, a reset link has been sent. '
              'For this demo, click the link below to continue.', 'info')
        if user:
            # In production: send email with signed token.
            # Demo: redirect directly with user id in session-like param.
            return redirect(url_for('auth.reset_password_confirm', user_id=user.id))
        return redirect(url_for('auth.login'))
    return render_template('auth/reset_password_request.html', form=form)


@auth_bp.route('/reset-password/<int:user_id>', methods=['GET', 'POST'])
def reset_password_confirm(user_id):
    """Step 2: set a new password."""
    if current_user.is_authenticated:
        return redirect(url_for('student.dashboard'))
    user = User.query.get_or_404(user_id)
    form = ResetPasswordForm()
    if form.validate_on_submit():
        # Server-side strength check
        result = validate_password_strength(form.new_password.data)
        if not result['valid']:
            for err in result['errors']:
                form.new_password.errors.append(err)
            return render_template('auth/reset_password_confirm.html', form=form, user=user)

        user.set_password(form.new_password.data)
        db.session.commit()
        flash('Your password has been reset successfully. Please log in.', 'success')
        return redirect(url_for('auth.login'))
    return render_template('auth/reset_password_confirm.html', form=form, user=user)
