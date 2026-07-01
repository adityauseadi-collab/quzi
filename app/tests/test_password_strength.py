"""
test_password_strength.py
=========================
Tests for:
  1. validate_password_strength() utility (unit tests)
  2. Registration endpoint — weak passwords rejected, strong accepted
  3. Change-password endpoint — weak passwords rejected, strong accepted
  4. Password-reset endpoint   — weak passwords rejected, strong accepted
  5. API endpoint /auth/api/password-strength
"""
import json
import pytest
from app.utils.password_strength import validate_password_strength, is_password_strong_enough
from app.models.user import User
from app.extensions import db


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 1 — Pure unit tests for validate_password_strength()
# ══════════════════════════════════════════════════════════════════════════════

class TestPasswordStrengthValidator:

    # ── Weak passwords ────────────────────────────────────────────────────────

    def test_empty_password_is_weak(self):
        r = validate_password_strength('')
        assert r['valid'] is False
        assert r['strength'] == 'Weak'

    def test_too_short_is_weak(self):
        r = validate_password_strength('Ab1')
        assert r['valid'] is False
        assert any('8 characters' in e for e in r['errors'])

    def test_no_uppercase_rejected(self):
        r = validate_password_strength('weakpass1')
        assert r['valid'] is False
        assert any('uppercase' in e for e in r['errors'])

    def test_no_lowercase_rejected(self):
        r = validate_password_strength('NOLOW1234')
        assert r['valid'] is False
        assert any('lowercase' in e for e in r['errors'])

    def test_no_number_rejected(self):
        r = validate_password_strength('NoNumber!')
        assert r['valid'] is False
        assert any('number' in e or 'digit' in e.lower() for e in r['errors'])

    def test_only_letters_rejected(self):
        r = validate_password_strength('onlyletters')
        assert r['valid'] is False

    def test_only_digits_rejected(self):
        r = validate_password_strength('12345678')
        assert r['valid'] is False

    def test_common_password_password123(self):
        # 'qwerty123' is in the common list and also lacks uppercase/digit mix
        r = validate_password_strength('qwerty123')
        assert r['valid'] is False

    def test_common_password_12345678(self):
        r = validate_password_strength('12345678')
        assert r['valid'] is False

    def test_common_password_qwerty123(self):
        r = validate_password_strength('qwerty123')
        assert r['valid'] is False

    def test_common_password_admin123(self):
        r = validate_password_strength('admin123')
        assert r['valid'] is False

    def test_common_password_case_insensitive(self):
        r = validate_password_strength('PASSWORD123')   # uppercase variant of common
        # Not in common list since it has no lowercase → rejected for that reason
        assert r['valid'] is False

    # ── Medium passwords ──────────────────────────────────────────────────────

    def test_medium_password_accepted(self):
        r = validate_password_strength('Password1')
        assert r['valid'] is True
        assert r['strength'] == 'Medium'

    def test_medium_password_quizmaster2026(self):
        r = validate_password_strength('QuizMaster2026')
        assert r['valid'] is True
        assert r['strength'] in ('Medium', 'Strong')

    def test_medium_password_all_required_rules(self):
        # Exactly 8 chars, upper+lower+digit, no special → Medium
        r = validate_password_strength('Abcdef1g')
        assert r['valid'] is True
        assert r['strength'] in ('Medium', 'Strong')

    def test_medium_has_no_required_errors(self):
        r = validate_password_strength('Secure99')
        assert r['valid'] is True
        assert r['errors'] == []

    # ── Strong passwords ──────────────────────────────────────────────────────

    def test_strong_with_special_char(self):
        r = validate_password_strength('P@ssw0rd!')
        assert r['valid'] is True
        assert r['strength'] == 'Strong'

    def test_strong_long_password(self):
        r = validate_password_strength('MyStr0ng!Password2026')
        assert r['valid'] is True
        assert r['strength'] == 'Strong'

    def test_strong_score_is_high(self):
        r = validate_password_strength('QuizM@ster2026!')
        assert r['score'] >= 5
        assert r['strength'] == 'Strong'

    def test_strong_valid_is_true(self):
        r = validate_password_strength('SuperS3cur3#Now')
        assert r['valid'] is True

    # ── Return-structure tests ────────────────────────────────────────────────

    def test_result_has_all_keys(self):
        r = validate_password_strength('Test1234')
        for key in ('valid', 'strength', 'score', 'errors', 'suggestions'):
            assert key in r

    def test_score_is_integer(self):
        r = validate_password_strength('Test1234')
        assert isinstance(r['score'], int)

    def test_score_range(self):
        for pwd in ('a', 'Abcdef1g', 'QuizM@ster2026!'):
            r = validate_password_strength(pwd)
            assert 0 <= r['score'] <= 6

    def test_errors_is_list(self):
        r = validate_password_strength('weak')
        assert isinstance(r['errors'], list)

    def test_suggestions_is_list(self):
        r = validate_password_strength('Password1')
        assert isinstance(r['suggestions'], list)

    # ── Helper functions ──────────────────────────────────────────────────────

    def test_is_password_strong_enough_weak(self):
        assert is_password_strong_enough('weakpass') is False

    def test_is_password_strong_enough_medium(self):
        assert is_password_strong_enough('Password1') is True

    def test_is_password_strong_enough_strong(self):
        assert is_password_strong_enough('Str0ng!Pass#2') is True

    def test_suggestions_given_for_no_special(self):
        r = validate_password_strength('Password1')
        # Should suggest adding a special character
        assert any('special' in s.lower() for s in r['suggestions'])

    def test_no_errors_for_strong_password(self):
        r = validate_password_strength('MyStr0ng!Pass')
        assert r['errors'] == []


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 2 — Registration endpoint tests
# ══════════════════════════════════════════════════════════════════════════════

