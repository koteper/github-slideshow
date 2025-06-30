import pytest
from app.models import User, Data, db
from tests.conftest import login_user_client, logout_user_client

def test_index_unauthenticated(client):
    response = client.get('/')
    assert response.status_code == 200
    assert b"Please log in to manage data." in response.data
    assert b"Login" in response.data
    assert b"Register" in response.data

def test_index_authenticated_basic_user(client, new_user):
    login_user_client(client, new_user.username, 'testpassword')
    response = client.get('/')
    assert response.status_code == 200
    assert f"Hello, {new_user.username}!".encode() in response.data
    assert b"Add New Data" in response.data # Link from base.html nav
    assert b"No data found." in response.data # Initially no data for this user

def test_add_data_page_unauthenticated(client):
    response = client.get('/add', follow_redirects=True)
    assert b"Login" in response.data # Redirected to login

def test_add_data_page_authenticated(client, new_user):
    login_user_client(client, new_user.username, 'testpassword')
    response = client.get('/add')
    assert response.status_code == 200
    assert b"Add Data" in response.data
    assert b"Name:" in response.data
    assert b"Value:" in response.data

def test_add_data_functionality(client, new_user, app):
    login_user_client(client, new_user.username, 'testpassword')
    response = client.post('/add', data={
        'name': 'Test Data Item',
        'value': 'This is a test value.'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b"Data added successfully." in response.data
    assert b"Test Data Item" in response.data # Check if data appears on index
    with app.app_context():
        data_item = Data.query.filter_by(name='Test Data Item').first()
        assert data_item is not None
        assert data_item.value == 'This is a test value.'
        assert data_item.user_id == new_user.id

def test_add_data_missing_name(client, new_user):
    login_user_client(client, new_user.username, 'testpassword')
    response = client.post('/add', data={
        'name': '',
        'value': 'This is a test value.'
    }, follow_redirects=True) # Follows redirect back to add_data form
    assert response.status_code == 200
    assert b"Name is required." in response.data # Flash message
    assert b"Add Data" in response.data # Should stay on or be redirected to the add form

def test_edit_data_page_unauthenticated(client, app, new_user): # new_user to create data first
    with app.app_context():
        data = Data(name="EditMe", value="Initial", user_id=new_user.id)
        db.session.add(data)
        db.session.commit()
        data_id = data.id

    response = client.get(f'/edit/{data_id}', follow_redirects=True)
    assert b"Login" in response.data # Redirected to login

def test_edit_data_page_basic_user_own_data(client, new_user, app):
    login_user_client(client, new_user.username, 'testpassword')
    with app.app_context():
        data = Data(name="MyData", value="InitialValue", user_id=new_user.id)
        db.session.add(data)
        db.session.commit()
        data_id = data.id

    response = client.get(f'/edit/{data_id}')
    assert response.status_code == 200
    assert b"Edit Data" in response.data
    assert b"MyData" in response.data # Name should be pre-filled
    assert b"InitialValue" in response.data # Value should be pre-filled

def test_edit_data_functionality_basic_user_own_data(client, new_user, app):
    login_user_client(client, new_user.username, 'testpassword')
    with app.app_context():
        data = Data(name="OldName", value="OldValue", user_id=new_user.id)
        db.session.add(data)
        db.session.commit()
        data_id = data.id

    response = client.post(f'/edit/{data_id}', data={
        'name': 'NewName',
        'value': 'NewValue'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b"Data updated successfully." in response.data
    assert b"NewName" in response.data # Check if updated data appears on index
    with app.app_context():
        updated_data = Data.query.get(data_id)
        assert updated_data.name == 'NewName'
        assert updated_data.value == 'NewValue'

def test_edit_data_basic_user_other_user_data_forbidden(client, new_user, new_editor, app):
    # new_user (basic) tries to edit new_editor's data
    with app.app_context():
        other_data = Data(name="EditorData", value="Belongs to Editor", user_id=new_editor.id)
        db.session.add(other_data)
        db.session.commit()
        other_data_id = other_data.id

    login_user_client(client, new_user.username, 'testpassword') # Log in as basic user
    response = client.get(f'/edit/{other_data_id}', follow_redirects=True)
    assert response.status_code == 200
    assert b"You are not authorized to edit this item." in response.data
    assert b"EditorData" not in response.data # Should not see the edit form for this item

    response = client.post(f'/edit/{other_data_id}', data={'name': 'AttemptedEdit', 'value': 'AttemptedValue'}, follow_redirects=True)
    assert response.status_code == 200
    assert b"You are not authorized to edit this item." in response.data
    with app.app_context(): # Verify data was not changed
        data_check = Data.query.get(other_data_id)
        assert data_check.name == "EditorData"


def test_delete_data_basic_user_own_data(client, new_user, app):
    login_user_client(client, new_user.username, 'testpassword')
    with app.app_context():
        data_to_delete = Data(name="ToDelete", value="DeleteMeValue", user_id=new_user.id)
        db.session.add(data_to_delete)
        db.session.commit()
        data_id = data_to_delete.id

    response = client.post(f'/delete/{data_id}', follow_redirects=True)
    assert response.status_code == 200
    assert b"Data deleted successfully." in response.data
    assert b"ToDelete" not in response.data # Data should be gone from index
    with app.app_context():
        assert Data.query.get(data_id) is None

def test_delete_data_basic_user_other_user_data_forbidden(client, new_user, new_editor, app):
    with app.app_context():
        other_data = Data(name="SafeData", value="Belongs to Editor", user_id=new_editor.id)
        db.session.add(other_data)
        db.session.commit()
        other_data_id = other_data.id

    login_user_client(client, new_user.username, 'testpassword') # Log in as basic user
    response = client.post(f'/delete/{other_data_id}', follow_redirects=True)
    assert response.status_code == 200
    assert b"You are not authorized to delete this item." in response.data
    with app.app_context():
        assert Data.query.get(other_data_id) is not None # Data should still exist

def test_editor_can_view_all_data(client, new_editor, new_user, app):
    with app.app_context():
        Data(name="UserItem", value="val1", user_id=new_user.id).save()
        Data(name="EditorItem", value="val2", user_id=new_editor.id).save()

    login_user_client(client, new_editor.username, 'editorpassword')
    response = client.get('/')
    assert response.status_code == 200
    assert b"UserItem" in response.data
    assert b"EditorItem" in response.data

def test_editor_can_edit_any_data(client, new_editor, new_user, app):
    with app.app_context():
        user_data = Data(name="UserDataOriginal", value="val1", user_id=new_user.id)
        db.session.add(user_data)
        db.session.commit()
        user_data_id = user_data.id

    login_user_client(client, new_editor.username, 'editorpassword')
    response = client.post(f'/edit/{user_data_id}', data={
        'name': 'UserDataEditedByEditor',
        'value': 'newval'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b"Data updated successfully." in response.data
    assert b"UserDataEditedByEditor" in response.data
    with app.app_context():
        edited_data = Data.query.get(user_data_id)
        assert edited_data.name == "UserDataEditedByEditor"

def test_editor_can_delete_any_data(client, new_editor, new_user, app):
    with app.app_context():
        user_data = Data(name="UserDataToDelete", value="val1", user_id=new_user.id)
        db.session.add(user_data)
        db.session.commit()
        user_data_id = user_data.id

    login_user_client(client, new_editor.username, 'editorpassword')
    response = client.post(f'/delete/{user_data_id}', follow_redirects=True)
    assert response.status_code == 200
    assert b"Data deleted successfully." in response.data
    with app.app_context():
        assert Data.query.get(user_data_id) is None

# Helper method for easier test data creation
# This should be defined globally or imported if used across multiple test files
# For now, defining it here.
def create_and_save_data(name, value, user_id):
    data_item = Data(name=name, value=value, user_id=user_id)
    db.session.add(data_item)
    db.session.commit()
    return data_item

# The monkeypatch was causing issues with collection.
# Using a direct helper function or fixture is cleaner.
# If Data.save() is desired as a method, it should be part of the model definition.
# For example:
# in app/models.py:
# class Data(db.Model):
#   ...
#   def save(self):
#       db.session.add(self)
#       db.session.commit()
#       return self

# Re-writing affected tests to use the helper or direct db.session operations

def test_editor_can_view_all_data(client, new_editor, new_user, app): # app fixture for db context
    with app.app_context():
        create_and_save_data(name="UserItem", value="val1", user_id=new_user.id)
        create_and_save_data(name="EditorItem", value="val2", user_id=new_editor.id)

    login_user_client(client, new_editor.username, 'editorpassword')
    response = client.get('/')
    assert response.status_code == 200
    assert b"UserItem" in response.data
    assert b"EditorItem" in response.data

def test_editor_can_edit_any_data(client, new_editor, new_user, app): # app fixture for db context
    with app.app_context():
        user_data = create_and_save_data(name="UserDataOriginal", value="val1", user_id=new_user.id)
        user_data_id = user_data.id

    login_user_client(client, new_editor.username, 'editorpassword')
    response = client.post(f'/edit/{user_data_id}', data={
        'name': 'UserDataEditedByEditor',
        'value': 'newval'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b"Data updated successfully." in response.data
    assert b"UserDataEditedByEditor" in response.data
    with app.app_context():
        edited_data = Data.query.get(user_data_id)
        assert edited_data.name == "UserDataEditedByEditor"

def test_editor_can_delete_any_data(client, new_editor, new_user, app): # app fixture for db context
    with app.app_context():
        user_data = create_and_save_data(name="UserDataToDelete", value="val1", user_id=new_user.id)
        user_data_id = user_data.id

    login_user_client(client, new_editor.username, 'editorpassword')
    response = client.post(f'/delete/{user_data_id}', follow_redirects=True)
    assert response.status_code == 200
    assert b"Data deleted successfully." in response.data
    with app.app_context():
        assert Data.query.get(user_data_id) is None
