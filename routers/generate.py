import os
import io
import time
import numpy as np
import pandas as pd
from flask import Blueprint, render_template, jsonify, request, send_file
from flask_login import login_required, current_user
import uuid
from werkzeug.utils import secure_filename
import pvlib
from pvlib.pvsystem import PVSystem, Array, FixedMount
from pvlib.location import Location

generate_bp = Blueprint('generate', __name__)

_HERE    = os.path.dirname(os.path.abspath(__file__))
_APPDIR  = os.path.dirname(_HERE)
_DATA    = os.path.join(_APPDIR, 'data')

def get_generator_config():
    from config import Config
    c = Config.get_station_config()
    return {
        'DC_CAPACITY_KW': c['DC_CAPACITY_KW'],
        'NUM_INVERTERS': c['NUM_INVERTERS'],
        'INVERTER_EFF': c['INVERTER_EFF'],
        'TEMP_COEFF_POWER': c['GAMMA_PDC'],
        'REF_TEMP': 25,
        'DC_CAPACITY_W': c['DC_CAPACITY_KW'] * 1000,
        'FAULT_LABELS': Config.FAULT_LABELS,
    }

class PVLibFaultInjector:
    def __init__(self, config):
        self.config = config
        self.dc_cap = config["DC_CAPACITY_W"]
        self.inv_eff = config["INVERTER_EFF"]
        self.temp_coeff = config["TEMP_COEFF_POWER"]
        self.ref_temp = config["REF_TEMP"]
        self.fault_labels = config["FAULT_LABELS"]

    def _pvwatts_dc(self, g_poa_effective, temp_cell, pdc0):
        return pvlib.pvsystem.pvwatts_dc(
            g_poa_effective, temp_cell, pdc0,
            self.temp_coeff, self.ref_temp)

    def _pvwatts_ac(self, pdc, pdc0, eta_inv_nom):
        return pvlib.inverter.pvwatts(pdc, pdc0, eta_inv_nom=eta_inv_nom)

    def _update_derived(self, df, indices):
        dc_p = df.loc[indices, "DC_POWER"].values
        dc_v = df.loc[indices, "DC_VOLTAGE"].values
        ac_p = df.loc[indices, "AC_POWER"].values
        irr = df.loc[indices, "IRRADIATION"].values
        df.loc[indices, "DC_CURRENT"] = np.where(dc_v > 0, dc_p / dc_v, 0)
        df.loc[indices, "DC_AC_RATIO"] = np.where(ac_p > 0, dc_p / ac_p, 0)
        df.loc[indices, "EFFICIENCY"] = np.where(irr > 0, (dc_p / (irr * self.dc_cap / 1000)) * 100, 0)
        df.loc[indices, "PERFORMANCE_RATIO"] = np.where(irr > 0, (ac_p / (irr / 1000 * self.dc_cap * self.inv_eff)) * 100, 0)
        df.loc[indices, "DC_AC_DEV"] = df.loc[indices, "DC_AC_RATIO"].values - (1 / self.inv_eff)
        df.loc[indices, "IRR_DC_RATIO"] = np.where(irr > 0, dc_p / irr, 0)

    def inject_partial_shading(self, df, indices, severities):
        irr = df.loc[indices, "IRRADIATION"].values
        temp = df.loc[indices, "MODULE_TEMP"].values
        real_dc = df.loc[indices, "DC_POWER"].values
        real_ac = df.loc[indices, "AC_POWER"].values
        shaded_frac = severities * 0.5
        shade_factor = 1 - severities * 0.6
        dc_unshaded = self._pvwatts_dc(irr, temp, self.dc_cap * (1 - shaded_frac))
        dc_shaded = self._pvwatts_dc(irr * shade_factor, temp, self.dc_cap * shaded_frac)
        dc_faulted = np.maximum(dc_unshaded + dc_shaded, 0)
        dc_normal = self._pvwatts_dc(irr, temp, self.dc_cap)
        ratio = np.where(dc_normal > 0, dc_faulted / dc_normal, 0)
        df.loc[indices, "DC_POWER"] = real_dc * ratio
        ac_normal = self._pvwatts_ac(dc_normal, self.dc_cap, self.inv_eff)
        ac_faulted = self._pvwatts_ac(dc_faulted, self.dc_cap, self.inv_eff)
        ac_ratio = np.where(ac_normal > 0, ac_faulted / ac_normal, 0)
        df.loc[indices, "AC_POWER"] = real_ac * ac_ratio
        df.loc[indices, "CURRENT_IMBALANCE"] = np.abs(dc_unshaded - dc_shaded) / (dc_faulted + 1) * 0.5
        self._update_derived(df, indices)
        df.loc[indices, "fault_label_id"] = 1

    def inject_soiling(self, df, indices, severities):
        irr = df.loc[indices, "IRRADIATION"].values
        temp = df.loc[indices, "MODULE_TEMP"].values
        real_dc = df.loc[indices, "DC_POWER"].values
        real_ac = df.loc[indices, "AC_POWER"].values
        soiling_factor = 1 - severities * 0.25
        g_poa_effective = irr * soiling_factor
        dc_normal = self._pvwatts_dc(irr, temp, self.dc_cap)
        dc_faulted = self._pvwatts_dc(g_poa_effective, temp, self.dc_cap)
        ratio = np.where(dc_normal > 0, dc_faulted / dc_normal, 0)
        df.loc[indices, "DC_POWER"] = real_dc * ratio
        ac_normal = self._pvwatts_ac(dc_normal, self.dc_cap, self.inv_eff)
        ac_faulted = self._pvwatts_ac(dc_faulted, self.dc_cap, self.inv_eff)
        ac_ratio = np.where(ac_normal > 0, ac_faulted / ac_normal, 0)
        df.loc[indices, "AC_POWER"] = real_ac * ac_ratio
        df.loc[indices, "CURRENT_IMBALANCE"] = severities * 0.5e-3 * _CAP_REF / 1000  # small realistic imbalance
        self._update_derived(df, indices)
        df.loc[indices, "fault_label_id"] = 2

    def inject_degradation(self, df, indices, severities):
        irr = df.loc[indices, "IRRADIATION"].values
        temp = df.loc[indices, "MODULE_TEMP"].values
        real_dc = df.loc[indices, "DC_POWER"].values
        real_ac = df.loc[indices, "AC_POWER"].values
        pdc0_degraded = self.dc_cap * (1 - severities * 0.08)
        dc_normal = self._pvwatts_dc(irr, temp, self.dc_cap)
        dc_faulted = self._pvwatts_dc(irr, temp, pdc0_degraded)
        ratio = np.where(dc_normal > 0, dc_faulted / dc_normal, 0)
        df.loc[indices, "DC_POWER"] = real_dc * ratio
        ac_normal = self._pvwatts_ac(dc_normal, self.dc_cap, self.inv_eff)
        ac_faulted = self._pvwatts_ac(dc_faulted, self.dc_cap, self.inv_eff)
        ac_ratio = np.where(ac_normal > 0, ac_faulted / ac_normal, 0)
        df.loc[indices, "AC_POWER"] = real_ac * ac_ratio
        df.loc[indices, "DC_VOLTAGE"] *= (1 - severities * 0.03)
        self._update_derived(df, indices)
        df.loc[indices, "fault_label_id"] = 3

    def inject_inverter_fault(self, df, indices, severities):
        irr = df.loc[indices, "IRRADIATION"].values
        temp = df.loc[indices, "MODULE_TEMP"].values
        real_ac = df.loc[indices, "AC_POWER"].values
        dc_normal = self._pvwatts_dc(irr, temp, self.dc_cap)
        eta_fault = self.inv_eff * (1 - severities * 0.8)
        ac_normal = self._pvwatts_ac(dc_normal, self.dc_cap, self.inv_eff)
        ac_faulted = self._pvwatts_ac(dc_normal, self.dc_cap, eta_fault)
        ac_ratio = np.where(ac_normal > 0, ac_faulted / ac_normal, 0)
        df.loc[indices, "AC_POWER"] = real_ac * ac_ratio
        ac_p = df.loc[indices, "AC_POWER"].values
        _AC_BUS_VOLTAGE = 480   # V — AC grid bus voltage (Arbuckle CA plant)
        df.loc[indices, "AC_CURRENT"] = np.where(ac_p > 0, ac_p / (_AC_BUS_VOLTAGE * np.sqrt(3)), 0)
        self._update_derived(df, indices)
        df.loc[indices, "fault_label_id"] = 4

    def inject_open_circuit(self, df, indices, severities):
        irr = df.loc[indices, "IRRADIATION"].values
        temp = df.loc[indices, "MODULE_TEMP"].values
        real_dc = df.loc[indices, "DC_POWER"].values
        real_ac = df.loc[indices, "AC_POWER"].values
        strings_lost = np.maximum(1, (severities * 4).astype(int))
        _STRINGS_PER_INV = 7   # Arbuckle CA plant: 7 strings per inverter
        remaining_frac = 1 - (strings_lost / _STRINGS_PER_INV)
        pdc0_reduced = self.dc_cap * remaining_frac
        dc_normal = self._pvwatts_dc(irr, temp, self.dc_cap)
        dc_faulted = self._pvwatts_dc(irr, temp, pdc0_reduced)
        ratio = np.where(dc_normal > 0, dc_faulted / dc_normal, 0)
        df.loc[indices, "DC_POWER"] = real_dc * ratio
        ac_normal = self._pvwatts_ac(dc_normal, self.dc_cap, self.inv_eff)
        ac_faulted = self._pvwatts_ac(dc_faulted, self.dc_cap, self.inv_eff)
        ac_ratio = np.where(ac_normal > 0, ac_faulted / ac_normal, 0)
        df.loc[indices, "AC_POWER"] = real_ac * ac_ratio
        df.loc[indices, "DC_CURRENT"] *= remaining_frac
        self._update_derived(df, indices)
        df.loc[indices, "fault_label_id"] = 5

    def inject_short_circuit(self, df, indices, severities):
        irr = df.loc[indices, "IRRADIATION"].values
        temp = df.loc[indices, "MODULE_TEMP"].values
        real_dc = df.loc[indices, "DC_POWER"].values
        real_ac = df.loc[indices, "AC_POWER"].values
        irr_factor = 1 - severities * 0.5
        temp_elevated = temp + severities * 30
        dc_normal = self._pvwatts_dc(irr, temp, self.dc_cap)
        dc_faulted = self._pvwatts_dc(irr * irr_factor, temp_elevated, self.dc_cap)
        ratio = np.where(dc_normal > 0, dc_faulted / dc_normal, 0)
        df.loc[indices, "DC_POWER"] = real_dc * ratio
        ac_normal = self._pvwatts_ac(dc_normal, self.dc_cap, self.inv_eff)
        ac_faulted = self._pvwatts_ac(dc_faulted, self.dc_cap, self.inv_eff)
        ac_ratio = np.where(ac_normal > 0, ac_faulted / ac_normal, 0)
        df.loc[indices, "AC_POWER"] = real_ac * ac_ratio
        df.loc[indices, "DC_VOLTAGE"] *= (1 - severities * 0.4)
        df.loc[indices, "MODULE_TEMP"] = temp_elevated
        df.loc[indices, "VOLTAGE_SPREAD"] = severities * 0.3 * np.abs(df.loc[indices, "DC_VOLTAGE"])
        self._update_derived(df, indices)
        df.loc[indices, "fault_label_id"] = 6

    def inject_sensor_fault(self, df, indices, severities):
        n = len(indices)
        fault_kinds = np.random.random(n)
        irr = df.loc[indices, "IRRADIATION"].values.astype(np.float64)
        mask_stuck = fault_kinds < 0.33
        irr[mask_stuck] = np.random.uniform(200, 600, mask_stuck.sum())
        mask_offset = (fault_kinds >= 0.33) & (fault_kinds < 0.66)
        irr[mask_offset] += np.random.uniform(-200, 200, mask_offset.sum())
        mask_spike = fault_kinds >= 0.66
        irr[mask_spike] *= np.random.uniform(1.5, 3.0, mask_spike.sum())
        irr = np.maximum(irr, 0)
        df.loc[indices, "IRRADIATION"] = irr
        dc_p = df.loc[indices, "DC_POWER"].values
        ac_p = df.loc[indices, "AC_POWER"].values
        df.loc[indices, "EFFICIENCY"] = np.where(irr > 0, (dc_p / (irr * self.dc_cap / 1000)) * 100, 0)
        df.loc[indices, "PERFORMANCE_RATIO"] = np.where(irr > 0, (ac_p / (irr / 1000 * self.dc_cap * self.inv_eff)) * 100, 0)
        df.loc[indices, "IRR_DC_RATIO"] = np.where(irr > 0, dc_p / irr, 0)
        df.loc[indices, "CLEARNESS_INDEX"] = np.clip(
            irr / (1000 * np.cos(df.loc[indices, "ZENITH_ANGLE"].values * np.pi / 180) + 0.01), 0, 1.5)
        df.loc[indices, "DIFFUSE_RATIO"] = np.clip(1 - df.loc[indices, "CLEARNESS_INDEX"].values * 0.8, 0, 1)
        df.loc[indices, "CLOUD_COVER_EST"] = np.clip((1 - df.loc[indices, "CLEARNESS_INDEX"].values) * 100, 0, 100)
        temp_corrupt_mask = np.random.random(n) < 0.5
        ambient_t = df.loc[indices, "AMBIENT_TEMP"].values.astype(np.float64)
        module_t = df.loc[indices, "MODULE_TEMP"].values.astype(np.float64)
        stuck_mask = temp_corrupt_mask & (np.random.random(n) < 0.5)
        ambient_t[stuck_mask] = 25.0
        module_t[stuck_mask] = 45.0
        offset_mask = temp_corrupt_mask & ~stuck_mask
        ambient_t[offset_mask] += np.random.uniform(-10, 10, offset_mask.sum())
        module_t[offset_mask] += np.random.uniform(-15, 15, offset_mask.sum())
        df.loc[indices, "AMBIENT_TEMP"] = ambient_t
        df.loc[indices, "MODULE_TEMP"] = module_t
        df.loc[indices, "TEMP_DIFFERENCE"] = module_t - ambient_t
        df.loc[indices, "TEMP_DEV"] = module_t - (ambient_t + (irr / 800) * 30)
        df.loc[indices, "TEMP_COEFF"] = 1 + self.temp_coeff * (module_t - self.ref_temp)
        df.loc[indices, "fault_label_id"] = 7