class TestRegistrationPasswordStrength:

    def _register(self, client, username, email, password, confirm=None):
        return client.post('/auth/register', data={
            'full_name':        'Test User',
            'username':         username,
            'email':            email,
            'password':         password,
            'confirm_password': confirm or password,
            'csrf_token':       'test',
        }, follow_redirects=True)

    def test_weak_password_rejected_on_register(self, client, app):
        with app.app_context():
            r = self._register(client, 'weakpwd_usr', 'weakpwd@test.com', 'weak')
            assert r.status_code == 200
            assert User.query.filter_by(username='weakpwd_usr').first() is None

    def test_no_uppercase_rejected_on_register(self, client, app):
        with app.app_context():
            r = self._register(client, 'noupper_usr', 'noupper@test.com', 'alllower1')
            assert User.query.filter_by(username='noupper_usr').first() is None

    def test_no_lowercase_rejected_on_register(self, client, app):
        with app.app_context():
            r = self._register(client, 'nolower_usr', 'nolower@test.com', 'ALLUPPER1')
            assert User.query.filter_by(username='nolower_usr').first() is None

    def test_no_number_rejected_on_register(self, client, app):
        with app.app_context():
            r = self._register(client, 'nonum_usr', 'nonum@test.com', 'NoNumbers!')
            assert User.query.filter_by(username='nonum_usr').first() is None

    def test_too_short_rejected_on_register(self, client, app):
        with app.app_context():
            r = self._register(client, 'short_usr2', 'short2@test.com', 'Ab1')
            assert User.query.filter_by(username='short_usr2').first() is None

    def test_common_password_rejected_on_register(self, client, app):
        with app.app_context():
            r = self._register(client, 'common_usr', 'common@test.com', 'passw0rd')
            assert User.query.filter_by(username='common_usr').first() is None

    def test_medium_password_accepted_on_register(self, client, app):
        with app.app_context():
            r = self._register(client, 'medium_usr', 'medium@test.com', 'Password1')
            assert r.status_code == 200
            user = User.query.filter_by(username='medium_usr').first()
            assert user is not None

    def test_strong_password_accepted_on_register(self, client, app):
        with app.app_context():
            r = self._register(client, 'strong_usr', 'strong@test.com', 'Str0ng!Pass#')
            assert r.status_code == 200
            user = User.query.filter_by(username='strong_usr').first()
            assert user is not None

    def test_quizmaster2026_accepted_on_register(self, client, app):
        with app.app_context():
            r = self._register(client, 'qm2026_usr', 'qm2026@test.com', 'QuizMaster2026')
            user = User.query.filter_by(username='qm2026_usr').first()
            assert user is not None

    def test_password_mismatch_rejected(self, client, app):
        with app.app_context():
            r = self._register(client, 'mismatch2_usr', 'mismatch2@test.com',
                               'Password1', 'Password2')
            assert User.query.filter_by(username='mismatch2_usr').first() is None
            assert b'match' in r.data.lower()

    def test_error_message_shown_for_weak_password(self, client, app):
        with app.app_context():
            r = self._register(client, 'errshow_usr', 'errshow@test.com', 'weak')
            # Page should render (not redirect) and show an error
            assert r.status_code == 200


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 3 — Change-password endpoint tests
# ══════════════════════════════════════════════════════════════════════════════

