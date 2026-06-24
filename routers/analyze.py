import os
import uuid
from flask import Blueprint, render_template, request, jsonify, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from db import query_db, execute_db
from datetime import datetime
import numpy as np

analyze_bp = Blueprint('analyze', __name__)

ALLOWED_EXT = {'csv'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXT


@analyze_bp.route('/analyze')
@login_required
def index():
    recent = query_db(
        'SELECT ar.*, u.full_name AS analyst '
        'FROM analysis_results ar '
        'LEFT JOIN users u ON ar.user_id = u.id '
        'ORDER BY ar.analysis_date DESC LIMIT 10'
    )
    return render_template(
        'analyze/index.html',
        recent_analyses=recent or [],
    )


@analyze_bp.route('/analyze/upload', methods=['POST'])
@login_required
def upload():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    if not file.filename or not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file. Please upload a CSV file.'}), 400

    filename    = secure_filename(f"{uuid.uuid4().hex}_{file.filename}")
    upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
    os.makedirs(os.path.dirname(upload_path), exist_ok=True)
    file.save(upload_path)

    try:
        import pandas as pd
        df        = pd.read_csv(upload_path, encoding='utf-8-sig')
        row_count = len(df)
        preview   = df.head(20).fillna('').to_dict(orient='records')

        from ai_inference import FAULT_LABELS
        from config import Config

        feature_cols = Config.FEATURE_COLS
        found_features = [c for c in feature_cols if c in df.columns]
        missing_features = [c for c in feature_cols if c not in df.columns]

        # Check if fault_label exists for validation
        has_fault_label = 'fault_label' in df.columns or 'fault_type' in df.columns

        return jsonify({
            'success'         : True,
            'filename'        : file.filename,
            'row_count'       : row_count,
            'columns'         : list(df.columns),
            'preview'         : preview,
            'stored_filename' : filename,
            'found_features'  : len(found_features),
            'missing_features': len(missing_features),
            'total_features'  : len(feature_cols),
            'has_fault_label' : has_fault_label,
            'ready_to_run'    : True,   # Missing features will be filled with 0
        })
    except Exception as e:
        return jsonify({'error': f'Error reading CSV: {str(e)}'}), 500


@analyze_bp.route('/analyze/run', methods=['POST'])
@login_required
def run_analysis():
    data            = request.get_json()
    stored_filename = data.get('stored_filename')
    model_key       = data.get('model_key', 'lgb')

    if not stored_filename:
        return jsonify({'error': 'No file to analyze'}), 400

    file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], stored_filename)
    if not os.path.exists(file_path):
        return jsonify({'error': 'File not found. Please re-upload.'}), 404

    try:
        import pandas as pd
        from ai_inference import infer_dataset, FAULT_LABELS, FAULT_RECOMMENDATIONS, FAULT_SEVERITY

        df     = pd.read_csv(file_path, encoding='utf-8-sig')
        result = infer_dataset(df, model_key=model_key)

        if 'error' in result:
            return jsonify({'error': result['error']}), 500

        summary    = result['summary']
        results    = result['results']

        anomaly_count  = summary['anomaly_count']
        fault_type     = summary['dominant_fault']
        health_score   = round(100.0 * (1.0 - anomaly_count / max(summary['total_rows'], 1)), 1)
        severity       = summary['severity']
        fault_counts   = summary['fault_distribution']
        avg_confidence = summary['avg_confidence']
        model_used     = summary['model_used']

        if severity == 'critical':  status_label = 'Critical'
        elif severity == 'warning': status_label = 'Degraded'
        else:                       status_label = 'Healthy'

        # Save to DB
        from config import Config
        execute_db(
            'INSERT INTO analysis_results '
            '(user_id, filename, stored_filename, model_used, row_count, inverter_count, anomaly_count, '
            'fault_type, health_score, analysis_date) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)',
            (current_user.id, data.get('original_filename', stored_filename),
             stored_filename, model_used,
             len(df), Config.get_station_config()['NUM_INVERTERS'], anomaly_count,
             fault_type, health_score, datetime.now())
        )

        # Recommendation
        if anomaly_count == 0:
            recommendation = 'All readings within normal parameters. No maintenance required.'
        elif severity == 'critical':
            breakdown = ', '.join(f'{cnt} {ft}' for ft, cnt in fault_counts.items() if ft != 'Normal')
            recommendation = (f'CRITICAL: {anomaly_count} anomalies detected out of {summary["total_rows"]} rows '
                              f'({breakdown}). Immediate inspection required.')
        else:
            breakdown = ', '.join(f'{cnt} {ft}' for ft, cnt in fault_counts.items() if ft != 'Normal')
            recommendation = (f'{anomaly_count} anomalies detected out of {summary["total_rows"]} rows '
                              f'({breakdown}). Schedule inspection within 48 hours.')

        return jsonify({
            'success'        : True,
            'row_count'      : summary['total_rows'],
            'anomaly_count'  : anomaly_count,
            'normal_count'   : summary['normal_count'],
            'fault_type'     : fault_type,
            'health_score'   : health_score,
            'severity'       : severity,
            'status_label'   : status_label,
            'model_used'     : model_used,
            'avg_confidence' : avg_confidence,
            'recommendation' : recommendation,
            'fault_distribution': fault_counts,
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@analyze_bp.route('/analyze/<int:analysis_id>/delete', methods=['POST'])
@login_required
def delete_analysis(analysis_id):
    from db import query_db, execute_db
    record = query_db('SELECT stored_filename FROM analysis_results WHERE id=%s AND user_id=%s', (analysis_id, current_user.id), one=True)
    if record and record['stored_filename']:
        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], record['stored_filename'])
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception as e:
                print(f"Error deleting file {file_path}: {e}")
                
    execute_db('DELETE FROM analysis_results WHERE id=%s AND user_id=%s', (analysis_id, current_user.id))
    return jsonify({'success': True})

@analyze_bp.route('/analyze/delete-all', methods=['POST'])
@login_required
def delete_all_analyses():
    from db import query_db, execute_db
    records = query_db('SELECT stored_filename FROM analysis_results WHERE user_id=%s', (current_user.id,))
    if records:
        for r in records:
            if r['stored_filename']:
                file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], r['stored_filename'])
                if os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                    except Exception as e:
                        print(f"Error deleting file {file_path}: {e}")
                        
    execute_db('DELETE FROM analysis_results WHERE user_id=%s', (current_user.id,))
    return jsonify({'success': True})
