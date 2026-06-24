import pymysql
import pymysql.cursors
from config import Config

_pool = None


def _get_pool():
    global _pool
    if _pool is not None:
        return _pool
    try:
        from dbutils.pooled_db import PooledDB
        _pool = PooledDB(
            creator         = pymysql,
            mincached       = 0,
            maxcached       = 4,
            maxconnections  = 6,
            blocking        = True,
            host            = Config.DB_HOST,
            user            = Config.DB_USER,
            password        = Config.DB_PASSWORD,
            database        = Config.DB_NAME,
            port            = Config.DB_PORT,
            charset         = 'utf8mb4',
            cursorclass     = pymysql.cursors.DictCursor,
            connect_timeout = 10,
            autocommit      = False,
        )
        return _pool
    except Exception as e:
        print(f'[db] Pool creation failed: {e}')
        return None


def get_connection():
    pool = _get_pool()
    if pool:
        return pool.connection()
    return pymysql.connect(
        host            = Config.DB_HOST,
        user            = Config.DB_USER,
        password        = Config.DB_PASSWORD,
        database        = Config.DB_NAME,
        port            = Config.DB_PORT,
        charset         = 'utf8mb4',
        cursorclass     = pymysql.cursors.DictCursor,
        connect_timeout = 10,
        autocommit      = False,
    )


def query_db(sql, args=(), one=False, commit=False):
    try:
        conn = get_connection()
        with conn.cursor() as cursor:
            cursor.execute(sql, args)
            if commit:
                conn.commit()
                return cursor.lastrowid
            rv = cursor.fetchall()
            return (rv[0] if rv else None) if one else rv
    except Exception as e:
        print(f'[db] query_db error: {e}')
        return None if one else []
    finally:
        try:
            conn.close()
        except Exception:
            pass


def execute_db(sql, args=()):
    try:
        conn = get_connection()
        with conn.cursor() as cursor:
            cursor.execute(sql, args)
            conn.commit()
            return cursor.lastrowid
    except Exception as e:
        print(f'[db] execute_db error: {e}')
        return None
    finally:
        try:
            conn.close()
        except Exception:
            pass