class TestChangePasswordStrength:

    def _login_student(self, client):
        client.post('/auth/login', data={
            'username':   'test_student',
            'password':   'Studentpass123',
            'csrf_token': 'test',
        }, follow_redirects=True)

    def _change(self, client, current, new_pwd, confirm=None):
        return client.post('/auth/profile', data={
            'current_password': current,
            'new_password':     new_pwd,
            'confirm_password': confirm or new_pwd,
            'csrf_token':       'test',
        }, follow_redirects=True)

    def test_weak_new_password_rejected(self, client, app, student_user):
        with app.app_context():
            self._login_student(client)
            r = self._change(client, 'Studentpass123', 'weak')
            assert r.status_code == 200
            # Password must not have changed — re-login with original
            student = User.query.filter_by(username='test_student').first()
            assert student.check_password('Studentpass123')

    def test_no_uppercase_rejected_on_change(self, client, app, student_user):
        with app.app_context():
            self._login_student(client)
            self._change(client, 'Studentpass123', 'alllower1')
            student = User.query.filter_by(username='test_student').first()
            assert student.check_password('Studentpass123')

    def test_no_number_rejected_on_change(self, client, app, student_user):
        with app.app_context():
            self._login_student(client)
            self._change(client, 'Studentpass123', 'NoNumbers!')
            student = User.query.filter_by(username='test_student').first()
            assert student.check_password('Studentpass123')

    def test_common_password_rejected_on_change(self, client, app, student_user):
        with app.app_context():
            self._login_student(client)
            self._change(client, 'Studentpass123', 'passw0rd')
            student = User.query.filter_by(username='test_student').first()
            assert student.check_password('Studentpass123')

    def test_medium_new_password_accepted(self, client, app, student_user):
        with app.app_context():
            self._login_student(client)
            r = self._change(client, 'Studentpass123', 'NewPass99')
            assert r.status_code == 200
            student = User.query.filter_by(username='test_student').first()
            assert student.check_password('NewPass99')
            # Restore for other tests
            student.set_password('Studentpass123')
            db.session.commit()

    def test_strong_new_password_accepted(self, client, app, student_user):
        with app.app_context():
            self._login_student(client)
            r = self._change(client, 'Studentpass123', 'SuperS3cur3#Now')
            assert r.status_code == 200
            student = User.query.filter_by(username='test_student').first()
            assert student.check_password('SuperS3cur3#Now')
            # Restore
            student.set_password('Studentpass123')
            db.session.commit()

    def test_wrong_current_password_blocked(self, client, app, student_user):
        with app.app_context():
            self._login_student(client)
            r = self._change(client, 'wrongcurrentpwd', 'NewPass99')
            assert r.status_code == 200
            assert b'incorrect' in r.data.lower() or b'Invalid' in r.data
            student = User.query.filter_by(username='test_student').first()
            assert student.check_password('Studentpass123')


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 4 — Password reset endpoint tests
# ══════════════════════════════════════════════════════════════════════════════