@generate_bp.route('/generate', methods=['GET'])
@login_required
def index():
    from config import Config
    
    # Scan all CSV files in data directory
    available_datasets = []
    if os.path.exists(_DATA):
        for f in os.listdir(_DATA):
            if f.endswith('.csv'):
                available_datasets.append(f)
                
    available_datasets.sort()
    dataset_exists = len(available_datasets) > 0
    
    # Determine the selected dataset
    default_dataset = 'processed_dataset_universal.csv'
    if default_dataset not in available_datasets and available_datasets:
        default_dataset = available_datasets[0]
        
    current_dataset = request.args.get('dataset_file', default_dataset)
    if current_dataset not in available_datasets and available_datasets:
        current_dataset = available_datasets[0]
        
    total_clean_rows = 1000000 # Dummy max value, actual limit handled by user input

    return render_template('generate/index.html',
                           dataset_exists=dataset_exists,
                           available_datasets=available_datasets,
                           current_dataset=current_dataset,
                           total_clean_rows=total_clean_rows,
                           station_name=Config.get_station_config()['STATION_NAME'],
                           dc_capacity_kw=Config.get_station_config()['DC_CAPACITY_KW'])


@generate_bp.route('/generate/upload', methods=['POST'])
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
    
    # Optional: basic validation of rows could go here
    try:
        import pandas as pd
        preview = pd.read_csv(upload_path, nrows=5)
        # Check if it has any columns
        if len(preview.columns) == 0:
            return jsonify({'error': 'CSV file is empty or invalid'}), 400
    except Exception as e:
        return jsonify({'error': f'Error reading CSV: {str(e)}'}), 400

    return jsonify({'success': True, 'filename': filename, 'original_name': file.filename})

