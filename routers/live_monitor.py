"""
SolarGuard AI — Live Monitoring Router
Reads faulted_dataset.csv and simulates real-time streaming with PVLib-based fault injection.
Supports all 8 fault types (F0-F7).
"""
import os
import json
import random
import numpy as np
import pandas as pd
from datetime import datetime
from flask import Blueprint, render_template, jsonify, request
from flask_login import login_required
import uuid
from werkzeug.utils import secure_filename
from config import Config

live_monitor_bp = Blueprint('live_monitor', __name__)

_HERE    = os.path.dirname(os.path.abspath(__file__))
_APPDIR  = os.path.dirname(_HERE)
_DATA    = os.path.join(_APPDIR, 'data')

FAULT_TYPES = {
    0: 'Normal', 1: 'Partial Shading', 2: 'Soiling', 3: 'Degradation',
    4: 'Inverter Fault', 5: 'Open-Circuit String', 6: 'Short-Circuit', 7: 'Sensor Fault',
}

FAULT_SEVERITY = {
    0: 'normal', 1: 'warning', 2: 'warning', 3: 'warning',
    4: 'critical', 5: 'critical', 6: 'critical', 7: 'warning',
}

FAULT_RECOMMENDATIONS = {
    0: 'System operating normally. No action required.',
    1: 'Partial shading detected. Inspect for obstructions and check bypass diodes.',
    2: 'Dust/soiling detected. Schedule panel cleaning within 24-48 hours.',
    3: 'Degradation detected. Compare against baseline and consider IV curve tracing.',
    4: 'Inverter fault! Shut down affected inverter. Check fuses and IGBT modules.',
    5: 'Open-circuit string detected. Check fuses and MC4 connectors.',
    6: 'Short-circuit detected! Isolate affected string immediately.',
    7: 'Sensor fault detected. Verify sensor wiring and calibration.',
}

FAULT_DROPDOWN = [
    (0, 'Normal', 'green'),
    (1, 'Partial Shading', 'blue'),
    (2, 'Soiling', 'amber'),
    (3, 'Degradation', 'orange'),
    (4, 'Inverter Fault', 'red'),
    (5, 'Open-Circuit String', 'red'),
    (6, 'Short-Circuit', 'red'),
    (7, 'Sensor Fault', 'purple'),
]

# ── Dataset Cache ────────────────────────────────────────────────────────
_df_cache = None
_sim_state = {
    'running': False,
    'step': 0,
    'model_key': 'lgb',
    'speed': 1,
    'alerts': [],
    'history': [],
    'last_fault_id': 0,
}


def _load_dataset():
    global _df_cache
    
    filename = _sim_state.get('dataset_file', 'faulted_dataset.csv')
    if not filename:
        return None
        
    path = os.path.join(_DATA, filename)
    
    if _df_cache is not None and _sim_state.get('cached_filename') == filename:
        return _df_cache

    if not os.path.exists(path):
        print(f'[live_monitor] Dataset not found at {path}')
        return None

    try:
        df = pd.read_csv(path)
        _sim_state['cached_filename'] = filename
        print(f'[live_monitor] Loaded dataset: {len(df):,} rows x {len(df.columns)} columns')

        # Filter to daytime (irradiance > 50 W/m²)
        if 'POA_IRRADIANCE' in df.columns:
            df = df[df['POA_IRRADIANCE'] > 50].reset_index(drop=True)
        elif 'IRRADIATION' in df.columns:
            df = df[df['IRRADIATION'] > 50].reset_index(drop=True)

        print(f'[live_monitor] Daytime rows: {len(df):,}')
        _df_cache = df
        return df
    except Exception as e:
        print(f'[live_monitor] Dataset load error: {e}')
        return None


def _get_row_features(row):
    """Extract feature dict from a dataset row."""
    from config import Config
    features = {}
    for col in Config.FEATURE_COLS:
        if col in row.index:
            try:
                features[col] = float(row[col])
            except (ValueError, TypeError):
                features[col] = 0.0
        else:
            features[col] = 0.0
    return features





