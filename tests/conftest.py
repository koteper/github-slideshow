import pytest
import os
import tempfile

# Import db instance from app module directly (e.g. app.__init__ or app.models)
# This ensures we are using the *same* db object as the application.
from app import create_app, db as application_db
from app.models import User, Data


@pytest.fixture(scope='session')
def app():
    """Session-wide test Flask application."""
    db_fd, db_path = tempfile.mkstemp(suffix='.sqlite')

    test_config = {
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_path}",
        "SECRET_KEY": "test_secret_key_for_pytest",
        "WTF_CSRF_ENABLED": False, # Disable CSRF for simpler form testing in tests
        "LOGIN_DISABLED": False, # Ensure login is enabled unless specifically disabled for a test
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,
        # "SERVER_NAME": "localhost.test" # If you need url_for to work with _external=True
    }

    _app = create_app(config_override=test_config)

    # db.create_all() is called within create_app factory now,
    # so tables should be created with the test DB URI.

    yield _app

    # Teardown: close and remove the temporary database file
    # No need for app_context here if operations are on the file system / OS level
    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture()
def client(app):
    """A test client for the app."""
    return app.test_client()


@pytest.fixture(scope='function')
def db(app): # app fixture provides the app context
    """Provides the transactional fixtures with an app context"""
    with app.app_context():
        # Ensure tables are created at the start of each test function's db fixture setup
        # This is crucial because previous test's teardown (drop_all) removed them.
        application_db.create_all()

        yield application_db # Use the db instance from the application

        # Clean up database state after each test
        application_db.session.remove()
        application_db.drop_all()
        # No need to create_all() here, as it will be done by the next test's setup phase of this fixture.


@pytest.fixture
def runner(app):
    """A test runner for the CLI."""
    return app.test_cli_runner()


@pytest.fixture
def new_user(db):
    user = User(username='testuser', privilege_level=1)
    user.set_password('testpassword')
    db.session.add(user)
    db.session.commit()
    return user

@pytest.fixture
def new_editor(db):
    editor = User(username='editoruser', privilege_level=2)
    editor.set_password('editorpassword')
    db.session.add(editor)
    db.session.commit()
    return editor

@pytest.fixture
def new_admin(db):
    admin = User(username='adminuser', privilege_level=3)
    admin.set_password('adminpassword')
    db.session.add(admin)
    db.session.commit()
    return admin

def login_user_client(client, username, password):
    """Helper function to log in a user with the test client."""
    return client.post('/login', data=dict(
        username=username,
        password=password
    ), follow_redirects=True)

def logout_user_client(client):
    """Helper function to log out a user."""
    return client.get('/logout', follow_redirects=True)
