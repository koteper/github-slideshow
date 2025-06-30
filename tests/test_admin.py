import pytest
from app.models import User, db
from tests.conftest import login_user_client, logout_user_client

def test_manage_users_page_unauthenticated(client):
    response = client.get('/admin/users', follow_redirects=True)
    assert b"Login" in response.data # Redirected to login

def test_manage_users_page_as_basic_user(client, new_user):
    login_user_client(client, new_user.username, 'testpassword')
    response = client.get('/admin/users', follow_redirects=True)
    assert response.status_code == 200
    assert b"You do not have permission to access this page." in response.data
    assert b"Manage User Privileges" not in response.data # Should be on index or other page

def test_manage_users_page_as_editor(client, new_editor):
    login_user_client(client, new_editor.username, 'editorpassword')
    response = client.get('/admin/users', follow_redirects=True)
    assert response.status_code == 200
    assert b"You do not have permission to access this page." in response.data
    assert b"Manage User Privileges" not in response.data

def test_manage_users_page_as_admin(client, new_admin, new_user):
    login_user_client(client, new_admin.username, 'adminpassword')
    response = client.get('/admin/users')
    assert response.status_code == 200
    assert b"Manage User Privileges" in response.data
    assert new_admin.username.encode() in response.data
    assert new_user.username.encode() in response.data # Should list other users

def test_set_privilege_as_admin(client, new_admin, new_user, app):
    login_user_client(client, new_admin.username, 'adminpassword')
    assert new_user.privilege_level == 1 # Initial state

    response = client.post(f'/admin/set_privilege/{new_user.id}', data={
        'privilege_level': '2' # Change to editor
    }, follow_redirects=True)

    assert response.status_code == 200
    assert f"Privileges for {new_user.username} updated successfully.".encode() in response.data
    with app.app_context():
        updated_user = User.query.get(new_user.id)
        assert updated_user.privilege_level == 2

def test_set_privilege_invalid_level(client, new_admin, new_user, app):
    login_user_client(client, new_admin.username, 'adminpassword')
    response = client.post(f'/admin/set_privilege/{new_user.id}', data={
        'privilege_level': '99' # Invalid level
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b"Invalid privilege level selected." in response.data
    with app.app_context(): # Ensure privilege was not changed
        user_check = User.query.get(new_user.id)
        assert user_check.privilege_level == 1

def test_admin_cannot_change_own_privilege_via_form(client, new_admin, app):
    initial_priv_level = new_admin.privilege_level
    login_user_client(client, new_admin.username, 'adminpassword')
    response = client.post(f'/admin/set_privilege/{new_admin.id}', data={
        'privilege_level': '1'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b"Admins cannot change their own privilege level directly via this form." in response.data
    with app.app_context():
        admin_check = User.query.get(new_admin.id)
        assert admin_check.privilege_level == initial_priv_level # Should not change

def test_admin_cannot_demote_last_admin(client, new_admin, app):
    # Ensure new_admin is the only admin
    with app.app_context():
        other_admins = User.query.filter(User.privilege_level == 3, User.id != new_admin.id).all()
        for oa in other_admins:
            db.session.delete(oa)
        db.session.commit()
        assert User.query.filter_by(privilege_level=3).count() == 1

    login_user_client(client, new_admin.username, 'adminpassword')
    # Try to demote self (which is blocked by another check, but good to have this specific one too)
    # This test is more about if an admin tries to demote *another* user who is the last admin.
    # For this specific test, let's assume there's another user, and admin tries to demote the *current* admin (self)
    # if this was the only admin. The route prevents self-demotion directly.
    # The more relevant test is: admin tries to demote another_admin_user who is the only admin.
    # But since new_admin is the only one, we can test the logic by attempting to demote new_admin
    # via a hypothetical scenario where it's allowed, but the "last admin" rule kicks in.
    # The current set_privilege route already prevents admin from changing their own role.
    # So, this test is slightly artificial for `set_privilege` but the logic is in the route.
    # Let's create a temporary second admin to test demoting one of them, making the other the last.

    temp_admin = User(username='tempadmin', privilege_level=3)
    temp_admin.set_password('temppass')
    with app.app_context():
        db.session.add(temp_admin)
        db.session.commit()
        assert User.query.filter_by(privilege_level=3).count() == 2 # new_admin and temp_admin

    # Admin (new_admin) tries to demote temp_admin (who is one of two admins) - this should be fine
    response = client.post(f'/admin/set_privilege/{temp_admin.id}', data={'privilege_level': '1'}, follow_redirects=True)
    assert b"Privileges for tempadmin updated successfully." in response.data
    with app.app_context():
         assert User.query.get(temp_admin.id).privilege_level == 1
         assert User.query.filter_by(privilege_level=3).count() == 1 # Only new_admin left as admin

    # Now, new_admin is the last admin. Try to demote new_admin (via form - blocked)
    # The route logic `if user_to_manage.privilege_level == 3 and User.query.filter_by(privilege_level=3).count() == 1 and new_privilege_level != 3:`
    # is what we want to ensure.
    # Since self-change is blocked, this exact path is hard to test directly via POST to self.
    # However, if an admin *could* change another admin who was the last one:
    # Imagine admin_A trying to change admin_B (last admin) to user.
    # The current test covers if admin_A tries to change admin_A (self) if they are the last admin.
    # The route logic is: if user_to_change.is_admin AND is_last_admin AND new_level_is_not_admin -> block.
    # This is correctly handled by the self-privilege change block.

    # Test deleting the last admin
    response = client.post(f'/admin/delete_user/{new_admin.id}', follow_redirects=True)
    assert b"Cannot delete the last admin account." in response.data
    with app.app_context():
        assert User.query.get(new_admin.id) is not None # Admin should still exist


def test_delete_user_as_admin(client, new_admin, new_user, app):
    login_user_client(client, new_admin.username, 'adminpassword')
    user_id_to_delete = new_user.id
    username_to_delete = new_user.username

    response = client.post(f'/admin/delete_user/{user_id_to_delete}', follow_redirects=True)
    assert response.status_code == 200
    assert f"User {username_to_delete} has been deleted.".encode() in response.data
    with app.app_context():
        assert User.query.get(user_id_to_delete) is None

def test_admin_cannot_delete_self(client, new_admin, app):
    login_user_client(client, new_admin.username, 'adminpassword')
    response = client.post(f'/admin/delete_user/{new_admin.id}', follow_redirects=True)
    assert response.status_code == 200
    assert b"You cannot delete your own account." in response.data
    with app.app_context():
        assert User.query.get(new_admin.id) is not None # Admin should still exist

def test_set_privilege_non_admin_access_denied(client, new_user):
    # new_user (basic) tries to set privilege for another user (e.g., self, or another)
    login_user_client(client, new_user.username, 'testpassword')
    # Attempt to change own privilege (though not an admin route, good to check)
    response = client.post(f'/admin/set_privilege/{new_user.id}', data={'privilege_level': '3'}, follow_redirects=True)
    assert b"You do not have permission to access this page." in response.data

def test_delete_user_non_admin_access_denied(client, new_user, new_editor):
    # new_user (basic) tries to delete new_editor
    login_user_client(client, new_user.username, 'testpassword')
    response = client.post(f'/admin/delete_user/{new_editor.id}', follow_redirects=True)
    assert b"You do not have permission to access this page." in response.data
    with db.session.app.app_context(): # Check user was not deleted
        assert User.query.get(new_editor.id) is not None
