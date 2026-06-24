"""
SolarGuard AI — Inference Engine v8 (Universal Version)
Uses trained LightGBM / XGBoost / CatBoost universal models with 27 features and 8 fault classes.
Models loaded from .pkl files in models/ directory.
No standard scaling required. Handles raw features by normalizing them on-the-fly.

Fault Classes:
  F0: Normal, F1: Partial Shading, F2: Soiling, F3: Degradation,
  F4: Inverter Fault, F5: Open-Circuit String, F6: Short-Circuit, F7: Sensor Fault
"""

import os
import warnings
import json
import numpy as np
import pandas as pd
import joblib

warnings.filterwarnings('ignore', category=UserWarning)

_HERE      = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(_HERE, 'models')
DATA_DIR   = os.path.join(_HERE, 'data')

FAULT_LABELS = {
    0: 'Normal', 1: 'Partial Shading', 2: 'Soiling', 3: 'Degradation',
    4: 'Inverter Fault', 5: 'Open-Circuit String', 6: 'Short-Circuit', 7: 'Sensor Fault',
}

FAULT_RECOMMENDATIONS = {
    0: 'All systems operating normally. No maintenance required. Continue regular monitoring schedule.',
    1: 'Partial shading detected on the array. Inspect for nearby vegetation growth, new structures, or debris casting shadows on panels. Check bypass diodes for proper operation. Consider trimming trees or relocating obstructions.',
    2: 'Soiling/dust accumulation detected. DC power output reduced uniformly. Schedule panel cleaning within 24-48 hours. Use dry brushing or water wash depending on dust severity. Monitor PR trend after cleaning.',
    3: 'Panel degradation detected — output reduced below expected levels for current conditions. Compare against historical baseline. If degradation exceeds 15% of rated output, consider panel replacement. Schedule IV curve tracing.',
    4: 'Inverter fault detected — significant AC output collapse. Shut down affected inverter immediately. Check internal fuses, IGBT modules, and DC-link capacitors. Contact manufacturer support if fault persists after reset.',
    5: 'Open-circuit string detected — one or more strings disconnected. Check string fuses and combiner box connections. Inspect wiring for loose MC4 connectors, corrosion, or rodent damage. Verify string voltage at the combiner.',
    6: 'Short-circuit detected — abnormal current flow in a string. Isolate affected string immediately to prevent fire risk. Inspect for water ingress, damaged insulation, or failed bypass diodes. Do not reconnect until root cause is identified.',
    7: 'Sensor fault detected — readings from temperature or irradiance sensors appear corrupted or stuck. Verify sensor wiring and calibration. Replace faulty sensors. Cross-check with neighboring inverter readings for validation.',
}

FAULT_SEVERITY = {
    0: 'normal', 1: 'warning', 2: 'warning',
    3: 'warning', 4: 'critical', 5: 'critical',
    6: 'critical', 7: 'warning',
}

FAULT_ICONS = {
    0: 'check_circle', 1: 'wb_cloudy', 2: 'blur_on',
    3: 'trending_down', 4: 'electrical_services', 5: 'link_off',
    6: 'bolt', 7: 'sensors',
}

FAULT_COLORS = {
    0: 'green', 1: 'blue', 2: 'amber',
    3: 'orange', 4: 'red', 5: 'red',
    6: 'red', 7: 'purple',
}

# Lazy model cache
_m = {}


