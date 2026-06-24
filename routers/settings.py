from flask import Blueprint, render_template, request, jsonify
from config import Config
from db import execute_db, query_db
import functools

settings_bp = Blueprint('settings', __name__, url_prefix='/settings')

# We use the existing logic for user authentication if we want to protect it, but currently the app doesn't enforce `@login_required` rigidly on some simple routes, though it's better. We'll skip for now or use Flask-Login if available.
# Let's assume user must be logged in. In `app.py` we can see login manager is used.
from flask_login import login_required

@settings_bp.route('/', methods=['GET'])
@login_required
def index():
    config = Config.get_station_config()
    return render_template('settings/index.html', config=config)

@settings_bp.route('/save', methods=['POST'])
@login_required
def save():
    try:
        data = request.form
        
        # Validate data basic types
        station_id = data.get('station_id')
        station_name = data.get('station_name')
        dc_cap = float(data.get('dc_capacity_kw', 0))
        num_inv = int(data.get('num_inverters', 0))
        inv_eff = float(data.get('inverter_eff', 0))
        pdc0_w = float(data.get('pdc0_w', 0))
        gamma_pdc = float(data.get('gamma_pdc', 0))
        eta_inv = float(data.get('eta_inv', 0))
        
        if not station_id or not station_name:
            return jsonify({'success': False, 'message': 'Station ID and Name are required'})
            
        execute_db('''
            UPDATE station_settings 
            SET station_id=%s, station_name=%s, dc_capacity_kw=%s, num_inverters=%s, 
                inverter_eff=%s, pdc0_w=%s, gamma_pdc=%s, eta_inv=%s
            WHERE id = 1
        ''', (station_id, station_name, dc_cap, num_inv, inv_eff, pdc0_w, gamma_pdc, eta_inv))
        
        return jsonify({'success': True, 'message': 'Configuration saved successfully!'})
        
    except ValueError as e:
        return jsonify({'success': False, 'message': 'Invalid number format provided. Please check your inputs.'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@settings_bp.route('/reset', methods=['POST'])
@login_required
def reset():
    try:
        execute_db('''
            UPDATE station_settings 
            SET station_id='2107', station_name='Arbuckle CA', dc_capacity_kw=893, num_inverters=24, 
                inverter_eff=0.96, pdc0_w=893000, gamma_pdc=-0.004, eta_inv=0.96
            WHERE id = 1
        ''')
        return jsonify({'success': True, 'message': 'Configuration reset to Arbuckle CA defaults!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})
