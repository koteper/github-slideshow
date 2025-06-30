from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from .models import db, User
import functools # Import functools

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

def admin_required(func):
    @login_required
    @functools.wraps(func) # Add functools.wraps
    def decorated_view(*args, **kwargs):
        if not current_user.is_authenticated or current_user.privilege_level != 3:
            flash('You do not have permission to access this page.')
            return redirect(url_for('main.index'))
        return func(*args, **kwargs)
    return decorated_view

@admin_bp.route('/users')
@admin_required
def manage_users():
    users = User.query.all()
    return render_template('manage_users.html', users=users)

@admin_bp.route('/set_privilege/<int:user_id>', methods=['POST'])
@admin_required
def set_privilege(user_id):
    user_to_manage = User.query.get_or_404(user_id)
    if user_to_manage.id == current_user.id:
        flash("Admins cannot change their own privilege level directly via this form.")
        return redirect(url_for('admin.manage_users'))

    new_privilege_level = request.form.get('privilege_level')
    if new_privilege_level:
        try:
            new_privilege_level = int(new_privilege_level)
            if new_privilege_level not in [1, 2, 3]:
                flash('Invalid privilege level selected.')
            else:
                # Prevent demoting the last admin or changing superadmin if implemented
                if user_to_manage.privilege_level == 3 and User.query.filter_by(privilege_level=3).count() == 1 and new_privilege_level != 3:
                    flash("Cannot remove the last admin's privileges.")
                else:
                    user_to_manage.privilege_level = new_privilege_level
                    db.session.commit()
                    flash(f"Privileges for {user_to_manage.username} updated successfully.")
        except ValueError:
            flash('Invalid privilege level format.')
    else:
        flash('No privilege level provided.')
    return redirect(url_for('admin.manage_users'))

@admin_bp.route('/delete_user/<int:user_id>', methods=['POST'])
@admin_required
def delete_user(user_id):
    user_to_delete = User.query.get_or_404(user_id)
    if user_to_delete.id == current_user.id:
        flash("You cannot delete your own account.")
        return redirect(url_for('admin.manage_users'))

    if user_to_delete.privilege_level == 3 and User.query.filter_by(privilege_level=3).count() == 1:
        flash("Cannot delete the last admin account.")
        return redirect(url_for('admin.manage_users'))

    # Optional: Reassign data or delete data associated with the user
    # For now, we'll just delete the user. Associated data might cause issues
    # if not handled (e.g. foreign key constraints if Data.user_id is not nullable or ON DELETE SET NULL)
    # A better approach would be to make user_id in Data nullable or set a default/sentinel user.
    # For simplicity, we assume related data should be considered or handled manually.

    db.session.delete(user_to_delete)
    db.session.commit()
    flash(f"User {user_to_delete.username} has been deleted.")
    return redirect(url_for('admin.manage_users'))