def _load(model_key=None):
    global _m
    if 'lgb' in _m or 'xgb' in _m or 'cb' in _m:
        return True
    try:
        _m.clear()

        # Try to load features list from metadata if it exists
        meta_path = os.path.join(MODELS_DIR, 'model_metadata.json')
        if os.path.exists(meta_path):
            with open(meta_path, 'r', encoding='utf-8') as f:
                meta = json.load(f)
                _m['feature_cols'] = meta.get('feature_cols', [])
        
        if not _m.get('feature_cols'):
            from config import Config
            _m['feature_cols'] = Config.FEATURE_COLS

        # Load all available models (.pkl)
        for key, filename in [('lgb', 'lgb_model.pkl'),
                              ('xgb', 'xgb_model.pkl'),
                              ('cb', 'cb_model.pkl')]:
            path = os.path.join(MODELS_DIR, filename)
            if os.path.exists(path):
                _m[key] = joblib.load(path)
                print(f'[AI] Loaded {filename}')

        if 'lgb' not in _m and 'xgb' not in _m and 'cb' not in _m:
            print('[AI] No model files found')
            return "No model files found"

        print(f'[AI] Models loaded: {list(_m.keys())}')
        return True
    except Exception as e:
        import traceback
        print(f'[AI] Model load error: {traceback.format_exc()}')
        _m.clear()
        return str(e)


def _best_model_key():
    """Return the key of the best available model."""
    for k in ['lgb', 'xgb', 'cb']:
        if k in _m:
            return k
    return None


