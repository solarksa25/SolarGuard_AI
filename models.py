"""
SolarGuard AI — User Model for Flask-Login
Uses MySQL users table with bcrypt password hashing.
"""
from db import query_db

_user_cache = {}


class User:
    def __init__(self, row):
        self.id         = row['id']
        self.full_name  = row['full_name']
        self.email      = row['email']
        self.phone      = row.get('phone', '')
        self.role       = row.get('role', 'engineer')
        self.password_hash = row.get('password_hash', '')

    @property
    def is_authenticated(self):
        return True

    @property
    def is_active(self):
        return True

    @property
    def is_anonymous(self):
        return False

    def get_id(self):
        return str(self.id)

    @staticmethod
    def get_by_id(user_id):
        if user_id in _user_cache:
            return _user_cache[user_id]
        row = query_db('SELECT * FROM users WHERE id = %s', (user_id,), one=True)
        if row:
            user = User(row)
            _user_cache[user_id] = user
            return user
        return None

    @staticmethod
    def get_by_email(email):
        return query_db('SELECT * FROM users WHERE email = %s', (email,), one=True)

    @staticmethod
    def get_all():
        return query_db('SELECT * FROM users ORDER BY id')

    @staticmethod
    def create(full_name, phone, email, password_hash, role='engineer'):
        return query_db(
            'INSERT INTO users (full_name, phone, email, password_hash, role) '
            'VALUES (%s, %s, %s, %s, %s)',
            (full_name, phone, email, password_hash, role),
            commit=True,
        )

    @staticmethod
    def delete(user_id):
        query_db('DELETE FROM users WHERE id = %s', (user_id,), commit=True)

    @staticmethod
    def update(user_id, full_name=None, phone=None, role=None):
        parts, args = [], []
        if full_name:
            parts.append('full_name = %s'); args.append(full_name)
        if phone:
            parts.append('phone = %s'); args.append(phone)
        if role:
            parts.append('role = %s'); args.append(role)
        if not parts:
            return
        args.append(user_id)
        query_db(f'UPDATE users SET {", ".join(parts)} WHERE id = %s', args, commit=True)


def _load_cache():
    rows = query_db('SELECT * FROM users')
    if rows:
        _user_cache.clear()
        for r in rows:
            _user_cache[r['id']] = User(r)
