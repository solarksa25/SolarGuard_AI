import os
import base64
from flask import Blueprint, render_template, request, jsonify, abort
from flask_login import login_required, current_user
from bcrypt import hashpw, gensalt
from models import User
from db import query_db, execute_db
from functools import wraps

admin_bp = Blueprint('admin', __name__)


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            abort(403)
        return f(*args, **kwargs)
    return decorated


@admin_bp.route('/admin/users')
@login_required
@admin_required
def users():
    all_users = User.get_all()
    return render_template('admin/users.html', users=all_users or [])


@admin_bp.route('/admin/users/create', methods=['POST'])
@login_required
@admin_required
def create_user():
    data      = request.get_json()
    full_name = data.get('full_name', '').strip()
    phone     = data.get('phone', '').strip()
    email     = data.get('email', '').strip().lower()
    password  = data.get('password', '')
    role      = data.get('role', 'engineer')

    if not all([full_name, email, password]):
        return jsonify({'error': 'Full name, email, and password are required.'}), 400
    if role not in ('admin', 'engineer'):
        return jsonify({'error': 'Invalid role.'}), 400

    existing = User.get_by_email(email)
    if existing:
        return jsonify({'error': 'Email already registered.'}), 400

    hashed  = hashpw(password.encode('utf-8'), gensalt()).decode('utf-8')
    user_id = User.create(full_name, phone, email, hashed, role)
    return jsonify({'success': True, 'user_id': user_id})


@admin_bp.route('/admin/users/<int:user_id>', methods=['DELETE'])
@login_required
@admin_required
def delete_user(user_id):
    if user_id == current_user.id:
        return jsonify({'error': 'Cannot delete your own account.'}), 400
    User.delete(user_id)
    return jsonify({'success': True})


@admin_bp.route('/admin/users/<int:user_id>', methods=['PUT'])
@login_required
@admin_required
def update_user(user_id):
    data = request.get_json()
    User.update(user_id, data.get('full_name'), data.get('phone'), data.get('role'))
    return jsonify({'success': True})


@admin_bp.route('/admin/reports')
@login_required
@admin_required
def reports():
    # Per-employee performance
    performance_data = query_db('''
        SELECT
            u.id,
            u.full_name,
            u.email,
            COUNT(a.id) AS total_resolved,
            COALESCE(AVG(TIMESTAMPDIFF(MINUTE, a.detected_at, a.updated_at)), 0) AS avg_resolution_time_min,
            SUM(CASE WHEN TIMESTAMPDIFF(MINUTE, a.detected_at, a.updated_at) < 60 THEN 1 ELSE 0 END) AS fast_resolutions,
            SUM(CASE WHEN TIMESTAMPDIFF(MINUTE, a.detected_at, a.updated_at) >= 60 THEN 1 ELSE 0 END) AS slow_resolutions
        FROM users u
        LEFT JOIN alerts a ON u.id = a.resolved_by AND a.status = 'resolved'
        WHERE u.role = 'engineer'
        GROUP BY u.id, u.full_name, u.email
        ORDER BY total_resolved DESC
    ''')

    # Overall summary stats
    summary = query_db('''
        SELECT
            COUNT(*) AS total_alerts,
            SUM(status = 'resolved') AS total_resolved,
            SUM(status = 'active') AS total_active,
            SUM(status = 'investigating') AS total_investigating,
            SUM(status = 'snoozed') AS total_snoozed,
            SUM(severity = 'critical') AS total_critical
        FROM alerts
    ''', one=True)

    # Fault type breakdown (resolved alerts only)
    fault_breakdown = query_db('''
        SELECT alert_type, COUNT(*) AS cnt
        FROM alerts
        WHERE status = 'resolved' AND alert_type IS NOT NULL
        GROUP BY alert_type
        ORDER BY cnt DESC
    ''')

    # Monthly resolved trend (last 6 months)
    monthly_trend = query_db('''
        SELECT
            DATE_FORMAT(updated_at, '%Y-%m') AS month,
            COUNT(*) AS resolved_count
        FROM alerts
        WHERE status = 'resolved'
          AND updated_at >= DATE_SUB(NOW(), INTERVAL 6 MONTH)
        GROUP BY month
        ORDER BY month ASC
    ''')

    # Logo as base64 data URI for PDF embedding
    logo_data_uri = ''
    try:
        logo_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'static', 'img', 'logo.png'
        )
        with open(logo_path, 'rb') as f:
            logo_b64 = base64.b64encode(f.read()).decode('utf-8')
        logo_data_uri = f'data:image/png;base64,{logo_b64}'
    except Exception:
        pass

    return render_template(
        'admin/reports.html',
        performance_data=performance_data or [],
        summary=summary or {},
        fault_breakdown=fault_breakdown or [],
        monthly_trend=monthly_trend or [],
        logo_data_uri=logo_data_uri,
    )