def normalize_dataset(df):
    """
    Ensure all 27 universal features exist in df, calculating/normalizing them if missing.
    """
    from config import Config
    df = df.copy()

    # Active station configuration (used for EFFICIENCY, PERFORMANCE_RATIO display)
    station_config = Config.get_station_config()
    dc_cap_w = station_config['DC_CAPACITY_KW'] * 1000
    inv_eff  = station_config['INVERTER_EFF']
    ac_cap_w = dc_cap_w * inv_eff

    # ── Training reference constants ─────────────────────────────────────────
    # These MUST match the normalization used during model training.
    # Training was done on Arbuckle CA plant (893 kW, 24 inverters, 480 V/inv).
    # Do NOT derive these from Config — they are fixed to the trained models.
    _CAP_REF  = 893_000.0          # W   — rated DC capacity (training plant)
    _AC_CAP   = _CAP_REF * inv_eff # W   — rated AC capacity (training plant)
    _VOLT_REF = 11_520.0           # V   — 24 × 480 V (training plant)
    _CURR_REF = 77.517             # A   — 893,000 / 11,520 (training plant)
    # ─────────────────────────────────────────────────────────────────────────

    # 1. Normalized Power features
    if 'NORM_DC_POWER' not in df.columns:
        if 'DC_POWER' in df.columns:
            df['NORM_DC_POWER'] = np.clip(df['DC_POWER'] / (_CAP_REF + 1e-6), 0, 1.5)
        else:
            df['NORM_DC_POWER'] = 0.0

    if 'NORM_AC_POWER' not in df.columns:
        if 'AC_POWER' in df.columns:
            df['NORM_AC_POWER'] = np.clip(df['AC_POWER'] / (_AC_CAP + 1e-6), 0, 1.5)
        else:
            df['NORM_AC_POWER'] = 0.0

    # 2. DC Voltage & Current
    if 'NORM_DC_VOLTAGE' not in df.columns:
        if 'DC_VOLTAGE' in df.columns:
            df['NORM_DC_VOLTAGE'] = np.clip(df['DC_VOLTAGE'] / _VOLT_REF, 0, 2.0)
        else:
            df['NORM_DC_VOLTAGE'] = 1.0  # fallback

    if 'NORM_DC_CURRENT' not in df.columns:
        if 'DC_CURRENT' in df.columns:
            df['NORM_DC_CURRENT'] = np.clip(df['DC_CURRENT'] / _CURR_REF, 0, 2.0)
        elif 'DC_POWER' in df.columns and 'DC_VOLTAGE' in df.columns:
            dc_volt  = df['DC_VOLTAGE'].values
            dc_power = df['DC_POWER'].values
            dc_curr  = np.where(dc_volt > 0, dc_power / dc_volt, 0)
            df['NORM_DC_CURRENT'] = np.clip(dc_curr / _CURR_REF, 0, 2.0)
        else:
            df['NORM_DC_CURRENT'] = 0.0

    # 3. Volatility, Imbalance, Spread
    if 'NORM_POWER_VOLATILITY' not in df.columns:
        if 'POWER_VOLATILITY' in df.columns:
            df['NORM_POWER_VOLATILITY'] = np.clip(df['POWER_VOLATILITY'] / (_CAP_REF + 1e-6), 0, 1.0)
        elif 'DC_POWER' in df.columns:
            if len(df) > 1:
                df['NORM_POWER_VOLATILITY'] = np.clip(np.abs(df['DC_POWER'].diff().fillna(0)) / (_CAP_REF + 1e-6), 0, 1.0)
            else:
                df['NORM_POWER_VOLATILITY'] = 0.0
        else:
            df['NORM_POWER_VOLATILITY'] = 0.0

    if 'NORM_CURRENT_IMBALANCE' not in df.columns:
        if 'CURRENT_IMBALANCE' in df.columns:
            df['NORM_CURRENT_IMBALANCE'] = np.clip(df['CURRENT_IMBALANCE'] / _CURR_REF, 0, 1.0)
        elif 'DC_CURRENT' in df.columns:
            if len(df) > 1:
                rolling_curr = df['DC_CURRENT'].rolling(6, min_periods=1).mean()
                df['NORM_CURRENT_IMBALANCE'] = np.clip(np.abs(df['DC_CURRENT'] - rolling_curr) / _CURR_REF, 0, 1.0)
            else:
                df['NORM_CURRENT_IMBALANCE'] = 0.0
        else:
            df['NORM_CURRENT_IMBALANCE'] = 0.0

    if 'NORM_VOLTAGE_SPREAD' not in df.columns:
        if 'VOLTAGE_SPREAD' in df.columns:
            df['NORM_VOLTAGE_SPREAD'] = np.clip(df['VOLTAGE_SPREAD'] / _VOLT_REF, 0, 1.0)
        elif 'DC_VOLTAGE' in df.columns:
            if len(df) > 1:
                rolling_volt = df['DC_VOLTAGE'].rolling(6, min_periods=1).mean()
                df['NORM_VOLTAGE_SPREAD'] = np.clip(np.abs(df['DC_VOLTAGE'] - rolling_volt) / _VOLT_REF, 0, 1.0)
            else:
                df['NORM_VOLTAGE_SPREAD'] = 0.0
        else:
            df['NORM_VOLTAGE_SPREAD'] = 0.0

    # Ensure all other columns exist (either directly or computed)
    if 'DC_AC_RATIO' not in df.columns:
        if 'DC_POWER' in df.columns and 'AC_POWER' in df.columns:
            df['DC_AC_RATIO'] = np.where(df['AC_POWER'] > 0, df['DC_POWER'] / df['AC_POWER'], 0)
        else:
            df['DC_AC_RATIO'] = 1.0 / inv_eff

    if 'EFFICIENCY' not in df.columns:
        if 'DC_POWER' in df.columns and 'IRRADIATION' in df.columns:
            df['EFFICIENCY'] = np.where(df['IRRADIATION'] > 0, (df['DC_POWER'] / (df['IRRADIATION'] * _CAP_REF / 1000.0)) * 100.0, 0)
        else:
            df['EFFICIENCY'] = 100.0

    if 'PERFORMANCE_RATIO' not in df.columns:
        if 'AC_POWER' in df.columns and 'IRRADIATION' in df.columns:
            df['PERFORMANCE_RATIO'] = np.where(df['IRRADIATION'] > 0, (df['AC_POWER'] / (df['IRRADIATION'] / 1000.0 * _CAP_REF * inv_eff)) * 100.0, 0)
        else:
            df['PERFORMANCE_RATIO'] = 100.0

    if 'DC_AC_DEV' not in df.columns:
        df['DC_AC_DEV'] = df['DC_AC_RATIO'] - (1.0 / inv_eff)

    if 'TEMP_DIFFERENCE' not in df.columns and 'MODULE_TEMP' in df.columns and 'AMBIENT_TEMP' in df.columns:
        df['TEMP_DIFFERENCE'] = df['MODULE_TEMP'] - df['AMBIENT_TEMP']

    if 'TEMP_DEV' not in df.columns and 'MODULE_TEMP' in df.columns and 'AMBIENT_TEMP' in df.columns and 'IRRADIATION' in df.columns:
        df['TEMP_DEV'] = df['MODULE_TEMP'] - (df['AMBIENT_TEMP'] + (df['IRRADIATION'] / 800.0) * 30.0)

    if 'TEMP_COEFF' not in df.columns and 'MODULE_TEMP' in df.columns:
        df['TEMP_COEFF'] = 1.0 + Config.get_station_config()['GAMMA_PDC'] * (df['MODULE_TEMP'] - 25.0)

    if 'CLEARNESS_INDEX' not in df.columns and 'IRRADIATION' in df.columns and 'ZENITH_ANGLE' in df.columns:
        df['CLEARNESS_INDEX'] = np.clip(df['IRRADIATION'] / (1000.0 * np.cos(df['ZENITH_ANGLE'] * np.pi / 180.0) + 0.01), 0, 1.5)

    if 'DIFFUSE_RATIO' not in df.columns and 'CLEARNESS_INDEX' in df.columns:
        df['DIFFUSE_RATIO'] = np.clip(1.0 - df['CLEARNESS_INDEX'] * 0.8, 0, 1)

    if 'CLOUD_COVER_EST' not in df.columns and 'CLEARNESS_INDEX' in df.columns:
        df['CLOUD_COVER_EST'] = np.clip((1.0 - df['CLEARNESS_INDEX']) * 100.0, 0, 100)

    if 'SKY_TEMP_EST' not in df.columns and 'AMBIENT_TEMP' in df.columns and 'CLOUD_COVER_EST' in df.columns:
        df['SKY_TEMP_EST'] = df['AMBIENT_TEMP'] - 20.0 - df['CLOUD_COVER_EST'] * 0.15

    # Any other feature defaults to 0.0
    for col in Config.FEATURE_COLS:
        if col not in df.columns:
            df[col] = 0.0

    return df