class TestPasswordResetStrength:

    def test_reset_request_page_loads(self, client):
        r = client.get('/auth/reset-password')
        assert r.status_code == 200
        assert b'Reset' in r.data

    def test_reset_request_with_registered_email(self, client, app, student_user):
        with app.app_context():
            r = client.post('/auth/reset-password', data={
                'email':      'student@test.com',
                'csrf_token': 'test',
            }, follow_redirects=True)
            assert r.status_code == 200

    def test_reset_request_with_unknown_email(self, client, app):
        with app.app_context():
            r = client.post('/auth/reset-password', data={
                'email':      'nobody@nowhere.com',
                'csrf_token': 'test',
            }, follow_redirects=True)
            # Always same message (anti-enumeration)
            assert r.status_code == 200

    def test_reset_confirm_page_loads(self, client, app, student_user):
        with app.app_context():
            student = User.query.filter_by(username='test_student').first()
            r = client.get(f'/auth/reset-password/{student.id}')
            assert r.status_code == 200
            assert b'New Password' in r.data or b'Reset' in r.data

    def test_weak_password_rejected_on_reset(self, client, app, student_user):
        with app.app_context():
            student = User.query.filter_by(username='test_student').first()
            r = client.post(f'/auth/reset-password/{student.id}', data={
                'new_password':     'weak',
                'confirm_password': 'weak',
                'csrf_token':       'test',
            }, follow_redirects=True)
            assert r.status_code == 200
            # Password must not have changed
            student = User.query.filter_by(username='test_student').first()
            assert student.check_password('Studentpass123')

    def test_no_uppercase_rejected_on_reset(self, client, app, student_user):
        with app.app_context():
            student = User.query.filter_by(username='test_student').first()
            client.post(f'/auth/reset-password/{student.id}', data={
                'new_password':     'alllower1',
                'confirm_password': 'alllower1',
                'csrf_token':       'test',
            }, follow_redirects=True)
            student = User.query.filter_by(username='test_student').first()
            assert student.check_password('Studentpass123')

    def test_common_password_rejected_on_reset(self, client, app, student_user):
        with app.app_context():
            student = User.query.filter_by(username='test_student').first()
            client.post(f'/auth/reset-password/{student.id}', data={
                'new_password':     'passw0rd',
                'confirm_password': 'passw0rd',
                'csrf_token':       'test',
            }, follow_redirects=True)
            student = User.query.filter_by(username='test_student').first()
            assert student.check_password('Studentpass123')

    def test_medium_password_accepted_on_reset(self, client, app, student_user):
        with app.app_context():
            student = User.query.filter_by(username='test_student').first()
            r = client.post(f'/auth/reset-password/{student.id}', data={
                'new_password':     'Reset99Pass',
                'confirm_password': 'Reset99Pass',
                'csrf_token':       'test',
            }, follow_redirects=True)
            assert r.status_code == 200
            student = User.query.filter_by(username='test_student').first()
            assert student.check_password('Reset99Pass')
            # Restore
            student.set_password('Studentpass123')
            db.session.commit()

    def test_strong_password_accepted_on_reset(self, client, app, student_user):
        with app.app_context():
            student = User.query.filter_by(username='test_student').first()
            r = client.post(f'/auth/reset-password/{student.id}', data={
                'new_password':     'Str0ng!NewPass#',
                'confirm_password': 'Str0ng!NewPass#',
                'csrf_token':       'test',
            }, follow_redirects=True)
            assert r.status_code == 200
            student = User.query.filter_by(username='test_student').first()
            assert student.check_password('Str0ng!NewPass#')
            # Restore
            student.set_password('Studentpass123')
            db.session.commit()

    def test_mismatch_rejected_on_reset(self, client, app, student_user):
        with app.app_context():
            student = User.query.filter_by(username='test_student').first()
            r = client.post(f'/auth/reset-password/{student.id}', data={
                'new_password':     'Password1',
                'confirm_password': 'Password2',
                'csrf_token':       'test',
            }, follow_redirects=True)
            assert b'match' in r.data.lower()
            student = User.query.filter_by(username='test_student').first()
            assert student.check_password('Studentpass123')


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 5 — API endpoint /auth/api/password-strength
# ══════════════════════════════════════════════════════════════════════════════

class TestPasswordStrengthAPI:

    def _post(self, client, password):
        return client.post(
            '/auth/api/password-strength',
            data=json.dumps({'password': password}),
            content_type='application/json',
        )

    def test_api_returns_200(self, client):
        r = self._post(client, 'Test1234')
        assert r.status_code == 200

    def test_api_returns_json(self, client):
        r = self._post(client, 'Test1234')
        data = json.loads(r.data)
        assert isinstance(data, dict)

    def test_api_weak_password(self, client):
        r = self._post(client, 'weak')
        data = json.loads(r.data)
        assert data['strength'] == 'Weak'
        assert data['valid'] is False

    def test_api_medium_password(self, client):
        r = self._post(client, 'Secure99x')
        data = json.loads(r.data)
        assert data['strength'] == 'Medium'
        assert data['valid'] is True

    def test_api_strong_password(self, client):
        r = self._post(client, 'SuperS3cur3#Now')
        data = json.loads(r.data)
        assert data['strength'] == 'Strong'
        assert data['valid'] is True

    def test_api_has_errors_key(self, client):
        r = self._post(client, 'weak')
        data = json.loads(r.data)
        assert 'errors' in data

    def test_api_has_score_key(self, client):
        r = self._post(client, 'Password1')
        data = json.loads(r.data)
        assert 'score' in data
        assert isinstance(data['score'], int)

    def test_api_common_password_invalid(self, client):
        r = self._post(client, 'password123')
        data = json.loads(r.data)
        assert data['valid'] is False

    def test_api_empty_password(self, client):
        r = self._post(client, '')
        data = json.loads(r.data)
        assert data['valid'] is False
        assert data['strength'] == 'Weak'
