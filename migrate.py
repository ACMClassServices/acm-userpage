#!/usr/bin/env python3

import sqlite3

try:
    from config import DB_NAME
except ModuleNotFoundError:
    DB_NAME = '/srv/userpage/userpage.db'

init_script = '''
BEGIN;
CREATE TABLE keys (
    jaccount TEXT UNIQUE,
    stuid TEXT UNIQUE,
    keys TEXT
);
CREATE TABLE members (
    stuid TEXT UNIQUE,
    name TEXT
);
CREATE TABLE sites (
    jaccount TEXT UNIQUE,
    slug TEXT UNIQUE,
    stuid TEXT UNIQUE,
    token TEXT
);
CREATE TABLE version (
    version INTEGER
);
INSERT INTO version (version) VALUES (1);
COMMIT;
'''

upgrade_scripts = [
    '''
    BEGIN;
    CREATE TABLE sites (
        jaccount TEXT UNIQUE,
        stuid TEXT UNIQUE,
        slug TEXT UNIQUE,
        token TEXT
    );
    INSERT INTO sites SELECT jaccount, stuid, jaccount as slug, NULL as token FROM keys;
    CREATE TABLE version (version INTEGER);
    INSERT INTO version (version) VALUES (1);
    COMMIT;
    ''',
]

latest_version = len(upgrade_scripts)

def get_version(db):
    has_version = db.execute('''SELECT name FROM sqlite_master WHERE name = 'version';''').fetchone()
    if has_version is None:
        has_tables = db.execute('''SELECT name FROM sqlite_master WHERE name = 'members';''').fetchone()
        if has_tables is None:
            return None
        else:
            return 0
    else:
        return db.execute('SELECT version FROM version;').fetchone()[0]

def is_up_to_date(db):
    return get_version(db) == latest_version

def main():
    db = sqlite3.connect(DB_NAME)

    version = get_version(db)
    if version is None:
        print('Initialising database')
        db.executescript(init_script)
    elif version < latest_version:
        print(f'Upgrading from version {version} to {latest_version}...')
        for i in range(version, latest_version):
            print(f'Running upgrade script {i} to {i + 1}')
            db.executescript(upgrade_scripts[i])
    elif version == latest_version:
        print('Already up-to-date')
    else:
        print('ERROR: unknown database version')
        exit(1)

if __name__ == '__main__':
    main()