def infer_single_row(features_dict, model_key=None):
    """
    Classify a single row of solar data.
    features_dict: dict with either absolute or normalized solar features.
    """
    if not _load():
        return {'error': 'Models not loaded. Place .pkl files in models/ directory.'}

    # Convert single row dict to DataFrame for uniform processing
    df = pd.DataFrame([features_dict])
    df_norm = normalize_dataset(df)
    
    feature_cols = _m.get('feature_cols', [])
    if not feature_cols:
        from config import Config
        feature_cols = Config.FEATURE_COLS

    # Build feature vector in correct order
    row = []
    for col in feature_cols:
        val = df_norm.iloc[0].get(col, 0.0)
        try:
            val = float(val)
        except (ValueError, TypeError):
            val = 0.0
        row.append(val)

    X = np.array([row], dtype=np.float64)

    # Predict (No Scaling needed!)
    key = model_key or _best_model_key()
    if key is None or key not in _m:
        return {'error': 'No model available'}

    model = _m[key]
    pred = int(model.predict(X)[0])
    proba = model.predict_proba(X)[0] if hasattr(model, 'predict_proba') else None

    fault_label = FAULT_LABELS.get(pred, f'Unknown (F{pred})')
    fault_prob = float(np.max(proba)) if proba is not None else 1.0
    fault_probs = {}
    if proba is not None:
        for i, p in enumerate(proba):
            fname = FAULT_LABELS.get(i, f'F{i}')
            fault_probs[fname] = round(float(p), 4)

    severity = FAULT_SEVERITY.get(pred, 'warning')
    recommendation = FAULT_RECOMMENDATIONS.get(pred, 'Inspect the system and consult the maintenance manual.')

    return {
        'fault_label_id': pred,
        'fault_type': fault_label,
        'fault_prob': round(fault_prob, 4),
        'fault_probs': fault_probs,
        'severity': severity,
        'recommendation': recommendation,
        'model_used': f'LightGBM' if key == 'lgb' else f'XGBoost' if key == 'xgb' else 'CatBoost',
        'features_used': len(feature_cols),
    }