@generate_bp.route('/generate/download', methods=['POST'])
@login_required
def download():
    from ai_inference import normalize_dataset
    
    data = request.json
    total_rows = int(data.get('totalRows', 5000))
    fault_distribution = data.get('distribution', {})  # e.g. {"1": 10, "2": 15, ...}
    base_dataset = data.get('baseDataset', 'processed_dataset_universal.csv')
    
    # Secure validation of base dataset file name
    base_dataset = os.path.basename(base_dataset)
    path = os.path.join(_DATA, base_dataset)
    if not os.path.exists(path):
        return jsonify({"error": f"Base dataset '{base_dataset}' not found in data/ directory."}), 404

    # Load base dataset
    try:
        df_base = pd.read_csv(path)
    except Exception as e:
        return jsonify({"error": f"Failed to load dataset: {str(e)}"}), 500

    if len(df_base) < total_rows:
        total_rows = len(df_base)

    # Sample rows — filter to MIDDAY quality rows only.
    # IRRADIATION > 300 W/m² AND PERFORMANCE_RATIO > 70% excludes dawn/dusk
    # periods whose naturally-low power output overlaps with fault signatures
    # (Soiling, Degradation, Partial Shading), which would corrupt the Normal class
    # and cause the AI model to misclassify Normal-labeled rows as faulty.
    if 'IRRADIATION' in df_base.columns:
        # Strong midday filter: high irradiance + good performance
        good_rows = df_base[df_base['IRRADIATION'] > 300]
        if 'PERFORMANCE_RATIO' in df_base.columns:
            good_rows = good_rows[good_rows['PERFORMANCE_RATIO'] > 70]
        if 'NORM_DC_POWER' in df_base.columns:
            good_rows = good_rows[good_rows['NORM_DC_POWER'] > 0.25]

        if len(good_rows) >= total_rows:
            df = good_rows.sample(n=total_rows).reset_index(drop=True)
        elif len(good_rows) >= max(total_rows // 2, 50):
            # Relax to IRRADIATION > 150 + PR > 60
            fallback1 = df_base[df_base['IRRADIATION'] > 150]
            if 'PERFORMANCE_RATIO' in df_base.columns:
                fallback1 = fallback1[fallback1['PERFORMANCE_RATIO'] > 60]
            if len(fallback1) >= total_rows:
                df = fallback1.sample(n=total_rows).reset_index(drop=True)
            else:
                df = fallback1.sample(n=total_rows, replace=True).reset_index(drop=True)
        else:
            # Last resort: basic daytime filter
            daytime = df_base[df_base['IRRADIATION'] > 50]
            if len(daytime) >= total_rows:
                df = daytime.sample(n=total_rows).reset_index(drop=True)
            else:
                df = df_base.sample(n=total_rows, replace=True).reset_index(drop=True)
    else:
        df = df_base.sample(n=total_rows).reset_index(drop=True)

    # Get active generator configuration
    generator_config = get_generator_config()

    # Training reference constants — fixed to match model training normalization
    # (Arbuckle CA plant: 893 kW, 24 inverters, 480 V/inverter)
    _CAP_REF  = 893_000.0          # W  — training plant rated DC capacity
    _VOLT_REF = 11_520.0           # V  — 24 × 480 V
    _CURR_REF = 77.517             # A  — 893,000 / 11,520
    inv_eff   = generator_config["INVERTER_EFF"]

    # Reconstruct raw absolute columns using training reference scale
    # (keeps DC_POWER / DC_VOLTAGE at the same magnitude as during training)
    if 'NORM_DC_POWER' in df.columns:
        df["DC_POWER"]   = df["NORM_DC_POWER"]   * _CAP_REF
        df["AC_POWER"]   = df["NORM_AC_POWER"]   * (_CAP_REF * inv_eff)
        df["DC_VOLTAGE"] = df["NORM_DC_VOLTAGE"] * _VOLT_REF
        df["DC_CURRENT"] = df["NORM_DC_CURRENT"] * _CURR_REF
    else:
        # Fallback: base dataset has raw physical columns — keep at original scale
        # DC_VOLTAGE is already correct (string voltage independent of capacity)
        # DC_POWER / DC_CURRENT are at 893 kW plant scale — leave unchanged
        pass  # no scaling needed

    df = df.copy()
    df["fault_label_id"] = 0
    df["fault_type"] = "Normal"

    # Pre-initialize key columns to prevent KeyError in injector functions
    for col in ["CURRENT_IMBALANCE", "VOLTAGE_SPREAD"]:
        if col not in df.columns:
            df[col] = 0.0

    # Calculate indices for each fault
    indices = np.random.permutation(total_rows)
    current_idx = 0

    injector = PVLibFaultInjector(generator_config)
    inject_methods = {
        1: injector.inject_partial_shading,
        2: injector.inject_soiling,
        3: injector.inject_degradation,
        4: injector.inject_inverter_fault,
        5: injector.inject_open_circuit,
        6: injector.inject_short_circuit,
        7: injector.inject_sensor_fault
    }

    for fault_id_str, percentage in fault_distribution.items():
        fault_id = int(fault_id_str)
        pct = float(percentage)
        num_rows = int((pct / 100.0) * total_rows)
        
        if num_rows > 0 and fault_id in inject_methods:
            idx_array = indices[current_idx:current_idx + num_rows]
            severities = np.random.uniform(0.5, 1.0, num_rows)
            inject_methods[fault_id](df, idx_array, severities)
            current_idx += num_rows

    # Drop old normalized and derived columns to force correct recalculation under the new capacity config
    cols_to_drop = [
        'NORM_DC_POWER', 'NORM_AC_POWER', 'NORM_DC_VOLTAGE', 'NORM_DC_CURRENT',
        'NORM_POWER_VOLATILITY', 'NORM_CURRENT_IMBALANCE', 'NORM_VOLTAGE_SPREAD',
        'DC_AC_RATIO', 'EFFICIENCY', 'PERFORMANCE_RATIO', 'DC_AC_DEV',
        'TEMP_COEFF', 'TEMP_DIFFERENCE', 'TEMP_DEV',
        'CLEARNESS_INDEX', 'DIFFUSE_RATIO', 'CLOUD_COVER_EST', 'SKY_TEMP_EST'
    ]
    df = df.drop(columns=[c for c in cols_to_drop if c in df.columns], errors='ignore')

    # Re-normalize using the active capacity configuration from config.py
    try:
        df = normalize_dataset(df)
    except Exception as e:
        import traceback
        print(f"[Generator] Error during dynamic normalization: {traceback.format_exc()}")

    # Map labels
    df = df.copy()
    df["fault_label"] = df["fault_label_id"]
    df["fault_type"] = df["fault_label_id"].map(generator_config['FAULT_LABELS'])

    # Write to memory buffer
    output = io.BytesIO()
    df.to_csv(output, index=False)
    output.seek(0)
    
    return send_file(
        output,
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'generated_dataset_{len(df)}rows.csv'
    )


@generate_bp.route('/generate/delete/<filename>', methods=['POST'])
@login_required
def delete_dataset(filename):
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    filename = secure_filename(filename)
    path = os.path.join(_DATA, filename)
    if os.path.exists(path):
        try:
            os.remove(path)
            return jsonify({'success': True})
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    return jsonify({'error': 'File not found'}), 404


@generate_bp.route('/generate/delete-all', methods=['POST'])
@login_required
def delete_all_datasets():
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
        
    try:
        if os.path.exists(_DATA):
            for f in os.listdir(_DATA):
                if f.endswith('.csv'):
                    os.remove(os.path.join(_DATA, f))
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