@live_monitor_bp.route('/live')
@login_required
def index():
    # Find all CSV files in the data directory
    available_datasets = []
    if os.path.exists(_DATA):
        for f in os.listdir(_DATA):
            if f.endswith('.csv'):
                available_datasets.append(f)
    
    # Ensure current selected dataset is valid
    current_dataset = _sim_state.get('dataset_file')
    if not current_dataset or current_dataset not in available_datasets:
        current_dataset = 'faulted_dataset.csv' if 'faulted_dataset.csv' in available_datasets else (available_datasets[0] if available_datasets else None)
        _sim_state['dataset_file'] = current_dataset

    dataset_loaded = False
    row_count = 0
    if current_dataset:
        df = _load_dataset()
        if df is not None:
            dataset_loaded = True
            row_count = len(df)

    return render_template('live_monitor/index.html',
                           dataset_loaded=dataset_loaded,
                           row_count=row_count,
                           available_datasets=available_datasets,
                           current_dataset=current_dataset)


@live_monitor_bp.route('/live/upload', methods=['POST'])
@login_required
def upload():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    file = request.files['file']
    if not file.filename:
        return jsonify({'error': 'Empty filename'}), 400
    if not file.filename.lower().endswith('.csv'):
        return jsonify({'error': 'Only CSV files are allowed'}), 400
    
    filename = secure_filename(f"{uuid.uuid4().hex}_{file.filename}")
    upload_path = os.path.join(_DATA, filename)
    os.makedirs(_DATA, exist_ok=True)
    file.save(upload_path)
    
    # Optional validation
    try:
        import pandas as pd
        preview = pd.read_csv(upload_path, nrows=5)
        if len(preview.columns) == 0:
            return jsonify({'error': 'CSV file is empty or invalid'}), 400
    except Exception as e:
        return jsonify({'error': f'Error reading CSV: {str(e)}'}), 400

    return jsonify({'success': True, 'filename': filename, 'original_name': file.filename})


@live_monitor_bp.route('/live/status')
@login_required
def status():
    return jsonify({
        'running': _sim_state['running'],
        'step':    _sim_state['step'],
    })


@live_monitor_bp.route('/live/start', methods=['POST'])
@login_required
def start():
    data = request.get_json() or {}
    
    new_dataset = data.get('dataset_file')
    if new_dataset and new_dataset != _sim_state.get('dataset_file'):
        _sim_state['dataset_file'] = new_dataset
        global _df_cache
        _df_cache = None # Force reload
        
    _sim_state['running']        = True
    _sim_state['step']           = 0
    _sim_state['model_key']      = data.get('model_key', 'lgb')
    _sim_state['speed']          = int(data.get('speed', 1))
    _sim_state['alerts']         = []
    _sim_state['history']        = []
    _sim_state['last_fault_id']  = 0
    return jsonify({'ok': True})


@live_monitor_bp.route('/live/stop', methods=['POST'])
@login_required
def stop():
    _sim_state['running'] = False
    return jsonify({'ok': True})


