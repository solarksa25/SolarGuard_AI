from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from db import query_db, execute_db
from datetime import datetime

alerts_bp = Blueprint('alerts', __name__)


@alerts_bp.route('/alerts')
@login_required
def index():
    status_filter   = request.args.get('status',   'all')
    severity_filter = request.args.get('severity', 'all')
    type_filter     = request.args.get('alert_type', 'all')
    start_date      = request.args.get('start_date', '')
    end_date        = request.args.get('end_date', '')

    sql = 'SELECT * FROM alerts'
    conditions, params = [], []
    if status_filter != 'all':
        conditions.append('status = %s');   params.append(status_filter)
    if severity_filter != 'all':
        conditions.append('severity = %s'); params.append(severity_filter)
    if type_filter != 'all':
        conditions.append('alert_type = %s'); params.append(type_filter)
    if start_date:
        conditions.append('DATE(detected_at) >= %s'); params.append(start_date)
    if end_date:
        conditions.append('DATE(detected_at) <= %s'); params.append(end_date)

    if conditions:
        sql += ' WHERE ' + ' AND '.join(conditions)
    sql += ' ORDER BY detected_at DESC LIMIT 200'

    alerts = query_db(sql, params)

    counts = query_db(
        'SELECT '
        'SUM(status="active") AS active_count, '
        'SUM(status="resolved" AND DATE(updated_at)=CURDATE()) AS resolved_today, '
        'SUM(severity="critical" AND status="active") AS critical_count '
        'FROM alerts', one=True
    )

    return render_template(
        'alerts/index.html',
        alerts=alerts or [],
        counts=counts or {},
        status_filter=status_filter,
        severity_filter=severity_filter,
        type_filter=type_filter,
        start_date=start_date,
        end_date=end_date,
    )


@alerts_bp.route('/alerts/<int:alert_id>/resolve', methods=['POST'])
@login_required
def resolve_alert(alert_id):
    execute_db(
        'UPDATE alerts SET status=%s, updated_at=%s, resolved_by=%s WHERE id=%s',
        ('resolved', datetime.now(), current_user.id, alert_id)
    )
    return jsonify({'success': True})


@alerts_bp.route('/alerts/<int:alert_id>/snooze', methods=['POST'])
@login_required
def snooze_alert(alert_id):
    execute_db(
        'UPDATE alerts SET status=%s, updated_at=%s WHERE id=%s',
        ('snoozed', datetime.now(), alert_id)
    )
    return jsonify({'success': True})


@alerts_bp.route('/alerts/<int:alert_id>/reactivate', methods=['POST'])
@login_required
def reactivate_alert(alert_id):
    execute_db(
        'UPDATE alerts SET status=%s, updated_at=%s WHERE id=%s',
        ('active', datetime.now(), alert_id)
    )
    return jsonify({'success': True})


@alerts_bp.route('/alerts/<int:alert_id>/investigate', methods=['POST'])
@login_required
def investigate_alert(alert_id):
    execute_db(
        'UPDATE alerts SET status=%s, updated_at=%s WHERE id=%s',
        ('investigating', datetime.now(), alert_id)
    )
    return jsonify({'success': True})


@alerts_bp.route('/alerts/<int:alert_id>/delete', methods=['POST'])
@login_required
def delete_alert(alert_id):
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    execute_db('DELETE FROM alerts WHERE id=%s', (alert_id,))
    return jsonify({'success': True})


@alerts_bp.route('/alerts/delete-all', methods=['POST'])
@login_required
def delete_all_alerts():
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    execute_db('DELETE FROM alerts', ())
    return jsonify({'success': True})
