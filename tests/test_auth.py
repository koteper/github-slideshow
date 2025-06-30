import pytest
from app.models import User, db
from tests.conftest import login_user_client, logout_user_client

def test_register_page(client):
    response = client.get('/register')
    assert response.status_code == 200
    assert b"Register" in response.data

def test_login_page(client):
    response = client.get('/login')
    assert response.status_code == 200
    assert b"Login" in response.data

def test_successful_registration(client, app):
    response = client.post('/register', data={
        'username': 'newuser',
        'password': 'newpassword'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b"Registration successful! Please log in." in response.data
    with app.app_context():
        user = User.query.filter_by(username='newuser').first()
        assert user is not None
        assert user.check_password('newpassword')

def test_registration_existing_user(client, new_user):
    response = client.post('/register', data={
        'username': new_user.username, # Using existing username
        'password': 'anotherpassword'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b"Username already exists." in response.data

def test_successful_login_logout(client, new_user):
    # Login
    response = login_user_client(client, new_user.username, 'testpassword')
    assert response.status_code == 200
    assert f"Hello, {new_user.username}!".encode() in response.data
    assert b"Logout" in response.data
    assert b"Login" not in response.data # Login link should not be present

    # Logout
    response = logout_user_client(client)
    assert response.status_code == 200
    assert b"Login" in response.data # Login link should be present again
    assert b"Logout" not in response.data

def test_login_wrong_password(client, new_user):
    response = login_user_client(client, new_user.username, 'wrongpassword')
    assert response.status_code == 200
    assert b"Invalid username or password." in response.data
    assert b"Logout" not in response.data

def test_login_nonexistent_user(client):
    response = login_user_client(client, 'nouser', 'nopass')
    assert response.status_code == 200
    assert b"Invalid username or password." in response.data

def test_authenticated_user_redirects_from_login_register(client, new_user):
    login_user_client(client, new_user.username, 'testpassword')

    response = client.get('/login', follow_redirects=True)
    assert b"Data Management" in response.data # Should redirect to index
    assert b"Login" not in response.data # Original login form should not be shown

    response = client.get('/register', follow_redirects=True)
    assert b"Data Management" in response.data # Should redirect to index
    assert b"Register" not in response.data # Original register form should not be shown

def test_logout_requires_login(client):
    response = client.get('/logout', follow_redirects=True)
    # Flask-Login redirects to login_view if @login_required fails
    assert b"Login" in response.data
    assert b"Please log in to access this page." in response.data # Default flash message
    assert response.request.path == "/login"

def test_access_protected_route_unauthenticated(client):
    response = client.get('/add', follow_redirects=True) # /add requires login
    assert response.status_code == 200
    assert b"Login" in response.data # Should be redirected to login
    assert b"Please log in to access this page." in response.data
    assert response.request.path == "/login"

def test_password_hashing(app):
    with app.app_context():
        u = User(username="hashuser")
        u.set_password("cat")
        assert u.password_hash != "cat"
        assert u.check_password("cat")
        assert not u.check_password("dog")
