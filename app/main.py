from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from .models import db, Data # User model is not directly used here anymore for users list

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    if current_user.is_authenticated:
        # Show all data for admin/editor, own data for basic user
        if current_user.privilege_level > 1: # Admin or Editor
            all_data = Data.query.all()
        else:
            all_data = Data.query.filter_by(user_id=current_user.id).all()
        # users list for privilege management is now handled by the admin blueprint
    else:
        all_data = []
    return render_template('index.html', data=all_data)

@main_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add_data():
    if request.method == 'POST':
        name = request.form.get('name')
        value = request.form.get('value')
        if not name:
            flash('Name is required.')
            return redirect(url_for('main.add_data'))
        new_data = Data(name=name, value=value, user_id=current_user.id)
        db.session.add(new_data)
        db.session.commit()
        flash('Data added successfully.')
        return redirect(url_for('main.index'))
    return render_template('data_form.html', action="Add", data_item=None)

@main_bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_data(id):
    data_item = Data.query.get_or_404(id)
    # Basic users can only edit their own data
    if current_user.privilege_level == 1 and data_item.user_id != current_user.id:
        flash('You are not authorized to edit this item.')
        return redirect(url_for('main.index'))
    # Editors can edit any data, Admins can edit any data
    if current_user.privilege_level < 2: # Not an editor or admin
        if data_item.user_id != current_user.id: # and not their own data
             flash('You are not authorized to edit this item.')
             return redirect(url_for('main.index'))

    if request.method == 'POST':
        data_item.name = request.form.get('name')
        data_item.value = request.form.get('value')
        if not data_item.name:
            flash('Name is required.')
            return render_template('data_form.html', action="Edit", data_item=data_item)
        db.session.commit()
        flash('Data updated successfully.')
        return redirect(url_for('main.index'))
    return render_template('data_form.html', action="Edit", data_item=data_item)

@main_bp.route('/delete/<int:id>', methods=['POST'])
@login_required
def delete_data(id):
    data_item = Data.query.get_or_404(id)
    # Basic users can only delete their own data
    if current_user.privilege_level == 1 and data_item.user_id != current_user.id:
        flash('You are not authorized to delete this item.')
        return redirect(url_for('main.index'))
    # Editors can delete any data, Admins can delete any data
    if current_user.privilege_level < 2: # Not an editor or admin
        if data_item.user_id != current_user.id: # and not their own data
            flash('You are not authorized to delete this item.')
            return redirect(url_for('main.index'))

    db.session.delete(data_item)
    db.session.commit()
    flash('Data deleted successfully.')
    return redirect(url_for('main.index'))
