from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from bcrypt import checkpw
from models import User

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/', methods=['GET'])
def index():
    if current_user.is_authenticated:
        return redirect(url_for('analyze.index'))
    return redirect(url_for('auth.login'))


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('analyze.index'))

    error = None
    if request.method == 'POST':
        email    = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        remember = request.form.get('remember') == 'on'

        if not email or not password:
            error = 'Please enter both email and password.'
        else:
            user_row = User.get_by_email(email)
            if user_row and checkpw(password.encode('utf-8'), user_row['password_hash'].encode('utf-8')):
                user_obj = User(user_row)
                login_user(user_obj, remember=remember)
                next_page = request.args.get('next')
                return redirect(next_page or url_for('analyze.index'))
            else:
                error = 'Invalid email or password.'

    return render_template('auth/login.html', error=error)


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))