def infer_dataset(df, model_key=None):
    """
    Run inference on a full DataFrame.
    Returns per-row predictions plus summary statistics.
    """
    load_res = _load()
    if load_res is not True:
        err_msg = load_res if isinstance(load_res, str) else 'Unknown error'
        return {'error': f'Models not loaded: {err_msg}', 'results': [], 'summary': {}}

    feature_cols = _m.get('feature_cols', [])
    if not feature_cols:
        from config import Config
        feature_cols = Config.FEATURE_COLS

    # Normalize dataset
    df_norm = normalize_dataset(df)

    # Ensure all feature columns exist in df_norm
    for col in feature_cols:
        if col not in df_norm.columns:
            df_norm[col] = 0.0

    X = df_norm[feature_cols].values.astype(np.float64)

    # Replace NaN/inf
    X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)

    key = model_key or _best_model_key()
    if key is None or key not in _m:
        return {'error': 'No model available', 'results': [], 'summary': {}}

    model = _m[key]
    preds = model.predict(X).ravel().astype(int)
    probas = model.predict_proba(X) if hasattr(model, 'predict_proba') else None

    # Per-row results
    results = []
    for i, pred in enumerate(preds):
        fault_name = FAULT_LABELS.get(pred, f'F{pred}')
        fault_prob = float(np.max(probas[i])) if probas is not None else 1.0
        fault_probs = {}
        if probas is not None:
            for j, p in enumerate(probas[i]):
                fname = FAULT_LABELS.get(j, f'F{j}')
                fault_probs[fname] = round(float(p), 4)

        results.append({
            'row_index': i,
            'fault_label_id': int(pred),
            'fault_type': fault_name,
            'fault_prob': round(fault_prob, 4),
            'fault_probs': fault_probs,
            'severity': FAULT_SEVERITY.get(pred, 'warning'),
        })

    # Summary
    fault_counts = {}
    for r in results:
        ft = r['fault_type']
        fault_counts[ft] = fault_counts.get(ft, 0) + 1

    anomaly_count = sum(1 for r in results if r['fault_label_id'] != 0)
    total = len(results)
    dominant = max(fault_counts, key=fault_counts.get) if fault_counts else 'Normal'

    severity = 'normal'
    if any(r['severity'] == 'critical' for r in results if r['fault_label_id'] != 0):
        severity = 'critical'
    elif anomaly_count > 0:
        severity = 'warning'

    avg_conf = float(np.mean([r['fault_prob'] for r in results])) if results else 0.0

    model_name = 'LightGBM' if key == 'lgb' else 'XGBoost' if key == 'xgb' else 'CatBoost'

    return {
        'results': results[:500],   # cap at 500 for memory
        'summary': {
            'total_rows': total,
            'anomaly_count': anomaly_count,
            'normal_count': total - anomaly_count,
            'dominant_fault': dominant,
            'severity': severity,
            'avg_confidence': round(avg_conf, 4),
            'fault_distribution': fault_counts,
            'model_used': model_name,
        },
    }


def get_model_info():
    """Return info about loaded models."""
    if not _load():
        return {'loaded': False, 'models': []}
    info = {
        'loaded': True,
        'models': [],
        'feature_count': len(_m.get('feature_cols', [])),
    }
    for key in ['lgb', 'xgb', 'cb']:
        if key in _m:
            name = 'LightGBM' if key == 'lgb' else 'XGBoost' if key == 'xgb' else 'CatBoost'
            info['models'].append({'key': key, 'name': name})
    return info
