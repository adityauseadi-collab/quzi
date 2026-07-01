import pytest
from app.models.user import User
from app.extensions import db


class TestRegistration:
    def test_register_page_loads(self, client):
        r = client.get('/auth/register')
        assert r.status_code == 200
        assert b'Register' in r.data or b'Create Account' in r.data

    def test_register_new_user(self, client, app):
        with app.app_context():
            r = client.post('/auth/register', data={
                'full_name': 'New User',
                'username': 'newuser_reg',
                'email': 'newuser_reg@test.com',
                'password': 'NewUser99',
                'confirm_password': 'NewUser99',
                'csrf_token': 'test'
            }, follow_redirects=True)
            assert r.status_code == 200
            user = User.query.filter_by(username='newuser_reg').first()
            assert user is not None
            assert user.role == 'student'
            assert user.full_name == 'New User'

    def test_register_duplicate_username(self, client, app, student_user):
        with app.app_context():
            r = client.post('/auth/register', data={
                'full_name': 'Dup User',
                'username': 'test_student',
                'email': 'unique_dup@test.com',
                'password': 'NewUser99',
                'confirm_password': 'NewUser99',
                'csrf_token': 'test'
            }, follow_redirects=True)
            assert b'already taken' in r.data or b'already' in r.data

    def test_register_duplicate_email(self, client, app, student_user):
        with app.app_context():
            r = client.post('/auth/register', data={
                'full_name': 'Another User',
                'username': 'unique_username_dup',
                'email': 'student@test.com',
                'password': 'NewUser99',
                'confirm_password': 'NewUser99',
                'csrf_token': 'test'
            }, follow_redirects=True)
            assert b'already registered' in r.data or b'already' in r.data

    def test_register_password_mismatch(self, client, app):
        with app.app_context():
            r = client.post('/auth/register', data={
                'full_name': 'Mismatch User',
                'username': 'mismatch_usr',
                'email': 'mismatch@test.com',
                'password': 'NewUser99',
                'confirm_password': 'Different456',
                'csrf_token': 'test'
            }, follow_redirects=True)
            assert b'match' in r.data.lower()

    def test_register_short_password(self, client, app):
        with app.app_context():
            r = client.post('/auth/register', data={
                'full_name': 'Short Pass',
                'username': 'shortpass_usr',
                'email': 'shortpass@test.com',
                'password': '123',
                'confirm_password': '123',
                'csrf_token': 'test'
            }, follow_redirects=True)
            # Should fail validation
            assert User.query.filter_by(username='shortpass_usr').first() is None


class TestLogin:
    def test_login_page_loads(self, client):
        r = client.get('/auth/login')
        assert r.status_code == 200
        assert b'Sign In' in r.data or b'Login' in r.data

    def test_login_valid_student(self, client, app, student_user):
        with app.app_context():
            r = client.post('/auth/login', data={
                'username': 'test_student',
                'password': 'Studentpass123',
                'csrf_token': 'test'
            }, follow_redirects=True)
            assert r.status_code == 200

    def test_login_valid_admin(self, client, app, admin_user):
        with app.app_context():
            r = client.post('/auth/login', data={
                'username': 'test_admin',
                'password': 'Adminpass123',
                'csrf_token': 'test'
            }, follow_redirects=True)
            assert r.status_code == 200

    def test_login_invalid_password(self, client, app, student_user):
        with app.app_context():
            r = client.post('/auth/login', data={
                'username': 'test_student',
                'password': 'wrongpassword',
                'csrf_token': 'test'
            }, follow_redirects=True)
            assert b'Invalid' in r.data

    def test_login_nonexistent_user(self, client, app):
        with app.app_context():
            r = client.post('/auth/login', data={
                'username': 'ghost_user_xyz',
                'password': 'password',
                'csrf_token': 'test'
            }, follow_redirects=True)
            assert b'Invalid' in r.data

    def test_login_with_email(self, client, app, student_user):
        with app.app_context():
            r = client.post('/auth/login', data={
                'username': 'student@test.com',
                'password': 'Studentpass123',
                'csrf_token': 'test'
            }, follow_redirects=True)
            assert r.status_code == 200

    def test_logout(self, client, app, student_user):
        with app.app_context():
            client.post('/auth/login', data={
                'username': 'test_student',
                'password': 'Studentpass123',
                'csrf_token': 'test'
            }, follow_redirects=True)
            r = client.get('/auth/logout', follow_redirects=True)
            assert r.status_code == 200