@live_monitor_bp.route('/live/tick')
@login_required
def tick():
    """Return the next batch of readings — called by frontend every second."""
    if not _sim_state['running']:
        return jsonify({'running': False})

    df = _load_dataset()
    if df is None:
        return jsonify({'error': 'Dataset not loaded. Place faulted_dataset.csv in data/ directory.'}), 500

    speed = max(1, min(_sim_state['speed'], 12))
    step = _sim_state['step']
    window_size = speed
    end_idx = min(step + window_size, len(df))
    
    if step >= len(df):
        _sim_state['running'] = False
        return jsonify({'running': False, 'done': True})

    rows_raw = df.iloc[step:end_idx]

    # Clean metrics (raw data)
    dc_power  = float(rows_raw['DC_POWER'].mean()) if 'DC_POWER' in df.columns else 0
    ac_power  = float(rows_raw['AC_POWER'].mean()) if 'AC_POWER' in df.columns else 0
    irr       = float(rows_raw['IRRADIATION'].mean()) if 'IRRADIATION' in df.columns else 0

    # Run AI inference on raw data (we take the first row of the chunk for AI)
    from ai_inference import infer_single_row
    sample_row = _get_row_features(rows_raw.iloc[0])
    ai_result = infer_single_row(sample_row, model_key=_sim_state['model_key'])
    
    if 'error' in ai_result:
        ai_result = {
            'fault_type': 'Error', 'fault_prob': 0, 'severity': 'normal',
            'fault_probs': {}, 'recommendation': ai_result['error'],
            'fault_label_id': 0
        }

    fault_id = ai_result.get('fault_label_id', 0)
    is_anomaly = fault_id != 0

    _sim_state['step'] = end_idx

    # Time label
    time_col = 'timestamp' if 'timestamp' in df.columns else 'DATE_TIME'
    if time_col in rows_raw.columns:
        time_label = str(rows_raw.iloc[-1][time_col])[:16]
    else:
        time_label = f'Step {end_idx}'

    # Alert logic
    new_alerts = []
    last_fault_id = _sim_state.get('last_fault_id', 0)

    # Only alert if it's a new fault type (transition from normal -> fault, or fault A -> fault B)
    if is_anomaly and fault_id != last_fault_id:
        fault_name = FAULT_TYPES.get(fault_id, 'Unknown')
        severity = FAULT_SEVERITY.get(fault_id, 'warning')
        health = round(100.0 - ai_result.get('fault_prob', 1.0) * (30 if fault_id in [1,2,3,7] else 60), 1)
        health = max(0, health)
        
        alert = {
            'time':       time_label,
            'source_key': 'INV-01',
            'fault_type': fault_name,
            'severity':   severity,
            'health':     health,
            'pr':         round(dc_power / max(irr * (Config.get_station_config()['DC_CAPACITY_KW'] * 1000), 1), 3),
            'message':    f"{'🔴' if severity == 'critical' else '🟡'} "
                          f"INV-01: AI Detected {fault_name} (Confidence: {ai_result.get('fault_prob',0)*100:.1f}%)",
        }
        _sim_state['alerts'].insert(0, alert)
        _sim_state['alerts'] = _sim_state['alerts'][:50]
        new_alerts.append(alert)

        try:
            from db import execute_db
            execute_db(
                'INSERT INTO alerts '
                '(severity, alert_type, source_key, description, recommendation, status, detected_at) '
                'VALUES (%s,%s,%s,%s,%s,%s,%s)',
                (severity, fault_name, 'INV-01',
                 f"[Live AI Monitor] INV-01: {fault_name} detected with {ai_result.get('fault_prob',0)*100:.1f}% confidence. Model: {_sim_state['model_key'].upper()}",
                 FAULT_RECOMMENDATIONS.get(fault_id, ''),
                 'active', time_label)
            )
        except Exception as e:
            print(f'[live_monitor] DB alert error: {e}')

    _sim_state['last_fault_id'] = fault_id

    # Simulated health for charting
    health_stat = 100.0 if not is_anomaly else round(100.0 - ai_result.get('fault_prob', 1.0) * (30 if fault_id in [1,2,3,7] else 60), 1)
    health_stat = max(0, health_stat)

    hist_point = {
        'time':       time_label,
        'dc_power':   round(dc_power, 1),
        'irr':        round(irr, 4),
        'health':     health_stat,
        'is_anomaly': is_anomaly,
    }
    _sim_state['history'].append(hist_point)
    _sim_state['history'] = _sim_state['history'][-120:]

    progress = round(100.0 * end_idx / len(df), 1)

    return jsonify({
        'running':       True,
        'step':          end_idx,
        'progress':      progress,
        'time_label':    time_label,
        'fault_type':    FAULT_TYPES.get(fault_id, 'Normal'),
        'fault_id':      fault_id,
        'health':        health_stat,
        'is_anomaly':    is_anomaly,
        'dc_power':      round(dc_power, 1),
        'ac_power':      round(ac_power, 1),
        'irr':           round(irr, 4),
        'ai_result':     ai_result,
        'new_alerts':    new_alerts,
        'all_alerts':    _sim_state['alerts'][:10],
        'history':       _sim_state['history'][-60:],
        'total_rows':    len(df),
    })

@live_monitor_bp.route('/live/reset', methods=['POST'])
@login_required
def reset():
    _sim_state.update({
        'running': False, 'step': 0,
        'model_key': 'lgb', 'speed': 1,
        'alerts': [], 'history': [],
        'last_fault_id': 0,
    })
    return jsonify({'ok': True})
