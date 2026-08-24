from pathlib import Path
from urllib.parse import urlsplit
import os

import psycopg2


def load_env_file():
    env_path = Path(__file__).with_name('.env')
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding='utf-8').splitlines():
        line = raw_line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, value = line.split('=', 1)
        os.environ.setdefault(key.strip(), value.strip())


def main():
    load_env_file()
    database_url = os.environ.get('LABCLINICO_DATABASE_URL')
    if not database_url:
        raise RuntimeError('No existe LABCLINICO_DATABASE_URL en .env')

    normalized_url = database_url.replace('postgresql+psycopg2://', 'postgresql://', 1)
    parsed = urlsplit(normalized_url)
    db_name = parsed.path.lstrip('/')
    if not db_name:
        raise RuntimeError('LABCLINICO_DATABASE_URL no contiene nombre de base de datos')

    admin_conn = psycopg2.connect(
        host=parsed.hostname or '127.0.0.1',
        port=parsed.port or 5432,
        user=parsed.username or 'postgres',
        password=parsed.password or '',
        dbname='postgres',
    )
    admin_conn.autocommit = True

    try:
        with admin_conn.cursor() as cur:
            cur.execute('SELECT 1 FROM pg_database WHERE datname = %s', (db_name,))
            exists = cur.fetchone() is not None
            if exists:
                print(f'La base {db_name} ya existe.')
                return

            cur.execute(
                f'CREATE DATABASE "{db_name}" WITH OWNER "{parsed.username or "postgres"}" ENCODING \'UTF8\' TEMPLATE template0'
            )
            print(f'Base creada: {db_name}')
    finally:
        admin_conn.close()


if __name__ == '__main__':
    main()
