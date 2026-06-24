import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'solarguard-ai-secret-2025')
    DB_HOST     = os.environ.get('DB_HOST', 'localhost')
    DB_NAME     = os.environ.get('DB_NAME', 'solar_db')
    DB_USER     = os.environ.get('DB_USER', 'root')
    DB_PASSWORD = os.environ.get('DB_PASSWORD', 'root')
    DB_PORT     = int(os.environ.get('DB_PORT', '8889'))   # MAMP default
    PERMANENT_SESSION_LIFETIME = 86400

    # Model Configuration — 27 features, 8 fault classes
    @staticmethod
    def get_station_config():
        from db import query_db, execute_db
        # Ensure table exists and has defaults
        execute_db('''
            CREATE TABLE IF NOT EXISTS station_settings (
                id INT PRIMARY KEY DEFAULT 1,
                station_id VARCHAR(50) NOT NULL,
                station_name VARCHAR(150) NOT NULL,
                dc_capacity_kw FLOAT NOT NULL,
                num_inverters INT NOT NULL,
                inverter_eff FLOAT NOT NULL,
                pdc0_w FLOAT NOT NULL,
                gamma_pdc FLOAT NOT NULL,
                eta_inv FLOAT NOT NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        ''')
        
        row = query_db('SELECT * FROM station_settings WHERE id = 1', one=True)
        if not row:
            # Insert defaults (Arbuckle CA 893kW)
            execute_db('''
                INSERT INTO station_settings 
                (id, station_id, station_name, dc_capacity_kw, num_inverters, inverter_eff, pdc0_w, gamma_pdc, eta_inv)
                VALUES (1, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', ('2107', 'Arbuckle CA', 893, 24, 0.96, 893000, -0.004, 0.96))
            row = query_db('SELECT * FROM station_settings WHERE id = 1', one=True)
            
        return {
            'STATION_ID': row['station_id'],
            'STATION_NAME': row['station_name'],
            'DC_CAPACITY_KW': float(row['dc_capacity_kw']),
            'NUM_INVERTERS': int(row['num_inverters']),
            'INVERTER_EFF': float(row['inverter_eff']),
            'PDC0_W': float(row['pdc0_w']),
            'GAMMA_PDC': float(row['gamma_pdc']),
            'ETA_INV': float(row['eta_inv'])
        }

    # Model Configuration — 27 features, 8 fault classes
    FAULT_LABELS = {
        0: 'Normal',
        1: 'Partial Shading',
        2: 'Soiling',
        3: 'Degradation',
        4: 'Inverter Fault',
        5: 'Open-Circuit String',
        6: 'Short-Circuit',
        7: 'Sensor Fault',
    }

    FEATURE_COLS = [
        'NORM_DC_POWER', 'NORM_AC_POWER', 'NORM_DC_VOLTAGE', 'NORM_DC_CURRENT',
        'NORM_POWER_VOLATILITY', 'NORM_CURRENT_IMBALANCE', 'NORM_VOLTAGE_SPREAD',
        'DC_AC_RATIO', 'EFFICIENCY', 'PERFORMANCE_RATIO', 'DC_AC_DEV',
        'AMBIENT_TEMP', 'MODULE_TEMP', 'TEMP_COEFF', 'TEMP_DIFFERENCE', 'TEMP_DEV',
        'WIND_SPEED', 'IRRADIATION', 'CLEARNESS_INDEX', 'DIFFUSE_RATIO',
        'CLOUD_COVER_EST', 'SKY_TEMP_EST', 'ZENITH_ANGLE', 'AZIMUTH_ANGLE',
        'HOUR', 'DAY_OF_YEAR', 'MONTH'
    ]

    NUM_FEATURES = 27

    # Default model key (lgb = LightGBM, best performing)
    DEFAULT_MODEL = 'lgb'
